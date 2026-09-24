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
    if receipt.get('source_kind', 'github') == 'files':
        check(receipt.get('scope_url'), 'scope_url')
    return errors


def timestamp(value):
    try:
        result = datetime.fromisoformat(value.replace('Z', '+00:00'))
        return result if result.tzinfo else None
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

    print('schedule receipt is internally consistent; source completeness and evidence truth were not verified')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
