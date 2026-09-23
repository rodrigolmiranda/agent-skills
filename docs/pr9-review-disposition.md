# PR9 review corrections

| Review concern | Implementation |
|---|---|
| Circular skill dependency | Interchange accepts any authorized caller; its exchange contract is local. Delivery Orchestrator consumes it. Boundary tests reject required reverse links. |
| Competing packet definitions | Delivery Orchestrator owns the semantic assignment; Interchange binds its revision/digest in an execution envelope. Portfolio formats reference the pair. |
| Portfolio rules in core | Opt-in `adapters/marvinamiranda/` preserves the operational procedure under governing authority. Core skills do not require it. |
| Ambiguous roles filenames | Semantic `roles.md` and execution `profiles.md` have distinct owners. |
| Hand-run sessions | Explicit manual observations retain reported provenance and do not fabricate relay or acceptance facts. |
| Scheduling ceremony | One complete current receipt, incremental changed-item checks, full scans for takeover/scope/stale coverage. |
| Client installation authority | Client-local entrypoints resolve a common approved revision, recorded in the installation manifest. Standalone Interchange is supported. |
| Waiting versus blocked | Five board columns distinguish a progressing owned prerequisite from intervention required. |

The review rejected duplicating principles and rejected the claim that the renderer inherently requires a relay launch: it accepts caller-supplied snapshots. The manual observation command makes that supported path explicit. Installation and product acceptance remain separate from source implementation.
