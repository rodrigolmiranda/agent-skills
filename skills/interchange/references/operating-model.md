# Interchange operating model

Initially approved by Rodrigo on 2026-09-09; brain/mechanical routing, Codex capacity conservation and owner-gated exceptional brains revised on 2026-09-13. Configured values live in `policy.json`; spreadsheet and diagrams are readable views. This document explains decisions and lifecycle. Shared portfolio rules remain in MarvinaMiranda GOV-0020 and GOV-0016. Repository product meaning stays with its repository. GitHub owns delivery state; runtime files hold execution state and link to it.

## Team and task size

Delivery manager owns outcome, dependencies, lead selection and final accountability. Coordination does not itself grant judgment authority. Sol high is the normal brain for product, architecture and ideation decisions. Astra medium and Fable 5.1 medium are owner-gated exceptions. Before every invocation in any role, including start, resume, retry and follow-up, the owner must freshly authorize the exact invocation and the record must explain concretely why Sol high cannot fit. Fable also requires its included-plan/no-extra-cost preflight. An Opus 5 high manager remains an approved continuity option when Codex capacity is unavailable, but routes unresolved interpretation to an approved brain. Add leads for independently manageable workstreams, including workstreams spanning several repositories. Do not equate one repository with one lead or one model with one role. Manager spends its context on decisions, exception summaries and integration evidence.

One manager owns a delivery at a time. Before switching managers, checkpoint the
approved outcome, governance revision, decisions, assignments, session/process
IDs, worktrees/branches, evidence, blockers and deadlines. Transfer supervision
explicitly and reconcile active workers before any replacement dispatch. Confirm
the incoming house can load these instructions and start, resume, monitor and
interrupt the intended workers; Codex-native tools are not automatically available
in Claude. An approved Opus manager profile is not proof of working transport.
Unavailable Codex quota also makes the Codex-review approval-bypass route
unavailable until its required evidence can be obtained.

During waits, prefer supported completion events or bounded blocking tool waits.
Use local deterministic status checks and return compact changes to the manager;
model-driven polling incurs another inference turn even when nothing changed.
Worker inference is separate from manager waiting. Record observed usage rather
than estimating token consumption from elapsed waiting time. Existing deadlines
and continuation ownership still apply; waiting does not release the applicable
global or delivery-manager reservation.

The manager remains active until owned workers return terminal handbacks or a live
supervisor accepts their handles. A wait timeout leads to another bounded wait,
not a final response. Read [runtime-adapters.md](runtime-adapters.md) for provider
transport, permission preflight, stream draining, lifecycle classification,
watchdogs and owner concurrency exceptions.

Separate judgment from mechanical coordination before selecting a lead. Sol high resolves product, architecture and consequential tradeoffs by default. Astra medium may resolve unusually large ambiguity across workstreams, and Fable 5.1 medium may explore product ideas, only after a fresh invocation-specific owner authorization with the Sol-high non-fit reason. The authorization is consumed by one invocation and cannot be reused for a resume, retry or follow-up. Terra leads, lower-effort Sol, Opus workers and other execution profiles may coordinate only settled contracts; they return unresolved choices to a brain. Size alone is not a risk measure.

Workers receive the smallest coherent assignment whose result can be verified independently without interpretation. Every mechanical packet supplies settled behavior, objective acceptance, owned paths and an explicit escalation boundary. Use fast, inexpensive workers when their startup, supervision and integration overhead is lower than the expected time or cost saved. Parallelize independent, objectively testable packets after interfaces are fixed; never overlap writable surfaces. Avoid fragments whose dispatch or merge overhead exceeds direct execution. Muse Spark 1.3 is the light mechanical and read/seek lane for repository search, localization, evidence collection, narrow checks and small explicit edits. Independent review means independently inspected artifacts, not necessarily another vendor.

For development worker selection, apply [routing.md](routing.md) and the configured pools in `policy.json`. Implementation difficulty, ambiguity, consequence and coupling are separate criteria. Grok uses its own CLI only; Claude uses Opus medium/high. The preferred development pools do not replace the smaller Muse/Luna support lane or grant workers lead permissions. Mechanical agents may gather verification evidence; independent semantic and risk acceptance belongs to Sol high, with Astra medium reserved for unusually large cross-workstream scope.

## Codex capacity conservation

Preserve Codex for judgment, integration decisions and independent semantic/risk acceptance across the full usage window. External houses are the normal mechanical and parallel execution lane. At delivery start, capture the Codex usage window when available, note known concurrent use and reserve capacity for the remaining brain and review path. A delivery must record a positive Codex mechanical allowance and reason before starting any Codex mechanical worker or mechanical lead; absence means zero.

The normal Codex mechanical concurrency is one. More requires explicit owner authorization, even when write surfaces do not overlap. After the first Codex mechanical checkpoint, capture usage again when available. Stop new Codex mechanical dispatch when observed burn exceeds the allowance, threatens the reserve or cannot be reconciled with known concurrent activity. Do not waste already-spent capacity by abruptly killing useful work: reach the nearest clean tested checkpoint unless the hard deadline or another safety boundary requires interruption, then transfer remaining execution through the normal ownership procedure.

Use Muse and other mechanical workers to gather repository evidence before a brain call. Batch related ambiguities into one decision packet. Run builds, tests and evidence collection outside Codex. Commission one Sol-high semantic/risk review per meaningful integrated chunk rather than per leaf assignment; any remedy changes the head and still requires re-review. The owner may set Codex delegation or leading to zero for a delivery while retaining only explicitly requested brain/review use.

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

No new spending, recharge or automatic paid fallback. Existing OpenCode Go allowance/balance may be used for the approved Muse and DeepSeek Flash profiles. DeepSeek V4 Pro is excluded even when Flash is unavailable. Bind quota observations to house/account/pool and timestamp; unavailable/old readings are unknown, not zero. Never equate a model's list price estimate to subscription debit.

Store provider counters without summing overlapping token categories. Wall time, exit status, model identity and session usage come from execution metadata where available. Reviewer records quality independently using GOV-0020 dimensions; workers report facts. Fewer than three comparable reviewed packets is insufficient ranking evidence. Group by model/version/effort/task class, with house and account context.

Use existing central LSN records. Weekly review proposes rule/routing changes with evidence, impact, affected profiles and rollback; owner approves before promotion. Per-run waiting intervals may adapt within approved bounds. Rodrigo's local Codex review is scheduled Mondays at 09:00 Australia/Perth, automation `interchange-weekly-feedback`. It stays quiet without actionable evidence and proposes changes for approval. This personal automation is not installed when another developer clones the skill. Scheduling and notification delivery are separate from the skill itself.

## Delivery stages

1. This package: approved design, named profiles, command templates, completion validator, document, workbook and decision diagrams.
2. First live runner: scoped dispatch/resume, parsed final events, event delivery, child-process interruption and ownership records. Prove forced failure and recovery; ordinary success is insufficient.
3. Cross-house replacement: durable checkpoint verified by another house, no duplicate writer, preserved acceptance and measured usage.
4. Governance enforcement: lead-only merge identity, exact-head review evidence, isolated bypass rule, repository adoption checks.
5. Optional product: persistent daemon/MCP, notification connectors and a visual interface. Maestri-like orchestration is feasible without depending on Maestri; feature parity is not claimed.
