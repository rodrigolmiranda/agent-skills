# Portfolio dispatch and acceptance formats

Governed by the adopted GOV-0020 authority. Fill actual assignment facts, omit inapplicable fields with a reason, and link owning requirements instead of copying them. Operational copies belong in the assignment artifact root, linked from GitHub.

## Dispatch document

```markdown
# <Session / packet ID> — <observable outcome>
Revision / date / owner / assigned writer:
Issue URLs / one-PR bundle / approved scope source:
Requested model/effort; observed identity or unknown:

## Read and understand first
Read this whole document, then every required source in the order below before
execution beyond safe reconnaissance. Record your understanding/checklist in
handover.md. Ask about missing or conflicting requirements before dependent work.
1. Applicable AGENTS.md/CLAUDE.md and resolved governance source/revision.
2. Exact product/decision/milestone file paths and relevant sections.
3. Live issue/PR URLs and controlling approved clarification records.
4. Exact implementation, contract, fixture and validation-script paths.
Checkout map / accessible artifact locations / successor-machine instructions:

## Outcome and acceptance
Actor / current behavior / desired observable result:
Acceptance ID | Expected result | Required proof | Owning issue

## Scope and prerequisites
Owned files / allowed variance / non-goals:
External contracts/packages and published evidence:
Gate | Current verified state | Owner | Event authorizing next action
Independent work allowed while a gate is closed:

## Workspace and coordination
Repository / base or minimum ancestor / drift policy:
Assigned isolated worktree / branch / resume-or-create instructions:
Protected source checkout, other writers' paths, generated files and runtime:
Allowed tools/actions, data mutations, environment and credential prerequisites:

## Execution and validation
Bounded implementation steps / approved commands and meaningful tests:
Local validation before ready PR / browser evidence when applicable:
Evidence directory, redaction, source/runtime identity and artifact requirements:
PR base / draft-to-ready conditions / merge authority:
Target budget / hard stop / escalation triggers:

## Questions and answers
Question file path; write context, options/trade-offs, recommendation and blocked
work; notify owner. Wait before dependent work; continue safe independent work.
Ask again if still unclear. Incorporate accepted answers into this packet revision
and the handover before a reset or transfer.

## Return
Durable handover path/link / expected report format:
PR/head SHA, acceptance mapping, validation, gaps, next owner/action.
```

## Clarification record

```markdown
# <Packet ID/revision> — questions
Verified baseline/state; actions already taken:
## Q<number> — <decision>
Context and precise question:
Options, trade-offs/example, recommendation:
Blocked action / independent work possible:
Answer (<decision owner>, date):
Resolved or follow-up question:
Incorporated into dispatch revision/link:
```

## Restartable handover document

```markdown
# <Packet ID/revision> — handover
Result: READY FOR PRIMARY REVIEW | PARTIAL | BLOCKED
Tool/client and version:
Provider and exact model ID/version:
Reasoning effort: requested / effective / evidence source:
Model changes or helpers: stage, model, effort, contribution:
Session reference (when available):
Duration and token/cost usage: measured values or unknown with reason:
Relevant lessons applied / new lesson candidates:
## Outcome, scope and acceptance remaining
## Repository, worktree, branch, base/head and live PR/check state
## Required reading and accepted clarifications
Resolved paths/URLs/revisions; unanswered questions; scope understanding.
## Changed files and preserved/foreign work
## Acceptance map
Acceptance ID | Implementation/result | Evidence with identity | Pass/fail/unverified
## Validation
Exact command | Exit status | Passed/failed/skipped counts | Artifact
Source, runtime, deployment and provider evidence kept distinct.
## Remaining gates and next safe action
Exact action/command, prerequisite, responsible owner; no implied background work.
## Runtime/process ownership and cleanup
Actual handles/state; resources preserved for another session.
## Return links
PR, full head SHA, durable evidence, questions and this document.
```

## Independent review packet and result

```markdown
# Review <session / packet revision / PR>
Reviewer identity / independence / reviewed full head SHA / live base/checks:
Inputs: complete dispatch, approved clarifications, criteria, governing decisions,
handover, actual diff and evidence map (resolved paths/URLs/revisions).

Target achievement: MET | NOT MET | CANNOT VERIFY
Acceptance ID | Expected outcome | Observed result/evidence | Disposition
Quality: PASS | FINDINGS | NOT ASSESSED
Evidence: SUFFICIENT | INSUFFICIENT (exact missing proof)
Overall session verdict: PASSED | NOT PASSED | REVIEW PENDING

Findings: severity, exact path/line or artifact, expected/actual, cause/owner,
minimal correction and verification. Distinguish stale packet wording from a
worker error; cite the controlling authorized clarification.
Remaining issue/merge/deployment gates and limits:
Recommendation: ready for owner action, or correction prompt below.
```

## Owner-facing verdict and correction prompt

```markdown
Session <name> — PR <number>: PASSED / NOT PASSED / REVIEW PENDING
Target achieved: <yes/no/unverified>. Quality/evidence: <result>.
Next action and owner: <explicit>; merge/deployment state: <separate>.

If NOT PASSED, send this to <writer>:
Continue packet <ID/revision> in <existing isolated worktree>, PR <URL/head>.
Unmet outcome/finding: <precise expected versus evidenced result>.
Read: <complete dispatch and review artifact paths>.
Correct only: <allowed files/actions>; preserve <other work/runtime>.
Verify with: <bounded check or authorized evidence recapture>.
Retain these holds/non-goals: <list>.
Stop/ask if: <scope/access/decision trigger>; timebox: <budget>.
Update dispatch answers and restartable handover; return full head SHA and
finding-to-evidence mapping. No merge or second task.
```
