> Historical compatibility reference. Not active instructions. New work uses [Interchange](../../../skills/interchange/SKILL.md).

# Installation and portable configuration

Repository layout supports several independently discoverable skills: `skills/interchange` and `skills/caveman`. Caveman is bundled unchanged from the MIT-licensed source recorded in its `UPSTREAM.json`, including the licence. A clone therefore has the required dependency without another download.

For Codex, use a symlink or copy of each skill directory under the user's configured skill directory (normally `~/.codex/skills`). Do not overwrite an existing skill. If Caveman already exists, retain it after checking that it has the expected clarity and exact-evidence boundaries. A local symlink automatically sees repository changes; use a tagged checkout or copy when a stable installed version is required.

Other houses need not discover Codex skills automatically. The Interchange packet explicitly supplies the resolved Caveman instructions and required governance excerpts/references. Configure each CLI's own supported skill discovery if desired; never assume a Codex installation also installs Claude, Grok or OpenCode skills.

Personal configuration belongs under `~/.config/interchange/`: local source-root mappings, profile overrides, account/usage-pool bindings and approved spending settings. Durable local execution state belongs under `~/.local/state/interchange/`, including assignment attempts, session references, events and checkpoints. These are proposed runtime locations; no runner currently loads them. Secrets remain in each house's existing credential store, not these files or prompts.

Adopting shared repositories should have a short `AGENTS.md` and a `CLAUDE.md` importing it. Keep company rules and repo commands there, not a developer's personal model preference or absolute folder path. Governance source identity and adopted revision go in `governance.lock`; resolve local checkout location through personal configuration. If source changes are uncommitted, record that explicitly and use content digests for a transport snapshot. A copied projection must retain revision and owning authority.

Clone `https://github.com/rodrigolmiranda/agent-skills` with an account granted access to the private repository. No GitHub ruleset is installed by this package. Rodrigo's local Codex installation links `~/.codex/skills/interchange` to this source; his existing Caveman installation is preserved. Other developers install explicitly as described above. To use the source before a client refresh discovers the skill, explicitly reference `skills/interchange/SKILL.md`; this uses skill instructions and the tested completion helper, not an autonomous runner.
