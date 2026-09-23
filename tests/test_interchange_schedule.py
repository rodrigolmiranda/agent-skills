import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

spec = importlib.util.spec_from_file_location(
    'check_schedule', Path(__file__).parents[1] / 'skills/delivery-orchestrator/scripts/check_schedule.py')
check_schedule = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_schedule)


def dispatched_item(item_id):
    return {
        'id': item_id,
        'ready': True,
        'disposition': 'dispatched',
        'job': 'job-' + item_id,
        'evidence': 'https://github.com/example/project/actions/runs/123',
    }


def receipt(items=None, source_ids=None):
    if items is None:
        items = [dispatched_item('PROJECT#1'), dispatched_item('PROJECT#2')]
    if source_ids is None:
        source_ids = [item['id'] for item in items]
    return {
        'scope_url': 'https://github.com/example/project/milestone/4',
        'checked_at': '2026-09-23T09:10:00Z',
        'source_complete': True,
        'source_ids': source_ids,
        'items': items,
        'write_leases': [],
        'checkpoint': {
            'trigger': 'return', 'next_owner': 'coordinator', 'next_event': 'worker return',
            'assessment_evidence': 'artifact://schedule/current',
            'last_progress_at': '2026-09-23T09:00:00Z',
            'last_progress_evidence': 'artifact://dispatch/startup',
            'source_query': 'artifact://inventory/query',
            'hierarchy_evidence': 'artifact://inventory/parents-and-children',
            'source_retrieved_at': '2026-09-23T09:00:00Z',
            'unchanged_checks': 0,
        },
    }


