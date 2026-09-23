"""Record a hand-run session report without manufacturing execution evidence."""
import argparse
from datetime import datetime
import fcntl
import json
import os
from pathlib import Path
import tempfile


def record(snapshot, event):
    required = {'observation_id', 'project_id', 'workflow_step_id', 'observed_at',
                'observer_id', 'observer_role', 'provenance', 'summary'}
    if not isinstance(event, dict) or not required <= event.keys() or event.keys() - required - {'reported_activity'}:
        raise ValueError('Invalid observation fields')
    for key in required - {'provenance'}:
        if not isinstance(event[key], str) or not event[key].strip() or len(event[key]) > 2000:
            raise ValueError('Invalid ' + key)
    stamp = datetime.fromisoformat(event['observed_at'].replace('Z', '+00:00'))
    if stamp.utcoffset() is None:
        raise ValueError('observed_at requires timezone')
    if event['observer_role'] not in {'owner', 'coordinator'}:
        raise ValueError('Invalid observer role')
    provenance = event['provenance']
    if not isinstance(provenance, dict) or set(provenance) != {'kind', 'source'} or provenance['kind'] != 'manual' or not isinstance(provenance['source'], str) or not provenance['source'].strip():
        raise ValueError('Manual provenance and source required')
    report = event.get('reported_activity', {})
    if not isinstance(report, dict) or report.keys() - {'status', 'current_action', 'task', 'owner', 'requested_model', 'requested_effort'}:
        raise ValueError('Invalid reported activity fields')
    if any(not isinstance(v, str) or not v.strip() or len(v) > 2000 for v in report.values()):
        raise ValueError('Reported values must be bounded nonempty text')
    path = Path(snapshot)
    with path.with_suffix(path.suffix + '.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads(path.read_text())
        if data.get('project_id') != event['project_id']:
            raise ValueError('Project mismatch')
        steps = [s for s in data.get('workflow_steps', []) if s.get('id') == event['workflow_step_id']]
        if len(steps) != 1:
            raise ValueError('Exactly one existing activity required')
        history = data.setdefault('manual_observations', [])
        for previous in history:
            if previous['observation_id'] == event['observation_id']:
                if previous != event:
                    raise ValueError('Observation ID already has different content')
                return False
        history.append(event)
        step = steps[0]
        previous = step.get('manual_observation')
        if not previous or stamp >= datetime.fromisoformat(previous['observed_at'].replace('Z', '+00:00')):
            step['manual_observation'] = event
        fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=path.name + '.')
        try:
            with os.fdopen(fd, 'w') as out:
                json.dump(data, out, indent=2)
                out.write('\n')
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
        return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('snapshot')
    parser.add_argument('event')
    args = parser.parse_args()
    try:
        changed = record(args.snapshot, json.loads(Path(args.event).read_text()))
    except (ValueError, OSError) as error:
        parser.exit(2, str(error) + '\n')
    print('Recorded' if changed else 'Already recorded')
