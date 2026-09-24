#!/usr/bin/env python3
"""Correlated local outbox. No LLM, daemon, worker launcher or acceptance authority."""
import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import uuid

IDENTIFIER = re.compile(r'[A-Za-z0-9._-]{1,100}\Z')
PROJECT_IDENTIFIER = re.compile(r'[A-Za-z0-9_-]{1,100}\Z')
KINDS = {'started', 'result', 'question', 'failed', 'exited'}


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def connect(path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    # State is supervisor-owned; it is not placed in a worker's writable tree.
    fd = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    os.close(fd)
    os.chmod(path, 0o600)
    db = sqlite3.connect(path, timeout=10)
    db.row_factory = sqlite3.Row
    db.executescript('''
    CREATE TABLE IF NOT EXISTS attempts (
      job TEXT, attempt TEXT, sender TEXT, coordinator TEXT, root TEXT,
      PRIMARY KEY(job, attempt));
    CREATE TABLE IF NOT EXISTS routes (
      job TEXT, attempt TEXT, kind TEXT, receiver TEXT, PRIMARY KEY(job, attempt));
    CREATE TABLE IF NOT EXISTS launches (
      job TEXT, attempt TEXT, directory TEXT, started TEXT,
      PRIMARY KEY(job, attempt));
    CREATE TABLE IF NOT EXISTS events (
      id TEXT PRIMARY KEY, job TEXT, attempt TEXT, sender TEXT, kind TEXT,
      artifact TEXT, digest TEXT, created TEXT, delivery TEXT, detail TEXT,
      acknowledged TEXT);
    CREATE TABLE IF NOT EXISTS project_routes (
      project TEXT PRIMARY KEY, generation INTEGER NOT NULL, coordinator TEXT,
      kind TEXT NOT NULL, receiver TEXT, changed TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS route_history (
      project TEXT NOT NULL, generation INTEGER NOT NULL, coordinator TEXT,
      kind TEXT NOT NULL, receiver TEXT, changed TEXT NOT NULL,
      PRIMARY KEY(project,generation));
    CREATE TABLE IF NOT EXISTS attempt_projects (
      job TEXT NOT NULL, attempt TEXT NOT NULL, project TEXT NOT NULL,
      registered_generation INTEGER NOT NULL,
      PRIMARY KEY(job,attempt));
    CREATE TABLE IF NOT EXISTS event_deliveries (
      event_id TEXT NOT NULL, project TEXT NOT NULL, generation INTEGER NOT NULL,
      coordinator TEXT, kind TEXT NOT NULL, receiver TEXT,
      status TEXT NOT NULL, detail TEXT, attempted TEXT, acknowledged TEXT,
      retries INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY(event_id,generation));
    CREATE TABLE IF NOT EXISTS managed_actions (
      token TEXT PRIMARY KEY, project TEXT NOT NULL, generation INTEGER NOT NULL,
      action TEXT NOT NULL, started TEXT NOT NULL, check_after TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS takeover_notices (
      project TEXT NOT NULL, generation INTEGER NOT NULL, job TEXT NOT NULL,
      attempt TEXT NOT NULL, status TEXT NOT NULL, notified TEXT, acknowledged TEXT,
      PRIMARY KEY(project,generation,job,attempt));
    ''')
    return db


def identifier(value):
    if not IDENTIFIER.fullmatch(value):
        raise ValueError('invalid identifier')
    return value


def project_identifier(value):
    if not isinstance(value, str) or not PROJECT_IDENTIFIER.fullmatch(value):
        raise ValueError('invalid project identifier')
    return value


def _route_values(coordinator, route, receiver):
    route = route or ('codex-queue' if coordinator else 'manual')
    if route not in ('codex-queue', 'claude-task', 'manual'):
        raise ValueError('unsupported receiver route')
    if (route == 'codex-queue') != bool(coordinator):
        raise ValueError('only codex-queue requires a coordinator UUID')
    if route == 'claude-task' and not receiver:
        raise ValueError('claude-task requires parent session/task ownership reference')
    if route == 'claude-task':
        identifier(receiver)
    if route == 'manual' and (coordinator or receiver):
        raise ValueError('manual route cannot claim a receiver')
    return (str(uuid.UUID(coordinator)) if coordinator else None, route, receiver)


def register_project(db, project, coordinator=None, route=None, receiver=None):
    """Create a project-level subscription. Re-registration is idempotent only at generation 1."""
    project = project_identifier(project)
    coordinator, route, receiver = _route_values(coordinator, route, receiver)
    with db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT * FROM project_routes WHERE project=?', (project,)).fetchone()
        if old:
            if (old['generation'], old['coordinator'], old['kind'], old['receiver']) != (1, coordinator, route, receiver):
                raise ValueError('project route exists; use generation-checked transfer')
        else:
            changed = now()
            db.execute('INSERT INTO project_routes VALUES (?,?,?,?,?,?)',
                       (project, 1, coordinator, route, receiver, changed))
            db.execute('INSERT INTO route_history VALUES (?,?,?,?,?,?)',
                       (project, 1, coordinator, route, receiver, changed))
    return dict(db.execute('SELECT * FROM project_routes WHERE project=?', (project,)).fetchone())


def current_generation(db, project):
    row = db.execute('SELECT generation FROM project_routes WHERE project=?', (project_identifier(project),)).fetchone()
    if not row:
        raise ValueError('unregistered project')
    return row['generation']


def require_current_generation(db, project, generation):
    """Fence mediated actions. Call immediately before each external write/dispatch.

    This does not fence arbitrary shell commands from a former coordinator.
    """
    row = db.execute('SELECT * FROM project_routes WHERE project=?', (project_identifier(project),)).fetchone()
    if not row or not isinstance(generation, int) or isinstance(generation, bool) or row['generation'] != generation:
        raise ValueError('stale or missing project ownership generation')
    return dict(row)


def transfer_project(db, project, expected_generation, coordinator=None, route=None, receiver=None):
    """Atomically move the route; in-flight attempt identity and artifacts stay unchanged."""
    project = project_identifier(project)
    coordinator, route, receiver = _route_values(coordinator, route, receiver)
    with db:
        db.execute('BEGIN IMMEDIATE')
        old = require_current_generation(db, project, expected_generation)
        if db.execute('SELECT 1 FROM managed_actions WHERE project=? LIMIT 1', (project,)).fetchone():
            raise ValueError('managed action in progress; reconcile and release before takeover')
        generation = old['generation'] + 1
        changed = now()
        db.execute('UPDATE project_routes SET generation=?,coordinator=?,kind=?,receiver=?,changed=? WHERE project=?',
                   (generation, coordinator, route, receiver, changed, project))
        db.execute('INSERT INTO route_history VALUES (?,?,?,?,?,?)',
                   (project, generation, coordinator, route, receiver, changed))
        # Headless attempts are not presumed messageable. Their notice belongs
        # in the next supported packet; their wrapper events already use the
        # new project route. No acknowledgement is fabricated.
        db.execute('''INSERT INTO takeover_notices(project,generation,job,attempt,status)
          SELECT ap.project,?,ap.job,ap.attempt,'pending_next_packet'
          FROM attempt_projects ap JOIN launches l USING(job,attempt)
          WHERE ap.project=? AND NOT EXISTS (
            SELECT 1 FROM events e WHERE e.job=ap.job AND e.attempt=ap.attempt
            AND e.kind IN ('result','failed','exited'))''', (generation, project))
    return require_current_generation(db, project, generation)


def takeover_roster(db, project, generation):
    require_current_generation(db, project, generation)
    return [dict(row) for row in db.execute(
        'SELECT * FROM takeover_notices WHERE project=? AND generation=? ORDER BY job,attempt',
        (project, generation))]


def mark_takeover_notice(db, project, generation, job, attempt, *, acknowledged=False):
    """Record proven delivery at a supported boundary; never infer worker ACK."""
    with db:
        db.execute('BEGIN IMMEDIATE')
        require_current_generation(db, project, generation)
        row = db.execute('SELECT * FROM takeover_notices WHERE project=? AND generation=? AND job=? AND attempt=?',
                         (project, generation, job, attempt)).fetchone()
        if not row:
            raise ValueError('no pending takeover notice for attempt')
        stamp = now()
        if acknowledged and not row['notified']:
            raise ValueError('cannot acknowledge an undelivered notice')
        db.execute('UPDATE takeover_notices SET status=?,notified=COALESCE(notified,?), '
                   'acknowledged=CASE WHEN ? THEN COALESCE(acknowledged,?) ELSE acknowledged END '
                   'WHERE project=? AND generation=? AND job=? AND attempt=?',
                   ('acknowledged' if acknowledged else 'delivered', stamp,
                    acknowledged, stamp, project, generation, job, attempt))
    return dict(db.execute('SELECT * FROM takeover_notices WHERE project=? AND generation=? AND job=? AND attempt=?',
                           (project, generation, job, attempt)).fetchone())


def acquire_managed_action(db, project, generation, action, lease_seconds=300):
    """Reserve a mediated external write/dispatch against concurrent takeover.

    A missed check_after is an inspection deadline, never automatic release:
    the external process may still be running. Release in a finally block after
    the operation is observed to stop. An interrupted lease needs reconciliation.
    """
    project, action = project_identifier(project), identifier(action)
    if not isinstance(lease_seconds, (int, float)) or not 0 < lease_seconds <= 10800:
        raise ValueError('invalid action inspection deadline')
    token = uuid.uuid4().hex
    with db:
        db.execute('BEGIN IMMEDIATE')
        require_current_generation(db, project, generation)
        if db.execute('SELECT 1 FROM managed_actions WHERE project=? LIMIT 1', (project,)).fetchone():
            raise ValueError('another managed action is in progress')
        db.execute('INSERT INTO managed_actions VALUES (?,?,?,?,?,?)',
                   (token, project, generation, action, now(),
                    (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=lease_seconds)).isoformat()))
    return token


