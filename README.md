# Agent Skills

Personal reusable skill source. Interchange is the first package in `skills/interchange`.

- [Operating design](skills/interchange/references/operating-model.md)
- [Configured rules and model profiles](skills/interchange/references/policy.json)
- [Development routing instructions](skills/interchange/references/routing.md)
- [Decision diagrams](docs/interchange-decisions.md)
- [Installation and Caveman dependency](skills/interchange/references/installation.md)
- [Completion protocol](skills/interchange/references/completion.md)

Source: [rodrigolmiranda/agent-skills](https://github.com/rodrigolmiranda/agent-skills), private repository. The skill, strict completion validator and provider-adapter contract exist. A live CLI supervisor, stream adapter, automatic callback transport, cancellation, cost enforcement, house reservation enforcement and merge enforcement remain future implementation stages. CLI send/resume smoke tests do not prove those capabilities.

The [workbook](outputs/interchange-design/interchange.xlsx) presents profiles, routing, monitoring and governance. Its adjacent Node script refreshes the existing workbook from policy using `@oai/artifact-tool`; supply that dependency through your environment. Mermaid decision diagrams live under `docs/`.
