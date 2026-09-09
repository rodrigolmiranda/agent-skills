"""Tests for the fail-closed Interchange PR base guard."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "interchange" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from pr_base_guard import (  # noqa: E402
    PullRequestBaseError,
    require_pr_base,
    validate_pr_base,
)


BASE_SHA = "1" * 40
HEAD_SHA = "2" * 40


class PullRequestBaseGuardTests(unittest.TestCase):
    def test_ordinary_main_is_rejected_before_creation(self) -> None:
        decision = validate_pr_base(
            {"operation_class": "ordinary", "base_ref": "main", "head_ref": "fix/a"}
        )
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "ordinary_base_denied")
        with self.assertRaises(PullRequestBaseError):
            require_pr_base(
                {"operation_class": "ordinary", "base_ref": "main", "head_ref": "fix/a"}
            )

    def test_ordinary_test_is_accepted(self) -> None:
        decision = require_pr_base(
            {"operation_class": "ordinary", "base_ref": "test", "head_ref": "fix/a"}
        )
        self.assertTrue(decision.allowed)
        self.assertEqual(decision.code, "ordinary_test")

    def test_hotfix_main_exception_requires_exact_human_evidence(self) -> None:
        decision = require_pr_base(
            {
                "operation_class": "hotfix",
                "base_ref": "main",
                "head_ref": "hotfix/auth-timeout",
                "human_controlled": True,
                "human_only_merge": True,
                "base_evidence": {"ref": "main", "sha": BASE_SHA},
                "head_evidence": {"ref": "hotfix/auth-timeout", "sha": HEAD_SHA},
            }
        )
        self.assertEqual(decision.code, "human_main_exception")

    def test_release_main_exception_requires_exception_shape(self) -> None:
        decision = validate_pr_base(
            {
                "operation_class": "release_promotion",
                "base_ref": "main",
                "head_ref": "test",
                "human_controlled": True,
                "human_only_merge": True,
                "base_evidence": {"ref": "main", "sha": BASE_SHA},
                "head_evidence": {"ref": "test", "sha": HEAD_SHA},
            }
        )
        self.assertTrue(decision.allowed)

    def test_main_exception_without_exact_evidence_is_rejected(self) -> None:
        packet = {
            "operation_class": "release_promotion",
            "base_ref": "main",
            "head_ref": "test",
            "human_controlled": True,
            "human_only_merge": True,
            "base_evidence": {"ref": "main", "sha": BASE_SHA},
        }
        decision = validate_pr_base(packet)
        self.assertFalse(decision.allowed)
        self.assertEqual(decision.code, "exact_head_evidence_required")

    def test_main_exception_with_mismatched_evidence_is_rejected(self) -> None:
        decision = validate_pr_base(
            {
                "operation_class": "release_promotion",
                "base_ref": "main",
                "head_ref": "test",
                "human_controlled": True,
                "human_only_merge": True,
                "base_evidence": {"ref": "main", "sha": BASE_SHA},
                "head_evidence": {"ref": "other-head", "sha": HEAD_SHA},
            }
        )
        self.assertEqual(decision.code, "exact_head_evidence_required")

    def test_hotfix_exception_cannot_use_non_hotfix_head(self) -> None:
        decision = validate_pr_base(
            {
                "operation_class": "hotfix",
                "base_ref": "main",
                "head_ref": "fix/a",
                "human_controlled": True,
                "human_only_merge": True,
                "base_evidence": {"ref": "main", "sha": BASE_SHA},
                "head_evidence": {"ref": "fix/a", "sha": HEAD_SHA},
            }
        )
        self.assertEqual(decision.code, "hotfix_head_denied")


if __name__ == "__main__":
    unittest.main()
