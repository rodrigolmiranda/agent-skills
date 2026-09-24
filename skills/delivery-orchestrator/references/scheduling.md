## Reassess safe parallelism; reuse useful context

**Scheduling gate.** Run at startup/resume, after every dispatch or delivered result, every worker return/question/failure, review disposition, dependency or ownership change, and before yielding. The approved delivery scope defines the universe, not the first ten board cards or the current worker count. Use the adopted task/dependency authority: GitHub when adopted, otherwise the programme’s file/document backlog. Enumerate all unfinished items and children; paginate API sources, or traverse the declared document index. Record source kind, retrieval time and stable IDs. Roadmap/unapproved items remain outside dispatch authority and are identified separately. Refresh only changed prerequisites after the initial complete pass; an unverified item is not a verified blocker.

For each item record one disposition: active, dispatched, dependency-blocked, conflict-blocked, capacity-blocked, authority-held, or coordinator-action. Include the exact blocker/dependency/resource and evidence pointer, resolution owner and next event. Unknown readiness becomes coordinator-action with a concrete next check, never a blanket blocked label. Do not stop the scan after finding one ready task or several blocked ones.

Select a maximal safe set: after each selected assignment, no other ready authorized item may remain unselected without a named conflict or measured capacity limit. This does not require an optimal graph algorithm. Respect task dependencies, file ownership, shared databases/ports/test resources, reviewer independence, model authority and actual provider capacity. Prefer coherent PR-sized outcomes; isolate conflicting integration steps rather than serializing unrelated work. Never manufacture tasks to occupy workers or bypass an explicit hold.

Dispatch the selected set and verify startup. Record failures and reassess other ready items immediately. A launch/PID alone is not execution proof. Prefer an idle agent with relevant context and appropriate role/model; never use a writer as its own independent reviewer. Native Codex models use native delegation; external-provider routes use the supported transport. Capacity failures are evidenced constraints, not a permanent one- or two-worker policy.

Persist the compact decision using [scheduling.json](../templates/scheduling.json): complete source ID coverage, dispositions, active/selected jobs, evidence-backed exclusions, and next wake owner. The receipt links GitHub and artifacts rather than copying issue bodies. Before yielding run `scripts/check_schedule.py <receipt> --before-yield`; fix missing coverage or unexplained ready-idle work. The checker verifies record consistency, not the truth of dependencies, safe ownership or actual execution: those remain the coordinator's responsibility. If the source cannot be queried, record that failure and the recovery action; do not certify complete coverage.

Completion criterion: every approved unfinished item is accounted for, every safe ready item is active/dispatched or has a specific evidenced exclusion, and each remaining coordinator action is completed or has a verified wake/owner decision. Reports show eligible, running, dispatched, blocked and unassessed counts. Every return can release several jobs; re-evaluate the whole ready set, not only the returning worker's successor. This gate adds no owner approval and no mandatory worker count.

## Event-to-schedule closure

Every material exchange closes with: consume verified event → update its disposition → recompute the entire approved ready set → check actual overlapping files/contracts/runtime/tests and provider capacity → dispatch every safely eligible assignment → verify startup → record exclusions and next wake. Do not consider only the returning worker or its immediate successor. A free slot is not permission to invent work; one active worker is not a reason to leave independent approved work idle.

Do not apply one generic hold to the whole backlog. Each excluded approved item needs its own applicable authority/dependency/resource evidence; ancestor holds must be checked against subsequent releases. Unknown readiness is an executable coordinator investigation, not a verified exclusion. Reuse the established dependency map and refresh changed facts instead of rereading the entire corpus on each event. The scheduling receipt and board must agree on the current decision.

## Incremental checkpoints

Keep one current complete scheduling receipt. At each material event refresh changed items and their dependent/conflicting ready candidates, reuse unchanged verified evidence and revalidate the receipt. Do not reread the entire backlog or create a new plan per return. Rescan fully when scope changes, coverage is incomplete or evidence is stale, and at takeover. Deduplicate identical notifications without inventing a new decision. For an active programme, establish the current baseline once; do not recreate historical receipts or interrupt safe running workers. Apply these rules where the workflow is adopted. An explicit owner instruction to defer adoption for a named active programme takes precedence: retain its current process until the owner releases that hold. New programmes use the configured workflow unless the owner specifies otherwise. Never manufacture retroactive receipts.


## Progress checkpoint and repeated waits

At material events and before going idle, maintain the existing `checkpoint` using the receipt template: trigger, current assessment evidence, last meaningful progress and its evidence, unchanged-check count, source query/retrieval time and parent/child inventory evidence, next event and owner. Meaningful progress means a verified startup, delivered artifact, resolved dependency, accepted correction or completed delivery. Polling, republishing the board and updating a timestamp do not reset the count. Preserve the prior checkpoint in linked evidence; increment unchanged checks from it. Never fabricate historical progress when adopting this gate: use the evidenced baseline establishment and label it as such.

