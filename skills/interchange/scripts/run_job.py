#!/usr/bin/env python3
"""One bounded external process; durable logs + terminal event, no model polling."""
import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import stat
from pathlib import Path
import signal
import sqlite3
import subprocess
import threading
import time

from relay import (acquire_managed_action, connect, emit, notify,
                   release_managed_action)

SUPERVISOR_ARTIFACTS = frozenset({'process-result.json', 'runner.json', 'stdout.log', 'stderr.log'})


def stop(proc):
    # Detached grandchildren may escape this group: abnormal exit requires ownership inspection.
    try:
        if os.name == 'posix': os.killpg(proc.pid, signal.SIGKILL)
        else: proc.kill()
    except (ProcessLookupError, PermissionError):
        if proc.poll() is None:
            proc.kill()


def _write_existing_regular(path, payload):
    fd = os.open(path, os.O_WRONLY | os.O_TRUNC | getattr(os, 'O_NOFOLLOW', 0))
    with os.fdopen(fd, 'w') as stream:
        if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
            raise ValueError('runner artifact is not a regular file')
        stream.write(json.dumps(payload))


def _output_limit_kill(manifest):
    """Return the explicit output-limit termination choice from a manifest."""
    choices = []
    for key in ('kill_on_output_limit', 'terminate_on_output_limit'):
        if key in manifest:
            value = manifest[key]
            if not isinstance(value, bool):
                raise ValueError(f'{key} must be a boolean')
            choices.append((key, value))
    if len(choices) == 2 and choices[0][1] != choices[1][1]:
        raise ValueError('conflicting output-limit termination options')
    return choices[0][1] if choices else False


def _final_artifact_path(manifest, directory):
    """Resolve the optional compact worker final artifact inside its attempt root."""
    configured = manifest.get('final_artifact')
    if configured is None:
        return None
    if not isinstance(configured, str) or not configured:
        raise ValueError('final_artifact must be a nonempty path string')
    path = Path(configured)
    if not path.is_absolute():
        path = directory / path
    path = path.resolve()
    if not path.is_relative_to(directory):
        raise ValueError('final_artifact must remain inside the attempt artifact root')
    if path.name in SUPERVISOR_ARTIFACTS:
        raise ValueError('final_artifact names a supervisor-owned artifact')
    return path


ENV_NAME = re.compile(r'^[A-Z_][A-Z0-9_]{0,127}$')
SECRET_NAME = re.compile(r'(TOKEN|SECRET|PASSWORD|PASSWD|API_?KEY|PRIVATE|CREDENTIAL)')


def _manifest_env(manifest):
    """Validate the optional non-secret environment map a worker needs (e.g. an OpenCode config).

    Credentials stay in the inherited environment; a name that looks like a secret is refused so a
    manifest can never become the place a token is written down.
    """
    configured = manifest.get('env')
    if configured is None:
        return {}
    if not isinstance(configured, dict):
        raise ValueError('env must be an object of string names to string values')
    result = {}
    for name, value in configured.items():
        if not isinstance(name, str) or not ENV_NAME.match(name):
            raise ValueError('env names must be upper-case shell identifiers')
        if SECRET_NAME.search(name):
            raise ValueError(f'env name {name} looks like a secret; keep credentials in the inherited environment')
        if not isinstance(value, str) or len(value) > 65536:
            raise ValueError(f'env value for {name} must be a string of at most 64 KiB')
        result[name] = value
    return result


