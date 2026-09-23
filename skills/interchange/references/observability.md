# Observability and continuation

Use this contract when dispatching, reporting status, evaluating a return or transferring coordination. Keep the records small and factual. GitHub owns delivery state; plans own scope/decisions; attempt artifacts own execution evidence. A report is a timestamped view of those sources, never a second editable backlog.

## Identity and records

Use a stable project ID, plan ID, job ID, attempt ID and agent ID. Namespace job IDs by project so concurrent projects cannot collide in a shared relay. Yellow/Blue are display aliases, not identities. Give the Planner an agent ID too. A new session/account gets a new agent ID; a retry or model change gets a new attempt, linked to its predecessor. An agent reused for related work retains its session ID but records each assignment separately.

For each agent/attempt record: role; client/provider; requested model/effort; observed model/effort and evidence or unknown; provider session ID; host alias; non-secret account alias; coordinator ID and ownership generation; packet revision; worktree/base/head; start/return/review times; last observed event/time; deadline; process handle; current owner/next action; previous attempt and evidence links. Account aliases identify execution context without storing account credentials or email addresses. Native sessions may expose no PID, timing or model proof: write unknown rather than reconstructing it from a role name.

Use the existing plan, assignment, handover and review for their fields. [continuation.json](../templates/continuation.json) is a small index pointing to them, the active agent roster and prior coordinator handovers. Retain each issued packet revision, question/answer, result, correction and disposition; an ordered list of linked events is enough. Do not copy full transcripts into packets. Raw transcripts are restricted evidence, not required reading.

The relay already records terminal notification events; runner receipts record process outcomes. Reference those where available. Other events and native attempts are recorded in the handover's interaction history. No new service, metrics database or background model is required. The current helpers do not automatically generate status reports, evaluate work, synchronize GitHub or transfer coordinator routes: the Planner performs those steps from this contract.

Record the worker's reported local start time with UTC offset/timezone and its normalized UTC equivalent, plus the coordinator receipt time separately. Do not use delayed delivery time as the start or infer start from dispatch. Unknown timing stays unknown.

## Comparable status report

On “status report”, use [status-report.md](../templates/status-report.md) with the same six sections, column order and project/job IDs every time. Report the requested project, or all active projects when portfolio-wide. Keep inactive history collapsed to links. Preserve numbered report snapshots and link the previous one; first report says baseline. Changed scope is a scope delta, not apparent progress.

Read the execution receipts and live GitHub state once on request; use already-delivered events for intervening updates. An unchanged report must not launch new work or prompt workers for status. Mark every unrefreshed source with last-verified time; distinguish running, waiting, exited, unknown and accepted. A saved session, silence or old PID does not prove a worker is running. Flag overdue deadlines, unreconciled terminal events, stale observations, ownership conflicts and failed delivery only when supported. Staleness is relative to the declared deadline/checkpoint, not a universal heartbeat interval.

Use fixed columns for current agents and changes since last report. Link previous dispatches, corrections and evaluations in the history column. Show outcome, checks, review, merge and deployment separately. Avoid invented completion percentages or ETAs: use accepted criteria counts only when the denominator is stable and meaningful. State the next event expected, who owns it and whether the user must act. A blocked project must not hide useful activity in another project.

## Evaluation after every dispatch

Every terminal dispatch gets a disposition: accepted, correction required, blocked, canceled or not assessable. Writer supplies facts; an independent reviewer evaluates deliverables. For mechanical/search work the Planner can independently inspect the artifact without another review agent. Reviewer dispatches are evaluated by the Planner against finding accuracy/usefulness; the Planner's own decisions receive owner feedback or independent inspection, never a self-awarded quality score. Blocked/canceled attempts retain timing and cause; unassessed dimensions stay unassessed.

Reuse the portfolio's five dimensions, each 0–3 or not assessed:

| Dimension | Question |
|---|---|
| Correctness | Did it achieve the accepted outcome? |
| Boundary discipline | Did it respect scope, ownership and authority? |
| Evidence reliability | Are claims reproducible and accurately qualified? |
| Maintainability | Is the solution clear, proportionate and conventional? |
| Autonomy | Did it progress and escalate usefully without invented decisions? |

Scale: 0 critical failure/unusable; 1 major repair; 2 minor correction; 3 accepted without correction in that dimension. Attach one short evidence reason to a nontrivial score. Use role-relevant dimensions; maintainability can be not assessed for an investigation. Preserve the first-review assessment and append correction outcomes so repaired work does not erase the original signal.

