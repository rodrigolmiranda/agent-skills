# Proportionate verification

Each development dispatch includes relevant unit/integration tests and a simple navigation smoke check when its change has a UI. Broader validation is assigned explicitly in the approved plan rather than repeated at every layer. The independent reviewer checks whether the target was hit, not merely whether code looks good. Evidence records command, exit, pass/fail/skip counts, source SHA and runtime identity where relevant.

| Trigger | Check | Who |
|---|---|---|
| Simple established component/pattern | targeted behavior proof + ordinary PR review | writer, independent reviewer |
| New pattern / board / calendar / guided branching / dense workflow | UX contract and prototype/mock when needed before UI; planned visual acceptance | UX Designer, Planner adopts decisions |
| Several connected UI slices or meaningful journey change | UX and functional seeded navigation checkpoint | UX Reviewer + Journey Tester may be one bounded session with separate verdicts |
| SDK development cluster complete | Integration in the plan-selected multiple real consumers, even before milestone exit; bind exact package/source/consumer versions | independent integration verification |
| Milestone/release acceptance | complete critical journey, permissions/error/recovery states, relevant devices | independent Journey Tester; UX review if not already proven at that source |
| No UI change | code/contract/data proof; no ceremonial screenshot | writer + PR reviewer |

UX review includes navigation/menu/page/action placement, content hierarchy, labels, task sequence, keyboard/focus, mobile, empty/loading/error/denied states and established theme. Guided questionnaires must demonstrate progress, sequencing, previous-answer context and any promised adaptive behavior; do not infer adaptivity from attractive pages. Challenge the Planner if the approved design contradicts the stated product outcome.

Use seeded realistic synthetic data. Record local/deployed environment and exact build; a fast local environment is appropriate when its dependencies, auth and configuration reproduce the acceptance contract. An SDK synthetic harness is not signed product proof. UI review and navigation testing may share one run to reduce setup cost, while keeping functional and visual judgments separate.

Report annotated or clearly captioned screenshots of what was actually inspected. After repair, capture the affected state again at the relevant sizes and verify it visually. Keep before/after proof; do not require a full journey rerun for a narrow visual fix. A screenshot with target rows clipped is not evidence of those rows.

PR review returns one consolidated list: introduced defects/target blockers, missing mandatory proof, and nonblocking future improvements. Blockers cite the controlling requirement and concrete failure. Unrelated findings become backlog items; no surprise gate. Corrections re-open only the changed surface and justified impact. For asynchronous behavior, proof must wait for the operation under test, not an already-true assertion; mutation proof is useful for disputed tests, not mandatory ceremony for every test.

A test-only proof repair needs focused tests and required hosted policy; it does not automatically invalidate retained backend/runtime evidence. Full CI runs at the integrated implementation boundary and again only when code/risk/policy warrants it. Draft checks that skip the full lane never count as full acceptance. Decide draft→ready explicitly to run the real gate; green gate, independent pass, merge and deployed acceptance are different states.

## Plan the validation boundaries once

The plan maps each accepted outcome to its evidence, owner and checkpoint. Task/PR checks cover the changed behavior; SDK contract proof includes an independent test consumer when relevant; the completed SDK development cluster gets a planned multi-consumer integration checkpoint; milestone/plan acceptance verifies the promised integrated outcomes. These are technical verdicts by reviewers/coordinator, separate from owner approval and merge authority.

Reuse valid earlier evidence at later boundaries when source, package, consumer wiring and environment still support the claim. Independent review may inspect/reproduce targeted evidence; it need not rerun every suite or journey. Re-run for a changed contract/integration/environment, a concrete risk, failed proof or applicable repository requirement. Explain the reason; passing the same test in three phases is not three different acceptance criteria. A consumer harness can prove the SDK contract but cannot prove adoption in a named product. Product adoption remains unverified until its actual integration is proven. Name the consumers and scenarios in the plan; “multiple consumers” does not authorize testing every portfolio repository.

For Claude-led navigation that needs credential entry, use the bounded Codex helper in [communication.md](../../interchange/references/communication.md); preserve the same intended browser and explicit ownership transfer.

## Base and CI changes

Update/rebase only for actual overlap, contract/base impact or repository merge policy; record why. A docs-only base change is not an automatic exemption, but avoid gratuitous branch updates and repeated full gates. Classify failures as code, infrastructure, suspected flake or unknown from direct evidence. A retry pass alone proves neither flakiness nor independence from the change. Classification never waives a required gate.
