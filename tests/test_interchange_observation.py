import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('observation', ROOT / 'skills/interchange/scripts/record_observation.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ObservationTests(unittest.TestCase):
    def test_record_is_idempotent_preserves_execution_and_rejects_changed_id(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshot.json'
            event = json.loads((ROOT / 'skills/interchange/templates/manual-observation.json').read_text())
            original = {'project_id': event['project_id'], 'attempts': [{'execution_state': 'stopped'}],
                        'workflow_steps': [{'id': event['workflow_step_id'], 'state': 'next', 'next_action': 'Await approval'}, {'id': 'other', 'state': 'done'}]}
            path.write_text(json.dumps(original))
            self.assertTrue(module.record(path, event))
            self.assertFalse(module.record(path, event))
            result = json.loads(path.read_text())
            self.assertEqual(original['attempts'], result['attempts'])
            self.assertEqual('next', result['workflow_steps'][0]['state'])
            self.assertEqual(original['workflow_steps'][1], result['workflow_steps'][1])
            self.assertEqual('Await approval', result['workflow_steps'][0]['next_action'])
            self.assertEqual(event, result['workflow_steps'][0]['manual_observation'])
            event['summary'] = 'different'
            with self.assertRaises(ValueError):
                module.record(path, event)
            self.assertEqual(result, json.loads(path.read_text()))

    def test_bad_provenance_timezone_and_unknown_fields_do_not_write(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'snapshot.json'
            path.write_text('{}')
            base = json.loads((ROOT / 'skills/interchange/templates/manual-observation.json').read_text())
            for changes in ({'observed_at': '2026-09-23T12:00:00'}, {'provenance': {'kind': 'verified', 'source': 'x'}}, {'relay_ack': True}):
                with self.assertRaises(ValueError):
                    module.record(path, dict(base, **changes))
                self.assertEqual('{}', path.read_text())
