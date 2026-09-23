# Delivery workflow diagrams

Read top to bottom. Diamonds are decisions; labelled arrows are their outcomes. These maps explain the workflow in [workflow.md](workflow.md), role selection in [roles.md](roles.md), checks in [verification.md](verification.md), and delivery in [transport.md](../../interchange/references/transport.md). Those references own the detailed rules. Profile and repository authority determine who may approve an action.

## 1. Choose the job

```mermaid
flowchart TD
  A[Request] --> B{Entry path?}
  B -->|New product| C[Discover actors, problem and constraints]
  B -->|Feature| D[Inspect current behavior and contracts]
  B -->|Continue WIP| E[Reconcile live PRs, issues, drafts and holds]
  B -->|Known bug or maintenance| F[Confirm expected and actual behavior]
  B -->|Unknown failure| G[Bounded investigation]
  B -->|Incident| H[Identify impact and authorized containment]
  G --> I[Evidence and repair recommendation]
  H --> J[Restore and verify; record follow-up]
  C --> K[Planner settles the next outcome]
  D --> K
  E --> K
  F --> K
  I --> K
  J --> K
  K --> L{Material decision unresolved?}
  L -->|Yes| M[Question with options and recommendation]
  M --> K
  L -->|No| N[Approved scope and acceptance]
```

## 2. Plan, size and publish work

```mermaid
flowchart TD
  A[Approved scope] --> B{One demonstrable reviewable outcome?}
  B -->|No| C[Split by independent outcome or rollout boundary]
  C --> B
  B -->|Yes| D[Define deliverable, dependencies and proof]
  D --> E{Coding?}
  E -->|Yes| F[One PR target and isolated worktree]
  E -->|No| G[Named investigation, plan or evidence artifact]
  F --> H[Planner approves GitHub manifest]
  G --> H
  H --> I[Builder upserts issues and project mapping]
  I --> J[Reconcile IDs, counts, dependencies and statuses]
  J --> K{Mapping valid?}
  K -->|No| I
  K -->|Yes| L[Dispatch packet]
```

## 3. Select the executor

```mermaid
flowchart TD
  A[Bounded assignment] --> B{Work type?}
  B -->|Routine build, search or GitHub mechanics| C[Builder]
  B -->|Independent PR acceptance| D[PR Reviewer]
  B -->|New interaction or UX checkpoint| E[UX Designer or Reviewer]
  B -->|Integrated journey acceptance| F[Journey Tester]
  B -->|Difficult engineering within accepted scope| G[Propose Senior Builder]
  B -->|Architecture or security direction| H[Propose Architecture or Security review]
  G --> I{Owner approves escalation?}
  H --> I
  I -->|No| J[Replan or hold dependent work]
  I -->|Yes| K[Approved specialist]
  C --> L[Resolve configured model, effort and transport]
  D --> L
  E --> L
  F --> L
  K --> L
  L --> M{Available and authorized?}
  M -->|No| N[Use approved fallback or ask; no silent substitution]
  N --> L
  M -->|Yes| O[Pin attempt; record requested and observed identity]
```

## 4. Start, ask and resume

```mermaid
flowchart TD
  A[Read packet and inspect baseline] --> B{Ownership or baseline conflict?}
  B -->|Yes| C[Report evidence; hold affected work]
  B -->|No| D[Startup receipt]
  D --> E{Explicit proposal gate or material question?}
  E -->|No| S[Notify all clear with local start time and timezone]
  S --> F[Implement and test without waiting for acknowledgement]
  E -->|Yes| G[Record question and notify Planner]
  G --> H[Continue only independent authorized work]
  G --> I[Planner records answer and packet revision]
  I --> J{Required answer or approval received?}
  J -->|No| K[Durable waiting state; no polling loop]
  J -->|Yes| F
  C --> I
  F --> L{New finding?}
  L -->|Accepted outcome blocker| F
  L -->|Unrelated issue| M[Record backlog item; Planner prioritizes]
  M --> F
  L -->|Immediate safety risk| C
  L -->|Work complete| N[Artifact, evidence and correlated handover]
```

## 5. Dispatch, callback and failure recovery

