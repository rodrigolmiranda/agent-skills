#!/usr/bin/env python3
"""Check scheduling-receipt consistency without querying external sources.

This validates the receipt's own coverage and required references. It cannot
prove that a source query was complete, an evidence pointer is true, or a
dependency, conflict, capacity limit, authority hold, or running job is real.
"""
import argparse
from collections import Counter
from datetime import datetime
import json
import importlib.util
import re
from pathlib import Path
import sys
from urllib.parse import urlparse, unquote


DISPOSITIONS = {
    'active', 'dispatched', 'dependency-blocked', 'conflict-blocked',
    'capacity-blocked', 'authority-held', 'coordinator-action',
}
HELD_DISPOSITIONS = {
    'dependency-blocked', 'conflict-blocked', 'capacity-blocked',
    'authority-held', 'coordinator-action',
}
READY_EXCLUSIONS = {'conflict-blocked', 'capacity-blocked', 'authority-held'}
READY_DISPOSITIONS = {'active', 'dispatched'} | READY_EXCLUSIONS
DEPENDENCY_GATES = {'reviewer-approval', 'accepted-integration'}


def reservation_conflicts(leases):
    """Compare supplied literal repo paths and shared resource identities.

    Directory reservations end in '/'. Legacy prose surfaces remain compatible
    but are not mechanically checked; caller must still inspect actual writes.
    """
    errors, held = [], []
    for lease in leases:
        if not isinstance(lease, dict) or lease.get('state') != 'held':
            continue
        paths, resources = lease.get('paths', []), lease.get('resources', [])
        if not isinstance(paths, list) or any(not isinstance(x, str) or not x or x.startswith('/') or any(part in ('.', '..') for part in x.split('/')) or '//' in x or '\\' in x or any(c in x for c in '*?[') for x in paths):
            errors.append('reservation paths must be literal relative paths (directory ends in /)')
            continue
        if paths and not lease.get('repository'):
            errors.append('path reservation requires repository identity')
        if not isinstance(resources, list) or any(not isinstance(x, str) or not x for x in resources):
            errors.append('reservation resources must be nonempty identities')
            continue
        for other in held:
            if other.get('job') == lease.get('job'):
                continue
            shared = set(resources) & set(other.get('resources', []))
            if lease.get('repository') and lease.get('repository') == other.get('repository'):
                for a in paths:
                    for b in other.get('paths', []):
                        if a.rstrip('/') == b.rstrip('/') or (a.endswith('/') and b.startswith(a)) or (b.endswith('/') and a.startswith(b)):
                            shared.add(a)
            if shared:
                errors.append('overlapping held reservations: ' + str(other.get('id')) + ' / ' + str(lease.get('id')) + ': ' + ', '.join(sorted(shared)))
        held.append(lease)
    return errors


def nonempty_text(value):
    return isinstance(value, str) and bool(value.strip())


def evidence_pointer(value):
    if not nonempty_text(value):
        return False
    text = value.strip()
    if text.casefold() in {
        'unknown', 'none', 'n/a', 'todo', 'tbd', 'placeholder',
        'artifact or github url', 'evidence pointer',
    }:
        return False
    try:
        parsed = urlparse(text)
    except ValueError:
        return False
    if parsed.scheme in {'http', 'https'}:
        return bool(parsed.netloc and parsed.path not in {'', '/'})
    if parsed.scheme == 'artifact':
        return bool(parsed.netloc or parsed.path.strip('/'))
    if parsed.scheme == 'file':
        return bool(parsed.path)
    # A bare file name with an extension (e.g. HANDOVER.md) is a local path under the artifact root;
    # validate_local_evidence still requires it to resolve to an existing file.
    return '/' in text or '#' in text or bool(re.fullmatch(r'[\w.-]+\.[A-Za-z0-9]{1,8}', text))


def validate_yield_recovery(receipt, artifact_root):
    """Use Interchange's one recovery-proof contract for native and external work."""
    if not any(isinstance(row, dict) and row.get('disposition') in ('active', 'dispatched')
               for row in receipt.get('items', [])):
        return []
    checked = timestamp(receipt.get('checked_at'))
    if checked is None:
        return ['recovery route needs a valid checked_at']
    helper = Path(__file__).resolve().parents[2] / 'interchange/scripts/relay.py'
    try:
        spec = importlib.util.spec_from_file_location('schedule_recovery_contract', helper)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        errors = module.validate_recovery_route(receipt.get('recovery_route'), checked, artifact_root)
    except (OSError, ImportError, AttributeError) as error:
        return ['recovery validation unavailable: ' + str(error)]
    return ['recovery_route: ' + error for error in errors]


def validate_local_evidence(receipt, artifact_root):
    """Resolve local evidence without fetching remote sources or reading contents."""
    errors = []
    root = Path(artifact_root).resolve() if artifact_root is not None else None
    def check(value, field):
        if not evidence_pointer(value):
            return  # Structural validators report malformed required pointers.
        parsed = urlparse(value)
        if parsed.scheme in ('http', 'https'):
            return
        if root is None:
            errors.append(f'{field}: local evidence requires artifact_root')
            return
        if parsed.scheme == 'artifact':
            path = root / unquote(parsed.netloc + parsed.path)
        elif parsed.scheme == 'file':
            if parsed.netloc not in ('', 'localhost'):
                errors.append(f'{field}: remote file authority is not local evidence')
                return
            path = Path(unquote(parsed.path))
        elif not parsed.scheme:
            path = root / unquote(parsed.path)
        else:
            errors.append(f'{field}: unsupported evidence scheme')
            return
        try:
            resolved = path.resolve()
            if parsed.scheme == 'artifact' and not resolved.is_relative_to(root):
                errors.append(f'{field}: artifact path escapes declared root')
            elif not resolved.is_file():
                errors.append(f'{field}: local evidence file does not exist: {path}')
        except (OSError, ValueError, RuntimeError):
            errors.append(f'{field}: invalid local evidence path')
    checkpoint = receipt.get('checkpoint')
    if isinstance(checkpoint, dict):
        for field in ('assessment_evidence', 'last_progress_evidence', 'source_query', 'hierarchy_evidence'):
            check(checkpoint.get(field), 'checkpoint.' + field)
        recovery = checkpoint.get('recovery')
        if isinstance(recovery, dict):
            for field in ('blocker_recheck', 'authorized_alternatives', 'independent_work'):
                check(recovery.get(field), 'checkpoint.recovery.' + field)
    for collection in ('items', 'write_leases'):
        rows = receipt.get(collection)
        if isinstance(rows, list):
            for index, row in enumerate(rows):
                if isinstance(row, dict):
                    for field in ('evidence', 'supervised_wait'):
                        check(row.get(field), f'{collection}[{index}].{field}')
    graph = receipt.get('dependency_graph')
    if isinstance(graph, dict):
        for collection in ('nodes', 'edges', 'events', 'validation_pauses'):
            rows = graph.get(collection)
            if isinstance(rows, list):
                for index, row in enumerate(rows):
                    if not isinstance(row, dict):
                        continue
                    for field in ('local_link', 'evidence', 'resume_packet', 'blocker_notified_evidence',
                                  'reviewer_handover_evidence', 'writer_completion_evidence',
                                  'ownership_check_evidence', 'ownership_evidence', 'base_evidence',
                                  'release_evidence', 'completion_evidence'):
                        check(row.get(field), f'dependency_graph.{collection}[{index}].{field}')
        review = graph.get('review')
        if isinstance(review, dict):
            for field in ('full_audit_evidence', 'critical_path_evidence'):
                check(review.get(field), 'dependency_graph.review.' + field)
            last_event = review.get('last_event')
            if isinstance(last_event, dict):
                check(last_event.get('evidence'), 'dependency_graph.review.last_event.evidence')
    if receipt.get('source_kind', 'github') == 'files':
        check(receipt.get('scope_url'), 'scope_url')
    return errors


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result if result.tzinfo is not None else None
    except (ValueError, TypeError, AttributeError):
        return None


