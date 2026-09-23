---
name: interchange
description: Execute authorized assignments through Codex, Claude Code or external sessions. Use for dispatch, startup verification, durable messages, callbacks, execution observations and communication recovery.
---

# Interchange

Execute an authorized assignment supplied by a human or coordinator and return correlated evidence. This skill works independently of any planning skill. It does not decide product scope, priority, review allocation or acceptance. Repository permissions and the supplied authority remain binding.

## Execute and return

1. Read the supplied semantic assignment and its authority, revision, owned surface, acceptance and holds. Missing or contradictory scope returns to its owner; do not invent a plan.
2. Resolve the selected authorized profile through [profiles](references/profiles.md). Record requested versus observed model and effort; never silently substitute a provider or model.
3. Bind the assignment to the [execution envelope](templates/assignment.md). Resolve portable records through [workspace](references/workspace.md), then use [transport](references/transport.md) for the chosen route.
4. Apply the [exchange contract](references/communication.md) to startup, questions, answers and returns. Verify startup rather than treating a PID or queued message as execution.
5. Correlate a return with its registered attempt and artifact digest, acknowledge receipt once and deliver evidence to the assignment owner. Exit, receipt and acceptance are distinct.
6. Before yielding, record actual process state, supervisor, deadline and next return owner. Never claim automatic continuation without a verified wake route. Unsupervised work requires repair or an explicit blocker.

Use [execution operations](references/execution-operations.md) for capability inventory, technical agreements, logs, board publication and communication recovery. The caller owns board dispositions and evaluations; Interchange records execution facts. Use [setup](references/adoption.md) for installation and manual observations.

Keep personal preferences and product-specific rules in explicit adopter configuration. Active attempts retain their recorded resources and protocol. Neither this skill nor a transport receipt grants merge, publication, deployment or expanded scope.
