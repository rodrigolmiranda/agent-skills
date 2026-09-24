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
    if value is None or value == '':
        value = 'Unknown'
    return html.escape(str(value), quote=True)


def readable_time(value):
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        label = parsed.strftime('%d %b %Y · %H:%M %Z')
        return label if parsed.tzinfo else label + ' (timezone unknown)'
    except (TypeError, ValueError, AttributeError):
        return 'Unknown'


def recorded_time(value):
    return readable_time(value) if parse_snapshot_time(value) is not None else 'Not recorded'


def parse_snapshot_time(value):
    """Parse a supplied snapshot timestamp without consulting the wall clock."""
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
        # Relative age is only truthful when both ends carry an offset.  Do
        # not compare an offsetless historical value with an aware snapshot.
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, AttributeError):
        return None


def explicit_value(sources, names):
    """Return the first supplied value, preserving explicit false/zero values."""
    for source in sources:
        if not isinstance(source, dict):
            continue
        for name in names:
            value = source.get(name)
            if value is not None and value != '':
                return value
    return None


def progress_details(item, attempt):
    sources = [item, attempt]
    progress = explicit_value(sources, ('last_progress_summary',))
    progress_at = explicit_value(sources, ('last_progress_at',))
    return progress, progress_at


def next_event_details(item, attempt):
    sources = [item, attempt]
    event = explicit_value(sources, ('next_event',))
    owner = explicit_value(sources, ('next_owner',))
    if owner is None and state_key(item.get('state')) == 'waiting':
        owner = explicit_value(sources, ('waiting_owner',))
    return event, owner


def follow_up_details(item, attempt):
    return explicit_value([item, attempt], ('follow_up_due_at',))


def waiting_duration(item, attempt, snapshot_at=None):
    waiting_since = explicit_value([item, attempt], ('waiting_since',))
    observed = parse_snapshot_time(snapshot_at)
    started = parse_snapshot_time(waiting_since)
    if started is None or observed is None:
        return 'Not recorded'
    # A future timestamp is evidence of an inconsistent snapshot, not a
    # negative duration we should present as elapsed waiting time.
    if started > observed:
        return 'Not recorded (waiting timestamp is after snapshot)'
    seconds = int((observed - started).total_seconds())
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, _ = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(str(days) + 'd')
    if hours or days:
        parts.append(str(hours) + 'h')
    parts.append(str(minutes) + 'm')
    return ' '.join(parts)


def follow_up_label(item, attempt, snapshot=None):
    due_at = follow_up_details(item, attempt)
    if due_at is None:
        return None
    observed = parse_snapshot_time(snapshot.get('updated_at') if isinstance(snapshot, dict) else None)
    due = parse_snapshot_time(due_at)
    if observed is None or due is None:
        return 'Follow-up status not recorded'
    if due <= observed:
        return 'Overdue follow-up'
    return 'Follow-up due ' + readable_time(due_at)


def status_label(value):
    if value is None or value == '':
        return 'Unknown'
    return re.sub(r'[_-]+', ' ', str(value)).strip().capitalize()


def compact_model_name(value):
    label = value.strip()
    if 'deepseek' in label.casefold():
        return 'DeepSeek'
    match = re.search(
        r'(?:^|[-\s])(?:gpt-\d+(?:\.\d+)?-)?(luna|sol|astra|terra)(?:$|[-\s])',
        label, re.IGNORECASE)
    return match.group(1).capitalize() if match else label


def has_identity_evidence(agent):
    if not isinstance(agent, dict):
        return False
    evidence = agent.get('identity_evidence')
    return (isinstance(evidence, str) and bool(evidence.strip())
            and evidence.strip().casefold() not in {'unknown', 'none', 'n/a', 'not exposed', 'not verified'})