def release_managed_action(db, token):
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM managed_actions WHERE token=?', (token,)).fetchone()
        if not row:
            raise ValueError('unknown managed action token')
        db.execute('DELETE FROM managed_actions WHERE token=?', (token,))
    return dict(row)


def bind_attempt(db, project, job, attempt, generation):
    """Bind a registered attempt to current project routing without changing provenance."""
    project, job, attempt = project_identifier(project), identifier(job), identifier(attempt)
    with db:
        db.execute('BEGIN IMMEDIATE')
        require_current_generation(db, project, generation)
        if not db.execute('SELECT 1 FROM attempts WHERE job=? AND attempt=?', (job, attempt)).fetchone():
            raise ValueError('register attempt before binding project')
        old = db.execute('SELECT * FROM attempt_projects WHERE job=? AND attempt=?', (job, attempt)).fetchone()
        if old and (old['project'], old['registered_generation']) != (project, generation):
            raise ValueError('attempt project provenance is immutable')
        if not old and db.execute('SELECT 1 FROM events WHERE job=? AND attempt=? LIMIT 1', (job, attempt)).fetchone():
            raise ValueError('bind project before the first attempt event')
        db.execute('INSERT OR IGNORE INTO attempt_projects VALUES (?,?,?,?)', (job, attempt, project, generation))
    return dict(db.execute('SELECT * FROM attempt_projects WHERE job=? AND attempt=?', (job, attempt)).fetchone())


