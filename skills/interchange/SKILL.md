---
name: interchange
description: Route judgment and mechanical work across Codex subagents and external Claude, Grok and OpenCode sessions. Use for small tasks too when a faster, cheaper worker yields a net gain; preserves explicit ownership, fixed profiles, supervision and independent acceptance.
---

# Interchange

Use Interchange for any delivery size when orchestration improves accepted-result speed or cost, including one small mechanical assignment. Apply the net-gain test before dispatch so orchestration overhead does not become the work.

Use the primary conversation as delivery manager. Coordination and judgment are separate responsibilities. Sol high is the default brain for product and architecture judgment; escalate unusually large cross-workstream ambiguity to Astra medium. Fable 5.1 medium is an included-plan-only product-ideation brain. A manager on another profile coordinates the delivery but routes interpretive decisions to one of those brains. Verify the active model/effort; loading the skill does not switch it. For manager handover and transport prerequisites, read [operating-model.md](references/operating-model.md). This package is an initial skill and protocol implementation, not an operational process supervisor. Never claim monitoring, cancellation or automatic callbacks are active without testing the actual transport.

## Start

1. Read applicable repository instructions. Resolve central governance through the adopter's `governance.lock` and local path map, not another developer's absolute paths. Read core principles once per relevant revision, then only task-specific rules. Missing required governance blocks the affected work; summaries cannot silently replace unavailable authority.
2. Read [policy.json](references/policy.json) for the approved Interchange personal profile, routing and limits. Read [routing.md](references/routing.md) when selecting development workers: it defines task bands and tie-breaks. These owner preferences do not impose personal subscriptions or model choices on other developers. Record overrides explicitly. Read [operating-model.md](references/operating-model.md) for planning, worktrees, incidents and review boundaries.
3. Ensure Caveman is available according to [installation.md](references/installation.md). Use concise internal prompts and handbacks, preserving exact evidence and its clarity exceptions. Do not change code, PR or product-document language into compressed fragments.
4. Select a named enabled execution profile. Verify available model and effort before dispatch; store requested and observed identity separately. A profile's model does not itself grant a lead role or merge permission. No Luna below xhigh. No external worker subdelegation unless explicitly assigned a lead role with an approved capability profile.

## Delegate

Apply `policy.json` house exclusivity before dispatch. Astra at any effort reserves
Codex globally; Fable 5.1 at any effort reserves Claude globally (currently
approved only at medium). Global means across visible Interchange-managed delivery
managers, projects and roles. Sol high or higher reserves Codex only within work
owned or supervised by the same delivery manager; Opus high or higher does the
same for Claude. Separately managed deliveries may use those houses concurrently.
Managers, leads, workers and reviewers have no exemption inside the applicable
scope. Prefer another eligible house or queue the work. Check both directions:
an exclusive job must also wait for conflicting active jobs. Do not silently
reduce effort or stop user sessions. Read the precise
scope/release rules in [routing.md](references/routing.md). This is not yet a
mechanically enforced cross-process lock.

New-product brainstorming uses Fable 5.1 medium or Astra medium. Ideation authority
does not authorize implementation or extra spend. Fable must pass the existing
no-extra-spending preflight before any headless request.

Before dispatch, separate judgment from execution. Only Sol high, Astra medium and Fable 5.1 medium may receive unresolved interpretation. Use Sol high normally, Astra medium for unusually large cross-workstream ambiguity, and Fable medium for product ideation. Semantic and risk acceptance also uses an independent Sol high brain, or Astra medium for unusually large cross-workstream scope. Terra, Luna, DeepSeek, Grok, Muse, Opus workers and lower-effort Sol profiles receive mechanical assignments based on settled decisions. A coordinator using another profile does not acquire judgment authority.

Give each assignment an ID, revision and unique attempt ID. Include outcome, acceptance, repo URL/ref/base, lead-allocated worktree, exclusive paths, read-only dependencies, fixed profile, governing decisions, allowed tools/actions, expected seconds, deadlines, stop/escalation conditions and return format. A mechanical packet must make every behavior choice objective: name the contract or expected transformation, allowed variance and evidence required. If two valid implementations require a tradeoff, acceptance is missing or sources conflict, the worker returns evidence and the smallest question instead of interpreting. Leaf workers cannot delegate, merge, expand scope, weaken checks or invent contracts.

Use fast, low-cost mechanical workers whenever expected startup, supervision and integration overhead still improves accepted-result time or cost. Parallelize objectively testable assignments after interfaces and ownership are settled, using separate non-overlapping write surfaces. Put Muse Spark 1.3 on light mechanical work: repository reading/search, file localization, evidence collection, narrow checks and small explicit edits. Do not fragment work when dispatch and integration would cost more than direct execution.

## Conserve Codex

Treat Codex as protected brain and acceptance capacity across the full usage window. Use qualified Claude, Grok or OpenCode profiles first for mechanical execution, including parallel implementation, repository exploration, gate execution and evidence collection. Codex being capable of the task is not a reason to spend its capacity on it.

Before any Codex mechanical subagent or mechanical Codex lead, capture the current Codex usage window when available, note known concurrent work, reserve enough capacity for remaining judgment, integration and exact-head semantic review, and record a positive delivery-level Codex mechanical allowance plus the reason. No recorded allowance means zero Codex mechanical dispatch. Start at most one Codex mechanical worker at a time; parallel Codex mechanical workers require explicit owner authorization.

Recheck usage after the first Codex mechanical checkpoint when observable. Freeze new Codex mechanical dispatch when burn exceeds the allowance, threatens the brain/review reserve or cannot be reconciled with known concurrent use. Let useful in-flight work reach its nearest clean tested checkpoint unless a hard limit or safety condition requires interruption, then move remaining mechanical work to another approved house. Batch related questions and integrated reviews so the Codex brain receives compact evidence and exceptions instead of raw exploration. Run one Sol-high semantic/risk review at each meaningful integrated chunk boundary; remedies still require exact-head re-review.