def model_effort(agent, requested, compact=False):
    prefix = 'requested' if requested else 'observed'
    if not isinstance(agent, dict):
        return 'Not exposed'
    if not requested and not has_identity_evidence(agent):
        return 'Not exposed'
    model = agent.get(prefix + '_model')
    effort = agent.get(prefix + '_effort')
    combined = agent.get(prefix + '_model_effort')
    if model is None and effort is None:
        if not isinstance(combined, str) or not combined.strip():
            return 'Not exposed'
        if combined.strip().casefold() in {'unknown', 'not exposed', 'n/a'}:
            return 'Not exposed'
        if compact:
            parts = re.split(r'\s*[·/]\s*', combined.strip(), maxsplit=1)
            if len(parts) == 2:
                return esc(compact_model_name(parts[0])) + ' · ' + esc(parts[1])
        return esc(combined.strip())
    if (not isinstance(model, str) or not model.strip()
            or not isinstance(effort, str) or not effort.strip()):
        return 'Not exposed'
    if model.strip().casefold() in {'unknown', 'not exposed', 'n/a'}:
        return 'Not exposed'
    if effort.strip().casefold() in {'unknown', 'not exposed', 'n/a'}:
        return 'Not exposed'
    model_label = compact_model_name(model) if compact else model.strip()
    return esc(model_label) + ' · ' + esc(effort.strip())


def summary_model_badge(attempt):
    if not isinstance(attempt, dict):
        return 'No agent'
    observed = model_effort(attempt, False, compact=True)
    if observed != 'Not exposed':
        return 'Observed · ' + observed
    return 'Requested · ' + model_effort(attempt, True, compact=True)


def snapshot_details(title, value, missing='Unknown'):
    if value is None or value == '' or value == [] or value == {}:
        content = esc(missing)
    else:
        content = esc(json.dumps(value, indent=2, ensure_ascii=False))
    return ('<details><summary>' + title + '</summary><pre>' + content + '</pre></details>')


def dependency_label(value):
    if value is None:
        return 'Unknown'
    if isinstance(value, (list, tuple)):
        return ', '.join(str(item) for item in value) if value else 'None'
    return str(value)


def ordered_steps(value):
    if not isinstance(value, list):
        return []

    def key(index_step):
        index, step = index_step
        order = step.get('order') if isinstance(step, dict) else None
        try:
            return (0, float(order), index)
        except (TypeError, ValueError):
            return (1, index, index)

    return [step for _, step in sorted(enumerate(value), key=key) if isinstance(step, dict)]


def state_key(value):
    return re.sub(r'[^a-z0-9]+', '_', str(value or '').lower()).strip('_')


def status_class(value):
    state = state_key(value)
    if state in {'running', 'in_progress', 'working', 'started', 'completed', 'complete', 'done', 'succeeded'}:
        return 'status-good'
    if state in {'blocked', 'waiting', 'needs_attention', 'failed', 'error', 'overdue_follow_up'}:
        return 'status-attention'
    if state in {'stopped', 'rejected', 'canceled', 'cancelled', 'provider_quota', 'quota_exhausted', 'model_rejected'}:
        return 'status-terminal'
    return 'status-unknown'


def recency_key(attempt):
    for key in ('last_observed_at', 'returned_at', 'ended_at', 'started_at', 'created_at'):
        value = attempt.get(key)
        try:
            parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return (parsed.timestamp(), str(attempt.get('agent_id') or ''))
        except (TypeError, ValueError, AttributeError):
            pass
    return (float('-inf'), str(attempt.get('agent_id') or ''))


def latest_attempt(attempts):
    return max(attempts, key=recency_key) if attempts else None


def activity_column(item, attempts):
    state = state_key(item.get('state')) if item is not None else ''
    execution = ''
    outcome = ''
    current = latest_attempt(attempts)
    if current:
        execution = state_key(current.get('execution_state') or current.get('last_observed_state'))
        outcome = state_key(current.get('outcome'))
    completed = {'done', 'complete', 'completed', 'finished', 'succeeded'}
    active = {'running', 'in_progress', 'working', 'started'}
    blocked = {'blocked', 'needs_attention', 'failed', 'error', 'stopped',
               'rejected', 'provider_quota', 'quota_exhausted', 'model_rejected',
               'canceled', 'cancelled'}
    # Explicit attempt failures and blocked plan states outrank a process merely
    # reporting that it finished. Completion is accepted only from an explicit
    # successful outcome or the coordinator's completed plan state.
    if outcome in blocked or execution in blocked:
        return 'blocked'
    if state == 'awaiting_acceptance':
        return 'blocked' if item.get('blocker') else 'next'
    if state in {'review', 'in_review'}:
        return 'review'
    if state == 'waiting':
        return 'waiting'
    if execution in active:
        return 'working'
    if state in blocked:
        return 'blocked'
    # A completed slice is a completed delivery at its declared scope.  The
    # parent issue remains open, which is rendered on the card separately.
    if item.get('completion_scope') == 'step' and state in completed:
        return 'done'
    if outcome in completed:
        return 'done'
    if state in completed:
        return 'done'
    if state in active:
        return 'working'
    if execution in completed:
        # The process ended, but the task outcome was not supplied.
        return 'blocked'
    # Unknown plan state remains visible as upcoming; the renderer does not infer readiness.
    return 'next'


