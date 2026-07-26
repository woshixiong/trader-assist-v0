# Project Rules Index

Successor windows read the following order before acting:

1. `AGENTS.md`
2. `governance/PROJECT_RULES_INDEX.md`
3. `governance/PROJECT_STATE.json`
4. `governance/V0_FAST_LAUNCH_PROGRAM.json`
5. `governance/POST_PR46_FIRST_LAUNCH_STATE_AND_NEXT_GATE_V1.md`
6. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md`
7. `governance/TRADER_ASSIST_ENGINEERING_WORKFLOW_V3_2026-07-22.md`
8. current live GitHub and CI state

Live GitHub objects override stale chat snapshots and stale PR-body snapshots. Future
windows must resolve live GitHub state before relying on historical text.

PR #35 and PR #44 are salvage inputs, not merged authority. PR #42, PR #43, and PR
#45 are superseded. PR #48 is a frozen failed-design and research reference; it is not
merged authority and has no fourth-commit authority.

No governance file independently grants host, deployment, runtime, smoke, account, or
exchange-write authority. Product authority, engineering authority, and Project Control
execution authority remain separate. A document may record an approved direction without
activating execution authority.

The current minimum First Launch direction is a fixed-host, human-controlled, guided
deployment and 3+3 `ta-status` qualification. The deferred two-script qualification V2 is
preserved for research and possible post-First-Launch implementation only when real operating
needs justify its cost.
