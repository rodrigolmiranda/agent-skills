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

## Bounds that prevent drift

- One writer per overlapping surface, isolated checkout; parallelize only independent outcomes. Shared runtime/tests are resources too. Tightly interacting workers use native collaboration when supported; otherwise route decisions through the Planner with versioned contracts.
- A defect introduced by this PR or preventing its accepted outcome belongs to the slice. An unrelated discovery becomes a bug record; escalate immediate safety risks, but do not quietly repair extra scope. Do not label it pre-existing without evidence.
- Tests prove changed behavior and named risks. Reuse valid head/content-bound evidence; no full CI/browser rerun for a test-proof correction unless repository policy or changed risk requires it. Quarantine/waivers require their actual authority.
- After two correction rounds on the same area, the Planner consolidates the underlying failure and chooses a bounded rescue/split/acceptance clarification; do not keep expanding a review indefinitely. New blockers still need concrete impact, not taste.
- Writer reports worker-complete, never independently accepted. Final status distinguishes code, proof, visual/journey, hosted gates, merge and deployment.

## UX and journey checkpoints

Use [verification guidance](verification.md) to select, not multiply, checks. New visual pattern or complex interaction gets design guidance before its UI work. An integrated journey/meaningful feature cluster gets periodic UX + functional navigation review. A milestone exit gets independent end-to-end acceptance. Reusing a simple established pattern needs no new design ceremony. Capture actual screenshots before/after fixes; a mockup or green test is not visual verification.

