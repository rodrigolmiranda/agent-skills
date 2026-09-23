# Portfolio workflow adapter

These procedures implement the adopted portfolio delivery method. Apply only to projects adopting the Portfolio Standard; generic projects use their own governance. Governance retains principles and authority.

Source: GOV-0020-multi-session-orchestration.md.

## Coordinator workflow

1. **Bind the outcome.** Link the approved scope and write the observable user
   acceptance before splitting work. Distinguish a foundation, prototype and
   deployed capability. A route change alone cannot prove an autonomous agent.
2. **Inspect the baseline.** Read current code, contracts and governing notes at
   recorded commits. Shared checkouts may be old or dirty; inspect the named ref
   or a clean worktree. Record what's reusable and what's actually missing.
3. **Partition.** Assign substantial coherent outcomes. Prefer an independent
   vertical slice; when a shared feature needs parallel components, specify the
   interface first and retain an explicit integration owner. One writer per file
   surface, including tests, manifests, lockfiles and generated output.
4. **Preflight the packets.** Verify paths, commands, schema examples and writable
   files; check that required tests can be implemented inside ownership. Remove
   contradictory requirements. Let workers choose routine private implementation
   details within the agreed public boundary.
5. **Dispatch and track.** Give one document and one read-and-execute prompt to
   each session. Record its packet revision, tool/model identity, worktrees and
   dependency status in the delivery issue. Human copy/paste is a supported transport.
6. **Check useful progress.** Inspect at startup, the first working boundary,
   a reported blocker, and handback. Prefer the diff and command evidence to chat
   volume. Do useful integration work between checks; avoid constant polling.
7. **Review independently.** Follow GOV-0020 §Independent acceptance and feedback (central authority); return precise
   findings with expected behaviour and a reproduction. Keep corrections with the
   assigned writer unless the coordinator explicitly takes ownership.
8. **Integrate and close.** Apply current repository merge/release authority,
   reconcile cross-repository changes, run the real user journey, update delivery
   state, then record feedback and relevant lessons. Unmerged work or incomplete
   acceptance remains visible with an owner and next action.

Percent allocations such as “30% Claude, 10% Grok” are planning intuition, not
measured completion. Derive completed acceptance items from the delivery artifacts.
Elapsed time and lines changed do not measure value. Estimate effort as a range
with uncertainty; never fill a six-hour slot by adding scope after its outcome passes.


Source: REG-03-delivery-method.md.

## Three levels

| Level | File | GitHub | Contract |
|---|---|---|---|
| **Milestone** `MS-Mn` | `10-delivery/MS-Mn-<name>.md` | Milestone | goal · user-visible outcome · `blocked_by` · slices · stage gates · pilot metric · gaps closed |
| **Slice** `Mn.Sk` | a section in that file | Issue, type Story | the fourteen-section story contract: outcome and actor · authorities · current and desired behaviour · scope and non-goals · inputs, outputs, rules · entitlements · errors and edges · journey · systems and dependencies · migration and rollout · **acceptance assertions** · verification matrix · running-product acceptance · knowledge impact |
| **Task** `Mn.k.j` | a checkbox in that slice | a checklist line in the Story | **artifact → proof** |

These are the full delivery records for work that needs milestones and slices;
they are not a ceremony to impose on every bounded change. Choose the entry
path before naming the work, then scale the plan and proof to its scope, risk,
ambiguity and dependencies. Scope measures coordination; severity measures
impact and required verification. Neither is inferred from the other.

**Tasks are never sub-issues.** Three to five issues per slice would be closed
by hand, abandoned within a month, and the state would then be a lie. The
checkbox is the plan; the Story open or closed is the state; one writer per
fact.

**Checkboxes live in the milestone note.** `MILESTONES.md` is generated.

### The task line

```markdown
- [ ] **M1.2.3** `Visit` aggregate: private ctor + `Create()` factory,
      `Confirm()`/`Cancel()` enforcing the invariant → unit tests reject
      the invalid transition
```

A backtick-quoted path or type, and a `→` clause naming the check. A task with
neither is a wish and cannot be ticked honestly.

## Sizing

A slice is **one pull request, one demo, one reviewable unit**. Around six
hours of focused work is the typical size — a guide for planning, **not a
cap**. A slice may be deliberately sized larger when the owner says so; what
must not happen is a slice that cannot be demonstrated or reviewed as one
thing. A milestone beyond roughly five slices is re-cut before it starts.

### Entry paths

| Work kind | Minimum intake and plan | Implementation and proof |
|---|---|---|
| New product | Discovery appropriate to its audience; ring cut; profile and capability-baseline assessment | Build the applicable Band A foundation, then prove vertical Band B capabilities from a real walking skeleton |
| Large feature in an existing product | Existing baseline evidence; changed product assumptions; outcome, contracts, dependencies and rollout | Use independently demonstrable vertical slices and milestones only where several slices or rollout stages have separate outcomes |
| Medium feature | Accepted desired behaviour; affected authorities; surface or contract impact; failure cases and rollout needs | Prefer one reviewable vertical slice and its proportionate proof; split only when acceptance or rollout is independently separable |
| Small feature or maintenance | Concise outcome, changed artifact, constraints and appropriate proof | One bounded change or pull request under the relevant plan; do not invent a milestone solely for tracking |
| Bug, known cause | Defect record with expected versus actual behaviour, affected environment or version, reproducible evidence, impact/severity, scope and exclusions | Narrow fix, meaningful regression proof where feasible, targeted checks and affected risk gates; record repeatable evidence when automation is infeasible |
| Bug, unknown cause | The same defect record plus a bounded diagnostic question, evidence and stop condition | Diagnose before planning a broad fix. Link any resulting capability or material migration to its own feature or enabling work |
| Incident or urgent hotfix | Impact, severity, incident owner, containment decision and permitted actions | Restore safely under authorised procedures, verify the affected path, observe recovery, then reconcile root cause, tests and documentation |

The concise bug record contains: defect ID/title; expected versus actual
behaviour; affected environment/version; reproduction or diagnostic evidence;
impact/severity; scope and exclusions; acceptance/regression proof;
implementation/test evidence; rollout or recovery needs; owner; and linked
authority. Use a Bug work item where the repository supports it. Do not
fabricate a Story, a milestone or fourteen empty story sections for one bounded
defect.

## Portfolio packet templates

Use [portfolio delivery formats](portfolio-delivery.md) for dispatch, questions, restartable handover, independent review and correction. Central GOV-0020 retains authority and evidence requirements.
