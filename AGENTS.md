# Agent Skills

Reusable skills live under `skills/<name>/SKILL.md`. For planning, scheduling and acceptance, start at `skills/delivery-orchestrator/SKILL.md`. For execution transport, callbacks and provider profiles use `skills/interchange/SKILL.md`. The two skill entrypoints are the current operating instructions; archived experiment records do not authorize dispatch.

Use Interchange for cross-house delivery. Workers are bounded leaves unless explicitly designated leads. Preserve other writers' work. Validate protocol changes with `python3 -m unittest discover -s tests`.

Target `test`. Only designated leads and delivery manager may merge, after independent current-head review and green gates. Required approval bypass needs a passing independent Codex PR review, all other requirements and a recorded reason/SHA. For an owner-enabled session, apply `skills/delivery-orchestrator/references/coordinator-merge.md`; a pending review request alone is not an additional hold. Workers never merge. No direct push to protected targets. Other branches/releases remain human-controlled.

Shared portfolio authority is MarvinaMiranda, resolved through local configuration. Do not hardcode another user's checkout path or assume uncommitted central rules exist in a fresh clone.

For delivery scheduling and repeated waits, use the installed `delivery-orchestrator` scheduling/progress checkpoint before yielding; this applies equally to Codex and Claude. Workflow rules live in that skill, not this router.

For technical decisions and escalation boundaries, Codex and Claude follow `skills/delivery-orchestrator/SKILL.md#supervisor-technical-decisions`; resolve them before recording an owner wait.

Owner-authorized agent delivery PRs are allowed. Restrictions on dependency/app-bot PRs do not prohibit the declared Interchange publication pipeline. Workers never publish through that pipeline; the authorized supervisor process owns GitHub publication.
