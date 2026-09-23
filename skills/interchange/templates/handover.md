# Handover <job ID>/<revision>/<attempt ID>

Result: <ready for review | partial | blocked> · Owner: <current owner> · Updated: <time/zone>
Omit inapplicable sections; do not leave blank ceremony.

## Startup receipt and result

- Read/understood: <packet revision and source paths/URLs/revisions>
- Baseline and scope understood: <brief record; open questions/holds>
- Outcome achieved / remaining: <observable result and gap>
- Acceptance map:

| ID | Result | Evidence and identity | Status |
|---|---|---|---|
| <A1> | <observed behavior> | <artifact, source/runtime, timestamp> | <pass | fail | unverified> |

## Changes and delivery state

- Changed paths/artifacts: <list; distinguish preserved or other-writer changes>
- PR: <URL or none>; base: <ref/SHA>; full head commit ID: <unabbreviated ID or unknown>
- Live checks at <time>: <name = pass/fail/pending/skipped, link and conclusion>; do not imply unobserved checks passed.
- Target map: <issue/acceptance ID → changed path/artifact and evidence>
- Clarifications incorporated: <question IDs and assignment/plan revision>

## Evidence and validation

- Commands: <exact command, exit status, pass/fail/skip counts, artifact link>
- Screenshots: <before/after paths, state, source/runtime identity, what was visually verified>
- Source/runtime/deployment identity: <commit/build/environment/version; unknown if unavailable>
- Evidence gaps or limits: <exact missing proof>
- Discovered bugs outside accepted criteria: <evidence and proposed backlog item; no scope change>

## Continuation and resources

- Process/session/provider handles and actual state: <IDs, running/stopped/unknown>
- Worktree/branch/base and resume steps: <location, dirty state, safe next command>
- Resources, credentials, data, locks, or artifacts retained: <owner/location/state>
- Next owner action: <one concrete action, prerequisite, and owner>
- Escalations/unanswered questions: <IDs and blocked work, or none>

## Interaction history and evaluation facts

| UTC time | Event / attempt | Decision, evidence and next owner |
|---|---|---|
| <time> | <dispatch/question/answer/correction/return> | <durable link; brief change> |

- Timing: <start/return, process duration, external wait and sources; unknown where unmeasured>
- Usage: <measured tokens/cost and source, or unknown>; owner interventions: <count/evidence or unknown>
- Evaluation: <independent review link and disposition, or pending>; prior attempt: <link or none>
