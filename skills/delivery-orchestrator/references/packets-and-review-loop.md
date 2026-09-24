# Packets, decisions and the review loop

Evidence: the guided-help programme, round 1 (2026-09-24). 12 SDK/consumer PRs came from headless OpenCode
builders, each with an independent risk review. Every large PR returned CHANGES-NEEDED at least once with real
defects: money-path leaks, a schema collision, a broken E2E fixture, an evidence-forging path, and a lost cross-page
recording. They converged after 2–4 rounds.

## Decision authority

Within the authority the owner delegated, the coordinator answers worker questions itself. It escalates to the owner
only for:
- a **product deviation**: user-visible behaviour or scope the owner hasn't decided;
- an irreversible or outward action;
- a policy the owner owns (for example, billing);
- a permission, contract or operational hold that the delegation doesn't cover.

Record each decision and a one-line reason in the job's answers file, and report it afterwards. Don't turn it into a
question for the owner. Owners who delegate a session expect this; a question that isn't a product deviation costs
them a round trip.

## Routing by risk surface

Keep the economical builder for a detailed, accepted contract, even when it touches money, concurrency, idempotency,
tenancy/RLS or cross-repository contracts ([roles](roles.md)). Escalate to a senior profile when:
- a high-consequence design question is still unresolved; or
- the **second CHANGES-NEEDED** arrives on the same risk surface.
Record the escalation and keep the model authority rules.

Evidence (owner decision 2026-09-24, cheap first):
- the economical builder converged in 1–2 review rounds on UI, CSS and inspection slices;
- a charging slice took four rounds on the same model (about 4 h of worker time), each closing the last findings and
  opening new edge cases (in-flight markers, shutdown, multi-replica), but it converged.

## What a packet must carry that a sandboxed worker cannot discover

- **Environment the launcher already sets:** names only, "already set; don't override". Without this, workers invented
  wrapper scripts and pointed tests at the owner's own database.
- **The repository's full gate set:** derive it from the CI workflow and repository instructions (unit, integration,
  E2E, JS suites), not only the local gate script. A worker told "E2E is not part of the gate" shipped a model change
  that broke every E2E fixture.
- **Consumer facts the change depends on:** how the component is mounted (routed page or layout), which routes and
  registrations exist, the consumer's HTTP timeouts. Either state them or stage the consumer's files into the packet.
  A recorder designed on the assumption that its panel survives navigation lost every cross-page recording in the
  real consumer.
- **Context discipline:**
  - write the full build/test log to a file and keep the exit status (`set -o pipefail`, or `cmd > log 2>&1; echo
    $?`), then show only a short tail or grep. A bare `| tail` can hide a failure;
  - read diffs per file;
  - never print a full test log into the conversation;
  - **commit at checkpoints**, not only at the end.
  A worker that most likely ran out of model context got an opaque provider 400 after 48 minutes. It exited with 26
  files uncommitted; they were still on disk, and a continuation attempt reviewed and committed them
  ([transport](../../interchange/references/transport.md) says how to check the diagnosis).
- **Fix packets state the rule, not a pointer.** Write "the browser resource equals the chat turn's resource for the
  same caller; add a test that pins it", not "sm360 uses `portal/{hash}`". The pointer version made the worker adopt
  one host's detail as the SDK default and broke the other hosts.

## The review loop

1. Every PR that touches a risk surface gets an independent, read-only risk review before merge. The review checks the
   delivery against the request, not only the code. Tell the reviewer the decisions already made, so it doesn't reopen
   them.
2. A CHANGES-NEEDED verdict becomes a fix packet listing each finding with the coordinator's decision, then the same
   worker continues on the same branch as new commits. Re-review with **the same reviewer session**: it keeps its probes
   and context, which makes the second pass 5–15 minutes instead of 20+.
3. After each fix round, re-review until SAFE. A fix round can introduce new defects: in this run, three of six re-reviews
   found a regression the fix itself introduced.
4. **Close small last findings inline.** When one or two findings touching one or two files remain, the coordinator makes
   the edit, proves it with a test that fails when the edit is removed, and asks the reviewer to confirm. That's cheaper
   than another ~30-minute worker round. It worked 4 of 4 times here.
5. LOW findings the reviewer marks non-blocking become recorded follow-ups, not silent drops.
6. Don't rebase or otherwise move a worktree while a reviewer is reading it. Rebase just before merge instead.

## Event-driven coordinators

A coordinator woken by harness notifications (Claude Code background tasks and monitors) gets many wakes that carry no
decision: a single CI step passing, a monitor line. Those wakes are not "unchanged checks" for repeated-wait recovery.
Count only coordinator-scheduled or idle reassessments. A material return, verdict, merge or unblock still triggers a
ready-set reassessment even though it isn't counted as an unchanged check.

Update the one evidence-backed receipt at material events, changing only the facts that changed. Before giving up
control with no further immediate action, run a **cheap pre-idle check**: executable coordinator work is done or
recorded, and the next wake is verified. Don't create new evidence documents for it, and don't rewrite the receipt for
routine progress notifications. This applies to both clients: a Codex turn can also yield for hours without its
session ending.
