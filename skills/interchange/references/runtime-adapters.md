# Runtime adapter and supervision contract

Read this file before launching an external Claude, Grok or OpenCode assignment.
These are required transport boundaries. Skill text does not implement the runner.

## Manager supervision

Before dispatch, register the packet/attempt, delivery manager, process and provider
session IDs, worktree, output sink, start time, expected duration, review/hard
deadlines, usage ceilings when observable, and the next wait mechanism.

After dispatch, the manager owns supervision until one of these is true:

- the attempt reaches a terminal lifecycle state and its handback is collected;
- another live supervisor explicitly accepts the complete checkpoint and handles;
- the owner pauses the delivery after active processes are stopped or assigned to
  a durable scheduler that has a verified wakeup path.

Keep the manager turn active while workers run. Use actual blocking process/event
waits in bounded intervals and continue after each timeout. A saved session ID,
future-tense promise, status note, or expected completion time is not supervision.
Do not send a final response while an owned worker is active. If the interface
cannot retain the turn or provide a verified wakeup, expose that limitation before
dispatching unattended work.

Waiting itself should not prompt the worker. Drain events mechanically and surface
only lifecycle changes. Do not ask the worker whether it is done before the review
deadline. At the review deadline request progress evidence once; apply the hard
deadline even without a reply. Keep user-facing progress updates compact and no
more than necessary to avoid leaving the user without visible activity.

If the manager, host, network or app stops, the process may continue, terminate,
or become unreachable depending on its transport. On return, classify it as
`supervision_lost`; inspect the process tree, provider session, worktree and output
artifacts before resuming or assigning another writer. Never infer termination
from silence.

A provider parent exit does not prove its subagents stopped. Before transferring a
writable assignment after any abnormal exit, require all three independent checks:

1. the recorded parent PID and every descendant/provider process are absent;
2. no process command or current working directory references the worktree;
3. the provider's background-agent/task registry has no active entry for the
   assignment or session.

Then inspect worktree status, locks and durable output. Record the exact checks and
timestamp. Any uncertain or positive signal keeps ownership with the prior writer
and blocks a duplicate writer until the lead resolves it.

## Machine-owned output

The adapter owns stdout/stderr and provider event streams. Drain raw output to a
bounded local artifact outside manager context. Emit only state transitions,
session/process IDs, usage counters, warnings, exit state and the final assistant
result. Enforce output-size limits without blocking the child process.

Extract the provider's final assistant channel mechanically. Validate it against
`final-response.schema.json`, then bind the exact completion marker outside model
formatting when the provider supports a structured channel. Prompt wording is not
a substitute: fenced JSON, backticked markers and object-shaped `evidence` remain
invalid. Exit zero with no final assistant response, `finish=tool-calls`, cancelled
execution or a missing/mismatched marker is incomplete.

Classify post-completion hook failures as environment warnings when the valid final
result and exit state were already durable. They do not erase a completed attempt.

## Packet and permission preflight

Transport the complete packet and every required coordination file inline, as an
attachment, inside the worktree, or through an explicitly authorized directory.
Attaching an index does not authorize later reads of referenced external files.

Build argv arrays and pass each prompt/path as one literal argument. Before model
execution, verify the installed CLI's exact argument order, model/effort identity,
attachment access, required tools and every exact command including flags and
composition. Abort on unknown or unmappable allow/deny rules. Advertised tool
visibility and actual deny enforcement are separate evidence; run a harmless
negative permission test before trusting a restrictive profile.

Generate permission rules from packet commands. Agents issue one approved command
per tool call unless the exact composite expression is authorized. Claude uses
Edit/Write for authorized file creation; shell redirection, `touch`, moves and
composites require explicit permission. Acceptance gates use an argv runner,
repository checked-status wrapper, or proven `pipefail`; truncate captured output
after completion rather than piping a gate through `tail` or `grep`.

## Provider notes

### OpenCode

Place the positional prompt before all variadic `--file` attachments. Attach the
complete packet, not only a retry note. Treat exit zero after `finish=tool-calls`
as incomplete. Resume only within the attempt watchdog and only when the installed
CLI demonstrably continues to a final assistant response.

For DeepSeek V4.1 Flash, require the exact provider code
`opencode-go/deepseek-v4.1-flash` and the selected `high` or `max` variant in both
the request and observed session metadata. A mismatch or unavailable route
terminates the preflight. Reroute through another approved house; V4 Pro, V4 Flash
and the vision-exp variants are different models, not fallbacks.

The provider renamed this code from `opencode-go/deepseek-flash`, which
`opencode models` no longer lists. Read the code as version-bearing now: the
`v4.1` in it is what distinguishes the approved model from `deepseek-v4-flash`,
so a packet must pin it in full rather than matching on a prefix.

### Grok

For a read-only reviewer, use the trial-validated `auto` permission mode with
explicit mutation denies only after the negative permission test passes. Abort on
any unmappable `--tools` entry. `dontAsk` is not a verified reviewer profile.

Never expose `streaming-json` directly to manager context. Drain NDJSON to disk.
Treat `grok export` as Markdown unless the installed CLI proves a JSON mode; save
it with `.md` and mechanically extract the last `## Assistant` block.

### Claude

Preflight exact Bash expressions. Direct the worker to use first-class Edit/Write
for authorized files and one approved shell command per call. Prefer a fresh,
compact session for deterministic micro-fixes; resume a large session only when
retained reasoning materially reduces risk or rediscovery.

Treat repeated automatic compaction without material artifact progress as
`autocompact_thrashing`, a context/transport failure rather than a code failure.
After two consecutive auto-compactions without a changed artifact, new evidence or
a completed gate, checkpoint and stop before a third. Record turns, wall time,
input/output/cache/reasoning counters and provider-reported cost when available.
Retry once with a fresh narrow packet and a larger bounded context only when the
task truly needs it; do not resume the thrashing session. Before retry or transfer,
apply the parent/descendant, worktree-holder and Claude background-agent registry
checks above.

## Watchdogs and concurrency exceptions

Every packet has wall-time and turn ceilings. Add token/cost ceilings only when the
adapter exposes timely counters and the selected account/pool semantics are known.
Stop on a deterministic blocker rather than spending the remaining ceiling.
Record input, output, reasoning and cache counters separately when available.

House exclusivity remains the default. A lead or manager cannot waive it. An owner
may create a time-bounded journalled exception naming the house, trigger, delivery
manager(s), assignments, start/expiry, occupancy evidence, isolated change
surfaces, reason and revocation condition. Probe occupancy before launch. Expiry
restores the default immediately; an exception grants neither extra spending nor
overlapping write ownership.
