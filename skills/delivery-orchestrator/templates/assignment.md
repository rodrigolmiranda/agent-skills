# Assignment <job ID> — <observable outcome>

Revision: <n> · Kind: <coding | inspection | research | other>
Project: <stable ID> · Coordinator: <agent ID / ownership generation> · Writer: <agent ID/profile> · Issued: <date/time and zone>
Omit inapplicable sections; do not leave blank ceremony.

## Outcome and startup

- Required result: <observable outcome>
- Startup state: <proceed | startup-held>; held only when explicitly stated here
- Startup receipt: record this packet and sources read, baseline, understood scope, and open questions in the handover. If no unresolved question and not startup-held, notify the coordinator that all is clear and work is starting (actual local timestamp, UTC offset and timezone), then proceed immediately; do not wait for acknowledgement.
- Unresolved questions / holds: <IDs and exact dependent actions, or none>
- Bugs outside acceptance: capture evidence and propose a backlog item; never expand this assignment automatically.

## Read and apply

Read in order before dependent work. Use task-supplied links or paths; include the relevant contract text below so the assignment survives context loss.

1. <repository instructions and governing decision, revision>
2. <product, milestone, contract, and implementation baseline>
3. <issue, PR, accepted clarification, and validation instructions>

- Clarified behavior/contracts: <full applicable clauses, field/error/state semantics, allowed variance>
- UX/journey and conventions: <actor, trigger, states, accessibility/content/design conventions>
- Clarification records incorporated: <question IDs, answer, packet revision>

## Acceptance and workspace

| Acceptance ID | Expected result | Required proof | Owner |
|---|---|---|---|
| <A1> | <observable, testable result> | <command, artifact, screenshot, or runtime evidence> | <role> |

- Repository/ref/base and drift rule: <URL/path, commit/ref, how to handle movement>
- Assigned worktree/branch and resume instructions: <location, preserve/reuse steps>
- Owned paths; read-only dependencies; shared/generated paths: <explicit map>
- Resources/credentials/data allowed: <named resources and limits; never include secrets>
- Environment already set by the launcher: <variable names only; "don't override">
- Consumer facts this change depends on: <how the component is mounted, routes, registrations, timeouts; or staged files>

## Dependency and collision handoff

- Task dependencies: <blocker task IDs, dependent IDs, gate type, current linked evidence, and exact unblock condition>
- Held packet and notification: <resumable packet for each held dependent; durable notice to the blocker task's agent; dependent IDs carried into the blocker's reviewer handover>
- Before editing a newly discovered file or shared surface, compare the active write leases. If another task owns it or ownership is unknown, stop work on that surface, record the exact path/contract/resource and blocking task ID, and return the held packet and unblock condition. Continue only non-overlapping assigned work; do not wait by sleeping or polling.
- On a verified blocker completion, reassess each named dependent once. A reviewer-gated task resumes only after an independent current exact-head `APPROVED` verdict and a fresh safe ownership/base check. A task needing merged or accepted code waits for the integration event. A timeout or PID alone never releases a lease.
- UX/E2E or milestone validation pause: <affected task IDs and concrete surfaces only; unrelated ready work remains schedulable>

## Validation and delivery decisions

- Required checks and review/UX/journey checkpoints: <selected proportionately; the full repository gate set derived from CI and repository instructions, not only a local script>
- Working rules: keep full build/test logs and exit status, and show only a tail; commit at checkpoints; decide small implementation questions and record them; stop and ask for a product-behaviour change, a permission, contract or operational hold, or a missing contract
- Stop/escalation conditions and allowed variance: <explicit boundaries>
- Expected artifact and PR base/readiness/merge authority: <exact contract>
- Execution: bind this semantic revision to Interchange's execution envelope; do not duplicate it there.