def validate_progress(receipt, before_yield=False):
    """Require an auditable checkpoint; facts still need independent verification."""
    errors = []
    checkpoint = receipt.get('checkpoint')
    if not isinstance(checkpoint, dict):
        return ['checkpoint is required; an unchanged inventory is not a progress assessment']
    checked = timestamp(receipt.get('checked_at'))
    for field in ('trigger', 'next_owner', 'next_event'):
        if not nonempty_text(checkpoint.get(field)):
            errors.append(f'checkpoint.{field} is required')
    if not evidence_pointer(checkpoint.get('assessment_evidence')):
        errors.append('checkpoint.assessment_evidence must link the current full-scope assessment')
    progress = timestamp(checkpoint.get('last_progress_at'))
    if progress is None or (checked and progress > checked):
        errors.append('checkpoint.last_progress_at must be a timestamp no later than checked_at')
    if not evidence_pointer(checkpoint.get('last_progress_evidence')):
        errors.append('checkpoint.last_progress_evidence is required; polling is not progress')
    for field in ('source_query', 'hierarchy_evidence'):
        if not evidence_pointer(checkpoint.get(field)):
            errors.append(f'checkpoint.{field} must link the complete adopted backlog inventory')
    retrieved = timestamp(checkpoint.get('source_retrieved_at'))
    if retrieved is None or (checked and retrieved > checked):
        errors.append('checkpoint.source_retrieved_at must be a timestamp no later than checked_at')
    count = checkpoint.get('unchanged_checks')
    if type(count) is not int or count < 0:
        errors.append('checkpoint.unchanged_checks must be a non-negative integer')
    elif count >= 2:
        recovery = checkpoint.get('recovery')
        if not isinstance(recovery, dict):
            errors.append('checkpoint.recovery is required after two unchanged checks')
        else:
            for field in ('blocker_recheck', 'authorized_alternatives', 'independent_work'):
                if not evidence_pointer(recovery.get(field)):
                    errors.append(f'checkpoint.recovery.{field} requires evidence')
            due = timestamp(recovery.get('next_check_at'))
            if due is None or (checked and due <= checked):
                errors.append('checkpoint.recovery.next_check_at must be after checked_at')
    leases = receipt.get('write_leases')
    if not isinstance(leases, list):
        errors.append('write_leases must list current reservations, including an empty list')
        leases = []
    lease_ids = set()
    for lease in leases:
        if not isinstance(lease, dict):
            errors.append('write lease must be an object')
            continue
        lease_id = lease.get('id')
        if not nonempty_text(lease_id) or lease_id in lease_ids:
            errors.append('write lease IDs must be non-empty and unique')
        else:
            lease_ids.add(lease_id)
        for field in ('owner', 'job', 'surface'):
            if not nonempty_text(lease.get(field)):
                errors.append(f'write lease {field} is required')
        if not evidence_pointer(lease.get('evidence')):
            errors.append('write lease evidence is required')
        if lease.get('state') == 'held':
            if lease.get('writer_state') not in ('running', 'startup', 'unknown'):
                errors.append('stopped writer cannot retain a held write lease; reconcile and release')
            due = timestamp(lease.get('recheck_at'))
            if due is None or (checked and due <= checked):
                errors.append('held write lease is overdue or lacks recheck_at; verify ownership, never auto-release')
        elif lease.get('state') != 'released':
            errors.append('write lease state must be held or released')
    errors.extend(reservation_conflicts(leases))
    held_ids = {x.get('id') for x in leases if isinstance(x, dict) and x.get('state') == 'held' and nonempty_text(x.get('id'))}
    for item in receipt.get('items', []) if isinstance(receipt.get('items'), list) else []:
        if not isinstance(item, dict):
            continue
        if item.get('disposition') == 'conflict-blocked':
            if not nonempty_text(item.get('conflict_surface')):
                errors.append('conflict-blocked item requires the concrete file/contract/runtime conflict_surface')
            if item.get('write_lease') is not None and (not nonempty_text(item.get('write_lease')) or item.get('write_lease') not in held_ids):
                errors.append('conflict references a released or absent write lease')
        if item.get('disposition') == 'coordinator-action' and (before_yield or checkpoint.get('trigger') == 'yield'):
            if not evidence_pointer(item.get('supervised_wait')):
                errors.append('yield leaves an executable coordinator-action without supervised wait evidence')
    return errors


def _valid_github_link(value):
    if not nonempty_text(value):
        return False
    try:
        parsed = urlparse(value)
    except ValueError:
        return False
    return parsed.scheme == 'https' and bool(parsed.netloc and parsed.path not in ('', '/'))


def _positive_minutes(value):
    return type(value) is int and 1 <= value <= 10080


def _surfaces_overlap(left, right):
    return (left == right or
            (left.endswith('/') and right.startswith(left)) or
            (right.endswith('/') and left.startswith(right)))