An explicit owner instruction such as “do not use Codex to delegate or lead” sets Codex mechanical worker and mechanical lead allocation to zero for that delivery, overriding any earlier allowance. Retain only the Codex brain or review use the owner explicitly requests. Run mechanical builds, tests and evidence collection outside Codex.

Before any adapter creates a pull request, run the exact preflight command in
the `adapter_contract.pr_base_preflight` entry of [commands.json](references/commands.json)
and fail closed on its nonzero result. Routine feature, fix, chore and
documentation packets target `test`; `main` requires the packet's explicit
human-controlled hotfix or release-promotion exception with exact base/head
evidence. This guard is shared by Claude, Grok, OpenCode and Codex adapters; it
does not replace later remote-ref resolution or live-base/head re-query.

Before external dispatch, read [runtime-adapters.md](references/runtime-adapters.md).
Use [commands.json](references/commands.json) as argument-array templates and read each profile's evidence status: newly configured Grok/Opus combinations have not yet been smoke-tested. These are not a production runner. Preflight literal argv, complete packet access, exact permissions and negative denies; abort closed on an unmappable rule. Do not substitute a shell-expanded string, use an unpinned default, or pass broader permissions merely to make a test succeed. Native subagents may collaborate directly; external sessions return through a supervised transport. Resume only when retained context justifies its cost. Grok runs through Grok CLI only; Cursor is excluded. Claude development uses Opus medium/high; do not select Sonnet, opusplan or automatic fallback to Sonnet.
DeepSeek V4.1 Flash uses only the OpenCode Go code `opencode-go/deepseek-v4.1-flash` at high or max. The displayed name and provider code identify the same approved model. The provider renamed this code from `opencode-go/deepseek-flash`, so the version now lives in the code itself. Treat a DeepSeek V4 Flash, V4 Pro or vision-exp selection as a profile mismatch; stop instead of substituting.

## Monitor and recover

Before ending a turn, reconcile unfinished authorized parent work. Continue if
unblocked and unowned; otherwise name a real active executor/wait mechanism,
concrete blocker or owner-requested pause. Never imply background continuation
from a saved session or future-tense promise. Apply GOV-0020's continuation
ownership rules; the current helper does not enforce automatic resumption.

After dispatch, remain the live supervisor until every owned worker reaches a
terminal state and its handback is collected, or another live supervisor accepts
the complete checkpoint and handles. Keep the turn active with real bounded
process/event waits. A timeout continues the wait loop; it is not a reason to end
the turn. Never send a final response while a supervised worker is active. If the
surface cannot retain the turn or wake reliably, disclose that before starting
unattended work. Apply the recovery procedure in `runtime-adapters.md` after any
loss of supervision.

Before reusing, retiring or cleaning up a session/worktree, read [session-lifecycle.md](references/session-lifecycle.md). Session lifetime follows related assignments and delivery boundaries, not one session per repository or per checkbox. Retirement is separate from deleting artifacts.

Use [completion.md](references/completion.md). The final token identifies the exact assignment and attempt; neither the token alone nor exit zero proves completion. Parse final assistant output separately from thinking, tool output and echoed prompts. Blocked/partial handbacks are terminal reports, not successes. Independent artifact verification is still required.

Local event reading and timer checks need no worker LLM calls. Drain raw provider
streams outside manager context and surface compact lifecycle changes; raw stream
replay can consume the manager's context even though waiting itself does not.
Do not send periodic 'are you done?' prompts. Schedule first retrieval from task
duration; use increasing bounded intervals afterward, with immediate event
delivery for completion/blockers and exact watchdog deadlines. Request a reason
once at the review deadline. Extensions need lead justification recorded before
hard expiry; output cannot reset elapsed time. If the transport cannot interrupt
or bound output, expose that limitation before starting a risky/long run.

After interruption or lost connectivity, inspect process/session, git status and artifacts before retrying. Confirm the previous writer and child processes stopped before transferring ownership. Reuse its worktree and checkpoint. After two failed recovery attempts, escalate to manager; one bounded independent diagnosis, then owner when unresolved. Read [operating-model.md](references/operating-model.md) for the war-room record.

After an abnormal external exit, parent termination alone is insufficient. Before
writer transfer, verify the parent/descendant processes, every process holding or
referencing the worktree, and the provider background-agent registry are all
clear; then inspect worktree state and locks. Any uncertainty blocks a duplicate
writer. For Claude, stop after two consecutive no-progress auto-compactions and
retry from a fresh compact checkpoint rather than resume a thrashing context.

## Accept and improve

Have a separate Sol high reviewer brain inspect semantics, risk, the actual diff and required evidence; use Astra medium when the review spans unusually large cross-workstream ambiguity. Mechanical workers may collect gates and evidence but cannot issue acceptance judgment. Reviewers return findings to the writer, not fix their own findings. Only a designated lead/manager may perform an authorized test merge. Read the current repository merge policy; bind review and gates to the current head and re-query the live base. Never use shared worker credentials as a claimed mechanical separation of roles.

Collect duration and available provider counters mechanically, with unknowns explicit. For before/after quota snapshots, Codex capacity conservation, local attempt history and aggregate weekly retention, read [history-and-retro.md](references/history-and-retro.md). Reuse canonical GOV-0020 score definitions and GOV-0016 lessons; do not create a competing delivery-state ledger. Quality precedes speed and remaining allowance. Weekly routing/governance changes are proposals requiring owner approval; bounded schedule adaptation must stay within approved limits.
