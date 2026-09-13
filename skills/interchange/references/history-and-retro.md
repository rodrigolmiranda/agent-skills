# Delivery history and weekly retro

Owner-approved refinement, 2026-09-09. Keep concise attempt-level execution records locally; retain weekly aggregate learning centrally. This is the Interchange trial's retention profile, not a migration of existing portfolio evaluation records.

## Usage signals

Use exact session token counters when available. Also capture the weekly quota used before and after a run for the same house, account, pool and reset window. Store capture timestamps, reset identity, source and display precision. Report the difference in percentage points as **observed pool usage during the run**, never as tokens or exact agent consumption. Other work in that pool can contribute; mark concurrent usage as known, absent only when verified, or unknown. Unknown concurrency is not isolation.

If the pool resets, capacity changes or a snapshot is missing, the direct delta is unavailable; preserve the reason. Do not turn a negative delta into zero. Rounded readings may hide small use. No token conversion or exact cost attribution from quota percentages. Failed and retried attempts remain part of delivery cost.

Never sum overlapping before/after deltas from concurrent assignments in the same pool. Weekly summary uses deduplicated pool observations over comparable windows. Keep account/pool quota trends separate from model-specific measured tokens and quality. A before/after delta is an approximate availability signal, not a basis for causal model rankings.

## Codex capacity conservation

At delivery start, record the available Codex window snapshot, known concurrent use, the capacity reserved for remaining brain/integration/review work, and any positive mechanical allowance. Missing usage data stays unknown; it does not create permission to spend an undeclared allowance. Before each Codex mechanical dispatch, record the exception reason and current active Codex mechanical count. Default concurrency is one and absence of an allowance means zero.

Record an owner instruction prohibiting Codex delegation or leading as a zero-allocation override. It supersedes an earlier mechanical allowance and remains active for the delivery until the owner changes it. Record separately which Codex brain/review use, if any, remains explicitly requested.

Capture another snapshot after the first Codex mechanical checkpoint when possible. Compare the observed pool change with the delivery allowance without claiming exact task attribution. If it exceeds plan, threatens the reserve or cannot be reconciled with known concurrent use, record the freeze and send remaining mechanical work to another eligible house. Retain in-flight checkpoint cost, review batching and repair/re-review use so the weekly retro can distinguish protected brain consumption from avoidable mechanical consumption.

## Astra and Fable authorization records

Before every Astra or Fable start, resume, retry or follow-up, store the packet ID,
attempt ID, unique invocation ID, model, effort, role/purpose, timestamp, explicit
owner authorization evidence and the concrete reason `gpt-5.6-sol` high cannot fit.
The authorization is valid for that invocation only. A later call, including a
resume of the same session, requires a new record and owner decision. Fable records
also include the separate included-plan/no-extra-spend preflight result. Never put
credentials or secret provider data in the authorization record.

## Storage

Local execution journal: `~/.local/state/interchange/history/`. One concise record per attempt: task title/ID, role, house/model/effort, start/end, result, exact usage if available, quota snapshot references, independent scores, significant note and evidence links. Use existing canonical GOV-0020 score definitions; workers do not assign their own scores.

Local records supply an end-of-run summary: contributions, time, measured tokens and approximate quota changes, retries, quality and comparable history. Collection and generation are requirements for the future runner; no automatic before/after collector is implemented yet.

Central retained history: `MarvinaMiranda/07 - Decisions & Learning/Agent Delivery/Retros/RETRO-YYYY-Www.md`. One retro per completed ISO week, in Australia/Perth time. Keep grouped results and lessons, not a second itemized task diary. Existing PRs, test evidence, incident records and previously retained evaluations are not deleted or duplicated.

Once a retro has been successfully persisted and reconciled to its inputs, routine local itemized records may be compacted into the retained aggregates by a future retention mechanism. Do not compact unresolved incidents, outstanding reviews or the only copy of acceptance evidence. No deletion or compaction is implemented or executed by the current scheduled retro.

## Retro contents and comparison

Keep: period, source coverage, completed/failed/reworked counts, comparable group identities and sample counts, assessed-score counts and sums, first-pass accepted/eligible counts, total measured usage and its coverage, elapsed/repair-time totals and counts, deduplicated quota observations with reset/concurrency caveats, material lessons, and proposed changes. Counts and sums support historical averages without retaining every task. Do not average weekly averages without their denominators.

Compare the same model/version, reasoning and task class/complexity against prior comparable weeks. Separate quality, accepted-result time and usage; no combined cost/quality score. Distinguish observed change from evidence of improvement. With fewer than three comparable reviewed attempts, missing measurements or a changed task mix, label conclusions insufficient or non-comparable. Pool quota changes cannot establish which individual model improved.

Use existing central lessons, appending recurrence rather than duplicating them. A retro may save findings and propose changes automatically. Routing, governance, spending or model-profile changes still require owner approval.

## Schedule

Codex heartbeat `interchange-weekly-feedback`, displayed as **Interchange weekly retro**, runs Mondays at 09:00 Australia/Perth. It reads available local/canonical evidence, updates one idempotent weekly aggregate, and notifies on meaningful findings or decisions. It stays quiet when there is no new evidence; it never invents a retrospective quota baseline. This scheduled review does not provide live worker monitoring or continuous quota capture.
