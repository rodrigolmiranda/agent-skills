import importlib.util
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
    def execute(self,code,timeout=3,limit=4096):
        return run_job.run({'job':'smoke','attempt':'one','sender':'fixture','cwd':str(self.root),
                            'argv':[sys.executable,'-c',code],'timeout_seconds':timeout,'max_output_bytes':limit},
                           self.state,self.root/'run')
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
    def test_output_limit_caps_artifact(self):
        result=self.execute('print("x"*50000)',limit=1024)
        self.assertEqual(result['result']['process_outcome'],'output_limit')
        self.assertLessEqual((self.root/'run/stdout.log').stat().st_size,1024)
    def test_error_exit_is_preserved(self):
        result=self.execute('raise SystemExit(7)')
        self.assertEqual(result['result']['exit_code'],7)
        self.assertTrue(result['result']['ownership_check_required'])

if __name__=='__main__':unittest.main()
