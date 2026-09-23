# Delivery workflow

## Intake paths

| Entry | First evidence | Plan only the delta | Result |
|---|---|---|---|
| New product | actors, problem, constraints, viability, existing reusable capabilities | end state and first useful vertical outcome; decisions needed for that outcome | roadmap plus executable first slices |
| New feature | current journey/code/contracts and changed need | behavior, UX, dependencies, migration/rollout | one or more independently demonstrable PRs |
| Continuation / WIP | live issues/PRs, branches, dirty files, shipped versus draft behavior, outstanding holds | reconcile accepted scope with remaining work; preserve useful drafts | restartable next-slice queue, not a second project |
| BAU / known bug | expected/actual, reproduction/version, impact | narrow fix or maintenance outcome and appropriate regression | one bounded issue/PR; existing milestone only if meaningful |
| Unknown failure | symptom, affected version, evidence, diagnostic question and budget | investigation first; Planner chooses repair from findings | evidence artifact then a fix packet |
| Incident | impact, owner, permitted containment, recovery point | minimum restoration, verification, follow-up | controlled repair plus separately prioritized root cause |

## Plan and GitHub division

The Planner owns scope, priorities, product trade-offs and the dependency graph. Keep durable plan/decision files rather than relying on chat memory. GitHub is the selected live delivery system; artifacts hold proof, not another manually maintained status board.

Builder receives fully specified issue bodies/labels, stable local IDs, dependencies, project/status and milestone mapping. Upsert by stable marker or an existing returned ID; a retry reconciles, not duplicates. Create objects in dependency order, record resulting IDs/URLs, then wire dependencies. Separate mechanical jobs may own disjoint object IDs, with shared project/schema setup done once first. No worker invents priorities or acceptance. Planner checks a sample plus all dependency/count/state mismatches before releasing coding.

Board views must make completed work discoverable and include cross-repository dependencies intentionally. Show an active queue and a completed/progress view; do not let an open-only filter impersonate the whole project. Use the repository's actual field IDs/statuses; the template's names are examples.

## Assignment lifecycle

Planned → Ready → Running → Question/Blocked or Worker-complete → Independent review → Correction or Accepted → Merge/Delivery gates → Done.

A startup receipt confirms read sources, baseline, ownership, acceptance and questions. Proceed automatically when the approved packet is unambiguous and gates are open. Use a proposal gate only for an explicitly unsettled contract, migration or UX surface. Continue independent safe work while one dependency is blocked; do not fabricate another task.

New writable scope gets a worktree; corrections keep the same worktree/session when coherent. Reuse a session while retained context helps; fresh session after unrelated scope/context pollution, with durable handover. Inspection, plans and GitHub mechanics do not require a source PR unless they change versioned artifacts. Every coding packet has a PR target and definition of completion.

## Scope triage

For a discovery, record expected/actual, affected source/runtime, evidence, impact, proposed owner and whether it blocks a named acceptance criterion. Planner then classifies:
- In-scope regression/acceptance blocker: correct inside the PR.
- Unrelated bug or improvement: create/draft a backlog issue and prioritize the next slices.
- Immediate safety incident: stop affected execution and escalate; do not perform unapproved containment.

An incident is not a license to audit the portfolio. A review correction is not a new feature. If scope grows materially, revise the packet/issue before implementation and budget it explicitly.

## Cost and escalation

Budgets are per outcome, not arbitrarily tiny fragments. Use one integrated review rather than multiple reviewers reading the same diff. Batch questions, summarize evidence, keep raw tool streams on disk. Mechanical supervision consumes no model calls. Record actual elapsed/usage where exposed, unknown otherwise; file size, time or callback count does not measure token usage.

Escalate a Builder when settled requirements still demand difficult cross-boundary engineering, repeated proof failure or unfamiliar high-consequence work. State why, proposed role/model, bounded output and cost/time limit; owner approves Senior/Architecture dispatch. Approval never authorizes new product scope.
