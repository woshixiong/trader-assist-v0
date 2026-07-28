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
13. Successor windows read `governance/PROJECT_RULES_INDEX.md`, `governance/SIMPLICITY_FIRST_ENGINEERING_AND_PROBLEM_SOLVING_RULE_V1.md`, `governance/PROJECT_STATE.json`, `governance/V0_FAST_LAUNCH_PROGRAM.json`, and `governance/POST_PR46_FIRST_LAUNCH_STATE_AND_NEXT_GATE_V1.md` after this file, then resolve live GitHub and CI state before acting.
14. Before scheduling or implementing any change that affects product behavior, operator workflow, notification channel, user interface, data presented to the user, human confirmation, execution authority, deployment topology, recurring operating burden, or future product path, Engineering Optimization must list the product decision points and obtain a recorded ruling from Product Function and Priority Control. Engineering may compare feasibility, cost, risk, reliability and reuse, but may not select or schedule product functionality. If a product decision point appears after work begins, stop safely, preserve evidence, and return it for product direction before continuing.
15. Across First Launch, V0, mainline and all later phases, apply the binding simplicity gate in `governance/SIMPLICITY_FIRST_ENGINEERING_AND_PROBLEM_SOLVING_RULE_V1.md`: define one exact question, choose the fewest safe components and operator actions, count total implementation/operation/review/maintenance cost, state success/failure/stop/replacement conditions, and stop or replace a route after two ineffective attempts. Assumed third-party UI behavior, unnecessary long manual payloads, avoidable relays and sunk-cost continuation are prohibited.
