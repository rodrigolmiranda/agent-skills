# Agent Skills

Reusable skills live under `skills/<name>/SKILL.md`. Interchange design and runtime scope are described in `skills/interchange/references/operating-model.md`; configured policy lives in `references/policy.json`. Keep generated workbook/diagram views aligned with that policy.

Use Interchange for cross-house delivery. Workers are bounded leaves unless explicitly designated leads. Preserve other writers' work. Validate protocol changes with `python3 -m unittest discover -s tests`.

Target `test`. Only designated leads and delivery manager may merge, after independent current-head review and green gates. Required approval bypass needs a passing independent Codex PR review, all other requirements and a recorded reason/SHA. Workers never merge. No direct push to protected targets. Other branches/releases remain human-controlled.

Shared portfolio authority is MarvinaMiranda, resolved through local configuration. Do not hardcode another user's checkout path or assume uncommitted central rules exist in a fresh clone.