def _isolated_worker(manifest, environment):
    """Return an optional privilege drop for a distinct-UID publication job.

    The default same-user adapter guards routine tool use; it is not a host
    security boundary. A separately provisioned UID provides stronger isolation.
    """
    if 'post_return' not in manifest and 'execution_isolation' not in manifest:
        return None
    config = manifest.get('execution_isolation') or {'mode': 'same_user'}
    if config.get('mode') == 'same_user':
        return None
    if not isinstance(config, dict) or config.get('mode') != 'distinct_uid':
        raise ValueError('unsupported post_return execution isolation')
    uid, gid = config.get('uid'), config.get('gid')
    if (not isinstance(uid, int) or isinstance(uid, bool) or not isinstance(gid, int)
            or isinstance(gid, bool) or uid <= 0 or gid <= 0 or uid == os.geteuid()):
        raise ValueError('worker must use a distinct unprivileged UID/GID')
    if os.geteuid() != 0:
        raise ValueError('distinct_uid isolation requires a privileged supervisor')
    home = Path(config.get('home', '')).resolve(strict=True)
    stat = home.stat()
    if not home.is_dir() or stat.st_uid != uid or stat.st_mode & 0o077:
        raise ValueError('isolated worker home must be private and owned by its UID')
    # Never pass the coordinator's publication credentials or browser profile.
    for name in list(environment):
        if (SECRET_NAME.search(name) or name.startswith(('GH_', 'GITHUB_', 'GIT_', 'SSH_',
                                                         'CODEX_', 'CLAUDE_', 'CHROME_', 'BROWSER_'))
                or name in {'HOME', 'XDG_CONFIG_HOME', 'XDG_DATA_HOME', 'XDG_CACHE_HOME'}):
            environment.pop(name, None)
    environment['HOME'] = str(home)
    environment['XDG_CONFIG_HOME'] = str(home / '.config')
    environment['XDG_DATA_HOME'] = str(home / '.local/share')
    environment['XDG_CACHE_HOME'] = str(home / '.cache')
    environment['GIT_CONFIG_GLOBAL'] = os.devnull
    environment['GIT_CONFIG_SYSTEM'] = os.devnull
    def drop():
        os.setgroups([])
        os.setgid(gid)
        os.setuid(uid)
    return drop