class ScheduleReceiptTests(unittest.TestCase):
    def test_complete_parallel_dispatch_is_consistent(self):
        items = [
            {'id': 'PROJECT#1', 'ready': True, 'disposition': 'active',
             'job': 'job-one', 'evidence': 'artifact://worker/one-started'},
            {'id': 'PROJECT#2', 'ready': True, 'disposition': 'dispatched',
             'job': 'job-two', 'evidence': 'https://github.com/example/project/actions/runs/234'},
        ]
        self.assertEqual([], check_schedule.validate_schedule(receipt(items)))

    def test_incomplete_source_duplicate_and_missing_or_extra_ids_are_rejected(self):
        items = [dispatched_item('PROJECT#1'), dispatched_item('PROJECT#3')]
        record = receipt(items, ['PROJECT#1', 'PROJECT#1', 'PROJECT#2'])
        record['source_complete'] = False

        errors = check_schedule.validate_schedule(record)

        self.assertTrue(any('source_complete must be true' in error for error in errors))
        self.assertTrue(any('duplicate ID' in error for error in errors))
        self.assertTrue(any('missing disposition rows: PROJECT#2' in error for error in errors))
        self.assertTrue(any('absent from source_ids: PROJECT#3' in error for error in errors))

    def test_duplicate_item_ids_are_rejected(self):
        first = dispatched_item('PROJECT#1')
        duplicate = dispatched_item('PROJECT#1')
        errors = check_schedule.validate_schedule(receipt([first, duplicate], ['PROJECT#1']))
        self.assertTrue(any('items contains duplicate ID' in error for error in errors))

    def test_unknown_disposition_is_rejected_without_crashing_on_non_string(self):
        item = {'id': 'PROJECT#1', 'ready': False, 'disposition': {'state': 'maybe'}}
        errors = check_schedule.validate_schedule(receipt([item], ['PROJECT#1']))
        self.assertTrue(any('disposition is unknown' in error for error in errors))

    def test_ready_idle_requires_evidence_backed_allowed_exclusion(self):
        item = {'id': 'PROJECT#1', 'ready': True, 'disposition': 'conflict-blocked',
                'reason': 'Conflicts with the shared migration test database',
                'next_owner': 'coordinator', 'next_event': 'database lock released'}
        errors = check_schedule.validate_schedule(receipt([item], ['PROJECT#1']))
        self.assertTrue(any('.evidence must be a concrete pointer for held work' in error
                            for error in errors))

        placeholder_evidence = {
            'id': 'PROJECT#1', 'ready': True, 'disposition': 'conflict-blocked',
            'reason': 'Conflicts with the shared migration test database',
            'evidence': 'artifact or GitHub URL',
            'next_owner': 'coordinator', 'next_event': 'database lock released',
        }
        errors = check_schedule.validate_schedule(receipt([placeholder_evidence], ['PROJECT#1']))
        self.assertTrue(any('.evidence must be a concrete pointer for held work' in error
                            for error in errors))

        malformed_evidence = dict(placeholder_evidence, evidence='https://[')
        errors = check_schedule.validate_schedule(receipt([malformed_evidence], ['PROJECT#1']))
        self.assertTrue(any('.evidence must be a concrete pointer for held work' in error
                            for error in errors))

        coordinator_action = {
            'id': 'PROJECT#1', 'ready': True, 'disposition': 'coordinator-action',
            'reason': 'Coordinator must select the task owner',
            'evidence': 'https://github.com/example/project/issues/1',
            'next_owner': 'coordinator', 'next_event': 'owner selected',
        }
        errors = check_schedule.validate_schedule(receipt([coordinator_action], ['PROJECT#1']))
        self.assertTrue(any('ready but idle' in error for error in errors))

    def test_measured_capacity_exclusion_with_evidence_is_consistent(self):
        item = {
            'id': 'PROJECT#1', 'ready': True, 'disposition': 'capacity-blocked',
            'reason': 'Both authorized DeepSeek slots are running; one slot is available after either returns',
            'evidence': 'artifact://capacity/snapshot-17',
            'next_owner': 'coordinator', 'next_event': 'first worker return or capacity change',
        }
        self.assertEqual([], check_schedule.validate_schedule(receipt([item], ['PROJECT#1'])))

    def test_held_rows_require_resolution_owner_and_next_event(self):
        item = {
            'id': 'PROJECT#1', 'ready': False, 'disposition': 'dependency-blocked',
            'reason': 'Wait for PROJECT#2 to merge', 'evidence': 'https://github.com/example/project/issues/2',
        }
        errors = check_schedule.validate_schedule(receipt([item], ['PROJECT#1']))
        self.assertTrue(any('next_owner is required for held work' in error for error in errors))
        self.assertTrue(any('next_event is required for held work' in error for error in errors))

    def test_coordinator_action_needs_a_concrete_evidence_backed_next_check(self):
        unverified = {'id': 'PROJECT#1', 'ready': False, 'disposition': 'coordinator-action'}
        errors = check_schedule.validate_schedule(receipt([unverified], ['PROJECT#1']))
        self.assertTrue(any('reason is required for held work' in error for error in errors))
        self.assertTrue(any('.evidence must be a concrete pointer for held work' in error
                            for error in errors))
        self.assertTrue(any('next_owner is required for held work' in error for error in errors))
        self.assertTrue(any('next_event is required for held work' in error for error in errors))

        verified = {
            'id': 'PROJECT#1', 'ready': False, 'disposition': 'coordinator-action',
            'reason': 'Readiness is not established; inspect the issue dependency state',
            'evidence': 'https://github.com/example/project/issues/1',
            'next_owner': 'coordinator', 'next_event': 'dependency state checked',
        }
        self.assertEqual([], check_schedule.validate_schedule(receipt([verified], ['PROJECT#1'])))

    def test_active_and_dispatched_rows_require_job_and_evidence(self):
        for disposition in ('active', 'dispatched'):
            with self.subTest(disposition=disposition):
                item = {'id': 'PROJECT#1', 'ready': True, 'disposition': disposition}
                errors = check_schedule.validate_schedule(receipt([item], ['PROJECT#1']))
                self.assertTrue(any(f'.job is required for {disposition} work' in error for error in errors))
                self.assertTrue(any(f'.evidence must be a concrete pointer for {disposition} work' in error
                                    for error in errors))

    def test_dependency_blocked_cannot_be_marked_ready(self):
        item = {
            'id': 'PROJECT#1', 'ready': True, 'disposition': 'dependency-blocked',
            'reason': 'Wait for PROJECT#2', 'evidence': 'https://github.com/example/project/issues/2',
            'next_owner': 'coordinator', 'next_event': 'PROJECT#2 resolves',
        }
        errors = check_schedule.validate_schedule(receipt([item], ['PROJECT#1']))
        self.assertTrue(any('cannot be ready and dependency-blocked' in error for error in errors))

    def test_checker_rejects_source_metadata_that_cannot_be_audited(self):
        record = receipt()
        record['scope_url'] = 'https://['
        record['checked_at'] = 'yesterday'
        errors = check_schedule.validate_schedule(record)
        self.assertTrue(any('scope_url must be an absolute HTTP(S) link' in error for error in errors))
        self.assertTrue(any('checked_at must be a valid timezone-aware ISO-8601 timestamp' in error
                            for error in errors))

    def test_cli_labels_success_as_consistency_only(self):
        record = receipt()
        script = Path(__file__).parents[1] / 'skills/delivery-orchestrator/scripts/check_schedule.py'
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', suffix='.json') as receipt_file:
            json.dump(record, receipt_file)
            receipt_file.flush()
            result = subprocess.run(
                [sys.executable, str(script), receipt_file.name],
                capture_output=True, text=True, check=False,
            )

        self.assertEqual(0, result.returncode, result.stderr + result.stdout)
        self.assertIn('source completeness and evidence truth were not verified', result.stdout)


