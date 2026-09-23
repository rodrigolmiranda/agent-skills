# Agent Skills

Reusable skills live under `skills/<name>/SKILL.md`. For new Interchange assignments, start at `skills/interchange/SKILL.md`; workflow, verification, transport and editable profiles are routed there. Legacy policy/operating-model files in archive/interchange/references apply only to unreconciled assignments. Existing generated views describe that legacy policy until explicitly regenerated.

Use Interchange for cross-house delivery. Workers are bounded leaves unless explicitly designated leads. Preserve other writers' work. Validate protocol changes with `python3 -m unittest discover -s tests`.

Target `test`. Only designated leads and delivery manager may merge, after independent current-head review and green gates. Required approval bypass needs a passing independent Codex PR review, all other requirements and a recorded reason/SHA. Workers never merge. No direct push to protected targets. Other branches/releases remain human-controlled.

Shared portfolio authority is MarvinaMiranda, resolved through local configuration. Do not hardcode another user's checkout path or assume uncommitted central rules exist in a fresh clone.
