# Roles and routing

Role describes responsibility; profile selects a currently available model. Percentages are planning aspirations, never quotas.

| Role | Assignment | Default authority |
|---|---|---|
| Planner | current coordinating chat; intake, decisions, sequence, questions, integration, acceptance disposition | owner-approved product scope; no duplicate lead layer |
| Builder | ordinary simple/medium implementation; GitHub mechanics; bounded search/evidence gathering | execute settled outcome; routine conventions; escalate material trade-offs |
| Senior Builder | difficult concurrency/integration/migration or repeated blocked implementation | bounded engineering judgment; owner approves dispatch |
| Architecture/Security Reviewer | new/complex architecture, trust boundaries, high-risk direction | advice/explicit decision proposal; owner approves dispatch |
| PR Reviewer | independent target/quality/evidence review and correction closure | findings/verdict; no new product scope or self-acceptance |
| UX Designer / Reviewer | new interaction guidance/prototype; periodic coherent journey review | accepted pattern and usability criteria; proposals for changed product behavior |
| Journey Tester | real seeded navigation, integrated acceptance, milestone exit | reproduce/report; writer remains responsible for unit/integration/relevant E2E |

Prefer the Builder for roughly 90% of execution, not for unresolved product decisions. A senior is justified by ambiguity/consequence left *within* an accepted contract, not by file count. Architecture/security review is exceptional and early when it can change a design economically.

For a Codex Planner prefer native Luna over Claude for coupled workers; for a Claude Planner prefer native Opus over Luna. DeepSeek is a preferred independent Builder when available. Cross-house workers are not assumed to share a mailbox; the portable relay can route them, but it does not create shared context or collaboration semantics.

Requested model/effort and observed provider identity are distinct fields. Resolve explicit versions first. An approved latest-in-family policy may resolve a newer documented successor before dispatch; record the exact resolution and pin the attempt. Never switch family, provider, billing pool or effort silently because availability changed. Unavailable settings trigger a question or an already-approved fallback. Do not claim current availability from the example profile.

Per-request overrides win, then project profile, then user profile, then example defaults. Reviewer independence means a separate session from the author, not a different vendor. Author can repair UX findings; a UX specialist can be an explicitly scoped repair writer, but another session must verify those repairs.
