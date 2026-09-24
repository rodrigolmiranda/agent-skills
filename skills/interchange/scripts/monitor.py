#!/usr/bin/env python3
"""Separate local supervisor monitor. Findings are durable; no owner alert is assumed.

Run as its own supervised process. The relay SQLite path must be reachable from
this host; neither this file nor a local dashboard is a cross-machine wake route.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time

from relay import connect, notify, retry_failed_delivery


def _age(seconds, now_seconds):
    try:
        return now_seconds - float(seconds)
    except (TypeError, ValueError):
        return None


def _finding(key, kind, owner, detail, recovery, job=None, attempt=None):
    return {'id': key, 'kind': kind, 'severity': 'error', 'next_owner': owner,
            'message': detail, 'next_check': recovery,
            'notification_available': False, 'job': job, 'attempt': attempt}


def scan(db, *, project=None, activities=None, now_seconds=None, overdue_seconds=300, retry_delivery=False):
    """Reconcile all attempts/events; retry only definite failed sends with a bound."""
    now_seconds = time.time() if now_seconds is None else now_seconds
    if overdue_seconds <= 0:
        raise ValueError('overdue_seconds must be positive')
    if project is not None and project not in {r['project'] for r in db.execute('SELECT project FROM project_routes')}:
        raise ValueError('unknown project monitor scope')
    db.execute('''CREATE TABLE IF NOT EXISTS monitor_findings (
      key TEXT PRIMARY KEY, kind TEXT NOT NULL, next_owner TEXT NOT NULL,
      detail TEXT NOT NULL, next_check TEXT NOT NULL,
      first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, resolved TEXT)''')
    findings = []
    routes = {r['project']: dict(r) for r in db.execute('SELECT * FROM project_routes')}
    for event in db.execute('SELECT * FROM events WHERE acknowledged IS NULL ORDER BY created').fetchall():
        bound = db.execute('SELECT project FROM attempt_projects WHERE job=? AND attempt=?',
                           (event['job'], event['attempt'])).fetchone()
        event_project = bound['project'] if bound else None
        if project is not None and event_project != project:
            continue
        if event_project:
            route = routes.get(event_project)
            if not route:
                findings.append(_finding('event:'+event['id'], 'missing_route', 'supervisor',
                                         event['id'], 'restore a project route', event['job'], event['attempt']))
                continue
            delivery = db.execute('SELECT * FROM event_deliveries WHERE event_id=? AND generation=?',
                                  (event['id'], route['generation'])).fetchone()
            if retry_delivery and (not delivery or delivery['status'] == 'failed'):
                try:
                    if delivery:
                        retry_failed_delivery(db, event['id'])
                    else:
                        notify(db, event['id'])
                except (ValueError, OSError):
                    pass  # Finding below captures the unresolved condition.
                delivery = db.execute('SELECT * FROM event_deliveries WHERE event_id=? AND generation=?',
                                      (event['id'], route['generation'])).fetchone()
            status = delivery['status'] if delivery else 'not_sent'
            if status != 'queued' or _event_age(event['created'], now_seconds) >= overdue_seconds:
                findings.append(_finding('event:'+event['id'], 'undelivered_event',
                                         route['coordinator'] or route['receiver'] or 'supervisor',
                                         f"{event['id']} at generation {route['generation']}: {status}",
                                         'acknowledge receipt through supported current route; inspect fallback',
                                         event['job'], event['attempt']))
        elif event['delivery'] not in ('queued',):
            findings.append(_finding('event:'+event['id'], 'undelivered_event', 'supervisor',
                                     f"{event['id']}: {event['delivery']}",
                                     'inspect registered receiver and manual fallback', event['job'], event['attempt']))
    for action in db.execute('SELECT * FROM managed_actions').fetchall():
        if project is not None and action['project'] != project:
            continue
        if _event_age(action['check_after'], now_seconds) >= 0:
            findings.append(_finding('action:'+action['token'], 'overdue_managed_action',
                                     routes.get(action['project'], {}).get('coordinator') or 'supervisor',
                                     f"{action['project']} generation {action['generation']} {action['action']}",
                                     'inspect process and remote side effect before releasing action'))
    for notice in db.execute('''SELECT n.* FROM takeover_notices n
      JOIN project_routes r USING(project) WHERE n.generation=r.generation
      AND n.acknowledged IS NULL''').fetchall():
        if project is not None and notice['project'] != project:
            continue
        findings.append(_finding('notice:'+notice['project']+':'+notice['job']+':'+notice['attempt'],
                                 'takeover_notice_pending',
                                 routes.get(notice['project'], {}).get('coordinator') or 'supervisor',
                                 f"{notice['job']}/{notice['attempt']}: {notice['status']}",
                                 'deliver on next supported worker interaction and retain forwarding',
                                 notice['job'], notice['attempt']))
    for launch in db.execute('SELECT * FROM launches').fetchall():
        if project is not None:
            bound = db.execute('SELECT project FROM attempt_projects WHERE job=? AND attempt=?',
                               (launch['job'], launch['attempt'])).fetchone()
            if not bound or bound['project'] != project:
                continue
        age = _age(launch['started'], now_seconds)
        if age is None:
            findings.append(_finding('launch:'+launch['job']+':'+launch['attempt'], 'invalid_launch_time',
                                     'supervisor', 'launch age unavailable', 'inspect attempt record',
                                     launch['job'], launch['attempt']))
            continue
        if age < overdue_seconds:
            continue
        terminal = db.execute("SELECT 1 FROM events WHERE job=? AND attempt=? AND kind IN ('result','failed','exited') LIMIT 1",
                              (launch['job'], launch['attempt'])).fetchone()
        directory = Path(launch['directory'])
        runner = _runner_state(directory / 'runner.json')
        declared_deadline = runner.get('deadline_at')
        try:
            deadline_passed = declared_deadline is not None and now_seconds >= float(declared_deadline) + overdue_seconds
        except (TypeError, ValueError):
            deadline_passed = False
        returned_without_event = (directory / 'process-result.json').is_file() or runner.get('state') == 'terminal'
        # A live worker inside its declared deadline is work, not a missing
        # return. An absent/corrupt runner after the grace period is orphaned.
        absent_runner = not runner
        if not terminal and (returned_without_event or deadline_passed or absent_runner):
            findings.append(_finding('launch:'+launch['job']+':'+launch['attempt'], 'missing_terminal_return',
                                     'supervisor', f"{launch['job']}/{launch['attempt']}",
                                     'inspect owned process, descendants, logs and worktree',
                                     launch['job'], launch['attempt']))
        elif not terminal and declared_deadline is None:
            findings.append(_finding('deadline:'+launch['job']+':'+launch['attempt'],
                                     'missing_launch_deadline', 'supervisor',
                                     f"{launch['job']}/{launch['attempt']}",
                                     'inspect running attempt and restore a declared deadline',
                                     launch['job'], launch['attempt']))
        journal = directory / 'post-return.json'
        if journal.is_file():
            try:
                journal_data = json.loads(journal.read_text())
                stage = journal_data.get('stage')
            except (OSError, ValueError, TypeError):
                stage = 'unreadable'
                journal_data = {}
            old_stage = now_seconds - journal.stat().st_mtime >= overdue_seconds
            if stage == 'review_started' and journal_data.get('reviewer_attempt'):
                reviewer_job = journal_data.get('reviewer_job')
                observed = db.execute('SELECT 1 FROM launches WHERE job=? AND attempt=? LIMIT 1',
                                      (reviewer_job, journal_data['reviewer_attempt'])).fetchone() if reviewer_job else None
                if not reviewer_job or not observed:
                    findings.append(_finding('pipeline:'+launch['job']+':'+launch['attempt'],
                                             'missing_reviewer_identity' if not reviewer_job else 'missing_reviewer_execution',
                                             'supervisor',
                                             f"{launch['job']}/{launch['attempt']}",
                                             'inspect reviewer launch and retry only reviewer stage',
                                             launch['job'], launch['attempt']))
            elif stage == 'exception' or (old_stage and stage not in ('review_started', 'done')):
                findings.append(_finding('pipeline:'+launch['job']+':'+launch['attempt'],
                                         'stalled_pipeline', 'supervisor',
                                         f"{launch['job']}/{launch['attempt']}: {stage}",
                                         'resume only the failed authorized stage after reconciliation',
                                         launch['job'], launch['attempt']))
    if activities is not None:
        findings.extend(_activity_findings(activities, project, now_seconds))
    stamp = datetime.fromtimestamp(now_seconds, timezone.utc).isoformat()
    with db:
        for item in findings:
            db.execute('''INSERT INTO monitor_findings VALUES (?,?,?,?,?,?,?,NULL)
              ON CONFLICT(key) DO UPDATE SET kind=excluded.kind,next_owner=excluded.next_owner,
              detail=excluded.detail,next_check=excluded.next_check,last_seen=excluded.last_seen,resolved=NULL''',
                       (item['id'], item['kind'], item['next_owner'], item['message'],
                        item['next_check'], stamp, stamp))
        # A scoped scan must never resolve findings for other projects.
        if project is None:
            keys = [item['id'] for item in findings]
            if keys:
                marks = ','.join('?' for _ in keys)
                db.execute(f'UPDATE monitor_findings SET resolved=? WHERE resolved IS NULL AND key NOT IN ({marks})',
                           (stamp, *keys))
            else:
                db.execute('UPDATE monitor_findings SET resolved=? WHERE resolved IS NULL', (stamp,))
    return findings


def _activity_findings(record, project, now_seconds):
    """Check an explicitly supplied full-scope activity ledger, never a top-N board slice."""
    if not isinstance(record, dict) or record.get('project_id') != project:
        raise ValueError('activity ledger project mismatch')
    steps = record.get('workflow_steps')
    if not isinstance(steps, list):
        raise ValueError('activity ledger requires workflow_steps array')
    findings = []
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get('id'), str):
            raise ValueError('activity ledger step requires id')
        ident = step['id']
        if len(ident) > 100 or not ident or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-' for c in ident):
            raise ValueError('invalid activity id')
        state = str(step.get('state', '')).lower()
        if state in ('done', 'cancelled'):
            continue
        owner = step.get('next_owner') or step.get('owner')
        expected = step.get('expected_transition')
        deadline = step.get('deadline_at')
        if not all(isinstance(value, str) and value.strip() for value in (owner, expected, deadline)):
            findings.append(_finding('activity:'+ident, 'incomplete_supervision', 'supervisor',
                                     ident, 'supply owner, expected transition and deadline'))
            continue
        if _event_age(deadline, now_seconds) < 0:
            continue
        if state in ('next', 'ready') and not step.get('executor_started_at'):
            code = 'ready_without_executor'
        elif state == 'review' and not step.get('executor_started_at'):
            code = 'review_without_executor'
        elif state == 'review' and step.get('verdict_at') and not step.get('disposition_at'):
            code = 'verdict_without_disposition'
        elif not step.get('observed_at') or _event_age(step.get('observed_at'), now_seconds) >= _event_age(deadline, now_seconds):
            code = 'stale_activity_observation'
        else:
            continue
        findings.append(_finding('activity:'+ident, code, owner, ident,
                                 'reconcile current execution and record next transition'))
    return findings


def write_snapshot(path, findings, project_id, now_seconds=None):
    """Publish a factual monitor projection for read-only dashboards."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    updated = datetime.fromtimestamp(now_seconds if now_seconds is not None else time.time(), timezone.utc).isoformat()
    alerts = [{'id': item['kind'] + ':' + hashlib.sha256(item['id'].encode()).hexdigest()[:16],
               'type': item['kind'], 'code': item['kind'],
               'severity': item['severity'], 'job': item['job'], 'attempt': item['attempt'],
               'next_owner': item['next_owner'], 'observed_at': updated}
              for item in findings]
    payload = {'project_id': project_id, 'updated_at': updated,
               'notification_available': False, 'alerts': alerts}
    fd, name = tempfile.mkstemp(prefix='.monitor-', suffix='.json', dir=path.parent)
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w') as stream:
            json.dump(payload, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)
    return payload


