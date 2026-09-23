# Setup and project configuration

1. Install Interchange; install a planning skill when the caller uses one. Read the entrypoint and configure the project's shared coordination root.
2. Record applicable governance, authorized scope and model preferences. Verify available provider commands, tools and return routes; requested settings are not observed identity.
3. The human or coordinator supplies the authorized semantic assignment. When using Delivery Orchestrator, it also owns the scheduling receipt. Interchange registers the attempt, launches the selected executor and verifies startup.
4. Preserve each active attempt's recorded contract and holds. Coordinate any change with its owner; do not silently change running work or replace its execution resources.
5. Verify a bounded round trip: startup, durable question if needed, result artifact, correlated receipt and acknowledgement. Record unsupported routes as unavailable.

Governance retains principles and authority. The human or coordinator owns the workflow; Interchange owns execution operations. Project routing files link to those authorities rather than duplicating their rules. Neither installation nor a successful transport probe grants product-write, merge, deployment or publication authority.

Use [execution operations](execution-operations.md) for logs, board publication and communication recovery. The caller supplies reporting semantics and acceptance decisions. Keep measured results separate from proposed capabilities.

## Hand-run session observations

A manually started session does not need a fabricated relay job. Add its activity to the coordinator's snapshot, then record a supplied observation:

```bash
python3 <interchange>/scripts/record_observation.py <snapshot.json> <event.json>
python3 <interchange>/scripts/dashboard.py --repo <checkout> --snapshot <snapshot.json>
```

Start with [the manual observation example](../templates/manual-observation.json).

The observation names `observation_id`, `project_id`, `workflow_step_id`, timezone-aware `observed_at`, `observer_id`, `observer_role` (`owner` or `coordinator`), `provenance` (`kind: manual`, `source: <report pointer>`) and `summary`. Optional `reported_activity` accepts `status`, `current_action`, `task`, `owner`, `requested_model` and `requested_effort` as bounded text. Reports are retained in `manual_observations` and displayed on the activity; they do not replace the coordinator’s next action or change its board state. The coordinator separately records that disposition. The target activity must already exist. Repeating the identical observation ID is a no-op; reusing it with changed content is rejected. These are reported facts, not proof of live execution, relay registration, receipt acknowledgement or accepted outcome. Never include credentials or raw private transcripts.