Count only coordinator-scheduled or idle reassessments without meaningful progress. Individual CI steps, monitor lines and duplicate callbacks do not increment unchanged checks. Material returns, verdicts, merges and unblocks still trigger scheduling. Reuse unchanged evidence and timestamps; a progress-only notification requires no receipt rewrite. Before relinquishing control, perform the cheap ready-work/verified-next-wake check with `--before-yield`; this is not limited to session termination and does not require new evidence files.

After two consecutive unchanged checks, complete a bounded recovery assessment before another wait: recheck the actual blocker; inspect existing authorized alternatives; reassess independent work across all approved parents and unfinished children, including participating repositories or indexed documents. Record evidence for all three and the next check time. Reuse the recovery assessment until that time or a material change, then refresh it. A sustained genuine external hold may remain waiting under verified supervision; recovery does not authorize a workaround, extra privileges or premature acceptance.

Approved-but-not-ready work requires readiness work. Publish already-authorized dependency requests, resolve known documentation gaps and prepare packets as coordinator actions. Perform these before yielding or record a genuine supervised wait/owner decision. A generic ancestor hold is insufficient: record how it applies to each excluded child and whether a smaller independent outcome is possible. One running worker is valid only when the full receipt explains every other candidate; no minimum or maximum worker count is introduced.

## Writing reservations and acceptance

Track `write_leases` separately from delivery status, with job, owner, concrete surface, state, execution evidence and recheck time. A stopped/returned writer's reservation is reconciled and released once ownership is verified. A review, pending browser proof or open PR does not itself reserve product source indefinitely. Retain separately evidenced runtime/test reservations where needed. Compare actual files, shared contracts and resources before dispatching dependent work; use an explicit base/integration plan when consuming unmerged changes.

A timeout or unknown process never automatically releases a reservation. Inspect the process and callback ownership first; retain an unknown reservation with a bounded recheck while resolving it. The checker rejects overdue held reservations and conflicts referring to released reservations. It cannot prove the process stopped or that two surfaces are independent.

The receipt checker rejects missing progress/coverage provenance, repeated waits without recovery, concrete conflicts without a surface, and a yield with executable coordinator actions lacking supervised-wait evidence. Passing validates supplied records, not completeness of GitHub queries or truth of evidence. Keep safe workers running while correcting a failed receipt.


## Evidence resolution

Declare `source_kind: github` (default) or `files` according to adopted governance. `scope_url` identifies the approved remote scope or local backlog index respectively; the historical field name does not require HTTP for a file backlog. `source_query` links the saved query or document-index traversal record, and `hierarchy_evidence` links the resulting complete inventory. Preserve the same source IDs across sessions; do not copy a GitHub backlog into files to evade its authority.

The checker resolves local evidence against `--artifact-root <machine-local-root>` (default: receipt directory). Relative paths resolve below that root; `artifact://jobs/name/result.md` maps to `<root>/jobs/name/result.md` and cannot escape it. Absolute paths and local `file://` URLs are supported for existing local records. Remote file authorities are rejected. Every supplied local evidence pointer must resolve to an existing regular file, including recovery and supervised-wait evidence. Missing access/file fails the gate; never create empty compliance artifacts. HTTP(S) evidence is not fetched by this checker. File existence does not verify content, freshness, authority or source completeness.

Before classifying a technical choice as an owner wait, apply [supervisor technical decisions](../SKILL.md#supervisor-technical-decisions). Keep supervisor-owned preparation in the executable set.


## Shared surfaces and CI lanes

Reserve concrete hotspot files (registration, interceptors, schema snapshots), contracts and shared runtime/test resources. Separate worktrees do not remove logical conflicts. Plan one writer per overlapping surface or sequence its integration. Distinguish incidental branch ancestry from product prerequisites: an isolated reviewed slice may integrate independently while unrelated stacked work remains held; refresh exact-head proof after integration.

Inspect the repository's actual CI concurrency group and cancellation settings. A repo-wide serial lane is a shared resource, not a reason to serialize independent code or review. A cancelled required run is incomplete, neither green nor proof of a code defect. Only re-request a policy-authorized current-head run when its lane is available; bound retries, preserve intentional cancellation and avoid mutual cancellation storms.

For mechanical reservation checks, add `repository` and literal repository-relative `paths` to held write leases (directory prefixes end in `/`), plus exact shared `resources` identities. The checker rejects overlaps across different jobs. Legacy prose-only surfaces remain compatible but require manual conflict inspection; they are not mechanically proved disjoint.

## Recovery qualification before idle

A receipt with active/dispatched work requires `recovery_route` before `--before-yield` passes. It identifies an independently scheduled heartbeat/supervisor, current coordinator/generation, expiry, maximum action-start latency and a hashed local idle-smoke artifact. Use the Interchange validator and [continuation contract](observability.md#native-completions-and-independent-recovery); do not maintain a second wake policy here. Include native subagent returns in the monitored ledger. A same-turn polling loop or dashboard-only alert is not an independent recovery route. Qualification records are evidence to verify, not a promise that arbitrary host APIs can wake an inactive conversation.