def safe_link(value, label):
    if isinstance(value, str) and value.startswith(('https://', 'http://')):
        return '<a href="' + esc(value) + '" target="_blank" rel="noreferrer">' + esc(label) + '</a>'
    return esc('Unknown')


def task_attempt_card(attempt):
    timing = attempt.get('timing')
    if timing is None:
        timing = {key: attempt.get(key) for key in ('started_at', 'ended_at', 'last_observed_at')}
        if all(value is None for value in timing.values()):
            timing = None
    execution = attempt.get('execution_state') or attempt.get('last_observed_state')
    return ('<div class="attempt-record"><strong>' + esc(attempt.get('attempt_id'))
            + '</strong> · ' + esc(attempt.get('agent_id')) + ' · Execution state: '
            + '<span class="status-text ' + status_class(execution) + '">'
            + esc(status_label(execution)) + '</span> · Outcome: '
            + '<span class="status-text ' + status_class(attempt.get('outcome')) + '">'
            + esc(status_label(attempt.get('outcome'))) + '</span><div class="attempt-details">'
            + '<span>Requested model / effort: ' + model_effort(attempt, True) + '</span>'
            + '<span>Observed model / effort: ' + model_effort(attempt, False) + '</span>'
            + ('<span>Model identity evidence: ' + esc(attempt.get('identity_evidence')) + '</span>'
               if has_identity_evidence(attempt) else '')
            + '<span>Started: ' + esc(readable_time(attempt.get('started_at'))) + '</span>'
            + '<span>Ended: ' + esc(readable_time(attempt.get('ended_at'))) + '</span>'
            + '<span>Last observed: ' + esc(readable_time(attempt.get('last_observed_at'))) + '</span>'
            + snapshot_details('Timing', timing)
            + snapshot_details('Evaluation dimensions', attempt.get('evaluation'), 'Not assessed')
            + snapshot_details('Interaction history', attempt.get('history'))
            + snapshot_details('Evidence', attempt.get('evidence'))
            + session_details(attempt) + '</div></div>')


def attempt_groups(record, steps):
    attempts = [attempt for attempt in record.get('attempts') or [] if isinstance(attempt, dict)]
    if not steps:
        grouped = {}
        for index, attempt in enumerate(attempts):
            job_id = attempt.get('job_id')
            key = str(job_id) if job_id else 'Unknown job ' + str(attempt.get('attempt_id') or index + 1)
            grouped.setdefault(key, []).append(attempt)
        return [({'id': key, 'job_id': key, 'title': (latest_attempt(group).get('task') or key)}, group)
                for key, group in grouped.items()], []

    def typed_id(value):
        if value is None or value == '' or not isinstance(value, (str, int, float, bool)):
            return None
        return type(value), value

    step_ids = {}
    job_ids = {}
    for index, step in enumerate(steps):
        step_id = typed_id(step.get('id'))
        job_id = typed_id(step.get('job_id'))
        if step_id is not None:
            step_ids.setdefault(step_id, []).append(index)
        if job_id is not None:
            job_ids.setdefault(job_id, []).append(index)

    attached = [[] for _ in steps]
    unmatched = []
    for attempt in attempts:
        # The two identifiers belong to different namespaces. An explicit step
        # identity is authoritative; job fallback is allowed only when absent.
        step_id = typed_id(attempt.get('workflow_step_id'))
        if step_id is not None:
            candidates = step_ids.get(step_id, [])
        else:
            job_id = typed_id(attempt.get('job_id'))
            candidates = job_ids.get(job_id, []) if job_id is not None else []
        if len(candidates) == 1:
            attached[candidates[0]].append(attempt)
        else:
            unmatched.append(attempt)

    return list(zip(steps, attached)), unmatched


