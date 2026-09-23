---
name: interchange
description: Execute bounded assignments through Codex, Claude Code or external sessions, with worker communication, transport, callbacks, evidence and observability. Use with delivery-orchestrator for planning and scheduling.
---

# Interchange

The current coordinator supplies an accepted assignment from delivery-orchestrator. Interchange executes that assignment and returns correlated evidence. The user may override any role, model, effort or assignment. Repository safety and execution permissions still apply.

For a visual walkthrough of job types, decision branches and recovery, read [workflow diagrams](references/diagrams.md).

Use [principles.md](references/principles.md) to choose when coordination is worthwhile and keep implementation proportionate. Resolve shared records and retention through [workspace.md](references/workspace.md). For status reports, dispatch evaluation, GitHub provenance or moving to another account/client, use [observability.md](references/observability.md).

Before sending a worker dispatch, question, answer or correction, use [communication.md](references/communication.md) and its compact message templates; decisions must be recorded in the packet, not left only in chat.

For capability inventory, technical exchange agreements, event logging, board freshness and communication recovery, use [execution operations](references/execution-operations.md). Interchange maintains execution facts; the orchestrator owns plan, priority, evaluation and acceptance.

## Accepted assignment → execution → return

[Delivery orchestrator](../delivery-orchestrator/SKILL.md) owns scope, roles, breakdown, scheduling, review selection and disposition. Receive its accepted packet and validated scheduling decision; do not create a second plan here.

1. Resolve the selected authorized profile through [roles.md](references/roles.md) and the adopter profile. Record requested versus observed identity; unsupported routes fail explicitly, never silently substitute.
2. Prepare the technical envelope using [assignment.md](templates/assignment.md): correlate job, attempt, packet revision, sender, worktree, callback route, budget and stop condition. Preserve the packet's semantic scope and authority. Read [transport.md](references/transport.md) before external dispatch.
3. Verify actual startup, not just a PID or queued prompt. Record the supervisor, deadline and return route. Provider failure returns to the coordinator for scheduling/routing disposition; retain the existing worktree and artifacts.
4. Correlate the return with the registered attempt and artifact digest, acknowledge receipt once, and deliver the evidence to the coordinator. An exit or callback is neither acceptance nor authorization. Durable [questions](templates/question.md) and [handovers](templates/handover.md) survive session changes.
5. Before releasing execution, supply actual process/receiver state to the orchestrator's [turn-exit checkpoint](../delivery-orchestrator/references/execution-checkpoints.md). A queued notification is not acknowledged receipt. Never claim automatic continuation without a verified supported wake route.

Review selection, test allocation, correction ownership and subsequent dispatch belong to delivery-orchestrator. This skill may carry a review or correction packet but does not decide the outcome.

## Customization and migration

This skill runs without an organization vault. Customize profile, templates and repository-specific adapters; do not embed personal paths, account quotas or product names in the portable core. Local instructions may add stronger rules. [adoption.md](references/adoption.md) describes adopting this revision without disrupting active assignments. Older reference files live outside the installed skill under repository `archive/interchange/references/`; protocol helpers are compatibility material for already-dispatched jobs, not extra rules to load for new assignments.
