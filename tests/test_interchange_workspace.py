import importlib.util
import json
from pathlib import Path
import tempfile
import subprocess
import unittest

spec = importlib.util.spec_from_file_location('workspace', Path(__file__).parents[1] / 'skills/interchange/scripts/workspace.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)

class WorkspaceTests(unittest.TestCase):
    def test_escape_and_symlink_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'root'; root.mkdir()
            (root / 'link').symlink_to(Path(directory))
            for value in ('../outside', '/tmp', 'link/outside'):
                with self.assertRaises(ValueError): w.inside(root, value)

    def test_unknown_retained_and_no_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); (root / 'log').write_text('proof')
            manifest = root / 'workspace.json'; mapping = root / 'machine.json'
            manifest.write_text(json.dumps({'retention_days': {'raw-log': 30}, 'resources': [{'id': 'x', 'kind': 'raw-log', 'path': 'log'}]}))
            mapping.write_text('{}')
            result = w.inspect(manifest, mapping)
            self.assertEqual('retain', result['resources'][0]['decision'])
            self.assertFalse(result['deletion_supported'])
            self.assertEqual('proof', (root / 'log').read_text())

    def test_dirty_worktree_stays_retained(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); repo = root / 'repo'
            def run(*args):
                return subprocess.check_output(['git', '-C', str(repo), *args], text=True).strip()
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            run('-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', 'commit', '--allow-empty', '-qm', 'baseline')
            head = run('rev-parse', 'HEAD')
            run('update-ref', 'refs/remotes/origin/test', head)
            manifest = root / 'workspace.json'; mapping = root / 'machine.json'
            item = {'id': 'job', 'kind': 'worktree', 'repository_id': 'repo', 'verified_head': head,
                    'active_owner': False, 'holds': [], 'disposition': 'accepted-merged',
                    'closed_at': '2000-01-01T00:00:00Z', 'archive_verified': True}
            manifest.write_text(json.dumps({'retention_days': {'worktree': 7}, 'resources': [item]}))
            mapping.write_text(json.dumps({'repositories': {'repo': str(repo)}, 'worktrees': {'job': str(repo)}}))
            self.assertEqual('candidate-for-review', w.inspect(manifest, mapping)['resources'][0]['decision'])
            (repo / 'untracked').write_text('keep')
            result = w.inspect(manifest, mapping)['resources'][0]
            self.assertEqual('retain', result['decision'])
            self.assertIn('dirty or untracked work', result['reasons'])
            self.assertEqual('keep', (repo / 'untracked').read_text())
