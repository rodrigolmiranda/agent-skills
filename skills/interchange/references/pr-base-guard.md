# Interchange PR base guard

Every adapter that can create a pull request must run this exact command with
the complete packet before invoking the provider API or CLI:

```text
python3 skills/interchange/scripts/protocol.py pr-base --packet-file <packet-file>
```

Exit `0` means the packet may proceed to PR creation; exit `1` is a denial and
must stop the adapter. Standard output is one machine-readable
`PullRequestBaseDecision` JSON object. The underlying reusable guard is
`skills/interchange/scripts/pr_base_guard.py`. Neither layer creates, approves,
merges, or publishes a pull request.

An ordinary feature, fix, chore, or documentation delivery has
`operation_class: ordinary` and must use `base_ref: test`. A packet that asks an
ordinary operation to target `main` is rejected before PR creation. This rule
applies equally to Claude, Grok, OpenCode, and Codex adapters.

`main` is reserved for an explicitly classified `hotfix` or
`release_promotion`. Such a packet must contain all of the following:

```json
{
  "operation_class": "hotfix",
  "base_ref": "main",
  "head_ref": "hotfix/example",
  "human_controlled": true,
  "human_only_merge": true,
  "base_evidence": {"ref": "main", "sha": "<40 hex commit SHA>"},
  "head_evidence": {"ref": "hotfix/example", "sha": "<40 hex commit SHA>"}
}
```

Release promotion uses the same exception shape, with
`operation_class: release_promotion`; its head ref is intentionally not
restricted to `hotfix/*`. The evidence refs must match the packet refs and both
SHAs must be full commit IDs. The hotfix exception additionally requires a
`hotfix/` head ref.

The guard is a local preflight boundary, not proof that a remote ref resolves or
that a live PR base/head still matches. The designated lead or delivery manager
must resolve the refs and re-query the live PR, then bind any later review,
approval, or merge to the exact reviewed head under the repository's governance.
Workers still cannot merge.

Historical lesson: SDK PR #130 was an old human release promotion to `main`,
not a routine worker delivery. Routine SDK publication is being redesigned by
`sm360-sdk` PR #132; this guard does not change either repository.