def _worker_adapter(manifest, environment):
    """Install the declared OpenCode tool policy for an opt-in implementation job.

    Same-user permissions guard routine model tool use, not arbitrary code run
    by a hostile process with access to the same account.
    """
    if 'post_return' not in manifest:
        return None
    adapter = manifest.get('worker_adapter')
    if not isinstance(adapter, dict) or adapter.get('kind') != 'opencode-headless':
        raise ValueError('post_return requires the supported opencode-headless worker adapter')
    argv = manifest['argv']
    if (Path(argv[0]).name != 'opencode' or len(argv) < 2 or argv[1] != 'run'
            or argv.count('--pure') != 1 or argv.count('--format') != 1
            or argv[argv.index('--format') + 1:argv.index('--format') + 2] != ['json']):
        raise ValueError('OpenCode worker must use run --pure --format json')
    forbidden = {'--attach', '--auto', '--share', '--continue', '--session', '--fork',
                 '--agent', '--command', '--dir', '--file', '--password', '--username',
                 '--port', '--interactive', '--no-pure'}
    owned = {'--pure', '--format', '--model'}
    if any((arg.split('=', 1)[0] in forbidden or
            (arg.startswith('--') and '=' in arg and arg.split('=', 1)[0] in owned) or
            any(arg.startswith('-' + short) for short in ('c', 's', 'f', 'i', 'p', 'u')) or
            (arg.startswith('-m') and arg != '-m'))
           for arg in argv[2:]):
        raise ValueError('OpenCode worker may not override its session, cwd, agent, or tool policy')
    if argv.count('--model') + argv.count('-m') != 1:
        raise ValueError('OpenCode worker requires one explicit provider/model')
    model = None
    for flag in ('--model', '-m'):
        if flag in argv and argv.index(flag) + 1 < len(argv):
            model = argv[argv.index(flag) + 1]
    if not isinstance(model, str) or '/' not in model:
        raise ValueError('OpenCode worker requires an explicit provider/model')
    allowed = adapter.get('allowed_bash')
    if not isinstance(allowed, list) or not allowed or not all(isinstance(x, str) and x.strip() for x in allowed):
        raise ValueError('OpenCode adapter needs explicit allowed_bash commands')
    bash = {'*': 'deny'}
    safe_git_subcommands = {'add', 'branch', 'cat-file', 'checkout', 'commit', 'describe',
                            'diff', 'diff-tree', 'fetch', 'log', 'ls-files', 'merge',
                            'rebase', 'restore', 'rev-parse', 'show', 'status', 'switch'}
    prefix_tools = {'ls', 'grep', 'sed', 'rg', 'cat', 'head', 'tail', 'wc', 'find',
                    'echo', 'printf'}
    for pattern in allowed:
        # v1.18.32 scans each command in a shell chain independently. A
        # trailing ` *` is therefore a bounded argument prefix; a bare `*`
        # or a wildcard inside the executable/subcommand remains too broad.
        prefix = pattern.endswith(' *')
        literal = pattern[:-2] if prefix else pattern
        if any(char in literal for char in (';', '|', '&', '`', '$', '>', '<', '\n', '\r')):
            raise ValueError('OpenCode allowed_bash cannot contain shell operators')
        if any(char in literal for char in ('*', '?', '[', ']')) or (not prefix and '*' in pattern):
            raise ValueError('OpenCode allowed_bash supports only trailing argument prefixes')
        try:
            tokens = shlex.split(literal)
        except ValueError as exc:
            raise ValueError('invalid OpenCode allowed_bash command') from exc
        if not tokens or '/' in tokens[0] or tokens[0] in ('gh', 'curl', 'wget', 'ssh', 'scp', 'open', 'osascript',
                                      'sudo', 'env', 'sh', 'zsh'):
            raise ValueError('OpenCode allowed_bash includes an unsafe command')
        if tokens[0] == 'git' and (len(tokens) < 2 or tokens[1] not in safe_git_subcommands):
            raise ValueError('OpenCode allowed_bash requires a literal safe Git subcommand')
        if tokens[0] == 'bash':
            script_arg = tokens[2] if len(tokens) >= 3 and tokens[1] == '-n' else (
                tokens[1] if len(tokens) >= 2 else None)
            script = Path(script_arg) if script_arg is not None else None
            if (script is None or script.is_absolute() or '..' in script.parts
                    or script.suffix != '.sh' or str(script) in ('.', '..')):
                raise ValueError('OpenCode bash permission requires a repo-relative .sh script')
        if tokens[0] == 'dotnet' and (len(tokens) < 2 or tokens[1] not in
                                      {'test', 'build', 'restore', 'format'}):
            raise ValueError('OpenCode dotnet permission requires a bounded subcommand')
        if tokens[0] in ('python', 'python3') and (len(tokens) < 3 or tokens[1] != '-m'
                                                  or tokens[2] not in ('unittest', 'pytest')):
            raise ValueError('OpenCode Python permission requires a test module')
        if prefix and tokens[0] not in prefix_tools | {'git', 'bash', 'dotnet', 'python', 'python3'}:
            raise ValueError('OpenCode allowed_bash prefix requires a qualified command')
        if any(re.search(r'(^|[^a-z])(gh|browser|chrome)([^a-z]|$)', token.lower()) for token in tokens):
            raise ValueError('OpenCode allowed_bash includes publication or browser access')
        bash[pattern] = 'allow'
    # Last matching rule wins. The v1.18.32 scanner checks every chained
    # command, so a later forbidden command cannot inherit an allowed prefix.
    bash.update({'git push*': 'deny', 'gh*': 'deny', 'curl*': 'deny', 'wget*': 'deny',
                 'ssh*': 'deny', 'scp*': 'deny', 'open*': 'deny', 'osascript*': 'deny',
                 '*browser*': 'deny', '*chrome*': 'deny', '*playwright*': 'deny',
                 '*computer*': 'deny'})
    permissions = {'read': 'allow', 'edit': 'allow', 'glob': 'allow', 'grep': 'allow',
                   'list': 'allow', 'todowrite': 'allow', 'bash': bash,
                   'webfetch': 'deny', 'websearch': 'deny', 'task': 'deny',
                   'question': 'deny', 'skill': 'deny', 'external_directory': 'deny',
                   'browser': 'deny', 'chrome': 'deny', 'browser*': 'deny',
                   'chrome*': 'deny', 'playwright*': 'deny', 'computer*': 'deny',
                   'mcp*': 'deny', 'mcp__*': 'deny'}
    configured = manifest.get('env') or {}
    if any(name.startswith('OPENCODE_CONFIG') for name in configured):
        raise ValueError('worker adapter owns OpenCode permission configuration')
    for name in list(environment):
        if name.startswith('OPENCODE_CONFIG'):
            environment.pop(name, None)
    environment['OPENCODE_CONFIG_CONTENT'] = json.dumps({'permission': permissions, 'mcp': {}, 'plugin': []},
                                                        separators=(',', ':'))
    return {'kind': 'opencode-headless', 'model_requested': model,
            'permission_sha256': hashlib.sha256(environment['OPENCODE_CONFIG_CONTENT'].encode()).hexdigest()}


