import concurrent.futures
import hashlib
import json
import importlib.util
from pathlib import Path
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).parents[1] / 'skills/interchange/scripts/relay.py'
spec = importlib.util.spec_from_file_location('relay_ownership', SOURCE)
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


class OwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.state = self.root / 'relay.sqlite'
        self.db = relay.connect(self.state)
        self.old = '01a0bd84-f736-78c3-91d3-a12d9989be4f'
        self.new = '16f55728-e1f6-41aa-b0ee-9d9674a688d6'
        relay.register_project(self.db, 'sales', self.old)
        relay.register(self.db, 'job', 'one', 'worker', self.root, self.old)
        relay.bind_attempt(self.db, 'sales', 'job', 'one', 1)
        self.artifact = self.root / 'result.md'
        self.artifact.write_text('Immutable worker result')

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def event(self, eid='result'):
        return relay.emit(self.db, 'job', 'one', 'worker', 'result', self.artifact, eid)

    def test_takeover_races_converge_on_one_generation_and_stale_actions_fail(self):
        def transfer():
            db = relay.connect(self.state)
            try:
                return relay.transfer_project(db, 'sales', 1, self.new)['generation']
            except ValueError:
                return 'stale'
            finally:
                db.close()
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            self.assertCountEqual(list(pool.map(lambda _: transfer(), range(2))), [2, 'stale'])
        self.assertEqual(relay.current_generation(self.db, 'sales'), 2)
        with self.assertRaises(ValueError):
            relay.require_current_generation(self.db, 'sales', 1)
        with self.assertRaises(ValueError):
            relay.bind_attempt(self.db, 'sales', 'job', 'one', 1)
        with self.assertRaises(ValueError):
            relay.transfer_project(self.db, 'sales', 1, self.old)
        self.assertEqual(self.db.execute('SELECT coordinator FROM attempts WHERE job=?', ('job',)).fetchone()[0], self.old)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM route_history WHERE project=?', ('sales',)).fetchone()[0], 2)

    def test_duplicate_notify_only_once_and_replay_to_new_route(self):
        self.event()
        with patch.object(relay.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
            self.assertEqual(relay.notify(self.db, 'result')['generation'], 1)
            self.assertFalse(relay.notify(self.db, 'result')['sent_again'])
            self.assertEqual(run.call_count, 1)
            relay.transfer_project(self.db, 'sales', 1, self.new)
            self.assertEqual(relay.notify(self.db, 'result')['generation'], 2)
            self.assertEqual(run.call_count, 2)
            self.assertEqual(run.call_args.args[0][3], self.new)
            self.assertEqual(run.call_args.args[0][5].count('INTERCHANGE_EVENT'), 1)
        with self.assertRaises(ValueError):
            relay.acknowledge(self.db, 'result', 1, self.old)
        self.assertFalse(relay.acknowledge(self.db, 'result', 2, self.new)['accepted'])
        self.assertTrue(relay.notify(self.db, 'result')['received'])
        rows = self.db.execute('SELECT generation,acknowledged FROM event_deliveries ORDER BY generation').fetchall()
        self.assertIsNone(rows[0]['acknowledged'])
        self.assertIsNotNone(rows[1]['acknowledged'])

    def test_acknowledged_event_does_not_replay_on_transfer(self):
        self.event()
        with patch.object(relay.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')) as run:
            relay.notify(self.db, 'result')
            relay.acknowledge(self.db, 'result', 1, self.old)
            relay.transfer_project(self.db, 'sales', 1, self.new)
            self.assertEqual(relay.notify(self.db, 'result')['delivery'], 'acknowledged')
            self.assertEqual(run.call_count, 1)

    def test_failed_delivery_retries_with_bound_and_unknown_does_not(self):
        self.event()
        with patch.object(relay.subprocess, 'run', return_value=subprocess.CompletedProcess([], 1, '', 'down')) as run:
            self.assertEqual(relay.notify(self.db, 'result')['delivery'], 'failed')
            self.assertEqual(relay.retry_failed_delivery(self.db, 'result', max_retries=1)['delivery'], 'failed')
            self.assertEqual(run.call_count, 2)
        with self.assertRaises(ValueError):
            relay.retry_failed_delivery(self.db, 'result', max_retries=1)
        self.event('other')
        with patch.object(relay.subprocess, 'run', side_effect=subprocess.TimeoutExpired('codex', 30)) as run:
            self.assertEqual(relay.notify(self.db, 'other')['delivery'], 'unknown')
            self.assertFalse(relay.notify(self.db, 'other')['sent_again'])
            self.assertEqual(run.call_count, 1)

    def test_manual_takeover_keeps_event_visible_without_false_wake(self):
        self.event()
        relay.transfer_project(self.db, 'sales', 1, route='manual')
        with patch.object(relay.subprocess, 'run') as run:
            self.assertEqual(relay.notify(self.db, 'result')['delivery'], 'manual')
            run.assert_not_called()
        self.assertIsNone(self.db.execute('SELECT acknowledged FROM events WHERE id=?', ('result',)).fetchone()[0])
        with self.assertRaises(ValueError):
            relay.acknowledge(self.db, 'result', 2)
        self.assertFalse(relay.acknowledge(self.db, 'result', 2, 'manual')['accepted'])

    def test_codex_ack_requires_current_nonnull_coordinator_identity(self):
        self.event()
        with patch.object(relay.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, '', '')):
            relay.notify(self.db, 'result')
        for identity in (None, 'manual', 'wrong'):
            with self.assertRaises(ValueError):
                relay.acknowledge(self.db, 'result', 1, identity)
        self.assertFalse(relay.acknowledge(self.db, 'result', 1, self.old)['accepted'])

    def test_claude_ack_requires_current_nonnull_receiver_identity(self):
        relay.transfer_project(self.db, 'sales', 1, route='claude-task', receiver='parent-task')
        self.event()
        self.assertEqual(relay.notify(self.db, 'result')['delivery'], 'harness-pending')
        for identity in (None, self.old, 'wrong'):
            with self.assertRaises(ValueError):
                relay.acknowledge(self.db, 'result', 2, identity)
        self.assertFalse(relay.acknowledge(self.db, 'result', 2, 'parent-task')['accepted'])

    def test_action_lease_serializes_takeover_and_does_not_expire_automatically(self):
        token = relay.acquire_managed_action(self.db, 'sales', 1, 'push', lease_seconds=1)
        other = relay.connect(self.state)
        try:
            with self.assertRaises(ValueError):
                relay.transfer_project(other, 'sales', 1, self.new)
            with self.assertRaises(ValueError):
                relay.acquire_managed_action(other, 'sales', 1, 'pr-create')
            self.db.execute("UPDATE managed_actions SET check_after='2000-01-01T00:00:00+00:00' WHERE token=?", (token,))
            self.db.commit()
            with self.assertRaises(ValueError):
                relay.transfer_project(other, 'sales', 1, self.new)
            relay.release_managed_action(self.db, token)
            self.assertEqual(relay.transfer_project(other, 'sales', 1, self.new)['generation'], 2)
            with self.assertRaises(ValueError):
                relay.acquire_managed_action(self.db, 'sales', 1, 'push')
        finally:
            other.close()

    def test_nonmessageable_active_worker_gets_forwarding_notice_without_ack(self):
        self.db.execute('INSERT INTO launches VALUES (?,?,?,?)', ('job','one',str(self.root),'1'))
        self.db.commit()
        relay.transfer_project(self.db, 'sales', 1, self.new)
        roster = relay.takeover_roster(self.db, 'sales', 2)
        self.assertEqual(len(roster), 1)
        self.assertEqual(roster[0]['status'], 'pending_next_packet')
        self.assertIsNone(roster[0]['acknowledged'])
        with self.assertRaises(ValueError):
            relay.mark_takeover_notice(self.db, 'sales', 2, 'job', 'one', acknowledged=True)
        delivered = relay.mark_takeover_notice(self.db, 'sales', 2, 'job', 'one')
        self.assertEqual(delivered['status'], 'delivered')
        self.assertIsNone(delivered['acknowledged'])
        self.assertEqual(relay.mark_takeover_notice(self.db, 'sales', 2, 'job', 'one', acknowledged=True)['status'],
                         'acknowledged')

    def test_takeover_during_old_queue_send_replays_to_new_route(self):
        self.event()
        entered = threading.Event()
        release = threading.Event()
        receivers = []
        def queue(argv, **kwargs):
            receivers.append(argv[3])
            if argv[3] == self.old:
                entered.set()
                self.assertTrue(release.wait(3))
            return subprocess.CompletedProcess([], 0, '', '')
        def old_send():
            db = relay.connect(self.state)
            try:
                return relay.notify(db, 'result')
            finally:
                db.close()
        with patch.object(relay.subprocess, 'run', side_effect=queue):
            with concurrent.futures.ThreadPoolExecutor(1) as pool:
                future = pool.submit(old_send)
                self.assertTrue(entered.wait(3))
                relay.transfer_project(self.db, 'sales', 1, self.new)
                release.set()
                self.assertEqual(future.result(timeout=3)['generation'], 1)
                self.assertEqual(relay.notify(self.db, 'result')['generation'], 2)
        self.assertEqual(receivers, [self.old, self.new])
        with self.assertRaises(ValueError):
            relay.acknowledge(self.db, 'result', 1, self.old)

    def test_existing_unbound_event_cannot_be_reinterpreted_as_project_event(self):
        relay.register(self.db, 'legacy', 'one', 'worker', self.root, self.old)
        relay.emit(self.db, 'legacy', 'one', 'worker', 'question', self.artifact, 'legacy-question')
        with self.assertRaises(ValueError):
            relay.bind_attempt(self.db, 'sales', 'legacy', 'one', 1)

    def test_project_identifier_matches_board_identity_contract(self):
        with self.assertRaises(ValueError):
            relay.register_project(self.db, 'other.project', route='manual')

    def test_recovery_route_requires_independent_action_start_proof(self):
        proof = {'schedule_id':'scheduled-monitor','coordinator_id':self.old,'ownership_generation':1,
                 'worker_completed_at':'2026-09-24T00:00:00+00:00',
                 'queued_at':'2026-09-24T00:00:01+00:00',
                 'delivered_at':'2026-09-24T00:00:02+00:00',
                 'awake_at':'2026-09-24T00:00:03+00:00',
                 'action_started_at':'2026-09-24T00:00:04+00:00',
                 'action_id':'review-1','execution_evidence':{'launch':'review-1'}}
        proof_path = self.root/'proof.json'
        proof_path.write_text(json.dumps(proof))
        route = {'kind':'supervisor','schedule_id':'scheduled-monitor','owner':'supervisor',
                 'coordinator_id':self.old,'ownership_generation':1,'independently_scheduled':True,
                 'acceptance':'next_action_started','max_action_latency_seconds':30,
                 'verified_at':'2026-09-24T00:00:05+00:00',
                 'expires_at':'2026-09-25T00:00:00+00:00',
                 'proof':{'path':'proof.json','sha256':hashlib.sha256(proof_path.read_bytes()).hexdigest()}}
        checked_at = 1790208010  # 2026-09-24T00:00:10Z
        self.assertEqual(relay.validate_recovery_route(route, checked_at, self.root), [])
        queued_only = dict(proof); queued_only.pop('action_started_at')
        proof_path.write_text(json.dumps(queued_only))
        route['proof']['sha256'] = hashlib.sha256(proof_path.read_bytes()).hexdigest()
        self.assertIn('invalid action_started_at', relay.validate_recovery_route(route, checked_at, self.root))
        route['ownership_generation'] = 2
        self.assertIn('recovery proof ownership_generation mismatch',
                      relay.validate_recovery_route(route, checked_at, self.root))
        route['ownership_generation'] = 1
        route['max_action_latency_seconds'] = float('nan')
        self.assertIn('invalid max_action_latency_seconds',
                      relay.validate_recovery_route(route, checked_at, self.root))
        route['max_action_latency_seconds'] = 30
        proof_path.write_text('null')
        route['proof']['sha256'] = hashlib.sha256(proof_path.read_bytes()).hexdigest()
        self.assertIn('recovery proof must be an object',
                      relay.validate_recovery_route(route, checked_at, self.root))


if __name__ == '__main__':
    unittest.main()
