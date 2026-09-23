import concurrent.futures
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).parents[1] / 'skills/interchange/scripts/relay.py'
spec = importlib.util.spec_from_file_location('relay', SOURCE)
relay = importlib.util.module_from_spec(spec)
spec.loader.exec_module(relay)


class RelayTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.db = relay.connect(self.root / 'state.sqlite')
        self.artifact = self.root / 'result.md'
        self.artifact.write_text('Worker result; not accepted.')
        self.thread = '01a0bd84-f736-78c3-91d3-a12d9989be4f'
        relay.register(self.db, 'job', 'one', 'worker', self.root, self.thread)

    def tearDown(self):
        self.db.close(); self.tmp.cleanup()

    def emit(self, **changes):
        args = dict(job='job',attempt='one',sender='worker',kind='result',artifact=self.artifact,event_id='e1')
        args.update(changes)
        return relay.emit(self.db, **args)

    def test_event_id_deduplicates_but_changed_result_is_refused(self):
        self.assertEqual(self.emit(), self.emit())
        self.artifact.write_text('different')
        with self.assertRaises(ValueError): self.emit()

    def test_competing_same_id_emissions_do_not_silently_replace_content(self):
        other = self.root / 'other.md'; other.write_text('different result')
        def send(path):
            db = relay.connect(self.root/'state.sqlite')
            try:
                relay.emit(db,'job','one','worker','result',path,'race')
                return 'recorded'
            except ValueError:
                return 'rejected'
            finally:
                db.close()
        with concurrent.futures.ThreadPoolExecutor(2) as pool:
            results = list(pool.map(send,[self.artifact,other]))
        self.assertCountEqual(results,['recorded','rejected'])

    def test_sender_attempt_and_acceptance_cannot_be_forged_by_payload(self):
        for change in ({'sender':'other'}, {'attempt':'other'}, {'kind':'accepted'}):
            with self.assertRaises(ValueError): self.emit(**change)

    def test_path_escape_and_symlink_escape_refused(self):
        with tempfile.TemporaryDirectory() as outside:
            target = Path(outside)/'r'; target.write_text('x')
            link = self.root/'link'; link.symlink_to(target)
            for p in (target,link):
                with self.assertRaises(ValueError): self.emit(artifact=p)

    def test_route_is_immutable_for_attempt(self):
        with self.assertRaises(ValueError):
            relay.register(self.db,'job','one','other',self.root,self.thread)

    def test_literal_queue_once_ack_is_not_acceptance(self):
        self.emit()
        with patch.object(relay.subprocess,'run',return_value=subprocess.CompletedProcess([],0,'queued','')) as run:
            self.assertEqual(relay.notify(self.db,'e1')['delivery'],'queued')
            self.assertFalse(relay.notify(self.db,'e1')['sent_again'])
            self.assertEqual(run.call_count,1)
            argv = run.call_args.args[0]
            self.assertEqual(argv[:4],['codex','queue','--thread',self.thread])
            self.assertIn('"id":"e1"',argv[5])
        self.assertEqual(relay.acknowledge(self.db,'e1')['accepted'],False)

    def test_unknown_send_does_not_repeat(self):
        self.emit()
        with patch.object(relay.subprocess,'run',side_effect=subprocess.TimeoutExpired('codex',30)) as run:
            self.assertEqual(relay.notify(self.db,'e1')['delivery'],'unknown')
            relay.notify(self.db,'e1')
            self.assertEqual(run.call_count,1)

    def test_modified_artifact_not_sent(self):
        self.emit(); self.artifact.write_text('changed')
        with patch.object(relay.subprocess,'run') as run:
            with self.assertRaises(ValueError): relay.notify(self.db,'e1')
            run.assert_not_called()

    def test_manual_route_does_not_claim_wakeup(self):
        relay.register(self.db,'manual','one','worker',self.root)
        self.emit(job='manual')
        with patch.object(relay.subprocess,'run') as run:
            self.assertEqual(relay.notify(self.db,'e1')['delivery'],'manual')
            run.assert_not_called()

if __name__ == '__main__': unittest.main()
