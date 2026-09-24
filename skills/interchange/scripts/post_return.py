"""Opt-in, fenced worker-return publication. No commit, merge, or acceptance authority.

This module is intentionally separate from the process runner. Its journal and the
remote PR query make stages restartable after a crash; a reviewer is a distinct
supervised run_job attempt, never a prompt appended to the coordinator turn.
"""
import fcntl
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
from urllib.parse import urlparse
import subprocess
import sys
import tempfile
import threading
import time

from relay import (acquire_managed_action, bind_attempt, register,
                   release_managed_action, require_current_generation)

BRANCH = re.compile(r'^(?!/)(?!.*\.\.)(?!.*//)[A-Za-z0-9][A-Za-z0-9._/-]{0,199}$')


class PipelineException(Exception):
    pass


def command(argv, cwd, timeout=30, input=None, env=None):
    result = subprocess.run(argv, cwd=cwd, input=input, capture_output=True, timeout=timeout, env=env)
    if result.returncode:
        raise PipelineException(f'{argv[0]} {argv[1]} failed (exit {result.returncode})')
    return result.stdout


GIT_OPTIONS = ['-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false',
               '-c', 'diff.external=', '-c', 'credential.helper=',
               '-c', 'protocol.ext.allow=never',
               '-c', 'core.sshCommand=ssh -o BatchMode=yes']


def _git_command(cwd, *args, timeout=30, credential_helper=None):
    environment = os.environ.copy()
    environment['GIT_CONFIG_GLOBAL'] = os.devnull
    environment['GIT_CONFIG_SYSTEM'] = os.devnull
    environment['GIT_EXTERNAL_DIFF'] = os.devnull
    environment['GIT_OPTIONAL_LOCKS'] = '0'
    environment['GIT_SSH_COMMAND'] = 'ssh -o BatchMode=yes'
    options = [*GIT_OPTIONS, '-c', f'safe.directory={cwd}']
    if credential_helper:
        options.extend(['-c', f'credential.helper=!{credential_helper} auth git-credential'])
    return command(['git', *options, *args], cwd, timeout=timeout, env=environment)


def git(cwd, *args):
    return _git_command(cwd, *args).decode().strip()


def _remote_git(spec, cwd, *args, timeout=30):
    helper = spec.get('gh_executable') if spec['remote_url'].startswith('https://') else None
    return _git_command(cwd, *args, timeout=timeout, credential_helper=helper).decode().strip()


def _verify_publication_url(spec):
    url = spec['remote_url']
    slug = spec['repository']
    host = spec.get('github_host', 'github.com')
    helper = spec.get('gh_executable')
    if not isinstance(helper, str) or not helper.startswith('/') or not re.fullmatch(r'[A-Za-z0-9/._-]+', helper):
        raise PipelineException('publication requires trusted absolute gh executable')
    path = Path(helper).resolve(strict=True)
    stat = path.stat()
    if not path.is_file() or stat.st_uid not in (0, os.geteuid()) or stat.st_mode & 0o022:
        raise PipelineException('gh executable is not supervisor-owned and non-writable by worker')
    if url.startswith('https://'):
        parsed = urlparse(url)
        if parsed.hostname != host or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise PipelineException('publication HTTPS URL does not match declared GitHub host')
        remote_slug = parsed.path.lstrip('/').removesuffix('.git')
    elif url.startswith('git@'):
        prefix = f'git@{host}:'
        if not url.startswith(prefix):
            raise PipelineException('publication SSH URL does not match declared GitHub host')
        remote_slug = url[len(prefix):].removesuffix('.git')
    elif url.startswith('ssh://'):
        parsed = urlparse(url)
        if parsed.hostname != host or parsed.username != 'git':
            raise PipelineException('publication SSH URL does not match declared GitHub host')
        remote_slug = parsed.path.lstrip('/').removesuffix('.git')
    else:
        raise PipelineException('unsupported publication URL scheme')
    if remote_slug != slug:
        raise PipelineException('publication URL repository differs from declared repository')


