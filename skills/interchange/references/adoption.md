# Adopting the refactor

This revision replaces stacked manager/brain roles with one Planner and bounded executable assignments. It separates configurable routing from portable workflow, and live model supervision from deterministic process supervision.

Existing packets keep their recorded contracts/holds until reconciled; do not rewrite a running worker's requirements mid-attempt. Legacy `policy.json`, `routing.md`, `operating-model.md`, `runtime-adapters.md`, `commands.json`, completion/history references are preserved under repository `archive/interchange/references/`, outside the installed skill. Historical policy tests and generator now explicitly read that archive; reusable protocol helpers remain in the skill. The refactored entrypoint deliberately does not load their house-exclusivity or per-invocation role rules. Do not run legacy dispatch templates as if they implement the current profiles.

Adoption steps:
1. Review the refactor diff and choose/copy a profile; resolve the two host adapters you actually use.
2. Keep organization-specific authority in local project instructions. This portable skill includes the useful generic workflow/templates directly; it requires no external vault or personal checkout.
3. Smoke-test outgoing request, actual final artifact, correlated callback and idle coordinator receipt. Mark unsupported directions honestly.
4. After independent review and owner merge/adoption approval, replace installed entrypoints for new jobs on the verified routes; preserve old attempt records. Never hot-swap a global skill while another coordinator is using it without coordinating.
5. Use the first bounded product assignments as the adoption pilot: one one-PR slice, unrelated-bug triage and question/resume when they arise naturally. Compare accepted-result time, manual relays, correction rounds and measured usage; refine the workflow from evidence. Unsupported routes stay manual or blocked, never implied supported by installation.

## Governance alignment proposal

The source portfolio already has proportional entry paths for new products, large/medium/small features, bugs and incidents. The missing operational piece is a continuation/WIP reconciliation and a runnable dispatch/return contract, not another complete governance hierarchy.

Suggested adopter change: add continuation intake (live backlog/PR/runtime/dirty-state reconciliation), BAU prioritization rules, standalone issue/PR path, explicit nonblocking bug backlog classification, periodic UX+journey trigger table, one Planner default, receipt-auto-proceed and deterministic callback supervision to the existing method/orchestration authorities. Carry the restartable templates and exact-head outcome review forward. Replace overlapping live-supervisor-only/model-reservation clauses through an explicit adoption revision. Keep merge/deploy/security holds local and unchanged.

This is a proposal for that governance change, not an edit or claim of central adoption. When governance changes, refactor the portable skill deliberately; do not make public consumers resolve organization-private references. Universal workflow is maintained here; adopters own additional constraints and their version lock.

Observability adoption belongs in the existing GOV-0020 quality/routing and continuation sections, not a new governance hierarchy: stable project/agent/attempt IDs; timestamped comparable reports; measured timing plus the existing five evaluation dimensions; coordinator transfer with ownership reconciliation; and exact-head GitHub provenance. Extend delivery templates with the small continuation index and report view. Keep AGENTS.md as a routing pointer. The portable [observability contract](observability.md) carries the generic behavior; the central amendment is still pending, not silently adopted by this refactor.