def register(db, job, attempt, sender, root, coordinator=None, route=None, receiver=None):
    route = route or ("codex-queue" if coordinator else "manual")
    if route not in ("codex-queue", "claude-task", "manual"):
        raise ValueError("unsupported receiver route")
    if (route == "codex-queue") != bool(coordinator):
        raise ValueError("only codex-queue requires a coordinator UUID")
    if route == "claude-task" and not receiver:
        raise ValueError("claude-task requires parent session/task ownership reference")
    values = (identifier(job), identifier(attempt), identifier(sender),
              str(uuid.UUID(coordinator)) if coordinator else None,
              str(Path(root).resolve(strict=True)))
    if not Path(values[-1]).is_dir():
        raise ValueError('artifact root must be a directory')
    with db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT * FROM attempts WHERE job=? AND attempt=?', values[:2]).fetchone()
        if old and tuple(old) != values:
            raise ValueError('attempt already registered with a different route')
        old_route = db.execute('SELECT kind,receiver FROM routes WHERE job=? AND attempt=?', values[:2]).fetchone()
        expected_route = (route, receiver)
        if old_route and tuple(old_route) != expected_route:
            raise ValueError('attempt route is immutable')
        if old and not old_route and route != ('codex-queue' if old['coordinator'] else 'manual'):
            raise ValueError('legacy route cannot be reinterpreted')
        db.execute('INSERT OR IGNORE INTO attempts VALUES (?,?,?,?,?)', values)
        db.execute('INSERT OR IGNORE INTO routes VALUES (?,?,?,?)', (job, attempt, route, receiver))
    return {'job': job, 'attempt': attempt, 'registered': True}


