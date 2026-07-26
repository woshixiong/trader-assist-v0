# Project Rules Index

Successor windows read the following order before acting:

1. `AGENTS.md`
2. `governance/PROJECT_RULES_INDEX.md`
3. `governance/PROJECT_STATE.json`
4. `governance/V0_FAST_LAUNCH_PROGRAM.json`
5. `governance/POST_PR46_FIRST_LAUNCH_STATE_AND_NEXT_GATE_V1.md`
6. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_AUTOMATION_ABANDONMENT_RULING_V1.md`
7. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md`
8. `governance/TRADER_ASSIST_ENGINEERING_WORKFLOW_V3_2026-07-22.md`
9. current live GitHub and CI state

Live GitHub objects override stale chat snapshots and stale PR-body snapshots. Future
windows must resolve live GitHub state before relying on historical text.

PR #35 and PR #44 are salvage inputs, not merged authority. PR #42, PR #43, and PR
#45 are superseded. PR #48 is a frozen failed-design and historical research reference; it is
not merged authority, has no fourth-commit authority, and must not be resumed as an active
feature without a new explicit user ruling.

No governance file independently grants host, deployment, runtime, smoke, account, or
exchange-write authority. Product authority, engineering authority, and Project Control
execution authority remain separate. A document may record an approved direction without
activating execution authority.

## Efficiency-first rule

Efficiency is the primary optimization target after the minimum real safety boundary is
preserved.

Before developing automation, determine:

- how frequently the event occurs;
- how much active human time guided execution requires;
- whether an existing command, checklist, or temporary visible script can complete it;
- the actual risk reduction produced by permanent automation;
- the full implementation, review, test and maintenance cost.

Do not build a product-grade or institution-grade feature for a low-frequency event that one
operator can complete safely with limited guided work.

Use this preferred order:

1. existing command;
2. short checklist;
3. temporary task-specific script;
4. small permanent script only after repeated use proves net value;
5. framework only when scale, authority or compliance objectively requires it.

A normal repair plus one exceptional repair is the maximum for a bounded route. If both fail,
do not continue iterative patching. Reduce scope, replace the route, or abandon the feature.

## Current host-qualification direction

The repository-backed automated supported-host qualification feature is abandoned because it
serves infrequent deployment events and costs more to build and maintain than guided manual
execution.

At a real deployment event, use one fixed host, one exact SHA, existing P4A guidance,
`ta-status`, one controlled restart, 3+3 readiness observations, and a temporary host-specific
command bundle generated for that session.

The failed PR #48 implementation, review findings and proposed two-script V2 remain archived
for research only. They are not an active or deferred implementation backlog.
