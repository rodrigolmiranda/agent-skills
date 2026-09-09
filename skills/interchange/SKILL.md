---
name: interchange
description: Coordinate governed delivery across Codex subagents and external Claude, Grok and OpenCode sessions, with explicit ownership, fixed execution profiles, checkpoints, bounded monitoring and independent acceptance.
---

# Interchange

Use the primary conversation as delivery manager. Resolve product ambiguity and cross-workstream dependencies here; delegate coherent owned outcomes. Default personal manager profile: Astra medium; Sol high and Opus 5 high are approved alternatives with no additional profile override needed. Verify the active model/effort; loading the skill does not switch it. For manager handover and transport prerequisites, read [operating-model.md](references/operating-model.md). This package is an initial skill and protocol implementation, not an operational process supervisor. Never claim monitoring, cancellation or automatic callbacks are active without testing the actual transport.

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

Give each assignment an ID, revision and unique attempt ID. Include outcome, acceptance, repo URL/ref/base, lead-allocated worktree, exclusive paths, read-only dependencies, fixed profile, governance references, allowed tools/actions, expected seconds, deadlines, stop/escalation conditions and return format. Leaf workers cannot delegate, merge, expand scope, weaken checks or invent contracts. For an ambiguity they cannot resolve inside the assignment, return evidence and the smallest question to the lead.

Use [commands.json](references/commands.json) as argument-array templates and read each profile's evidence status: newly configured Grok/Opus combinations have not yet been smoke-tested. These are not a production runner. Do not substitute a shell-expanded string, use an unpinned default, or pass broader permissions merely to make a test succeed. Probe unsupported features and report unavailable metadata honestly. Native subagents may collaborate directly; external sessions return through a supervised transport. Resume a recorded session for follow-ups. Grok runs through Grok CLI only; Cursor is excluded. Claude development uses Opus medium/high; do not select Sonnet, opusplan or automatic fallback to Sonnet.

## Monitor and recover

Before ending a turn, reconcile unfinished authorized parent work. Continue if
unblocked and unowned; otherwise name a real active executor/wait mechanism,
concrete blocker or owner-requested pause. Never imply background continuation
from a saved session or future-tense promise. Apply GOV-0020's continuation
ownership rules; the current helper does not enforce automatic resumption.

Before reusing, retiring or cleaning up a session/worktree, read [session-lifecycle.md](references/session-lifecycle.md). Session lifetime follows related assignments and delivery boundaries, not one session per repository or per checkbox. Retirement is separate from deleting artifacts.

Use [completion.md](references/completion.md). The final token identifies the exact assignment and attempt; neither the token alone nor exit zero proves completion. Parse final assistant output separately from thinking, tool output and echoed prompts. Blocked/partial handbacks are terminal reports, not successes. Independent artifact verification is still required.

Local event reading and timer checks need no LLM calls. Do not send periodic 'are you done?' prompts. Schedule first retrieval from task duration; use increasing bounded intervals afterward, with immediate event delivery for completion/blockers and exact watchdog deadlines. Request a reason once at the review deadline. Extensions need lead justification recorded before hard expiry; output cannot reset elapsed time. If the transport cannot interrupt, expose that limitation before starting a risky/long run.

After interruption or lost connectivity, inspect process/session, git status and artifacts before retrying. Confirm the previous writer and child processes stopped before transferring ownership. Reuse its worktree and checkpoint. After two failed recovery attempts, escalate to manager; one bounded independent diagnosis, then owner when unresolved. Read [operating-model.md](references/operating-model.md) for the war-room record.

## Accept and improve

Have a separate qualified reviewer inspect the actual diff and required evidence. Reviewers return findings to the writer, not fix their own findings. Only a designated lead/manager may perform an authorized test merge. Read the current repository merge policy; bind review and gates to the current head and re-query the live base. Never use shared worker credentials as a claimed mechanical separation of roles.

Collect duration and available provider counters mechanically, with unknowns explicit. For before/after quota snapshots, local attempt history and aggregate weekly retention, read [history-and-retro.md](references/history-and-retro.md). Reuse canonical GOV-0020 score definitions and GOV-0016 lessons; do not create a competing delivery-state ledger. Quality precedes speed and remaining allowance. Weekly routing/governance changes are proposals requiring owner approval; bounded schedule adaptation must stay within approved limits.