class ProgressCheckpointTests(unittest.TestCase):
    def test_old_inventory_alone_cannot_certify_progress(self):
        record = receipt()
        del record['checkpoint']
        self.assertTrue(any('checkpoint is required' in e for e in check_schedule.validate_schedule(record)))

    def test_two_unchanged_checks_require_recovery_across_all_work(self):
        record = receipt()
        record['checkpoint']['unchanged_checks'] = 2
        self.assertTrue(any('recovery is required' in e for e in check_schedule.validate_schedule(record)))
        record['checkpoint']['recovery'] = {
            'blocker_recheck': 'artifact://recovery/current-cause',
            'authorized_alternatives': 'artifact://recovery/alternatives',
            'independent_work': 'artifact://recovery/full-backlog',
            'next_check_at': '2026-09-23T09:30:00Z',
        }
        self.assertEqual([], check_schedule.validate_schedule(record))
        record['checkpoint']['recovery']['next_check_at'] = record['checked_at']
        self.assertTrue(any('next_check_at' in e for e in check_schedule.validate_schedule(record)))

    def test_inventory_needs_children_and_retrieval_provenance(self):
        record = receipt()
        del record['checkpoint']['hierarchy_evidence']
        record['checkpoint']['source_retrieved_at'] = 'tomorrow'
        self.assertTrue(any('hierarchy_evidence' in e for e in check_schedule.validate_schedule(record)))
        self.assertTrue(any('source_retrieved_at' in e for e in check_schedule.validate_schedule(record)))

    def test_stopped_writer_does_not_reserve_acceptance_surface(self):
        record = receipt()
        record['write_leases'] = [{
            'id': 'writer', 'job': 'job-one', 'owner': 'coder', 'surface': 'src/view.py',
            'evidence': 'artifact://writer/exit', 'state': 'held', 'writer_state': 'exited',
            'recheck_at': '2026-09-23T09:30:00Z',
        }]
        self.assertTrue(any('stopped writer' in e for e in check_schedule.validate_schedule(record)))
        record['write_leases'][0]['state'] = 'released'
        self.assertEqual([], check_schedule.validate_schedule(record))

    def test_unknown_writer_requires_recheck_not_automatic_release(self):
        record = receipt()
        record['write_leases'] = [{
            'id': 'writer', 'job': 'job-one', 'owner': 'coder', 'surface': 'src/view.py',
            'evidence': 'artifact://writer/timeout', 'state': 'held', 'writer_state': 'unknown',
            'recheck_at': record['checked_at'],
        }]
        self.assertTrue(any('never auto-release' in e for e in check_schedule.validate_schedule(record)))
        record['write_leases'][0]['recheck_at'] = '2026-09-23T09:30:00Z'
        self.assertEqual([], check_schedule.validate_schedule(record))

    def test_released_lease_cannot_block_a_ready_item(self):
        item = {'id': 'PROJECT#1', 'ready': True, 'disposition': 'conflict-blocked',
                'reason': 'shared file', 'next_owner': 'coordinator', 'next_event': 'release',
                'evidence': 'artifact://conflict/source', 'conflict_surface': 'src/view.py',
                'write_lease': 'released'}
        self.assertTrue(any('released or absent' in e for e in check_schedule.validate_schedule(receipt([item]))))

    def test_yield_cannot_leave_an_unowned_readiness_action(self):
        item = {'id': 'PROJECT#1', 'ready': False, 'disposition': 'coordinator-action',
                'reason': 'publish accepted platform request', 'next_owner': 'coordinator',
                'next_event': 'request filed', 'evidence': 'artifact://packet/request'}
        record = receipt([item])
        record['checkpoint']['trigger'] = 'yield'
        self.assertTrue(any('executable coordinator-action' in e for e in check_schedule.validate_schedule(record)))
        item['supervised_wait'] = 'artifact://supervisor/request-owner'
        self.assertEqual([], check_schedule.validate_schedule(record))

    def test_exit_validation_applies_to_reused_worker_return_receipt(self):
        item = {'id': 'PROJECT#1', 'ready': False, 'disposition': 'coordinator-action',
                'reason': 'publish accepted request', 'next_owner': 'coordinator',
                'next_event': 'request filed', 'evidence': 'artifact://packet/request'}
        record = receipt([item])
        self.assertEqual([], check_schedule.validate_schedule(record))
        self.assertTrue(any('executable coordinator-action' in e for e in
                            check_schedule.validate_schedule(record, before_yield=True)))
        script = Path(check_schedule.__file__)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json') as f:
            json.dump(record, f)
            f.flush()
            result = subprocess.run([sys.executable, str(script), f.name, '--before-yield'],
                                    capture_output=True, text=True)
        self.assertEqual(1, result.returncode)
        self.assertIn('executable coordinator-action', result.stdout)

    def test_malformed_lease_references_return_errors_not_exceptions(self):
        record = receipt()
        record['write_leases'] = [None, {'id': []}]
        self.assertTrue(check_schedule.validate_schedule(record))
        record['items'][0].update(disposition='conflict-blocked', write_lease=[],
                                 conflict_surface='src/view.py')
        self.assertTrue(check_schedule.validate_schedule(record))

    def test_progress_cannot_be_future_or_counter_boolean(self):
        record = receipt()
        record['checkpoint']['last_progress_at'] = '2026-09-24T09:00:00Z'
        record['checkpoint']['unchanged_checks'] = True
        errors = check_schedule.validate_schedule(record)
        self.assertTrue(any('last_progress_at' in e for e in errors))
        self.assertTrue(any('unchanged_checks' in e for e in errors))


if __name__ == '__main__':
    unittest.main()