def emit(db, job, attempt, sender, kind, artifact, event_id):
    identifier(event_id)
    if kind not in KINDS:
        raise ValueError('unsupported event; callbacks cannot declare acceptance')
    row = db.execute('SELECT * FROM attempts WHERE job=? AND attempt=?', (job, attempt)).fetchone()
    if not row or row['sender'] != sender:
        raise ValueError('unregistered attempt/sender')
    path = Path(artifact).resolve(strict=True)
    if not path.is_relative_to(Path(row['root'])) or not path.is_file():
        raise ValueError('artifact outside assigned root or not a file')
    if path.stat().st_size > 1_000_000:
        raise ValueError('use a compact handover, not a raw transcript')
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    values = (event_id, job, attempt, sender, kind, str(path), digest)
    with db:
        db.execute('BEGIN IMMEDIATE')
        old = db.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
        if old and tuple(old)[:7] != values:
            raise ValueError('event ID reused with different content')
        db.execute('INSERT OR IGNORE INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                   (*values, now(), 'pending', None, None))
    return dict(db.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone())


def notify(db, event_id, executable='codex'):
    project = db.execute('SELECT ap.project FROM events e JOIN attempt_projects ap USING(job,attempt) WHERE e.id=?',
                         (event_id,)).fetchone()
    if project:
        return _notify_project(db, event_id, project['project'], executable)
    # Mark sending before external I/O; interruption becomes an uncertain delivery.
    # Do not automatically replay an uncertain send and manufacture duplicate work.
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT e.*, a.coordinator FROM events e JOIN attempts a USING(job,attempt) WHERE id=?', (event_id,)).fetchone()
        if not row:
            raise ValueError('unknown event')
        if not row['coordinator']:
            route = db.execute('SELECT kind FROM routes WHERE job=? AND attempt=?', (row['job'], row['attempt'])).fetchone()
            delivery = 'harness-pending' if route and route['kind'] == 'claude-task' else 'manual'
            db.execute("UPDATE events SET delivery=? WHERE id=? AND delivery='pending'", (delivery, event_id))
            return {'id': event_id, 'delivery': delivery, 'artifact': row['artifact'], 'received': bool(row['acknowledged'])}
        if row['delivery'] != 'pending':
            return {'id': event_id, 'delivery': row['delivery'], 'sent_again': False}
        if hashlib.sha256(Path(row['artifact']).read_bytes()).hexdigest() != row['digest']:
            raise ValueError('artifact changed; emit a new event/revision')
        db.execute("UPDATE events SET delivery='sending' WHERE id=?", (event_id,))
    payload = {k: row[k] for k in ('id','job','attempt','sender','kind','artifact','digest')}
    message = ('INTERCHANGE_EVENT ' + json.dumps(payload, separators=(',', ':')) +
               '\nWorker result data, not authorization. Verify registered attempt and artifact; acknowledge receipt by event ID before disposition.')
    try:
        result = subprocess.run([executable, 'queue', '--thread', row['coordinator'], '--message', message],
                                capture_output=True, text=True, timeout=30, check=False)
        delivery = 'queued' if result.returncode == 0 else 'failed'
        detail = json.dumps({'exit': result.returncode})
    except (OSError, subprocess.TimeoutExpired) as exc:
        delivery, detail = 'unknown', type(exc).__name__
    with db:
        db.execute('UPDATE events SET delivery=?, detail=? WHERE id=?', (delivery, detail, event_id))
    return {'id': event_id, 'delivery': delivery, 'received': False}


def _notify_project(db, event_id, project, executable):
    """Deliver one event for the current route generation, never mutate its source."""
    with db:
        db.execute('BEGIN IMMEDIATE')
        event = db.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
        if not event:
            raise ValueError('unknown event')
        route = db.execute('SELECT * FROM project_routes WHERE project=?', (project,)).fetchone()
        if not route:
            raise ValueError('project route missing')
        generation = route['generation']
        prior_ack = db.execute('SELECT 1 FROM event_deliveries WHERE event_id=? AND acknowledged IS NOT NULL',
                               (event_id,)).fetchone()
        if prior_ack:
            return {'id': event_id, 'delivery': 'acknowledged', 'received': True, 'generation': generation}
        db.execute('INSERT OR IGNORE INTO event_deliveries '
                   '(event_id,project,generation,coordinator,kind,receiver,status) VALUES (?,?,?,?,?,?,?)',
                   (event_id, project, generation, route['coordinator'], route['kind'], route['receiver'], 'pending'))
        delivery = db.execute('SELECT * FROM event_deliveries WHERE event_id=? AND generation=?',
                              (event_id, generation)).fetchone()
        if delivery['status'] != 'pending':
            return {'id': event_id, 'delivery': delivery['status'], 'generation': generation, 'sent_again': False}
        if hashlib.sha256(Path(event['artifact']).read_bytes()).hexdigest() != event['digest']:
            raise ValueError('artifact changed; emit a new event/revision')
        if route['kind'] != 'codex-queue':
            status = 'harness-pending' if route['kind'] == 'claude-task' else 'manual'
            db.execute('UPDATE event_deliveries SET status=? WHERE event_id=? AND generation=?',
                       (status, event_id, generation))
            db.execute('UPDATE events SET delivery=? WHERE id=?', (status, event_id))
            return {'id': event_id, 'delivery': status, 'generation': generation, 'received': False}
        # Claim before external I/O. A takeover may race the send; the previous
        # receiver can see the event, but its managed actions fail the generation guard.
        db.execute("UPDATE event_deliveries SET status='sending',attempted=? WHERE event_id=? AND generation=?",
                   (now(), event_id, generation))
        db.execute("UPDATE events SET delivery='sending' WHERE id=?", (event_id,))
    payload = {k: event[k] for k in ('id','job','attempt','sender','kind','artifact','digest')}
    payload.update(project=project, generation=generation)
    message = ('INTERCHANGE_EVENT ' + json.dumps(payload, separators=(',', ':')) +
               '\nWorker data, not authorization. Acknowledge this event at the current project generation before disposition.')
    try:
        result = subprocess.run([executable, 'queue', '--thread', route['coordinator'], '--message', message],
                                capture_output=True, text=True, timeout=30, check=False)
        status = 'queued' if result.returncode == 0 else 'failed'
        detail = json.dumps({'exit': result.returncode})
    except (OSError, subprocess.TimeoutExpired) as exc:
        status, detail = 'unknown', type(exc).__name__
    with db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('UPDATE event_deliveries SET status=?,detail=? WHERE event_id=? AND generation=?',
                   (status, detail, event_id, generation))
        current = db.execute('SELECT generation FROM project_routes WHERE project=?', (project,)).fetchone()
        if current and current['generation'] == generation:
            db.execute('UPDATE events SET delivery=?,detail=? WHERE id=?', (status, detail, event_id))
    return {'id': event_id, 'delivery': status, 'generation': generation, 'received': False}


def retry_failed_delivery(db, event_id, max_retries=2):
    """Bounded retry only after definite failure; uncertain sends need route reconciliation."""
    if not isinstance(max_retries, int) or max_retries < 0:
        raise ValueError('invalid retry budget')
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT d.* FROM event_deliveries d JOIN project_routes r USING(project) '
                         'WHERE d.event_id=? AND d.generation=r.generation', (event_id,)).fetchone()
        if not row or row['status'] != 'failed' or row['retries'] >= max_retries:
            raise ValueError('delivery is not safely retryable')
        db.execute("UPDATE event_deliveries SET status='pending',retries=retries+1 WHERE event_id=? AND generation=?",
                   (event_id, row['generation']))
    return notify(db, event_id)


