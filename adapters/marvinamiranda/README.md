# Portfolio adapter

Load only when project governance explicitly selects this adapter. Governance owns normative principles, authority and delivery-record definitions; these files implement portfolio operational procedures. They are not generic skill defaults.

- [Workflow](portfolio-workflow.md)
- [Procedures](portfolio-procedures.md)
- [Formats](portfolio-delivery.md)
- [Browser sign-in policy](browser-sign-in.md)

Install the adapter as an opt-in part of the same approved release tree, preserving `adapters/marvinamiranda/` alongside `skills/` so relative links resolve. Configure its entrypoint in project routing. Do not copy this folder alone into a flattened skill directory. The two core skills remain usable without it.
