#!/usr/bin/env python3
"""Serve one always-available dashboard for every project under a shared coordination root.

Nothing registers a project: the coordinator already writes ``<root>/projects/<project>/continuation.json``
when a plan starts, so a project appears on the next page load. Rendering happens per request
(no timer, no background refresh) and reuses ``dashboard.render``. Each attempt card gains a few
sanitized live facts read from its attempt directory (state, tool calls seen, last output time),
never raw worker output.

The server is read-only and binds to loopback by default. A project whose record cannot be read or
rendered is shown as an error card; it never blanks the page for the other projects.

Usage: dashboard_server.py --root <shared coordination root> [--bind 127.0.0.1] [--port 7390]
"""
import argparse
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import tempfile

import dashboard

PROJECT_ID = re.compile(r'^[A-Za-z0-9_-]{1,100}$')
TOOL_PART = b'"type":"tool_use"'


def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat(timespec='seconds')


def attempt_facts(project_dir, attempt):
    """Sanitized facts for one attempt, derived from its attempt directory; no worker text."""
    job = attempt.get('job_id')
    name = attempt.get('attempt') or attempt.get('attempt_id') or 'a1'
    if not isinstance(job, str) or not PROJECT_ID.match(job) or not re.fullmatch(r'[A-Za-z0-9_-]{1,40}', str(name)):
        return None
    directory = project_dir / 'jobs' / job / f'attempt-{name}'
    stdout = directory / 'stdout.log'
    if not stdout.is_file():
        return None
    try:
        data = stdout.read_bytes()
        facts = {'tool_calls': data.count(TOOL_PART), 'last_output_at': iso(stdout.stat().st_mtime)}
        result = directory / 'process-result.json'
        if result.is_file():
            receipt = json.loads(result.read_text())
            facts['process'] = f"exited {receipt.get('exit_code')} ({receipt.get('process_outcome')})"
        else:
            facts['process'] = 'running'
        return facts
    except (OSError, ValueError):
        return {'process': 'unreadable'}


def collect(root):
    """Return (records, errors) for every project with a continuation record."""
    records, errors = [], []
    projects = root / 'projects'
    for project_dir in sorted(p for p in projects.glob('*') if p.is_dir()) if projects.is_dir() else []:
        path = project_dir / 'continuation.json'
        if not path.is_file():
            continue
        try:
            record = json.loads(path.read_text())
            if not isinstance(record, dict) or not PROJECT_ID.match(str(record.get('project_id', ''))):
                raise ValueError('project_id missing or not 1-100 letters, digits, _ or -')
            coordinator = record.get('coordinator')
            if not isinstance(coordinator, dict) or not PROJECT_ID.match(str(coordinator.get('agent_id', ''))):
                raise ValueError('coordinator.agent_id missing or not a plain identifier')
            for attempt in record.get('attempts') or []:
                if isinstance(attempt, dict):
                    facts = attempt_facts(project_dir, attempt)
                    if facts:
                        attempt['live_facts'] = facts
                        if facts['process'] == 'running' and not str(attempt.get('execution_state', '')).startswith(('MERGED', 'done')):
                            attempt['execution_state'] = f"running · {facts['tool_calls']} tool calls · last output {facts['last_output_at']}"
            monitor_path = project_dir / 'monitor.json'
            if monitor_path.exists():
                if monitor_path.is_symlink() or monitor_path.stat().st_size > 1_000_000:
                    raise ValueError('unsafe or oversized monitor record')
                monitor = json.loads(monitor_path.read_text())
                if not isinstance(monitor, dict) or monitor.get('project_id') != record['project_id']:
                    raise ValueError('monitor project identity mismatch')
                record['supervision'] = {
                    'updated_at': monitor.get('updated_at'),
                    'notification_available': monitor.get('notification_available') is True,
                    'alerts': [{k: str(a.get(k, ''))[:120] for k in
                                ('code', 'type', 'job', 'attempt', 'next_owner')}
                               for a in monitor.get('alerts', []) if isinstance(a, dict)][:100],
                }
            dashboard.validate_done_sources(record)
            records.append(record)
        except Exception as exc:  # one broken project must not blank the others
            errors.append((project_dir.name, f'{type(exc).__name__}: {exc}'))
    return records, errors


def build_page(root):
    """Render every project into one page; error cards first so a broken record is visible."""
    records, errors = collect(Path(root))
    with tempfile.TemporaryDirectory() as scratch:
        target = Path(scratch)
        (target / 'coordinators').mkdir()
        for index, record in enumerate(records):
            dashboard.atomic_write(target / 'coordinators' / f'{index:04d}.json', json.dumps(record))
        dashboard.render(target)
        page = (target / 'index.html').read_text()
    if errors:
        cards = ''.join('<section class="unmapped"><strong>' + dashboard.esc(name) + '</strong>: this project could '
                        'not be rendered — ' + dashboard.esc(message) + '</section>' for name, message in errors)
        page = page.replace('<main>', '<main>' + cards, 1)
    return page


def make_handler(root):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.split('?', 1)[0] not in ('/', '/index.html'):
                self.send_error(404)
                return
            try:
                body = build_page(root).encode()
                self.send_response(200)
            except Exception as exc:
                body = ('<!doctype html><p>Dashboard render failed: '
                        + dashboard.esc(f'{type(exc).__name__}: {exc}') + '</p>').encode()
                self.send_response(500)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Cache-Control', 'no-store')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            return

    return Handler


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', required=True, help='shared coordination root (contains projects/)')
    parser.add_argument('--bind', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=7390)
    args = parser.parse_args(argv)
    root = Path(args.root).resolve()
    if not (root / 'projects').is_dir():
        parser.error(f'{root} has no projects/ directory')
    server = ThreadingHTTPServer((args.bind, args.port), make_handler(root))
    print(f'Serving {root} at http://{args.bind}:{args.port}/', flush=True)
    server.serve_forever()


if __name__ == '__main__':
    main()
