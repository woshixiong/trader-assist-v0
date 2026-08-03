# Agent Operating Rules

1. GitHub is the shared source of truth. Read the merged TraderOS V0 architecture and the active bounded issue before changing files.
2. Work on one bounded issue and one branch at a time. Report repository, main/base SHA, branch/worktree, task, allowed files, tests, credential state, and rollback before edits.
3. Preserve the repository boundary: TraderOS production authorities cannot be replaced or weakened by V0.
4. AI, strategy, dashboard, research, and context modules never receive exchange credentials and never call an exchange write endpoint.
5. Uncertain, stale, gapped, disconnected, conflicted, or unreconciled mandatory state means no new risk.
6. Never use simulated, sentinel, or default market/account data as decision evidence.
7. Historical code is `SEED` or `REFERENCE` until ported behind a reviewed V0 contract with provenance and tests.
8. V0-01 may add bounded offline evidence runtime and public read-only source definitions. Any public network transport requires its own later bounded authorization and review.
9. Credentials, wallets, signing, exchange-write endpoints, order mutation, Testnet/Mainnet execution enablement, strategy logic, AI recommendations, and risk sizing remain prohibited unless a later task explicitly authorizes them.
10. Do not commit raw market/account data, databases, logs, virtual environments, caches, secrets, source archives, or real account identifiers.
11. No direct commits to `main`, no force-push after review begins, no auto-merge, and no shared-history rewrite.
12. Every completion report lists exact changed files, commands/tests actually observed, artifacts/hashes, residual risks, rollback, issue/PR, and merge state.
13. Successor windows read `governance/PROJECT_RULES_INDEX.md`, `governance/PROJECT_STATE.json`, `governance/V0_FAST_LAUNCH_PROGRAM.json`, and `governance/POST_PR46_FIRST_LAUNCH_STATE_AND_NEXT_GATE_V1.md` after this file, then resolve live GitHub and CI state before acting.
14. Mature maintained external tools, provider-native capabilities, frameworks, libraries, and proven design patterns must be evaluated first. When an external solution satisfies the current authority, correctness, operational, licensing, and lifecycle requirements, reuse it through the thinnest practical adapter instead of rebuilding it. Any decision to build custom infrastructure must document the exact external candidates considered and the blocking fit gaps.
15. Concentrate project-owned engineering and research effort on proprietary strategy value: Scanner, Setup semantics, Market Event, Strategy Kernel, PlanDraft/TradeIntent, evidence, Outcome, and rapid strategy iteration. Avoid high-difficulty custom infrastructure unless a bounded spike proves that no acceptable maintained solution exists.
16. Prioritize work that remains reusable across shadow validation, human-confirmed execution, and future automated execution. Do not spend large development, review, testing, or maintenance resources on a one-time or low-frequency task when an existing command, checklist, temporary script, or maintained external tool can complete it safely.
17. Use cumulative small-step delivery: test small, observe, review, decide, implement the minimum coherent change, forward-validate, and iterate. Do not attempt a perfect system or complete trading engine in one stage. Major investment before a bounded spike is prohibited, and failed routes must be reduced or cleanly replaced rather than repaired indefinitely.
