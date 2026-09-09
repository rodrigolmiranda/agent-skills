"""Fail-closed PR base validation for Interchange adapters.

This module performs only local packet validation.  It does not create, query,
approve, merge, or publish a pull request.  Every adapter should call
``require_pr_base`` before invoking its provider's PR-creation command.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping


_COMMIT_SHA = re.compile(r"[0-9a-fA-F]{40}\Z")
_ORDINARY = "ordinary"
_HOTFIX = "hotfix"
_RELEASE = "release_promotion"
_TEST = "test"
_MAIN = "main"


@dataclass(frozen=True)
class PullRequestBaseDecision:
    """The deterministic result an adapter can log before PR creation."""

    allowed: bool
    code: str
    reason: str


class PullRequestBaseError(ValueError):
    """Raised when a packet cannot safely authorize its requested PR base."""

    def __init__(self, decision: PullRequestBaseDecision) -> None:
        super().__init__(f"{decision.code}: {decision.reason}")
        self.decision = decision


def validate_pr_base(packet: Mapping[str, Any]) -> PullRequestBaseDecision:
    """Validate a packet's PR target before an adapter creates a PR.

    Routine operations must target ``test``.  ``main`` is accepted only for a
    packet explicitly classified as ``hotfix`` or ``release_promotion`` and
    carrying the human-control declaration plus full base/head commit
    evidence.  Unknown operation classes and malformed packets are rejected.
    """

    if not isinstance(packet, Mapping):
        return _deny("packet_invalid", "PR packet must be a mapping")

    operation_class = packet.get("operation_class")
    base_ref = packet.get("base_ref")
    head_ref = packet.get("head_ref")
    if not all(
        isinstance(value, str) and value
        for value in (operation_class, base_ref, head_ref)
    ):
        return _deny(
            "packet_fields_missing",
            "operation_class, base_ref, and head_ref are required",
        )

    if operation_class == _ORDINARY:
        if base_ref == _TEST:
            return _allow("ordinary_test", "ordinary delivery targets test")
        return _deny(
            "ordinary_base_denied",
            "ordinary feature/fix/chore/docs delivery must target test",
        )

    if operation_class not in (_HOTFIX, _RELEASE):
        return _deny(
            "operation_class_denied",
            "only ordinary, hotfix, and release_promotion are recognized",
        )

    if base_ref != _MAIN:
        return _deny(
            "exception_base_denied",
            "human-controlled hotfix/release exceptions must target main",
        )

    if operation_class == _HOTFIX and not head_ref.startswith("hotfix/"):
        return _deny(
            "hotfix_head_denied",
            "a hotfix exception requires a head ref under hotfix/",
        )

    if packet.get("human_controlled") is not True:
        return _deny(
            "human_control_required",
            "main exceptions require human_controlled=true",
        )
    if packet.get("human_only_merge") is not True:
        return _deny(
            "human_merge_required",
            "main exceptions require human_only_merge=true",
        )

    base_evidence = packet.get("base_evidence")
    head_evidence = packet.get("head_evidence")
    if not _exact_evidence(base_evidence, base_ref) or not _exact_evidence(
        head_evidence, head_ref
    ):
        return _deny(
            "exact_head_evidence_required",
            "main exceptions require exact base and head ref/SHA evidence",
        )

    return _allow(
        "human_main_exception",
        "explicit human-controlled main exception is documented",
    )


def require_pr_base(packet: Mapping[str, Any]) -> PullRequestBaseDecision:
    """Return an allowed decision or raise before PR creation."""

    decision = validate_pr_base(packet)
    if not decision.allowed:
        raise PullRequestBaseError(decision)
    return decision


def _exact_evidence(value: Any, expected_ref: str) -> bool:
    if not isinstance(value, Mapping):
        return False
    return (
        value.get("ref") == expected_ref
        and isinstance(value.get("sha"), str)
        and _COMMIT_SHA.fullmatch(value["sha"]) is not None
    )


def _allow(code: str, reason: str) -> PullRequestBaseDecision:
    return PullRequestBaseDecision(True, code, reason)


def _deny(code: str, reason: str) -> PullRequestBaseDecision:
    return PullRequestBaseDecision(False, code, reason)
