import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest import mock

SCRIPTS=Path(__file__).parents[1]/'skills/interchange/scripts'
sys.path.insert(0,str(SCRIPTS))
import relay
import run_job

class RunnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.state=self.root/'state.db'
        db=relay.connect(self.state);relay.register(db,'smoke','one','fixture',self.root);db.close()
    def tearDown(self):self.tmp.cleanup()
    def execute(self,code,timeout=3,limit=4096,**manifest):
        config={'job':'smoke','attempt':'one','sender':'fixture','cwd':str(self.root),
                'argv':[sys.executable,'-c',code],'timeout_seconds':timeout,'max_output_bytes':limit}
        config.update(manifest)
        return run_job.run(config,self.state,self.root/'run')
    def test_exit_is_not_acceptance_and_second_launch_refused(self):
        result=self.execute('print("result")')
        self.assertEqual(result['result']['exit_code'],0)
        self.assertFalse(result['result']['accepted'])
        self.assertEqual(result['notification']['delivery'],'manual')
        with self.assertRaises(FileExistsError):self.execute('print("duplicate")')
    def test_attempt_cannot_launch_again_in_a_different_directory(self):
        self.execute('print("once")')
        with self.assertRaises(FileExistsError):
            run_job.run({'job':'smoke','attempt':'one','sender':'fixture','cwd':str(self.root),
                         'argv':[sys.executable,'-c','print("duplicate")'],'timeout_seconds':3},
                        self.state,self.root/'other')

    def test_long_valid_ids_still_emit_terminal_event(self):
        job='j'*100;attempt='a'*100
        db=relay.connect(self.state);relay.register(db,job,attempt,'fixture',self.root);db.close()
        result=run_job.run({'job':job,'attempt':attempt,'sender':'fixture','cwd':str(self.root),
                           'argv':[sys.executable,'-c','print("done")'],'timeout_seconds':3},
                          self.state,self.root/'long')
        self.assertEqual(result['notification']['delivery'],'manual')
        self.assertLessEqual(len(result['notification']['id']),100)

    def test_timeout_is_bounded_and_not_completion(self):
        result=self.execute('import time;time.sleep(5)',timeout=.05)
        self.assertEqual(result['result']['process_outcome'],'timeout')
        self.assertTrue(result['result']['ownership_check_required'])
    def test_output_limit_caps_artifact_but_drains_to_final(self):
        final=self.root/'run/final.json'
        code=('import os;print("x"*50000);'
              'open(os.environ["INTERCHANGE_FINAL_ARTIFACT"],"w").write("FINAL")')
        result=self.execute(code,limit=1024,final_artifact=str(final))
        receipt=result['result']
        self.assertEqual(receipt['process_outcome'],'exited')
        self.assertTrue(receipt['output_truncated'])
        self.assertGreater(receipt['output_bytes_seen'],receipt['output_bytes_captured'])
        self.assertLessEqual(receipt['output_bytes_captured'],1024)
        self.assertLessEqual((self.root/'run/stdout.log').stat().st_size,1024)
        self.assertEqual(receipt['final_artifact']['status'],'validated')
        self.assertTrue(receipt['final_artifact_validated'])
        self.assertFalse(receipt['worker_result_verified'])
        self.assertFalse(receipt['accepted'])

    def test_output_limit_kill_is_explicit(self):
        result=self.execute('import time;print("x"*50000,flush=True);time.sleep(5)',limit=1024,
                            kill_on_output_limit=True)
        receipt=result['result']
        self.assertEqual(receipt['process_outcome'],'output_limit')
        self.assertTrue(receipt['output_truncated'])
        self.assertEqual(receipt['output_limit_action'],'kill')
        self.assertTrue(receipt['ownership_check_required'])

    def test_deadline_wins_while_output_is_drained(self):
        result=self.execute('import time;print("x"*50000,flush=True);time.sleep(5)',timeout=.05,limit=1024)
        receipt=result['result']
        self.assertEqual(receipt['process_outcome'],'timeout')
        self.assertTrue(receipt['output_truncated'])
        self.assertTrue(receipt['ownership_check_required'])

    def test_short_stream_event_is_visible_before_child_exits(self):
        release = self.root / 'release-child'
        code = ('import json,pathlib,time\n'
                'print(json.dumps({"type":"assistant","message":{"content":[]}}),flush=True)\n'
                f'p=pathlib.Path({str(release)!r})\n'
                'while not p.exists(): time.sleep(.02)\n')
        finished = []
        thread = threading.Thread(target=lambda: finished.append(self.execute(code, timeout=5)))
        thread.start()
        log = self.root / 'run/stdout.log'
        seen_while_running = False
        try:
            deadline = time.monotonic() + 2
            while time.monotonic() < deadline:
                if log.exists() and '"type": "assistant"' in log.read_text():
                    seen_while_running = thread.is_alive()
                    break
                time.sleep(.02)
        finally:
            release.touch()
            thread.join(timeout=6)
        self.assertTrue(seen_while_running)
        self.assertFalse(thread.is_alive())
        self.assertEqual(finished[0]['result']['exit_code'], 0)

    def test_stream_final_accepts_one_fenced_json_verdict_with_intro(self):
        directory=self.root/'review';directory.mkdir()
        target=directory/'review.json'
        verdict={'reviewed_head':'a'*40,'verdict':'passed','findings':[]}
        final=('I reviewed the code only; tests could not run in this sandbox.\n\n'
               '```json\n'+json.dumps(verdict,indent=2)+'\n```')
        (directory/'stdout.log').write_text(json.dumps({'type':'result','result':final})+'\n')
        run_job._collect_stream_final({'final_artifact_from_stdout':True},target,directory)
        self.assertEqual(json.loads(target.read_text()),verdict)

    def test_stream_final_rejects_competing_or_incomplete_fences(self):
        directory=self.root/'review';directory.mkdir()
        target=directory/'review.json'
        body=json.dumps({'reviewed_head':'a'*40,'verdict':'passed'})
        candidates=[
            'Intro\n```json\n'+body+'\n```\n```json\n'+body+'\n```',
            'Intro {"verdict":"passed"}\n```json\n'+body+'\n```',
            'Intro\n```json\n'+body,
            'Intro\n```json\n'+body+'\n```\n{"reviewed_head":"b"}',
            'Intro\n```json\n'+body+' extra\n```',
        ]
        for candidate in candidates:
            with self.subTest(candidate=candidate[:35]):
                (directory/'stdout.log').write_text(json.dumps({'type':'result','result':candidate})+'\n')
                run_job._collect_stream_final({'final_artifact_from_stdout':True},target,directory)
                self.assertFalse(target.exists())
        (directory/'stdout.log').write_text(json.dumps({'type':'result','result':body})+'\n')
        run_job._collect_stream_final({'final_artifact_from_stdout':True},target,directory)
        self.assertEqual(json.loads(target.read_text())['reviewed_head'],'a'*40)

    def test_missing_final_artifact_stays_unverified(self):
        result=self.execute('print("completed")',final_artifact=str(self.root/'run/missing.json'))
        receipt=result['result']
        self.assertEqual(receipt['final_artifact']['status'],'missing')
        self.assertFalse(receipt['final_artifact_validated'])
        self.assertFalse(receipt['worker_result_verified'])
        self.assertFalse(receipt['accepted'])

    def test_reserved_final_artifacts_are_rejected_before_launch(self):
        for name in ('process-result.json','runner.json','stdout.log','stderr.log'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                self.execute('print("should not launch")',final_artifact=str(self.root/'run'/name))
        db=relay.connect(self.state)
        self.assertIsNone(db.execute('SELECT 1 FROM launches WHERE job=? AND attempt=?',
                                     ('smoke','one')).fetchone())
        db.close()

    def test_final_artifact_symlink_escape_is_rejected_at_proof_time(self):
        outside=self.root/'outside-final.json'
        outside.write_text('outside')
        code=('from pathlib import Path;import os;'
              'Path(os.environ["INTERCHANGE_FINAL_ARTIFACT"]).symlink_to(' +
              json.dumps(str(outside)) + ')')
        result=self.execute(code,final_artifact=str(self.root/'run'/'final.json'))
        proof=result['result']['final_artifact']
        self.assertEqual(proof['status'],'outside_artifact_root')
        self.assertFalse(proof['validated'])
        self.assertFalse(result['result']['worker_result_verified'])
        self.assertFalse(result['result']['accepted'])

    def test_worker_stdin_is_closed(self):
        result=self.execute('import sys;print(repr(sys.stdin.read()))')
        self.assertEqual(result['result']['exit_code'],0)
        self.assertIn("''",(self.root/'run/stdout.log').read_text())

    def test_child_pwd_is_bound_to_manifest_cwd(self):
        code=('import json,os;print(json.dumps({"cwd":os.getcwd(),'
              '"pwd":os.environ.get("PWD"),"oldpwd":os.environ.get("OLDPWD")}))')
        with mock.patch.dict('os.environ', {'PWD': str(self.root/'wrong-checkout'),
                                            'OLDPWD': str(self.root/'stale-checkout')}):
            result=self.execute(code)
        self.assertEqual(result['result']['exit_code'],0)
        child=json.loads((self.root/'run/stdout.log').read_text())
        self.assertEqual(child['cwd'],str(self.root.resolve()))
        self.assertEqual(child['pwd'],child['cwd'])
        self.assertIsNone(child['oldpwd'])

    def test_env_map_reaches_the_worker_and_refuses_secret_names(self):
        result=self.execute('import os;print(os.environ["WORKER_CONFIG"])',env={'WORKER_CONFIG':'{"a":1}'})
        self.assertEqual(result['result']['exit_code'],0)
        self.assertIn('{"a":1}',(self.root/'run/stdout.log').read_text())
        for bad in ({'GH_TOKEN':'x'},{'lower':'x'},{'OK_NAME':1}):
            with self.assertRaises(ValueError):
                run_job._manifest_env({'env':bad})

    def test_final_artifact_source_inside_cwd_is_collected_and_proven(self):
        (self.root/'wt').mkdir()
        code='open(".interchange-final.md","w").write("DONE")'
        result=self.execute(code,cwd=str(self.root/'wt'),final_artifact_source='.interchange-final.md')
        proof=result['result']['final_artifact']
        self.assertTrue(proof['validated'])
        self.assertEqual((self.root/'run/final.md').read_text(),'DONE')

    def test_final_artifact_source_env_points_at_the_writable_source(self):
        (self.root/'wt').mkdir()
        code='import os;open(os.environ["INTERCHANGE_FINAL_ARTIFACT"],"w").write("VIA ENV")'
        result=self.execute(code,cwd=str(self.root/'wt'),final_artifact_source='attempt-one-final.md')
        self.assertTrue(result['result']['final_artifact']['validated'])
        self.assertEqual((self.root/'run/final.md').read_text(),'VIA ENV')

    def test_a_final_left_by_an_earlier_attempt_is_refused_before_launch(self):
        (self.root/'wt').mkdir();(self.root/'wt/old-final.md').write_text('OLD ATTEMPT RESULT')
        with self.assertRaises(ValueError):
            self.execute('pass',cwd=str(self.root/'wt'),final_artifact_source='old-final.md')

    def test_collection_never_writes_through_a_planted_destination_symlink(self):
        (self.root/'wt').mkdir();outside=self.root/'outside.txt';outside.write_text('PRESERVE')
        # The worker plants the link while it runs, after the launch-time containment check.
        code=('import os;open("result.md","w").write("REPLACED");'
              f'os.symlink({str(outside)!r},{str(self.root/"run/final.md")!r})')
        result=self.execute(code,cwd=str(self.root/'wt'),final_artifact_source='result.md')
        self.assertEqual(outside.read_text(),'PRESERVE')
        self.assertFalse(result['result']['final_artifact']['validated'])

    def test_final_artifact_source_cannot_leave_cwd(self):
        (self.root/'wt').mkdir()
        with self.assertRaises(ValueError):
            run_job._final_artifact_source({'final_artifact_source':'../outside.md'},(self.root/'wt').resolve())
    def test_error_exit_is_preserved(self):
        result=self.execute('raise SystemExit(7)')
        self.assertEqual(result['result']['exit_code'],7)
        self.assertTrue(result['result']['ownership_check_required'])

if __name__=='__main__':unittest.main()
