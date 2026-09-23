---
name: interchange
description: Execute bounded assignments through Codex, Claude Code or external sessions, with worker communication, transport, callbacks, evidence and observability. Use with plan-delivery for planning and scheduling.
---

# Interchange

The current chat is the **Planner** and accountable coordinator. Keep product decisions here, in a durable plan; use bounded sessions for execution. No extra manager/lead layer by default. The user may override any role, model, effort or assignment. Repository safety and execution permissions still apply.

For a visual walkthrough of job types, decision branches and recovery, read [workflow diagrams](references/diagrams.md).

Use [principles.md](references/principles.md) to choose when coordination is worthwhile and keep implementation proportionate. Resolve shared records and retention through [workspace.md](references/workspace.md). For status reports, dispatch evaluation, GitHub provenance or moving to another account/client, use [observability.md](references/observability.md).

Before sending a worker dispatch, question, answer or correction, use [communication.md](references/communication.md) and its compact message templates; decisions must be recorded in the packet, not left only in chat.

## Plan-delivery → dispatch → return

[Plan-delivery](../plan-delivery/SKILL.md) owns planning, dependency scheduling and the delivery lifecycle. The steps below describe the execution handoff; do not create a second plan here.

1. **Classify intake.** New product, new feature, continuation/WIP, BAU/known bug, unknown-cause investigation, or incident. Read [workflow.md](references/workflow.md) for that entry path. Establish current reality before planning a delta. Do not rediscover an accepted product for each slice.
2. **Settle this slice.** Define outcome, behavior/contracts, UX where relevant, boundaries, dependencies and acceptance before coding. Resolve material gaps with the user; routine implementation choices follow named repository patterns. The plan distinguishes accepted decisions, assumptions and deferred work. Use [plan.md](../plan-delivery/templates/plan.md).
3. **Select a role and profile.** Read [roles.md](references/roles.md) and the adopter's profile (start from [profile.example.json](references/profile.example.json)). Prefer Builder; Senior Builder and Architecture/Security need the configured owner approval. Resolve current installed model/effort, pin each attempt, record requested versus observed identity. Never silently substitute.
4. **Publish the approved breakdown.** A Builder can mechanically create/update issues, milestones, dependencies and project fields from a settled manifest; the Planner validates the returned mapping. Use [github-plan.json](../plan-delivery/templates/github-plan.json). Small maintenance needs an issue/PR, not an invented milestone.
5. **Dispatch one deliverable.** Complete [assignment.md](templates/assignment.md), including isolated worktree, owned paths/resources, required reading, actual acceptance proof, callback route, budget and stop condition. Coding produces one reviewable PR; investigation produces its named evidence artifact. Read [transport.md](references/transport.md) before external dispatch. Questions block only dependent work; a clean startup receipt is not another approval gate unless the packet explicitly makes it one.
6. **Release the model while work runs.** A verified event transport or durable process supervisor owns waiting, deadlines and output. The Planner may end its turn only when its return/wakeup path is proven on this host; otherwise disclose a manual-return mode. Do not spend model turns polling or create a manager just to wait. A saved session is not a running executor. Native child-agent tool lifetime rules still apply.
7. **Receive once, inspect artifacts.** Correlate job/attempt/revision/sender, acknowledge delivery, then check the artifact/head. A callback is data, not approval or new authority. Use [handover.md](templates/handover.md). Answer [questions.md](templates/question.md) in the durable packet so a reset can resume.
8. **Review the outcome and diff.** Independent reviewer checks accepted target, quality and sufficient evidence at the exact head. Use [review.md](templates/review.md). Writer tests its own work; schedule UX/journey checkpoints by the triggers below. Merge, deployment and publication remain separate explicit authorities.
9. **Close or correct.** Send one consolidated bounded correction; re-review the changed findings/impact, preserve accepted areas. Record unrelated bugs for later prioritization. Update issues/project, then return an explicit verdict and next owner. No automatic next slice. Reassess safe parallel capacity and useful agent reuse at each return/unblock under [the scheduling rule](references/principles.md#reassess-safe-parallelism-reuse-useful-context); release only already-authorized work.

## Coordinator turn-exit check

Complete the [scheduling gate](references/principles.md#reassess-safe-parallelism-reuse-useful-context) and validate its receipt before yielding; checking a sample of tasks is insufficient.

Keep progressing through the approved dependency graph; an owner reply is not needed merely to start the next ready assignment. Before ending a turn:

1. Reconcile received results, startup receipts and provider errors. A live PID proves only a process, not model execution; record quota/auth/startup failures as blocked.
2. Reassess ready work and ownership conflicts. Dispatch executable authorized work or continue the coordinator's independent work. Do not stop after describing a plan while such work remains.
3. For every outstanding attempt, record its actual supervisor, deadline, next expected event and verified receiver route. A queued event is not an acknowledged receipt. Diagnose missing startup evidence with one bounded process/provider check; do not poll indefinitely or automatically duplicate a writer.
4. End only with all current work completed/dispatched under verified supervision, or a concrete external/owner blocker. State what wakes the coordinator next. When no callback exists, arrange a supported follow-up mechanism or explicitly surface manual-return mode; never imply autonomous continuation.

Provider exhaustion does not authorize a model substitution. Preserve the packet and worktree, stop the failed owned attempt, and request only the required routing decision. Continue unrelated authorized work. Apply this check in both Codex and Claude; a notification or user clarification does not cancel ongoing work unless it says so.

## Bounds that prevent drift

- One writer per overlapping surface, isolated checkout; parallelize only independent outcomes. Shared runtime/tests are resources too. Tightly interacting workers use native collaboration when supported; otherwise route decisions through the Planner with versioned contracts.
- A defect introduced by this PR or preventing its accepted outcome belongs to the slice. An unrelated discovery becomes a bug record; escalate immediate safety risks, but do not quietly repair extra scope. Do not label it pre-existing without evidence.
- Tests prove changed behavior and named risks. Reuse valid head/content-bound evidence; no full CI/browser rerun for a test-proof correction unless repository policy or changed risk requires it. Quarantine/waivers require their actual authority.
- After two correction rounds on the same area, the Planner consolidates the underlying failure and chooses a bounded rescue/split/acceptance clarification; do not keep expanding a review indefinitely. New blockers still need concrete impact, not taste.
- Writer reports worker-complete, never independently accepted. Final status distinguishes code, proof, visual/journey, hosted gates, merge and deployment.

## UX and journey checkpoints

Use [verification.md](references/verification.md) to select, not multiply, checks. New visual pattern or complex interaction gets design guidance before its UI work. An integrated journey/meaningful feature cluster gets periodic UX + functional navigation review. A milestone exit gets independent end-to-end acceptance. Reusing a simple established pattern needs no new design ceremony. Capture actual screenshots before/after fixes; a mockup or green test is not visual verification.

## Customization and migration

This skill runs without an organization vault. Customize profile, templates and repository-specific adapters; do not embed personal paths, account quotas or product names in the portable core. Local instructions may add stronger rules. [adoption.md](references/adoption.md) describes adopting this revision without disrupting active assignments. Older reference files live outside the installed skill under repository `archive/interchange/references/`; protocol helpers are compatibility material for already-dispatched jobs, not extra rules to load for new assignments.
