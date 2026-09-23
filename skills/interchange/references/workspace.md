# One workspace, portable records

Choose one authorized shared directory and put [workspace.json](../templates/workspace.json) there. Its containing directory is the root; both clients read the same manifest. Store project records under `projects/<project>/`, with plans, jobs/attempts, reports and continuation index. Put private supervisor state under `supervisor/` and retained proof under `archive/`. Do not embed machine paths or secrets in the portable manifest.

A private machine map supplies `repositories: {repo-id: checkout-path}` and `worktrees: {resource-id: existing-worktree-path}`. Register existing worktrees where they are; do not move them. New worktrees conventionally use `worktrees/<project>/<repo>/<job>` under the shared root. One writer per job, never a nested checkout inside another writer's surface. This naming convention is not a sandbox. Cross-machine transfer carries records and exact pushed Git references, not worktree metadata, credentials or processes. Preserve dirty/unpushed changes explicitly; verify incoming access and ownership before resuming.

## Retention: report first

Run `python3 <skill>/scripts/workspace.py --manifest <workspace.json> --machine-map <private-map.json>` to inspect registered resources. It never deletes, archives or moves anything. No automatic sweeper is installed. A candidate is a request for review, not deletion authority.

Resources have `id`, `kind`, `closed_at` (timezone-qualified), `disposition` (`accepted-merged` or explicitly `retired`), `active_owner: false`, `holds: []`, `archive_verified: true`. Unknowns retain. Raw-log resources supply a root-relative `path`; worktrees supply `repository_id` and `verified_head` and use the machine map. Worktree checks compare Git common-dir, cleanliness, head and locally observed remote containment. Remote refs can be stale; candidates require a fresh remote/process/ownership check before any removal. Squash equivalence is a separate reviewed proof, never inferred from absence of a branch.

Default eligibility is seven days after closure for clean merged/retired worktrees and thirty days for raw logs after resolution, with required evidence already retained. Required screenshots/acceptance/rollback proof may be archived after ninety days, but not deleted while linked or held. Plans, decisions, questions, reviews, evaluations, attempt/event IDs, acknowledgements and tombstones stay for project lifetime. Protected data, shared runtime, credentials and separately governed backups are outside this tool.

Approved cleanup remains: enumerate → verify archive/hash/link availability → obtain applicable authority → refresh all ownership/Git/process/hold checks → supported non-force removal → retain a tombstone. No `git clean`, force-removal, broad deletion, or reuse of purged attempt IDs. This first implementation deliberately provides inventory only; add execution only after dry-run experience warrants it.
