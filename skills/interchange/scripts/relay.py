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
KINDS = {'result', 'question', 'failed', 'exited'}


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
    CREATE TABLE IF NOT EXISTS launches (
      job TEXT, attempt TEXT, directory TEXT, started TEXT,
      PRIMARY KEY(job, attempt));
    CREATE TABLE IF NOT EXISTS events (
      id TEXT PRIMARY KEY, job TEXT, attempt TEXT, sender TEXT, kind TEXT,
      artifact TEXT, digest TEXT, created TEXT, delivery TEXT, detail TEXT,
      acknowledged TEXT);
    ''')
    return db


def identifier(value):
    if not IDENTIFIER.fullmatch(value):
        raise ValueError('invalid identifier')
    return value


def register(db, job, attempt, sender, root, coordinator=None):
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
        db.execute('INSERT OR IGNORE INTO attempts VALUES (?,?,?,?,?)', values)
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
    # Mark sending before external I/O; interruption becomes an uncertain delivery.
    # Do not automatically replay an uncertain send and manufacture duplicate work.
    with db:
        db.execute('BEGIN IMMEDIATE')
        row = db.execute('SELECT e.*, a.coordinator FROM events e JOIN attempts a USING(job,attempt) WHERE id=?', (event_id,)).fetchone()
        if not row:
            raise ValueError('unknown event')
        if not row['coordinator']:
            return {'id': event_id, 'delivery': 'manual', 'artifact': row['artifact']}
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
        detail = json.dumps({'exit': result.returncode, 'stdout': result.stdout[-1500:], 'stderr': result.stderr[-1500:]})
    except (OSError, subprocess.TimeoutExpired) as exc:
        delivery, detail = 'unknown', type(exc).__name__
    with db:
        db.execute('UPDATE events SET delivery=?, detail=? WHERE id=?', (delivery, detail, event_id))
    return {'id': event_id, 'delivery': delivery, 'received': False}


def acknowledge(db, event_id):
    with db:
        row = db.execute('SELECT * FROM events WHERE id=?', (event_id,)).fetchone()
        if not row:
            raise ValueError('unknown event')
        db.execute('UPDATE events SET acknowledged=COALESCE(acknowledged,?) WHERE id=?', (now(),event_id))
    return {'id': event_id, 'received': True, 'accepted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', required=True, help='private supervisor SQLite file')
    sub = parser.add_subparsers(dest='command', required=True)
    reg = sub.add_parser('register')
    for key in ('job','attempt','sender','root'):
        reg.add_argument('--'+key, required=True)
    reg.add_argument('--coordinator', help='Codex thread UUID; omit for manual inbox')
    event = sub.add_parser('emit')
    for key in ('job','attempt','sender','kind','artifact','event-id'):
        event.add_argument('--'+key, required=True)
    send = sub.add_parser('notify'); send.add_argument('--event-id', required=True)
    ack = sub.add_parser('ack'); ack.add_argument('--event-id', required=True)
    sub.add_parser('list')
    args = vars(parser.parse_args()); db = connect(args.pop('state')); command = args.pop('command')
    try:
        if command == 'register': result = register(db, **args)
        elif command == 'emit': result = emit(db, **args)
        elif command == 'notify': result = notify(db, **args)
        elif command == 'ack': result = acknowledge(db, **args)
        else: result = [dict(row) for row in db.execute('SELECT * FROM events ORDER BY created')]
        print(json.dumps(result, indent=2))
    finally:
        db.close()


if __name__ == '__main__':
    main()
