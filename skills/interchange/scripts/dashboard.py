#!/usr/bin/env python3
"""Publish coordinator snapshots and render one local dashboard per Git repository."""
import argparse
import fcntl
import html
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from datetime import datetime, timezone


def root_for(repo):
    common = subprocess.check_output(
        ['git', '-C', str(repo), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
        text=True).strip()
    common = Path(common).resolve()
    # Linked worktrees share the primary checkout's .git directory.
    return (common.parent / '.interchange' / 'observability'
            if common.name == '.git' else common / 'interchange-observability')


def atomic_write(path, value):
    fd, name = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(value)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def render(root):
    records = [json.loads(p.read_text()) for p in sorted((root / 'coordinators').glob('*.json'))]
    cards = []
    for record in records:
        project = str(record['project_id'])
        coordinator = record['coordinator']['agent_id']
        cards.append('<section data-project="' + html.escape(project, quote=True) + '"><h2>'
                     + html.escape(project + ' / ' + coordinator) + '</h2><p>Snapshot: '
                     + html.escape(str(record.get('updated_at') or 'unknown'))
                     + ' · Published: ' + html.escape(str(record.get('published_at') or 'unknown'))
                     + ' — reported state, not a live process check.</p><pre>'
                     + html.escape(json.dumps(record, indent=2)) + '</pre></section>')
    options = ''.join('<option>' + html.escape(p) + '</option>' for p in sorted(
        {str(r['project_id']) for r in records}))
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Interchange observability</title><style>
body{font:16px system-ui;margin:2rem auto;max-width:1100px;padding:0 1rem;background:#f4f6fa;color:#192334}
section{background:white;border:1px solid #ccd3df;border-radius:12px;padding:1rem;margin:1rem 0}
pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:13px}select{padding:.6rem}h1{margin-bottom:.4rem}
</style><h1>Interchange</h1><p>Repository activity · reload after a published update. Commands are displayed only; this page executes nothing.</p>
<label>Project <select id="project"><option value="">All activity</option>''' + options + '''</select></label>'''
    page += ''.join(cards) or '<p>No coordinator snapshots published.</p>'
    page += '''<script>document.getElementById('project').onchange=function(){
document.querySelectorAll('section').forEach(s=>s.hidden=!!this.value&&s.dataset.project!==this.value);};</script></html>'''
    atomic_write(root / 'index.html', page)


def publish(repo, record):
    project = record['project_id']
    agent = record['coordinator']['agent_id']
    for value in (project, agent):
        if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', value):
            raise ValueError('project and coordinator IDs must be 1–100 letters, digits, _ or -')
    root = root_for(repo)
    (root / 'coordinators').mkdir(parents=True, exist_ok=True)
    # Ignore locally generated state without changing the repository's tracked files.
    atomic_write(root / '.gitignore', '*\n')
    with (root / '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        record = dict(record)
        record['published_at'] = datetime.now(timezone.utc).isoformat()
        identity = hashlib.sha256(json.dumps([project, agent]).encode()).hexdigest()
        atomic_write(root / 'coordinators' / (identity + '.json'),
                     json.dumps(record, indent=2) + '\n')
        render(root)
    return root / 'index.html'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='.')
    parser.add_argument('--snapshot', required=True, help='continuation.json; no secrets or raw transcripts')
    args = parser.parse_args()
    print(publish(args.repo, json.loads(Path(args.snapshot).read_text())))


if __name__ == '__main__':
    main()