def task_card(item, attempts, snapshot=None):
    current = latest_attempt(attempts)
    column = activity_column(item, attempts)
    title = item.get('title') or (current.get('task') if current else None) or 'Untitled activity'
    owner = item.get('owner')
    if owner is None or owner == '':
        owner = (current.get('owner') or current.get('agent_id')) if current else None
    owner_label = 'Unassigned' if owner is None or owner == '' else str(owner)
    summary_owner = re.sub(r'[_-]+', ' ', owner_label)
    execution_state = (current.get('execution_state') or current.get('last_observed_state')) if current else None
    outcome = current.get('outcome') if current else None
    action = item.get('next_action') or (current.get('current_action') or current.get('next_action') if current else None)
    blocker = item.get('blocker') or (current.get('blocker') if current else None)
    progress, progress_at = progress_details(item, current)
    next_event, next_owner = next_event_details(item, current)
    follow_up = follow_up_label(item, current, snapshot)
    snapshot_at = snapshot.get('updated_at') if isinstance(snapshot, dict) else None
    readiness = item.get('readiness')
    if readiness is None:
        readiness_label = 'Not supplied'
    elif isinstance(readiness, bool):
        readiness_label = 'Ready' if readiness else 'Not ready'
    else:
        readiness_label = str(readiness)
    order = item.get('order')
    requested = model_effort(current, True)
    observed = model_effort(current, False)
    links = []
    issue_url = item.get('issue_url') or item.get('source_url') or ((current.get('issue_url') or current.get('source_url')) if current else None)
    parent_url = item.get('parent_url')
    if issue_url:
        links.append('<span><strong>Issue:</strong> ' + safe_link(issue_url, item.get('issue_title') or issue_url) + '</span>')
    if parent_url:
        links.append('<span><strong>Parent:</strong> ' + safe_link(parent_url, item.get('parent_title') or parent_url) + '</span>')
    pr_url = item.get('pr_url') or (current.get('pr_url') if current else None)
    if pr_url:
        links.append('<span><strong>PR:</strong> ' + safe_link(pr_url, item.get('pr_title') or 'Pull request') + '</span>')
    for link in item.get('links') or []:
        if isinstance(link, dict) and link.get('url'):
            links.append(safe_link(link['url'], link.get('label') or link['url']))
    parallel = item.get('can_run_in_parallel')
    if parallel is None:
        parallel_label = 'Not supplied'
    else:
        parallel_label = 'Yes' if parallel else 'No'
    logical_status = {'working': 'Working now', 'blocked': 'Blocked', 'next': 'Next', 'waiting': 'Waiting', 'review': 'Review', 'done': 'Done'}[column]
    if column == 'done' and item.get('completion_scope') == 'step':
        parent_state = state_key(item.get('github_issue_state'))
        logical_status = {
            'open': 'Step done · parent remains open',
            'closed': 'Step done · parent already closed',
        }.get(parent_state, 'Step done · slice scope')
    if column == 'blocked':
        summary_detail = blocker or (status_label(outcome) if outcome else 'Needs attention')
    else:
        summary_detail = action or 'No current action supplied'
    show_models = column in {'working', 'done'}
    model_badge = ('<span class="summary-model-badge">' + esc(summary_model_badge(current))
                   + '</span>') if show_models else ''
    follow_up_badge = ('<span class="summary-follow-up status-attention">' + esc(follow_up)
                       + '</span>') if follow_up == 'Overdue follow-up' else ''
    attempts_block = ('<details class="attempt-history"><summary>Attempts and retries ('
                      + str(len(attempts)) + ')</summary>'
                      + (''.join(task_attempt_card(attempt) for attempt in sorted(attempts, key=recency_key, reverse=True))
                         or '<p class="empty">No attempts recorded.</p>') + '</details>')
    content = ('<details class="task-card"><summary class="task-summary">'
               + '<span class="summary-top-row"><span class="summary-title">' + esc(title) + '</span>'
               + model_badge + follow_up_badge + '</span>'
               + '<span class="summary-meta"><span class="summary-owner">' + esc(summary_owner)
               + '</span><span aria-hidden="true">·</span><span class="summary-status '
               + status_class(column) + '">' + esc(logical_status) + '</span></span>'
               + '<span class="summary-detail">' + esc(summary_detail) + '</span>'
               + '</summary>'
               + '<div class="task-card-body"><div class="card-title"><strong>' + esc(title)
               + '</strong><span class="badge ' + status_class(column) + '">'
               + 'Board status: ' + esc(logical_status) + '</span></div>'
               + '<p><strong>Activity:</strong> ' + esc(item.get('id'))
               + ' · <strong>Order:</strong> ' + esc(order) + '</p>'
               + '<p><strong>Plan status:</strong> ' + esc(status_label(item.get('state'))) + '</p>'
               + '<p><strong>Owner:</strong> ' + esc(owner_label) + '</p>'
               + '<p><strong>Requested model / effort:</strong> ' + requested + '</p>'
               + '<p><strong>Observed model / effort:</strong> ' + observed + '</p>'
               + '<p><strong>Current action:</strong> ' + esc(action) + '</p>'
               + '<p><strong>Last meaningful progress:</strong> ' + esc(progress or 'Not recorded')
               + ' · <strong>At:</strong> ' + esc(recorded_time(progress_at))
               + '</p>'
               + '<p><strong>Next event:</strong> ' + esc(next_event or 'Not recorded')
               + ' · <strong>Next owner:</strong> ' + esc(next_owner or 'Not recorded') + '</p>')
    if column == 'waiting':
        content += '<p><strong>Waiting for:</strong> ' + esc(item.get('waiting_for') or 'Not supplied') + '</p>'
        content += '<p><strong>Waiting owner:</strong> ' + esc(item.get('waiting_owner') or 'Not supplied') + '</p>'
        waiting_since = item.get('waiting_since')
        content += '<p><strong>Waiting since:</strong> ' + esc(recorded_time(waiting_since)) + '</p>'
        content += '<p><strong>Waiting duration:</strong> ' + esc(waiting_duration(item, current, snapshot_at)) + '</p>'
    if follow_up:
        content += '<p><strong>Follow-up:</strong> <span class="status-text ' + status_class(follow_up) + '">' + esc(follow_up) + '</span></p>'
    if item.get('completion_scope') == 'step' and column == 'done':
        parent_state = state_key(item.get('github_issue_state'))
        parent_note = {
            'open': 'Parent remains open (snapshot says OPEN).',
            'closed': 'Parent is already closed (snapshot says CLOSED).',
        }.get(parent_state, 'Parent state not recorded.')
        content += '<p><strong>Completion scope:</strong> Step slice complete; ' + esc(parent_note) + '</p>'
    if item.get('review_history'):
        content += snapshot_details('Completed checks (not delivery acceptance)', item['review_history'])
    if item.get('manual_observation'):
        report = item['manual_observation']
        content += '<p><strong>Reported (not verified):</strong> ' + esc(report.get('summary')) + '</p>'
        content += snapshot_details('Reported observation (not verified execution)', item['manual_observation'])
    if has_identity_evidence(current):
        content += '<p><strong>Model identity evidence:</strong> ' + esc(current.get('identity_evidence')) + '</p>'
    if column == 'blocked':
        content += '<p><strong>Blocker:</strong> ' + esc(blocker or outcome or 'Unknown') + '</p>'
    content += ('<p><strong>Execution state:</strong> <span class="status-text '
                + status_class(execution_state) + '">' + esc(status_label(execution_state))
                + '</span> · <strong>Outcome:</strong> <span class="status-text '
                + status_class(outcome) + '">' + esc(status_label(outcome)) + '</span></p>')
    content += ('<p><strong>Issue and parent:</strong> ' + ' · '.join(links) + '</p>' if links
                else '<p><strong>Source:</strong> Unknown</p>')
    content += ('<p><strong>Dependencies:</strong> ' + esc(dependency_label(item.get('dependencies')))
                + ' · <strong>Readiness:</strong> ' + esc(readiness_label)
                + '</p><p><strong>Can run in parallel:</strong> ' + esc(parallel_label) + '</p>'
                + attempts_block + '</div></details>')
    return content, column


