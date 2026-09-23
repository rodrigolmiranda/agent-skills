# Portfolio operational procedures

Operational procedures for projects adopting GOV-0020. The central register retains principles, authority and evidence constraints; these procedures implement that adopted contract and cannot redefine it. Trial source: agent-skills PR #9; no portfolio-wide adoption implied.

## Executable packet: required content

Use the [semantic assignment](../../skills/delivery-orchestrator/templates/assignment.md) plus the [execution envelope](../../skills/interchange/templates/assignment.md). Portfolio additions are exact governing revision, canonical public contract fixture, calibration lessons and the mandatory handback below. They supplement the semantic layer; do not maintain a second dispatch-field list.

Keep general rules in this authority. Packets carry task-specific instructions and
link here instead of duplicating governance. A public contract used by parallel
writers has one authoritative fixture; both consumers test against it. Semantic
agreement matters in addition to JSON field names. Amend the contract with a new
packet revision and notify every affected session before dependent implementation.

**Base drift:** default to a minimum ancestor plus an owned-path/contract impact
check. Unrelated descendant changes may be recorded and accepted. Stop for rewritten
history, overlapping changes or incompatible dependencies. Use exact equality only
where reproducibility genuinely requires it, naming why. Never restart clean work
solely because the integration branch advanced. The packet states whether work stays
on its captured base or may absorb a reviewed update.

**Worktree discipline:** workers preserve other sessions' changes. Existing packet
worktrees are resumed after inspecting their status, not reset. Returning work means
leaving commits, branch and workspace accessible to the coordinator. When moving to
another tool/model, send a checkpoint containing completed work, outstanding checks,
current ownership and exact commits before the successor writes.


## Self-contained dispatch and clarification

Owner-approved 2026-09-21 from the Thruu Sales parallel delivery trial. Use
[[GOV-0020-delivery-templates]] for dispatch, questions, restartable handover,
review and correction formats. These formats operationalize this register;
product requirements remain in their owning notes and live state remains in GitHub.

Every assignment has one durable, versioned dispatch document. A fresh agent must
be able to execute it without chat history. Include the outcome, issue URLs,
accepted decisions, exact required reading and reading order, source/base contract,
assigned isolated worktree, owned files, exclusions, prerequisites, local validation,
evidence requirements, timebox, stop conditions and handover location. Name the
files for this task rather than asking the worker to read an unspecified corpus.
Resolve local paths through the checkout map; provide accessible pinned references
for another machine. A temporary file alone is not durable: retain the approved
packet and final handover in the assignment's governed artifact location and link
it from GitHub before retiring the session. Credentials never belong in packets.

Workers read the complete packet and required sources before dependent execution,
then record their scope/acceptance understanding. Missing authority, conflicting
requirements or a necessary unknown decision triggers a written question with
context, options/trade-offs, recommendation and affected work. Wait for the answer
before dependent work; continue independent safe work. Ask again if the answer is
still ambiguous. Routine implementation choices inside settled boundaries do not
need escalation. The coordinator answers in the questions document and incorporates
accepted answers into the dispatch/handover revision, notifying affected sessions.
A chat reply alone is insufficient for a successor. Approved configurability is
not a reason to repeatedly ask configurable versus fixed; unresolved defaults,
permissions and ownership still require their own decision when material.

Assign a fresh isolated worktree for new writable scope, or explicitly resume the
existing assignment worktree after verifying ownership and status. Preserve dirty
source checkouts. Parallel packets name protected paths and runtime/process owners;
separate files alone do not make shared runtime mutations safe. A blocked gate stays
visible: reading/preflight is not permission to begin held implementation.

Slice size follows coherent outcomes and observed acceptance, not issue count.
Two or three related issues may form one reviewable PR with an itemized acceptance
map. Increase size when the owner requests it and evidence supports the trial;
record the relative budget/complexity assumption rather than claiming an exact
multiple from file count. Hold or reduce scope after material repair unless the
owner explicitly chooses otherwise. Increasing size never lifts dependencies,
security holds or the independent-review requirement.


## Continuation ownership and permitted stopping states

Before ending a turn or retiring a session, reconcile the requested outcome with
unfinished acceptance, review, integration, documentation and authorized deployment
work. A completed subtask does not complete the parent outcome. If authorized,
unblocked work remains and no other executor owns it, continue it in the current
turn; do not end with a future-tense promise or an offer to do already authorized work.

Every unfinished assignment must have one accountable owner and one explicit state:

- **Running:** an actual active tool/process/agent reference, current assignment,
  and the supervisor that will consume its result. A dispatched prompt alone is
  not proof that a worker is running or that the parent will resume.
