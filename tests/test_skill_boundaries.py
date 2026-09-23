"""Guard the portable skill dependency boundary and packet ownership."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SkillBoundaryTests(unittest.TestCase):
    def test_interchange_markdown_does_not_require_orchestrator_files(self):
        for path in (ROOT / 'skills/interchange').rglob('*.md'):
            for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                self.assertNotIn('delivery-orchestrator', target, str(path))

    def test_core_skills_do_not_require_portfolio_adapter(self):
        for skill in ('interchange', 'delivery-orchestrator'):
            for path in (ROOT / 'skills' / skill).rglob('*.md'):
                for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                    self.assertNotIn('adapters/', target, str(path))

    def test_relative_document_links_resolve(self):
        for folder in ('skills/interchange', 'skills/delivery-orchestrator', 'adapters'):
            for path in (ROOT / folder).rglob('*.md'):
                for target in re.findall(r'\]\(([^)]+)\)', path.read_text()):
                    if ':' in target or target.startswith('#') or '<' in target:
                        continue
                    self.assertTrue((path.parent / target.split('#')[0]).exists(), f'{path}: {target}')
