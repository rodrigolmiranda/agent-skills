import hashlib
import concurrent.futures
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

    def route(self, coordinator=None, generation=1):
        coordinator = coordinator or self.coordinator
        base = datetime.now(timezone.utc)
        iso = lambda offset: (base + timedelta(seconds=offset)).isoformat()
        proof = {'schedule_id':'fixture-schedule','coordinator_id':coordinator,
                 'ownership_generation':generation, 'worker_completed_at':iso(-10),
                 'queued_at':iso(-9), 'delivered_at':iso(-8), 'awake_at':iso(-7),
                 'action_started_at':iso(-6), 'action_id':'prior-smoke',
                 'execution_evidence':{'fixture':'independent-supervisor'}}
        path = self.root/f'smoke-{generation}.json'
        path.write_text(json.dumps(proof))
        return {'kind':'supervisor','schedule_id':'fixture-schedule','owner':'fixture-supervisor',
                'coordinator_id':coordinator,'ownership_generation':generation,
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
        reviewer.write_text('import json,pathlib,sys,time\nwith pathlib.Path(sys.argv[1]).open("a") as marker: marker.write("started\\n")\nprint(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"review active"}}),flush=True)\ntime.sleep(2)\n')
        adapter = self.root/'coordinator.py'
        adapter.write_text('''import hashlib,json,os,pathlib,subprocess,sys,time
sys.path.insert(0,sys.argv[1])
import relay
db=relay.connect(os.environ['INTERCHANGE_RELAY_STATE'])
action=os.environ['INTERCHANGE_ACTION_ID']; generation=int(os.environ['INTERCHANGE_OWNERSHIP_GENERATION'])
token=os.environ['INTERCHANGE_CLAIM_TOKEN']
relay.acknowledge_recovery_awake(db,action,generation,token)
review_dir=pathlib.Path(sys.argv[4]).parent/'review-attempt'; review_dir.mkdir()
relay.register(db,'review-job','one','reviewer',review_dir,os.environ['INTERCHANGE_COORDINATOR_ID'])
relay.bind_attempt(db,os.environ['INTERCHANGE_PROJECT'],'review-job','one',generation)
stdout=(review_dir/'stdout.log').open('w')
with db: db.execute('INSERT INTO launches VALUES (?,?,?,?)',('review-job','one',str(review_dir),str(time.time())))
proc=subprocess.Popen([sys.executable,sys.argv[2],sys.argv[3]],stdout=stdout,start_new_session=True)
marker=pathlib.Path(sys.argv[3])
for _ in range(100):
    if marker.exists() and (review_dir/'stdout.log').exists() and (review_dir/'stdout.log').stat().st_size: break
    time.sleep(.01)
proof=pathlib.Path(sys.argv[4]); proof.write_text(json.dumps({'kind':'reviewer_started','action_id':action,'generation':generation,'reviewer_job':'review-job','reviewer_attempt':'one'}))
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

    def test_pid_or_launch_row_without_reviewer_activity_cannot_prove_start(self):
        self.declare([sys.executable, str(self.root/'coordinator.py')])
        relay.emit(self.db, 'native-job', 'one', 'native-worker', 'native-completed',
                   self.result, 'native-done')
        claim = relay.claim_next_action(self.db, 'review-after-native')
        relay.mark_recovery_delivered(self.db, 'review-after-native', 1, claim['claim_token'], os.getpid())
        relay.acknowledge_recovery_awake(self.db, 'review-after-native', 1, claim['claim_token'])
        proof_path = self.root/'start.json'
        def record(proof):
            proof_path.write_text(json.dumps(proof))
            return relay.record_next_action_started(self.db, 'review-after-native', 1,
                    claim['claim_token'], {'path':str(proof_path),
                                           'sha256':hashlib.sha256(proof_path.read_bytes()).hexdigest()})
        identity = {'kind':'reviewer_started','action_id':'review-after-native','generation':1}
        with self.assertRaisesRegex(ValueError, 'bound reviewer'):
            record({**identity,'reviewer_pid':os.getpid()})
        review_dir = self.root/'review'; review_dir.mkdir()
        relay.register(self.db, 'review-job', 'one', 'reviewer', review_dir, self.coordinator)
        relay.bind_attempt(self.db, 'sales', 'review-job', 'one', 1)
        self.db.execute('INSERT INTO launches VALUES (?,?,?,?)',
                        ('review-job','one',str(review_dir),str(time.time())))
        self.db.commit()
        bound = {**identity,'reviewer_job':'review-job','reviewer_attempt':'one'}
        with self.assertRaisesRegex(ValueError, 'no structured'):
            record(bound)
        (review_dir/'stdout.log').write_text('sleeping\n')
        with self.assertRaisesRegex(ValueError, 'no structured'):
            record(bound)
        self.assertFalse(relay.next_action(self.db, 'review-after-native')['acceptance_met'])
        (review_dir/'stdout.log').write_text(json.dumps(
            {'type':'item.completed','item':{'type':'agent_message','text':'review active'}})+'\n')
        self.assertTrue(record(bound)['acceptance_met'])

    def test_completion_racing_takeover_is_adopted_once_by_new_owner(self):
        new_coordinator = '16f55728-e1f6-41aa-b0ee-9d9674a688d6'
        marker = self.root/'adopted-review.txt'
        reviewer = self.root/'reviewer.py'
        reviewer.write_text('import json,pathlib,sys,time\npathlib.Path(sys.argv[1]).write_text("started")\nprint(json.dumps({"type":"item.completed","item":{"type":"agent_message","text":"review active"}}),flush=True)\ntime.sleep(1)\n')
        adapter = self.root/'coordinator.py'
        adapter.write_text('''import hashlib,json,os,pathlib,subprocess,sys,time
sys.path.insert(0,sys.argv[1]); import relay
db=relay.connect(os.environ['INTERCHANGE_RELAY_STATE'])
action=os.environ['INTERCHANGE_ACTION_ID']; gen=int(os.environ['INTERCHANGE_OWNERSHIP_GENERATION']); token=os.environ['INTERCHANGE_CLAIM_TOKEN']
relay.acknowledge_recovery_awake(db,action,gen,token)
review_dir=pathlib.Path(sys.argv[4]).parent/'adopted-review-attempt'; review_dir.mkdir()
relay.register(db,'adopted-review','one','reviewer',review_dir,os.environ['INTERCHANGE_COORDINATOR_ID'])
relay.bind_attempt(db,os.environ['INTERCHANGE_PROJECT'],'adopted-review','one',gen)
with (review_dir/'stdout.log').open('w') as stdout:
    with db: db.execute('INSERT INTO launches VALUES (?,?,?,?)',('adopted-review','one',str(review_dir),str(time.time())))
    proc=subprocess.Popen([sys.executable,sys.argv[2],sys.argv[3]],stdout=stdout,start_new_session=True)
    for _ in range(100):
        if pathlib.Path(sys.argv[3]).exists() and (review_dir/'stdout.log').stat().st_size: break
        time.sleep(.01)
    proof=pathlib.Path(sys.argv[4]); proof.write_text(json.dumps({'kind':'reviewer_started','action_id':action,'generation':gen,'reviewer_job':'adopted-review','reviewer_attempt':'one'}))
    relay.record_next_action_started(db,action,gen,token,{'path':str(proof),'sha256':hashlib.sha256(proof.read_bytes()).hexdigest()})
db.close()
''')
        self.declare([sys.executable, str(adapter), str(SCRIPTS), str(reviewer),
                      str(marker), str(self.root/'adopted-proof.json')])
        # Simulate a database created before next_action_history existed.
        self.db.execute('DELETE FROM next_action_history WHERE action_id=?', ('review-after-native',))
        self.db.commit()
        def emit():
            db = relay.connect(self.root/'relay.sqlite')
            try:
                relay.emit(db, 'native-job', 'one', 'native-worker', 'native-completed',
                           self.result, 'native-done')
            finally:
                db.close()
        def transfer():
            db = relay.connect(self.root/'relay.sqlite')
            try:
                relay.transfer_project(db, 'sales', 1, new_coordinator)
            finally:
                db.close()
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            list(pool.map(lambda task: task(), (emit, transfer)))
        self.assertEqual(relay.current_generation(self.db, 'sales'), 2)
        self.assertEqual(monitor.recover_next_actions(self.db, project='sales')[0]['status'], 'not_claimed')
        with self.assertRaisesRegex(ValueError, 'new recovery route'):
            relay.adopt_next_action(self.db, 'review-after-native', 1, 2, self.route())
        new_route = self.route(new_coordinator, 2)
        adopted = relay.adopt_next_action(self.db, 'review-after-native', 1, 2, new_route)
        self.assertEqual(adopted['action_id'], 'review-after-native')
        self.assertEqual(adopted['generation'], 2)
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM next_action_history WHERE action_id=?',
                                         ('review-after-native',)).fetchone()[0], 2)
        with self.assertRaises(ValueError):
            relay.adopt_next_action(self.db, 'review-after-native', 1, 2, new_route)
        monitor_cmd = [sys.executable, str(SCRIPTS/'monitor.py'), '--state',
                       str(self.root/'relay.sqlite'), '--project', 'sales', '--recover']
        first = subprocess.run(monitor_cmd, check=True, capture_output=True, text=True)
        self.assertIn('"status": "delivered"', first.stdout)
        second = subprocess.run(monitor_cmd, check=True, capture_output=True, text=True)
        self.assertNotIn('"status": "delivered"', second.stdout)
        deadline = time.time()+5
        while time.time() < deadline and relay.next_action(self.db, 'review-after-native')['state'] != 'action_started':
            time.sleep(.02)
        self.assertTrue(relay.next_action(self.db, 'review-after-native')['acceptance_met'])
        self.assertEqual(marker.read_text(), 'started')

    def test_same_coordinator_new_generation_rejects_old_smoke_and_can_dispose(self):
        self.declare([sys.executable, str(self.root/'coordinator.py')])
        old_route = self.route()
        relay.transfer_project(self.db, 'sales', 1, self.coordinator)
        with self.assertRaisesRegex(ValueError, 'new recovery route'):
            relay.adopt_next_action(self.db, 'review-after-native', 1, 2, old_route)
        new_route = self.route(self.coordinator, 2)
        stopped = relay.dispose_next_action(self.db, 'review-after-native', 1, 2,
                                             new_route, 'Accepted scope withdrawn by owner')
        self.assertEqual(stopped['state'], 'disposed')
        relay.emit(self.db, 'native-job', 'one', 'native-worker', 'native-completed',
                   self.result, 'native-done')
        self.assertEqual(monitor.recover_next_actions(self.db, project='sales'), [])
        self.assertEqual(self.db.execute('SELECT COUNT(*) FROM next_action_history WHERE action_id=?',
                                         ('review-after-native',)).fetchone()[0], 2)


if __name__ == '__main__':
    unittest.main()