def _verify_worker_adapter(manifest, environment, privilege_drop):
    """Resolve the exact client config before model launch; reject inherited MCP/plugins."""
    if 'post_return' not in manifest:
        return
    # OpenCode's run command prefers PWD over process.cwd() when selecting its
    # project. Its config probe must observe the same canonical checkout.
    environment['PWD'] = str(Path(manifest['cwd']).resolve(strict=True))
    environment.pop('OLDPWD', None)
    argv = manifest['argv']
    if any(pattern.endswith(' *') for pattern in manifest['worker_adapter']['allowed_bash']):
        try:
            version = subprocess.run([argv[0], '--version'], cwd=manifest['cwd'], env=environment,
                                     preexec_fn=privilege_drop, stdin=subprocess.DEVNULL,
                                     capture_output=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ValueError('OpenCode Bash prefix version probe did not complete') from exc
        if version.returncode or version.stdout.decode(errors='replace').strip() != '1.18.32':
            raise ValueError('OpenCode Bash prefixes require qualified version 1.18.32')
    try:
        check = subprocess.run([argv[0], 'debug', 'config', '--pure'], cwd=manifest['cwd'],
                               env=environment, preexec_fn=privilege_drop, stdin=subprocess.DEVNULL,
                               capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ValueError('OpenCode adapter configuration probe did not complete') from exc
    if check.returncode:
        raise ValueError('OpenCode adapter configuration probe failed')
    try:
        loaded = json.loads(check.stdout)
        declared = json.loads(environment['OPENCODE_CONFIG_CONTENT'])
    except (ValueError, KeyError) as exc:
        raise ValueError('OpenCode adapter configuration was not JSON') from exc
    if loaded.get('mcp') or loaded.get('plugin'):
        raise ValueError('OpenCode adapter inherited external MCP/plugins')
    actual = loaded.get('permission') or {}
    expected = declared['permission']
    if any(actual.get(key) != value for key, value in expected.items()):
        raise ValueError('OpenCode adapter did not load declared tool denies')


def _private_artifact_root(manifest, row, directory, cwd):
    """Create private supervisor artifacts before an isolated child can execute."""
    if (manifest.get('execution_isolation') or {}).get('mode') != 'distinct_uid':
        return
    config = manifest.get('execution_isolation') or {}
    uid, gid = config.get('uid'), config.get('gid')
    if not isinstance(uid, int) or not isinstance(gid, int):
        raise ValueError('isolated artifact root needs worker UID/GID')
    root = Path(row['root']).resolve(strict=True)
    home = Path(config.get('home', '')).resolve(strict=True)
    if (root.is_relative_to(cwd) or cwd.is_relative_to(root)
            or root.is_relative_to(home) or home.is_relative_to(root)):
        raise ValueError('isolated artifacts cannot overlap worker checkout or home')
    root_stat = root.stat()
    if root_stat.st_uid != os.geteuid() or stat.S_IMODE(root_stat.st_mode) & 0o077:
        raise ValueError('registered artifact root must be supervisor-owned and mode 0700')
    for ancestor in (root, *root.parents):
        info = ancestor.stat()
        mode = stat.S_IMODE(info.st_mode)
        if info.st_uid == uid:
            raise ValueError('worker owns an artifact ancestor')
        if (mode & 0o002 and not mode & stat.S_ISVTX) or (info.st_gid == gid and mode & 0o020):
            raise ValueError('worker can mutate an artifact ancestor')
    current = root
    for part in directory.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            raise ValueError('artifact path contains a symlink')
        if not current.exists():
            current.mkdir(mode=0o700)
        info = current.stat()
        if not current.is_dir() or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('artifact directory must be supervisor-owned and mode 0700')


def _private_state_path(manifest, state, cwd):
    if (manifest.get('execution_isolation') or {}).get('mode') != 'distinct_uid':
        return
    config = manifest.get('execution_isolation') or {}
    uid, gid = config.get('uid'), config.get('gid')
    if not isinstance(uid, int) or not isinstance(gid, int):
        raise ValueError('isolated state needs worker UID/GID')
    path = Path(state).absolute()
    parent = path.parent.resolve(strict=True)
    home = Path(config.get('home', '')).resolve(strict=True)
    if (parent.is_relative_to(cwd) or cwd.is_relative_to(parent)
            or parent.is_relative_to(home) or home.is_relative_to(parent)):
        raise ValueError('isolated state cannot overlap worker checkout or home')
    if path.is_symlink():
        raise ValueError('state path cannot be a symlink')
    info = parent.stat()
    if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
        raise ValueError('state parent must be supervisor-owned and mode 0700')
    for ancestor in (parent, *parent.parents):
        info = ancestor.stat()
        mode = stat.S_IMODE(info.st_mode)
        if info.st_uid == uid or (mode & 0o002 and not mode & stat.S_ISVTX) or (info.st_gid == gid and mode & 0o020):
            raise ValueError('worker can mutate a state ancestor')
    if path.exists():
        info = path.stat()
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise ValueError('state file must be supervisor-owned and private')


def _canonical_state(state):
    return Path(state).resolve(strict=False)


def _final_artifact_source(manifest, cwd):
    """Resolve an optional worker-written final inside the worker's own cwd.

    A sandboxed worker (e.g. OpenCode with external_directory denied) cannot write into the
    attempt root. It writes its final inside its worktree instead; the runner copies it into the
    attempt root after exit so the usual integrity proof applies.
    """
    configured = manifest.get('final_artifact_source')
    if configured is None:
        return None
    if not isinstance(configured, str) or not configured or Path(configured).is_absolute():
        raise ValueError('final_artifact_source must be a nonempty path relative to cwd')
    path = (cwd / configured).resolve()
    if not path.is_relative_to(cwd):
        raise ValueError('final_artifact_source must remain inside cwd')
    if path.exists() or path.is_symlink():
        raise ValueError('final_artifact_source already exists; use an attempt-specific path so an earlier final is never reused')
    return path


def _collect_final_artifact(source, target, cwd, directory, launched_at):
    """Copy the worker's in-cwd final into the attempt root without following either side outside.

    The source must resolve inside cwd, be a regular file and have been written after launch (a final
    left by an earlier attempt is never reused). The destination is created fresh with O_EXCL|O_NOFOLLOW
    after removing only a plain file this runner owns, so a planted symlink can never redirect the write.
    """
    if source is None or target is None:
        return
    try:
        resolved = source.resolve()
        if not resolved.is_relative_to(cwd) or not resolved.is_file():
            return
        info = resolved.stat()
        if info.st_size > 1_000_000 or info.st_mtime < launched_at:
            return
        if not target.parent.resolve().is_relative_to(directory):
            return
        if target.is_symlink():
            return
        if target.exists():
            if not target.is_file():
                return
            target.unlink()
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0)
        fd = os.open(target, flags, 0o600)
        with os.fdopen(fd, 'wb') as out, resolved.open('rb') as src:
            shutil.copyfileobj(src, out)
    except OSError:
        return


def _final_artifact_proof(path, directory):
    """Return integrity evidence for a compact worker final, never an acceptance claim."""
    if path is None:
        return {
            'configured': False,
            'path': None,
            'status': 'not_configured',
            'validated': False,
            'bytes': 0,
            'sha256': None,
        }
    try:
        # Resolve again after the worker exits. A worker can replace the configured
        # path with a symlink after launch; never hash a target outside this attempt.
        resolved = path.resolve()
        if not resolved.is_relative_to(directory):
            return {'configured': True, 'path': str(path), 'status': 'outside_artifact_root',
                    'validated': False, 'bytes': 0, 'sha256': None}
        if resolved.name in SUPERVISOR_ARTIFACTS:
            return {'configured': True, 'path': str(path), 'status': 'supervisor_artifact',
                    'validated': False, 'bytes': 0, 'sha256': None}
        size = resolved.stat().st_size
        if not resolved.is_file():
            return {'configured': True, 'path': str(path), 'status': 'not_a_file',
                    'validated': False, 'bytes': size, 'sha256': None}
        if size == 0:
            return {'configured': True, 'path': str(path), 'status': 'empty',
                    'validated': False, 'bytes': 0, 'sha256': None}
        if size > 1_000_000:
            return {'configured': True, 'path': str(path), 'status': 'too_large',
                    'validated': False, 'bytes': size, 'sha256': None}
        digest = hashlib.sha256()
        with resolved.open('rb') as source:
            for block in iter(lambda: source.read(64 * 1024), b''):
                digest.update(block)
        return {'configured': True, 'path': str(path), 'status': 'validated',
                'validated': True, 'bytes': size, 'sha256': digest.hexdigest()}
    except (FileNotFoundError, NotADirectoryError):
        return {'configured': True, 'path': str(path), 'status': 'missing',
                'validated': False, 'bytes': 0, 'sha256': None}
    except RuntimeError:
        return {'configured': True, 'path': str(path), 'status': 'unreadable',
                'validated': False, 'bytes': 0, 'sha256': None,
                'error_type': 'symlink_loop'}
    except OSError as exc:
        return {'configured': True, 'path': str(path), 'status': 'unreadable',
                'validated': False, 'bytes': 0, 'sha256': None,
                'error_type': type(exc).__name__}


def _collect_stream_final(manifest, target, directory):
    """Copy a structured headless reviewer verdict from its bounded event stream."""
    if not manifest.get('final_artifact_from_stdout') or target is None:
        return
    if target.exists() or target.is_symlink():
        return
    stdout = directory / 'stdout.log'
    if not stdout.is_file():
        return
    verdict = None
    with stdout.open('rb') as stream:
        for raw in stream:
            if len(raw) > 100_000:
                continue
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            if event.get('type') == 'result' and isinstance(event.get('result'), str):
                candidate = event['result']
            elif event.get('type') == 'item.completed' and event.get('item', {}).get('type') == 'agent_message':
                candidate = event['item'].get('text')
            else:
                continue
            try:
                parsed = json.loads(candidate)
            except (TypeError, ValueError):
                continue
            if (isinstance(parsed, dict) and parsed.get('verdict') in ('passed', 'changes_needed')
                    and isinstance(parsed.get('reviewed_head'), str)):
                verdict = parsed
    if verdict is not None:
        fd = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, 'O_NOFOLLOW', 0), 0o600)
        with os.fdopen(fd, 'w') as out:
            json.dump(verdict, out)
            out.write('\n')


