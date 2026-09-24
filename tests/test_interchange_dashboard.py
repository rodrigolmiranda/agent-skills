import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('dashboard', Path(__file__).parents[1] / 'skills/interchange/scripts/dashboard.py')
dashboard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dashboard)


class DashboardTests(unittest.TestCase):
    def test_awaiting_acceptance_does_not_claim_running_review(self):
        self.assertEqual('next', dashboard.activity_column({'state': 'awaiting_acceptance'}, []))
        self.assertEqual('blocked', dashboard.activity_column({'state': 'awaiting_acceptance', 'blocker': 'fixture missing'}, []))
        self.assertEqual('review', dashboard.activity_column({'state': 'review'}, []))

    def test_worktrees_share_page_and_coordinators_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory) / 'repo'
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'initial'], check=True)
            worktree = Path(directory) / 'worker'
            subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '-q', '--detach', str(worktree)], check=True)
            first = {'project_id': 'one', 'coordinator': {'agent_id': 'codex'}, 'next_action': '<script>alert(1)</script>'}
            second = {'project_id': 'two', 'coordinator': {'agent_id': 'claude'}}
            page = dashboard.publish(repo, first)
            self.assertEqual(page, dashboard.publish(worktree, second))
            self.assertEqual(2, len(list((page.parent / 'coordinators').glob('*.json'))))
            self.assertIn('&lt;script&gt;', page.read_text())
            self.assertNotIn('<script>alert', page.read_text())
            dashboard.publish(repo, first)
            self.assertEqual(2, len(list((page.parent / 'coordinators').glob('*.json'))))
            self.assertEqual('', subprocess.check_output(['git', '-C', str(repo), 'status', '--porcelain'], text=True))

    def test_collision_ignore_and_observation_provenance(self):
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            (repo / '.interchange').mkdir()
            ignore = repo / '.interchange/.gitignore'
            ignore.write_text('private/\n')
            for project, agent in [('a--b', 'c'), ('a', 'b--c')]:
                page = dashboard.publish(repo, {'project_id': project, 'coordinator': {'agent_id': agent}, 'updated_at': '2000-01-01T00:00:00Z'})
            records = [json.loads(p.read_text()) for p in (page.parent / 'coordinators').glob('*.json')]
            self.assertEqual(2, len(records))
            self.assertEqual('private/\n', ignore.read_text())
            for record in records:
                self.assertEqual('2000-01-01T00:00:00Z', record['updated_at'])
                self.assertNotEqual(record['updated_at'], record['published_at'])

    def test_workflow_board_groups_one_logical_job_in_requested_column_order(self):
        record = {
            'project_id': 'board',
            'coordinator': {'agent_id': 'planner'},
            'workflow_steps': [
                {'id': 'run', 'job_id': 'job-run', 'order': 1, 'title': 'Current task',
                 'state': 'blocked', 'owner': 'builder', 'next_action': 'Finish the report',
                 'issue_url': 'https://example.test/issues/17', 'parent_url': 'https://example.test/issues/10'},
                {'id': 'blocked', 'job_id': 'job-blocked', 'order': 2, 'title': 'Quota task',
                 'state': 'blocked', 'owner': None, 'blocker': 'Provider quota'},
                {'id': 'next', 'job_id': 'job-next', 'order': 3, 'title': 'Upcoming task',
                 'state': 'not-started', 'owner': None},
                {'id': 'done', 'job_id': 'job-done', 'order': 4, 'title': 'Finished task',
                 'state': 'completed', 'owner': 'builder', 'pr_url': 'https://example.test/pull/1'},
            ],
            'attempts': [
                {'job_id': 'job-run', 'attempt_id': 'a1', 'agent_id': 'builder', 'task': 'Old failed retry',
                 'last_observed_state': 'failed', 'outcome': 'error', 'last_observed_at': '2026-09-22T10:00:00Z'},
                {'job_id': 'job-run', 'attempt_id': 'a2', 'agent_id': 'builder', 'task': 'Current task',
                 'execution_state': 'running', 'outcome': None, 'requested_model': 'gpt-6-luna',
                 'requested_effort': 'xhigh', 'observed_model': 'gpt-6-luna', 'observed_effort': 'xhigh',
                 'identity_evidence': 'provider response metadata',
                 'started_at': '2026-09-23T08:00:00Z', 'last_observed_at': '2026-09-23T08:05:00Z',
                 'evaluation': {'dimensions': {'correctness': 'Not assessed'}}},
                {'job_id': 'job-blocked', 'attempt_id': 'a3', 'agent_id': 'builder',
                 'execution_state': 'stopped', 'outcome': 'provider_quota',
                 'last_observed_at': '2026-09-23T08:02:00Z'},
                {'job_id': 'job-done', 'attempt_id': 'a4', 'agent_id': 'builder',
                 'execution_state': 'completed', 'outcome': 'done',
                 'last_observed_at': '2026-09-23T08:01:00Z'},
            ],
        }
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            page = dashboard.publish(repo, record).read_text()

        board = page[page.index('<div class="board"'):]
        self.assertLess(board.index('Next'), board.index('Blocked'))
        self.assertLess(board.index('Blocked'), board.index('Working now'))
        self.assertLess(board.index('Working now'), board.index('Done'))
        self.assertIn('Working now <span class="count">1</span>', board)
        self.assertIn('Blocked <span class="count">1</span>', board)
        self.assertIn('Board status: Working now', page)
        self.assertIn('summary-status status-good">Working now</span>', page)
        self.assertIn('Plan status:</strong> Blocked', page)
        self.assertIn('<strong>Outcome:</strong>', page)
        self.assertIn('>Provider quota</span>', page)
        self.assertIn('<strong>Execution state:</strong>', page)
        self.assertIn('>Stopped</span>', page)
        self.assertIn('Requested model / effort:</strong> gpt-6-luna · xhigh', page)
        self.assertIn('Observed model / effort:</strong> gpt-6-luna · xhigh', page)
        self.assertEqual(1, page.count('<strong>Current task</strong>'))
        self.assertIn('Attempts and retries (2)', page)
        self.assertIn('Evaluation dimensions', page)
        self.assertLess(page.index('Issue:'), page.index('Parent:'))

    def test_task_cards_are_collapsed_with_compact_column_status_and_full_details(self):
        item = {'id': 'private-step-42', 'title': 'Check supplier access',
                'state': 'blocked', 'owner': None, 'blocker': 'Provider quota',
                'next_action': 'Wait for quota reset and retry the export'}
        attempt = {'attempt_id': 'attempt-7', 'agent_id': 'builder',
                   'execution_state': 'completed', 'outcome': None,
                   'requested_model': 'gpt-6-luna', 'requested_effort': 'xhigh',
                   'evaluation': {'dimensions': {'correctness': 'Not assessed'}}}
        card, column = dashboard.task_card(item, [attempt])

        self.assertEqual('blocked', column)
        self.assertTrue(card.startswith('<details class="task-card"><summary class="task-summary">'))
        compact = card.split('</summary>', 1)[0]
        self.assertIn('<span class="summary-title">Check supplier access</span>', compact)
        self.assertIn('<span class="summary-owner">builder</span>', compact)
        self.assertIn('<span class="summary-status status-attention">Blocked</span>', compact)
        self.assertIn('<span class="summary-detail">Provider quota</span>', compact)
        self.assertNotIn('summary-model', compact)
        for technical_value in ('private-step-42', 'Snapshot status', 'Execution state', 'Completed'):
            self.assertNotIn(technical_value, compact)
        self.assertIn('</summary><div class="task-card-body">', card)
        self.assertIn('<strong>Activity:</strong> private-step-42', card)
        self.assertIn('Board status: Blocked', card)
        self.assertIn('Plan status:</strong> Blocked', card)
        self.assertIn('Execution state:</strong>', card)
        self.assertIn('Requested model / effort:</strong> gpt-6-luna · xhigh', card)
        self.assertIn('Current action:</strong> Wait for quota reset and retry the export', card)
        self.assertIn('Attempts and retries (1)', card)
        self.assertIn('Evaluation dimensions', card)
        self.assertNotIn('<details open class="task-card">', card)

    def test_working_and_done_model_badge_sits_on_top_row_and_marks_its_source(self):
        cases = [
            ({'id': 'working-id', 'title': 'Run export', 'state': 'running',
              'owner': 'export-builder', 'next_action': 'Validate the CSV'},
             {'agent_id': 'export-builder', 'execution_state': 'running', 'outcome': 'in_progress',
              'requested_model': 'gpt-6-luna', 'requested_effort': 'xhigh',
              'observed_model': 'gpt-6-sol', 'observed_effort': 'high',
              'identity_evidence': 'provider response metadata'},
             'working', 'Working now', 'Observed · Sol · high',
             'gpt-6-luna · xhigh', 'gpt-6-sol · high'),
            ({'id': 'done-id', 'title': 'Publish package', 'state': 'completed',
              'next_action': 'Check the release record'},
             {'agent_id': 'release-builder', 'execution_state': 'completed', 'outcome': 'done',
              'requested_model': 'gpt-6-sol', 'requested_effort': 'high'},
             'done', 'Done', 'Requested · Sol · high', 'gpt-6-sol · high', 'Not exposed'),
            ({'id': 'deepseek-id', 'title': 'Run repository checks', 'state': 'running',
              'next_action': 'Review the test output'},
             {'agent_id': 'deepseek-worker', 'execution_state': 'running',
              'requested_model': 'deepseek-flash-code', 'requested_effort': 'high'},
             'working', 'Working now', 'Requested · DeepSeek · high',
             'deepseek-flash-code · high', 'Not exposed'),
        ]
        for item, attempt, expected_column, status, badge, requested, observed in cases:
            with self.subTest(status=status):
                card, column = dashboard.task_card(item, [attempt])
                compact = card.split('</summary>', 1)[0]
                self.assertEqual(expected_column, column)
                self.assertTrue(card.startswith('<details class="task-card"><summary class="task-summary">'))
                self.assertIn(f'<span class="summary-status {dashboard.status_class(column)}">{status}</span>', compact)
                top_row = compact.split('<span class="summary-top-row">', 1)[1].split(
                    '</span><span class="summary-meta">', 1)[0]
                meta_row = compact.split('<span class="summary-meta">', 1)[1].split(
                    '</span><span class="summary-detail">', 1)[0]
                action_row = compact.split('<span class="summary-detail">', 1)[1]
                self.assertIn(f'<span class="summary-model-badge">{badge}</span>', top_row)
                self.assertNotIn('summary-model-badge', meta_row)
                self.assertNotIn('summary-model-badge', action_row)
                self.assertIn(f'Requested model / effort:</strong> {requested}', card)
                self.assertIn(f'Observed model / effort:</strong> {observed}', card)
                if observed != 'Not exposed':
                    self.assertIn('Model identity evidence:</strong> provider response metadata', card)
                self.assertEqual(1, compact.count('class="summary-title"'))
                self.assertEqual(1, compact.count('class="summary-meta"'))
                self.assertEqual(1, compact.count('class="summary-detail'))
                self.assertNotIn('<details open class="task-card">', card)

    def test_front_badge_is_allowlisted_in_summary_and_detail(self):
        item = {'id': 'front-step', 'title': 'Review pipeline', 'state': 'not-started',
                'front': ' MENTORA ', 'next_action': 'Review the pipeline'}
        card, column = dashboard.task_card(item, [])

        self.assertEqual('next', column)
        compact = card.split('</summary>', 1)[0]
        self.assertIn('<span class="summary-front-badge">Front · Mentora</span>', compact)
        self.assertIn('<span class="badge summary-front-badge">Front: Mentora</span>', card)
        self.assertIn('<strong>Front:</strong> Mentora', card)

        unknown, _ = dashboard.task_card(
            {'id': 'shared-step', 'title': 'Unclassified foundation work',
             'state': 'not-started', 'front': '<script>alert(1)</script>'}, [])
        self.assertIn('<span class="summary-front-badge">Front · Unknown front</span>', unknown)
        self.assertIn('<strong>Front:</strong> Unknown front', unknown)
        self.assertNotIn('<script>', unknown)

        non_string, _ = dashboard.task_card(
            {'id': 'invalid-step', 'title': 'Invalid front data',
             'state': 'not-started', 'front': ['retail']}, [])
        self.assertIn('<strong>Front:</strong> Unknown front', non_string)

    def test_missing_requested_identity_and_no_agent_are_explicit(self):
        item = {'id': 'working-id', 'title': 'Run export', 'state': 'running',
                'owner': None, 'next_action': 'Validate the CSV'}
        attempt = {'agent_id': 'export-builder', 'execution_state': 'running',
                   'observed_model': 'gpt-6-sol', 'observed_effort': 'high',
                   'identity_evidence': 'unknown'}
        card, column = dashboard.task_card(item, [attempt])
        compact = card.split('</summary>', 1)[0]
        self.assertEqual('working', column)
        self.assertIn('<span class="summary-model-badge">Requested · Not exposed</span>', compact)
        self.assertIn('Requested model / effort:</strong> Not exposed', card)
        self.assertIn('Observed model / effort:</strong> Not exposed', card)

        unassigned, column = dashboard.task_card(
            {'id': 'planned-id', 'title': 'Plan the review', 'state': 'not-started'}, [])
        compact = unassigned.split('</summary>', 1)[0]
        self.assertEqual('next', column)
        self.assertNotIn('summary-model-badge', compact)

        no_agent_done, column = dashboard.task_card(
            {'id': 'done-id', 'title': 'Record completion', 'state': 'completed'}, [])
        compact = no_agent_done.split('</summary>', 1)[0]
        self.assertEqual('done', column)
        self.assertIn('<span class="summary-model-badge">No agent</span>', compact)
        self.assertNotIn('summary-model-badge">Unknown', compact)

    def test_finished_execution_needs_success_outcome_before_done(self):
        finished = {'execution_state': 'completed'}
        failed = {'execution_state': 'completed', 'outcome': 'failed'}
        succeeded = {'execution_state': 'completed', 'outcome': 'succeeded'}

        self.assertEqual('blocked', dashboard.activity_column({'state': 'not-started'}, [finished]))
        self.assertEqual('blocked', dashboard.activity_column({'state': 'not-started'}, [failed]))
        self.assertEqual('blocked', dashboard.activity_column({'state': 'blocked'}, [finished]))
        self.assertEqual('blocked', dashboard.activity_column({'state': 'completed'}, [failed]))
        self.assertEqual('done', dashboard.activity_column({'state': 'not-started'}, [succeeded]))
        self.assertEqual('done', dashboard.activity_column({'state': 'completed'}, []))

    def test_explicit_step_identity_is_exclusive_and_ambiguous_job_is_unmapped(self):
        steps = [
            {'id': 'build', 'job_id': 'shared-job', 'title': 'Build'},
            {'id': 'review', 'job_id': 'shared-job', 'title': 'Review'},
        ]
        explicit = {'attempt_id': 'build-attempt', 'job_id': 'shared-job',
                    'workflow_step_id': 'build', 'execution_state': 'running'}
        ambiguous_fallback = {'attempt_id': 'unassigned-attempt', 'job_id': 'shared-job',
                              'execution_state': 'running'}
        record = {'workflow_steps': steps, 'attempts': [explicit, ambiguous_fallback]}
        grouped, unmatched = dashboard.attempt_groups(record, steps)

        self.assertEqual([explicit], grouped[0][1])
        self.assertEqual([], grouped[1][1])
        self.assertEqual([ambiguous_fallback], unmatched)
        self.assertEqual('working', dashboard.activity_column(grouped[0][0], grouped[0][1]))
        self.assertEqual('next', dashboard.activity_column(grouped[1][0], grouped[1][1]))
        rendered = dashboard.board(record)
        self.assertIn('Working now <span class="count">1</span>', rendered)
        self.assertIn('Next <span class="count">1</span>', rendered)
        self.assertIn('Attempt records without a matching workflow activity (1)', rendered)
        self.assertEqual(1, rendered.count('<strong>build-attempt</strong>'))
        self.assertEqual(1, rendered.count('<strong>unassigned-attempt</strong>'))

    def test_job_fallback_never_matches_an_equal_step_id_and_ids_remain_typed(self):
        steps = [
            {'id': 'shared-job', 'job_id': 'build-job'},
            {'id': 'review', 'job_id': 'shared-job'},
        ]
        fallback = {'attempt_id': 'fallback', 'job_id': 'shared-job', 'execution_state': 'running'}
        grouped, unmatched = dashboard.attempt_groups({'attempts': [fallback]}, steps)
        self.assertEqual([], grouped[0][1])
        self.assertEqual([fallback], grouped[1][1])
        self.assertEqual([], unmatched)

        typed_steps = [{'id': 7, 'job_id': 'unique-job'}]
        mismatched_explicit = {'attempt_id': 'typed', 'workflow_step_id': '7',
                               'job_id': 'unique-job', 'execution_state': 'running'}
        typed_group, typed_unmatched = dashboard.attempt_groups(
            {'attempts': [mismatched_explicit]}, typed_steps)
        self.assertEqual([], typed_group[0][1])
        self.assertEqual([mismatched_explicit], typed_unmatched)

    def test_unassigned_workflow_activity_without_attempt_stays_visible(self):
        record = {
            'project_id': 'unassigned', 'coordinator': {'agent_id': 'planner'},
            'workflow_steps': [{'id': 'step-1', 'order': 1, 'title': 'Write acceptance notes',
                                'state': 'not-started', 'owner': None,
                                'next_action': 'Draft the notes', 'dependencies': []}],
        }
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            page = dashboard.publish(repo, record).read_text()
        self.assertIn('Write acceptance notes', page)
        self.assertIn('<strong>Owner:</strong> Unassigned', page)
        self.assertIn('Requested model / effort:</strong> Not exposed', page)
        self.assertIn('Observed model / effort:</strong> Not exposed', page)
        self.assertIn('Current action:</strong> Draft the notes', page)
        self.assertIn('Can run in parallel:</strong> Not supplied', page)
        self.assertIn('Readiness:</strong> Not supplied', page)
        self.assertIn('Attempts and retries (0)', page)

    def test_next_column_limits_initial_cards_but_reveals_all_in_plan_order(self):
        steps = [{'id': f'step-{number:02d}', 'job_id': f'job-{number:02d}', 'order': number,
                  'title': f'Activity {number:02d}', 'state': 'not-started'}
                 for number in range(12, 0, -1)]
        record = {'project_id': 'many-next', 'coordinator': {'agent_id': 'planner'}, 'workflow_steps': steps}
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            page = dashboard.publish(repo, record).read_text()
        self.assertIn('Next <span class="count">12</span>', page)
        self.assertIn('Show all 12 planned activities (2 more)', page)
        first = page.index('<strong>Activity 01</strong>')
        second = page.index('<strong>Activity 02</strong>')
        tenth = page.index('<strong>Activity 10</strong>')
        reveal = page.index('Show all 12 planned activities')
        self.assertLess(first, second)
        self.assertLess(second, tenth)
        self.assertLess(tenth, reveal)
        self.assertIn('<strong>Activity 12</strong>', page)
        for number in range(1, 13):
            self.assertEqual(1, page.count(f'<strong>Activity {number:02d}</strong>'))

    def test_next_column_limit_is_per_front_and_does_not_invent_cards(self):
        steps = []
        for front in ('shared', 'mentora', 'b2b', 'retail'):
            steps += [{'id': f'{front}-{number}', 'order': number,
                       'title': f'{front} activity {number}', 'front': front,
                       'state': 'not-started'} for number in range(11, 0, -1)]
        record = {'workflow_steps': steps}
        page = dashboard.board(record)
        self.assertIn('Next <span class="count">44</span>', page)
        for front in ('Shared', 'Mentora', 'B2B', 'Retail'):
            self.assertIn(f'<h4>{front} <span class="count">11</span></h4>', page)
        self.assertEqual(4, page.count('Show all 11 planned activities (1 more)'))
        for front in ('shared', 'mentora', 'b2b', 'retail'):
            tenth = page.index(f'<strong>{front} activity 10</strong>')
            eleventh = page.index(f'<strong>{front} activity 11</strong>')
            self.assertLess(tenth, eleventh)
            self.assertEqual(1, page.count(f'<strong>{front} activity 11</strong>'))

        one_front = dashboard.board({'workflow_steps': steps[:11]})
        self.assertNotIn('<h4>Retail <span', one_front)

    def test_approved_scope_is_visible_without_claiming_ready_activity(self):
        items = [{'id': f'retail-{number}', 'front': 'retail',
                  'title': f'Retail item {number}', 'url': f'https://example.test/issues/{number}',
                  'disposition': 'dependency-blocked', 'reason': 'Published source contract pending'}
                 for number in range(19)]
        items.append({'id': 'unsafe', 'front': '<script>x</script>',
                      'title': '<script>unsafe</script>', 'url': 'javascript:alert(1)'})
        record = {'project_id': 'scope', 'coordinator': {'agent_id': 'planner'},
                  'workflow_steps': [], 'approved_scope': {
                      'source_url': 'https://example.test/project/15',
                      'checked_at': '2026-09-24T13:00:00Z', 'items': items}}
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            page = dashboard.publish(repo, record).read_text()
        self.assertIn('Next <span class="count">0</span>', page)
        self.assertIn('Approved H1 scope (20 open items) · browse all approved issues', page)
        self.assertIn('<details class="approved-scope" open>', page)
        self.assertLess(page.index('Approved H1 scope (20 open items)'), page.index('Next <span class="count">0</span>'))
        self.assertIn('<h4>Retail <span class="count">19</span></h4>', page)
        self.assertIn('Retail item 18', page)
        self.assertIn('Unknown front <span class="count">1</span>', page)
        self.assertIn('&lt;script&gt;unsafe&lt;/script&gt;', page)
        self.assertNotIn('href="javascript:alert(1)"', page)
        self.assertIn('max-height:min(28vh,280px);overflow-y:auto', page)
        self.assertIn("new URLSearchParams(location.search).get('project')", page)

    def test_current_action_on_step_is_visible_on_working_card(self):
        card, column = dashboard.task_card({'id': 'sdk-query', 'title': 'SDK query seam',
                                            'state': 'running', 'current_action': 'Implement local view adapter'}, [])
        self.assertEqual('working', column)
        self.assertIn('Implement local view adapter', card)
        self.assertNotIn('No current action supplied', card)

    def test_long_board_columns_are_bounded_and_keep_keyboard_focus_visible(self):
        steps = [{'id': f'done-{number:02d}', 'order': number,
                  'title': f'Done activity {number:02d}', 'state': 'done',
                  'pr_url': f'https://example.test/pull/{number}'}
                 for number in range(1, 19)]
        record = {'project_id': 'long-done', 'coordinator': {'agent_id': 'planner'},
                  'workflow_steps': steps}
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            page = dashboard.publish(repo, record).read_text()

        self.assertIn('max-height:min(70vh,760px)', page)
        self.assertIn('overflow-y:auto', page)
        self.assertIn('position:sticky;top:-8px', page)
        self.assertIn('scroll-margin-top:48px', page)
        self.assertIn('max-height:min(65vh,560px)', page)
        self.assertIn('Done <span class="count">18</span>', page)
        self.assertIn('<strong>Done activity 18</strong>', page)

    def test_legacy_attempt_snapshot_and_unknown_identity_remain_clear(self):
        record = {'project_id': 'legacy', 'coordinator': {'agent_id': 'planner'},
                  'attempts': [{'job_id': 'job-1', 'attempt_id': 'a1', 'agent_id': 'builder',
                                'task': '<script>task</script>', 'last_observed_state': 'running'}]}
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            page = dashboard.publish(repo, record).read_text()
        self.assertIn('Current execution horizon', page)
        self.assertIn('&lt;script&gt;task&lt;/script&gt;', page)
        self.assertNotIn('<script>task</script>', page)
        self.assertIn('Working now <span class="count">1</span>', page)
        self.assertIn('Requested model / effort:</strong> Not exposed', page)
        self.assertIn('Observed model / effort:</strong> Not exposed', page)
        self.assertIn('<strong>Execution state:</strong>', page)
        self.assertIn('>Running</span>', page)
        self.assertIn('Started: Unknown', page)
        self.assertIn('Not assessed', page)

    def test_unsafe_identity_refused(self):
        with self.assertRaises(ValueError):
            dashboard.publish('.', {'project_id': '../bad', 'coordinator': {'agent_id': 'x'}})

