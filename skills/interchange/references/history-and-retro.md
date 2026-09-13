# Delivery history and weekly retro

Owner-approved refinement, 2026-09-09. Keep concise attempt-level execution records locally; retain weekly aggregate learning centrally. This is the Interchange trial's retention profile, not a migration of existing portfolio evaluation records.

## Usage signals

Use exact session token counters when available. Also capture the weekly quota used before and after a run for the same house, account, pool and reset window. Store capture timestamps, reset identity, source and display precision. Report the difference in percentage points as **observed pool usage during the run**, never as tokens or exact agent consumption. Other work in that pool can contribute; mark concurrent usage as known, absent only when verified, or unknown. Unknown concurrency is not isolation.

If the pool resets, capacity changes or a snapshot is missing, the direct delta is unavailable; preserve the reason. Do not turn a negative delta into zero. Rounded readings may hide small use. No token conversion or exact cost attribution from quota percentages. Failed and retried attempts remain part of delivery cost.

Never sum overlapping before/after deltas from concurrent assignments in the same pool. Weekly summary uses deduplicated pool observations over comparable windows. Keep account/pool quota trends separate from model-specific measured tokens and quality. A before/after delta is an approximate availability signal, not a basis for causal model rankings.

## Capacity tiers

At delivery start, record the available Codex and Claude window snapshots when observable, known concurrent use and the capacity reserved for remaining brain/integration/review work. Terra, Sol and Claude Code are the moderate balanced tier: record material allocation choices and reasons for concentration when an equally suitable other house was available. Missing usage data stays unknown.

Before each Terra/Sol mechanical dispatch, record the positive allowance, exception reason and active Terra/Sol count. Default Terra/Sol concurrency is one and absence of an allowance means zero. Luna xhigh/max, DeepSeek V4.1 Flash and Muse Spark 1.3 require no balancing allowance or concurrency authorization; record their ordinary attempt evidence without turning quota tracking into a dispatch gate.

Record an owner instruction prohibiting Codex delegation or leading as a zero-allocation override. It supersedes an earlier mechanical allowance and remains active for the delivery until the owner changes it. Record separately which Codex brain/review use, if any, remains explicitly requested.

Capture another snapshot after the first Terra/Sol mechanical checkpoint when possible. Compare the observed pool change with the delivery allowance without claiming exact task attribution. If it exceeds plan, threatens the reserve or cannot be reconciled with known concurrent use, record the freeze and send remaining mechanical work to another eligible profile. Retain in-flight checkpoint cost, review batching and repair/re-review use so the weekly retro can distinguish protected brain consumption from avoidable premium mechanical consumption.

## Astra and Fable authorization records

Before every Astra or Fable start, resume, retry or follow-up, store the packet ID,
attempt ID, unique invocation ID, model, effort, role/purpose, timestamp, explicit
owner authorization evidence and the concrete reason `gpt-5.6-sol` high cannot fit.
The authorization is valid for that invocation only. A later call, including a
resume of the same session, requires a new record and owner decision. Fable records
also include the separate included-plan/no-extra-spend preflight result. Never put
credentials or secret provider data in the authorization record.

## Storage

Local execution journal: `~/.local/state/interchange/history/`. One concise record per attempt: source project, repository URL/path and immutable base/head where available; task title/ID and revision; attempt ID; role; house/tool/model/version; requested and observed effort; start/end; result; exact usage if available; quota snapshot references; independent scores; significant note; command or permission failures; the verified correction or unresolved blocker; and evidence links. Use existing canonical GOV-0020 score definitions; workers do not assign their own scores. Unknown values remain explicit rather than inferred.

Local records supply an end-of-run summary: contributions, time, measured tokens and approximate quota changes, retries, quality and comparable history. Collection and generation are requirements for the future runner; no automatic before/after collector is implemented yet.

Until that collector exists, the delivery manager writes or updates the local record
when each attempt becomes `ready_for_review`, `blocked`, `partial`, `failed` or
otherwise terminal. Do this before replacement dispatch, worktree reuse or final
delivery reporting. A failed attempt still counts toward cost, elapsed time and
first-pass quality.

When an attempt exposes a CLI invocation, attachment, working-directory, command
composition or permission failure, record the exact failing condition and safe
diagnostic evidence without credentials. If a bounded correction is verified by
resolved configuration plus a positive allowed-path probe and a negative sibling
or denied-action probe, update the applicable section of
[runtime-adapters.md](runtime-adapters.md) in the same delivery and link that change
from the attempt. If it is not verified, retain it as an unresolved transport
blocker; do not publish a guessed recipe. Repeated worker-quality or packet-design
failures follow the central lesson lifecycle below rather than accumulating as
adapter trivia.

Central retained history: `MarvinaMiranda/07 - Decisions & Learning/Agent Delivery/Retros/RETRO-YYYY-Www.md`. One retro per completed ISO week, in Australia/Perth time. Keep grouped results and lessons, not a second itemized task diary. Existing PRs, test evidence, incident records and previously retained evaluations are not deleted or duplicated.

Once a retro has been successfully persisted and reconciled to its inputs, routine local itemized records may be compacted into the retained aggregates by a future retention mechanism. Do not compact unresolved incidents, outstanding reviews or the only copy of acceptance evidence. No deletion or compaction is implemented or executed by the current scheduled retro.

## Retro contents and comparison

Keep: period, source coverage, completed/failed/reworked counts, comparable group identities and sample counts, assessed-score counts and sums, first-pass accepted/eligible counts, total measured usage and its coverage, elapsed/repair-time totals and counts, deduplicated quota observations with reset/concurrency caveats, material lessons, and proposed changes. Counts and sums support historical averages without retaining every task. Do not average weekly averages without their denominators.

Compare the same model/version, reasoning and task class/complexity against prior comparable weeks. Separate quality, accepted-result time and usage; no combined cost/quality score. Distinguish observed change from evidence of improvement. With fewer than three comparable reviewed attempts, missing measurements or a changed task mix, label conclusions insufficient or non-comparable. Pool quota changes cannot establish which individual model improved.

Use existing central lessons, appending recurrence rather than duplicating them. A retro may save findings and propose changes automatically. Routing, governance, spending or model-profile changes still require owner approval.

## Schedule

Codex heartbeat `interchange-weekly-feedback`, displayed as **Interchange weekly retro**, runs Mondays at 09:00 Australia/Perth. It reads available local/canonical evidence, updates one idempotent weekly aggregate, and notifies on meaningful findings or decisions. It stays quiet when there is no new evidence; it never invents a retrospective quota baseline. This scheduled review does not provide live worker monitoring or continuous quota capture.
