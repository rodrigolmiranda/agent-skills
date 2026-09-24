# Execution and acceptance checkpoints

Delivery-orchestrator owns these decisions; Interchange supplies transport evidence. Apply existing authorization and the complete scheduling gate.

## Coordinator turn-exit check

Complete the [scheduling gate and progress checkpoint](scheduling.md) and validate its receipt with `check_schedule.py <receipt> --before-yield` before yielding; checking a sample of tasks is insufficient.

Keep progressing through the approved dependency graph; an owner reply is not needed merely to start the next ready assignment. Before going idle (including a turn that relinquishes control, not only session termination):

1. Reconcile received results, startup receipts and provider errors. A live PID proves only a process, not model execution; record quota/auth/startup failures as blocked.
2. Reassess ready work and ownership conflicts. Dispatch executable authorized work or continue the coordinator's independent work. Do not stop after describing a plan while such work remains.
3. For every outstanding attempt, record its actual supervisor, deadline, next expected event and verified receiver route. A queued event is not an acknowledged receipt. Diagnose missing startup evidence with one bounded process/provider check; do not poll indefinitely or automatically duplicate a writer.
4. End only with all current work completed/dispatched under verified supervision, or a concrete external/owner blocker. State what wakes the coordinator next. When no callback exists, arrange a supported follow-up mechanism or explicitly surface manual-return mode; never imply autonomous continuation.

Provider exhaustion does not authorize a model substitution. Preserve the packet and worktree, stop the failed owned attempt, and request only the required routing decision. Continue unrelated authorized work. Apply this check in both Codex and Claude; a notification or user clarification does not cancel ongoing work unless it says so.

## Required work at every delivery gate

Treat each missing review, test, UX check, runtime proof or acceptance condition as an assignment to finish, not a status to park. On a worker return or gate result, identify the exact remaining criterion, evidence, responsible executor and real prerequisites; perform or dispatch every ready authorized gate immediately, in parallel where ownership/resources permit. Reuse valid proof and avoid redundant gates. The supervisor handles technical preparation and corrections within authority. An acceptance gap alone is not a blocker.

A review stage requires an assigned reviewer and verified startup. Apply the same rule to a tester or UX reviewer when that gate is required. If unavailable, name the actual capacity/dependency restriction and its recovery owner. Queued review is not running review. If a gate cannot yet run, do all available prerequisite work rather than leave a generic “pending review” or “acceptance gap.” Preserve explicit permission and operational boundaries; document the exact remaining authorization instead of inferring it.

Use board states consistently:
- **Working now:** implementation, correction or coordinator preparation is executing.
- **Review:** an assigned independent review, UX or acceptance check is executing; show its kind and executor.
- **Waiting:** a submitted external operation/event is genuinely pending (for example CI), with evidence, owner and next check/wake. Internal technical decisions are not external waits.
- **Blocked:** a named prerequisite activity, unavailable resource or explicit authority restriction prevents the next step. Link the prerequisite and start any authorized work that can clear it.
- **Next:** executable planned work not yet started; the scheduling gate must dispatch it or record a concrete exclusion.
- **Done:** the defined outcome and required closure are evidenced, not merely the worker's return.

Reconcile the workflow state, current attempt outcome, gate result, blocker, executor and next event together before publishing a return. Clear superseded “pending review” values after a verdict; historical attempts stay historical. Check the resulting card against the evidence so a fallback label cannot replace the real prerequisite. Before yielding, no supervisor-solvable gate may remain idle without a concrete, evidenced resource restriction.

## Bounds that prevent drift

- One writer per overlapping surface, isolated checkout; parallelize only independent outcomes. Shared runtime/tests are resources too. Tightly interacting workers use native collaboration when supported; otherwise route decisions through the Planner with versioned contracts.
- A defect introduced by this PR or preventing its accepted outcome belongs to the slice. An unrelated discovery becomes a bug record; escalate immediate safety risks, but do not quietly repair extra scope. Do not label it pre-existing without evidence.
- Tests prove changed behavior and named risks. Reuse valid head/content-bound evidence; no full CI/browser rerun for a test-proof correction unless repository policy or changed risk requires it. Quarantine/waivers require their actual authority.
- After two correction rounds on the same area, the Planner consolidates the underlying failure and chooses a bounded rescue/split/acceptance clarification; do not keep expanding a review indefinitely. New blockers still need concrete impact, not taste.
- Writer reports worker-complete, never independently accepted. Final status distinguishes code, proof, visual/journey, hosted gates, merge and deployment.

## UX and journey checkpoints

Use [verification guidance](verification.md) to select, not multiply, checks. New visual pattern or complex interaction gets design guidance before its UI work. An integrated journey/meaningful feature cluster gets periodic UX + functional navigation review. A milestone exit gets independent end-to-end acceptance. Reusing a simple established pattern needs no new design ceremony. Capture actual screenshots before/after fixes; a mockup or green test is not visual verification.



## Declared automatic return pipeline

When authorized, declare the post-return pipeline before dispatch. Interchange's runner validates mechanical publication conditions, pushes only the owned branch, creates/updates a draft PR, and starts an independent headless reviewer alongside CI. The independent reviewer decides delivery quality and conformance to the accepted packet. Do not insert a duplicate coordinator quality-review turn between worker return and review startup. The coordinator resolves verdicts/exceptions and performs separately authorized merging.

Read-only jobs need no PR. A known failing required gate goes directly to correction rather than routine quality review; an explicit diagnostic review may still help resolve it. Missing commits/handover, dirty scope or publication failure is an actionable exception, never completion. A script process existing is not reviewer startup proof.

For every unfinished activity retain expected transition, executor, deadline/check and verified receiver. A separately supervised monitor detects returned-without-review, unconsumed verdicts, interrupted workers and lost delivery. The board remains read-only. An overdue alert must identify recovery ownership; no commit count or dashboard refresh substitutes for meaningful progress. See Interchange's execution contract for the runner/monitor configuration.

## Recover uncommitted work

An interrupted worker may leave useful changes; a normal return may deliberately leave publication to its declared pipeline. Preserve the worktree, restricted logs and recovery inventory. Inspect ownership before another writer starts. Prefer worker-authored checkpoint commits; never have the wrapper indiscriminately commit or publish dirty changes. Exclude secrets from portable recovery records. Select checkpoint/deadline thresholds by task class: investigation and tests need not produce commits.