class WaitingTests(unittest.TestCase):
    def test_waiting_order_and_failed_attempt_remains_blocked(self):
        waiting = {'id': 'w', 'state': 'waiting', 'waiting_for': 'SDK publication',
                   'waiting_owner': 'Publisher', 'waiting_since': '2026-09-23T11:00:00Z', 'next_event': 'CI return'}
        self.assertEqual('waiting', dashboard.activity_column(waiting, []))
        self.assertEqual('blocked', dashboard.activity_column(waiting, [{'execution_state': 'failed'}]))
        card, _ = dashboard.task_card(waiting, [])
        self.assertIn('SDK publication', card)
        self.assertIn('Publisher', card)
        board = dashboard.board({'workflow_steps': [waiting]})
        positions = [board.index('column-' + key) for key in ('next', 'blocked', 'working', 'waiting', 'review', 'done')]
        self.assertEqual(sorted(positions), positions)

class ArtifactLinkTests(unittest.TestCase):
    def test_done_links_include_return_pr_and_activity_sources(self):
        card, column = dashboard.task_card(
            {'state': 'done', 'links': [{'label': 'Earlier PR', 'url': 'https://github.com/o/r/pull/1'}]},
            [{'pr_url': 'https://github.com/o/r/pull/2', 'issue_url': 'https://github.com/o/r/issues/3'}])
        self.assertEqual('done', column)
        for suffix in ('pull/1', 'pull/2', 'issues/3'):
            self.assertIn('https://github.com/o/r/' + suffix, card)

