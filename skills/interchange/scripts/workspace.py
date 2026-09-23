#!/usr/bin/env python3
"""Resolve a portable workspace and report retention candidates. Never deletes."""
import argparse
import json
from pathlib import Path
import subprocess
from datetime import datetime, timezone


def inside(root, relative):
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('workspace paths must be relative without parent traversal')
    result = (root / path).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError('workspace path escapes root')
    return result


def git(path, *args):
    return subprocess.check_output(['git', '-C', str(path), *args], text=True).strip()


def inspect(manifest, mappings, now=None):
    root = Path(manifest).resolve().parent
    config = json.loads(Path(manifest).read_text())
    local = json.loads(Path(mappings).read_text())
    now = now or datetime.now(timezone.utc)
    output = []
    for item in config.get('resources', []):
        reasons = []
        kind = item.get('kind')
        if kind == 'worktree':
            raw = local.get('worktrees', {}).get(item['id'])
            path = Path(raw).resolve() if raw else None
            expected = local.get('repositories', {}).get(item.get('repository_id'))
            if path is None or not expected:
                reasons.append('missing machine mapping')
            else:
                try:
                    common = git(path, 'rev-parse', '--path-format=absolute', '--git-common-dir')
                    expected_common = git(expected, 'rev-parse', '--path-format=absolute', '--git-common-dir')
                    if common != expected_common:
                        reasons.append('repository identity mismatch')
                    if git(path, 'status', '--porcelain'):
                        reasons.append('dirty or untracked work')
                    if git(path, 'rev-parse', 'HEAD') != item.get('verified_head'):
                        reasons.append('head differs from retained review')
                    # Exact remote reachability only; squash-equivalence needs separate review.
                    if not git(path, 'branch', '-r', '--contains', 'HEAD'):
                        reasons.append('no locally observed remote contains head; squash needs review')
                except (OSError, subprocess.CalledProcessError):
                    reasons.append('worktree verification unavailable')
        else:
            path = inside(root, item['path'])
            if not path.exists():
                reasons.append('path missing')
        if item.get('active_owner') is not False:
            reasons.append('active owner or ownership unknown')
        if item.get('holds') != []:
            reasons.append('holds present or unknown')
        if item.get('disposition') not in ('accepted-merged', 'retired'):
            reasons.append('not accepted and merged or explicitly retired')
        retention = config.get('retention_days', {}).get(kind)
        if kind not in ('worktree', 'raw-log') or not isinstance(retention, int) or retention < 0:
            reasons.append('retained by default')
        try:
            closed = datetime.fromisoformat(item['closed_at'].replace('Z', '+00:00'))
            if retention is not None and (now - closed).days < retention:
                reasons.append('retention period not elapsed')
        except (KeyError, ValueError, TypeError):
            reasons.append('closure time unknown')
        if item.get('archive_verified') is not True:
            reasons.append('required evidence archive not verified')
        output.append({'id': item['id'], 'path': str(path) if path else None,
                       'decision': 'retain' if reasons else 'candidate-for-review', 'reasons': reasons})
    return {'root': str(root), 'mode': 'dry-run', 'deletion_supported': False, 'resources': output}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--machine-map', required=True)
    args = parser.parse_args()
    print(json.dumps(inspect(args.manifest, args.machine_map), indent=2))


if __name__ == '__main__':
    main()
