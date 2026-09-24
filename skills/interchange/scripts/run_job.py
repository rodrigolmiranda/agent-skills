#!/usr/bin/env python3
"""One bounded external process; durable logs + terminal event, no model polling."""
import argparse
import hashlib
import json
import os
import re
import shutil
from pathlib import Path
import signal
import sqlite3
import subprocess
import threading
import time

from relay import connect, emit, notify

SUPERVISOR_ARTIFACTS = frozenset({'process-result.json', 'runner.json', 'stdout.log', 'stderr.log'})


def stop(proc):
    # Detached grandchildren may escape this group: abnormal exit requires ownership inspection.
    try:
        if os.name == 'posix': os.killpg(proc.pid, signal.SIGKILL)
        else: proc.kill()
    except (ProcessLookupError, PermissionError):
        if proc.poll() is None:
            proc.kill()


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
    return path


def _collect_final_artifact(source, target, cwd):
    """Copy the worker's in-cwd final into the attempt root; never follow it outside cwd."""
    if source is None or target is None:
        return
    try:
        resolved = source.resolve()
        if not resolved.is_relative_to(cwd) or not resolved.is_file() or resolved.stat().st_size > 1_000_000:
            return
        shutil.copyfile(resolved, target)
        os.chmod(target, 0o600)
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
    kill_on_output_limit = _output_limit_kill(manifest)
    extra_env = _manifest_env(manifest)
    final_source = _final_artifact_source(manifest, cwd)
    if final_source is not None and manifest.get('final_artifact') is None:
        manifest = {**manifest, 'final_artifact': 'final.md'}
    final_artifact_path = _final_artifact_path(manifest, directory)
    db = connect(state)
    row = db.execute('SELECT * FROM attempts WHERE job=? AND attempt=?',
                     (manifest['job'],manifest['attempt'])).fetchone()
    if not row or row['sender'] != manifest['sender'] or not directory.is_relative_to(Path(row['root'])):
        db.close(); raise ValueError('register matching attempt and artifact root first')
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
    proc = None
    output_truncated = threading.Event()
    output_limit_kill_requested = threading.Event()
    lock = threading.Lock()
    seen_bytes = 0
    captured_bytes = 0
    logs = []
    try:
        environment = os.environ.copy()
        environment.update(extra_env)
        if final_artifact_path is not None:
            environment['INTERCHANGE_FINAL_ARTIFACT'] = str(final_artifact_path)
        # stdin is always closed: an inherited open, non-TTY stdin makes some headless workers
        # (OpenCode) wait forever and print nothing.
        proc = subprocess.Popen(argv,cwd=cwd,env=environment,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE,start_new_session=True)
        lease.write_text(json.dumps({'runner_pid':os.getpid(),'worker_pid':proc.pid,'state':'running',
                                    'job':manifest['job'],'attempt':manifest['attempt']}))
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
        _collect_final_artifact(final_source, final_artifact_path, cwd)
        final_proof = _final_artifact_proof(final_artifact_path, directory)
        result = {'job':manifest['job'],'attempt':manifest['attempt'],'sender':manifest['sender'],
                  'process_outcome':outcome,'exit_code':exit_code,'seconds':round(time.monotonic()-begun,3),
                  'output_bytes_seen':seen_bytes,'output_bytes_captured':captured_bytes,
                  'output_truncated':output_truncated.is_set(),
                  'output_limit_action':'kill' if kill_on_output_limit else 'drain',
                  'final_artifact':final_proof,
                  'final_artifact_validated':final_proof['validated'],
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
                'accepted':False,'worker_result_verified':False,'ownership_check_required':True}
    artifact=directory/'process-result.json'
    artifact.write_text(json.dumps(result,indent=2)+'\n');os.chmod(artifact,0o600)
    lease.write_text(json.dumps({'runner_pid':os.getpid(),'state':'terminal','artifact':str(artifact)}))
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
