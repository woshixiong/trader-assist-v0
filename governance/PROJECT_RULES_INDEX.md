# Project Rules Index

Successor windows read the following order before acting:

1. `AGENTS.md`
2. `governance/PROJECT_RULES_INDEX.md`
3. `governance/PROJECT_STATE.json`
4. `governance/V0_FAST_LAUNCH_PROGRAM.json`
5. `governance/POST_PR46_FIRST_LAUNCH_STATE_AND_NEXT_GATE_V1.md`
6. `governance/FIRST_LAUNCH_MINIMUM_RECOVERY_READINESS_V1.md`
7. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_LOWEST_PRIORITY_BACKLOG_RULING_V1.md`
8. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md`
9. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_AUTOMATION_ABANDONMENT_RULING_V1.md`
10. `governance/TRADER_ASSIST_ENGINEERING_WORKFLOW_V3_2026-07-22.md`
11. current live GitHub and CI state

Live GitHub objects override stale chat snapshots and stale PR-body snapshots. Future windows
must resolve live GitHub state before relying on historical text.

PR #35 and PR #44 are salvage inputs, not merged authority. PR #42, PR #43 and PR #45 are
superseded. PR #48 is a frozen failed-design and historical research reference; it is not
merged authority and has no fourth-commit authority.

No governance file independently grants host, deployment, runtime, smoke, account or
exchange-write authority. Product authority, engineering authority and Project Control
execution authority remain separate.

## Efficiency-first rule

Efficiency is the primary optimization target after the minimum real safety boundary is
preserved.

Before developing automation, determine:

- event frequency;
- active guided human time;
- whether an existing command, checklist or temporary visible script can complete the task;
- actual risk reduction;
- implementation, review, testing and maintenance cost.

Do not build product-grade or institution-grade functionality for a low-frequency event that one
operator can complete safely with limited guided work.

Use this preferred order:

1. existing command;
2. short checklist;
3. temporary task-specific script;
4. provider-native or maintained external tool;
5. small permanent script only after repeated use proves net value;
6. framework only when scale, authority or compliance objectively requires it.

A normal repair plus one exceptional repair is the maximum for one bounded design route. If
both fail, do not continue iterative patching. Reduce scope or start a clean replacement.

## Operator window and Codex CLI delivery rule

Every engineering handoff to the human operator must state the execution destination before the
instructions. Do not leave the operator to infer whether a new chat/window is required.

Use exactly one of these user-visible directives as appropriate:

- `新开一个窗口：<role / tool / purpose>` when a fresh independent window is required;
- `使用原有窗口：<specific existing window / role>` when continuity with an existing window is required;
- `不需要打开窗口：直接在 Terminal 执行` when the instruction is a local Terminal operation rather than a chat/window handoff.

When reusing a window, identify which existing window is intended. Do not say only “use the old
window” or otherwise leave the referent ambiguous.

For Codex CLI work, the default operator deliverable is a single copy-ready macOS Terminal block
that launches the Codex CLI itself. A naked Codex prompt is not the default deliverable.

Unless the user explicitly asks for prompt text only, every Codex CLI task must therefore:

1. be directly pasteable into macOS Terminal;
2. be provided as one contiguous one-copy block;
3. invoke `codex exec` from the intended worktree/repository rather than requiring the operator
   to manually open Codex and paste a second prompt;
4. include the intended model, reasoning effort, sandbox/approval configuration and task prompt
   in the Terminal block when those controls are material;
5. include fail-closed preflight checks for material repository, branch, SHA, worktree, Python or
   authority assumptions when the task depends on them;
6. preserve the current task's explicit mutation and authority boundaries;
7. state what output the operator should return after execution.

Do not confuse Codex CLI with the Codex desktop application. If a desktop application/window is
actually required, say `新开一个窗口` or `使用原有窗口` explicitly instead of presenting CLI
instructions.

This is an operator-interface and task-transport rule only. It does not grant commit, push,
Mark Ready, merge, deployment, runtime, cloud, credential, account, signing or exchange-write
authority. Those authorities remain governed by the current task and user gate.

## Current First Launch recovery boundary

Deferring PR #48-style automation does not permit deferring all recovery preparation.

Before accepted real operation, complete the minimum recovery-readiness anchors:

- independent cloud-account recovery access;
- external recoverable notification-credential source;
- exact release and non-secret path card;
- approved SQLite-consistent backup and restore method;
- one verified post-qualification SQLite backup;
- explicit provider-snapshot or rebuild-only decision.

Event-specific recovery commands and complete automation may remain deferred.

## Current host-qualification direction

The PR #48 design is frozen and must not receive another repair.

For the immediate First Launch and ordinary low-frequency deployment events, use one fixed
host, one exact SHA, existing P4A guidance, `ta-status`, one controlled restart, 3+3 readiness
observations and a temporary host-specific command bundle.

The more complete automated qualification capability remains in the backlog at the lowest
priority:

`DEFERRED_LOWEST_PRIORITY__NO_CURRENT_IMPLEMENTATION_AUTHORITY`

It must not displace First Launch, real-operation stability, strategy, risk-control or required
account/execution safety work. It may be reconsidered when development capacity exists or when
a real migration, major redeployment, disaster recovery, multi-host, multi-operator,
higher-authority or compliance need justifies it.

When reconsidered, evaluate provider snapshots, images, maintained external tools and other
standard solutions before custom development. Use a clean task from current main; do not resume
or patch PR #48.

The former permanent-abandonment ruling is superseded but retained as historical decision
context. The failed implementation, review findings, RR-01 through RR-08 and proposed two-script
architecture remain preserved for future research.
