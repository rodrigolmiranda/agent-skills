"""Controlled publication fixtures. These do not provision host UID isolation."""
import hashlib
import json
import os
from pathlib import Path
import shutil
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

CLAUDE_SAFE_ARGS = ['--safe-mode', '--restricted', '--strict-mcp-config',
                    '--mcp-config', '{"mcpServers":{}}', '--tools', 'Bash,Read,Glob,Grep',
                    '--no-chrome', '--disallowedTools',
                    'Browser*,Chrome*,Playwright*,Computer*,mcp__*']


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
                                  'argv': ['claude', *CLAUDE_SAFE_ARGS,
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

    def test_same_user_reviewer_rejects_inherited_browser_and_overrides(self):
        owner_home = self.root / 'owner-home'
        owner_home.mkdir()
        (owner_home / '.claude.json').write_text(json.dumps({'mcpServers': {
            'owner-browser': {'command': 'browser-bridge'}}}))
        fixture_claude = self.root / 'claude'
        fixture_claude.write_text('#!/bin/sh\nexit 0\n')
        fixture_claude.chmod(0o755)
        self.spec['reviewer']['execution_isolation'] = {'mode': 'same_user'}
        self.spec['reviewer']['argv'] = [str(fixture_claude), '--no-chrome', '--disallowedTools',
                                        'Browser*', '--output-format', 'stream-json', '-p', 'review']
        with mock.patch.dict(os.environ, {'HOME': str(owner_home)}):
            with self.assertRaisesRegex(post_return.PipelineException, 'browser tool deny'):
                post_return._validate_spec(self.spec, self.manifest, self.repo.resolve())
            self.spec['reviewer']['argv'] = [str(fixture_claude), *CLAUDE_SAFE_ARGS,
                                             '--output-format', 'stream-json', '--model', 'fixture-claude',
                                             '--effort', 'medium', '-p', 'review']
            post_return._validate_spec(self.spec, self.manifest, self.repo.resolve())
            for extra in (['--mcp-config', '{"mcpServers":{"owner-browser":{}}}'],
                          ['--tools=default'], ['--plugin-dir=owner-tools'],
                          ['--settings=owner-settings.json'], ['--disallowed-tools', 'Browser*'],
                          ['--resume'], ['-c'], ['-r', 'owner-session'],
                          ['--add-dir=owner-home'], ['--model=other']):
                with self.subTest(extra=extra):
                    self.spec['reviewer']['argv'].extend(extra)
                    with self.assertRaises(post_return.PipelineException):
                        post_return._validate_spec(self.spec, self.manifest, self.repo.resolve())
                    del self.spec['reviewer']['argv'][-len(extra):]
            self.spec['reviewer']['argv'][0] = str(self.root / 'missing' / 'claude')
            with self.assertRaisesRegex(post_return.PipelineException, 'reviewer CLI unavailable'):
                post_return._validate_spec(self.spec, self.manifest, self.repo.resolve())

    def test_same_user_default_and_invalid_distinct_uid(self):
        env = os.environ.copy()
        with self.assertRaises(ValueError):
            run_job._isolated_worker({'post_return': {}, 'execution_isolation': {
                'mode': 'distinct_uid', 'uid': os.geteuid(), 'gid': os.getegid(), 'home': str(self.root)}}, env)
        self.assertIsNone(run_job._isolated_worker({'post_return': {}}, env))

    def test_hook_config_and_transient_probe_failure_cannot_prove_denial(self):
        git(self.repo, 'config', 'core.hooksPath', str(self.root / 'fake-hooks'))
        failed = self.execute()
        self.assertIn('unsafe worker-controlled Git config', failed['error'])
        self.assertFalse(post_return._permission_denial(b'Could not resolve host: github.com'))
        self.assertFalse(post_return._permission_denial(b'non-fast-forward'))
        self.assertTrue(post_return._permission_denial(b'Permission denied (publickey).'))

    def test_worker_home_gh_credentials_block_publication_preflight(self):
        home = self.root / 'worker-home'
        (home / '.config/gh').mkdir(parents=True)
        (home / '.config/gh/hosts.yml').write_text('github.com: token: sentinel')
        self.manifest['execution_isolation']['home'] = str(home)
        self.spec['gh_executable'] = '/usr/bin/true'
        with self.assertRaisesRegex(post_return.PipelineException, 'credential path'):
            post_return._worker_credential_boundary(self.spec, self.manifest, {}, lambda: None, self.repo)

    def test_actual_gh_identity_probe_rejects_available_token_without_logging_it(self):
        home = self.root / 'empty-worker-home'
        home.mkdir()
        self.manifest['execution_isolation']['home'] = str(home)
        self.spec['gh_executable'] = '/usr/bin/true'
        token = subprocess.CompletedProcess([], 0, stdout=b'secret-value', stderr=b'')
        with mock.patch.object(post_return.subprocess, 'run', return_value=token):
            with self.assertRaisesRegex(post_return.PipelineException, 'CLI credentials') as error:
                post_return._worker_credential_boundary(self.spec, self.manifest, {}, lambda: None, self.repo)
        self.assertNotIn('secret-value', str(error.exception))

    def test_worker_writable_artifact_root_is_rejected_before_launch(self):
        home = self.root / 'worker-home'
        home.mkdir()
        os.chmod(self.repo, 0o700)
        db = self.db
        relay.register(db, 'unsafe', 'one', 'worker', self.repo)
        manifest = {'job': 'unsafe', 'attempt': 'one', 'sender': 'worker',
                    'cwd': str(self.repo), 'argv': [sys.executable, '-c', 'print("unsafe")'],
                    'timeout_seconds': 10,
                    'execution_isolation': {'mode': 'distinct_uid', 'uid': 1002,
                                            'gid': 1002, 'home': str(home)}}
        with self.assertRaisesRegex(ValueError, 'overlap'):
            run_job.run(manifest, self.state, self.repo / 'attempt')
        self.assertIsNone(db.execute('SELECT 1 FROM launches WHERE job=? AND attempt=?',
                                     ('unsafe', 'one')).fetchone())

    def test_state_alias_is_canonicalized_before_private_path_validation(self):
        safe = self.root / 'safe-state'
        safe.mkdir(mode=0o700)
        alias = self.repo / 'state-link'
        alias.symlink_to(safe, target_is_directory=True)
        state = safe / 'state.db'
        self.assertEqual(run_job._canonical_state(alias / 'state.db'), state.resolve())
        home = self.root / 'worker-home'
        home.mkdir()
        manifest = {'execution_isolation': {'mode': 'distinct_uid', 'uid': 1002,
                                             'gid': 1002, 'home': str(home)}}
        # The canonical path is separate from the worker-owned alias.
        run_job._private_state_path(manifest, run_job._canonical_state(alias / 'state.db'), self.repo)

    def test_reviewer_pid_or_error_output_is_not_startup(self):
        review_dir = self.root / 'review'
        review_dir.mkdir()
        (review_dir / 'stdout.log').write_text('{"type":"system","subtype":"init"}\n')
        (review_dir / 'stderr.log').write_text('authentication failed\n')
        self.assertFalse(post_return._reviewer_evidence(review_dir, self.spec['reviewer'], self.head))
        (review_dir / 'stdout.log').write_text(json.dumps({'type': 'assistant', 'message': {
            'model': 'claude-opus', 'content': [{'type': 'tool_use', 'name': 'Read'}]}}) + '\n')
        self.assertTrue(post_return._reviewer_evidence(review_dir, self.spec['reviewer'], self.head))

    def test_same_user_adapter_policy_rejects_publication_browser_and_broad_shell(self):
        argv = ['opencode', 'run', '--pure', '--format', 'json', '--model', 'fixture/model', 'packet']
        manifest = {'post_return': {}, 'argv': argv, 'cwd': str(self.repo),
                    'worker_adapter': {'kind': 'opencode-headless',
                                       'allowed_bash': ['git status --short', 'git add owned.txt']}}
        environment = {'OPENCODE_CONFIG_CONTENT': '{"permission":"allow"}'}
        receipt = run_job._worker_adapter(manifest, environment)
        self.assertEqual(receipt['kind'], 'opencode-headless')
        policy = json.loads(environment['OPENCODE_CONFIG_CONTENT'])['permission']
        self.assertEqual(policy['bash']['*'], 'deny')
        self.assertEqual(policy['bash']['git push*'], 'deny')
        self.assertEqual(policy['bash']['gh*'], 'deny')
        self.assertEqual(policy['webfetch'], 'deny')
        self.assertEqual(policy['browser'], 'deny')
        self.assertEqual(policy['mcp__*'], 'deny')
        self.assertEqual(policy['playwright*'], 'deny')
        for unsafe in ('git push origin feature/one', 'gh pr create', 'open -a Chrome',
                       'git status; gh pr create', '*', 'git *', 'git -C . push',
                       'git --git-dir=.git push', 'git --work-tree=. push',
                       'git status*', 'git status --short*', '/usr/bin/git push',
                       'bash *', 'bash infra/local/scripts/*', 'dotnet *',
                       'python3 *', 'npm *'):
            with self.subTest(unsafe=unsafe), self.assertRaises(ValueError):
                run_job._worker_adapter({**manifest,
                    'worker_adapter': {'kind': 'opencode-headless', 'allowed_bash': [unsafe]}}, {})
        prefixes = ['git status *', 'git diff *', 'git add *', 'git commit -m *',
                    'ls *', 'rg *', 'sed *', 'echo *', 'printf *',
                    'python3 -m unittest *', 'dotnet test *',
                    'bash infra/local/scripts/ci.sh *', 'bash -n infra/local/scripts/ci.sh']
        prefix_env = {}
        run_job._worker_adapter({**manifest, 'worker_adapter': {
            'kind': 'opencode-headless', 'allowed_bash': prefixes}}, prefix_env)
        prefix_policy = json.loads(prefix_env['OPENCODE_CONFIG_CONTENT'])['permission']['bash']
        self.assertTrue(all(prefix_policy[p] == 'allow' for p in prefixes))
        self.assertEqual(prefix_policy['git push*'], 'deny')
        self.assertEqual(prefix_policy['gh*'], 'deny')
        self.assertEqual(prefix_policy['curl*'], 'deny')
        wrong_version = subprocess.CompletedProcess([], 0, stdout=b'1.18.31\n', stderr=b'')
        with mock.patch.object(run_job.subprocess, 'run', return_value=wrong_version):
            with self.assertRaisesRegex(ValueError, 'qualified version 1.18.32'):
                run_job._verify_worker_adapter({**manifest, 'worker_adapter': {
                    'kind': 'opencode-headless', 'allowed_bash': prefixes}}, prefix_env, None)
        with self.assertRaises(ValueError):
            run_job._worker_adapter({**manifest, 'argv': argv + ['--attach', 'http://localhost:4096']}, {})
        for extra in (['--session=old'], ['-s', 'old'], ['-c'], ['--dir=elsewhere'],
                      ['--pure=false'], ['--format=default'], ['--model=other']):
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                run_job._worker_adapter({**manifest, 'argv': argv + extra}, {})
        with self.assertRaises(ValueError):
            run_job._worker_adapter({**manifest, 'env': {'OPENCODE_CONFIG_CONTENT': '{}'}}, {})
        inherited = subprocess.CompletedProcess([], 0, stdout=json.dumps({
            'permission': policy, 'mcp': {'owner-browser': {'type': 'local'}}, 'plugin': []}).encode(), stderr=b'')
        with mock.patch.object(run_job.subprocess, 'run', return_value=inherited):
            with self.assertRaisesRegex(ValueError, 'inherited external MCP'):
                run_job._verify_worker_adapter(manifest, environment, None)

    @unittest.skipUnless(shutil.which('opencode'), 'OpenCode CLI unavailable')
    def test_generated_policy_is_loaded_by_installed_opencode(self):
        manifest = {'post_return': {},
                    'argv': ['opencode', 'run', '--pure', '--format', 'json', '--model', 'fixture/model', 'packet'],
                    'worker_adapter': {'kind': 'opencode-headless', 'allowed_bash': ['git status --short']}}
        environment = os.environ.copy()
        run_job._worker_adapter(manifest, environment)
        loaded = subprocess.run(['opencode', 'debug', 'config', '--pure'], cwd=self.repo,
                                env=environment, capture_output=True, timeout=20, check=True)
        policy = json.loads(loaded.stdout)['permission']
        self.assertEqual(policy['bash']['git status --short'], 'allow')
        self.assertEqual(policy['bash']['git push*'], 'deny')
        self.assertEqual(policy['bash']['gh*'], 'deny')
        self.assertEqual(policy['webfetch'], 'deny')

    def test_same_user_full_return_draft_pr_and_headless_review(self):
        git(self.repo, 'reset', '--hard', self.start)
        exclude = self.repo / '.git/info/exclude'
        with exclude.open('a') as stream:
            stream.write('\n.worker-final.json\n')
        fake_bin = self.root / 'bin'
        fake_bin.mkdir()
        worker = fake_bin / 'opencode'
        worker.write_text('''#!/usr/bin/env python3
import json,os,subprocess,sys
from pathlib import Path
policy=json.loads(os.environ['OPENCODE_CONFIG_CONTENT'])['permission']
assert os.environ['PWD']==os.getcwd()
if sys.argv[1:4]==['debug','config','--pure']:
    print(json.dumps({'permission':policy,'mcp':{},'plugin':[]}))
    raise SystemExit(0)
if sys.argv[1:]==['--version']:
    print('1.18.32')
    raise SystemExit(0)
assert sys.argv[1:4]==['run','--dir',os.environ['PWD']]
assert policy['bash']['git push*']=='deny'
assert policy['bash']['gh*']=='deny'
assert policy['browser']=='deny'
Path('owned.txt').write_text('worker implementation\\n')
subprocess.run(['git','add','owned.txt'],check=True)
subprocess.run(['git','commit','-m','worker implementation'],check=True,stdout=subprocess.DEVNULL)
head=subprocess.run(['git','rev-parse','HEAD'],check=True,capture_output=True,text=True).stdout.strip()
Path(os.environ['INTERCHANGE_FINAL_ARTIFACT']).write_text(json.dumps({
  'job':'job','attempt':'same','packet_revision':'r1','head':head,
  'result':'ready_for_review','required_gates':{'unit':'passed'}}))
print(json.dumps({'type':'tool','part':{'type':'tool','name':'bash'}}),flush=True)
''')
        worker.chmod(0o755)
        pr_state = self.root / 'pr.json'
        pr_count = self.root / 'pr-count.txt'
        gh = fake_bin / 'gh'
        gh.write_text('#!/usr/bin/env python3\n'
                      'import json,subprocess,sys\nfrom pathlib import Path\n'
                      f'state=Path({str(pr_state)!r}); count=Path({str(pr_count)!r})\n'
                      'if sys.argv[1:3]==["pr","list"]:\n'
                      '    print(json.dumps([json.loads(state.read_text())] if state.exists() else []))\n'
                      'elif sys.argv[1:3]==["pr","create"]:\n'
                      '    head=subprocess.run(["git","rev-parse","HEAD"],check=True,capture_output=True,text=True).stdout.strip()\n'
                      '    state.write_text(json.dumps({"number":7,"url":"https://example.test/pr/7",'
                      '"headRefName":"feature/one","baseRefName":"test","isDraft":True,"headRefOid":head}))\n'
                      '    count.write_text(str(int(count.read_text())+1 if count.exists() else 1))\n'
                      '    print("https://example.test/pr/7")\n')
        gh.chmod(0o755)
        review_count = self.root / 'review-count.txt'
        claude = fake_bin / 'claude'
        claude.write_text('#!/usr/bin/env python3\n'
                          'import json,os,re,sys\nfrom pathlib import Path\n'
                          'assert os.environ["PWD"]==os.getcwd()\n'
                          'assert all(flag in sys.argv for flag in '
                          '["--safe-mode","--restricted","--strict-mcp-config","--no-chrome"])\n'
                          'assert sys.argv[sys.argv.index("--mcp-config")+1]=='
                          '\'{"mcpServers":{}}\'\n'
                          'assert "mcp__*" in sys.argv[sys.argv.index("--disallowedTools")+1]\n'
                          f'count=Path({str(review_count)!r})\n'
                          'head=re.search(r"[0-9a-f]{40}", " ".join(sys.argv)).group()\n'
                          'count.write_text(str(int(count.read_text())+1 if count.exists() else 1))\n'
                          'print(json.dumps({"type":"assistant","message":'
                          '{"model":"fixture-claude","content":[{"type":"tool_use","name":"Read"}]}}),flush=True)\n'
                          'print(json.dumps({"type":"result","result":json.dumps('
                          '{"reviewed_head":head,"verdict":"passed"})}),flush=True)\n')
        claude.chmod(0o755)
        spec = dict(self.spec)
        spec['gh_executable'] = str(gh)
        spec['reviewer'] = {'adapter': 'claude-headless',
                            'argv': [str(claude), *CLAUDE_SAFE_ARGS,
                                     '--output-format', 'stream-json', '--model', 'fixture-claude',
                                     '--effort', 'medium', '-p', 'Review {head} at {pr_url}'],
                            'timeout_seconds': 15, 'startup_seconds': 10, 'route': 'manual'}
        manifest = {'job': 'job', 'attempt': 'same', 'sender': 'worker', 'cwd': str(self.repo),
                    'argv': [str(worker), 'run', '--pure', '--format', 'json', '--model',
                             'fixture/model', 'packet'], 'timeout_seconds': 15,
                    'final_artifact_source': '.worker-final.json',
                    'worker_adapter': {'kind': 'opencode-headless',
                                       'allowed_bash': ['git add *', 'git commit -m *']},
                    'post_return': spec}
        relay.register(self.db, 'job', 'same', 'worker', self.root)
        relay.bind_attempt(self.db, 'project', 'job', 'same', 1)
        attempt = self.root / 'same-attempt'
        with mock.patch.object(post_return, '_verify_publication_url', return_value=None):
            with mock.patch.dict(os.environ, {'PWD': str(self.root / 'wrong-parent-checkout')}):
                receipt = run_job.run(manifest, self.state, attempt)
        self.assertEqual(receipt['result']['exit_code'], 0)
        self.assertEqual(receipt['result']['worker_adapter']['session_directory'], str(self.repo.resolve()))
        self.assertEqual(receipt['result']['post_return']['stage'], 'review_started')
        published_head = git(self.repo, 'rev-parse', 'HEAD')
        self.assertEqual(git(self.repo, 'ls-remote', '--heads', str(self.remote), 'feature/one').split()[0], published_head)
        self.assertEqual(pr_count.read_text(), '1')
        review_dir = Path(receipt['result']['post_return']['reviewer_directory'])
        deadline = time.monotonic() + 10
        while not (review_dir / 'process-result.json').exists() and time.monotonic() < deadline:
            time.sleep(.1)
        self.assertTrue((review_dir / 'process-result.json').exists())
        self.assertEqual(json.loads((review_dir / 'review.json').read_text())['reviewed_head'], published_head)
        self.assertEqual(review_count.read_text(), '1')
        with mock.patch.object(post_return, '_verify_publication_url', return_value=None):
            db = relay.connect(self.state)
            try:
                again = post_return.execute(spec, manifest, receipt['result'], db, self.state, attempt)
            finally:
                db.close()
        self.assertEqual(again['stage'], 'review_started')
        self.assertEqual((pr_count.read_text(), review_count.read_text()), ('1', '1'))


@unittest.skipUnless(hasattr(os, 'geteuid') and os.geteuid() == 0,
                     'requires isolated root test container')
class RootIsolationTests(unittest.TestCase):
    """Actual UID isolation with a root-owned local Git remote and fake model CLI."""
    setUp = PipelineTests.setUp
    tearDown = PipelineTests.tearDown

    def test_distinct_worker_cannot_push_and_reviewer_launches_under_second_uid(self):
        os.chmod(self.root, 0o755)
        self.db.close()
        private_state = self.root / 'private-state'
        private_state.mkdir(mode=0o700)
        self.state = private_state / 'state.db'
        self.db = relay.connect(self.state)
        relay.register_project(self.db, 'project')
        worker_uid, reviewer_uid = 1002, 1003
        for name, uid in [('worker-home', worker_uid), ('review-home', reviewer_uid)]:
            home = self.root / name
            home.mkdir(mode=0o700)
            os.chown(home, uid, uid)
        # Worker owns its checkout; the bare remote remains root-owned and read-only to it.
        for path in [self.repo, *self.repo.rglob('*')]:
            os.chown(path, worker_uid, worker_uid)
        db = self.db
        private_worker_root = self.root / 'private-worker-root'
        private_worker_root.mkdir(mode=0o700)
        relay.register(db, 'uidworker', 'one', 'worker', private_worker_root)
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
        worker_receipt = run_job.run(worker_manifest, self.state, private_worker_root / 'uid-attempt')
        self.assertEqual(worker_receipt['result']['exit_code'], 0)
        self.assertIn('push_denied=True', (private_worker_root / 'uid-attempt/stdout.log').read_text())
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
