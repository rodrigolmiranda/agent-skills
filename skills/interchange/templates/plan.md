# Delivery plan — <plan ID>

Revision: <n> · Owner: <name> · Date: <YYYY-MM-DD>
Intake: <new | continuation | BAU | incident> · Status: <proposed | approved | held>
Omit inapplicable sections; do not leave blank ceremony.

## Baseline

- Existing behavior/state and evidence: <paths, URLs, revisions, or unknowns>
- Prior work, open PRs/issues, and preserved local changes: <references>
- Scope authority and accepted decisions: <references; resolved text for clarifications>

## Outcome and scope

- User/operational trigger and observable outcome: <who does what, when, and result>
- Included: <bounded behavior, systems, and data>
- Excluded: <explicit boundaries>
- Decisions / assumptions: <decision and authority, or question ID>
- Dependencies and gates: <dependency, current evidence, owner, next gate>
- Risks and rollback/recovery: <only task-relevant items>

## PR slices

One row per independently reviewable PR. Order by dependency; keep each slice concrete.

| Slice ID | Outcome / acceptance IDs | Repository and owned paths | Depends on | Writer / reviewer | Proof |
|---|---|---|---|---|---|
| <S1> | <observable result / A1> | <repo / paths> | <IDs or none> | <roles> | <checks / evidence> |

## Journey and visual review

- User journey / trigger: <entry point, actor, key state transitions>
- UX review trigger: <new pattern | complex interaction | integrated checkpoint | none, with reason>
- Evidence to capture: <before/after screenshots and states, if applicable>
- Visual verification boundary: <what can and cannot be checked>

## Intake and next action

- Continuation: <last verified checkpoint, current owner, exact next action>
- BAU: <cadence/trigger, service boundary, completion signal>
- Incident: <impact, start time, containment, incident owner, update/escalation route>
- Unresolved questions: <question IDs; dependent work held>
- Safe independent work while held: <bounded work or none>
- Next action and owner: <specific action>
