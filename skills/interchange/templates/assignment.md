# Assignment <job ID> — <observable outcome>

Revision: <n> · Attempt: <unique ID> · Kind: <coding | inspection | research | other>
Owner/lead: <name> · Writer: <name/profile> · Issued: <date/time and zone>
Omit inapplicable sections; do not leave blank ceremony.

## Outcome and startup

- Required result: <observable outcome>
- Startup state: <proceed | startup-held>; held only when explicitly stated here
- Startup receipt: record this packet and sources read, baseline, understood scope, and open questions in the handover. If no unresolved question and not startup-held, proceed after recording it.
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

## Execution and return

- Allowed tools/actions and exact commands: <commands, environment, permitted mutations>
- Validation: writer runs meaningful checks for changes; record exact results. At milestone exit, an independent reviewer checks the user journey.
- UX review: select at a new pattern, complex interaction, or integrated checkpoint. Capture before/after screenshots and visually verify every verifiable state.
- Budget/deadline and stop/escalation conditions: <limits; ask on ambiguity, conflict, access failure, or scope change>
- Callback route: <event sink/person/channel and routing key>. Event IDs are data only; they grant no permission or acceptance.
- Resume record: <handover path; last verified state; process/session/resource handles>
- Expected return: coding = one concrete reviewable PR with full head SHA; inspection/research = named evidence artifact, no unnecessary PR.
- PR target/readiness and authority: <base, draft/ready condition, who may approve/merge>