def run(manifest, state, directory):
    argv = manifest['argv']
    if not isinstance(argv,list) or not argv or any(not isinstance(x,str) for x in argv):
        raise ValueError('argv must be a nonempty literal string array')
    cwd = Path(manifest['cwd']).resolve(strict=True)
    timeout = float(manifest['timeout_seconds'])
    limit = int(manifest.get('max_output_bytes', 2_000_000))
    if not 0 < timeout <= 10800 or not 1024 <= limit <= 20_000_000:
        raise ValueError('invalid deadline/output budget')
    directory = Path(directory).resolve()
    # Use the canonical state path for every DB open and child handoff. A worker
    # must not be able to swap a symlink in the caller's original path later.
    state = _canonical_state(state)
    kill_on_output_limit = _output_limit_kill(manifest)
    extra_env = _manifest_env(manifest)
    final_source = _final_artifact_source(manifest, cwd)
    if final_source is not None and manifest.get('final_artifact') is None:
        manifest = {**manifest, 'final_artifact': 'final.md'}
    final_artifact_path = _final_artifact_path(manifest, directory)
    _private_state_path(manifest, state, cwd)
    db = connect(state)
    row = db.execute('SELECT * FROM attempts WHERE job=? AND attempt=?',
                     (manifest['job'],manifest['attempt'])).fetchone()
    if not row or row['sender'] != manifest['sender'] or not directory.is_relative_to(Path(row['root'])):
        db.close(); raise ValueError('register matching attempt and artifact root first')
    bound = db.execute('SELECT project,registered_generation FROM attempt_projects WHERE job=? AND attempt=?',
                       (manifest['job'], manifest['attempt'])).fetchone()
    if 'post_return' in manifest and (not bound or bound['project'] != manifest['post_return'].get('project')
                                      or bound['registered_generation'] != manifest['post_return'].get('generation')):
        db.close(); raise ValueError('post_return requires a matching project-bound worker attempt')
    _private_artifact_root(manifest, row, directory, cwd)
    try:
        with db:
            db.execute('INSERT INTO launches VALUES (?,?,?,?)',
                       (manifest['job'],manifest['attempt'],str(directory),str(time.time())))
    except sqlite3.IntegrityError:
        db.close()
        raise FileExistsError('attempt already launched; inspect existing ownership before retry')
    directory.mkdir(parents=True,exist_ok=True)
    # Exclusive lease intentionally survives a crash. Never auto-launch a duplicate writer.
    lease = directory/'runner.json'
    try:
        fd = os.open(lease,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
        os.close(fd)
    except Exception:
        db.close()
        raise
    begun = time.monotonic()
    launched_wall = time.time() - 1  # mtime granularity margin
    deadline_wall = time.time() + timeout
    proc = None
    output_truncated = threading.Event()
    output_limit_kill_requested = threading.Event()
    lock = threading.Lock()
    seen_bytes = 0
    captured_bytes = 0
    logs = []
    publication_preflight = None
    worker_adapter_receipt = None
    try:
        environment = os.environ.copy()
        environment.update(extra_env)
        # Popen(cwd=...) changes the OS cwd but some clients (OpenCode included)
        # select their project from inherited PWD. Bind both before any probe.
        environment['PWD'] = str(cwd)
        environment.pop('OLDPWD', None)
        privilege_drop = _isolated_worker(manifest, environment)
        worker_adapter_receipt = _worker_adapter(manifest, environment)
        _verify_worker_adapter(manifest, environment, privilege_drop)
        if worker_adapter_receipt is not None:
            # Caller-supplied --dir is forbidden by _worker_adapter. This
            # runner-owned absolute argument pins OpenCode's session directory.
            argv = [argv[0], 'run', '--dir', str(cwd), *argv[2:]]
            worker_adapter_receipt['session_directory'] = str(cwd)
        if 'post_return' in manifest:
            import post_return
            publication_preflight = post_return.preflight(manifest['post_return'], manifest, cwd,
                                                          environment, privilege_drop)
        if final_source is not None:
            # The worker writes where it can: its own cwd. The runner copies it into the attempt root.
            environment['INTERCHANGE_FINAL_ARTIFACT'] = str(final_source)
        elif final_artifact_path is not None and not manifest.get('final_artifact_from_stdout'):
            environment['INTERCHANGE_FINAL_ARTIFACT'] = str(final_artifact_path)
        # stdin is always closed: an inherited open, non-TTY stdin makes some headless workers
        # (OpenCode) wait forever and print nothing.
        launch_owner = manifest.get('launch_generation')
        if bound:
            registered_owner = {'project': bound['project'], 'generation': bound['registered_generation']}
            if launch_owner is not None and launch_owner != registered_owner:
                raise ValueError('launch generation conflicts with bound attempt')
            launch_owner = registered_owner
        if launch_owner is None and 'post_return' in manifest:
            launch_owner = {key: manifest['post_return'][key] for key in ('project', 'generation')}
        launch_token = None
        try:
            if launch_owner is not None:
                launch_token = acquire_managed_action(db, launch_owner['project'],
                                                      launch_owner['generation'], 'worker-launch')
            proc = subprocess.Popen(argv,cwd=cwd,env=environment,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE,start_new_session=True,preexec_fn=privilege_drop)
        finally:
            if launch_token is not None:
                release_managed_action(db, launch_token)
        _write_existing_regular(lease, {'runner_pid':os.getpid(),'worker_pid':proc.pid,'state':'running',
                                        'job':manifest['job'],'attempt':manifest['attempt'],
                                        'timeout_seconds':timeout,'deadline_at':deadline_wall})
        def drain(stream,path):
            nonlocal seen_bytes, captured_bytes
            outfd = os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(outfd,'wb') as out:
                while True:
                    # read1 drains bytes already available without waiting for a full
                    # 4096-byte chunk; the supervisor's wall-clock deadline must not
                    # be hidden behind a buffered pipe read.
                    block = stream.read1(4096)
                    if not block: break
                    with lock:
                        seen_bytes += len(block)
                        available = max(0, limit-captured_bytes)
                        captured = block[:available]
                        captured_bytes += len(captured)
                        exceeded = len(block) > available
                        if exceeded:
                            output_truncated.set()
                            should_kill = kill_on_output_limit and not output_limit_kill_requested.is_set()
                            if should_kill:
                                output_limit_kill_requested.set()
                        else:
                            should_kill = False
                    out.write(captured)
                    if captured:
                        out.flush()  # publish short structured events before process exit
                    if should_kill:
                        stop(proc)
            stream.close()
        for name,stream in [('stdout.log',proc.stdout),('stderr.log',proc.stderr)]:
            thread = threading.Thread(target=drain,args=(stream,directory/name),daemon=True)
            thread.start();logs.append(thread)
        try:
            exit_code = proc.wait(timeout=timeout)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            stop(proc); exit_code = proc.wait(timeout=5)
        for thread in logs: thread.join(timeout=2)
        if any(thread.is_alive() for thread in logs):
            # A descendant retains a pipe. Do not infer that the whole writer is gone.
            outcome='descendant_or_pipe_open'; stop(proc)
        elif timed_out:
            outcome='timeout'
        elif output_limit_kill_requested.is_set():
            outcome='output_limit'
        else:
            outcome='exited'
        _collect_final_artifact(final_source, final_artifact_path, cwd, directory, launched_wall)
        _collect_stream_final(manifest, final_artifact_path, directory)
        final_proof = _final_artifact_proof(final_artifact_path, directory)
        result = {'job':manifest['job'],'attempt':manifest['attempt'],'sender':manifest['sender'],
                  'process_outcome':outcome,'exit_code':exit_code,'seconds':round(time.monotonic()-begun,3),
                  'output_bytes_seen':seen_bytes,'output_bytes_captured':captured_bytes,
                  'output_truncated':output_truncated.is_set(),
                  'output_limit_action':'kill' if kill_on_output_limit else 'drain',
                  'final_artifact':final_proof,
                  'final_artifact_validated':final_proof['validated'],
                  'publication_preflight':publication_preflight,
                  'worker_adapter':worker_adapter_receipt,
                  'accepted':False,'worker_result_verified':False,
                  'ownership_check_required':outcome!='exited' or exit_code!=0 or
                  output_truncated.is_set() or not final_proof['validated'],
                  'stdout':str(directory/'stdout.log'),'stderr':str(directory/'stderr.log')}
    except Exception as exc:
        if proc: stop(proc); proc.wait(timeout=5)
        result={'job':manifest['job'],'attempt':manifest['attempt'],'sender':manifest['sender'],
                'process_outcome':'launch_or_supervisor_error','error_type':type(exc).__name__,
                'output_bytes_seen':seen_bytes,'output_bytes_captured':captured_bytes,
                'output_truncated':output_truncated.is_set(),
                'output_limit_action':'kill' if kill_on_output_limit else 'drain',
                'final_artifact':_final_artifact_proof(final_artifact_path, directory),
                'publication_preflight':publication_preflight,
                'worker_adapter':worker_adapter_receipt,
                'accepted':False,'worker_result_verified':False,'ownership_check_required':True}
    artifact=directory/'process-result.json'
    if 'post_return' in manifest:
        try:
            import post_return
            result['post_return'] = post_return.execute(manifest['post_return'], manifest, result,
                                                        db, state, directory)
        except Exception as exc:
            result['post_return'] = {'stage': 'exception', 'error_type': type(exc).__name__,
                                     'error': str(exc)[:500]}
    artifact_fd = os.open(artifact, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    with os.fdopen(artifact_fd, 'w') as stream:
        stream.write(json.dumps(result, indent=2) + '\n')
    _write_existing_regular(lease, {'runner_pid':os.getpid(),'state':'terminal','artifact':str(artifact),
                                    'timeout_seconds':timeout,'deadline_at':deadline_wall})
    event_id='exit-'+hashlib.sha256(json.dumps([manifest['job'],manifest['attempt']],separators=(',',':')).encode()).hexdigest()
    emit(db,manifest['job'],manifest['attempt'],manifest['sender'],'exited',artifact,event_id)
    delivery=notify(db,event_id)
    db.close()
    return {'result':result,'notification':delivery}


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',required=True);p.add_argument('--state',required=True);p.add_argument('--directory',required=True)
    a=p.parse_args()
    print(json.dumps(run(json.loads(Path(a.manifest).read_text()),a.state,a.directory),indent=2))

if __name__=='__main__':main()
