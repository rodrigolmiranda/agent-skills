# Interchange decision diagrams

Approved configuration: [policy.json](../skills/interchange/references/policy.json). These diagrams explain its decision paths. Profile assignments are initial hypotheses, not benchmark results. Runtime controls shown here are design requirements; only the completion/scheduling helper is implemented.

## Team and model selection

```mermaid
flowchart TD
  A[Approved outcome] --> B{One direct lookup?}
  B -->|Yes| C[Use local search or tool]
  B -->|No| D[Delivery manager: Astra medium default, Sol high or Opus 5 high]
  D --> E[Partition coherent workstreams and dependencies]
  D -->|New product brainstorming| W[Fable 5.1 medium or Astra medium]
  W --> R
  E --> F{Lead decision complexity}
  F -->|Defined contracts| G[Terra xhigh]
  F -->|Difficult integration, defined architecture| H[Terra max]
  F -->|Moderate architecture| I[Sol medium]
  F -->|High consequence or coupling| J[Sol high]
  F -->|Unresolved cross-workstream architecture| K[Astra medium]
  G & H & I & J & K --> L[Bounded packets with one writer and acceptance]
  L --> M{Implementation class after ambiguity and risk assessment}
  M -->|Small bounded support| N[Muse xhigh or Luna xhigh/max]
  M -->|Low/mid| O[Grok high, Opus medium, Terra xhigh, Sol medium]
  M -->|Upper-mid| P[Grok xhigh or Opus medium]
  M -->|High| Q[Sol high or Opus high]
  M -->|Demanding but well-defined| T[Terra max]
  N & O & P & Q & T --> R[Quality eligibility, then accepted-result speed, available pool and context continuity]
  R --> U{Same-house exclusivity conflict?}
  X[Global: any Astra in Codex, any Fable 5.1 in Claude] -.-> U
  Y[Same delivery manager only: Sol high+ in Codex, Opus high+ in Claude] -.-> U
  U -->|Yes| V[Eligible other house or queue]
  U -->|No| S[Exact profile and tool permissions verified before dispatch]
```

Pools are starting preferences, not model rankings. Read [development routing instructions](../skills/interchange/references/routing.md) for task boundaries and escalation. Grok uses Grok CLI only; Claude development uses Opus. Worker model choice grants no delegation or merge authority.

Policy 0.4.0 allows Sol high and Opus 5 high as alternative delivery managers, with Astra medium
remaining the default. Product brainstorming uses Fable 5.1 medium or Astra medium.
Any Astra reserves Codex globally and any Fable 5.1 reserves Claude globally.
Sol high-or-higher and Opus high-or-higher reserve their houses only for work
under the same delivery manager. Only medium is currently approved for Fable.
Fable needs confirmed
included-plan eligibility under the no-extra-spending rule.

This revision also requires the manager to retain live supervision while workers
run, machine-owned provider output, fail-closed permission preflight, complete
packet transport, finite watchdogs and verified ownership transfer after abnormal
provider exits. Claude stops after two consecutive no-progress auto-compactions.

## Monitoring and completion

```mermaid
flowchart TD
  A[Lead allocates assignment, attempt and worktree] --> B[Preflight packet, permissions, budgets and handles]
  B --> C[Adapter starts fixed profile and drains raw stream]
  C --> O[Manager retains live supervision with bounded waits]
  O --> D{Final assistant response and process exit?}
  D -->|Yes| E{Exit zero, valid JSON, matching final marker?}
  E -->|No| F[Failed or incomplete: inspect before retry]
  E -->|Yes| G{Reported result}
  G -->|Blocked or partial| H[Lead receives blocker]
  G -->|Ready for review| I[Independent artifact verification]
  I --> J[Accepted only after evidence passes]
  D -->|No| K{Deadline or repeated failure?}
  K -->|Below review deadline| L[Adaptive bounded retrieval interval]
  L --> O
  K -->|Review at 2x estimate| M[Request reason and progress evidence once]
  M --> O
  K -->|Hard limit at 3x estimate| N[Interrupt and verify child processes stopped]
  N --> H
```

## Recovery and war room

```mermaid
flowchart TD
  A[Failure or blocker] --> B[Lead classifies evidence]
  B -->|Network or CLI| C[Inspect process and checkpoint; resume same session]
  B -->|Quota| D[Choose eligible available account and pool]
  B -->|Capability| E[Narrow problem or choose approved model and effort]
  B -->|Scope or contracts| F[Stop dependent work; accountable lead decision]
  C & D & E & F --> G{Recovered within two attempts?}
  G -->|Yes| H[Continue with preserved ownership and acceptance]
  G -->|No or several workstreams affected| I[War room: one incident lead]
  I --> J[Delivery manager commissions one bounded independent diagnosis]
  J --> K{Resolved within authority?}
  K -->|Yes| H
  K -->|No| L[Owner decision with evidence and options]
```

## Merge authority

```mermaid
flowchart TD
  A[PR ready] --> B{Designated lead or manager?}
  B -->|No| C[Return evidence; worker cannot merge]
  B -->|Yes| D{Live base exactly test and repository adopted?}
  D -->|No| E[Follow human authority or repository hold]
  D -->|Yes| F{Current-head independent review and all checks pass?}
  F -->|No| G[Fix and re-review current head]
  F -->|Yes| H{Required approving review present?}
  H -->|Yes| I[Re-query head and merge bound to reviewed SHA]
  H -->|No| J{Independent Codex PR review passed and approved bypass available?}
  J -->|No| K[Wait for required approval]
  J -->|Yes| L[Record reason and SHA; bypass approval only]
  L --> I
```

## Session reuse and retirement

```mermaid
flowchart TD
  A[Next assignment] --> B{Previous context materially helps?}
  B -->|No| C[Fresh session with concise verified packet]
  B -->|Yes| D{Compatible role, scope and healthy context?}
  D -->|No| C
  D -->|Yes| E[Record reuse reason and verify current baseline]
  E --> F[Resume related work]
  F --> G{Assignment accepted and handback saved?}
  G -->|No| H[Continue corrections or suspend with owner]
  G -->|Yes| I[Retire session from active routing]
  I --> J{Workspace unused and all work/evidence preserved?}
  J -->|No| K[Retain workspace with reason]
  J -->|Yes| L[Lead may perform guarded worktree cleanup]
```

Apply [session lifecycle rules](../skills/interchange/references/session-lifecycle.md). Baseline layers and vertical business slices have different handover boundaries. Neither completion markers nor merges alone authorize cleanup.

## Feedback and changes

```mermaid
flowchart LR
  A[Mechanical usage and elapsed time] --> C[Comparable delivery evaluation]
  B[Independent acceptance findings] --> C
  C --> D[Canonical lesson when triggered]
  D --> E[Weekly proposed change with evidence and rollback]
  E --> F{Owner approves?}
  F -->|Yes| G[Version policy and adopt in affected repositories]
  F -->|No| H[Keep current policy and record decision]
  G --> I[Observe next comparable deliveries]
  I --> C
```
