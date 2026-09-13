# Development routing instructions

Owner revision 2026-09-13; configured profile IDs and evidence status are in `policy.json` version 0.8.0. These are initial preferred pools, not benchmark rankings or interchangeable capability claims.

Sol high is the default product, architecture and ideation brain. Astra medium and
Fable 5.1 medium are candidates only after the owner authorizes that exact model
invocation and the record states concretely why Sol high cannot fit. Delivery managers on other approved
profiles may coordinate, monitor and integrate settled work, but must route
unresolved interpretation to a brain. Astra reserves Codex globally. Sol high
reserves Codex only within work under the same delivery manager. Opus high has
that same manager-scoped effect in Claude. Cross-house manager transport still
needs verification.

## Active houses and profiles

Use Codex, Grok CLI, Claude Code and OpenCode. Remove Cursor from Interchange routing; this does not uninstall Cursor. Grok work runs through Grok CLI with `grok-4.6` and effort `high` or `xhigh`. Claude development uses `claude-opus-5` with effort `medium` or `high`. Sonnet is excluded, including implicit execution switches and fallback routes. DeepSeek V4.1 Flash runs only through the OpenCode Go model code `opencode-go/deepseek-v4.1-flash`, at `high` or `max`. Treat the displayed model name and provider code as two identities for the same approved model. Never select `opencode-go/deepseek-flash`, `deepseek-v4-flash` or `deepseek-v4-pro`, and never substitute another DeepSeek route after an error. Verify actual model/effort before trusting a run; documented support is not an execution test.

## Choose a developer

For new-product ideas and product brainstorming, use Sol high by default. Fable
5.1 medium or Astra medium may be used only after the per-invocation owner gate.
Explore user/problem evidence, alternatives, assumptions and validation
questions; return recommendations without inventing owner decisions or starting
implementation. These are ideation profiles, not additions to the default coding
pool. Fable's exact runtime identity and included-plan eligibility remain unverified.

The gate applies to every Astra or Fable start, resume, retry and follow-up in any
role. Authorization must name the packet, attempt, invocation, model, effort and
purpose, and record a concrete reason `gpt-5.6-sol` high cannot fit. Only the owner
can authorize. An earlier authorization, general model preference or delivery
approval cannot be reused. Without it, use Sol high if suitable or stop and ask the
owner with the proposed reason. Fable additionally requires separate proof that
the invocation stays inside the included plan and creates no extra spend.

Before choosing a developer, resolve every product, behavior, architecture and
tradeoff decision through Sol high, Astra medium or Fable medium as applicable.
All other profiles are mechanical executors. Their packets name settled behavior,
objective acceptance, owned paths and the condition that returns ambiguity to the
brain. A coordinator on a non-brain profile does not decide merely because it owns
the delivery session.

## Preserve Codex capacity

Route mechanical work to qualified Claude, Grok or OpenCode profiles first. Preserve
Codex for judgment, integration decisions and semantic/risk review across the full
usage window. Before a Codex mechanical worker or mechanical lead, record the current
usage snapshot when available, known concurrent work, the brain/review reserve, a
positive mechanical allowance and the reason external execution is unsuitable. No
allowance means no Codex mechanical dispatch. Start one Codex mechanical worker at a
time; more requires explicit owner authorization. Recheck usage at its first clean
checkpoint and freeze further Codex mechanical dispatch when burn exceeds plan or
threatens the reserve.

An owner instruction not to use Codex for delegation or leading overrides every
mechanical allowance and sets Codex worker/lead allocation to zero. Keep only the
Codex brain/review use explicitly requested. Run builds, tests and evidence collection
through mechanical external workers.

Batch related brain questions. Gather repository evidence and run gates through
mechanical workers. Use one Sol-high semantic/risk review at a meaningful integrated
chunk boundary rather than reviewing every leaf task; a remedy commit still requires
exact-head re-review.

## House exclusivity

Astra at any effort reserves Codex globally. Fable 5.1 at any effort reserves
Claude globally (currently approved only at medium). Global covers all visible
Interchange-managed delivery managers, deliveries, projects and roles.

Sol high or higher reserves Codex only within assignments owned or supervised by
the same delivery manager. Opus high or higher applies the same manager-scoped
reservation to Claude. Another delivery manager may use that house concurrently,
subject to any global reservation. Managers, leads, workers and reviewers have no
implicit exemption inside the applicable scope.

