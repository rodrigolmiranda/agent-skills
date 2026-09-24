#!/usr/bin/env python3
"""One bounded retry for an explicitly authorized cancelled CI run; never a merge gate.

A supervisor supplies exact repo/PR/head/run and cancellation authorization. The
shared lane lock serializes cooperating retry callers; GitHub/external actors
remain outside it. Persist intent before the API call so uncertain delivery is
reconciled rather than automatically retried.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess


def gh(args):
    p = subprocess.run(['gh', *args], capture_output=True, text=True, check=True)
    return json.loads(p.stdout) if p.stdout.strip() else None


def retry(policy, state_dir, api=gh):
    required = ('repo', 'pr', 'head', 'run_id', 'reason')
    if any(not policy.get(k) for k in required) or policy.get('retry_authorized') is not True:
        raise ValueError('exact run and explicit cancellation retry authorization required')
    repo = policy['repo']
    if len(repo.split('/')) != 2 or any(not part or part in ('.', '..') for part in repo.split('/')):
        raise ValueError('invalid repository')
    import hashlib
    root = Path(state_dir)
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    key = hashlib.sha256(repo.encode()).hexdigest()
    with (root / (key + '.lock')).open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        record = root / (key + '-' + str(int(policy['run_id'])) + '.json')
        if record.exists():
            return {'state': 'reconcile', 'record': json.loads(record.read_text())}
        pr = api(['pr', 'view', str(int(policy['pr'])), '-R', repo, '--json', 'headRefOid,state'])
        if pr.get('state') != 'OPEN' or pr.get('headRefOid') != policy['head']:
            return {'state': 'superseded'}
        run = api(['api', f"repos/{repo}/actions/runs/{int(policy['run_id'])}"])
        if run.get('head_sha') != policy['head'] or run.get('status') != 'completed' or run.get('conclusion') != 'cancelled':
            return {'state': 'not-cancelled-current-run'}
        pages = api(['api', f'repos/{repo}/actions/runs?per_page=100', '--paginate', '--slurp'])
        if not isinstance(pages, list) or any(not isinstance(p, dict) or 'workflow_runs' not in p for p in pages):
            raise ValueError('cannot establish CI lane availability')
        runs = [r for p in pages for r in p['workflow_runs']]
        lane = policy.get('lane_workflow_ids')
        if lane is not None:
            if not isinstance(lane, list) or not lane or any(type(x) is not int or x <= 0 for x in lane):
                raise ValueError('lane_workflow_ids must name verified positive workflow IDs')
            if run.get('workflow_id') not in lane:
                raise ValueError('cancelled run is outside declared lane')
            runs = [r for r in runs if r.get('workflow_id') in lane]
        if any(r.get('status') != 'completed' for r in runs):
            return {'state': 'waiting-for-lane'}
        # Re-read the live head after lane enumeration. External pushes can still
        # race the API call; exact-head merge verification remains mandatory.
        current = api(['pr', 'view', str(int(policy['pr'])), '-R', repo, '--json', 'headRefOid,state'])
        if current.get('state') != 'OPEN' or current.get('headRefOid') != policy['head']:
            return {'state': 'superseded'}
        intent = {**policy, 'state': 'retry-request-uncertain'}
        fd = os.open(record, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, 'w') as f:
            json.dump(intent, f); f.flush(); os.fsync(f.fileno())
        api(['api', '--method', 'POST', f"repos/{repo}/actions/runs/{int(policy['run_id'])}/rerun"])
        intent['state'] = 'retry-requested'
        record.write_text(json.dumps(intent))
        return intent


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--policy', required=True)
    p.add_argument('--state-dir', required=True)
    args = p.parse_args()
    print(json.dumps(retry(json.loads(Path(args.policy).read_text()), args.state_dir)))


if __name__ == '__main__':
    main()
