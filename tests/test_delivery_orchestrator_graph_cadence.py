"""Mechanical checks for dependency graphs, dispatch cadence, and unblock events."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest

SPEC = importlib.util.spec_from_file_location(
    'check_schedule', Path(__file__).parents[1] / 'skills/delivery-orchestrator/scripts/check_schedule.py')
check_schedule = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check_schedule)


def local_link(anchor='record'):
    return 'artifact://graph/links.json#' + anchor


def active_item(task_id, disposition='dispatched'):
    return {
        'id': task_id,
        'ready': disposition in ('active', 'dispatched'),
        'disposition': disposition,
        'job': 'job-' + task_id,
        'evidence': 'https://github.com/example/project/actions/runs/123',
        'selected_at': '2026-09-25T09:05:00Z',
    }


def graph_node(task_id, depends_on=None, surface=None):
    return {
        'id': task_id,
        'state': 'unfinished',
        'local_link': local_link('tasks/' + task_id),
        'github_link': 'https://github.com/example/project/issues/' + task_id.rsplit('#', 1)[-1],
        'surfaces': [surface or 'src/' + task_id.replace('#', '-') + '.cs'],
        'depends_on': list(depends_on or []),
    }


def graph_edge(edge_id, from_id, to_id, **values):
    return {
        'id': edge_id,
        'kind': 'dependency',
        'from': from_id,
        'to': to_id,
        'blocker_task_id': from_id,
        'dependent_task_id': to_id,
        'state': 'verified',
        'satisfied': True,
        'local_link': local_link('edges/' + edge_id),
        'github_link': 'https://github.com/example/project/issues/' + to_id.rsplit('#', 1)[-1],
        **values,
    }


def receipt():
    ids = ['PROJECT#1', 'PROJECT#2']
    return {
        'scope_url': 'https://github.com/example/project/milestone/4',
        'checked_at': '2026-09-25T09:10:00Z',
        'source_complete': True,
        'source_ids': ids,
        'items': [active_item(task_id) for task_id in ids],
        'write_leases': [],
        'dependency_graph_required': True,
        'dependency_graph': {
            'complete': True,
            'nodes': [graph_node(task_id) for task_id in ids],
            'edges': [],
            'review': {
                'event_interval_minutes': 10,
                'full_audit_interval_minutes': 60,
                'last_full_audit_at': '2026-09-25T09:00:00Z',
                'full_audit_evidence': local_link('full-audit'),
                'critical_path_evidence': local_link('critical-path'),
                'incremental_at': '2026-09-25T09:10:00Z',
                'last_event': {
                    'event_id': 'event-return-1',
                    'kind': 'return',
                    'occurred_at': '2026-09-25T09:09:00Z',
                    'checked_at': '2026-09-25T09:10:00Z',
                    'affected_ids': ids,
                    'evidence': local_link('return-event'),
                },
            },
            'events': [],
            'validation_pauses': [],
        },
        'checkpoint': {
            'trigger': 'return',
            'next_owner': 'coordinator',
            'next_event': 'verified worker return',
            'assessment_evidence': local_link('assessment'),
            'last_progress_at': '2026-09-25T09:00:00Z',
            'last_progress_evidence': local_link('startup'),
            'source_query': local_link('source-query'),
            'hierarchy_evidence': local_link('hierarchy'),
            'source_retrieved_at': '2026-09-25T09:00:00Z',
            'unchanged_checks': 0,
        },
    }


class DependencyGraphCadenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence_dir = tempfile.TemporaryDirectory()
        cls.artifact_root = Path(cls.evidence_dir.name)
        (cls.artifact_root / 'graph').mkdir()
        (cls.artifact_root / 'graph' / 'links.json').write_text('{}', encoding='utf-8')

    @classmethod
    def tearDownClass(cls):
        cls.evidence_dir.cleanup()

    def validate(self, record):
        return check_schedule.validate_schedule(record, artifact_root=self.artifact_root)

    def test_complete_graph_requires_local_and_github_links_for_every_node_and_edge(self):
        record = receipt()
        record['dependency_graph']['nodes'][1]['depends_on'] = ['PROJECT#1']
        record['dependency_graph']['nodes'][0]['state'] = 'complete'
        record['dependency_graph']['nodes'][0].update({
            'completed_at': '2026-09-25T09:00:00Z',
            'completion_evidence': local_link('completed-prerequisite'),
        })
        record['source_ids'] = ['PROJECT#2']
        record['items'] = [record['items'][1]]
        record['dependency_graph']['nodes'].append(graph_node('PROJECT#3', surface='src/extra.cs'))
        record['source_ids'].append('PROJECT#3')
        record['items'].append(active_item('PROJECT#3'))
        record['dependency_graph']['edges'] = [graph_edge('edge-1', 'PROJECT#1', 'PROJECT#2')]

        self.assertEqual([], self.validate(record))

        missing = copy.deepcopy(record)
        missing['dependency_graph']['nodes'].pop()
        self.assertTrue(any('exactly match source_ids' in error for error in self.validate(missing)))

        unlinked = copy.deepcopy(record)
        unlinked['dependency_graph']['edges'][0].pop('github_link')
        self.assertTrue(any('github_link must link' in error for error in self.validate(unlinked)))

    def test_graph_gate_has_no_fixed_worker_count_cap(self):
        record = receipt()
        ids = [f'PROJECT#{number}' for number in range(1, 13)]
        record['source_ids'] = ids
        record['items'] = [active_item(task_id) for task_id in ids]
        record['dependency_graph']['nodes'] = [graph_node(task_id) for task_id in ids]
        record['dependency_graph']['review']['last_event']['affected_ids'] = ids

        self.assertEqual([], self.validate(record))

    def test_malformed_surface_values_return_validation_errors_instead_of_crashing(self):
        record = receipt()
        record['dependency_graph']['nodes'][0]['surfaces'] = [{'unknown': 'shape'}]
        record['items'][0]['disposition'] = ['not', 'a', 'disposition']

        errors = self.validate(record)

        self.assertTrue(any('surfaces must list' in error for error in errors))
        self.assertTrue(any('disposition is unknown' in error for error in errors))

    def test_malformed_collection_values_return_errors_instead_of_crashing(self):
        record = receipt()
        record['source_ids'] = None
        record['items'] = None
        record['write_leases'] = None

        errors = self.validate(record)

        self.assertTrue(any('source_ids must be an array' in error for error in errors))
        self.assertTrue(any('items must be an array' in error for error in errors))
        self.assertTrue(any('write_leases must list' in error for error in errors))

    def test_strict_mode_rejects_incomplete_graph_but_legacy_receipts_are_not_certified(self):
        record = receipt()
        record['dependency_graph']['complete'] = False
        self.assertTrue(any('complete must be true' in error for error in self.validate(record)))

        legacy = receipt()
        legacy.pop('dependency_graph')
        legacy.pop('dependency_graph_required')
        self.assertEqual([], self.validate(legacy))

    def test_stale_or_unknown_dependency_edges_cannot_dispatch_dependents(self):
        for state in ('stale', 'unknown'):
            record = receipt()
            record['dependency_graph']['nodes'][1]['depends_on'] = ['PROJECT#1']
            edge = graph_edge('edge-1', 'PROJECT#1', 'PROJECT#2', state=state)
            record['dependency_graph']['edges'] = [edge]
            errors = self.validate(record)
            self.assertTrue(any('every incoming dependency edge is verified and satisfied' in error for error in errors), state)

    def test_event_reassessment_overrides_the_ten_minute_tick_without_waiting_for_hourly_audit(self):
        record = receipt()
        record['checked_at'] = '2026-09-25T09:09:00Z'
        record['dependency_graph']['review']['incremental_at'] = '2026-09-25T09:09:00Z'
        record['dependency_graph']['review']['last_event'].update({
            'kind': 'unblock',
            'occurred_at': '2026-09-25T09:08:00Z',
            'checked_at': '2026-09-25T09:09:00Z',
            'affected_ids': ['PROJECT#2'],
        })
        record['items'][1]['selected_at'] = '2026-09-25T09:09:00Z'

        self.assertEqual([], self.validate(record))

    def test_event_reassessment_later_than_ten_minutes_is_rejected(self):
        record = receipt()
        record['dependency_graph']['review']['last_event'].update({
            'occurred_at': '2026-09-25T08:59:00Z',
            'checked_at': '2026-09-25T09:10:00Z',
        })

        errors = self.validate(record)

        self.assertTrue(any('not incrementally reassessed within the configured interval' in error for error in errors))

    def test_dispatch_after_hourly_graph_and_critical_path_audit_is_due_fails(self):
        record = receipt()
        record['checked_at'] = '2026-09-25T10:05:00Z'
        review = record['dependency_graph']['review']
        review['incremental_at'] = '2026-09-25T10:05:00Z'
        review['last_event'].update({
            'occurred_at': '2026-09-25T10:04:00Z',
            'checked_at': '2026-09-25T10:05:00Z',
        })
        record['items'][1]['selected_at'] = '2026-09-25T10:01:00Z'

        errors = self.validate(record)

        self.assertTrue(any('full graph/critical-path audit became due' in error for error in errors))

    def test_open_writer_conflict_blocks_only_the_deferred_surface(self):
        record = receipt()
        record['dependency_graph']['nodes'] = [
            graph_node('PROJECT#1', surface='src/shared.cs'),
            graph_node('PROJECT#2', surface='src/shared.cs'),
        ]
        blocked = record['items'][1]
        blocked.update({
            'ready': False,
            'disposition': 'conflict-blocked',
            'reason': 'PROJECT#1 holds src/shared.cs',
            'conflict_surface': 'src/shared.cs',
            'next_owner': 'coordinator',
            'next_event': 'writer completion and ownership check',
        })
        record['write_leases'] = [{
            'id': 'lease-writer', 'owner': 'worker-one', 'job': 'job-PROJECT#1',
            'surface': 'src/shared.cs', 'state': 'held', 'writer_state': 'running',
            'evidence': local_link('writer-lease'), 'recheck_at': '2026-09-25T09:20:00Z',
            'repository': 'example/project', 'paths': ['src/shared.cs'], 'resources': [],
        }]
        record['dependency_graph']['edges'] = [{
            'id': 'conflict-1', 'kind': 'conflict', 'from': 'PROJECT#1', 'to': 'PROJECT#2',
            'blocking_task_id': 'PROJECT#1', 'deferred_task_id': 'PROJECT#2',
            'state': 'verified', 'lifecycle': 'open', 'surface': 'src/shared.cs',
            'write_lease_id': 'lease-writer', 'discovery_event_id': 'collision-1',
            'local_link': local_link('collision-local'),
            'github_link': 'https://github.com/example/project/issues/2',
        }]
        record['dependency_graph']['events'] = [{
            'event_id': 'collision-1', 'kind': 'conflict-discovered', 'edge_id': 'conflict-1',
            'blocking_task_id': 'PROJECT#1', 'deferred_task_id': 'PROJECT#2',
            'surface': 'src/shared.cs', 'observed_at': '2026-09-25T09:08:00Z',
            'evidence': local_link('collision-evidence'),
        }]
        record['dependency_graph']['review']['last_event'].update({
            'event_id': 'collision-1', 'kind': 'conflict-discovered',
            'occurred_at': '2026-09-25T09:08:00Z',
            'affected_ids': ['PROJECT#1', 'PROJECT#2'],
        })

        self.assertEqual([], self.validate(record))

        blocked['ready'] = True
        blocked['disposition'] = 'dispatched'
        blocked['selected_at'] = '2026-09-25T09:10:00Z'
        self.assertTrue(any('conflict surface and writer are verified/released' in error
                            for error in self.validate(record)))

    def test_two_selected_tasks_cannot_write_the_same_surface(self):
        record = receipt()
        record['dependency_graph']['nodes'] = [
            graph_node('PROJECT#1', surface='src/shared.cs'),
            graph_node('PROJECT#2', surface='src/shared.cs'),
        ]

        errors = self.validate(record)

        self.assertTrue(any('selected writers for overlapping surface' in error for error in errors))

    def test_unknown_dynamic_conflict_quarantines_both_tasks(self):
        record = receipt()
        record['dependency_graph']['nodes'] = [
            graph_node('PROJECT#1', surface='src/shared.cs'),
            graph_node('PROJECT#2', surface='src/shared.cs'),
        ]
        record['items'][0]['disposition'] = 'active'
        record['items'][1].update({
            'ready': False,
            'disposition': 'conflict-blocked',
            'reason': 'PROJECT#1 holds src/shared.cs while ownership is checked',
            'conflict_surface': 'src/shared.cs',
            'next_owner': 'coordinator',
            'next_event': 'verify the current writer owner',
        })
        record['dependency_graph']['edges'] = [{
            'id': 'conflict-unknown', 'kind': 'conflict', 'from': 'PROJECT#1', 'to': 'PROJECT#2',
            'blocking_task_id': 'PROJECT#1', 'deferred_task_id': 'PROJECT#2',
            'state': 'unknown', 'lifecycle': 'open', 'surface': 'src/shared.cs',
            'write_lease_id': 'lease-writer', 'discovery_event_id': 'collision-unknown',
            'local_link': local_link('collision-local'),
            'github_link': 'https://github.com/example/project/issues/2',
        }]
        record['write_leases'] = [{
            'id': 'lease-writer', 'owner': 'worker-one', 'job': 'job-PROJECT#1',
            'surface': 'src/shared.cs', 'state': 'held', 'writer_state': 'running',
            'evidence': local_link('writer-lease'), 'recheck_at': '2026-09-25T09:20:00Z',
            'repository': 'example/project', 'paths': ['src/shared.cs'], 'resources': [],
        }]
        record['dependency_graph']['events'] = [{
            'event_id': 'collision-unknown', 'kind': 'conflict-discovered', 'edge_id': 'conflict-unknown',
            'blocking_task_id': 'PROJECT#1', 'deferred_task_id': 'PROJECT#2',
            'surface': 'src/shared.cs', 'observed_at': '2026-09-25T09:08:00Z',
            'evidence': local_link('collision-evidence'),
        }]
        record['dependency_graph']['review']['last_event'].update({
            'event_id': 'collision-unknown', 'kind': 'conflict-discovered',
            'occurred_at': '2026-09-25T09:08:00Z',
            'affected_ids': ['PROJECT#1', 'PROJECT#2'],
        })

        self.assertEqual([], self.validate(record))

        record['write_leases'][0]['writer_state'] = 'unknown'
        self.assertTrue(any('current ownership is unknown' in error for error in self.validate(record)))
        record['write_leases'][0]['writer_state'] = 'running'

        record['items'][1].update({'ready': True, 'disposition': 'dispatched', 'selected_at': '2026-09-25T09:10:00Z'})
        self.assertTrue(any('conflict surface and writer are verified/released' in error
                            for error in self.validate(record)))

    def test_conflict_release_requires_actual_ownership_check_and_exactly_once_reassessment(self):
        record = receipt()
        record['dependency_graph']['nodes'] = [
            graph_node('PROJECT#1', surface='src/shared.cs'),
            graph_node('PROJECT#2', surface='src/shared.cs'),
        ]
        record['dependency_graph']['nodes'][0]['state'] = 'complete'
        record['dependency_graph']['nodes'][0].update({
            'completed_at': '2026-09-25T09:07:00Z',
            'completion_evidence': local_link('writer-completion'),
        })
        record['source_ids'] = ['PROJECT#2']
        record['items'] = [record['items'][1]]
        record['items'][0].update({
            'ready': False,
            'disposition': 'conflict-blocked',
            'reason': 'PROJECT#1 held src/shared.cs until its completion and ownership were verified',
            'conflict_surface': 'src/shared.cs',
            'next_owner': 'coordinator',
            'next_event': 'release writer reservation and reassess',
        })
        record['write_leases'] = [{
            'id': 'lease-writer', 'owner': 'worker-one', 'job': 'job-PROJECT#1',
            'surface': 'src/shared.cs', 'state': 'released', 'writer_state': 'completed',
            'evidence': local_link('writer-lease'), 'repository': 'example/project',
            'paths': ['src/shared.cs'], 'resources': [],
        }]
        edge = {
            'id': 'conflict-1', 'kind': 'conflict', 'from': 'PROJECT#1', 'to': 'PROJECT#2',
            'blocking_task_id': 'PROJECT#1', 'deferred_task_id': 'PROJECT#2',
            'state': 'verified', 'lifecycle': 'released', 'surface': 'src/shared.cs',
            'write_lease_id': 'lease-writer', 'discovery_event_id': 'collision-1',
            'release_event_id': 'release-1',
            'writer_completed_at': '2026-09-25T09:07:00Z',
            'writer_completion_evidence': local_link('writer-completion'),
            'ownership_checked_at': '2026-09-25T09:08:00Z',
            'ownership_check_type': 'actual-owner-verified',
            'ownership_check_evidence': local_link('ownership-check'),
            'local_link': local_link('collision-local'),
            'github_link': 'https://github.com/example/project/issues/2',
        }
        record['dependency_graph']['edges'] = [edge]
        record['dependency_graph']['events'] = [
            {'event_id': 'collision-1', 'kind': 'conflict-discovered', 'edge_id': 'conflict-1',
             'blocking_task_id': 'PROJECT#1', 'deferred_task_id': 'PROJECT#2',
             'surface': 'src/shared.cs', 'observed_at': '2026-09-25T09:05:00Z', 'evidence': local_link('collision-evidence')},
            {'event_id': 'release-1', 'kind': 'conflict-released', 'edge_id': 'conflict-1',
             'blocking_task_id': 'PROJECT#1', 'deferred_task_id': 'PROJECT#2', 'surface': 'src/shared.cs',
             'observed_at': '2026-09-25T09:09:00Z', 'evidence': local_link('release-evidence')},
            {'event_id': 'reeval-1', 'kind': 'successor-reassessed', 'release_event_id': 'release-1',
             'task_id': 'PROJECT#2', 'result_disposition': 'dispatched',
             'observed_at': '2026-09-25T09:10:00Z', 'evidence': local_link('successor-startup')},
        ]
        record['dependency_graph']['review']['last_event'].update({
            'event_id': 'release-1', 'kind': 'conflict-released',
            'occurred_at': '2026-09-25T09:09:00Z',
            'affected_ids': ['PROJECT#1', 'PROJECT#2'],
        })
        record['items'][0].update({
            'ready': True,
            'disposition': 'dispatched',
            'selected_at': '2026-09-25T09:10:00Z',
        })

        self.assertEqual([], self.validate(record))

        later_event = copy.deepcopy(record)
        later_event['checked_at'] = '2026-09-25T09:12:00Z'
        later_event['dependency_graph']['review']['incremental_at'] = '2026-09-25T09:12:00Z'
        later_event['dependency_graph']['events'].append({
            'event_id': 'review-2', 'kind': 'review-verdict', 'blocking_task_id': 'PROJECT#2',
            'held_dependent_task_ids': [], 'review_verdict': 'CHANGES_NEEDED',
            'reviewed_head': 'abc123', 'expected_head': 'abc123', 'head_current': True,
            'observed_at': '2026-09-25T09:11:00Z', 'evidence': local_link('later-review'),
        })
        later_event['dependency_graph']['review']['last_event'].update({
            'event_id': 'review-2', 'kind': 'review-verdict',
            'occurred_at': '2026-09-25T09:11:00Z', 'checked_at': '2026-09-25T09:12:00Z',
            'affected_ids': ['PROJECT#2'], 'evidence': local_link('later-review'),
        })
        self.assertEqual([], self.validate(later_event))

        incomplete_writer = copy.deepcopy(record)
        incomplete_writer['dependency_graph']['nodes'][0]['state'] = 'unfinished'
        self.assertTrue(any('cannot release until its blocking writer task is complete'
                            in error for error in self.validate(incomplete_writer)))

        duplicate = copy.deepcopy(record['dependency_graph']['events'][-1])
        duplicate['event_id'] = 'reeval-duplicate'
        record['dependency_graph']['events'].append(duplicate)
        errors = self.validate(record)
        self.assertTrue(any('reassess one release event exactly once' in error for error in errors))

        record['dependency_graph']['events'].pop()
        edge.pop('ownership_check_type')
        errors = self.validate(record)
        self.assertTrue(any('actual current ownership check' in error for error in errors))

    def test_approved_review_reactivates_only_its_declared_dependent_once(self):
        record = receipt()
        dependent = record['items'][1]
        record['dependency_graph']['nodes'][1]['depends_on'] = ['PROJECT#1']
        edge = graph_edge(
            'dependency-1', 'PROJECT#1', 'PROJECT#2', satisfied=True,
            gate_type='reviewer-approval', blocker_notified_evidence=local_link('blocker-notice'),
            reviewer_handover_evidence=local_link('reviewer-handover'),
            reviewer_handover_dependent_ids=['PROJECT#2'], resume_packet=local_link('resume-packet'),
            unblock_condition='Independent exact-head review approved and base remains safe.')
        record['dependency_graph']['edges'] = [edge]
        record['dependency_graph']['events'] = [
            {'event_id': 'review-1', 'kind': 'review-verdict', 'blocking_task_id': 'PROJECT#1',
             'held_dependent_task_ids': ['PROJECT#2'], 'review_verdict': 'APPROVED',
             'reviewed_head': 'abc123', 'expected_head': 'abc123', 'head_current': True,
             'observed_at': '2026-09-25T09:08:00Z', 'evidence': 'https://github.com/example/project/pull/1#review-1'},
            {'event_id': 'resume-1', 'kind': 'resume-assessment', 'task_id': 'PROJECT#2',
             'source_event_id': 'review-1',
             'ownership_verified': True, 'base_safe': True,
             'ownership_evidence': local_link('ownership'), 'base_evidence': local_link('base'),
             'observed_at': '2026-09-25T09:09:00Z', 'evidence': local_link('resume-assessment')},
            {'event_id': 'reactivation-1', 'kind': 'dependency-reactivated', 'edge_id': 'dependency-1',
             'task_id': 'PROJECT#2', 'generation': 1, 'source_event_id': 'review-1',
             'assessment_event_id': 'resume-1', 'observed_at': '2026-09-25T09:10:00Z',
            'evidence': local_link('reactivation')},
        ]
        record['dependency_graph']['review']['last_event'].update({
            'event_id': 'review-1', 'kind': 'review-verdict',
            'occurred_at': '2026-09-25T09:08:00Z',
            'affected_ids': ['PROJECT#1', 'PROJECT#2'],
        })
        dependent['selected_at'] = '2026-09-25T09:10:00Z'

        self.assertEqual([], self.validate(record))

        later_event = copy.deepcopy(record)
        later_event['checked_at'] = '2026-09-25T09:12:00Z'
        later_event['dependency_graph']['review']['incremental_at'] = '2026-09-25T09:12:00Z'
        later_event['dependency_graph']['events'].append({
            'event_id': 'review-2', 'kind': 'review-verdict', 'blocking_task_id': 'PROJECT#1',
            'held_dependent_task_ids': [], 'review_verdict': 'CHANGES_NEEDED',
            'reviewed_head': 'abc123', 'expected_head': 'abc123', 'head_current': True,
            'observed_at': '2026-09-25T09:11:00Z', 'evidence': local_link('later-review'),
        })
        later_event['dependency_graph']['review']['last_event'].update({
            'event_id': 'review-2', 'kind': 'review-verdict',
            'occurred_at': '2026-09-25T09:11:00Z', 'checked_at': '2026-09-25T09:12:00Z',
            'affected_ids': ['PROJECT#1'], 'evidence': local_link('later-review'),
        })
        self.assertEqual([], self.validate(later_event))

        missing_provenance = copy.deepcopy(record)
        missing_provenance['dependency_graph']['edges'][0].pop('gate_type')
        missing_provenance['dependency_graph']['edges'][0].pop('blocker_notified_evidence')
        errors = self.validate(missing_provenance)
        self.assertTrue(any('.gate_type must be reviewer-approval or accepted-integration' in error
                            for error in errors))
        self.assertTrue(any('.blocker_notified_evidence must link' in error for error in errors))

        repeated = copy.deepcopy(record['dependency_graph']['events'][-1])
        repeated['event_id'] = 'reactivation-2'
        record['dependency_graph']['events'].append(repeated)
        errors = self.validate(record)
        self.assertTrue(any('repeats dependency reactivation' in error for error in errors))

    def test_review_approval_does_not_release_integration_gate(self):
        record = receipt()
        record['dependency_graph']['nodes'][1]['depends_on'] = ['PROJECT#1']
        edge = graph_edge(
            'dependency-1', 'PROJECT#1', 'PROJECT#2', satisfied=True,
            gate_type='accepted-integration', blocker_notified_evidence=local_link('blocker-notice'),
            reviewer_handover_evidence=local_link('reviewer-handover'),
            reviewer_handover_dependent_ids=['PROJECT#2'], resume_packet=local_link('resume-packet'),
            unblock_condition='Accepted integration event for PROJECT#1.')
        record['dependency_graph']['edges'] = [edge]
        record['dependency_graph']['events'] = [
            {'event_id': 'review-1', 'kind': 'review-verdict', 'blocking_task_id': 'PROJECT#1',
             'held_dependent_task_ids': [], 'review_verdict': 'APPROVED',
             'reviewed_head': 'abc123', 'expected_head': 'abc123', 'head_current': True,
             'observed_at': '2026-09-25T09:08:00Z', 'evidence': 'https://github.com/example/project/pull/1#review-1'},
            {'event_id': 'resume-1', 'kind': 'resume-assessment', 'task_id': 'PROJECT#2',
             'source_event_id': 'review-1',
             'ownership_verified': True, 'base_safe': True,
             'ownership_evidence': local_link('ownership'), 'base_evidence': local_link('base'),
             'observed_at': '2026-09-25T09:09:00Z', 'evidence': local_link('resume-assessment')},
            {'event_id': 'reactivation-1', 'kind': 'dependency-reactivated', 'edge_id': 'dependency-1',
             'task_id': 'PROJECT#2', 'generation': 1, 'source_event_id': 'review-1',
             'assessment_event_id': 'resume-1', 'observed_at': '2026-09-25T09:10:00Z',
            'evidence': local_link('reactivation')},
        ]
        record['dependency_graph']['review']['last_event'].update({
            'event_id': 'review-1', 'kind': 'review-verdict',
            'occurred_at': '2026-09-25T09:08:00Z',
            'affected_ids': ['PROJECT#1', 'PROJECT#2'],
        })

        errors = self.validate(record)

        self.assertTrue(any('review approval cannot release integration gates' in error for error in errors))

    def test_accepted_integration_event_releases_only_after_safe_reassessment(self):
        record = receipt()
        record['dependency_graph']['nodes'][1]['depends_on'] = ['PROJECT#1']
        edge = graph_edge(
            'dependency-1', 'PROJECT#1', 'PROJECT#2', satisfied=True,
            gate_type='accepted-integration', blocker_notified_evidence=local_link('blocker-notice'),
            reviewer_handover_evidence=local_link('reviewer-handover'),
            reviewer_handover_dependent_ids=['PROJECT#2'], resume_packet=local_link('resume-packet'),
            unblock_condition='Accepted integration event for PROJECT#1.')
        record['dependency_graph']['edges'] = [edge]
        record['dependency_graph']['events'] = [
            {'event_id': 'integration-1', 'kind': 'integration-accepted',
             'blocking_task_id': 'PROJECT#1', 'held_dependent_task_ids': ['PROJECT#2'],
             'integrated_ref': 'sha:deadbeef', 'observed_at': '2026-09-25T09:08:00Z',
             'evidence': 'https://github.com/example/project/commit/deadbeef'},
            {'event_id': 'resume-1', 'kind': 'resume-assessment', 'task_id': 'PROJECT#2',
             'source_event_id': 'integration-1', 'ownership_verified': True, 'base_safe': True,
             'ownership_evidence': local_link('ownership'), 'base_evidence': local_link('base'),
             'observed_at': '2026-09-25T09:09:00Z', 'evidence': local_link('resume-assessment')},
            {'event_id': 'reactivation-1', 'kind': 'dependency-reactivated', 'edge_id': 'dependency-1',
             'task_id': 'PROJECT#2', 'generation': 1, 'source_event_id': 'integration-1',
             'assessment_event_id': 'resume-1', 'observed_at': '2026-09-25T09:10:00Z',
             'evidence': local_link('reactivation')},
        ]
        record['dependency_graph']['review']['last_event'].update({
            'event_id': 'integration-1', 'kind': 'integration-accepted',
            'occurred_at': '2026-09-25T09:08:00Z',
            'affected_ids': ['PROJECT#1', 'PROJECT#2'],
        })
        record['items'][1]['selected_at'] = '2026-09-25T09:10:00Z'

        self.assertEqual([], self.validate(record))

    def test_ux_e2e_pause_holds_only_affected_surface(self):
        record = receipt()
        record['dependency_graph']['validation_pauses'] = [{
            'id': 'pause-ux-1', 'kind': 'ux-e2e', 'state': 'active',
            'affected_ids': ['PROJECT#2'], 'surfaces': ['src/'],
            'evidence': local_link('ux-e2e-finding'),
        }]

        errors = self.validate(record)
        self.assertTrue(any('PROJECT#1 is dispatchable while its affected surface has an active UX/E2E validation pause'
                            in error for error in errors))

        record['dependency_graph']['validation_pauses'][0]['surfaces'] = ['docs/']
        errors = self.validate(record)
        self.assertFalse(any('PROJECT#1 is dispatchable while its affected surface has an active UX/E2E validation pause'
                             in error for error in errors))
        self.assertTrue(any('PROJECT#2 is dispatchable while its affected surface has an active UX/E2E validation pause'
                            in error for error in errors))


if __name__ == '__main__':
    unittest.main()
