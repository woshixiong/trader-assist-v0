# Agent Operating Rules

1. GitHub is the shared source of truth. Read the merged TraderOS V0 architecture and the active bounded issue before changing files.
2. For any research plan, product/strategy/engineering route, architecture or technical direction, framework/tool/provider selection, or other material design decision, follow `governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md` in this exact order: independent analysis first; external research and evidence second; synthesis and final decision third. Do not reverse the order, search only for confirming evidence, or present externally anchored conclusions as independent reasoning. Purely mechanical execution and exact state verification are exempt unless they expose a new material design choice.
3. Work on one bounded issue and one branch at a time. Report repository, main/base SHA, branch/worktree, task, allowed files, tests, credential state, and rollback before edits.
4. Preserve the repository boundary: TraderOS production authorities cannot be replaced or weakened by V0.
5. AI, strategy, dashboard, research, and context modules never receive exchange credentials and never call an exchange write endpoint.
6. Uncertain, stale, gapped, disconnected, conflicted, or unreconciled mandatory state means no new risk.
7. Never use simulated, sentinel, or default market/account data as decision evidence.
8. Historical code is `SEED` or `REFERENCE` until ported behind a reviewed V0 contract with provenance and tests.
9. V0-01 may add bounded offline evidence runtime and public read-only source definitions. Any public network transport requires its own later bounded authorization and review.
10. Credentials, wallets, signing, exchange-write endpoints, order mutation, Testnet/Mainnet execution enablement, strategy logic, AI recommendations, and risk sizing remain prohibited unless a later task explicitly authorizes them.
11. Do not commit raw market/account data, databases, logs, virtual environments, caches, secrets, source archives, or real account identifiers.
12. No direct commits to `main`, no force-push after review begins, no auto-merge, and no shared-history rewrite.
13. Every completion report lists exact changed files, commands/tests actually observed, artifacts/hashes, residual risks, rollback, issue/PR, and merge state.
14. Successor windows read `governance/PROJECT_RULES_INDEX.md`, `governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`, `governance/PROJECT_STATE.json`, `governance/V0_FAST_LAUNCH_PROGRAM.json`, and `governance/POST_PR46_FIRST_LAUNCH_STATE_AND_NEXT_GATE_V1.md` after this file, then resolve live GitHub and CI state before acting.
15. When acting in the role `HERMES_EXECUTION_OPERATOR`, also read and obey `governance/HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md` and `schemas/control/lossless-task-packet-v1.schema.json`; when `EXECUTOR=TRAE_COMPUTER_USE`, additionally obey `governance/HERMES_TRAE_COMPUTER_USE_PROFILE_V1_2026-08-16.md`. In that role, Hermes is transport/execution infrastructure only: it may execute only a frozen Task Packet, must not paraphrase authoritative handoffs, must not choose executor/model/technical route or make research/review/approval decisions, and must fail closed on ambiguity or any action outside the packet.
