from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).parents[1] / 'skills/interchange/scripts'))
import retry_cancelled_ci as ci
import watch_pr_checks as watch


class RetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.policy = dict(repo='owner/repo', pr=12, head='a'*40, run_id=42,
                           reason='verified repo concurrency cancellation', retry_authorized=True)
        self.calls = []
        self.active = False
        self.moved = False
        self.fail_post = False

    def api(self, args):
        self.calls.append(args)
        if args[0] == 'pr':
            return dict(headRefOid='b'*40 if self.moved else 'a'*40, state='OPEN')
        if '--method' in args:
            if self.fail_post:
                raise RuntimeError('lost response')
            return None
        if '--paginate' in args:
            return [{'workflow_runs': []}, {'workflow_runs': [{'status': 'in_progress'}] if self.active else []}]
        return dict(head_sha='a'*40, status='completed', conclusion='cancelled', workflow_id=7)

    def test_retries_once_and_preserves_uncertainty(self):
        self.fail_post = True
        with self.assertRaises(RuntimeError):
            ci.retry(self.policy, self.tmp.name, self.api)
        self.assertEqual(ci.retry(self.policy, self.tmp.name, self.api)['state'], 'reconcile')
        self.assertEqual(sum('--method' in a for a in self.calls), 1)

    def test_active_other_pr_on_second_page_prevents_retry_then_allows(self):
        self.active = True
        self.assertEqual(ci.retry(self.policy, self.tmp.name, self.api)['state'], 'waiting-for-lane')
        self.active = False
        self.assertEqual(ci.retry(self.policy, self.tmp.name, self.api)['state'], 'retry-requested')
        self.assertEqual(ci.retry(self.policy, self.tmp.name, self.api)['state'], 'reconcile')

    def test_verified_lane_excludes_unrelated_workflow(self):
        self.active = True
        self.policy['lane_workflow_ids'] = [7]
        self.assertEqual(ci.retry(self.policy, self.tmp.name, self.api)['state'], 'retry-requested')

    def test_superseded_head_never_restarted(self):
        self.moved = True
        self.assertEqual(ci.retry(self.policy, self.tmp.name, self.api)['state'], 'superseded')
        self.assertFalse(any('--method' in a for a in self.calls))

    def test_intentional_or_unknown_cancellation_needs_authorization(self):
        self.policy['retry_authorized'] = False
        with self.assertRaises(ValueError):
            ci.retry(self.policy, self.tmp.name, self.api)
        self.assertEqual(self.calls, [])

    def test_cancelled_check_is_incomplete_not_failed_or_green(self):
        def api(args):
            if args[0] == 'pr': return {'headRefOid': 'a'*40}, None
            return [{'check_runs': [{'name': 'ci', 'status': 'completed', 'conclusion': 'cancelled'}]}], None
        state, lines = {}, []
        self.assertTrue(watch.poll_once('owner/repo#12', state, api, lines.append))
        self.assertTrue(state['incomplete'])
        self.assertFalse(state['failed'])
        self.assertIn('INCOMPLETE', lines[-1])
