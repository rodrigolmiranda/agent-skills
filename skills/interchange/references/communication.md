# Worker communication

Use [message templates](../templates/messages.md) for dispatch, questions, answers/resume, return and correction. Every message names project/job, packet revision, attempt, sender, recipient and the durable record. Native subagents and external workers follow the same record contract; transport differs. Do not require workers to infer instructions from an inaccessible chat history.

## Understand → record → act → return

1. **Planner prepares.** Put the outcome, accepted decisions, required reading, owned surface, proof, stop conditions and return route in the assignment. Point to the question file and handover. Mark any proposal or permission gate explicitly.
2. **Worker understands.** Read the packet and referenced sources, verify baseline/ownership, and record current versus intended behavior, acceptance-to-proof mapping and material gaps in the startup receipt. A short acknowledgement confirms receipt, not acceptance of a design or permission to exceed scope.
3. **Worker proceeds or asks.** If clear and authorized, proceed without waiting for ceremonial confirmation. If an explicit startup gate or material gap exists, write a question before dependent work. Continue only safe independent work already authorized by the packet.
4. **Planner answers durably.** Verify the evidence and answer within existing authority. If the owner must decide, present that question to the owner and record the actual answer in the file; silence or elapsed time is not consent. Update affected scope/acceptance in the plan and packet before releasing changed work.
5. **Planner resumes precisely.** Send the resolved IDs, answer-file revision and permitted next action. Worker re-reads them, marks incorporation in its receipt, and proceeds. A new external invocation gets a new attempt ID, linked to the previous attempt, even when reusing the same provider session.
6. **Worker returns.** Update the handover with full head/artifact identity, acceptance map, actual checks, gaps, resource state and next owner. Send a compact pointer. Worker-complete is not independent acceptance.
7. **Reviewer and Planner close.** Review uses the approved packet and answers, not only the PR prose. Corrections are one durable finding-to-action packet; the worker returns evidence against those IDs. The Planner records disposition and reconciles GitHub.

## Questions cannot live only in messages

Use one question file per job with numbered entries, or a directory with one file per ID. Batch related questions. Each question must contain verified context, the precise decision, governing requirement, options with consequences where meaningful, recommendation, blocked actions, safe independent work and decision owner. A single factual clarification need not invent multiple options.

States: **open → needs evidence (when applicable) → answered → incorporated**. An answer requesting more investigation leaves the decision unresolved. Record timestamps, answer provenance and the resulting packet revision. Superseded answers remain identifiable; do not erase the history.

Write the question first, then send a question event with its path/URL and IDs. Add the blocked state, next owner and last notification receipt to the handover. The event is a notice to read the record, not the only copy of the question. If a worker asks in chat first, record it and link the file before answering/releasing dependent work. The Planner may transcribe a direct owner answer, identifying its source rather than pretending the worker decided it.

A waiting worker holds no model open merely to poll. Persist its state and exit/idle under the provider's supported lifecycle. The Planner or supervisor owns notification and deadlines. Failed or uncertain delivery is reconciled through [transport.md](transport.md); it does not authorize guessing an answer or creating a competing writer. Status reports surface open question IDs and the responsible decision owner.

## Evidence and delivery rules

Use a shared durable path or an accessible artifact URL. Before hashed relay delivery, freeze a compact event artifact for that revision; later edits to the working question/handover use a new snapshot/event ID. Do not mutate a queued artifact and invalidate its digest. Record queued versus acknowledged separately.

A receipt says “received”; a release says exactly which gate or work is authorized. A worker result never grants approval. Requests for extra permissions, paid/model escalation, scope changes or runtime changes retain the actual authority boundary. Corrections and answers must be discoverable from the continuation index so a fresh coordinator can resume without rereading transcripts.

Message size should be enough to route and act: outcome/state, changed IDs, evidence link, next owner. Keep logs and long explanations in the linked file. No repeated status pings, duplicate questions already answered in the packet, or separate approval for routine implementation choices.