def _event_age(value, now_seconds):
    try:
        return now_seconds - datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
    except (AttributeError, TypeError, ValueError):
        return float('inf')


def _runner_state(path):
    try:
        state = json.loads(path.read_text())
        return state if isinstance(state, dict) else {}
    except (OSError, ValueError):
        return {}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True)
    parser.add_argument('--interval', type=float, default=0,
                        help='seconds; 0 performs one scan; supervise periodic runs externally')
    parser.add_argument('--overdue-seconds', type=float, default=300)
    parser.add_argument('--retry-delivery', action='store_true')
    parser.add_argument('--output', help='atomic monitor.json projection for a read-only board')
    parser.add_argument('--project', help='required with --output; filter one project board')
    parser.add_argument('--activities', help='full project activity ledger JSON with workflow_steps')
    args = parser.parse_args()
    if args.output and not args.project:
        parser.error('--output requires --project so the board contains only its own alerts')
    if args.activities and not args.project:
        parser.error('--activities requires --project')
    db = connect(args.state)
    try:
        while True:
            activities = json.loads(Path(args.activities).read_text()) if args.activities else None
            findings = scan(db, project=args.project, overdue_seconds=args.overdue_seconds,
                            retry_delivery=args.retry_delivery, activities=activities)
            payload = write_snapshot(args.output, findings, args.project) if args.output else {
                'project_id': args.project,
                'updated_at': datetime.now(timezone.utc).isoformat(),
                'notification_available': False, 'alerts': findings}
            print(json.dumps(payload, indent=2), flush=True)
            if args.interval <= 0:
                break
            time.sleep(args.interval)
    finally:
        db.close()


if __name__ == '__main__':
    main()
