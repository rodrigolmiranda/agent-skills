import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).parents[1] / 'skills/interchange/scripts'
sys.path.insert(0, str(SCRIPTS))
import relay
spec = importlib.util.spec_from_file_location('interchange_monitor', SCRIPTS / 'monitor.py')
monitor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(monitor)


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = relay.connect(self.root/'state.sqlite')
        self.old = '01a0bd84-f736-78c3-91d3-a12d9989be4f'
        relay.register_project(self.db, 'sales', self.old)
        relay.register(self.db, 'job', 'one', 'worker', self.root, self.old)
        relay.bind_attempt(self.db, 'sales', 'job', 'one', 1)
        self.artifact = self.root/'result.md'
        self.artifact.write_text('return')

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def test_missing_delivery_is_visible_and_snapshot_is_structured(self):
        relay.emit(self.db, 'job', 'one', 'worker', 'result', self.artifact, 'event')
        alerts = monitor.scan(self.db, now_seconds=2000000000, overdue_seconds=1)
        self.assertEqual([a['kind'] for a in alerts], ['undelivered_event'])
        record = monitor.write_snapshot(self.root/'monitor.json', alerts, 'sales', now_seconds=2000000000)
        self.assertFalse(record['notification_available'])
        self.assertEqual(record['project_id'], 'sales')
        self.assertTrue(record['alerts'][0]['id'].startswith('undelivered_event:'))
        self.assertEqual(record, json.loads((self.root/'monitor.json').read_text()))
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM monitor_findings WHERE resolved IS NULL').fetchone()[0], 1)

    def test_stale_action_and_pipeline_stage_are_reported_without_auto_release(self):
        token = relay.acquire_managed_action(self.db, 'sales', 1, 'push')
        self.db.execute("UPDATE managed_actions SET check_after='2000-01-01T00:00:00+00:00'")
        directory = self.root/'attempt'; directory.mkdir()
        self.db.execute('INSERT INTO launches VALUES (?,?,?,?)', ('job','one',str(directory),'1'))
        (directory/'post-return.json').write_text(json.dumps({'stage':'pr_created'}))
        self.db.commit()
        alerts = monitor.scan(self.db, now_seconds=2000000000, overdue_seconds=1)
        kinds = {a['kind'] for a in alerts}
        self.assertIn('overdue_managed_action', kinds)
        self.assertIn('missing_terminal_return', kinds)
        self.assertIn('stalled_pipeline', kinds)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM managed_actions').fetchone()[0], 1)
        relay.release_managed_action(self.db, token)

    def test_resolved_finding_keeps_history(self):
        relay.emit(self.db, 'job', 'one', 'worker', 'result', self.artifact, 'event')
        monitor.scan(self.db, now_seconds=2000000000, overdue_seconds=1)
        relay.transfer_project(self.db, 'sales', 1, route='manual')
        relay.notify(self.db, 'event')
        relay.acknowledge(self.db, 'event', 2)
        self.assertEqual(monitor.scan(self.db, now_seconds=2000000001, overdue_seconds=1), [])
        self.assertIsNotNone(self.db.execute('SELECT resolved FROM monitor_findings WHERE key=?', ('event:event',)).fetchone()[0])

    def test_long_running_worker_inside_declared_deadline_is_not_missing(self):
        directory = self.root/'long'; directory.mkdir()
        self.db.execute('INSERT INTO launches VALUES (?,?,?,?)', ('job','one',str(directory),'100'))
        self.db.commit()
        (directory/'runner.json').write_text(json.dumps({'state':'running','deadline_at':2000}))
        self.assertEqual(monitor.scan(self.db, project='sales', now_seconds=1000, overdue_seconds=300), [])
        alerts = monitor.scan(self.db, project='sales', now_seconds=2400, overdue_seconds=300)
        self.assertEqual([a['kind'] for a in alerts], ['missing_terminal_return'])

    def test_full_activity_ledger_detects_ready_review_and_verdict_gaps(self):
        record = {'project_id':'sales', 'workflow_steps':[
            {'id':'next-work','state':'next','owner':'lead','expected_transition':'working',
             'deadline_at':'2026-01-01T00:00:00+00:00'},
            {'id':'review-work','state':'review','owner':'reviewer','expected_transition':'verdict',
             'deadline_at':'2026-01-01T00:00:00+00:00'},
            {'id':'verdict-work','state':'review','owner':'lead','expected_transition':'disposition',
             'deadline_at':'2026-01-01T00:00:00+00:00', 'executor_started_at':'2025-12-31T00:00:00+00:00',
             'verdict_at':'2026-01-01T00:00:00+00:00'},
            {'id':'older-record','state':'working','owner':'lead'},
        ]}
        timestamp = 1767312000  # 2026-01-02 UTC
        alerts = monitor.scan(self.db, project='sales', activities=record,
                              now_seconds=timestamp, overdue_seconds=300)
        self.assertEqual({a['kind'] for a in alerts}, {
            'ready_without_executor', 'review_without_executor',
            'verdict_without_disposition', 'incomplete_supervision'})
        with self.assertRaises(ValueError):
            monitor.scan(self.db, project='sales', activities={**record,'project_id':'other'},
                         now_seconds=timestamp)

    def test_project_snapshot_excludes_another_projects_events(self):
        other = self.root/'other.md'; other.write_text('other')
        relay.register_project(self.db, 'other', route='manual')
        relay.register(self.db, 'other-job', 'one', 'worker', self.root)
        relay.bind_attempt(self.db, 'other', 'other-job', 'one', 1)
        relay.emit(self.db, 'other-job', 'one', 'worker', 'question', other, 'other-event')
        self.assertEqual(monitor.scan(self.db, project='sales', now_seconds=2000000000), [])
        alerts = monitor.scan(self.db, project='other', now_seconds=2000000000)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0]['job'], 'other-job')


if __name__ == '__main__':
    unittest.main()
