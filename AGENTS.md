# Agent Operating Rules

1. GitHub is the shared source of truth. Read the merged TraderOS V0 architecture and the active bounded issue before changing files.
2. Work on one bounded issue and one branch at a time. Report repository, main/base SHA, branch/worktree, task, allowed files, tests, credential state, and rollback before edits.
3. Preserve the repository boundary: TraderOS production authorities cannot be replaced or weakened by V0.
4. AI, strategy, dashboard, research, and context modules never receive exchange credentials and never call an exchange write endpoint.
5. Uncertain, stale, gapped, disconnected, conflicted, or unreconciled mandatory state means no new risk.
6. Never use simulated, sentinel, or default market/account data as decision evidence.
7. Historical code is `SEED` or `REFERENCE` until ported behind a reviewed V0 contract with provenance and tests.
8. Do not add an adapter, API wallet, credential, Testnet/Mainnet enablement, or automatic execution in V0-00.
9. Do not commit raw market/account data, databases, logs, virtual environments, caches, secrets, or source archives.
10. No direct commits to `main`, no force-push after review begins, no auto-merge, and no shared-history rewrite.
11. Every completion report lists exact changed files, commands/tests actually observed, artifacts/hashes, residual risks, rollback, issue/PR, and merge state.