Speed is measured, not a subjective score: dispatch-to-return, reported process execution, external wait, review/correction elapsed, and dispatch-to-independent-acceptance. Keep queue delay separate when exposed. Unknown intervals stay unknown; overlapping intervals are not added and provider process duration is not model compute time. Record estimate versus actual only if an estimate was declared. Add correction rounds, manual owner interventions and unnecessary reruns where evidenced. Tokens/cost are optional measured fields with source and currency; never infer them from duration or transcript length.

Compare only similar task class/complexity, client/provider/model/effort and environment, showing sample count and wait exclusions. Fewer than three comparable results is insufficient for a ranking. No weighted league table, quota-driven quality target or blanket penalty for legitimate questions. Use recurring findings to improve the packet, tests or routing; do not introduce a rule for every one-off defect.

## Portable coordinator transfer

Store durable records in a project-controlled location, not a temporary directory as their only copy. Use repository-relative paths and immutable GitHub/artifact URLs plus hashes/revisions; private logs/screenshots stay in an authorized artifact store. A local-only file is marked nonportable. Index required evidence explicitly and verify the recipient can access it. Secrets, raw credentials and browser sessions never enter a continuation bundle.

1. Checkpoint the plan, accepted decisions, unanswered questions, attempts, GitHub cursor/time, evidence and resources in the continuation index. Record dirty work and preserve it; do not require committing unrelated changes.
2. Name outgoing and incoming coordinator IDs and increment the ownership generation. The old coordinator stops issuing work. This record is an ownership agreement, not a distributed lock.
3. The incoming coordinator reads the index and relevant authorities; maps repo/artifact roots on its host; checks authentication and permissions; verifies live PR heads, dirty worktrees, processes and open holds. Missing access is a concrete blocker, not permission to recreate work.
4. Reconcile in-flight workers before dispatch: retain an old callback route only if it is still supervised and receipt can be forwarded safely; otherwise drain/stop the attempt or explicitly hand back its work before registering a new attempt to the new receiver. Current relay routes are immutable. Do not pretend an active route can be edited or run a competing writer.
5. Prove the new receiver's callback/wake path, record incoming acknowledgement and next action, then resume only remaining authorized work. If the old coordinator cannot acknowledge, inspect and stop/reconcile its owned execution before taking over; never infer release from silence.

The plan must be sufficient without chat history: accepted contract text or durable links, decision rationale, remaining acceptance, permissions/holds, current ownership and exact next step. Changing account/provider does not transfer credentials or expand authority. Supported transports differ; a Codex wake test proves nothing about a Claude receiver.

## GitHub reconciliation and provenance

Update issues/project at substantive transitions: started, blocked with reason/owner, review, correction, accepted, merged and deployed when applicable. Reconcile live head/checks before publishing. Use existing fields and stable markers to update a summary instead of creating a comment for every tool call. Cross-repository dependencies and completed work remain discoverable. On a failed sync, record pending reconciliation and report drift; never claim GitHub is current. Merge alone closes only acceptance that the issue actually defines.

Add compact provenance to commits and PRs using stable IDs. Preserve the actual Git author/committer and configured signing; these fields are attribution, not cryptographic signatures or evidence of review:

```text
Interchange-Project: <project-id>
Interchange-Job: <job-id>/<attempt-id>
Interchange-Writer: <agent-id>
Interchange-Coordinator: <agent-id>/<ownership-generation>
```

Use the same footer in the PR body with links to packet/handover and an explicit review state. After independent review, record reviewer agent ID, exact reviewed SHA, verdict, time and evidence in the review record/PR. A new head invalidates a blanket current-head review claim until impact is checked. Do not add a reviewer trailer before a review, invent a Co-authored-by email, impersonate an account, rewrite existing commits solely for attribution or mark a cryptographic signature verified from these text fields. Squash merges preserve the compact job attribution when the authorized merger controls the message; the review record retains the reviewed pre-merge SHA.

## Keep the layer small

Start with linked records and on-demand reports. Automate only measured repetitive work: rendering the same report, reconciling a known GitHub mapping, or detecting a missing return. No agent heartbeat chat, speculative dashboards, per-tool scoring, transcript mirroring or per-minute status spam. Record important transitions once and link them everywhere else.
