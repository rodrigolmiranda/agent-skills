# Development routing instructions

Owner revision 2026-09-09; configured profile IDs and evidence status are in `policy.json` version 0.3.1. These are initial preferred pools, not benchmark rankings or interchangeable capability claims.

Delivery manager: Astra medium by default; Sol high and Opus 5 high are approved
alternatives. A matching conversation may use its manager profile without a new
override. Astra and Sol high reserve Codex; Opus high reserves Claude, including
during supervised waits. Cross-house manager transport still needs verification.

## Active houses and profiles

Use Codex, Grok CLI, Claude Code and OpenCode. Remove Cursor from Interchange routing; this does not uninstall Cursor. Grok work runs through Grok CLI with `grok-4.6` and effort `high` or `xhigh`. Claude development uses `claude-opus-5` with effort `medium` or `high`. Sonnet is excluded, including implicit execution switches and fallback routes. Verify actual model/effort before trusting a run; documented support is not an execution test.

## Choose a developer

For new-product ideas and product brainstorming, use Fable 5.1 medium or Astra
medium. Explore user/problem evidence, alternatives, assumptions and validation
questions; return recommendations without inventing owner decisions or starting
implementation. These are ideation profiles, not additions to the default coding
pool. Fable's exact runtime identity and included-plan eligibility remain unverified.

## House exclusivity

Sol high or higher reserves Codex. Opus high or higher reserves Claude. Astra at
any effort reserves Codex. Fable 5.1 at any effort reserves Claude (currently
approved only at medium). While such an assignment is active, no other
Interchange-managed activity may run in that house, across projects and roles.
This includes the active manager and native subagents; no implicit exception.

The check is symmetric: an exclusive job must wait for existing same-house jobs,
and a new ordinary job must wait behind an exclusive reservation. Prefer another
eligible house; otherwise queue. Do not lower effort, change the approved roster,
kill user work or expand spending to avoid the queue. Higher effort means only
levels supported by that model and already approved for the role; the rule grants
no new model/effort permission.

Release reservation after the attempt stops, or explicit suspension confirms no
remaining computation and preserves supervision/continuation ownership. Merely
waiting for a tool or posting a checkpoint does not release an active assignment.
An idle saved transcript is not itself a reservation. An active Astra or Sol-high manager
therefore sends parallel workers to other houses. It cannot launch a parallel
Codex developer unless its own active assignment is properly suspended or ended.

Fable medium cannot run alongside any other active Claude assignment. External user
sessions may be invisible; disclose uncertain occupancy rather than claim a
global lock. Mechanical enforcement needs the future shared runner.

Fable may bill usage credits without prompting in headless mode. Existing
no-extra-spending policy still applies: verify included allowance before launch;
if credit billing cannot be excluded, use an eligible alternative or report the
blocker. Selecting Fable is not permission to spend credits. See
[Claude model configuration](https://code.claude.com/docs/en/model-config).

## Development pools

| Assignment | Preferred pool | Assignment boundary |
|---|---|---|
| Small bounded support work | Muse Spark 1.3 Contributor xhigh; Luna xhigh/max as alternatives | Focused exploration, explicit small edits, test preparation; no delegation |
| Low/mid complexity development | Grok high, Opus medium, Terra xhigh, Sol medium | Known patterns, clear acceptance, bounded dependencies |
| Upper-mid complexity development | Grok xhigh, Opus medium | Difficult implementation with settled architecture and manageable coupling |
| High complexity development | Sol high, Opus high | Substantial reasoning or consequential/coupled boundaries; independent review remains mandatory |
| Demanding, well-defined implementation | Terra max | Dense implementation or integration with explicit contracts, tests and finite scope |

Entries in a pool are not listed in priority order. First select configurations with evidence of suitable quality for the task. Then consider expected time to an accepted result, available quota, existing session/context and the cost of transferring context. For parallel independent assignments, distribute suitable work across houses to preserve capacity. Reuse the same house when continuity or observed performance justifies it.

## Classification and escalation

Assess implementation difficulty, ambiguity, consequence and coupling separately. A small permission edit can be high consequence; a large mechanical change can have low ambiguity. A high consequence requires appropriate review even if implementation is simple.

Do not treat higher effort as a universal capability ranking. Use Terra max for sustained, bounded implementation, not to compensate for missing requirements or to persist in a loop. If the public contract or product outcome is unclear, the lead resolves that decision before assigning more execution effort. Stop and escalate under the existing watchdog/recovery limits.

Keep the delivery manager and lead routing unchanged. A worker using Sol or Terra is still a leaf unless explicitly assigned lead authority. Workers cannot merge or delegate merely because their model is also available to leads.

## Calibration

These pools express the owner's preferred starting allocation. Compare actual first-pass acceptance, repair effort, elapsed time and measured usage by task class. Do not claim Muse beats Luna, or Grok xhigh equals Opus medium, without comparable delivery evidence. Recommend changes through the existing weekly approval process. No extra spending or silent substitutions.

Configuration evidence: Grok's installed `grok models` lists `grok-4.6`, and its installed headless guide documents model-specific effort flags. Claude's installed CLI documents medium/high; [official model configuration](https://code.claude.com/docs/en/model-config) documents the pinned `claude-opus-5` ID. New Grok/Opus combinations require a bounded runtime confirmation; the former default-Grok and Sonnet smoke tests are historical transport evidence only.
