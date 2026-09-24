import importlib.util
from pathlib import Path
import unittest
s = importlib.util.spec_from_file_location('schedule_reservations', Path(__file__).parents[1] / 'skills/delivery-orchestrator/scripts/check_schedule.py')
m = importlib.util.module_from_spec(s); s.loader.exec_module(m)

class ReservationTests(unittest.TestCase):
    def lease(self, job, **kw):
        return dict(id=job, job=job, state='held', repository='o/r', **kw)
    def test_same_file_or_parent_directory_conflicts(self):
        for paths in [['src/Program.cs'], ['src/']]:
            self.assertTrue(m.reservation_conflicts([self.lease('a', paths=paths), self.lease('b', paths=['src/Program.cs'])]))
    def test_shared_test_runtime_conflicts_across_repos(self):
        a = self.lease('a', resources=['db:fixture']); b = self.lease('b', resources=['db:fixture']); b['repository'] = 'o/other'
        self.assertTrue(m.reservation_conflicts([a,b]))
    def test_disjoint_paths_and_released_writer_allowed(self):
        a=self.lease('a',paths=['src/A.cs']); b=self.lease('b',paths=['src/B.cs'])
        self.assertEqual(m.reservation_conflicts([a,b]), [])
        b.update(paths=['src/A.cs'],state='released')
        self.assertEqual(m.reservation_conflicts([a,b]), [])
    def test_traversal_and_globs_rejected(self):
        for p in ['../outside','src/*','/abs','src/./A.cs','src//A.cs','src\\A.cs']:
            self.assertTrue(m.reservation_conflicts([self.lease('a',paths=[p])]))