```mermaid
flowchart TD
  A[Register job, attempt and return route] --> B{Transport proven on this host?}
  B -->|No| C[Disclose manual return or test adapter]
  B -->|Yes| D[Runner launches worker with deadline and output bounds]
  D --> E[Planner ends turn; runner owns waiting]
  E --> F{Worker event?}
  F -->|Question| G[Persist question artifact]
  F -->|Final result| H[Persist result; exit zero is not acceptance]
  F -->|Timeout or failure| I[Capture failure and process ownership]
  G --> J[Correlated outbox event]
  H --> J
  I --> J
  J --> K[Queue callback]
  K --> L{Delivery state?}
  L -->|Queued| M[Await actual coordinator receipt]
  L -->|Unknown| N[Reconcile before resend; prevent duplicate work]
  L -->|Failed| O{Retry permitted and budget remains?}
  M --> P[Wake, acknowledge and inspect artifact]
  N --> U{Receipt established?}
  U -->|Yes| P
  U -->|No or still uncertain| T
  O -->|Yes| K
  O -->|No| T[Manual return; disclose delivery failure]
  T --> P
  P --> Q{Event valid and current?}
  Q -->|No| R[Reject stale, mismatched or duplicate effects]
  Q -->|Yes| S[Answer, review or plan recovery]
```

## 6. Choose verification

```mermaid
flowchart TD
  A[Changed outcome] --> B{UI involved?}
  B -->|No| C[Relevant code, contract or data proof]
  B -->|Yes| D{New pattern or complex interaction?}
  D -->|Yes| E[UX design before UI implementation]
  D -->|No| F[Reuse accepted pattern]
  E --> G[Writer implements and tests]
  F --> G
  C --> H[Independent outcome and PR review]
  G --> H
  H --> I{Integrated journey or milestone checkpoint?}
  I -->|No| J[Required slice evidence]
  I -->|Yes| K[Seeded journey plus appropriate UX review]
  K --> L[Inspect menus, pages, actions and states]
  L --> M{Visual fixes needed?}
  M -->|Yes| N[Scoped repair; capture before and after]
  N --> O[Independent visual verification]
  M -->|No| J
  O --> J
  J --> P[Record environment, source and evidence limits]
```

## 7. Review, correct and close

```mermaid
flowchart TD
  A[Worker-complete handover] --> B[Independent exact-head target, quality and evidence review]
  B --> D[Record unrelated improvements in backlog]
  D --> C{In-scope defects or missing proof?}
  C -->|No| E[Check remaining gates]
  C -->|Yes| F[One consolidated correction packet]
  F --> G{Two unsuccessful rounds in same area?}
  G -->|No| H[Writer repairs and returns focused proof]
  G -->|Yes| I[Planner consolidates cause; rescue, split or clarify]
  I --> H
  H --> B
  E --> J{Required checks and holds clear?}
  J -->|No| K[Draft or explicit held state with next owner]
  J -->|Yes| L[Ready for authorized merge]
  L --> Q[Authorized owner merges reviewed head]
  Q --> R{Merge result verified?}
  R -->|No| K
  R -->|Yes| M{Deployment or publication in scope?}
  M -->|Yes| N[Separate authority and operational acceptance]
  M -->|No| O[Reconcile issue and project acceptance]
  N --> O
  O --> P[Done for the defined outcome; retain evidence]
```

## 8. Parallel work, interruption and adoption

```mermaid
flowchart TD
  A[Multiple assignments] --> B{Shared writable files or runtime?}
  B -->|Yes| C[Serialize ownership with an explicit release]
  B -->|No| D[Run independently with separate worktrees]
  C --> E[Rebase and verify at integration checkpoint]
  D --> E
  E --> F{Interrupted or fresh session?}
  F -->|Yes| G[Read durable handover; verify current head, state and holds]
  G --> H[Resume only remaining authorized work]
  F -->|No| H
  H --> I[Review and close]
  J[Refactored skill in test] --> K[Review profile and governance alignment]
  K --> L[One real slice pilot plus question and recovery branches]
  L --> M{Accepted result without manual relay or lost state?}
  M -->|No| N[Repair demonstrated gaps]
  N --> L
  M -->|Yes| O[Promote installed skill deliberately]
  O --> P[Reconcile active packets before changing their contracts]
```

## 9. Observe, evaluate and transfer