- **Waiting:** a named external prerequisite, exact event or next-check deadline,
  and an actually registered wait/wakeup mechanism with its handle. If the tool
  cannot wake the coordinator, remain in a supported active wait, arrange an
  authorized continuation, or report that limitation as blocked. Do not imply a
  later turn will run itself.
- **Blocked / needs decision:** concrete blocker, evidence, next owner and the
  smallest action/decision required. Continue independent authorized work where
  useful; never invent permission or weaken gates to remove the blocker.
- **Paused by owner:** the explicit pause/cancellation and preserved checkpoint.

**Complete** requires the assignment's acceptance evidence, not a marker, merge
or successful worker exit alone. A retiring worker may return a reviewed handback
to an active lead; the lead still owns all remaining parent acceptance. A callback
is not a substitute for integrating and reviewing the result.

Do not say 'no action needed' while authorized work remains idle without a real
continuation. Completion, blockers and active waits must be described honestly.
When the current authorized scope is complete but a broader unapproved scope
remains, state that boundary rather than imply background implementation.

Persist a compact continuation checkpoint before planned suspension, compaction
or handoff: outcome/acceptance remaining, current owner, session/process handles,
repo/head, evidence, next executable action, blocker/wait event and deadline.
After resuming, reconcile these handles with reality before starting another writer.
Never assume a saved 'running' flag proves that a process survived a crash.

A supervisor must treat unfinished work with no live executor or registered wait
as **orphaned**, then resume within its existing authority or escalate. It must
not automatically retry potentially completed writes until state is reconciled.
Enforcement needs a real supervisor/host continuation mechanism; prompt rules
alone cannot guarantee another turn after the host stops. Interchange's current
skill/protocol helper does not yet implement this live enforcement.


## Session lifetime and cleanup

Session lifetime follows a coherent assignment, not one repository or one task
checkbox. Reuse only when previous context materially helps, role/permissions
remain compatible and context is healthy; record the specific benefit briefly.
Keep writer sessions through related subtasks and review corrections. Use a fresh
independent reviewer; a writer's own context cannot independently accept its work.
Unrelated outcomes default to fresh sessions with concise verified packets.

Leads may span related slices in a workstream. At each milestone boundary, review
their useful context and record a checkpoint rather than retaining every transcript
indefinitely. Band A baseline workers retire as their accepted assignments close;
at the Band A-to-B transition, new business workers receive baseline contracts,
setup/code maps, evidence and known constraints. Do not inject the full baseline
debugging transcript. Layer milestones do not require one giant session each.

At acceptance, preserve the handback and retire the session from normal routing.
Blocked sessions may be suspended with an owner and explicit resumption condition.
Milestone acceptance under REG-03 triggers a session/worktree inventory, including
remaining parent work and named carryovers. Retirement does not delete a workspace,
transcript or evidence; reviews and incidents may require retention beyond coding.

The lead may remove a worktree only after confirming no live process/dependent
uses it, no unpreserved uncommitted/untracked user work or unique commits exist,
required artifacts/evidence are durable, and remaining reviews/incidents/dependencies
are resolved or explicitly transferred. Verify content preservation after squash
merges rather than relying solely on ancestry. Do not force-remove/reset/clean to
make inventory tidy. Preserve uncertain workspaces with the reason. Provider
session deletion may also delete worktrees; verify its semantics before using it.
Weekly retros may flag orphaned resources but do not grant automatic deletion.


## Worker workflow and escalation

Read the packet and governing pointers, identify actual model/effort, validate the
baseline and create the assigned worktrees. Return a short startup receipt identifying
packet revision, actual base, owned paths and any missing prerequisite.

Implement the assigned outcome; run targeted checks while iterating, then applicable
full gates. Capture command exit status directly, positive pass counts and skipped
checks. For risky boundaries, demonstrate that a regression makes a meaningful test
fail; a changed assertion that merely compares against a wrong constant is weaker
than a regression in the boundary itself.

When blocked, report the first unmet acceptance item, exact evidence, what was tried,
smallest proposed change and independent work still possible. Stop only dependent
work. Do not invent an interface, weaken a gate or claim a fake provider/DOM/database
as real acceptance. A prerequisite or packet defect belongs to the coordinator.

A checkpoint is due before a context/tool switch, on a material blocker, or when
requested. Automated monitoring needs an available connector and authorization;
otherwise use the delivery issue or human relay. Never imply another session is
being watched when it is not accessible.


## Mandatory handback

