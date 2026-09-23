import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

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

    def test_error_exit_is_preserved(self):
        result=self.execute('raise SystemExit(7)')
        self.assertEqual(result['result']['exit_code'],7)
        self.assertTrue(result['result']['ownership_check_required'])

if __name__=='__main__':unittest.main()