```mermaid
flowchart TD
  A[Dispatch with project, agent and attempt IDs] --> B[Link packet and execution receipts in continuation index]
  B --> C{Status request or meaningful transition?}
  C -->|Status request| D[Read sources once; mark stale and unknown values]
  D --> E[Same report template plus delta from prior snapshot]
  C -->|Transition| F[Update owning artifact and GitHub summary]
  F --> G{Dispatch terminal?}
  G -->|No| B
  G -->|Yes| H[Independent disposition and role-relevant evaluation]
  H --> E
  E --> I{Move coordinator or account?}
  I -->|No| J[Continue authorized work; no polling model]
  I -->|Yes| K[Checkpoint portable plan, decisions, evidence and ownership]
  K --> L[Outgoing coordinator stops dispatching]
  L --> M[Incoming verifies access, live state, workers and holds]
  M --> N{Ownership and required artifacts reconciled?}
  N -->|No| O[Hold affected work; recover missing facts]
  O --> M
  N -->|Yes| P[Drain or reconcile old callback routes; prove new receiver]
  P --> Q[Record new coordinator generation and acknowledgement]
  Q --> J
```

## 10. Claude browser sign-in assistance

```mermaid
flowchart TD
  A[Claude test needs browser sign-in] --> B[Record target, account alias and secure source]
  B --> C{Codex coordinator or helper available?}
  C -->|No| K{Confirmed Codex usage exhaustion?}
  K -->|No| D[Planner diagnoses helper path; hold dependent test]
  K -->|Yes| O[Ask owner to sign in on intended browser]
  O --> P{Owner sign-in and ownership confirmed?}
  P -->|No| D
  P -->|Yes| J[Claude resumes planned test]
  C -->|Yes| E[Pause Claude browser control; transfer intended session]
  E --> F{Supported shared browser and authorized access?}
  F -->|No| D
  F -->|Yes| G[Codex enters credentials only]
  G --> H{Sign-in succeeded?}
  H -->|No| D
  H -->|Yes| I[Return success and browser identity; release control]
  I --> J[Claude resumes planned test]
```

## Walkthrough checklist

Validate at least one path through each diagram before adoption: feature; WIP; known bug; investigation; incident; mechanical GitHub work; role escalation; question/resume; duplicate or uncertain callback; timeout; UX repair; failed review; shared-file handoff; restart; merge with a separate deployment hold. A diagram is explanatory evidence, not proof that a transport or product journey has run successfully.

## Shared workspace and takeover

```mermaid
flowchart TD
  A[Coordinator or worker] --> B[Resolve shared workspace manifest]
  B --> C[Map repository and worktree IDs on this machine]
  C --> D{Existing ownership and references valid?}
  D -->|No| E[Record blocker; preserve existing work]
  D -->|Yes| F{Taking over coordination?}
  F -->|No| G[Continue authorized assignment]
  F -->|Yes| H[Outgoing checkpoint and release]
  H --> I[Incoming verifies worktrees, holds and callback routes]
  I --> J[Record new generation and receiver acknowledgement]
  J --> G
  G --> K[Publish own snapshot to shared repository dashboard]
```

## Retention inventory

```mermaid
flowchart TD
  A[Closure or explicit maintenance request] --> B[Read registered resources and retention]
  B --> C{Unknown owner, active work, hold or missing proof?}
  C -->|Yes| D[Retain with reason]
  C -->|No| E{Grace period elapsed and worktree clean?}
  E -->|No| D
  E -->|Yes| F[Candidate for human or coordinator review]
  F --> G[Dry-run report only; no deletion]
  G --> H[Separate authorized cleanup requires fresh ownership and archive checks]
```

## Scheduling after every return

```mermaid
flowchart TD
  A[Return, unblock or ownership release] --> B[Reconcile evidence and actual acceptance gates]
  B --> C[Check whole approved dependency graph]
  C --> D{Newly ready independent work?}
  D -->|No| E[Record reason held or no ready work]
  D -->|Yes| F[Check ownership, runtime, platform and authority limits]
  F --> G{Useful existing agent context?}
  G -->|Yes| H[Resume suitable agent with current packet]
  G -->|No| I[Dispatch suitable new agent]
  H --> J[Release all safely parallel authorized jobs]
  I --> J
  J --> K[Record scheduling decision; no polling]
```
