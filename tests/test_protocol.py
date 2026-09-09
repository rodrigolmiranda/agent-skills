"""Tests for the bounded, deterministic Interchange protocol."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


SCRIPTS = Path(__file__).resolve().parents[1] / "skills" / "interchange" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from protocol import classify_completion, completion_marker, polling_schedule  # noqa: E402


PACKET_ID = "packet-17"
ATTEMPT_ID = "attempt-2"


def final_response(**overrides: object) -> str:
    response = {
        "packet_id": PACKET_ID,
        "attempt_id": ATTEMPT_ID,
        "result": "ready_for_review",
        "summary": "Implemented the bounded protocol.",
        "evidence": ["unit tests pass"],
    }
    response.update(overrides)
    return f"{json.dumps(response)}\n{completion_marker(PACKET_ID, ATTEMPT_ID)}\n"


class CompletionClassificationTests(unittest.TestCase):
    def test_ready_response_never_becomes_accepted_here(self) -> None:
        text = final_response()
        self.assertEqual(
            classify_completion(text, 0, PACKET_ID, ATTEMPT_ID), "ready_for_review"
        )

    def test_quoted_marker_is_not_a_terminal_marker(self) -> None:
        text = final_response().replace(
            completion_marker(PACKET_ID, ATTEMPT_ID),
            f'"{completion_marker(PACKET_ID, ATTEMPT_ID)}"',
        )
        self.assertEqual(
            classify_completion(text, 0, PACKET_ID, ATTEMPT_ID), "incomplete"
        )

    def test_marker_for_another_attempt_is_incomplete(self) -> None:
        text = final_response().replace(ATTEMPT_ID, "attempt-3")
        self.assertEqual(
            classify_completion(text, 0, PACKET_ID, ATTEMPT_ID), "incomplete"
        )

    def test_nonzero_exit_takes_precedence_over_plausible_response(self) -> None:
        self.assertEqual(
            classify_completion(final_response(), 9, PACKET_ID, ATTEMPT_ID), "failed"
        )

    def test_partial_response_never_reports_success(self) -> None:
        self.assertEqual(
            classify_completion(
                final_response(result="partial"),
                0,
                PACKET_ID,
                ATTEMPT_ID,
            ),
            "incomplete",
        )

    def test_strict_schema_rejects_wrong_evidence_and_summary_types(self) -> None:
        self.assertEqual(
            classify_completion(
                final_response(evidence="tests pass"), 0, PACKET_ID, ATTEMPT_ID
            ),
            "incomplete",
        )
        self.assertEqual(
            classify_completion(
                final_response(summary=["implemented"]), 0, PACKET_ID, ATTEMPT_ID
            ),
            "incomplete",
        )

    def test_object_shaped_evidence_is_incomplete(self) -> None:
        self.assertEqual(
            classify_completion(
                final_response(evidence={"tests": "pass"}),
                0,
                PACKET_ID,
                ATTEMPT_ID,
            ),
            "incomplete",
        )

    def test_fenced_json_is_incomplete(self) -> None:
        text = final_response()
        json_text, marker = text.strip().splitlines()
        fenced = f"```json\n{json_text}\n```\n{marker}"
        self.assertEqual(
            classify_completion(fenced, 0, PACKET_ID, ATTEMPT_ID),
            "incomplete",
        )

    def test_backticked_marker_is_incomplete(self) -> None:
        marker = completion_marker(PACKET_ID, ATTEMPT_ID)
        text = final_response().replace(marker, f"`{marker}`")
        self.assertEqual(
            classify_completion(text, 0, PACKET_ID, ATTEMPT_ID),
            "incomplete",
        )

    def test_model_text_cannot_self_accept(self) -> None:
        text = final_response(result="accepted")
        self.assertEqual(
            classify_completion(text, 0, PACKET_ID, ATTEMPT_ID),
            "incomplete",
        )

    def test_public_api_has_no_acceptance_switch(self) -> None:
        self.assertEqual(
            classify_completion(final_response(), 0, PACKET_ID, ATTEMPT_ID),
            "ready_for_review",
        )

    def test_result_wrong_type_is_incomplete_not_an_exception(self) -> None:
        self.assertEqual(
            classify_completion(
                final_response(result=["ready_for_review"]), 0, PACKET_ID, ATTEMPT_ID
            ),
            "incomplete",
        )

    def test_extra_handback_fields_cannot_self_accept(self) -> None:
        self.assertEqual(
            classify_completion(
                final_response(accepted=True), 0, PACKET_ID, ATTEMPT_ID
            ),
            "ready_for_review",
        )

    def test_empty_evidence_is_incomplete(self) -> None:
        self.assertEqual(
            classify_completion(final_response(evidence=[]), 0, PACKET_ID, ATTEMPT_ID),
            "incomplete",
        )

    def test_duplicate_json_keys_are_incomplete(self) -> None:
        duplicate = (
            '{"packet_id":"packet-17","packet_id":"packet-17",'
            '"attempt_id":"attempt-2","result":"ready_for_review",'
            '"summary":"done","evidence":["test"]}'
        )
        text = f"{duplicate}\n{completion_marker(PACKET_ID, ATTEMPT_ID)}"
        self.assertEqual(
            classify_completion(text, 0, PACKET_ID, ATTEMPT_ID), "incomplete"
        )

    def test_nonstandard_json_constants_are_incomplete(self) -> None:
        nonstandard = (
            '{"packet_id":"packet-17","attempt_id":"attempt-2",'
            '"result":"ready_for_review","summary":"done",'
            '"evidence":[NaN]}'
        )
        text = f"{nonstandard}\n{completion_marker(PACKET_ID, ATTEMPT_ID)}"
        self.assertEqual(
            classify_completion(text, 0, PACKET_ID, ATTEMPT_ID), "incomplete"
        )

    def test_identifiers_must_be_safe_nonempty_tokens(self) -> None:
        for bad_id in ("", "packet id", "packet:id"):
            self.assertEqual(
                classify_completion(final_response(), 0, bad_id, ATTEMPT_ID),
                "incomplete",
            )


class PollingScheduleTests(unittest.TestCase):
    def test_first_poll_and_bounded_backoff(self) -> None:
        first = polling_schedule(200, 0)
        self.assertEqual(first["next_poll_seconds"], 100.0)
        later = polling_schedule(200, 0, previous_interval=250)
        self.assertEqual(later["next_poll_seconds"], 300.0)

    def test_review_and_hard_deadlines_use_elapsed_clock_only(self) -> None:
        before_review = polling_schedule(100, 190, previous_interval=60)
        self.assertEqual(before_review["next_poll_seconds"], 10.0)
        self.assertFalse(before_review["review_due"])
        at_review = polling_schedule(100, 200, previous_interval=60)
        self.assertEqual(at_review["next_poll_seconds"], 0.0)
        self.assertTrue(at_review["review_due"])
        after_hard = polling_schedule(100, 301, previous_interval=60)
        self.assertEqual(after_hard["next_poll_seconds"], 0.0)
        self.assertTrue(after_hard["hard_deadline_due"])

    def test_reported_review_does_not_repeat_but_hard_deadline_still_wins(self) -> None:
        reported = polling_schedule(
            100, 200, previous_interval=60, review_reported=True
        )
        self.assertEqual(reported["next_poll_seconds"], 90.0)
        self.assertTrue(reported["review_due"])
        at_hard = polling_schedule(
            100, 300, previous_interval=60, review_reported=True
        )
        self.assertEqual(at_hard["next_poll_seconds"], 0.0)
        self.assertTrue(at_hard["hard_deadline_due"])

    def test_estimates_must_be_positive_and_finite(self) -> None:
        for bad_expected in (0, -1, float("inf"), float("nan")):
            with self.assertRaises(ValueError):
                polling_schedule(bad_expected, 0)


if __name__ == "__main__":
    unittest.main()
