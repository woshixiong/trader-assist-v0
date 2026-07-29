# Agent Operating Rules

1. GitHub is the shared source of truth. Read the merged TraderOS V0 architecture and the active bounded issue before changing files.
2. Work on one bounded issue and one branch at a time. Report repository, main/base SHA, branch/worktree, task, allowed files, tests, credential state, rollback, execution environment and available capabilities before edits.
3. Every task assignment must pass a capability preflight. Local implementation, tests, commit and push may only be assigned to an authenticated local Writer with the required repository and toolchain access. A Connector-only window is not a local Writer and must SAFE_STOP rather than weaken gates.
4. Within one authorized coherent stage, the capability-matched Writer executes implementation, local gates, normal commit, normal push and exact-head CI continuously. Do not use the user as a routine message bus or split work by file, command, test or lint finding.
5. Independent exact-head read-only review remains mandatory. Mark Ready, merge, deployment, activation, credentials, account access and exchange writes remain separate user authority gates.
6. Preserve the repository boundary: TraderOS production authorities cannot be replaced or weakened by V0.
7. AI, strategy, dashboard, research, and context modules never receive exchange credentials and never call an exchange write endpoint.
8. Uncertain, stale, gapped, disconnected, conflicted, or unreconciled mandatory state means no new risk.
9. Never use simulated, sentinel, or default market/account data as decision evidence.
10. Historical code is `SEED` or `REFERENCE` until ported behind a reviewed V0 contract with provenance and tests.
11. V0-01 may add bounded offline evidence runtime and public read-only source definitions. Any public network transport requires its own later bounded authorization and review.
12. Credentials, wallets, signing, exchange-write endpoints, order mutation, Testnet/Mainnet execution enablement, strategy logic, AI recommendations, and risk sizing remain prohibited unless a later task explicitly authorizes them.
13. Do not commit raw market/account data, databases, logs, virtual environments, caches, secrets, source archives, or real account identifiers.
14. No direct commits to `main`, no force-push after review begins, no auto-merge, and no shared-history rewrite.
15. Every completion report lists exact changed files, commands/tests actually observed, artifacts/hashes, residual risks, rollback, issue/PR, merge state and capability-preflight result.
16. Successor windows read `governance/PROJECT_RULES_INDEX.md`, `governance/PROJECT_STATE.json`, `governance/V0_FAST_LAUNCH_PROGRAM.json`, `governance/POST_PR46_FIRST_LAUNCH_STATE_AND_NEXT_GATE_V1.md`, and `governance/ENGINEERING_STAGE_EXECUTION_AND_TASK_ALLOCATION_STANDARD_V1.md` after this file, then resolve live GitHub and CI state before acting.
