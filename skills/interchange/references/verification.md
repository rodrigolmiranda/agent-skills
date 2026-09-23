# Proportionate verification

The writer owns unit/integration checks and relevant E2E for the changed behavior. The independent reviewer checks whether the target was hit, not merely whether code looks good. Evidence records command, exit, pass/fail/skip counts, source SHA and runtime identity where relevant.

| Trigger | Check | Who |
|---|---|---|
| Simple established component/pattern | targeted behavior proof + ordinary PR review | writer, independent reviewer |
| New pattern / board / calendar / guided branching / dense workflow | UX contract and prototype/mock when needed before UI; planned visual acceptance | UX Designer, Planner adopts decisions |
| Several connected UI slices or meaningful journey change | UX and functional seeded navigation checkpoint | UX Reviewer + Journey Tester may be one bounded session with separate verdicts |
| Milestone/release acceptance | complete critical journey, permissions/error/recovery states, relevant devices | independent Journey Tester; UX review if not already proven at that source |
| No UI change | code/contract/data proof; no ceremonial screenshot | writer + PR reviewer |

UX review includes navigation/menu/page/action placement, content hierarchy, labels, task sequence, keyboard/focus, mobile, empty/loading/error/denied states and established theme. Guided questionnaires must demonstrate progress, sequencing, previous-answer context and any promised adaptive behavior; do not infer adaptivity from attractive pages. Challenge the Planner if the approved design contradicts the stated product outcome.

Use seeded realistic synthetic data. Record local/deployed environment and exact build; a fast local environment is appropriate when its dependencies, auth and configuration reproduce the acceptance contract. An SDK synthetic harness is not signed product proof. UI review and navigation testing may share one run to reduce setup cost, while keeping functional and visual judgments separate.

Report annotated or clearly captioned screenshots of what was actually inspected. After repair, capture the affected state again at the relevant sizes and verify it visually. Keep before/after proof; do not require a full journey rerun for a narrow visual fix. A screenshot with target rows clipped is not evidence of those rows.

PR review returns one consolidated list: introduced defects/target blockers, missing mandatory proof, and nonblocking future improvements. Blockers cite the controlling requirement and concrete failure. Unrelated findings become backlog items; no surprise gate. Corrections re-open only the changed surface and justified impact. For asynchronous behavior, proof must wait for the operation under test, not an already-true assertion; mutation proof is useful for disputed tests, not mandatory ceremony for every test.

A test-only proof repair needs focused tests and required hosted policy; it does not automatically invalidate retained backend/runtime evidence. Full CI runs at the integrated implementation boundary and again only when code/risk/policy warrants it. Draft checks that skip the full lane never count as full acceptance. Decide draft→ready explicitly to run the real gate; green gate, independent pass, merge and deployed acceptance are different states.
