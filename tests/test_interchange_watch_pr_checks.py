from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).parents[1] / 'skills/interchange/scripts'))
import watch_pr_checks as watch


class FakeGh:
    """Scripted gh responses: a list of (head_sha, runs|None) per poll."""

    def __init__(self, polls):
        self.polls = list(polls)
        self.current = None

    def __call__(self, args):
        if args[0] == 'pr':
            self.current = self.polls.pop(0)
            sha = self.current[0]
            return ({'headRefOid': sha}, None) if sha else (None, 'HTTP 502')
        runs = self.current[1]
        if runs is None:
            return None, 'no check runs'
        return {'check_runs': [{'name': n, 'status': s, 'conclusion': c} for n, s, c in runs]}, None


class WatchPrChecksTests(unittest.TestCase):
    def run_polls(self, polls):
        fake, out, state, finished = FakeGh(polls), [], {}, []
        for _ in polls:
            finished.append(watch.poll_once('o/r#1', state, fetch=fake, emit=out.append))
        return out, finished

    def test_fetch_failure_is_reported_not_silent(self):
        out, finished = self.run_polls([(None, None)])
        self.assertIn('NO DATA', out[0])
        self.assertEqual(finished, [False])

    def test_every_terminal_conclusion_is_emitted_and_failure_named(self):
        out, finished = self.run_polls([('a' * 40, [('build', 'completed', 'failure'), ('lint', 'completed', 'success')])])
        self.assertTrue(any('build: failure' in line for line in out))
        self.assertIn('FAILED build', out[-1])
        self.assertEqual(finished, [True])

    def test_green_on_an_old_head_is_not_reported_for_the_new_head(self):
        out, finished = self.run_polls([
            ('a' * 40, [('build', 'in_progress', None)]),
            ('b' * 40, [('build', 'queued', None)]),
            ('b' * 40, [('build', 'completed', 'success')]),
        ])
        self.assertTrue(any('head moved' in line for line in out))
        self.assertEqual(finished, [False, False, True])
        self.assertIn('bbbbbbbb ALL CHECKS DONE: all green', out[-1])

    def test_no_checks_yet_is_not_done(self):
        out, finished = self.run_polls([('c' * 40, [])])
        self.assertIn('no checks registered yet', out[0])
        self.assertEqual(finished, [False])


if __name__ == '__main__':
    unittest.main()