def validate_dependency_graph(receipt):
    """Validate graph coverage, paired links, and event-backed release records."""
    errors = []
    graph = receipt.get('dependency_graph')
    required = receipt.get('dependency_graph_required')
    if required is not None and type(required) is not bool:
        errors.append('dependency_graph_required must be true or false')
    if not isinstance(graph, dict):
        if required is True:
            errors.append('dependency_graph is required when dependency_graph_required is true')
        return errors
    if required is not True:
        errors.append('dependency_graph_required must be true when a graph is supplied')
    if graph.get('complete') is not True:
        errors.append('dependency_graph.complete must be true; unknown coverage cannot be certified')

    raw_source_ids = receipt.get('source_ids')
    source_ids = set(x for x in (raw_source_ids if isinstance(raw_source_ids, list) else []) if nonempty_text(x))
    nodes = graph.get('nodes')
    if not isinstance(nodes, list):
        errors.append('dependency_graph.nodes must list every approved unfinished item and prerequisite')
        nodes = []
    node_by_id, node_scope = {}, set()
    for index, node in enumerate(nodes):
        prefix = f'dependency_graph.nodes[{index}]'
        if not isinstance(node, dict):
            errors.append(f'{prefix} must be an object')
            continue
        node_id = node.get('id')
        if not nonempty_text(node_id) or node_id != node_id.strip():
            errors.append(f'{prefix}.id must be a non-empty trimmed string')
            continue
        if node_id in node_by_id:
            errors.append(f'dependency_graph.nodes contains duplicate ID {node_id!r}')
            continue
        node_by_id[node_id] = node
        state = node.get('state')
        if state not in ('unfinished', 'complete'):
            errors.append(f'{prefix}.state must be unfinished or complete')
        if state == 'unfinished':
            node_scope.add(node_id)
        for field in ('local_link', 'github_link'):
            value = node.get(field)
            if field == 'local_link' and not evidence_pointer(value):
                errors.append(f'{prefix}.{field} must link the local task record')
            if field == 'github_link' and not _valid_github_link(value):
                errors.append(f'{prefix}.{field} must link the matching GitHub issue')
        if state == 'complete':
            if timestamp(node.get('completed_at')) is None:
                errors.append(f'{prefix}.completed_at must timestamp a completed prerequisite')
            if not evidence_pointer(node.get('completion_evidence')):
                errors.append(f'{prefix}.completion_evidence must prove the completed prerequisite')
        surfaces = node.get('surfaces')
        if state == 'unfinished' and (not isinstance(surfaces, list) or not surfaces or
                any(not nonempty_text(surface) for surface in surfaces)):
            errors.append(f'{prefix}.surfaces must list the concrete write surfaces for unfinished work')
        if not isinstance(node.get('depends_on'), list) or any(not nonempty_text(x) for x in node.get('depends_on', [])):
            errors.append(f'{prefix}.depends_on must be an array of dependency IDs')

    if node_scope != source_ids:
        errors.append('dependency_graph unfinished node IDs must exactly match source_ids')
    for node_id, node in node_by_id.items():
        for dependency_id in node.get('depends_on', []) if isinstance(node.get('depends_on'), list) else []:
            if not nonempty_text(dependency_id):
                continue
            if dependency_id not in node_by_id:
                errors.append(f'node {node_id} depends_on unknown graph node {dependency_id}')
            elif node_by_id[dependency_id].get('state') != 'unfinished' and node_by_id[dependency_id].get('state') != 'complete':
                errors.append(f'node {node_id} depends_on node {dependency_id} with unknown state')

    raw_items = receipt.get('items')
    items = {item.get('id'): item for item in (raw_items if isinstance(raw_items, list) else [])
             if isinstance(item, dict) and nonempty_text(item.get('id'))}
    edges = graph.get('edges')
    if not isinstance(edges, list):
        errors.append('dependency_graph.edges must be an array, including when empty')
        edges = []
    edge_by_id, incoming_dependencies = {}, {}
    for index, edge in enumerate(edges):
        prefix = f'dependency_graph.edges[{index}]'
        if not isinstance(edge, dict):
            errors.append(f'{prefix} must be an object')
            continue
        edge_id = edge.get('id')
        if not nonempty_text(edge_id) or edge_id in edge_by_id:
            errors.append('dependency graph edge IDs must be non-empty and unique')
        else:
            edge_by_id[edge_id] = edge
        for field in ('from', 'to'):
            if not nonempty_text(edge.get(field)) or edge.get(field) not in node_by_id:
                errors.append(f'{prefix}.{field} must identify a graph node')
        if edge.get('state') not in ('verified', 'stale', 'unknown'):
            errors.append(f'{prefix}.state must be verified, stale, or unknown')
        if not _valid_github_link(edge.get('github_link')):
            errors.append(f'{prefix}.github_link must link the GitHub relationship source')
        if not evidence_pointer(edge.get('local_link')):
            errors.append(f'{prefix}.local_link must link the local relationship record')
        kind = edge.get('kind')
        if kind == 'dependency':
            endpoints_valid = all(nonempty_text(edge.get(field)) and edge.get(field) in node_by_id for field in ('from', 'to'))
            blocker_unfinished = (endpoints_valid and
                                  node_by_id[edge.get('from')].get('state') == 'unfinished')
            requires_release_contract = edge.get('satisfied') is False or blocker_unfinished
            if edge.get('blocker_task_id') != edge.get('from') or edge.get('dependent_task_id') != edge.get('to'):
                errors.append(f'{prefix} must name its blocker_task_id and dependent_task_id consistently')
            if endpoints_valid:
                incoming_dependencies.setdefault(edge.get('to'), set()).add(edge.get('from'))
            if type(edge.get('satisfied')) is not bool:
                errors.append(f'{prefix}.satisfied must be true or false')
            if requires_release_contract:
                if not nonempty_text(edge.get('gate_type')) or edge.get('gate_type') not in DEPENDENCY_GATES:
                    errors.append(f'{prefix}.gate_type must be reviewer-approval or accepted-integration')
                for field in ('blocker_notified_evidence', 'reviewer_handover_evidence', 'resume_packet', 'unblock_condition'):
                    if not evidence_pointer(edge.get(field)) and field != 'unblock_condition':
                        errors.append(f'{prefix}.{field} must link the durable blocker/dependent handover')
                    if field == 'unblock_condition' and not nonempty_text(edge.get(field)):
                        errors.append(f'{prefix}.{field} must state the release gate')
                handover_ids = edge.get('reviewer_handover_dependent_ids')
                if (not isinstance(handover_ids, list) or
                        any(not nonempty_text(task_id) for task_id in handover_ids) or
                        edge.get('to') not in handover_ids):
                    errors.append(f'{prefix}.reviewer_handover_dependent_ids must carry the dependent task ID')
        elif kind == 'conflict':
            if edge.get('blocking_task_id') != edge.get('from') or edge.get('deferred_task_id') != edge.get('to'):
                errors.append(f'{prefix} must name its blocking_task_id and deferred_task_id consistently')
            surface = edge.get('surface')
            if not nonempty_text(surface):
                errors.append(f'{prefix}.surface must name the exact conflicting path, contract, or resource')
            lifecycle = edge.get('lifecycle')
            if lifecycle not in ('open', 'released'):
                errors.append(f'{prefix}.lifecycle must be open or released')
            if not nonempty_text(edge.get('write_lease_id')):
                errors.append(f'{prefix}.write_lease_id must identify the writer reservation')
            if lifecycle == 'released':
                for field in ('writer_completed_at', 'ownership_checked_at'):
                    if timestamp(edge.get(field)) is None:
                        errors.append(f'{prefix}.{field} must be a valid timestamp')
                for field in ('writer_completion_evidence', 'ownership_check_evidence'):
                    if not evidence_pointer(edge.get(field)):
                        errors.append(f'{prefix}.{field} must link verified completion or ownership evidence')
                if not nonempty_text(edge.get('release_event_id')):
                    errors.append(f'{prefix}.release_event_id must identify the verified release event')
                if edge.get('ownership_check_type') != 'actual-owner-verified':
                    errors.append(f'{prefix}.ownership_check_type must record an actual current ownership check')
                if edge.get('state') != 'verified':
                    errors.append(f'{prefix} cannot release a stale or unknown conflict edge')
                completed = timestamp(edge.get('writer_completed_at'))
                ownership_checked = timestamp(edge.get('ownership_checked_at'))
                if completed and ownership_checked and ownership_checked <= completed:
                    errors.append(f'{prefix}.ownership_checked_at must follow verified writer completion')
        else:
            errors.append(f'{prefix}.kind must be dependency or conflict')

    for node_id, node in node_by_id.items():
        declared = set(task_id for task_id in node.get('depends_on', [])
                       if nonempty_text(task_id)) if isinstance(node.get('depends_on'), list) else set()
        actual = incoming_dependencies.get(node_id, set())
        if declared != actual:
            errors.append(f'node {node_id} local depends_on links do not match graph edges')
    for edge in edges:
        if not isinstance(edge, dict) or edge.get('kind') != 'dependency':
            continue
        blocker = node_by_id.get(edge.get('from')) if nonempty_text(edge.get('from')) else None
        requires_release_contract = (edge.get('satisfied') is False or
                                    (isinstance(blocker, dict) and blocker.get('state') == 'unfinished'))
        if not requires_release_contract:
            continue
        if edge.get('gate_type') == 'reviewer-approval':
            expected = {candidate.get('to') for candidate in edges if isinstance(candidate, dict) and nonempty_text(candidate.get('to')) and
                        candidate.get('kind') == 'dependency' and candidate.get('from') == edge.get('from') and
                        candidate.get('gate_type') == 'reviewer-approval' and
                        (candidate.get('satisfied') is False or
                         node_by_id.get(candidate.get('from'), {}).get('state') == 'unfinished')}
            handover_ids = edge.get('reviewer_handover_dependent_ids', [])
            handover_set = set(task_id for task_id in handover_ids if nonempty_text(task_id)) if isinstance(handover_ids, list) else set()
            if handover_set != expected:
                errors.append(f'dependency edge {edge.get("id")} reviewer handover must carry every held dependent ID')

    raw_leases = receipt.get('write_leases')
    leases = {lease.get('id'): lease for lease in (raw_leases if isinstance(raw_leases, list) else [])
              if isinstance(lease, dict) and nonempty_text(lease.get('id'))}
    for edge_id, edge in edge_by_id.items():
        if edge.get('kind') != 'conflict':
            continue
        lease_id = edge.get('write_lease_id')
        lease = leases.get(lease_id) if nonempty_text(lease_id) else None
        lifecycle = edge.get('lifecycle')
        expected_lease_state = 'held' if lifecycle == 'open' else 'released'
        if lease is None or lease.get('state') != expected_lease_state:
            errors.append(f'conflict edge {edge_id} must match a {expected_lease_state} writer reservation')
            continue
        writer_id = edge.get('from')
        writer = items.get(writer_id) if nonempty_text(writer_id) else None
        if writer is not None and nonempty_text(lease.get('job')) and lease.get('job') != writer.get('job'):
            errors.append(f'conflict edge {edge_id} reservation must belong to its blocking writer task')
        surface = edge.get('surface')
        lease_paths = lease.get('paths') if isinstance(lease.get('paths'), list) else []
        lease_resources = lease.get('resources') if isinstance(lease.get('resources'), list) else []
        reserved = {value for value in lease_paths if nonempty_text(value)} | {value for value in lease_resources if nonempty_text(value)}
        if not nonempty_text(surface) or surface not in reserved:
            errors.append(f'conflict edge {edge_id} surface must match the blocking writer reservation')
        for task_id in (edge.get('from'), edge.get('to')):
            if not nonempty_text(task_id):
                continue
            task_surfaces = node_by_id.get(task_id, {}).get('surfaces', [])
            if (not nonempty_text(surface) or not isinstance(task_surfaces, list) or
                    not any(_surfaces_overlap(surface, candidate) for candidate in task_surfaces if nonempty_text(candidate))):
                errors.append(f'conflict edge {edge_id} surface must be declared on both linked tasks')
        if lifecycle == 'released':
            writer_node = node_by_id.get(edge.get('from'))
            completed = timestamp(edge.get('writer_completed_at'))
            node_completed = timestamp(writer_node.get('completed_at')) if isinstance(writer_node, dict) else None
            if not isinstance(writer_node, dict) or writer_node.get('state') != 'complete':
                errors.append(f'conflict edge {edge_id} cannot release until its blocking writer task is complete')
            elif completed is None or node_completed != completed:
                errors.append(f'conflict edge {edge_id} writer completion must match the completed graph node')
            graph_events = graph.get('events') if isinstance(graph.get('events'), list) else []
            release_event = next((event for event in graph_events if isinstance(event, dict) and event.get('event_id') == edge.get('release_event_id')), None)
            if not isinstance(release_event, dict) or release_event.get('kind') != 'conflict-released' or release_event.get('edge_id') != edge_id:
                errors.append(f'conflict edge {edge_id} requires its unique conflict-released event')
            else:
                release_at = timestamp(release_event.get('observed_at'))
                ownership_at = timestamp(edge.get('ownership_checked_at'))
                if release_at is None or ownership_at is None or release_at <= ownership_at:
                    errors.append(f'conflict edge {edge_id} release event must follow the actual ownership check')

    review = graph.get('review')
    if not isinstance(review, dict):
        errors.append('dependency_graph.review is required for incremental and full-audit cadence')
    else:
        for field in ('event_interval_minutes', 'full_audit_interval_minutes'):
            if not _positive_minutes(review.get(field)):
                errors.append(f'dependency_graph.review.{field} must be a positive configurable minute interval')
        checked = timestamp(receipt.get('checked_at'))
        full_audit_at = timestamp(review.get('last_full_audit_at'))
        if full_audit_at is None or (checked and full_audit_at > checked):
            errors.append('dependency_graph.review.last_full_audit_at must be no later than checked_at')
        for field in ('full_audit_evidence', 'critical_path_evidence'):
            if not evidence_pointer(review.get(field)):
                errors.append(f'dependency_graph.review.{field} must link the full graph and critical-path audit')
        incremental_at = timestamp(review.get('incremental_at'))
        if incremental_at is None or (checked and incremental_at > checked):
            errors.append('dependency_graph.review.incremental_at must be no later than checked_at')
        last_event = review.get('last_event')
        if last_event is None:
            errors.append('dependency_graph.review.last_event is required for incremental event scheduling')
        else:
            if not isinstance(last_event, dict):
                errors.append('dependency_graph.review.last_event must be an object')
            else:
                event_at = timestamp(last_event.get('occurred_at'))
                event_checked_at = timestamp(last_event.get('checked_at'))
                if not nonempty_text(last_event.get('event_id')) or not nonempty_text(last_event.get('kind')):
                    errors.append('dependency_graph.review.last_event requires event_id and kind')
                if not evidence_pointer(last_event.get('evidence')):
                    errors.append('dependency_graph.review.last_event.evidence is required')
                if event_at is None or event_checked_at is None or (checked and event_checked_at > checked) or (event_at and event_checked_at and event_checked_at < event_at):
                    errors.append('dependency_graph.review.last_event timestamps are invalid')
                if event_checked_at and incremental_at and event_checked_at > incremental_at:
                    errors.append('incremental_at must include the latest material event reassessment')
                interval = review.get('event_interval_minutes')
                if event_at and event_checked_at and _positive_minutes(interval) and (event_checked_at - event_at).total_seconds() > interval * 60:
                    errors.append('material event was not incrementally reassessed within the configured interval')
                affected = last_event.get('affected_ids')
                if not isinstance(affected, list) or any(not nonempty_text(task_id) or task_id not in node_by_id for task_id in affected):
                    errors.append('dependency_graph.review.last_event.affected_ids must name graph nodes')

    events = graph.get('events', [])
    if not isinstance(events, list):
        errors.append('dependency_graph.events must be an array, including when empty')
        events = []
    event_by_id, reactivated = {}, set()
    reassessed_releases = {}
    for index, event in enumerate(events):
        prefix = f'dependency_graph.events[{index}]'
        if not isinstance(event, dict):
            errors.append(f'{prefix} must be an object')
            continue
        event_id = event.get('event_id')
        if not nonempty_text(event_id) or event_id in event_by_id:
            errors.append('dependency graph event IDs must be non-empty and unique')
        else:
            event_by_id[event_id] = event
        if timestamp(event.get('observed_at')) is None:
            errors.append(f'{prefix}.observed_at must be a valid timestamp')
        observed_at = timestamp(event.get('observed_at'))
        checked_at = timestamp(receipt.get('checked_at'))
        if observed_at and checked_at and observed_at > checked_at:
            errors.append(f'{prefix}.observed_at cannot be later than receipt.checked_at')
        if not evidence_pointer(event.get('evidence')):
            errors.append(f'{prefix}.evidence must link the event proof')
        if event.get('kind') == 'review-verdict':
            blocker_id = event.get('blocking_task_id')
            if not nonempty_text(blocker_id) or blocker_id not in node_by_id or event.get('review_verdict') not in ('APPROVED', 'CHANGES_NEEDED', 'NOT_ASSESSABLE'):
                errors.append(f'{prefix} must identify a blocker and a recognized review verdict')
            if not nonempty_text(event.get('reviewed_head')) or not nonempty_text(event.get('expected_head')) or type(event.get('head_current')) is not bool:
                errors.append(f'{prefix} must record the reviewed and expected heads plus current-head status')
            held_ids = event.get('held_dependent_task_ids')
            reactivated_edges = {candidate.get('edge_id') for candidate in events if isinstance(candidate, dict) and
                                 nonempty_text(candidate.get('edge_id')) and candidate.get('kind') == 'dependency-reactivated' and
                                 candidate.get('source_event_id') == event_id}
            expected = sorted(edge.get('to') for edge in edges if isinstance(edge, dict) and edge.get('kind') == 'dependency' and nonempty_text(edge.get('to')) and
                              edge.get('from') == blocker_id and edge.get('gate_type') == 'reviewer-approval' and
                              (edge.get('satisfied') is False or edge.get('id') in reactivated_edges))
            if (not isinstance(held_ids, list) or
                    any(not nonempty_text(task_id) for task_id in held_ids) or
                    sorted(set(task_id for task_id in held_ids if nonempty_text(task_id))) != expected):
                errors.append(f'{prefix}.held_dependent_task_ids must match the declared reviewer-gated dependents')
        elif event.get('kind') == 'conflict-released':
            edge_id = event.get('edge_id')
            edge = edge_by_id.get(edge_id) if nonempty_text(edge_id) else None
            if (not isinstance(edge, dict) or edge.get('kind') != 'conflict' or
                    event.get('blocking_task_id') != edge.get('from') or
                    event.get('deferred_task_id') != edge.get('to') or
                    event.get('surface') != edge.get('surface')):
                errors.append(f'{prefix}.edge_id must identify a conflict edge')
        elif event.get('kind') == 'conflict-discovered':
            edge_id = event.get('edge_id')
            edge = edge_by_id.get(edge_id) if nonempty_text(edge_id) else None
            if (not isinstance(edge, dict) or edge.get('kind') != 'conflict' or
                    event.get('surface') != edge.get('surface') or
                    event.get('blocking_task_id') != edge.get('from') or
                    event.get('deferred_task_id') != edge.get('to')):
                errors.append(f'{prefix} must identify both task IDs and the exact conflict surface')
        elif event.get('kind') == 'integration-accepted':
            blocker_id = event.get('blocking_task_id')
            if not nonempty_text(event.get('integrated_ref')):
                errors.append(f'{prefix}.integrated_ref must identify the accepted integration revision')
            reactivated_edges = {candidate.get('edge_id') for candidate in events if isinstance(candidate, dict) and
                                 nonempty_text(candidate.get('edge_id')) and candidate.get('kind') == 'dependency-reactivated' and
                                 candidate.get('source_event_id') == event_id}
            expected = sorted(edge.get('to') for edge in edges if isinstance(edge, dict) and nonempty_text(edge.get('to')) and edge.get('kind') == 'dependency' and
                              edge.get('from') == blocker_id and edge.get('gate_type') == 'accepted-integration' and
                              (edge.get('satisfied') is False or edge.get('id') in reactivated_edges))
            held_ids = event.get('held_dependent_task_ids')
            if (not nonempty_text(blocker_id) or blocker_id not in node_by_id or not isinstance(held_ids, list) or
                    any(not nonempty_text(task_id) for task_id in held_ids) or
                    sorted(set(task_id for task_id in held_ids if nonempty_text(task_id))) != expected):
                errors.append(f'{prefix} must identify the integrated blocker and its held dependents')
        elif event.get('kind') == 'successor-reassessed':
            release_id = event.get('release_event_id')
            if not nonempty_text(release_id) or release_id in reassessed_releases:
                errors.append(f'{prefix} must reassess one release event exactly once')
            else:
                reassessed_releases[release_id] = event
            if not nonempty_text(event.get('task_id')) or event.get('task_id') not in source_ids or event.get('result_disposition') not in DISPOSITIONS:
                errors.append(f'{prefix} must record the successor task and its new disposition')
        elif event.get('kind') == 'resume-assessment':
            if not nonempty_text(event.get('task_id')) or event.get('task_id') not in source_ids:
                errors.append(f'{prefix}.task_id must identify an approved dependent task')
            if type(event.get('ownership_verified')) is not bool or type(event.get('base_safe')) is not bool:
                errors.append(f'{prefix} must record boolean ownership and source/base assessment results')
            for field in ('ownership_evidence', 'base_evidence'):
                if not evidence_pointer(event.get(field)):
                    errors.append(f'{prefix}.{field} must link current ownership/base proof')
        elif event.get('kind') == 'dependency-reactivated':
            generation = event.get('generation')
            if not nonempty_text(event.get('edge_id')) or not nonempty_text(event.get('task_id')) or type(generation) is not int or generation < 1:
                errors.append(f'{prefix} requires edge/task IDs and a positive integer generation')
            else:
                key = (event.get('edge_id'), event.get('task_id'), generation)
                if key in reactivated:
                    errors.append(f'{prefix} repeats dependency reactivation; each event may resume its task once')
                reactivated.add(key)
            if not isinstance(generation, int) or generation < 1:
                errors.append(f'{prefix}.generation must be a positive integer')
        elif event.get('kind') not in ('conflict-discovered', 'integration-accepted', 'resume-assessment', 'dependency-reactivated'):
            errors.append(f'{prefix}.kind is unknown: {event.get("kind")!r}')

    for edge_id, edge in edge_by_id.items():
        if edge.get('kind') == 'conflict':
            discovery = event_by_id.get(edge.get('discovery_event_id'))
            if not isinstance(discovery, dict) or discovery.get('kind') != 'conflict-discovered' or discovery.get('edge_id') != edge_id:
                errors.append(f'conflict edge {edge_id} requires its unique conflict-discovered event')

    for edge_id, edge in edge_by_id.items():
        if edge.get('kind') == 'dependency' and nonempty_text(edge.get('gate_type')) and edge.get('gate_type') in DEPENDENCY_GATES:
            dependent_id = edge.get('to')
            matching = [event for event in events if isinstance(event, dict) and event.get('kind') == 'dependency-reactivated' and event.get('edge_id') == edge_id and event.get('task_id') == dependent_id]
            if edge.get('satisfied') is True and matching:
                reactivation = matching[0]
                source_event_id = reactivation.get('source_event_id')
                assessment_event_id = reactivation.get('assessment_event_id')
                source_event = event_by_id.get(source_event_id) if nonempty_text(source_event_id) else None
                assessment = event_by_id.get(assessment_event_id) if nonempty_text(assessment_event_id) else None
                allowed_source = ('review-verdict' if edge.get('gate_type') == 'reviewer-approval' else 'integration-accepted')
                blocker_id = edge.get('from')
                if not isinstance(source_event, dict) or source_event.get('kind') != allowed_source or source_event.get('blocking_task_id') != blocker_id:
                    errors.append(f'dependency edge {edge_id} requires the declared gate event; review approval cannot release integration gates')
                if edge.get('gate_type') == 'reviewer-approval' and (not isinstance(source_event, dict) or source_event.get('review_verdict') != 'APPROVED' or edge.get('to') not in source_event.get('held_dependent_task_ids', [])):
                    errors.append(f'dependency edge {edge_id} requires its exact-head APPROVED blocker event')
                if edge.get('gate_type') == 'reviewer-approval' and (not isinstance(source_event, dict) or source_event.get('reviewed_head') != source_event.get('expected_head') or source_event.get('head_current') is not True):
                    errors.append(f'dependency edge {edge_id} requires a current exact-head APPROVED blocker event')
                if not isinstance(assessment, dict) or assessment.get('kind') != 'resume-assessment' or assessment.get('task_id') != dependent_id:
                    errors.append(f'dependency edge {edge_id} requires a fresh ownership/base resume assessment')
                if isinstance(assessment, dict) and (assessment.get('ownership_verified') is not True or assessment.get('base_safe') is not True):
                    errors.append(f'dependency edge {edge_id} cannot reactivate until ownership and base are verified safe')
                if isinstance(assessment, dict) and isinstance(source_event, dict) and assessment.get('source_event_id') != source_event.get('event_id'):
                    errors.append(f'dependency edge {edge_id} resume assessment must match its exact unblock event')
                if isinstance(assessment, dict) and isinstance(source_event, dict):
                    assessment_at = timestamp(assessment.get('observed_at'))
                    source_at = timestamp(source_event.get('observed_at'))
                    resumed_at = timestamp(reactivation.get('observed_at'))
                    if (assessment_at is None or source_at is None or resumed_at is None or
                            assessment_at < source_at or resumed_at < assessment_at):
                        errors.append(f'dependency edge {edge_id} must record review, safety assessment, then reactivation in order')
                    selected_at = timestamp(items.get(dependent_id, {}).get('selected_at')) if nonempty_text(dependent_id) else None
                    if selected_at is None or (resumed_at and selected_at < resumed_at):
                        errors.append(f'dependency edge {edge_id} dependent dispatch must follow its reactivation event')
                if len(matching) != 1:
                    errors.append(f'dependency edge {edge_id} must have exactly one reactivation event per receipt')
            elif edge.get('satisfied') is True and edge.get('gate_type') in DEPENDENCY_GATES:
                errors.append(f'dependency edge {edge_id} cannot certify gate release without one reactivation event')

    for edge_id, edge in edge_by_id.items():
        if edge.get('kind') == 'conflict' and edge.get('lifecycle') == 'released':
            release_id = edge.get('release_event_id')
            reassessment = reassessed_releases.get(release_id) if nonempty_text(release_id) else None
            dependent_id = edge.get('to')
            if not isinstance(reassessment, dict) or reassessment.get('task_id') != dependent_id:
                errors.append(f'conflict edge {edge_id} requires exactly one successor reassessment after verified release')
            elif reassessment.get('result_disposition') != items.get(dependent_id, {}).get('disposition'):
                errors.append(f'conflict edge {edge_id} successor reassessment must match the current disposition')
            release_event = event_by_id.get(release_id) if nonempty_text(release_id) else None
            if isinstance(reassessment, dict) and isinstance(release_event, dict):
                reassessment_at = timestamp(reassessment.get('observed_at'))
                release_at = timestamp(release_event.get('observed_at'))
                if reassessment_at is None or release_at is None or reassessment_at < release_at:
                    errors.append(f'conflict edge {edge_id} successor reassessment must follow the verified release')
                if reassessment.get('result_disposition') in ('active', 'dispatched'):
                    dependent_id = edge.get('to')
                    successor = items.get(dependent_id, {}) if nonempty_text(dependent_id) else {}
                    selected_at = timestamp(successor.get('selected_at'))
                    if selected_at is None or (reassessment_at and selected_at < reassessment_at):
                        errors.append(f'conflict edge {edge_id} safe successor dispatch must follow its reassessment')

    pauses = graph.get('validation_pauses')
    if not isinstance(pauses, list):
        errors.append('dependency_graph.validation_pauses must be an array, including when empty')
        pauses = []
    for index, pause in enumerate(pauses):
        prefix = f'dependency_graph.validation_pauses[{index}]'
        if not isinstance(pause, dict):
            errors.append(f'{prefix} must be an object')
            continue
        if not nonempty_text(pause.get('id')) or not nonempty_text(pause.get('kind')):
            errors.append(f'{prefix} requires an ID and validation kind')
        if pause.get('state') not in ('active', 'released'):
            errors.append(f'{prefix}.state must be active or released')
        affected = pause.get('affected_ids')
        surfaces = pause.get('surfaces')
        if not isinstance(affected, list) or not affected or any(not nonempty_text(task_id) or task_id not in node_by_id for task_id in affected):
            errors.append(f'{prefix}.affected_ids must identify the affected approved tasks')
        if not isinstance(surfaces, list) or not surfaces or any(not nonempty_text(surface) for surface in surfaces):
            errors.append(f'{prefix}.surfaces must list the affected surfaces')
        if not evidence_pointer(pause.get('evidence')):
            errors.append(f'{prefix}.evidence must link the UX/E2E or validation finding')
        if pause.get('state') == 'released' and not evidence_pointer(pause.get('release_evidence')):
            errors.append(f'{prefix}.release_evidence is required before the affected surface resumes')
    return errors


