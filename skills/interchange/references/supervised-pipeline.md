# Supervised return pipeline and portable ownership

Use this contract for an explicitly authorized automatic worker-return pipeline, a supervisor transfer, or recovery of missing transitions. The caller supplies accepted scope, permitted publication target and reviewer selection. Neither process exit nor this mechanism grants acceptance or merge authority.

## Ownership and neutral inbox

The private relay database must be accessible to the supervisor host. Register a project route before binding new pipeline attempts:

```sh
python3 scripts/relay.py --state "$STATE" register-project --project "$PROJECT" --route codex-queue --coordinator "$COORDINATOR"
python3 scripts/relay.py --state "$STATE" bind-attempt --project "$PROJECT" --generation 1 --job "$JOB" --attempt "$ATTEMPT"
```

Register the attempt normally first. Its original route remains immutable provenance; a bound project's current generation controls delivery. Transfer with the observed generation:

```sh
python3 scripts/relay.py --state "$STATE" transfer-project --project "$PROJECT" --expected-generation 1 --route codex-queue --coordinator "$INCOMING"
```

Python callers use `register_project`, `bind_attempt`, `require_current_generation`, and an `acquire_managed_action` / `release_managed_action` pair around each managed write. `takeover_roster` records notice state; `mark_takeover_notice` records delivery and later acknowledgement separately. Managed actions fence publication/dispatch against transfer. A transfer refuses while an action is held; an overdue action is inspected before release, never automatically stolen. This does not prevent an old chat from running arbitrary shell commands outside these helpers. Restrict publication credentials to the supervisor process and reconcile old automation ownership.

Re-notify unacknowledged event IDs through the current project route; acknowledge with the current generation and coordinator. Never repeat the worker or publication to recover a lost notification. Native messageable workers receive takeover notice immediately; non-messageable headless workers keep running and receive the notice in their next packet. Record those different states honestly. Verify an actual receiver acknowledgement, not just queued delivery. Cross-machine use needs reachable storage and a supported wake adapter; the local SQLite file is not a network service.

## Monitor and board

Run the monitor as a separate supervised process; the dashboard stays read-only:

```sh
python3 scripts/monitor.py --state "$STATE" --project "$PROJECT" --output "$PROJECT_ROOT/monitor.json" --interval 60 --overdue-seconds 300
```

Choose the overdue interval for the assignment/transport; a long test is not necessarily stalled. Add `--retry-delivery` only for the supported bounded retry of definite delivery failures. Uncertain or queued-but-unacknowledged sends require reconciliation, not blind resend. The project dashboard reads the sanitized `monitor.json` beside `continuation.json`, showing observed time and recovery owner. It does not emit owner notifications. Owner notification remains explicitly unavailable until a separate channel is configured and tested. A visible warning is not proof the owner was alerted.

For full activity coverage add `--activities LEDGER.json`: the record must match `project_id` and enumerate `workflow_steps`, with `owner`, `expected_transition`, and `deadline_at` for each unfinished activity. Use the existing continuation as that ledger when it carries these fields. Without it the monitor covers registered attempts/events only and cannot claim all approved work was checked. Track every job, review and expected transition in the authoritative records. Preserve worktrees on interruption; do not auto-commit dirty work or use commit count as the only progress signal. A known required-gate failure routes to correction; diagnostic review can be separately authorized. Never edit an acknowledged result to correct its claims—write a linked disposition/revision.

## CI cancellation

`watch_pr_checks.py` reports cancelled/stale registered runs as incomplete (exit 2), not failed or green. It is not a merge gate. For a verified concurrency cancellation, `retry_cancelled_ci.py --policy POLICY.json --state-dir PRIVATE_DIR` accepts an explicit policy containing `repo`, `pr`, `head`, `run_id`, `reason`, and `retry_authorized: true`.

An optional `lane_workflow_ids` list narrows the lane to workflow IDs whose actual concurrency configuration was verified; omitting it conservatively treats the repository as one lane. The retry helper checks the live open PR/head and cancelled run, waits while repo runs are active, and stores intent before requesting one rerun. An uncertain API result returns to reconciliation instead of automatic repetition. Cooperating callers share the same state directory; the local lock cannot prevent unrelated GitHub actors from launching CI. Do not authorize retries for intentionally cancelled or superseded work. Respect actual repo concurrency configuration and re-query every merge gate afterward.

## Security boundaries

Worker command permissions alone are not an OS sandbox. Pipeline publication requires the supported worker-isolation preflight, including distinct credentials and a denied publication probe; unsupported configurations fail visibly. Do not silently run a privileged supervisor or provision identities to satisfy it. Reviewer launch must disable owner-browser integration and isolate credentials/profile; no secrets belong in manifests or portable artifacts. Headless execution is a separate supervised attempt and must prove actual activity, not just a PID.

See the process template and runner's opt-in contract for concrete publication/reviewer configuration. Existing jobs without that contract remain compatible; they do not acquire automatic GitHub writes.
