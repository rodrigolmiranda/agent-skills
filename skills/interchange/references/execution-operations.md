# Agent execution operations

Interchange maintains the operational picture; delivery-orchestrator owns its delivery meaning.

## Capability and session inventory

Keep one shared, evidence-backed inventory of available clients/providers, supported model IDs and reasoning settings, skills, tools, commands, session open/resume routes, capacity and limitations. Record observation time and provenance. Requested settings are not observed settings; unavailable runtime metadata remains explicitly not exposed. Never infer capability from a name or silently substitute a provider. Supply this inventory to the orchestrator, which selects the role/profile based on scope, difficulty, risk and owner preferences.

## Exchange agreement

Before launch, bind job/attempt IDs, sender/receiver, packet revision, owned worktree/resources, supported commands, timeout/output limits, durable question/result paths, callback/ack route and session recovery instructions. The orchestrator supplies scope, authority, acceptance, priorities and stop conditions; Interchange checks that the technical exchange can carry them. Use the existing assignment/question/handover/message templates rather than a second agreement file containing copied decisions.

## Logging and board maintenance

Record dispatch, actual startup, questions, answers, model/route changes, exits, errors, receipts and acknowledgements with timestamps and linked evidence. Know who is doing what and whether that observation is current. Preserve prior attempts and requested/observed identity separately. Correlate and acknowledge returns before forwarding for disposition.

Publish those execution facts into the board owned by delivery-orchestrator after each material event. Update attempt and activity records together: a completed reviewer cannot remain Working because an old attempt says running. Do not turn process exit into accepted delivery, calculate quality scores, infer readiness or overwrite the orchestrator's plan/priority/blocker disposition. An unresolved mismatch is visible as stale/unreconciled, with an owner; never silently present it as live truth. Board publishing failure is an operational error to repair or report, not a reason to stop unrelated product work.

## Communication recovery

Diagnose missing startup, duplicate/late callbacks, bad correlation, stale session handles and failed delivery within the existing exchange authority. Safe idempotent notification retries may reuse the event identity. Reconcile uncertain process/write state before any relaunch; never duplicate a writer or replay product mutations to repair messaging. A new executor, changed provider/effort, scope, privilege or material deadline needs orchestrator disposition and any required owner authority.

Record the symptom, evidence, cause, repair and prevention in the existing improvement record. Fix reusable communication defects at their owning adapter/protocol; product workflow decisions return to delivery-orchestrator. Use native delegation directly where supported; do not add a relay merely to make a native exchange resemble an external process.
