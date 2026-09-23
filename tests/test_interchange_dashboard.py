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

    def test_unsafe_identity_refused(self):
        with self.assertRaises(ValueError):
            dashboard.publish('.', {'project_id': '../bad', 'coordinator': {'agent_id': 'x'}})
