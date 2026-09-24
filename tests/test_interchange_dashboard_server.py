import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
import urllib.request

sys.path.insert(0, str(Path(__file__).parents[1] / 'skills/interchange/scripts'))
import dashboard_server


def record(project, attempts=()):
    return {'project_id': project, 'updated_at': '2026-09-24T00:00:00+00:00',
            'coordinator': {'agent_id': 'claude-coordinator', 'client': 'claude-code'},
            'workflow_steps': [{'id': 'job-a', 'job_id': 'job-a', 'order': 1, 'title': 'Job A', 'state': 'running'}],
            'attempts': list(attempts)}


class DashboardServerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / 'projects').mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def project(self, name, data):
        folder = self.root / 'projects' / name
        folder.mkdir()
        (folder / 'continuation.json').write_text(json.dumps(data) if isinstance(data, dict) else data)
        return folder

    def test_a_new_project_appears_without_registration(self):
        self.assertIn('No coordinator snapshots', dashboard_server.build_page(self.root))
        self.project('alpha', record('alpha'))
        self.assertIn('data-project="alpha"', dashboard_server.build_page(self.root))

    def test_live_facts_are_counted_not_copied(self):
        folder = self.project('beta', record('beta', [{'agent_id': 'worker-a', 'job_id': 'job-a', 'attempt': 'a1',
                                                        'execution_state': 'running'}]))
        attempt = folder / 'jobs/job-a/attempt-a1'
        attempt.mkdir(parents=True)
        (attempt / 'stdout.log').write_bytes(b'{"type":"tool_use","secret":"SHOULD-NOT-APPEAR"}\n' * 3)
        page = dashboard_server.build_page(self.root)
        self.assertIn('3 tool calls', page)
        self.assertNotIn('SHOULD-NOT-APPEAR', page)

    def test_a_broken_project_is_an_error_card_not_a_blank_page(self):
        self.project('good', record('good'))
        self.project('broken', '{not json')
        page = dashboard_server.build_page(self.root)
        self.assertIn('data-project="good"', page)
        self.assertIn('broken</strong>: this project could not be rendered', page)

    def test_serves_over_http_on_loopback(self):
        self.project('gamma', record('gamma'))
        server = dashboard_server.ThreadingHTTPServer(('127.0.0.1', 0), dashboard_server.make_handler(self.root))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            port = server.server_address[1]
            with urllib.request.urlopen(f'http://127.0.0.1:{port}/') as response:
                self.assertEqual(response.status, 200)
                self.assertIn(b'data-project="gamma"', response.read())
            with self.assertRaises(urllib.error.HTTPError):
                urllib.request.urlopen(f'http://127.0.0.1:{port}/../etc/passwd')
        finally:
            server.shutdown()


if __name__ == '__main__':
    unittest.main()