def _paths(cwd, *args):
    return [os.fsdecode(p) for p in _git_command(cwd, *args, '-z').split(b'\0') if p]


def _control_digest(cwd):
    git_entry = cwd / '.git'
    common = Path(git(cwd, 'rev-parse', '--git-common-dir')).resolve()
    parts = [str(common).encode(), git_entry.read_bytes() if git_entry.is_file() else b'.git-directory']
    for name in ('config', 'config.worktree'):
        path = Path(git(cwd, 'rev-parse', '--git-path', name))
        if not path.is_absolute():
            path = cwd / path
        parts.append(path.read_bytes() if path.exists() else b'')
    return hashlib.sha256(b'\0'.join(parts)).hexdigest()


def _reject_unsafe_git_config(cwd):
    result = subprocess.run(['git', *GIT_OPTIONS, '-c', f'safe.directory={cwd}',
                             'config', '--local', '--name-only', '--list'],
                            cwd=cwd, capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise PipelineException('cannot inspect local Git config')
    for key in result.stdout.lower().splitlines():
        if key.startswith(('url.', 'include.', 'includeif.', 'alias.', 'filter.',
                           'credential.', 'core.hookspath', 'core.fsmonitor',
                           'core.sshcommand', 'diff.')):
            raise PipelineException('unsafe worker-controlled Git config setting')
        if key.startswith('remote.') and key.endswith('.pushurl'):
            raise PipelineException('worker-controlled remote push URL')


def _permission_denial(output):
    denial = output.decode(errors='replace').lower()
    markers = ('permission denied', 'authentication failed', 'could not read username',
               'write access to repository not granted', 'denied to',
               'requested url returned error: 403', 'publickey')
    return any(marker in denial for marker in markers)


def _worker_credential_boundary(spec, manifest, environment, privilege_drop, cwd):
    """Reject known on-disk publication credentials and probe gh under the actual child UID.

    This does not claim to discover every possible secret. It binds the supported
    adapter to a dedicated, credential-free account and refuses ambiguous probes.
    """
    home = Path(manifest['execution_isolation']['home']).resolve(strict=True)
    forbidden = ('.config/gh', '.local/share/gh', '.config/hub',
                 '.git-credentials', '.gitconfig', '.config/git', '.netrc',
                 '.ssh', '.local/share/git-credential-manager',
                 '.config/git-credential-manager', 'Library/Application Support/gh')
    for relative in forbidden:
        path = home / relative
        if path.exists() or path.is_symlink():
            raise PipelineException('worker home contains a GitHub/Git/SSH credential path')
    probe_env = dict(environment)
    probe_env['GH_PROMPT_DISABLED'] = '1'
    probe_env['GIT_TERMINAL_PROMPT'] = '0'
    try:
        check = subprocess.run([spec['gh_executable'], 'auth', 'token',
                                '--hostname', spec.get('github_host', 'github.com')],
                               cwd=cwd, env=probe_env, preexec_fn=privilege_drop,
                               stdin=subprocess.DEVNULL, capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PipelineException('worker GitHub credential probe did not complete') from exc
    if check.returncode == 0:
        raise PipelineException('worker identity has GitHub CLI credentials')
    # gh auth token is a local credential lookup. Unknown errors or unsupported
    # CLI behavior are not evidence that the identity lacks a publication route.
    detail = check.stderr.decode(errors='replace').lower()
    if not any(marker in detail for marker in ('not logged in', 'not logged into',
                                               'no oauth token', 'no authentication')):
        raise PipelineException('worker GitHub credential probe inconclusive')


def _save(path, data):
    fd, temporary = tempfile.mkstemp(prefix=path.name + '.', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def _stage(journal, path, stage, **values):
    journal.update(stage=stage, updated_at=time.time(), **values)
    _save(path, journal)


def _fence(db, spec):
    require_current_generation(db, spec['project'], spec['generation'])


def _managed(db, spec, action, callback):
    token = acquire_managed_action(db, spec['project'], spec['generation'], action)
    try:
        return callback()
    finally:
        release_managed_action(db, token)


def _validate_spec(spec, manifest, cwd):
    if spec.get('version') != 1 or spec.get('kind') != 'implementation':
        raise PipelineException('post_return requires version 1 implementation contract')
    if not all(isinstance(spec.get(k), str) and spec[k] for k in
               ('project', 'packet_revision', 'start_head', 'branch', 'base', 'remote', 'remote_url', 'title')):
        raise PipelineException('incomplete declared publication contract')
    if not isinstance(spec.get('generation'), int) or spec['generation'] < 1:
        raise PipelineException('missing current ownership generation')
    if not isinstance(spec.get('allowed_paths'), list) or not spec['allowed_paths']:
        raise PipelineException('allowed_paths must declare owned change surface')
    if not all(isinstance(p, str) and p and not p.startswith('/') and '..' not in Path(p).parts
               for p in spec['allowed_paths']):
        raise PipelineException('invalid allowed path')
    for key in ('branch', 'base'):
        if not BRANCH.fullmatch(spec[key]):
            raise PipelineException(f'invalid {key}')
    if spec['branch'] == spec['base']:
        raise PipelineException('owned branch cannot be publication base')
    reviewer = spec.get('reviewer')
    if not isinstance(reviewer, dict) or reviewer.get('adapter') not in ('claude-headless', 'codex-headless'):
        raise PipelineException('unsupported independent reviewer adapter')
    argv = reviewer.get('argv')
    if not isinstance(argv, list) or not argv or not all(isinstance(x, str) for x in argv):
        raise PipelineException('reviewer argv must be literal strings')
    if reviewer['adapter'] == 'claude-headless':
        if Path(argv[0]).name != 'claude' or '--no-chrome' not in argv or '--disallowedTools' not in argv:
            raise PipelineException('Claude reviewer requires --no-chrome and --disallowedTools')
        if '--output-format' not in argv or argv[argv.index('--output-format') + 1:argv.index('--output-format') + 2] != ['stream-json']:
            raise PipelineException('Claude reviewer requires stream-json execution evidence')
        deny = argv[argv.index('--disallowedTools') + 1] if argv.index('--disallowedTools') + 1 < len(argv) else ''
        if not deny or ('chrome' not in deny.lower() and 'browser' not in deny.lower()):
            raise PipelineException('reviewer browser tool deny list missing')
    else:
        if (Path(argv[0]).name != 'codex' or 'exec' not in argv or '--sandbox' not in argv
                or argv[argv.index('--sandbox') + 1:argv.index('--sandbox') + 2] != ['read-only']):
            raise PipelineException('Codex reviewer requires headless exec in read-only sandbox')
        if '--json' not in argv:
            raise PipelineException('Codex reviewer requires JSON execution evidence')
        # Codex's read-only sandbox does not prove owner-browser/profile isolation by itself.
        # A distinct UID and private HOME are required by run_job for this route as well.
    isolation = reviewer.get('execution_isolation')
    if not isinstance(isolation, dict) or isolation.get('mode') != 'distinct_uid':
        raise PipelineException('reviewer requires distinct_uid owner-browser isolation')
    if isolation.get('uid') == manifest.get('execution_isolation', {}).get('uid'):
        raise PipelineException('reviewer must use a separate identity from the worker')
    if not (Path(argv[0]).is_file() or shutil.which(argv[0])):
        raise PipelineException('reviewer CLI unavailable on this host')
    if not isinstance(reviewer.get('timeout_seconds'), (int, float)) or not 0 < reviewer['timeout_seconds'] <= 10800:
        raise PipelineException('reviewer timeout missing or invalid')
    if not isinstance(spec.get('required_gates'), list) or not spec['required_gates']:
        raise PipelineException('required gates must be declared')
    if not all(isinstance(x, str) and x for x in spec['required_gates']):
        raise PipelineException('invalid required gate')
    if git(cwd, 'rev-parse', '--show-toplevel') != str(cwd):
        raise PipelineException('cwd must be the owned repository root')
    _reject_unsafe_git_config(cwd)


def preflight(spec, manifest, cwd, environment, privilege_drop):
    """Before the worker starts, prove this checkout and its identity cannot publish."""
    _validate_spec(spec, manifest, cwd)
    if git(cwd, 'rev-parse', 'HEAD') != spec['start_head']:
        raise PipelineException('start head differs from declared packet head')
    if git(cwd, 'branch', '--show-current') != spec['branch']:
        raise PipelineException('worker checkout is not the owned branch')
    if _paths(cwd, 'status', '--porcelain', '--untracked-files=all'):
        raise PipelineException('worker checkout must start clean')
    _verify_publication_url(spec)
    if privilege_drop is None:
        raise PipelineException('worker publication isolation not installed')
    _worker_credential_boundary(spec, manifest, environment, privilege_drop, cwd)
    probe_env = dict(environment)
    probe_env['GIT_TERMINAL_PROMPT'] = '0'
    probe_env['GIT_SSH_COMMAND'] = 'ssh -o BatchMode=yes -o IdentitiesOnly=yes'
    try:
        if not _remote_git(spec, cwd, 'ls-remote', '--heads', spec['remote_url'], spec['base']):
            raise PipelineException('supervisor cannot read authorized remote/base')
        probe_options = [*GIT_OPTIONS, '-c', f'safe.directory={cwd}']
        readable = subprocess.run(['git', *probe_options, 'ls-remote', '--heads', spec['remote_url'], spec['base']],
                                  cwd=cwd, env=probe_env, preexec_fn=privilege_drop,
                                  capture_output=True, timeout=30)
        denied = subprocess.run(['git', *probe_options, 'push', '--dry-run', spec['remote_url'],
                                 f"HEAD:refs/heads/{spec['branch']}"],
                                cwd=cwd, env=probe_env, preexec_fn=privilege_drop,
                                capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PipelineException('worker publication denial probe did not complete') from exc
    if denied.returncode == 0:
        raise PipelineException('worker can publish owned branch; isolation denied')
    if not _permission_denial(denied.stderr + denied.stdout):
        raise PipelineException('worker push probe failed for an unclassified reason; publication denial unproved')
    return {'remote_readable_by_supervisor': True,
            'remote_readable_by_worker': readable.returncode == 0 and bool(readable.stdout.strip()),
            'push_dry_run_denied': True,
            'git_control_digest': _control_digest(cwd)}


def _return_evidence(spec, result, cwd):
    if result.get('process_outcome') != 'exited' or result.get('exit_code') != 0:
        raise PipelineException('worker did not return normally; preserve worktree and inspect descendants')
    proof = result.get('final_artifact', {})
    if not proof.get('validated'):
        raise PipelineException('worker handover integrity missing')
    if (result.get('publication_preflight', {}).get('git_control_digest') != _control_digest(cwd)):
        raise PipelineException('worker changed Git control metadata; publication quarantined')
    try:
        handover = json.loads(Path(proof['path']).read_text())
    except (OSError, ValueError, KeyError) as exc:
        raise PipelineException('worker handover must be structured JSON') from exc
    if hashlib.sha256(Path(proof['path']).read_bytes()).hexdigest() != proof.get('sha256'):
        raise PipelineException('worker handover changed after integrity proof')
    if handover.get('job') != result['job'] or handover.get('attempt') != result['attempt'] or handover.get('packet_revision') != spec['packet_revision']:
        raise PipelineException('worker handover identity/revision mismatch')
    if handover.get('head') != git(cwd, 'rev-parse', 'HEAD'):
        raise PipelineException('worker handover head does not match actual head')
    if handover.get('result') != 'ready_for_review' or handover.get('question'):
        raise PipelineException('worker return is not a ready implementation')
    gates = handover.get('required_gates')
    if not isinstance(gates, dict) or any(gates.get(g) != 'passed' for g in spec['required_gates']):
        raise PipelineException('known required gate failure or missing gate proof; route correction')
    head = git(cwd, 'rev-parse', 'HEAD')
    if head == spec['start_head'] or git(cwd, 'rev-parse', spec['start_head']) != spec['start_head']:
        raise PipelineException('no committed implementation since declared start head')
    if git(cwd, 'merge-base', spec['start_head'], head) != spec['start_head']:
        raise PipelineException('worker head is not a descendant of declared start head')
    if git(cwd, 'branch', '--show-current') != spec['branch']:
        raise PipelineException('worker left owned branch')
    if _paths(cwd, 'status', '--porcelain', '--untracked-files=all'):
        raise PipelineException('dirty worker worktree; preserve uncommitted evidence')
    try:
        commits = git(cwd, 'rev-list', '--reverse', f"{spec['start_head']}..{head}").splitlines()
        if not commits:
            raise PipelineException('no commits in declared worker range')
        changed = []
        for commit in commits:
            parents = git(cwd, 'rev-list', '--parents', '-n', '1', commit).split()
            if len(parents) > 2:
                raise PipelineException('merge commit in worker range requires supervised integration')
            changed.extend(_paths(cwd, 'diff-tree', '--no-commit-id', '--name-only', '-r', commit))
    except PipelineException as exc:
        raise PipelineException('cannot prove complete committed change surface') from exc
    if not changed:
        raise PipelineException('no actual committed change')
    allowed = spec['allowed_paths']
    if any(not any(path == a or (a.endswith('/') and path.startswith(a)) for a in allowed) for path in changed):
        raise PipelineException('committed change outside owned paths')
    if git(cwd, 'remote', 'get-url', spec['remote']) != spec['remote_url']:
        raise PipelineException('publication remote changed')
    if not _remote_git(spec, cwd, 'ls-remote', '--heads', spec['remote_url'], spec['base']):
        raise PipelineException('authorized base missing on remote')
    return head, changed


def _existing_pr(spec, cwd):
    raw = command([spec.get('gh_executable', 'gh'), 'pr', 'list', '--repo', spec['repository'], '--state', 'open', '--head', spec['branch'],
                   '--json', 'number,url,headRefName,baseRefName,isDraft,headRefOid'], cwd)
    prs = json.loads(raw)
    if len(prs) > 1:
        raise PipelineException('multiple open PRs for owned branch')
    return prs[0] if prs else None


def _check_pr(pr, spec, head):
    if (pr.get('headRefName') != spec['branch'] or pr.get('baseRefName') != spec['base']
            or not pr.get('isDraft') or pr.get('headRefOid') != head):
        raise PipelineException('existing PR base/draft/head conflicts with declared publication')


def _reviewer_evidence(review_dir, reviewer, head):
    """A PID/queued request is insufficient; observe model activity or valid verdict."""
    stdout = review_dir / 'stdout.log'
    if stdout.exists():
        with stdout.open('rb') as stream:
            for raw in stream:
                if len(raw) > 100_000:
                    continue
                try:
                    event = json.loads(raw)
                except ValueError:
                    continue
                if reviewer['adapter'] == 'claude-headless':
                    if event.get('type') == 'assistant':
                        message = event.get('message') or {}
                        if message.get('model') and message.get('content'):
                            return True
                else:
                    if event.get('type') in ('item.started', 'item.completed'):
                        item = event.get('item') or {}
                        if item.get('type') in ('command_execution', 'agent_message', 'file_change'):
                            return True
    receipt = review_dir / 'process-result.json'
    final = review_dir / 'review.json'
    if receipt.exists() and final.exists():
        try:
            result = json.loads(receipt.read_text())
            verdict = json.loads(final.read_text())
            if (result.get('process_outcome') == 'exited' and result.get('exit_code') == 0
                    and result.get('final_artifact_validated')
                    and verdict.get('reviewed_head') == head
                    and verdict.get('verdict') in ('passed', 'changes_needed')):
                return True
        except (OSError, ValueError):
            pass
    return False


def _reviewer_identity(reviewer):
    argv = reviewer['argv']
    def after(flag):
        return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None
    requested_model = after('--model') or after('-m')
    requested_effort = after('--effort')
    if requested_effort is None:
        requested_effort = next((part.split('=', 1)[1] for part in argv
                                 if part.startswith('model_reasoning_effort=')), None)
    return {'requested_model': requested_model, 'requested_effort': requested_effort,
            'observed_model': None, 'observed_effort': None,
            'model_observation': 'unavailable'}


def _reviewer_stage(db, spec, head, cwd, directory, state, journal, journal_path):
    reviewer = spec['reviewer']
    reviewer_attempt = f"review-{head[:12]}"
    review_dir = directory / 'review' / head
    for path in (directory / 'review', review_dir):
        path.mkdir(mode=0o700, exist_ok=True)
        if path.is_symlink() or path.stat().st_uid != os.geteuid():
            raise PipelineException('review artifact directory is not supervisor-owned')
        os.chmod(path, 0o700)
    _fence(db, spec)
    register(db, spec['reviewer_job'], reviewer_attempt, spec['reviewer_sender'], review_dir,
             coordinator=reviewer.get('coordinator'), route=reviewer.get('route', 'manual'),
             receiver=reviewer.get('receiver'))
    bind_attempt(db, spec['project'], spec['reviewer_job'], reviewer_attempt, spec['generation'])
    launch = db.execute('SELECT directory FROM launches WHERE job=? AND attempt=?',
                        (spec['reviewer_job'], reviewer_attempt)).fetchone()
    if launch and _reviewer_evidence(review_dir, reviewer, head):
        _stage(journal, journal_path, 'review_started', reviewer_attempt=reviewer_attempt,
               reviewer_job=spec['reviewer_job'], reviewer_directory=str(review_dir),
               **_reviewer_identity(reviewer))
        return
    if launch:
        raise PipelineException('reviewer launch exists without model activity or valid verdict; inspect attempt')
    final_path = review_dir / 'review.json'
    argv = [x.replace('{head}', head).replace('{pr_url}', journal['pr_url'])
            .replace('{final_artifact}', str(final_path)) for x in reviewer['argv']]
    manifest = {'job': spec['reviewer_job'], 'attempt': reviewer_attempt,
                'sender': spec['reviewer_sender'], 'cwd': str(cwd), 'argv': argv,
                'timeout_seconds': reviewer['timeout_seconds'],
                'max_output_bytes': reviewer.get('max_output_bytes', 2_000_000),
                'final_artifact': str(final_path),
                'final_artifact_from_stdout': True,
                'execution_isolation': reviewer['execution_isolation'],
                'launch_generation': {'project': spec['project'], 'generation': spec['generation']}}
    manifest_path = review_dir / 'reviewer-manifest.json'
    _save(manifest_path, manifest)
    def launch():
        return subprocess.Popen([sys.executable, str(Path(__file__).with_name('run_job.py')),
                                 '--manifest', str(manifest_path), '--state', str(state),
                                 '--directory', str(review_dir)], cwd=cwd, stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
    _fence(db, spec)
    proc = launch()
    threading.Thread(target=proc.wait, daemon=True).start()
    deadline = time.monotonic() + reviewer.get('startup_seconds', 120)
    while time.monotonic() < deadline:
        launch = db.execute('SELECT 1 FROM launches WHERE job=? AND attempt=?',
                            (spec['reviewer_job'], reviewer_attempt)).fetchone()
        receipt = review_dir / 'runner.json'
        if launch and receipt.exists():
            status = json.loads(receipt.read_text())
            activity = _reviewer_evidence(review_dir, reviewer, head)
            if status.get('state') in ('running', 'terminal') and activity:
                _stage(journal, journal_path, 'review_started', reviewer_attempt=reviewer_attempt,
                       reviewer_job=spec['reviewer_job'], reviewer_directory=str(review_dir), reviewer_pid=proc.pid,
                       **_reviewer_identity(reviewer))
                return
        if proc.poll() is not None:
            raise PipelineException('reviewer launcher exited before verified startup')
        time.sleep(.2)
    raise PipelineException('reviewer startup not observed before deadline; inspect registered attempt')


def execute(spec, manifest, result, db, state, directory):
    """Execute declared stages once; call again with same return to resume a failed stage."""
    cwd = Path(manifest['cwd']).resolve(strict=True)
    directory = Path(directory).resolve()
    journal_path = directory / 'post-return.json'
    lock_path = directory / 'post-return.lock'
    lock_fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        journal = json.loads(journal_path.read_text()) if journal_path.exists() else {'stage': 'new'}
        try:
            _validate_spec(spec, manifest, cwd)
            for key in ('repository', 'reviewer_job', 'reviewer_sender'):
                if not isinstance(spec.get(key), str) or not spec[key]:
                    raise PipelineException(f'missing {key}')
            _fence(db, spec)
            head, paths = _return_evidence(spec, result, cwd)
            if journal.get('head') and journal['head'] != head:
                raise PipelineException('worker head changed after return; old review cannot apply')
            _stage(journal, journal_path, journal['stage'], head=head, changed_paths=paths,
                   project=spec['project'], job=result['job'], attempt=result['attempt'])
            if journal['stage'] == 'review_started':
                return journal
            _fence(db, spec)
            remote_head = _remote_git(spec, cwd, 'ls-remote', '--heads', spec['remote_url'], spec['branch']).split('\t')[0]
            if remote_head != head:
                # Force is deliberately unavailable: divergence requires supervision.
                _managed(db, spec, 'owned-branch-push',
                         lambda: _remote_git(spec, cwd, 'push', spec['remote_url'],
                                             f'{head}:refs/heads/{spec["branch"]}', timeout=120))
                if _remote_git(spec, cwd, 'ls-remote', '--heads', spec['remote_url'], spec['branch']).split('\t')[0] != head:
                    raise PipelineException('push returned without matching remote head')
            _stage(journal, journal_path, 'pushed')
            _fence(db, spec)
            pr = _existing_pr(spec, cwd)
            if not pr:
                body = (f"Packet revision: {spec['packet_revision']}\n"
                        f"Worker: {result['job']}/{result['attempt']}\n"
                        f"Head: {head}\n"
                        f"Handover SHA-256: {result['final_artifact']['sha256']}\n"
                        f"Known limitations: {spec.get('known_limitations', 'none reported')}\n")
                body_path = directory / 'draft-pr-body.md'
                _save(body_path, {'body': body})  # private exact evidence, not worker writable
                plain_path = directory / 'draft-pr-body.txt'
                plain_path.write_text(body)
                os.chmod(plain_path, 0o600)
                _managed(db, spec, 'draft-pr-create',
                         lambda: command([spec.get('gh_executable', 'gh'), 'pr', 'create', '--repo', spec['repository'], '--draft',
                                          '--base', spec['base'], '--head', spec['branch'],
                                          '--title', spec['title'], '--body-file', str(plain_path)], cwd, timeout=120))
                pr = _existing_pr(spec, cwd)
            if not pr:
                raise PipelineException('draft PR creation returned without visible PR')
            _check_pr(pr, spec, head)
            _stage(journal, journal_path, 'pr_created', pr_url=pr['url'], pr_number=pr['number'])
            _reviewer_stage(db, spec, head, cwd, directory, state, journal, journal_path)
            return journal
        except Exception as exc:
            _stage(journal, journal_path, 'exception', failed_stage=journal.get('stage'),
                   error_type=type(exc).__name__, error=str(exc)[:500])
            return journal
    finally:
        fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def main():
    parser = argparse.ArgumentParser(description='Resume only failed post-return stages; never rerun worker')
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--state', required=True)
    parser.add_argument('--directory', required=True)
    args = parser.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    if 'post_return' not in manifest:
        raise SystemExit('manifest has no declared post_return pipeline')
    receipt = json.loads((Path(args.directory) / 'process-result.json').read_text())
    if (receipt.get('job'), receipt.get('attempt')) != (manifest.get('job'), manifest.get('attempt')):
        raise SystemExit('process receipt does not match manifest attempt')
    from relay import connect
    db = connect(args.state)
    try:
        outcome = execute(manifest['post_return'], manifest, receipt, db, args.state, args.directory)
        print(json.dumps(outcome, indent=2))
        if outcome['stage'] == 'exception':
            raise SystemExit(2)
    finally:
        db.close()


if __name__ == '__main__':
    main()