def validate_graph_dispatch(receipt):
    """Reject selected tasks with unresolved relationships or affected validation holds."""
    graph = receipt.get('dependency_graph')
    if not isinstance(graph, dict):
        return []
    errors = []
    raw_items = receipt.get('items')
    raw_nodes = graph.get('nodes')
    raw_edges = graph.get('edges')
    raw_leases = receipt.get('write_leases')
    raw_pauses = graph.get('validation_pauses')
    items = {item.get('id'): item for item in (raw_items if isinstance(raw_items, list) else [])
             if isinstance(item, dict) and nonempty_text(item.get('id'))}
    nodes = {node.get('id'): node for node in (raw_nodes if isinstance(raw_nodes, list) else [])
             if isinstance(node, dict) and nonempty_text(node.get('id'))}
    edges = [edge for edge in raw_edges if isinstance(edge, dict)] if isinstance(raw_edges, list) else []
    leases = {lease.get('id'): lease for lease in (raw_leases if isinstance(raw_leases, list) else [])
              if isinstance(lease, dict) and nonempty_text(lease.get('id'))}
    pauses = raw_pauses if isinstance(raw_pauses, list) else []
    selected_surfaces = []
    for item_id, item in items.items():
        if item.get('disposition') == 'dependency-blocked':
            blockers = [edge for edge in edges if edge.get('kind') == 'dependency' and edge.get('to') == item_id and
                        (edge.get('state') != 'verified' or edge.get('satisfied') is not True)]
            if not blockers:
                errors.append(f'{item_id} is dependency-blocked without a stale, unknown, or unsatisfied dependency edge')
        if item.get('disposition') == 'conflict-blocked':
            conflict_surface = item.get('conflict_surface')
            blockers = [edge for edge in edges if edge.get('kind') == 'conflict' and edge.get('to') == item_id and
                        edge.get('lifecycle') == 'open' and edge.get('surface') == conflict_surface]
            if not blockers:
                errors.append(f'{item_id} is conflict-blocked without a matching open conflict edge')
        if item.get('disposition') not in ('active', 'dispatched'):
            continue
        node = nodes.get(item_id, {})
        raw_surfaces = node.get('surfaces')
        node_surfaces = {surface for surface in raw_surfaces if nonempty_text(surface)} if isinstance(raw_surfaces, list) else set()
        for surface in node_surfaces:
            for other_surface, other_id in selected_surfaces:
                if other_id != item_id and _surfaces_overlap(surface, other_surface):
                    errors.append(f'{item_id} and {other_id} are selected writers for overlapping surface {surface}')
            selected_surfaces.append((surface, item_id))
        for edge in edges:
            if edge.get('kind') == 'dependency' and edge.get('to') == item_id:
                if edge.get('state') != 'verified' or edge.get('satisfied') is not True:
                    errors.append(f'{item_id} is dispatchable only when every incoming dependency edge is verified and satisfied')
            if edge.get('kind') == 'conflict' and item_id in (edge.get('from'), edge.get('to')):
                if edge.get('lifecycle') == 'open' and edge.get('to') == item_id:
                    errors.append(f'{item_id} is dispatchable only after its conflict surface and writer are verified/released')
                if (edge.get('lifecycle') == 'open' and edge.get('from') == item_id and
                        edge.get('state') in ('unknown', 'stale') and item.get('disposition') != 'active'):
                    errors.append(f'{item_id} cannot be newly dispatched while its discovered conflict edge is stale or unknown')
                if (edge.get('lifecycle') == 'open' and edge.get('from') == item_id and
                        edge.get('state') in ('unknown', 'stale') and item.get('disposition') == 'active'):
                    lease = leases.get(edge.get('write_lease_id'))
                    if not isinstance(lease, dict) or lease.get('state') != 'held' or lease.get('writer_state') != 'running':
                        errors.append(f'{item_id} cannot continue writing while current ownership is unknown')
        for pause in pauses:
            if not isinstance(pause, dict) or pause.get('state') != 'active':
                continue
            affected_ids = pause.get('affected_ids') if isinstance(pause.get('affected_ids'), list) else []
            pause_surfaces = {surface for surface in pause.get('surfaces', []) if nonempty_text(surface)} if isinstance(pause.get('surfaces'), list) else set()
            if (item_id in affected_ids or
                    any(_surfaces_overlap(task_surface, pause_surface)
                        for task_surface in node_surfaces for pause_surface in pause_surfaces)):
                errors.append(f'{item_id} is dispatchable while its affected surface has an active UX/E2E validation pause')
        review = graph.get('review') if isinstance(graph.get('review'), dict) else {}
        selected_at = timestamp(item.get('selected_at'))
        if selected_at is None:
            errors.append(f'{item_id} selected_at is required to prove cadence at dispatch')
        else:
            checked = timestamp(receipt.get('checked_at'))
            if checked and selected_at > checked:
                errors.append(f'{item_id} selected_at cannot be later than checked_at')
            full_audit_at = timestamp(review.get('last_full_audit_at'))
            interval = review.get('full_audit_interval_minutes')
            if full_audit_at and _positive_minutes(interval) and selected_at > full_audit_at and (selected_at - full_audit_at).total_seconds() >= interval * 60:
                errors.append(f'{item_id} was selected after the configurable full graph/critical-path audit became due')
            incremental_at = timestamp(review.get('incremental_at'))
            event_interval = review.get('event_interval_minutes')
            if incremental_at and _positive_minutes(event_interval) and selected_at > incremental_at and (selected_at - incremental_at).total_seconds() >= event_interval * 60:
                errors.append(f'{item_id} was selected after its incremental graph check became stale')
    return errors


