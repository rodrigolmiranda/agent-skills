import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone

SCRIPTS = Path(__file__).parents[1] / 'skills/interchange/scripts'
sys.path.insert(0, str(SCRIPTS))
import relay
import monitor


class NativeRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = relay.connect(self.root/'relay.sqlite')
        self.coordinator = '01a0bd84-f736-78c3-91d3-a12d9989be4f'
        relay.register_project(self.db, 'sales', self.coordinator)
        relay.register(self.db, 'native-job', 'one', 'native-worker', self.root, self.coordinator)
        relay.bind_attempt(self.db, 'sales', 'native-job', 'one', 1)
        self.result = self.root/'native-result.json'
        self.result.write_text('{"completed":true}')

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def route(self):
        base = datetime.now(timezone.utc)
        iso = lambda offset: (base + timedelta(seconds=offset)).isoformat()
        proof = {'schedule_id':'fixture-schedule','coordinator_id':self.coordinator,
                 'ownership_generation':1, 'worker_completed_at':iso(-10),
                 'queued_at':iso(-9), 'delivered_at':iso(-8), 'awake_at':iso(-7),
                 'action_started_at':iso(-6), 'action_id':'prior-smoke',
                 'execution_evidence':{'fixture':'independent-supervisor'}}
        path = self.root/'smoke.json'
        path.write_text(json.dumps(proof))
        return {'kind':'supervisor','schedule_id':'fixture-schedule','owner':'fixture-supervisor',
                'coordinator_id':self.coordinator,'ownership_generation':1,
                'independently_scheduled':True,'acceptance':'next_action_started',
                'max_action_latency_seconds':30, 'verified_at':iso(-5),
                'expires_at':iso(3600),
                'proof':{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}

    def declare(self, argv):
        return relay.declare_next_action(self.db, 'review-after-native', 'sales', 1,
                                         'native-job', 'one', 'native-completed', argv,
                                         self.root,
                                         (datetime.now(timezone.utc)+timedelta(seconds=20)).isoformat(),
                                         self.route())

    def test_native_completion_recovery_starts_reviewer_once_without_ack_or_user_turn(self):
        marker = self.root/'reviewer-started.txt'
        reviewer = self.root/'reviewer.py'
        reviewer.write_text('import pathlib,sys,time\nwith pathlib.Path(sys.argv[1]).open("a") as marker: marker.write("started\\n")\ntime.sleep(2)\n')
        adapter = self.root/'coordinator.py'
        adapter.write_text('''import hashlib,json,os,pathlib,subprocess,sys,time
sys.path.insert(0,sys.argv[1])
import relay
db=relay.connect(os.environ['INTERCHANGE_RELAY_STATE'])
action=os.environ['INTERCHANGE_ACTION_ID']; generation=int(os.environ['INTERCHANGE_OWNERSHIP_GENERATION'])
token=os.environ['INTERCHANGE_CLAIM_TOKEN']
relay.acknowledge_recovery_awake(db,action,generation,token)
proc=subprocess.Popen([sys.executable,sys.argv[2],sys.argv[3]],start_new_session=True)
marker=pathlib.Path(sys.argv[3])
for _ in range(100):
    if marker.exists(): break
    time.sleep(.01)
proof=pathlib.Path(sys.argv[4]); proof.write_text(json.dumps({'kind':'reviewer_started','action_id':action,'generation':generation,'reviewer_pid':proc.pid}))
relay.record_next_action_started(db,action,generation,token,{'path':str(proof),'sha256':hashlib.sha256(proof.read_bytes()).hexdigest()})
db.close()
''')
        self.declare([sys.executable, str(adapter), str(SCRIPTS), str(reviewer),
                      str(marker), str(self.root/'review-proof.json')])
        # Worker process records completion while the coordinator is absent.
        subprocess.run([sys.executable, str(SCRIPTS/'relay.py'), '--state', str(self.root/'relay.sqlite'),
                        'emit', '--job', 'native-job', '--attempt', 'one', '--sender', 'native-worker',
                        '--kind', 'native-completed', '--artifact', str(self.result),
                        '--event-id', 'native-done'], check=True, capture_output=True)
        # Completion is deliberately unacknowledged: the independent monitor
        # must still execute the pre-authorized continuation.
        self.assertIsNone(self.db.execute('SELECT acknowledged FROM events WHERE id=?', ('native-done',)).fetchone()[0])
        # Scheduled monitor fixture runs in its own process. It is not a claim
        # that the host has a real Codex idle-wake route installed.
        monitor_cmd = [sys.executable, str(SCRIPTS/'monitor.py'), '--state',
                       str(self.root/'relay.sqlite'), '--project', 'sales', '--recover']
        monitors = [subprocess.Popen(monitor_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                     text=True) for _ in range(2)]
        outputs = []
        for proc in monitors:
            stdout, stderr = proc.communicate(timeout=5)
            self.assertEqual(proc.returncode, 0, stderr)
            outputs.append(stdout)
        self.assertEqual(sum('"status": "delivered"' in output for output in outputs), 1)
        second = subprocess.run([sys.executable, str(SCRIPTS/'monitor.py'), '--state',
                                 str(self.root/'relay.sqlite'), '--project', 'sales', '--recover'],
                                check=True, capture_output=True, text=True)
        self.assertNotIn('"status": "delivered"', second.stdout)
        deadline = time.time()+5
        while time.time() < deadline and relay.next_action(self.db, 'review-after-native')['state'] != 'action_started':
            time.sleep(.02)
        row = relay.next_action(self.db, 'review-after-native')
        self.assertEqual(row['state'], 'action_started')
        self.assertTrue(row['acceptance_met'])
        self.assertIsNotNone(row['queued_at'])
        self.assertIsNotNone(row['delivered_at'])
        self.assertIsNotNone(row['awake_at'])
        self.assertIsNotNone(row['action_started_at'])
        self.assertEqual(marker.read_text(), 'started\n')
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM next_actions WHERE state=?', ('action_started',)).fetchone()[0], 1)
        completed_at = datetime.fromisoformat(self.db.execute(
            'SELECT created FROM events WHERE id=?', ('native-done',)).fetchone()[0])
        started_at = datetime.fromisoformat(row['action_started_at'])
        self.assertLess((started_at - completed_at).total_seconds(), 30)
        self.assertLessEqual(started_at, datetime.fromisoformat(row['deadline_at']))

    def test_stale_generation_refuses_recovery_and_completion_is_immutable(self):
        self.declare([sys.executable, str(self.root/'coordinator.py')])
        relay.emit(self.db, 'native-job', 'one', 'native-worker', 'native-completed',
                   self.result, 'native-done')
        with self.assertRaises(ValueError):
            relay.emit(self.db, 'native-job', 'one', 'native-worker', 'native-completed',
                       self.result, 'native-other')
        relay.transfer_project(self.db, 'sales', 1, '16f55728-e1f6-41aa-b0ee-9d9674a688d6')
        self.assertIsNone(relay.next_action(self.db, 'review-after-native')['claim_token'])
        result = monitor.recover_next_actions(self.db, project='sales')
        self.assertEqual(result[0]['status'], 'not_claimed')

    def test_takeover_lists_unlaunched_native_attempt_without_fabricated_ack(self):
        relay.transfer_project(self.db, 'sales', 1, '16f55728-e1f6-41aa-b0ee-9d9674a688d6')
        roster = relay.takeover_roster(self.db, 'sales', 2)
        self.assertEqual([(r['job'],r['attempt'],r['status']) for r in roster],
                         [('native-job','one','pending_next_packet')])
        self.assertIsNone(roster[0]['acknowledged'])


if __name__ == '__main__':
    unittest.main()
