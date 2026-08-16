# Project Rules Index

Successor windows read the following order before acting:

1. `AGENTS.md`
2. `governance/PROJECT_RULES_INDEX.md`
3. `governance/OPERATOR_ONE_PASTE_TERMINAL_DELIVERY_RULE_V1_2026-08-16.md`
4. `governance/PROJECT_STATE.json`
5. `governance/V0_FAST_LAUNCH_PROGRAM.json`
6. `governance/POST_PR46_FIRST_LAUNCH_STATE_AND_NEXT_GATE_V1.md`
7. `governance/FIRST_LAUNCH_MINIMUM_RECOVERY_READINESS_V1.md`
8. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_LOWEST_PRIORITY_BACKLOG_RULING_V1.md`
9. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md`
10. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_AUTOMATION_ABANDONMENT_RULING_V1.md`
11. `governance/TRADER_ASSIST_ENGINEERING_WORKFLOW_V3_2026-07-22.md`
12. current live GitHub and CI state

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

## One-paste Terminal operator-delivery rule

`governance/OPERATOR_ONE_PASTE_TERMINAL_DELIVERY_RULE_V1_2026-08-16.md` is the canonical operator-interface rule for user-operated engineering execution.

The user-facing execution contract is intentionally tool-agnostic:

1. the user opens ordinary macOS Terminal;
2. Engineering supplies exactly one contiguous copy-ready block;
3. the user pastes it once and runs it;
4. that block owns working-directory selection, preflight, shell/Git/tool routing, Codex invocation and complete prompt injection when Codex is needed, verification, and only the mutations currently authorized.

Do not require the user to distinguish `Terminal local command` from `Terminal -> Codex CLI`, launch Codex separately, perform a preparatory `cd`, manually switch branches, create a prompt file solely for transport, or perform a second paste. Those distinctions and routing decisions belong inside the Engineering-supplied block.

A naked Codex prompt is not the default operator deliverable. Multi-step blocks should use a contained subshell/heredoc or equivalent so fail-closed `exit` does not unnecessarily close the parent Terminal or SSH session.

The existing FinalShell rule remains companion authority for target-host work: when FinalShell is already connected to the Lightsail target host, provide one contiguous copy-ready remote-shell block and do not repeat SSH setup.

Additional human steps are allowed only when technically unavoidable or when an explicit safety/authority boundary requires them, such as MFA/security-key confirmation, secret handling, or a separate merge/deploy/runtime authorization gate.

This operator-interface rule does not grant commit, push, Mark Ready, merge, deployment, runtime, cloud, credential, account, signing, wallet or exchange-write authority. Those authorities remain governed by the current task and user gate.

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