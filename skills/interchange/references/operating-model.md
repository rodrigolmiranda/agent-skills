# Interchange operating model

Approved by Rodrigo on 2026-09-09. Configured values live in `policy.json`; spreadsheet and diagrams are readable views. This document explains decisions and lifecycle. Shared portfolio rules remain in MarvinaMiranda GOV-0020 and GOV-0016. Repository product meaning stays with its repository. GitHub owns delivery state; runtime files hold execution state and link to it.

## Team and task size

Delivery manager owns outcome, dependencies, lead selection and final accountability. Add leads for independently manageable workstreams, including workstreams spanning several repositories. Do not equate one repository with one lead or one model with one role. Manager spends its context on decisions, exception summaries and integration evidence.

Select lead strength by ambiguity, consequence and coupling. Defined contracts and routine coordination suit Terra xhigh; difficult integration within defined architecture may use Terra max. Moderate design decisions suit Sol medium; high consequence or coupling suits Sol high. Unresolved architecture crossing workstreams suits Astra medium. These are initial routing hypotheses, calibrated through actual reviewed work. Size alone is not a risk measure.

Workers receive the smallest coherent assignment whose result can be verified independently. Prefer local tools for one lookup; batch related exploration so builders reuse findings. Avoid tiny tasks that duplicate startup context. Spread similar eligible work across usage pools when this improves availability or time; same-house assignment is allowed with a reason. Independent review means independently inspected artifacts, not necessarily another vendor.

For development worker selection, apply [routing.md](routing.md) and the configured pools in `policy.json`. Implementation difficulty, ambiguity, consequence and coupling are separate criteria. Grok uses its own CLI only; Claude uses Opus medium/high. The preferred development pools do not replace the smaller Muse/Luna support lane or grant workers lead permissions.

## Workspaces and context

Apply [session-lifecycle.md](session-lifecycle.md) for reuse, milestone checkpoints, baseline-to-business handovers and cleanup. Retain useful context across related tasks; default to fresh sessions for unrelated outcomes. Retiring a session does not itself remove its worktree or evidence.

Lead allocates a worktree per writable assignment per repository. One writer owns its paths, including lockfiles/generated files. Successors reuse that assignment's worktree after verified ownership transfer; no reset to simplify recovery. Read-only helpers need no writable worktree; review a recorded immutable head to avoid moving-target evidence. Parallel interfaces get one contract fixture and an integration owner before consumers start.

Checkpoints preserve objective, accepted decisions, rejected approaches, packet revision, source references, repo/ref/base/head, changed files, tests, missing evidence, ownership, process/session IDs and next action. New house verifies these against disk before writing. Checkpoints transfer useful context; they do not transfer hidden model state.

All agents receive a short universal boundary set plus applicable role/task rules and pinned references. Leads select references; workers can request additional applicable authority. Record source revisions/digests. A cached projection is an index/extract, not a competing authority. Refresh on governing revision or ownership changes. Personal root paths resolve through a local configuration map. If the central working tree is uncommitted, identify it as such and capture file digests; never fabricate a source commit or assume another clone has those changes.

## Incident and escalation

Before ending a turn with work unfinished, apply the adopted GOV-0020 continuation
rule: continue authorized unblocked work, or record a real executor/wait handle,
concrete blocker, or owner-requested pause. A future-tense promise is not a
continuation mechanism. At resumption verify actual process state before assigning
another writer. The current Interchange helper cannot enforce host wakeups.

Single worker -> lead -> delivery manager -> owner. Classify availability/quota separately from capability, scope and contract problems. Resume interrupted work where possible. Switch model/effort only to a named approved profile; switch house for relevant capability, independent diagnosis or available allowance. Missing quota does not relax acceptance.

Create a war room when failures repeat or affect several workstreams. One incident lead owns the record: incident ID, affected packets/repos, current owner, exact evidence, hypotheses, failed attempts, stopped processes, remaining budget/deadline, next action and decision needed. Investigators are bounded and read-only unless reassigned ownership. Do not restart every worker or expand scope as a recovery technique.

Automatic interruption is approved at the hard deadline. Do not launch a competing writer if the old process might still run. Preserve incomplete work and deliver a blocker when cancellation cannot be confirmed. Manager may commission one independent diagnosis after two failed recovery attempts. Owner decides unresolved product scope, additional permission or exceptions outside the approved roster. Teams/Telegram/WhatsApp and unattended operation are deferred; no external notification connector is assumed.

## Merge and access

For explicitly adopted repositories, only lead/delivery manager may merge PRs whose current base is exactly `test`. Require current green checks and independent review on the current head. Normally one approving review is required. The owner permits bypass of that approval requirement only after a passing independent Codex PR review, all other requirements satisfied and a recorded reason/head SHA. Unresolved findings cannot be bypassed. Workers cannot merge or self-approve. New commits invalidate head-bound evidence.

Keep bypassable approval rules separate from non-bypassable checks and restrict bypass to PR flow. GitHub permissions belong to credentials, not model personas. Strong enforcement requires a lead-only merge service/identity unavailable to worker processes; skill prose alone cannot enforce credential separation. No GitHub rules or credentials have been changed by this initial package. `uat`, `main`, releases and separate security/deployment holds stay human-controlled. Adoption does not silently migrate every collaborator's workflow.

## Usage and learning

Apply [history-and-retro.md](history-and-retro.md) for the owner-approved Interchange refinement: local attempt details, approximate before/after quota observations and centrally retained weekly aggregates. This refines storage for this trial while preserving the existing score definitions and retained portfolio records.

No new spending, recharge or automatic paid fallback. Existing OpenCode Go allowance/balance may be used for Muse only. Bind quota observations to house/account/pool and timestamp; unavailable/old readings are unknown, not zero. Never equate a model's list price estimate to subscription debit.

Store provider counters without summing overlapping token categories. Wall time, exit status, model identity and session usage come from execution metadata where available. Reviewer records quality independently using GOV-0020 dimensions; workers report facts. Fewer than three comparable reviewed packets is insufficient ranking evidence. Group by model/version/effort/task class, with house and account context.

Use existing central LSN records. Weekly review proposes rule/routing changes with evidence, impact, affected profiles and rollback; owner approves before promotion. Per-run waiting intervals may adapt within approved bounds. Rodrigo's local Codex review is scheduled Mondays at 09:00 Australia/Perth, automation `interchange-weekly-feedback`. It stays quiet without actionable evidence and proposes changes for approval. This personal automation is not installed when another developer clones the skill. Scheduling and notification delivery are separate from the skill itself.

## Delivery stages

1. This package: approved design, named profiles, command templates, completion validator, document, workbook and decision diagrams.
2. First live runner: scoped dispatch/resume, parsed final events, event delivery, child-process interruption and ownership records. Prove forced failure and recovery; ordinary success is insufficient.
3. Cross-house replacement: durable checkpoint verified by another house, no duplicate writer, preserved acceptance and measured usage.
4. Governance enforcement: lead-only merge identity, exact-head review evidence, isolated bypass rule, repository adoption checks.
5. Optional product: persistent daemon/MCP, notification connectors and a visual interface. Maestri-like orchestration is feasible without depending on Maestri; feature parity is not claimed.