def board(record):
    steps = ordered_steps(record.get('workflow_steps'))
    activities, unmatched = attempt_groups(record, steps)
    columns = {'working': [], 'blocked': [], 'next': [], 'waiting': [], 'review': [], 'done': []}
    for position, (item, attempts) in enumerate(activities):
        content, column = task_card(item, attempts, record)
        date = max((recency_key(attempt)[0] for attempt in attempts), default=float('-inf'))
        columns[column].append((content, position, date))
    columns['next'].sort(key=lambda entry: entry[1])
    for name in ('working', 'blocked', 'waiting', 'review', 'done'):
        columns[name].sort(key=lambda entry: (entry[2], -entry[1]), reverse=True)

    markup = ['<div class="board" aria-label="Current execution board">']
    for key, label in (('next', 'Next'), ('blocked', 'Blocked'), ('working', 'Working now'), ('waiting', 'Waiting'), ('review', 'Review'), ('done', 'Done')):
        entries = columns[key]
        visible = entries[:10] if key == 'next' else entries
        cards = ''.join(entry[0] for entry in visible)
        if key == 'next' and len(entries) > 10:
            remaining_cards = ''.join(entry[0] for entry in entries[10:])
            cards += ('<details class="show-all"><summary>Show all ' + str(len(entries))
                      + ' planned activities (' + str(len(entries) - 10) + ' more)</summary>'
                      + remaining_cards + '</details>')
        if not cards:
            cards = '<p class="empty">No activities in this column.</p>'
        markup.append('<section class="board-column column-' + key + '"><h3>' + label
                      + ' <span class="count">' + str(len(entries)) + '</span></h3>' + cards + '</section>')
    markup.append('</div>')
    if unmatched:
        markup.append('<details class="unmapped"><summary>Attempt records without a matching workflow activity ('
                      + str(len(unmatched)) + ')</summary>'
                      + ''.join(task_attempt_card(attempt) for attempt in sorted(unmatched, key=recency_key, reverse=True))
                      + '</details>')
    return ''.join(markup)


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
        plan = (record.get('plan') or {}).get('path', '')
        link = ('<a class="button" href="' + esc(plan) + '">Open plan / PR ↗</a>'
                if isinstance(plan, str) and plan.startswith(('https://', 'http://')) else '')
        cards.append('<section data-project="' + esc(project) + '"><header class="project-head"><div>'
                     + '<div class="eyebrow">PROJECT</div><h2>' + esc(project.replace('-', ' ').title())
                     + '</h2><p class="muted">Coordinated by <strong>' + esc(coordinator['agent_id'])
                     + '</strong> · ' + esc(coordinator.get('client')) + '</p></div>' + link + '</header>'
                     + board(record)
                     + '<details class="coordination"><summary>Coordination and takeover</summary><p>'
                     + esc(record.get('scheduling')) + '</p><p><strong>Takeover:</strong> '
                     + esc((record.get('transfer') or {}).get('state', 'Not requested').replace('-', ' '))
                     + '</p>' + session_details(coordinator) + '</details>'
                     + '<footer>Snapshot observed ' + esc(readable_time(record.get('updated_at')))
                     + ' · Published ' + esc(readable_time(record.get('published_at'))) + '</footer>'
                     + '<details class="raw"><summary>Technical record</summary><pre>'
                     + esc(json.dumps(record, indent=2)) + '</pre></details></section>')
    options = ''.join('<option value="' + esc(p) + '">' + esc(p.replace('-', ' ').title()) + '</option>'
                      for p in sorted({r['project_id'] for r in records}))
    page = '''<!doctype html><html lang="en"><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Delivery Orchestrator · Project activity</title>
<style>
:root{--ink:#202c38;--muted:#62707b;--line:#dce1e4;--paper:#f8f9fa;--accent:#245e5a}
*{box-sizing:border-box}body{font:14px/1.45 system-ui;margin:0;background:var(--paper);color:var(--ink)}
.top{border-bottom:1px solid var(--line);padding:10px 20px;display:flex;justify-content:space-between;align-items:center}.brand{font-weight:750;letter-spacing:-.5px;font-size:17px}.top span{font-size:12px;color:var(--muted)}
main{max-width:1400px;margin:auto;padding:12px 20px}h1{font-size:19px;letter-spacing:-.3px;margin:0}h2{font-size:19px;letter-spacing:-.3px;margin:2px 0}h3{font-size:14px;margin:0 0 10px}h4{font-size:13px;margin:24px 0 4px}p{margin:5px 0 8px}.muted,footer{color:var(--muted);font-size:12px}
.toolbar{display:flex;justify-content:space-between;align-items:center;gap:12px;margin-bottom:10px}.toolbar p{display:none}select,.button,button{font:inherit;border:1px solid var(--line);border-radius:6px;padding:6px 10px;background:transparent;color:var(--ink)}a{color:var(--accent);overflow-wrap:anywhere}.button{text-decoration:none;font-size:12px;white-space:nowrap}.button:hover,button:hover{background:#edf2f1}button{cursor:pointer}select:focus-visible,a:focus-visible,summary:focus-visible,button:focus-visible{outline:3px solid #71a7a1;outline-offset:3px}
section{border:1px solid var(--line);border-radius:9px;margin:0 0 16px;overflow:hidden;background:#fcfcfc}.project-head{padding:12px 14px;display:flex;justify-content:space-between;align-items:center;gap:12px}.eyebrow{font-size:10px;letter-spacing:1px;font-weight:700;color:var(--muted)}.count,.badge{font-size:11px;background:#edf0f2;padding:2px 6px;border-radius:4px;font-weight:600;display:inline-block}.count{margin-left:4px}.empty{padding:12px;border:1px dashed var(--line);border-radius:6px;color:var(--muted);font-size:12px}.board{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px;padding:0 12px 12px}.board-column{border:1px solid var(--line);border-radius:7px;padding:8px;background:#f7f8f8;min-width:0}.board-column h3{display:flex;justify-content:space-between;align-items:center}.task-card{background:white;border:1px solid var(--line);border-radius:6px;padding:9px;margin:0 0 8px;min-width:0;overflow-wrap:anywhere}.card-title{display:flex;align-items:flex-start;justify-content:space-between;gap:6px;margin-bottom:6px}.card-title strong{font-size:13px;line-height:1.3}.task-card p{font-size:11.5px;margin:4px 0}.task-card .badge{white-space:normal;text-align:left}.status-text{font-weight:700}.status-good{color:#176b45}.status-attention{color:#8a4b00}.status-terminal{color:#545c65}.status-unknown{color:#586674}.attempt-history{border-top:1px solid var(--line);margin-top:7px;padding-top:4px}.attempt-record{border-top:1px solid var(--line);padding:7px 0;font-size:11px;overflow-wrap:anywhere}.attempt-details{display:grid;gap:4px;margin:5px 0 0}.attempt-details>span{font-size:11px}.attempt-details pre{max-height:200px;overflow:auto}.attempt-history details,.attempt-history summary,.agent-details details{font-size:11px}.show-all{grid-column:1/-1;background:white;border:1px solid var(--line);padding:4px 8px;border-radius:6px}.show-all .task-card{max-width:360px}.unmapped{margin:0 12px 12px;padding:4px 8px;background:#fff8e8;border:1px solid #ead6af;border-radius:6px}.history{padding:0 14px 8px}.coordination{padding:4px 14px 10px;border-top:1px solid var(--line)}.agent-details{display:grid;gap:6px;margin-top:6px}details{font-size:12px}summary{cursor:pointer;color:var(--accent);padding:6px 0}code,pre{font:11px/1.5 ui-monospace,monospace;overflow-wrap:anywhere;white-space:pre-wrap}footer{padding:10px 14px;border-top:1px solid var(--line);font-size:11px}.raw{padding:0 14px 10px}.raw summary{color:var(--muted)}.note{font-size:11px;color:var(--muted)}[hidden]{display:none!important}
.task-card>summary.task-summary{padding:0;color:var(--ink)}.task-card>summary.task-summary::marker{color:var(--accent)}.summary-top-row{display:flex;align-items:center;gap:6px;min-width:0;line-height:1.3}.summary-title{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:13px;font-weight:700}.summary-model-badge{flex:none;max-width:52%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;border:1px solid var(--line);border-radius:4px;background:#f2f5f5;padding:1px 5px;color:var(--muted);font-size:10px;line-height:1.4}.summary-meta{display:flex;align-items:center;gap:5px;min-width:0;font-size:11px;line-height:1.3;overflow:hidden;white-space:nowrap}.summary-owner{flex:1 1 auto;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.summary-status{flex:none;font-weight:700}.summary-detail{display:block;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px;line-height:1.3;color:var(--muted)}.task-card[open]>summary.task-summary{padding-bottom:6px;border-bottom:1px solid var(--line)}.task-card-body{padding-top:6px}
.column-next{border-top:3px solid #64748b}.column-next>h3{color:#64748b;background:#f1f5f9;border-radius:4px;padding:5px}
.column-blocked{border-top:3px solid #b42332}.column-blocked>h3{color:#b42332;background:#fff1f2;border-radius:4px;padding:5px}
.column-working{border-top:3px solid #2563eb}.column-working>h3{color:#2563eb;background:#eff6ff;border-radius:4px;padding:5px}
.column-waiting{border-top:3px solid #b77900}.column-waiting>h3{color:#b77900;background:#fffbeb;border-radius:4px;padding:5px}
.column-review{border-top:3px solid #7c3aed}.column-review>h3{color:#7c3aed;background:#f5f3ff;border-radius:4px;padding:5px}
.column-done{border-top:3px solid #16804a}.column-done>h3{color:#16804a;background:#ecfdf3;border-radius:4px;padding:5px}
@media(max-width:1100px){.board{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media(max-width:650px){main{padding:8px}.top{padding:8px 12px}.toolbar{margin-bottom:7px}.toolbar,.project-head{align-items:flex-start;flex-direction:column}.board{grid-template-columns:1fr;padding:0 8px 8px;gap:8px}.board-column{padding:9px}.project-head{padding:10px}.card-title{align-items:flex-start}.top span{display:none}}
</style><div class="top"><div class="brand">Delivery Orchestrator <span> / Project activity</span></div><button onclick="location.reload()">Refresh</button></div>
<main><div class="toolbar"><h1>Current execution horizon</h1><label>Project <select id="project"><option value="">All activity</option>''' + options + '</select></label></div>'
    page += ''.join(cards) or '<p class="empty">No coordinator snapshots published yet.</p>'
    page += '''<p class="note">Snapshot only, not live monitoring. GitHub remains the backlog authority; readiness, dependencies and parallel work are shown only when supplied in the snapshot. Session commands are shown for inspection and are never run here.</p></main><script>document.getElementById('project').onchange=function(){document.querySelectorAll('section[data-project]').forEach(s=>s.hidden=!!this.value&&s.dataset.project!==this.value);};</script></html>'''
    atomic_write(root / 'index.html', page)



def validate_done_sources(record):
    activities, _ = attempt_groups(record, ordered_steps(record.get('workflow_steps')))
    for item, attempts in activities:
        if activity_column(item, attempts) != 'done':
            continue
        current = latest_attempt(attempts) or {}
        if item.get('issue_url') or current.get('issue_url'):
            scope = item.get('completion_scope')
            if scope not in {'step', 'issue'}:
                raise ValueError('Done activity must declare step or issue completion: ' + str(item.get('id')))
            if scope == 'issue' and (item.get('github_issue_state') != 'CLOSED' or not item.get('github_checked_at')):
                raise ValueError('Issue completion requires verified CLOSED GitHub state: ' + str(item.get('id')))
        sources = [item.get(k) or current.get(k) for k in ('issue_url', 'source_url', 'pr_url')]
        sources += [link.get('url') for link in item.get('links') or [] if isinstance(link, dict)]
        if not any(isinstance(url, str) and url.startswith(('https://', 'http://')) for url in sources):
            raise ValueError('Done activity requires a source/evidence link: ' + str(item.get('id') or item.get('title')))


def publish(repo, record):
    validate_done_sources(record)
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
