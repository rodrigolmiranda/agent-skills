"""Tests for the fail-closed Interchange PR base guard."""

from __future__ import annotations

import sys
import json
import subprocess
import tempfile
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "interchange" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from pr_base_guard import (  # noqa: E402
    PullRequestBaseError,
    require_pr_base,
    validate_pr_base,
)


PROTOCOL = SCRIPTS / "protocol.py"


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

    def test_short_or_non_hex_sha_is_rejected_for_each_evidence_side(self) -> None:
        for evidence_name in ("base_evidence", "head_evidence"):
            for invalid_sha in ("a" * 39, "g" * 40):
                packet = {
                    "operation_class": "release_promotion",
                    "base_ref": "main",
                    "head_ref": "test",
                    "human_controlled": True,
                    "human_only_merge": True,
                    "base_evidence": {"ref": "main", "sha": BASE_SHA},
                    "head_evidence": {"ref": "test", "sha": HEAD_SHA},
                }
                packet[evidence_name]["sha"] = invalid_sha
                decision = validate_pr_base(packet)
                self.assertFalse(decision.allowed)
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


class PullRequestBaseCliTests(unittest.TestCase):
    def run_preflight(self, packet: object) -> tuple[int, dict[str, object]]:
        with tempfile.TemporaryDirectory() as directory:
            packet_file = Path(directory) / "packet.json"
            packet_file.write_text(json.dumps(packet), encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PROTOCOL),
                    "pr-base",
                    "--packet-file",
                    str(packet_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        return completed.returncode, json.loads(completed.stdout)

    def test_cli_accepts_ordinary_test_packet(self) -> None:
        code, decision = self.run_preflight(
            {"operation_class": "ordinary", "base_ref": "test", "head_ref": "fix/a"}
        )
        self.assertEqual(code, 0)
        self.assertEqual(decision["code"], "ordinary_test")
        self.assertTrue(decision["allowed"])

    def test_cli_denies_ordinary_main_packet(self) -> None:
        code, decision = self.run_preflight(
            {"operation_class": "ordinary", "base_ref": "main", "head_ref": "fix/a"}
        )
        self.assertEqual(code, 1)
        self.assertEqual(decision["code"], "ordinary_base_denied")
        self.assertFalse(decision["allowed"])

    def test_cli_accepts_explicit_release_and_hotfix_exceptions(self) -> None:
        for operation_class, head_ref in (
            ("release_promotion", "test"),
            ("hotfix", "hotfix/auth-timeout"),
        ):
            code, decision = self.run_preflight(
                {
                    "operation_class": operation_class,
                    "base_ref": "main",
                    "head_ref": head_ref,
                    "human_controlled": True,
                    "human_only_merge": True,
                    "base_evidence": {"ref": "main", "sha": BASE_SHA},
                    "head_evidence": {"ref": head_ref, "sha": HEAD_SHA},
                }
            )
            self.assertEqual(code, 0)
            self.assertEqual(decision["code"], "human_main_exception")

    def test_cli_denies_malformed_and_missing_evidence_packets(self) -> None:
        cases = (
            {"operation_class": "release_promotion", "base_ref": "main", "head_ref": "test"},
            {"operation_class": "release_promotion", "base_ref": "main", "head_ref": "test",
             "human_controlled": True, "human_only_merge": True,
             "base_evidence": {"ref": "main", "sha": BASE_SHA}},
        )
        for packet in cases:
            code, decision = self.run_preflight(packet)
            self.assertEqual(code, 1)
            self.assertFalse(decision["allowed"])

    def test_cli_denies_invalid_json_as_machine_readable_result(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            packet_file = Path(directory) / "packet.json"
            packet_file.write_text("{broken", encoding="utf-8")
            completed = subprocess.run(
                [
                    sys.executable,
                    str(PROTOCOL),
                    "pr-base",
                    "--packet-file",
                    str(packet_file),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
        self.assertEqual(completed.returncode, 1)
        self.assertEqual(json.loads(completed.stdout)["code"], "packet_invalid")


if __name__ == "__main__":
    unittest.main()