The check is symmetric: an exclusive job must wait for existing conflicting jobs,
and a new ordinary job must wait behind an applicable reservation. Prefer another
eligible house; otherwise queue. Do not lower effort, change the approved roster,
kill user work or expand spending to avoid the queue. Higher effort means only
levels supported by that model and already approved for the role; the rule grants
no new model/effort permission.

Release reservation after the attempt stops, or explicit suspension confirms no
remaining computation and preserves supervision/continuation ownership. Merely
waiting for a tool or posting a checkpoint does not release an active assignment.
An idle saved transcript is not itself a reservation. An active Astra manager
therefore sends all parallel Codex work to other houses. A Sol-high manager sends
its own parallel Codex work elsewhere, while an independent delivery manager may
still use Codex if no global reservation applies.

Fable medium cannot run alongside any other active Claude assignment. External user
sessions may be invisible; disclose uncertain occupancy rather than claim a
global lock. Mechanical enforcement needs the future shared runner.

Fable may bill usage credits without prompting in headless mode. Owner authorization
to invoke Fable is not spending authorization. Existing
no-extra-spending policy still applies: verify included allowance before launch;
if credit billing cannot be excluded, use an eligible alternative or report the
blocker. Selecting Fable is not permission to spend credits. See
[Claude model configuration](https://code.claude.com/docs/en/model-config).

## Development pools

| Assignment | Preferred pool | Assignment boundary |
|---|---|---|
| Light mechanical and read/seek work | Muse Spark 1.3 Contributor xhigh; Luna xhigh/max as alternatives | Repository search, file localization, evidence collection, narrow checks and small explicit edits; no interpretation or delegation |
| Low/mid complexity development | DeepSeek V4.1 Flash high, Grok high, Opus medium, Terra xhigh, Sol medium | Settled behavior, objective acceptance and bounded dependencies; no interpretation |
| Upper-mid complexity development | DeepSeek V4.1 Flash high, Grok xhigh, Opus medium | Difficult mechanical implementation with settled architecture; return tradeoffs instead of choosing |
| High complexity development | Sol high settles judgment; Opus high or another qualified profile executes mechanical packets | Separate consequential decisions from implementation; independent brain review remains mandatory |
| Demanding, well-defined implementation | DeepSeek V4.1 Flash high; Opus high | Terra max requires a recorded Codex mechanical allowance; contracts, tests and scope must already be settled |
| Novel public contract implementation | Sol high settles the shape; DeepSeek V4.1 Flash max implements it | Public API, identity, schema or serialization shape and objective contract tests are decided before dispatch |

Entries in a pool are not listed in priority order. First select configurations with evidence of suitable quality for the mechanical task. Then prefer the fastest, lowest-cost eligible profile after accounting for startup, supervision, context transfer and integration. Run independent, objectively testable packets in parallel after decisions, interfaces and write ownership are fixed. Do not split work when orchestration overhead would erase the gain. Distribute suitable work across houses to preserve capacity; reuse the same house when continuity or observed performance justifies it.

## Classification and escalation

Assess implementation difficulty, ambiguity, consequence and coupling separately. A small permission edit can be high consequence; a large mechanical change can have low ambiguity. Route interpretation to a brain before implementation. A high consequence requires appropriate review even if implementation is simple.

Do not treat higher effort as a universal capability ranking. Use Terra max for sustained, bounded implementation, not to compensate for missing requirements or to persist in a loop. DeepSeek high is the default DeepSeek effort. Use DeepSeek max only to implement a novel public contract after an approved brain settles its shape and objective contract tests; max does not receive interpretation authority or replace independent review. If the public contract or product outcome is unclear, the brain resolves that decision before assigning execution. Stop and escalate under the existing watchdog/recovery limits.

A worker using a brain-capable model remains a mechanical leaf unless explicitly assigned a brain role. Workers cannot merge, delegate or interpret merely because their model is also available to leads or managers.

## Calibration

These pools express the owner's preferred starting allocation. Compare actual first-pass acceptance, repair effort, elapsed time and measured usage by task class. Do not claim Muse beats Luna, or Grok xhigh equals Opus medium, without comparable delivery evidence. Recommend changes through the existing weekly approval process. No extra spending or silent substitutions.

Configuration evidence: Grok's installed `grok models` lists `grok-4.6`, and its installed headless guide documents model-specific effort flags. Claude's installed CLI documents medium/high; [official model configuration](https://code.claude.com/docs/en/model-config) documents the pinned `claude-opus-5` ID. New Grok/Opus combinations require a bounded runtime confirmation; the former default-Grok and Sonnet smoke tests are historical transport evidence only.
