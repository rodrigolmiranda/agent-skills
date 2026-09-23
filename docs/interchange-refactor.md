# Interchange — refactor proposal

This proposal makes the current coordinating chat the Planner. Builder executes the majority of settled work; Senior Builder and Architecture/Security are owner-approved exceptions. PR review is independent. UX design/review and functional journey verification are scheduled at meaningful boundaries rather than every small step.

## Why change

The old entrypoint mandates live model supervision, separates manager and judgment roles, and carries dated house/model reservations. Manual transport made the owner copy packets and returns between tools. Repeated correction gates accumulated while unrelated discoveries risked expanding slices. The refactored workflow makes one accountable plan, one concrete deliverable per assignment, finite correction packets, and explicit backlog triage.

This is a refactor of the existing test-stage Interchange skill, not a second product version.

Browse the [workflow diagrams](../skills/interchange/references/diagrams.md) for intake, planning, role selection, questions, callbacks, verification, closure and parallel work.

## Included

- Portable entrypoint and workflow, role/verification/transport guides.
- Editable example profile; specific provider IDs are dated preferences, not availability promises.
- Plan, assignment, questions, handover, review and GitHub upsert-manifest templates.
- [Observability contract](../skills/interchange/references/observability.md), consistent status report and portable continuation index; explicit agent/provenance attribution and dispatch evaluations. These are Planner-maintained records, not an implemented dashboard or automatic GitHub synchronizer.
- Correlated local outbox with artifact hashes, duplicate protection and separate queue/receipt state.
- One-process non-LLM supervisor with deadline/output bounds and exclusive attempt receipt. It does not parse provider exit0 as success, install a resident service, or guarantee escaped-child termination.
- Compatibility for old protocol/policy files and already-dispatched jobs. No active installation or existing packet was changed.

## User-specific choices still to confirm

The proposal preserves the existing Astra-low Codex PR-review preference until changed. It interprets the architecture/security matrix as Astra high for a Codex head and Opus 5.5 xhigh for a Claude head; that rare role remains owner-approved. The Claude routine PR-review default is a proposed Opus medium. These are profile choices, not public workflow requirements.

## Transport experiment (2026-09-23)

| Path | Observed result | Remaining proof |
|---|---|---|
| Claude Code 2.1.280 / claude-opus-5-5 low → literal callback → Codex 0.154.0 queue | Callback command executed; exit0, queue ID returned; init reports requested model | Exact callback received in the coordinator task after queuing; app-closed/reboot wake not tested |
| OpenCode 1.18.32 / opencode-go/deepseek-v4.1-flash high → direct tool callback | Two attempts emitted tool-call text without executing; not completion | Direct path unsupported in this experiment |
| OpenCode same model → validated final text → non-LLM wrapper → Codex queue | Fresh expected final captured; exported session reports provider/model and finish=stop; queue exit0 | Exact callback received in the coordinator task after queuing; app-closed/reboot wake not tested |
| External worker → idle Claude coordinator | Not tested | Use native Claude collaboration/manual inbox until a supported route is proven |

No product repo/runtime/credentials were changed by these probes. Both exact callback codes subsequently arrived as messages in the coordinating task. A separate 30-second delayed callback then started a new coordinator turn after the prior turn ended, with no intervening user follow-up: idle wake passed for the live Codex session. This proves end-to-end delivery for this live desktop session; it does not establish app-closed/reboot recovery or a Claude-head receiver. Queue acceptance and actual receipt remain separate states. Local raw records are held outside the public skill package; only sanitized outcomes belong here.

## Governance alignment

The existing portfolio method already supports new products/features, maintenance, known/unknown bugs and incidents. Proposed additions are explicit continuation/WIP reconciliation, per-slice versus periodic/milestone check selection, automatic proceed after an unblocked receipt, unrelated-bug prioritization, and tested event-based continuation. The skill contains the useful generic workflow directly; it has no dependency on a private organization repository. Central adoption and installed-skill promotion remain separate owner decisions.

## Verification

Python suite: 69 tests, including outbox and process-runner regressions. Skill frontmatter validator passes. Independent review evaluated BAU, WIP parallel writers, uncertain/duplicate callback delivery and proportional UX/journey scenarios. Live provider probes validate request/result/queue and actual coordinator receipt for both providers, within the limits above.

Reference consulted: https://github.com/rafaelquintanilha/skills/blob/master/skills/orchestrate/SKILL.md — independent outcome delegation, ownership, net-gain test and primary integration. The portable text here is an original synthesis of the user's workflow and those general principles, not a copied skill.
