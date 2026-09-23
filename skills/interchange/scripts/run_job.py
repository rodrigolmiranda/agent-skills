#!/usr/bin/env python3
"""One bounded external process; durable logs + terminal event, no model polling."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sqlite3
import subprocess
import threading
import time

from relay import connect, emit, notify


def stop(proc):
    # Detached grandchildren may escape this group: abnormal exit requires ownership inspection.
    try:
        if os.name == 'posix': os.killpg(proc.pid, signal.SIGKILL)
        else: proc.kill()
    except (ProcessLookupError, PermissionError):
        if proc.poll() is None:
            proc.kill()


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
    exceeded = threading.Event()
    lock = threading.Lock()
    byte_count = 0
    logs = []
    try:
        proc = subprocess.Popen(argv,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                                start_new_session=True)
        lease.write_text(json.dumps({'runner_pid':os.getpid(),'worker_pid':proc.pid,'state':'running',
                                    'job':manifest['job'],'attempt':manifest['attempt']}))
        def drain(stream,path):
            nonlocal byte_count
            outfd = os.open(path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
            with os.fdopen(outfd,'wb') as out:
                while True:
                    block = stream.read(4096)
                    if not block: break
                    with lock:
                        available = max(0, limit-byte_count)
                        byte_count += len(block)
                    out.write(block[:available])
                    if byte_count > limit:
                        exceeded.set(); stop(proc)
            stream.close()
        for name,stream in [('stdout.log',proc.stdout),('stderr.log',proc.stderr)]:
            thread = threading.Thread(target=drain,args=(stream,directory/name),daemon=True)
            thread.start();logs.append(thread)
        try:
            exit_code = proc.wait(timeout=timeout)
            outcome = 'output_limit' if exceeded.is_set() else 'exited'
        except subprocess.TimeoutExpired:
            stop(proc); exit_code = proc.wait(timeout=5); outcome='timeout'
        for thread in logs: thread.join(timeout=2)
        if exceeded.is_set(): outcome='output_limit'
        if any(thread.is_alive() for thread in logs):
            # A descendant retains a pipe. Do not infer that the whole writer is gone.
            outcome='descendant_or_pipe_open'; stop(proc)
        result = {'job':manifest['job'],'attempt':manifest['attempt'],'sender':manifest['sender'],
                  'process_outcome':outcome,'exit_code':exit_code,'seconds':round(time.monotonic()-begun,3),
                  'output_bytes_seen':byte_count,'accepted':False,'worker_result_verified':False,
                  'ownership_check_required':outcome!='exited' or exit_code!=0,
                  'stdout':str(directory/'stdout.log'),'stderr':str(directory/'stderr.log')}
    except Exception as exc:
        if proc: stop(proc); proc.wait(timeout=5)
        result={'job':manifest['job'],'attempt':manifest['attempt'],'sender':manifest['sender'],
                'process_outcome':'launch_or_supervisor_error','error_type':type(exc).__name__,
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
