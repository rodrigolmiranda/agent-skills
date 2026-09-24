"""Controlled publication fixtures. These do not provision host UID isolation."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

SCRIPTS = Path(__file__).parents[1] / 'skills/interchange/scripts'
sys.path.insert(0, str(SCRIPTS))
import post_return
import relay
import run_job


def git(cwd, *args):
    return subprocess.run(['git', *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.remote = self.root / 'remote.git'
        self.repo.mkdir()
        git(self.repo, 'init')
        git(self.repo, 'config', 'user.email', 'fixture@example.test')
        git(self.repo, 'config', 'user.name', 'Fixture')
        (self.repo / 'owned.txt').write_text('base\n')
        git(self.repo, 'add', 'owned.txt')
        git(self.repo, 'commit', '-m', 'base')
        git(self.repo, 'branch', '-M', 'test')
        git(self.root, 'init', '--bare', str(self.remote))
        git(self.repo, 'remote', 'add', 'origin', str(self.remote))
        git(self.repo, 'push', 'origin', 'test')
        self.start = git(self.repo, 'rev-parse', 'HEAD')
        git(self.repo, 'checkout', '-b', 'feature/one')
        (self.repo / 'owned.txt').write_text('changed\n')
        git(self.repo, 'add', 'owned.txt')
        git(self.repo, 'commit', '-m', 'implementation')
        self.head = git(self.repo, 'rev-parse', 'HEAD')
        self.attempt = self.root / 'attempt'
        self.attempt.mkdir()
        self.handover = self.attempt / 'final.json'
        self.handover.write_text(json.dumps({'job': 'job', 'attempt': 'one',
                                             'packet_revision': 'r1', 'head': self.head,
                                             'result': 'ready_for_review',
                                             'required_gates': {'unit': 'passed'}}))
        self.result = {'job': 'job', 'attempt': 'one', 'process_outcome': 'exited', 'exit_code': 0,
                       'final_artifact': {'path': str(self.handover), 'validated': True,
                                          'sha256': hashlib.sha256(self.handover.read_bytes()).hexdigest()},
                       'publication_preflight': {'git_control_digest': post_return._control_digest(self.repo)}}
        self.manifest = {'cwd': str(self.repo), 'execution_isolation': {'mode': 'distinct_uid', 'uid': 1002}}
        self.spec = {'version': 1, 'kind': 'implementation', 'project': 'project', 'generation': 1,
                     'packet_revision': 'r1', 'start_head': self.start, 'branch': 'feature/one',
                     'base': 'test', 'remote': 'origin', 'remote_url': str(self.remote),
                     'repository': 'fixture/repo', 'title': 'Implement one',
                     'allowed_paths': ['owned.txt'], 'required_gates': ['unit'],
                     'reviewer_job': 'reviewjob', 'reviewer_sender': 'reviewer',
                     'reviewer': {'adapter': 'claude-headless',
                                  'argv': ['claude', '--no-chrome', '--disallowedTools', 'Browser*',
                                           '--output-format', 'stream-json', '-p', 'review'],
                                  'timeout_seconds': 60,
                                  'execution_isolation': {'mode': 'distinct_uid', 'uid': 1003}}}
        self.state = self.root / 'state.db'
        self.db = relay.connect(self.state)
        relay.register_project(self.db, 'project')
        self.pr = None
        self.creates = 0
        self.reviews = 0
        self.fail_create = False

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def command(self, argv, cwd, timeout=30, input=None, env=None):
        if argv[:2] == ['gh', 'pr']:
            if argv[2] == 'list':
                return json.dumps([self.pr] if self.pr else []).encode()
            if argv[2] == 'create':
                self.creates += 1
                if self.fail_create:
                    raise post_return.PipelineException('fixture PR unavailable')
                self.pr = {'number': 7, 'url': 'https://example.test/pr/7',
                           'headRefName': 'feature/one', 'baseRefName': 'test',
                           'isDraft': True, 'headRefOid': self.head}
                return b'https://example.test/pr/7'
        return self.real_command(argv, cwd, timeout=timeout, input=input, env=env)

    def review(self, db, spec, head, cwd, directory, state, journal, path):
        self.reviews += 1
        post_return._stage(journal, path, 'review_started', reviewer_attempt='review-' + head[:12],
                           reviewer_directory=str(directory / 'review' / head))

    def execute(self):
        self.real_command = post_return.command
        with mock.patch.object(post_return, 'command', side_effect=self.command), \
             mock.patch.object(post_return, '_reviewer_stage', side_effect=self.review), \
             mock.patch.object(post_return.shutil, 'which', return_value='/usr/bin/true'):
            return post_return.execute(self.spec, self.manifest, self.result,
                                       self.db, self.state, self.attempt)

    def test_valid_return_pushes_once_creates_one_draft_and_starts_one_review(self):
        first = self.execute()
        second = self.execute()
        self.assertEqual(first['stage'], 'review_started')
        self.assertEqual(second['stage'], 'review_started')
        self.assertEqual(git(self.repo, 'ls-remote', '--heads', str(self.remote), 'feature/one').split()[0], self.head)
        self.assertEqual((self.creates, self.reviews), (1, 1))
        self.assertEqual(first['head'], self.head)

    def test_pr_failure_resumes_without_worker_rerun_or_duplicate_push(self):
        self.fail_create = True
        failed = self.execute()
        self.assertEqual(failed['stage'], 'exception')
        self.assertEqual(failed['failed_stage'], 'pushed')
        self.assertEqual(self.creates, 1)
        self.fail_create = False
        done = self.execute()
        self.assertEqual(done['stage'], 'review_started')
        self.assertEqual((self.creates, self.reviews), (2, 1))

    def test_known_gate_failure_and_no_change_do_not_publish(self):
        self.handover.write_text(json.dumps({'job': 'job', 'attempt': 'one',
            'packet_revision': 'r1', 'head': self.head, 'result': 'ready_for_review',
            'required_gates': {'unit': 'failed'}}))
        self.result['final_artifact']['sha256'] = hashlib.sha256(self.handover.read_bytes()).hexdigest()
        failed = self.execute()
        self.assertEqual(failed['stage'], 'exception')
        self.assertIn('required gate failure', failed['error'])
        self.assertEqual((self.creates, self.reviews), (0, 0))

    def test_out_of_scope_or_dirty_worktree_stops_publication(self):
        (self.repo / 'other.txt').write_text('uncommitted')
        failed = self.execute()
        self.assertIn('dirty worker worktree', failed['error'])
        self.assertEqual(self.creates, 0)

    def test_intermediate_out_of_scope_commit_is_not_hidden_by_deletion(self):
        (self.repo / 'secret.txt').write_text('should not be published\n')
        git(self.repo, 'add', 'secret.txt')
        git(self.repo, 'commit', '-m', 'unrelated file')
        git(self.repo, 'rm', 'secret.txt')
        git(self.repo, 'commit', '-m', 'remove unrelated file')
        new_head = git(self.repo, 'rev-parse', 'HEAD')
        self.handover.write_text(json.dumps({'job': 'job', 'attempt': 'one',
            'packet_revision': 'r1', 'head': new_head, 'result': 'ready_for_review',
            'required_gates': {'unit': 'passed'}}))
        self.result['final_artifact']['sha256'] = hashlib.sha256(self.handover.read_bytes()).hexdigest()
        failed = self.execute()
        self.assertIn('outside owned paths', failed['error'])
        self.assertEqual(self.creates, 0)

    def test_generation_transfer_fences_push(self):
        relay.transfer_project(self.db, 'project', 1)
        failed = self.execute()
        self.assertIn('stale', failed['error'])
        self.assertEqual(self.creates, 0)

    def test_head_change_invalidates_previous_review(self):
        self.assertEqual(self.execute()['stage'], 'review_started')
        (self.repo / 'owned.txt').write_text('second change\n')
        git(self.repo, 'add', 'owned.txt')
        git(self.repo, 'commit', '-m', 'new head')
        failed = self.execute()
        self.assertEqual(failed['stage'], 'exception')
        self.assertIn('handover head does not match', failed['error'])
        self.assertEqual((self.creates, self.reviews), (1, 1))

    def test_reviewer_browser_and_route_preflight(self):
        self.spec['reviewer']['argv'].remove('--no-chrome')
        self.assertIn('no-chrome', self.execute()['error'])
        self.spec['reviewer']['adapter'] = 'codex-headless'
        self.spec['reviewer']['argv'] = ['codex', 'exec', '--sandbox', 'read-only', '--json', 'review']
        self.assertEqual(self.execute()['stage'], 'review_started')

    def test_isolation_configuration_fails_closed_for_same_user(self):
        env = os.environ.copy()
        with self.assertRaises(ValueError):
            run_job._isolated_worker({'post_return': {}, 'execution_isolation': {
                'mode': 'distinct_uid', 'uid': os.geteuid(), 'gid': os.getegid(), 'home': str(self.root)}}, env)
        with self.assertRaises(ValueError):
            run_job._isolated_worker({'post_return': {}}, env)

    def test_hook_config_and_transient_probe_failure_cannot_prove_denial(self):
        git(self.repo, 'config', 'core.hooksPath', str(self.root / 'fake-hooks'))
        failed = self.execute()
        self.assertIn('unsafe worker-controlled Git config', failed['error'])
        self.assertFalse(post_return._permission_denial(b'Could not resolve host: github.com'))
        self.assertFalse(post_return._permission_denial(b'non-fast-forward'))
        self.assertTrue(post_return._permission_denial(b'Permission denied (publickey).'))

    def test_reviewer_pid_or_error_output_is_not_startup(self):
        review_dir = self.root / 'review'
        review_dir.mkdir()
        (review_dir / 'stdout.log').write_text('{"type":"system","subtype":"init"}\n')
        (review_dir / 'stderr.log').write_text('authentication failed\n')
        self.assertFalse(post_return._reviewer_evidence(review_dir, self.spec['reviewer'], self.head))
        (review_dir / 'stdout.log').write_text(json.dumps({'type': 'assistant', 'message': {
            'model': 'claude-opus', 'content': [{'type': 'tool_use', 'name': 'Read'}]}}) + '\n')
        self.assertTrue(post_return._reviewer_evidence(review_dir, self.spec['reviewer'], self.head))


@unittest.skipUnless(hasattr(os, 'geteuid') and os.geteuid() == 0,
                     'requires isolated root test container')
class RootIsolationTests(unittest.TestCase):
    """Actual UID isolation with a root-owned local Git remote and fake model CLI."""
    setUp = PipelineTests.setUp
    tearDown = PipelineTests.tearDown

    def test_distinct_worker_cannot_push_and_reviewer_launches_under_second_uid(self):
        os.chmod(self.root, 0o755)
        worker_uid, reviewer_uid = 1002, 1003
        for name, uid in [('worker-home', worker_uid), ('review-home', reviewer_uid)]:
            home = self.root / name
            home.mkdir(mode=0o700)
            os.chown(home, uid, uid)
        # Worker owns its checkout; the bare remote remains root-owned and read-only to it.
        for path in [self.repo, *self.repo.rglob('*')]:
            os.chown(path, worker_uid, worker_uid)
        db = self.db
        relay.register(db, 'uidworker', 'one', 'worker', self.root)
        worker_code = ("import subprocess;"
                       "r=subprocess.run(['git','-c','safe.directory=*','push','origin','HEAD:refs/heads/feature/one'],"
                       "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);"
                       "print('push_denied='+str(r.returncode!=0),flush=True)")
        worker_manifest = {'job': 'uidworker', 'attempt': 'one', 'sender': 'worker',
                           'cwd': str(self.repo), 'argv': [sys.executable, '-c', worker_code],
                           'timeout_seconds': 10,
                           'execution_isolation': {'mode': 'distinct_uid', 'uid': worker_uid,
                                                   'gid': worker_uid,
                                                   'home': str(self.root / 'worker-home')}}
        worker_receipt = run_job.run(worker_manifest, self.state, self.root / 'uid-attempt')
        self.assertEqual(worker_receipt['result']['exit_code'], 0)
        self.assertIn('push_denied=True', (self.root / 'uid-attempt/stdout.log').read_text())
        self.assertFalse(git(self.repo, 'ls-remote', '--heads', str(self.remote), 'feature/one'))
        # The supervisor can publish the same SHA to that remote.
        subprocess.run(['git', '-c', f'safe.directory={self.repo}', 'push', str(self.remote),
                        f'{self.head}:refs/heads/feature/one'], cwd=self.repo, check=True,
                       capture_output=True)

        fake_bin = self.root / 'bin'
        fake_bin.mkdir(mode=0o755)
        fake = fake_bin / 'claude'
        fake.write_text('#!/usr/bin/env python3\n'
                        'import json,os\n'
                        'from pathlib import Path\n'
                        'assert os.geteuid()==1003\n'
                        'assert Path("owned.txt").read_text()=="changed\\n"\n'
                        'try:\n'
                        '    Path("owned.txt").write_text("illegal")\n'
                        'except PermissionError:\n'
                        '    pass\n'
                        'else:\n'
                        '    raise AssertionError("reviewer can write worker source")\n'
                        'print(json.dumps({"type":"assistant","message":'
                        '{"model":"fixture-claude","content":[{"type":"tool_use","name":"Read"}]}}),flush=True)\n'
                        f'print(json.dumps({{"type":"result","result":json.dumps('
                        f'{{"reviewed_head":"{self.head}","verdict":"passed"}})}}),flush=True)\n')
        fake.chmod(0o755)
        self.spec['reviewer']['argv'][0] = str(fake)
        self.spec['reviewer']['execution_isolation'] = {
            'mode': 'distinct_uid', 'uid': reviewer_uid, 'gid': reviewer_uid,
            'home': str(self.root / 'review-home')}
        self.spec['reviewer']['startup_seconds'] = 10
        journal = {'stage': 'pr_created', 'pr_url': 'https://example.test/pr/7'}
        journal_path = self.attempt / 'post-return.json'
        post_return._save(journal_path, journal)
        post_return._reviewer_stage(db, self.spec, self.head, self.repo, self.attempt,
                                    self.state, journal, journal_path)
        self.assertEqual(journal['stage'], 'review_started')
        review_dir = Path(journal['reviewer_directory'])
        deadline = time.monotonic() + 10
        while not (review_dir / 'process-result.json').exists() and time.monotonic() < deadline:
            time.sleep(.1)
        self.assertTrue((review_dir / 'process-result.json').exists())
        review_result = json.loads((review_dir / 'process-result.json').read_text())
        self.assertTrue(review_result['final_artifact_validated'])
        self.assertEqual(json.loads((review_dir / 'review.json').read_text())['reviewed_head'], self.head)

if __name__ == '__main__':
    unittest.main()
