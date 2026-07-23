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
13. Every Product Planning, Engineering Optimization, Project Control, Writer, Reviewer, Codex, TRAE, or OpenCode context must begin by reading `AGENTS.md`, `governance/PROJECT_RULES_INDEX.md`, and every document marked `REQUIRED` for the current phase. Live GitHub and CI state must then be reverified.
14. Persistent product decisions, engineering rules, model/Agent routing, resource policies, deferred work, and cross-window instructions must be versioned in GitHub governance. Chat history and local control files are not sufficient permanent records.
15. User language such as “同步固定对齐”, “固定下来”, “定规则”, “固定规则”, “以后都按这个执行”, “让其他窗口继承”, or equivalent durable-language triggers the GitHub governance persistence workflow: documentation-only branch, Draft PR, independent Review, safe merge point, and post-merge verification.
16. All project plans must distinguish: work required before First Launch accepted real operation; deferred/residual work preserved for V0 or mainline; and post-First-Launch evidence, product planning, V0 implementation, and mainline development.
17. No non-blocking finding with future product, security, reliability, data, trading-closure, engineering-process, or maintainability value may disappear. It must be recorded in the persistent deferred register with a stable ID, source, risk, trigger, owner, acceptance criteria, and final disposition.
18. Product Function and Priority decides what and why; Engineering Optimization decides how to build; Project Control executes accepted decisions. No window may infer or replace another authority.
19. Use one primary Writer for one coherent stage. Group repairs by root cause. One-finding-per-Writer, one-finding-per-task, one-file-per-Agent, and open-ended repair loops are prohibited by default.
20. Codex quota is reserved for proven code-critical work. Documentation, status consolidation, planning, routine read-only Review, and persistent-register maintenance must use ordinary ChatGPT or TRAE where appropriate. Quota pressure never authorizes weaker tests or skipped safety gates.