#!/usr/bin/env python3
"""Watch CI check runs for PRs and emit one line per terminal fact; exit when every PR is done.

Designed as the command behind an event-stream monitor (one stdout line = one notification). It is
deliberately loud about the states a hand-rolled shell loop tends to hide:

- a fetch that returns nothing or fails is emitted as ``NO DATA`` rather than read as "pending";
- results are bound to the PR's *current head sha*, so a push that restarts CI resets the watch and
  a green result from an older head is never reported as the current one;
- every terminal conclusion is emitted (success, failure, cancelled, timed_out, ...), not only
  success;
- every PR is re-read on every poll, including finished ones, so a push to a PR that finished
  earlier while another was still running restarts its watch instead of being missed.

It reports a snapshot of the check runs registered for the head at that moment. That is not proof
that every required check (legacy statuses, late-registered workflows) passed, and it is not a merge
gate: re-query the live head and required checks before merging.

Exit status: 0 = every PR finished with all registered runs green; 1 = every PR finished and at
least one run failed; 2 = incomplete/cancelled or stopped before every PR finished (--max-polls).

Usage: watch_pr_checks.py owner/repo#123 [owner/repo#456 ...] [--interval 60] [--max-polls N]
"""
import argparse
import json
import subprocess
import sys
import time


def gh_json(args):
    """Run a gh command and return parsed JSON, or None with the error text."""
    proc = subprocess.run(['gh', *args], capture_output=True, text=True)
    if proc.returncode != 0:
        return None, (proc.stderr or proc.stdout or 'gh failed').strip()[:160]
    try:
        return json.loads(proc.stdout or 'null'), None
    except json.JSONDecodeError:
        return None, 'unparseable gh output'


def head_sha(repo, number, fetch=gh_json):
    data, error = fetch(['pr', 'view', str(number), '-R', repo, '--json', 'headRefOid'])
    if not data or not data.get('headRefOid'):
        return None, error or 'no head sha'
    return data['headRefOid'], None


def check_runs(repo, sha, fetch=gh_json):
    # --paginate emits one JSON object per page; --slurp wraps them in a single array.
    data, error = fetch(['api', f'repos/{repo}/commits/{sha}/check-runs', '--paginate', '--slurp'])
    pages = data if isinstance(data, list) else [data] if isinstance(data, dict) else None
    if pages is None:
        return None, error or 'no check runs'
    runs = [run for page in pages if isinstance(page, dict) for run in page.get('check_runs', [])]
    return [(run['name'], run['status'], run.get('conclusion')) for run in runs], None


def poll_once(target, state, fetch=gh_json, emit=print):
    """Advance one PR's watch; return True when it reached a terminal state for its current head."""
    repo, number = target.split('#', 1)
    sha, error = head_sha(repo, number, fetch)
    if sha is None:
        emit(f'{target} NO DATA ({error})')
        return False
    if state.get('sha') != sha:
        if state.get('sha'):
            emit(f'{target} head moved {state["sha"][:8]} -> {sha[:8]}; watching the new head')
        state.clear()
        state.update(sha=sha, seen=set())
    runs, error = check_runs(repo, sha, fetch)
    if not runs:
        emit(f'{target} {sha[:8]} NO DATA ({error or "no checks registered yet"})')
        return False
    for name, status, conclusion in runs:
        if status == 'completed' and (name, conclusion) not in state['seen']:
            state['seen'].add((name, conclusion))
            emit(f'{target} {sha[:8]} {name}: {conclusion}')
    if all(status == 'completed' for _, status, _ in runs):
        incomplete = [name for name, _, conclusion in runs if conclusion in ('cancelled', 'stale', None)]
        failed = [name for name, _, conclusion in runs if conclusion not in ('success', 'skipped', 'neutral', 'cancelled', 'stale', None)]
        state['incomplete'] = bool(incomplete)
        state['failed'] = bool(failed)
        if state.get('reported') != sha:
            state['reported'] = sha
            emit(f'{target} {sha[:8]} registered runs finished: ' +
                 ('FAILED ' + ', '.join(failed) if failed else 'INCOMPLETE ' + ', '.join(incomplete) if incomplete else 'all green'))
        return True
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('targets', nargs='+', help='owner/repo#number')
    parser.add_argument('--interval', type=float, default=60)
    parser.add_argument('--max-polls', type=int, default=0, help='0 = until every PR is done')
    args = parser.parse_args(argv)
    for target in args.targets:
        if '#' not in target or '/' not in target.split('#', 1)[0]:
            parser.error(f'{target} is not owner/repo#number')
    states = {target: {} for target in args.targets}
    polls = 0
    while True:
        # Every PR is re-read on every poll, including ones already finished: a new push to a
        # finished PR restarts its watch instead of being missed while another PR is still running.
        done = {target for target in args.targets if poll_once(target, states[target])}
        sys.stdout.flush()
        polls += 1
        if len(done) == len(args.targets):
            return 1 if any(state.get('failed') for state in states.values()) else 2 if any(state.get('incomplete') for state in states.values()) else 0
        if args.max_polls and polls >= args.max_polls:
            return 2
        time.sleep(args.interval)


if __name__ == '__main__':
    sys.exit(main())
