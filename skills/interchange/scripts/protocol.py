"""Deterministic completion validation and watchdog scheduling for Interchange.

This module validates already-collected final assistant text.  It does not run,
watch, cancel, or merge anything.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import math
from pathlib import Path
import re
import sys
from typing import Any

from pr_base_guard import validate_pr_base


_RESULTS = frozenset({"ready_for_review", "blocked", "partial"})
_SCHEMA_KEYS = frozenset(
    {"packet_id", "attempt_id", "result", "summary", "evidence"}
)
_IDENTIFIER = re.compile(r"[A-Za-z0-9._-]+\Z")


def completion_marker(packet_id: str, attempt_id: str) -> str:
    """Return the exact terminal marker bound to one packet attempt."""
    return f"INTERCHANGE_DONE:{packet_id}:{attempt_id}"


def classify_completion(
    final_text: str,
    exit_code: int | None,
    packet_id: str,
    attempt_id: str,
) -> str:
    """Classify a completed attempt without accepting model-provided success.

    ``final_text`` must be the final assistant response selected by the caller.
    This protocol can return ``ready_for_review`` but never ``accepted``.
    Acceptance belongs to a future repository/head-bound verifier.
    """
    return _completion_validation(final_text, exit_code, packet_id, attempt_id)["status"]


def polling_schedule(
    expected_seconds: float,
    elapsed_seconds: float,
    previous_interval: float | None = None,
    *,
    review_reported: bool = False,
) -> dict[str, float | bool]:
    """Return the next bounded poll and fixed review/hard deadlines.

    ``review_reported`` records that the one review escalation was emitted.
    This only calculates scheduling from elapsed wall-clock time.  It does not
    monitor a process, consume output, refresh deadlines, or cancel work.
    """
    expected = _positive_finite("expected_seconds", expected_seconds)
    elapsed = _nonnegative_finite("elapsed_seconds", elapsed_seconds)
    if not isinstance(review_reported, bool):
        raise ValueError("review_reported must be a bool")
    if previous_interval is None:
        interval = min(300.0, max(60.0, expected * 0.5))
    else:
        previous = _positive_finite("previous_interval", previous_interval)
        interval = min(300.0, max(60.0, previous * 1.5))

    review_deadline = expected * 2.0
    hard_deadline = expected * 3.0
    review_due = elapsed >= review_deadline
    hard_deadline_due = elapsed >= hard_deadline

    if hard_deadline_due or (review_due and not review_reported):
        next_poll = 0.0
    else:
        # Do not schedule past the first escalation that has not been emitted.
        deadline = hard_deadline if review_reported else review_deadline
        next_poll = min(interval, deadline - elapsed)

    return {
        "next_poll_seconds": next_poll,
        "review_deadline_seconds": review_deadline,
        "hard_deadline_seconds": hard_deadline,
        "review_due": review_due,
        "hard_deadline_due": hard_deadline_due,
    }


def _completion_validation(
    final_text: Any,
    exit_code: Any,
    packet_id: Any,
    attempt_id: Any,
) -> dict[str, Any]:
    # Process state wins over all model-provided text.
    if exit_code is None:
        return _result("running", False, "exit_code_missing")
    if not isinstance(exit_code, int) or isinstance(exit_code, bool):
        return _result("incomplete", False, "exit_code_invalid")
    if exit_code != 0:
        return _result("failed", False, "nonzero_exit")

    if not _identifier(packet_id) or not _identifier(attempt_id):
        return _result("incomplete", False, "identifier_invalid")
    if not isinstance(final_text, str):
        return _result("incomplete", False, "final_text_invalid")

    lines = final_text.splitlines()
    while lines and not lines[-1].strip():
        lines.pop()
    if not lines or lines[-1] != completion_marker(packet_id, attempt_id):
        return _result("incomplete", False, "marker_missing_or_mismatched")

    response_text = "\n".join(lines[:-1]).strip()
    try:
        response = json.loads(
            response_text,
            object_pairs_hook=_unique_object,
            parse_constant=_reject_nonstandard_constant,
        )
    except (TypeError, ValueError, json.JSONDecodeError):
        return _result("incomplete", False, "response_json_malformed")

    schema_error = _schema_error(response, packet_id, attempt_id)
    if schema_error is not None:
        return _result("incomplete", False, schema_error)

    result = response["result"]
    if result == "blocked":
        return _result("blocked", True, "model_reported_blocked")
    if result == "partial":
        return _result("incomplete", True, "model_reported_partial")
    return _result("ready_for_review", True, "artifact_unverified")


def _schema_error(response: Any, packet_id: str, attempt_id: str) -> str | None:
    if not isinstance(response, dict) or not _SCHEMA_KEYS.issubset(response):
        return "response_schema_invalid"
    if not _identifier(response["packet_id"]) or not _identifier(response["attempt_id"]):
        return "response_identifier_invalid"
    if response["packet_id"] != packet_id or response["attempt_id"] != attempt_id:
        return "response_identifier_mismatched"
    if not isinstance(response["result"], str) or response["result"] not in _RESULTS:
        return "response_result_invalid"
    if not isinstance(response["summary"], str) or not response["summary"].strip():
        return "response_summary_invalid"
    if not isinstance(response["evidence"], list) or not response["evidence"] or not all(
        isinstance(item, str) and item.strip() for item in response["evidence"]
    ):
        return "response_evidence_invalid"
    return None


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    response: dict[str, Any] = {}
    for key, value in pairs:
        if key in response:
            raise ValueError("duplicate JSON key")
        response[key] = value
    return response


def _reject_nonstandard_constant(value: str) -> Any:
    raise ValueError(f"nonstandard JSON constant: {value}")


def _identifier(value: Any) -> bool:
    return isinstance(value, str) and _IDENTIFIER.fullmatch(value) is not None


def _positive_finite(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive finite number")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric <= 0:
        raise ValueError(f"{name} must be a positive finite number")
    return numeric


def _nonnegative_finite(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number at least zero")
    numeric = float(value)
    if not math.isfinite(numeric) or numeric < 0:
        raise ValueError(f"{name} must be a finite number at least zero")
    return numeric


def _result(status: str, protocol_valid: bool, reason: str) -> dict[str, Any]:
    return {
        "status": status,
        "protocol_valid": protocol_valid,
        "reason": reason,
    }


def _completion_main(argv: list[str]) -> int:
    """Validate a final-response file; never dispatches work or merges."""
    parser = argparse.ArgumentParser(description="Validate an Interchange final response")
    parser.add_argument("final_response_file", type=Path)
    parser.add_argument("--exit-code", required=True, type=int)
    parser.add_argument("--packet-id", required=True)
    parser.add_argument("--attempt-id", required=True)
    args = parser.parse_args(argv)

    try:
        final_text = args.final_response_file.read_text(encoding="utf-8")
    except OSError:
        validation = _result("incomplete", False, "final_response_unreadable")
    else:
        validation = _completion_validation(
            final_text,
            args.exit_code,
            args.packet_id,
            args.attempt_id,
        )
    print(json.dumps(validation, sort_keys=True))
    return 0


def _pr_base_main(argv: list[str]) -> int:
    """Run the adapter PR-base preflight and emit one JSON decision."""
    parser = argparse.ArgumentParser(
        prog="protocol.py pr-base",
        description="Validate an Interchange packet before PR creation",
    )
    parser.add_argument("--packet-file", required=True, type=Path)
    args = parser.parse_args(argv)

    try:
        packet = json.loads(args.packet_file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        decision = {
            "allowed": False,
            "code": "packet_invalid",
            "reason": "packet file must contain valid UTF-8 JSON",
        }
        print(json.dumps(decision, sort_keys=True))
        return 1

    decision = validate_pr_base(packet)
    print(json.dumps(asdict(decision), sort_keys=True))
    return 0 if decision.allowed else 1


def main(argv: list[str] | None = None) -> int:
    """Dispatch the existing protocol validator or the PR-base preflight."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments and arguments[0] == "pr-base":
        return _pr_base_main(arguments[1:])
    return _completion_main(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
