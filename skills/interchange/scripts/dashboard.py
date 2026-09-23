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


def esc(value):
    return html.escape(str(value or 'Not recorded'), quote=True)


def readable_time(value):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).strftime('%d %b %Y · %H:%M %Z')
    except (TypeError, ValueError, AttributeError):
        return 'Not recorded'


def session_details(agent):
    access = agent.get('session_access') or {}
    rows = '<p class="muted">Session ' + esc(agent.get('session_id')) + '</p>'
    for key, label in [('open_action', 'Open session'), ('inspect_argv', 'Inspect'), ('resume_argv', 'Resume after ownership check'), ('artifact_fallback', 'Handover')]:
        value = access.get(key)
        if value:
            if isinstance(value, list):
                import shlex
                value = shlex.join(value)
            rows += '<p><strong>' + label + '</strong><br><code>' + esc(value) + '</code></p>'
    return '<details><summary>Session &amp; handover</summary>' + rows + '</details>'


def render(root):
    records = [json.loads(p.read_text()) for p in sorted((root / 'coordinators').glob('*.json'))]
    cards = []
    for record in records:
        project = record['project_id']
        coordinator = record['coordinator']
        attempts = record.get('attempts') or []
        agents = ''
        for attempt in attempts:
            agents += ('<div class="agent"><div><strong>' + esc(attempt.get('agent_id'))
                       + '</strong><span class="muted"> · ' + esc(attempt.get('role'))
                       + '</span><p>' + esc(attempt.get('job_id')) + '</p></div><div><span class="badge">'
                       + esc(attempt.get('last_observed_state')) + '</span><p class="muted">'
                       + esc(attempt.get('observed_model_effort') or 'Model not verified')
                       + '</p></div>' + session_details(attempt) + '</div>')
        if not agents:
            agents = '<p class="empty">No worker activity recorded in this snapshot.</p>'
        plan = (record.get('plan') or {}).get('path', '')
        link = ('<a class="button" href="' + esc(plan) + '">Open plan / PR ↗</a>'
                if isinstance(plan, str) and plan.startswith(('https://', 'http://')) else '')
        cards.append('<section data-project="' + esc(project) + '"><header class="project-head"><div>'
                     + '<div class="eyebrow">PROJECT</div><h2>' + esc(project.replace('-', ' ').title())
                     + '</h2><p class="muted">Coordinated by <strong>' + esc(coordinator['agent_id'])
                     + '</strong> · ' + esc(coordinator.get('client')) + '</p></div>' + link + '</header>'
                     + '<div class="next"><div class="eyebrow">NEXT ACTION</div><p>' + esc(record.get('next_action')) + '</p></div>'
                     + '<div class="columns"><div><h3>Agent activity <span class="count">' + str(len(attempts))
                     + '</span></h3>' + agents + '</div><aside><h3>Coordination</h3><p>'
                     + esc(record.get('scheduling')) + '</p><h4>Takeover</h4><p>'
                     + esc((record.get('transfer') or {}).get('state', 'Not requested').replace('-', ' '))
                     + '</p>' + session_details(coordinator) + '</aside></div>'
                     + '<footer>Observed ' + esc(readable_time(record.get('updated_at')))
                     + ' · Published ' + esc(readable_time(record.get('published_at'))) + '</footer>'
                     + '<details class="raw"><summary>Technical record</summary><pre>'
                     + esc(json.dumps(record, indent=2)) + '</pre></details></section>')
    options = ''.join('<option value="' + esc(p) + '">' + esc(p.replace('-', ' ').title()) + '</option>'
                      for p in sorted({r['project_id'] for r in records}))
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Interchange · Activity</title>
<style>
:root{--ink:#202c38;--muted:#62707b;--line:#dce1e4;--paper:#f8f9fa;--accent:#245e5a}
*{box-sizing:border-box}body{font:15px/1.55 system-ui;margin:0;background:var(--paper);color:var(--ink)}
.top{border-bottom:1px solid var(--line);padding:18px 32px;display:flex;justify-content:space-between;align-items:center}.brand{font-weight:750;letter-spacing:-.5px;font-size:20px}.top span{font-size:13px;color:var(--muted)}
main{max-width:1160px;margin:auto;padding:36px 28px}h1{font-size:30px;letter-spacing:-1px;margin:0}h2{font-size:23px;letter-spacing:-.5px;margin:4px 0}h3{font-size:15px;margin:0 0 16px}h4{font-size:13px;margin:24px 0 4px}p{margin:6px 0 12px}.muted,footer{color:var(--muted);font-size:13px}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:20px;margin-bottom:28px}.toolbar p{color:var(--muted)}select,.button,button{font:inherit;border:1px solid var(--line);border-radius:6px;padding:9px 12px;background:transparent;color:var(--ink)}a{color:var(--accent)}.button{text-decoration:none;font-size:13px;white-space:nowrap}.button:hover,button:hover{background:#edf2f1}button{cursor:pointer}select:focus-visible,a:focus-visible,summary:focus-visible,button:focus-visible{outline:3px solid #71a7a1;outline-offset:3px}
section{border:1px solid var(--line);border-radius:10px;margin:0 0 24px;overflow:hidden;background:#fcfcfc}.project-head{padding:24px;display:flex;justify-content:space-between;align-items:center;gap:16px}.eyebrow{font-size:11px;letter-spacing:1.2px;font-weight:700;color:var(--muted)}.next{margin:0 24px;padding:16px 18px;background:#edf3f1;border-left:3px solid var(--accent);border-radius:3px}.next p{margin:5px 0;font-size:16px}
.columns{display:grid;grid-template-columns:1.65fr 1fr;gap:32px;padding:28px 24px}.columns aside{border-left:1px solid var(--line);padding-left:24px}.count,.badge{font-size:12px;background:#edf0f2;padding:3px 8px;border-radius:4px;font-weight:500}.count{margin-left:6px}.empty{padding:24px 16px;border:1px dashed var(--line);color:var(--muted);font-size:14px}.agent{border-top:1px solid var(--line);padding:14px 0;display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px}.agent details{width:100%}details{font-size:13px}summary{cursor:pointer;color:var(--accent);padding:8px 0}code,pre{font:12px/1.6 ui-monospace,monospace;overflow-wrap:anywhere;white-space:pre-wrap}footer{padding:16px 24px;border-top:1px solid var(--line);font-size:12px}.raw{padding:0 24px 12px}.raw summary{color:var(--muted)}.note{font-size:12px;color:var(--muted)}[hidden]{display:none!important}
@media(max-width:650px){main{padding:24px 16px}.top{padding:16px}.toolbar,.project-head{align-items:flex-start;flex-direction:column}.columns{grid-template-columns:1fr;gap:20px}.columns aside{border-left:0;border-top:1px solid var(--line);padding:20px 0 0}.top span{display:none}.project-head,.columns{padding:20px}.next{margin:0 20px}}
</style><div class="top"><div class="brand">Interchange <span> / repository activity</span></div><button onclick="location.reload()">Refresh snapshot</button></div>
<main><div class="toolbar"><div><h1>Work in motion</h1><p>Projects, people and the next step.</p></div><label>Project <select id="project"><option value="">All activity</option>''' + options + '</select></label></div>'
    page += ''.join(cards) or '<p class="empty">No coordinator snapshots published yet.</p>'
    page += '''<p class="note">Published snapshots, not live monitoring. Session commands are shown for inspection; this page does not launch agents.</p></main><script>document.getElementById('project').onchange=function(){document.querySelectorAll('section').forEach(s=>s.hidden=!!this.value&&s.dataset.project!==this.value);};</script></html>'''
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