class DoneSourceGateTests(unittest.TestCase):
    def test_publication_rejects_missing_source_before_writing(self):
        record = {'project_id': 'x', 'coordinator': {'agent_id': 'a'},
                  'workflow_steps': [{'id': 'finished-work', 'state': 'done'}]}
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(ValueError, 'finished-work'):
                dashboard.publish(directory, record)
            self.assertEqual([], list(Path(directory).iterdir()))
        record['workflow_steps'][0]['pr_url'] = 'https://github.com/o/r/pull/1'
        dashboard.validate_done_sources(record)

class CompletionScopeTests(unittest.TestCase):
    def test_step_completion_does_not_close_issue(self):
        step = {'id': 'review', 'state': 'done', 'issue_url': 'https://github.com/o/r/issues/54'}
        with self.assertRaisesRegex(ValueError, 'declare step or issue'):
            dashboard.validate_done_sources({'workflow_steps': [step]})
        step.update(completion_scope='step', github_issue_state='OPEN')
        dashboard.validate_done_sources({'workflow_steps': [step]})
        card, column = dashboard.task_card(step, [])
        self.assertEqual('done', column)
        self.assertIn('Step done · parent remains open', card)
        self.assertIn('Step slice complete; Parent remains open (snapshot says OPEN).', card)
        self.assertEqual('blocked', dashboard.activity_column(step, [{'execution_state': 'failed'}]))
        self.assertEqual('working', dashboard.activity_column(step, [{'execution_state': 'running'}]))
        step['completion_scope'] = 'issue'
        with self.assertRaisesRegex(ValueError, 'CLOSED'):
            dashboard.validate_done_sources({'workflow_steps': [step]})
        step.update(github_issue_state='CLOSED', github_checked_at='2026-09-23T13:00:00Z')
        dashboard.validate_done_sources({'workflow_steps': [step]})