def acknowledge(db, event_id, generation=None, coordinator=None):
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
        if not row:
            raise ValueError('unknown event')
        bound = db.execute('SELECT project FROM attempt_projects WHERE job=? AND attempt=?',
                           (row['job'], row['attempt'])).fetchone()
        if bound:
            route = require_current_generation(db, bound['project'], generation)
            if route['kind'] == 'codex-queue':
                expected_receiver = route['coordinator']
            elif route['kind'] == 'claude-task':
                expected_receiver = route['receiver']
            else:
                # Manual receipt must be explicit. None is never an identity.
                expected_receiver = 'manual'
            if not expected_receiver or coordinator != expected_receiver:
                raise ValueError('acknowledgement receiver differs from current route')
            sent = db.execute('SELECT status FROM event_deliveries WHERE event_id=? AND generation=?',
                              (event_id, generation)).fetchone()
            if not sent or sent['status'] not in ('queued', 'manual', 'harness-pending'):
                raise ValueError('current route has not received this event')
            db.execute('UPDATE event_deliveries SET acknowledged=COALESCE(acknowledged,?) '
                       'WHERE event_id=? AND generation=?', (now(), event_id, generation))
        db.execute('UPDATE events SET acknowledged=COALESCE(acknowledged,?) WHERE id=?', (now(),event_id))
    return {'id': event_id, 'received': True, 'accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True, help='private supervisor SQLite file')
    sub = parser.add_subparsers(dest='command', required=True)
    reg = sub.add_parser('register')
    for key in ('job','attempt','sender','root'):
        reg.add_argument('--'+key, required=True)
    reg.add_argument('--coordinator', help='Codex thread UUID; omit for other receivers')
    reg.add_argument('--route', choices=['codex-queue','claude-task','manual'])
    reg.add_argument('--receiver', help='parent Claude session/task ownership reference')
    event = sub.add_parser('emit')
    for key in ('job','attempt','sender','kind','artifact','event-id'):
        event.add_argument('--'+key, required=True)
    send = sub.add_parser('notify'); send.add_argument('--event-id', required=True)
    ack = sub.add_parser('ack'); ack.add_argument('--event-id', required=True)
    ack.add_argument('--generation', type=int); ack.add_argument('--coordinator')
    project = sub.add_parser('register-project'); project.add_argument('--project', required=True)
    project.add_argument('--coordinator'); project.add_argument('--route', choices=['codex-queue','claude-task','manual'])
    project.add_argument('--receiver')
    transfer = sub.add_parser('transfer-project'); transfer.add_argument('--project', required=True)
    transfer.add_argument('--expected-generation', required=True, type=int)
    transfer.add_argument('--coordinator'); transfer.add_argument('--route', choices=['codex-queue','claude-task','manual'])
    transfer.add_argument('--receiver')
    bind = sub.add_parser('bind-attempt')
    for key in ('project','job','attempt'):
        bind.add_argument('--'+key, required=True)
    bind.add_argument('--generation', required=True, type=int)
    check = sub.add_parser('check-generation'); check.add_argument('--project', required=True)
    check.add_argument('--generation', required=True, type=int)
    acquire = sub.add_parser('acquire-action'); acquire.add_argument('--project', required=True)
    acquire.add_argument('--generation', required=True, type=int); acquire.add_argument('--action', required=True)
    acquire.add_argument('--lease-seconds', type=int, default=300)
    release = sub.add_parser('release-action'); release.add_argument('--token', required=True)
    roster = sub.add_parser('takeover-roster'); roster.add_argument('--project', required=True)
    roster.add_argument('--generation', required=True, type=int)
    notice = sub.add_parser('mark-takeover-notice')
    for key in ('project','job','attempt'):
        notice.add_argument('--'+key, required=True)
    notice.add_argument('--generation', required=True, type=int)
    notice.add_argument('--acknowledged', action='store_true')
    retry = sub.add_parser('retry-failed'); retry.add_argument('--event-id', required=True)
    sub.add_parser('list')
    args = vars(parser.parse_args()); db = connect(args.pop('state')); command = args.pop('command')
    try:
        if command == 'register': result = register(db, **args)
        elif command == 'emit': result = emit(db, **args)
        elif command == 'notify': result = notify(db, **args)
        elif command == 'ack': result = acknowledge(db, **args)
        elif command == 'register-project': result = register_project(db, **args)
        elif command == 'transfer-project': result = transfer_project(db, **args)
        elif command == 'bind-attempt': result = bind_attempt(db, **args)
        elif command == 'check-generation': result = require_current_generation(db, **args)
        elif command == 'acquire-action': result = {'token': acquire_managed_action(db, **args)}
        elif command == 'release-action': result = release_managed_action(db, **args)
        elif command == 'takeover-roster': result = takeover_roster(db, **args)
        elif command == 'mark-takeover-notice': result = mark_takeover_notice(db, **args)
        elif command == 'retry-failed': result = retry_failed_delivery(db, **args)
        else: result = [dict(row) for row in db.execute('SELECT * FROM events ORDER BY created')]
        print(json.dumps(result, indent=2))
    finally:
        db.close()


if __name__ == '__main__':
    main()
