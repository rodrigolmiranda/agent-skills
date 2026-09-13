# Interchange decision diagrams

Approved configuration: [policy.json](../skills/interchange/references/policy.json). These diagrams explain its decision paths. Profile assignments are initial hypotheses, not benchmark results. Runtime controls shown here are design requirements; only the completion/scheduling helper is implemented.

## Team and model selection

```mermaid
flowchart TD
  A[Approved outcome] --> B{Unresolved interpretation?}
  B -->|Ordinary product or architecture judgment| C[Sol high brain]
  B -->|Unusually large cross-workstream ambiguity| D[Astra medium brain]
  B -->|Product ideation| E[Fable 5.1 medium brain after included-plan check]
  B -->|No| F[Mechanical candidate]
  C & D & E --> G[Settle behavior, interfaces, tradeoffs and acceptance]
  G --> F
  F --> H{Mechanical work class}
  H -->|Immediate direct lookup| I[Local tool]
  H -->|Light read/seek or narrow edit| J[Muse xhigh; Luna alternative]
  H -->|Bounded implementation| K[DeepSeek, Grok, Opus, Terra or Sol worker profile]
  H -->|Dense settled integration| L[Terra max or approved bounded worker]
  I & J & K & L --> M{Net gain after startup, supervision and integration?}
  M -->|No| N[Execute directly or keep one coherent packet]
  M -->|Yes| O[Choose fastest low-cost qualified profile]
  O --> CA{Codex mechanical profile?}
  CA -->|No| P{Independent objective packets and non-overlapping writes?}
  CA -->|Yes| CZ{Owner set Codex delegation or leading to zero?}
  CZ -->|Yes| CE[Use an eligible external house]
  CZ -->|No| CB{Positive allowance, reason and brain-review reserve recorded?}
  CB -->|No| CE[Use an eligible external house]
  CB -->|Yes| CC{No active Codex mechanical worker?}
  CC -->|Yes| CD[Start one; recheck usage at first clean checkpoint]
  CC -->|No| CF[Queue or obtain explicit owner authorization]
  CE & CD & CF --> P
  P -->|Yes| Q[Run in parallel]
  P -->|No| R[Run sequentially with one writer]
  N & Q & R --> U{Same-house exclusivity conflict?}
  X[Global: any Astra in Codex, any Fable 5.1 in Claude] -.-> U
  Y[Same delivery manager only: Sol high+ in Codex, Opus high+ in Claude] -.-> U
  U -->|Yes| V[Eligible other house or queue]
  U -->|No| S[Exact profile and tool permissions verified before dispatch]
```

Sol high is the default product and architecture brain. Astra medium handles unusually large cross-workstream ambiguity; Fable 5.1 medium handles product ideation after its included-plan/no-extra-cost check. Independent semantic and risk acceptance also uses Sol high, with Astra medium for unusually large cross-workstream scope. Other profiles execute settled mechanical packets and return ambiguity instead of interpreting it. A delivery manager on another profile may coordinate but does not gain judgment authority.

Muse Spark 1.3 is the light mechanical and read/seek lane. Use fast, low-cost workers when startup, supervision and integration still produce a net gain, and parallelize only independent objectively testable packets with non-overlapping write ownership. Pools are starting preferences, not universal model rankings. Read [development routing instructions](../skills/interchange/references/routing.md) for task boundaries and escalation. Worker model choice grants no delegation or merge authority.

Codex is protected brain and semantic-review capacity. External houses take mechanical work first. A Codex mechanical worker requires a recorded delivery allowance, exception reason and remaining brain/review reserve; no allowance means zero dispatch. An owner instruction not to use Codex for delegation or leading overrides the allowance and sets worker/lead allocation to zero. Default Codex mechanical concurrency is one, with a usage checkpoint after its first clean checkpoint. Batch brain questions and review meaningful integrated chunks instead of every leaf assignment.

Policy 0.7.0 separates coordination from judgment and protects Codex capacity. Opus 5 high remains an approved
delivery-manager continuity profile but routes interpretation to an approved brain.
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

PR creation has a separate fail-closed base preflight. Ordinary feature, fix,
chore and documentation packets must target `test`; an ordinary packet
requesting `main` is rejected before the provider API or CLI is called. Only an
explicitly classified human-controlled `hotfix` or `release_promotion` packet
may target `main`, and it must carry `human_only_merge: true` plus full,
matching base/head ref and commit-SHA evidence. The reusable implementation is
`skills/interchange/scripts/pr_base_guard.py`; it is an adapter boundary rather
than remote GitHub enforcement. See [the guard contract](../skills/interchange/references/pr-base-guard.md).

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