Persist the handback as a restartable document, update it on a material blocker,
before a context reset/tool or agent transfer, and at completion. Include the exact
next safe action, outstanding acceptance, accepted clarifications, protected work,
owned processes and their actual state. Link it in the return message.

Every worker returns this information, even if it used a different tool or multiple
models. Unknown metadata is `unknown`, with the reason; never infer a model from the
session title or present a requested effort as verified runtime metadata.

```text
Packet ID / revision:
Result: READY FOR PRIMARY REVIEW | PARTIAL | BLOCKED
Tool/client and version:
Provider and exact model ID/version:
Reasoning effort: requested / effective / source of evidence
Model changes or delegated helpers: stage, model, effort, contribution
Session reference (when available):

For each repository:
  URL / worktree / branch / captured base / final HEAD
  Implementation commit(s) / delivery-note commit
  PR URL / live base / live head / draft and check state
  Changed-file list / final worktree status

Acceptance item -> implementation -> test/runtime evidence:
Commands -> direct exit status -> passed/failed/skipped counts:
Negative-path or mutation results and restored passing state:
Local vs hosted vs real-provider evidence:
Runtime/configuration prerequisites and reproduction steps:
Known gaps / unrun checks / blockers / next owner:
Drift or deviations and authorization:
Duration and token/cost usage: measured values, or unknown
Relevant lessons applied / new lesson candidates:
```

No secrets, raw credentials or customer data belong in handbacks. Evidence links need
commit/run/environment identity. `READY FOR PRIMARY REVIEW` does not mean accepted,
merged, deployed or product-complete. A PR with known remaining implementation or
verification gaps stays draft under the project's PR policy.


## Independent acceptance and feedback

The coordinator or assigned reviewer verifies live PR base/head/checks, the three-dot
diff, ownership, public contracts and applicable tests at the reviewed commit. For
user-visible work, exercise the running product. A screenshot of the final page does
not prove who caused the action: capture prompt, intermediate action/results, URL or
state changes and final result. Test more than a memorized demonstration phrase.

Review both **target achievement** and **quality**, not the diff alone. Give the
independent reviewer the full dispatch revision, approved clarifications, issue
criteria, governing product decisions, handover, exact PR head and evidence map.
Map every acceptance item to observed implementation and sufficient evidence.
If the expected outcome is missing or ambiguous, report **cannot verify acceptance**;
never infer requirements or pass on code quality or green CI alone.

Use the latest authorized scope when evaluating evidence. Reconcile stale issue
wording with explicit approved clarifications and update the owning delivery record;
do not invent exemptions or penalize a worker for following the controlling packet.
Attribute packet/coordinator defects separately from implementation defects.

For user-visible acceptance, inspect evidence of the actual user journey and the
relevant records/states, not merely a signed-in page. Check screenshot contents;
viewport clipping, an empty list or a final count may not prove the claimed action.
Distinguish source SHA, image digest, source provenance, runtime/configuration and
local versus deployment proof. Preserve enough redacted evidence to independently
assess each claim; no single artifact format is mandatory when another is sufficient.
Recover existing proof first. If evidence needs recapture, give a narrowly scoped
prompt specifying authorized steps and mutations; preserve original versus later
run provenance. Do not restart the full journey or repair application behavior
merely to fill an evidence gap. Re-review corrections at the new exact head.

For each named session/PR, the coordinator's response starts **PASSED**, **NOT PASSED**
or **REVIEW PENDING**, and reports target achievement, quality/evidence, and remaining
gates separately. Distinguish ready for review, independent pass, merge readiness,
issue acceptance and deployment; none substitutes for another. When NOT PASSED,
include a ready-to-send correction prompt in the same response without waiting for
the owner to ask. Name the writer, issue/PR/head, exact missing result, bounded allowed
actions/files, required evidence, retained holds, stop conditions and return format.
If work is blocked, that prompt asks the smallest actionable question rather than
ordering an unauthorized fix. Keep each session's verdict and next action unambiguous.

Return one review record per packet:

- accepted behaviour and concrete strengths;
- findings with severity, evidence and reproduction;
- root cause: implementation, packet ambiguity, shared interface, environment,
  prerequisite, or coordinator integration;
- corrections required, responsible writer and verification needed;
- primary repairs, if any, with their effort and changed surface; and
- next routing recommendation with relevant lesson IDs.

Check the real exit status and expected success count. Evidence provenance mistakes
are findings even when the implementation works. Attribute ownership fairly: the
SM360 phrase-matched navigation being described as model control was a coordinator
claim failure; it is not evidence that a delegated model failed that requirement.
