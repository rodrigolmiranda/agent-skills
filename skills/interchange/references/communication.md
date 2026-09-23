# Worker communication

Use [message templates](../templates/messages.md) for dispatch, questions, answers/resume, return and correction. Every message names project/job, packet revision, attempt, sender, recipient and the durable record. Native subagents and external workers follow the same record contract; transport differs. Do not require workers to infer instructions from an inaccessible chat history.

## Understand → record → act → return

1. **Planner prepares.** Put the outcome, accepted decisions, required reading, owned surface, proof, stop conditions and return route in the assignment. Point to the question file and handover. Mark any proposal or permission gate explicitly.
2. **Worker understands.** Read the packet and referenced sources, verify baseline/ownership, and record current versus intended behavior, acceptance-to-proof mapping and material gaps in the startup receipt. A short acknowledgement confirms receipt, not acceptance of a design or permission to exceed scope.
3. **Worker proceeds or asks.** If clear and authorized, record and send “all clear — work starting” with the actual local start timestamp, UTC offset and timezone name, then proceed immediately without waiting for acknowledgement. The Planner logs the reported start separately from notification receipt time. A startup message confirms understanding and no open questions; it does not claim acceptance. If an explicit startup gate or material gap exists, write a question before dependent work. Continue only safe independent work already authorized by the packet.
4. **Planner answers durably.** Verify the evidence and answer within existing authority. Settle material choices through questioning before plan approval; ask the owner afterward only when a genuinely new decision appears. Default new behavior choices to configurable when practical within approved scope; ask if configurability is disproportionately large, costly, incompatible or materially changes the plan. If the owner must decide, present that question to the owner and record the actual answer in the file; silence or elapsed time is not consent. Update affected scope/acceptance in the plan and packet before releasing changed work.
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

## Browser sign-in assistance

Owner operating rule: when Claude is the tester, delegate entering a browser username/password to Codex, including local synthetic accounts. This is a routing rule, not a claim that every Claude installation is technically unable to type credentials. If the Planner is Codex, it may perform the bounded action; if the Planner is Claude, request a Codex sign-in helper using a supported dispatch/return route. This is a non-coding operational helper, not a new product slice or PR.

The request records the authorized URL/environment/account alias, secure credential source (never the values), intended browser/session, return route and success indicator. Claude pauses control of that browser/profile and hands ownership to Codex. Codex verifies the destination and scope, enters only the authorized credentials using the approved local/secret mechanism, and returns sign-in success/failure plus browser identity. It does not change roles, grants, registration, credentials or application data, extract tokens/cookies, or export an authenticated profile. Do not capture credentials in screenshots, transcripts or evidence. Human-only challenges or missing authorized access return a precise blocker; no authentication bypass.

Use the same browser session only if both tools can safely control that supported surface in sequence. A login in an inaccessible separate profile is not a handback. After Codex releases browser ownership, Claude resumes the planned test. If a compatible Codex helper/return route/browser is unavailable, hold only the sign-in-dependent work and ask the Planner to arrange it; do not claim cross-client credential handoff is tested until a real bounded trial proves it.