class SnapshotObservabilityTests(unittest.TestCase):
    def test_progress_event_and_overdue_follow_up_are_escaped_and_visible(self):
        item = {
            'id': 'slice', 'title': 'Publish <slice>', 'state': 'running',
            'last_progress_summary': 'Returned <PR> & evidence',
            'last_progress_at': '2026-09-24T11:00:00Z',
            'next_event': 'Review <PR>', 'next_owner': 'Owner & team',
            'follow_up_due_at': '2026-09-24T11:30:00Z',
        }
        card, column = dashboard.task_card(item, [], {'updated_at': '2026-09-24T12:00:00Z'})
        self.assertEqual('working', column)
        self.assertIn('Last meaningful progress:</strong> Returned &lt;PR&gt; &amp; evidence', card)
        self.assertIn('At:</strong> 24 Sep 2026 · 11:00 UTC', card)
        self.assertIn('Next event:</strong> Review &lt;PR&gt; · <strong>Next owner:</strong> Owner &amp; team', card)
        self.assertIn('summary-follow-up status-attention">Overdue follow-up', card)
        self.assertIn('Follow-up:</strong> <span class="status-text status-attention">Overdue follow-up', card)
        self.assertNotIn('<PR>', card)

    def test_waiting_duration_is_snapshot_relative_and_future_time_is_not_negative(self):
        waiting = {
            'id': 'waiting', 'state': 'waiting', 'waiting_since': '2026-09-24T10:00:00Z',
            'waiting_owner': 'publisher', 'next_event': 'CI return',
        }
        card, _ = dashboard.task_card(waiting, [], {'updated_at': '2026-09-24T12:30:00Z'})
        self.assertIn('Waiting duration:</strong> 2h 30m', card)
        future = dict(waiting, waiting_since='2026-09-24T13:00:00Z')
        card, _ = dashboard.task_card(future, [], {'updated_at': '2026-09-24T12:30:00Z'})
        self.assertIn('Waiting duration:</strong> Not recorded (waiting timestamp is after snapshot)', card)
        self.assertNotIn('-', card.split('Waiting duration:</strong>', 1)[1].split('</p>', 1)[0])
        offsetless = dict(waiting, waiting_since='2026-09-24T10:00:00')
        card, _ = dashboard.task_card(offsetless, [], {'updated_at': '2026-09-24T12:30:00Z'})
        self.assertIn('Waiting duration:</strong> Not recorded', card)

    def test_missing_observability_fields_are_not_recorded(self):
        card, _ = dashboard.task_card({'id': 'unrecorded', 'state': 'waiting'}, [], {})
        self.assertIn('Last meaningful progress:</strong> Not recorded · <strong>At:</strong> Not recorded', card)
        self.assertIn('Next event:</strong> Not recorded · <strong>Next owner:</strong> Not recorded', card)
        self.assertIn('Waiting duration:</strong> Not recorded', card)
        self.assertNotIn('1970', card)

    def test_completed_pr_slice_keeps_open_parent_and_all_source_links(self):
        item = {
            'id': 'slice', 'title': 'Completed PR slice', 'state': 'done',
            'completion_scope': 'step', 'github_issue_state': 'OPEN',
            'issue_url': 'https://github.com/o/r/issues/54',
            'parent_url': 'https://github.com/o/r/issues/10',
            'pr_url': 'https://github.com/o/r/pull/8',
        }
        card, column = dashboard.task_card(item, [])
        self.assertEqual('done', column)
        self.assertIn('Step done · parent remains open', card)
        self.assertIn('Step slice complete; Parent remains open (snapshot says OPEN).', card)
        for url in ('issues/54', 'issues/10', 'pull/8'):
            self.assertIn('https://github.com/o/r/' + url, card)

        closed = dict(item, github_issue_state='CLOSED')
        closed_card, _ = dashboard.task_card(closed, [])
        self.assertIn('Step done · parent already closed', closed_card)
        self.assertNotIn('parent remains open', closed_card)