def validate_schedule(receipt, before_yield=False, artifact_root=None):
    """Return consistency errors for one scheduling receipt."""
    errors = []
    if not isinstance(receipt, dict):
        return ['receipt must be a JSON object']

    scope_url = receipt.get('scope_url')
    try:
        parsed_scope = urlparse(scope_url) if nonempty_text(scope_url) else None
    except ValueError:
        parsed_scope = None
    source_kind = receipt.get('source_kind', 'github')
    if source_kind == 'github':
        if parsed_scope is None or parsed_scope.scheme not in {'http', 'https'} or not parsed_scope.netloc:
            errors.append('scope_url must be an absolute HTTP(S) link to the approved source scope')
    elif source_kind == 'files':
        if not evidence_pointer(scope_url) or parsed_scope is None or parsed_scope.scheme not in ('', 'file', 'artifact'):
            errors.append('file backlog scope_url must identify a local inventory file')
    else:
        errors.append('source_kind must be github or files')

    checked_at = receipt.get('checked_at')
    try:
        checked = datetime.fromisoformat(checked_at.replace('Z', '+00:00'))
        if checked.tzinfo is None:
            errors.append('checked_at must include a timezone')
    except (TypeError, ValueError, AttributeError):
        errors.append('checked_at must be a valid timezone-aware ISO-8601 timestamp')

    if receipt.get('source_complete') is not True:
        errors.append('source_complete must be true; incomplete or failed source retrieval cannot be certified')

    source_ids = receipt.get('source_ids')
    if not isinstance(source_ids, list):
        errors.append('source_ids must be an array of source item IDs')
        source_ids = []
    valid_source_ids = []
    for index, source_id in enumerate(source_ids):
        if not nonempty_text(source_id) or source_id != source_id.strip():
            errors.append(f'source_ids[{index}] must be a non-empty trimmed string')
        else:
            valid_source_ids.append(source_id)
    for source_id, count in Counter(valid_source_ids).items():
        if count > 1:
            errors.append(f'source_ids contains duplicate ID {source_id!r}')

    items = receipt.get('items')
    if not isinstance(items, list):
        errors.append('items must be an array of disposition rows')
        items = []

    item_ids = []
    normalized_items = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            errors.append(f'items[{index}] must be an object')
            continue
        item_id = item.get('id')
        if not nonempty_text(item_id) or item_id != item_id.strip():
            errors.append(f'items[{index}].id must be a non-empty trimmed string')
        else:
            item_ids.append(item_id)
        normalized_items.append((index, item, item_id))

    for item_id, count in Counter(item_ids).items():
        if count > 1:
            errors.append(f'items contains duplicate ID {item_id!r}')

    source_set = set(valid_source_ids)
    item_set = set(item_ids)
    missing_rows = sorted(source_set - item_set)
    extra_rows = sorted(item_set - source_set)
    if missing_rows:
        errors.append('source IDs missing disposition rows: ' + ', '.join(missing_rows))
    if extra_rows:
        errors.append('disposition rows absent from source_ids: ' + ', '.join(extra_rows))

    for index, item, item_id in normalized_items:
        prefix = f'items[{index}]'
        ready = item.get('ready')
        if not isinstance(ready, bool):
            errors.append(f'{prefix}.ready must be true or false')

        disposition = item.get('disposition')
        if not isinstance(disposition, str) or disposition not in DISPOSITIONS:
            errors.append(f'{prefix}.disposition is unknown: {disposition!r}')
            continue

        if disposition in {'active', 'dispatched'}:
            if not nonempty_text(item.get('job')):
                errors.append(f'{prefix}.job is required for {disposition} work')
            if not evidence_pointer(item.get('evidence')):
                errors.append(f'{prefix}.evidence must be a concrete pointer for {disposition} work')

        if disposition in HELD_DISPOSITIONS:
            for field in ('reason', 'next_owner', 'next_event'):
                if not nonempty_text(item.get(field)):
                    errors.append(f'{prefix}.{field} is required for held work ({disposition})')
            if not evidence_pointer(item.get('evidence')):
                errors.append(f'{prefix}.evidence must be a concrete pointer for held work ({disposition})')

        if disposition == 'dependency-blocked' and ready is True:
            errors.append(f'{prefix} cannot be ready and dependency-blocked')

        if ready is True and disposition not in READY_DISPOSITIONS:
            errors.append(
                f'{prefix} is ready but idle; use active/dispatched or an evidence-backed '
                'conflict-blocked, capacity-blocked, or authority-held exclusion')

    if before_yield:
        errors.extend(validate_yield_recovery(receipt, artifact_root))
    errors.extend(validate_dependency_graph(receipt))
    errors.extend(validate_graph_dispatch(receipt))
    errors.extend(validate_progress(receipt, before_yield=before_yield))
    errors.extend(validate_local_evidence(receipt, artifact_root))
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('receipt', help='path to a scheduling receipt JSON file')
    parser.add_argument('--before-yield', action='store_true', help='enforce turn-exit readiness independently of event trigger')
    parser.add_argument('--artifact-root', help='local artifact root; defaults to receipt directory')
    args = parser.parse_args(argv)
    try:
        receipt = json.loads(Path(args.receipt).read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError) as error:
        print(f'invalid schedule receipt: {error}', file=sys.stderr)
        return 2

    errors = validate_schedule(receipt, before_yield=args.before_yield,
                               artifact_root=args.artifact_root or Path(args.receipt).resolve().parent)
    if errors:
        print('invalid schedule receipt:')
        for error in errors:
            print(f'- {error}')
        return 1

    if receipt.get('dependency_graph') is None and receipt.get('dependency_graph_required') is not True:
        print('legacy schedule receipt is internally consistent; dependency graph completeness and critical path were not certified; source completeness and evidence truth were not verified')
    else:
        print('schedule receipt is internally consistent; source completeness and evidence truth were not verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
