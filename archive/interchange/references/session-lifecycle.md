> Historical compatibility reference. Not active instructions. New work uses [Interchange](../../../skills/interchange/SKILL.md).

# Session reuse and cleanup

Use delivery boundaries from the adopted REG-03: Band A foundation is layer-shaped; Band B business implementation is vertical. A milestone groups slices; a task is an artifact-to-proof checkbox, not automatically a separate agent session.

## Default lifetime

| Role | Keep the session for | Reassess or retire at |
|---|---|---|
| Worker | One coherent assignment, its related subtasks and review corrections | Assignment accepted and handback persisted |
| Reviewer | One independent review and verification of its corrections | Review closed; new unrelated slice gets a fresh review session |
| Workstream lead | Related slices sharing an outcome, contracts and dependencies | Milestone/layer boundary, completed workstream or material scope change |
| Delivery manager | Outcome coordination across workstreams | Milestone checkpoint and major phase transition; renew when prior transcript is no longer useful |

Do not create a new session for every checkbox when the same code and decisions remain relevant. Do not reuse one merely because it is open or belongs to the same repository. Every reuse decision should name the context being reused in one short sentence, for example: 'Same slice; fixing reviewer finding against current implementation.' No meaningful reason means a fresh session.

## Reuse decision

Reuse only when the previous context materially helps the next assignment, the role and permission scope remain compatible, and the session is healthy. Verify current code/contract revisions; prior remembered facts are not authoritative. Recheck requested/effective model and reasoning if settings change.

Create a fresh session for an unrelated outcome, unrelated code surface, switch from writer to independent reviewer, contaminated/stale assumptions, repeated context mistakes or failed recovery that calls for an independent approach. Do not use the same conversation to independently approve its own implementation. A new model/house receives a concise verified checkpoint; it does not inherit the entire old transcript by default.

Long context alone is not a universal token threshold: provider limits differ. Repetition, contradictory assumptions and time spent reconstructing irrelevant history are evidence to checkpoint and replace. Native compaction can preserve useful continuity, but is not proof that stale assumptions have been removed.

## Delivery boundaries

**Band A:** workers finish bounded baseline assignments inside a layer milestone. At each layer milestone's accepted handover, retire finished workers and pass contracts, commands, tests and remaining dependencies forward. Keep a lead only when the next work shares meaningful decisions and ownership. Layers do not require one giant session each.

**Band B:** group related tasks into a coherent slice assignment where ownership permits. Keep the writer through implementation and review corrections. After accepted handback, normally retire that session; the next vertical business slice starts fresh unless a lead records a specific continuity benefit. Leads may coordinate several related slices in the same milestone.

**Band A to Band B:** start fresh business implementation workers with a verified baseline package: architecture/contracts, code map, setup commands, passing evidence, known constraints and dependency state. Review lead/manager context at this transition; retain only useful product decisions and dependencies. Do not carry all baseline debugging history into business implementation.

**Milestone close:** use REG-03 acceptance, including required pilot evidence and reconciled docs, not merge alone. Inventory active sessions/worktrees, close completed assignments, identify explicit carryovers and checkpoint leads/manager. A blocked assignment may be suspended with an owner and resumption condition instead of running idle.

## Close context separately from deleting resources

States: active -> awaiting review -> retired, or active -> suspended when blocked. Retired means excluded from normal routing and no active writer ownership, with the handback and session reference retained. Historical transcripts need not be loaded to remain available. Reopening requires an explicit related assignment and ownership check; do not automatically resume the last session for a repository.

Before retirement, persist result, actual session/model/effort, repo/base/head, changes, checks, reviewer findings, usage observations and unresolved carryovers. Ensure successors can continue from artifacts rather than chat. Completion marker or process exit is not acceptance.

Stopping a worker requires checking its process and child processes, saving recoverable work and confirming termination before another writer takes over. After an abnormal provider exit, also prove that no process command/current working directory references the worktree and no provider background-agent/task registry entry remains active. Parent exit alone never transfers ownership. Record the checks and time before assigning a successor. A retired session's worktree is removable only after all of these are proven:

- No active process, writer, dependent agent or required local runtime uses it.
- No uncommitted/untracked user work or unique unpreserved commits would be lost.
- Required changes and evidence are preserved in durable commits/artifacts; squash merges are verified by their resulting content, not ancestry alone.
- No unresolved review, incident, dependency or carryover needs that workspace.

Use normal guarded removal; never force removal/reset/clean to achieve a tidy inventory. Keep uncertain worktrees and report the exact reason. Session transcript deletion is separate from worktree cleanup and local diary aggregation. Never delete the only copy of evidence or assume a CLI's session-delete command leaves its worktree intact.

## Ownership and implementation status

Lead owns worker retirement and worktree cleanup decisions; manager owns lead turnover and milestone inventory. Weekly retro may flag orphaned/suspended resources and missing owners; it does not delete them automatically. Local housekeeping status is execution state, not a duplicate milestone plan.

These are workflow rules for Interchange. Automatic session retirement, provider-specific deletion and safe worktree garbage collection are not implemented. This document does not perform or authorize a blanket deletion of existing sessions, worktrees or evidence.

Ending the manager turn does not retire or safely suspend its workers. Before any
manager exit, inventory every active handle. Continue bounded waits, transfer each
one to another live supervisor, or stop it and preserve recovery state. On return
after an unexpected exit, reconcile process/session/worktree state before any new
dispatch so a silent worker cannot overlap a replacement writer.
