# Independent review <job ID>/<revision>/<attempt ID>

Reviewer: <identity and independence basis> · Reviewed: <timestamp>
Omit inapplicable sections; do not leave blank ceremony.
Exact full head commit ID: <unabbreviated ID> · Live base: <ref/SHA> · Checks at <time>: <actual pass/fail/pending/skipped with links>

## Inputs and verdict

- Inputs: <assignment and accepted clarifications, plan/criteria, handover, diff, evidence map>
- Target outcome: <met | not met | cannot verify> — <evidence for conclusion>
- Quality: <pass | findings | not assessed> — <findings or reason>
- Evidence: <sufficient | insufficient> — <source/runtime, screenshots, checks, exact gaps>
- Overall: <passed | not passed | review pending>

## Acceptance map

| ID | Expected result | Observed evidence | Verdict |
|---|---|---|---|
| <A1> | <criterion> | <exact artifact/path/runtime> | <met | unmet | cannot verify> |

## Findings and next action

| Finding ID | Severity / type | Location and expected vs actual | Minimal correction / proof |
|---|---|---|---|
| <F1> | <blocker | follow-up> | <path/line; discrepancy> | <bounded fix and verification> |

- Blockers: <must fix for acceptance, or none>
- Follow-ups: <backlog/recommendation outside acceptance; never block unless criterion requires it>
- Correction round: report only finding IDs whose state changed; summarize unchanged open IDs separately.
- Return one consolidated correction packet: exact head/SHA, unmet IDs, precise edits, evidence to recapture, preserved holds, owner, and timebox.
- Next owner action: <ready for owner action | correction | gather named evidence>; approval/merge/deployment authority remains separate.

## Dispatch evaluation

Apply [observability.md](../../delivery-orchestrator/references/observability.md): C correctness / B boundary discipline / E evidence reliability / M maintainability / A autonomy, each 0–3 or not assessed, with brief evidence. Keep initial scores and correction outcomes separate.

- Attempt / evaluator IDs and role: <IDs>; assessment time: <UTC>
- C/B/E/M/A: <scores and reasons>; disposition: <accepted/correction/blocked/canceled/not assessable>
- Timing: <return/acceptance/wait, measured or unknown>; correction rounds: <count>; manual owner interventions: <count or unknown>
- Routing lesson: <one evidenced improvement or none; no overall vendor ranking>
