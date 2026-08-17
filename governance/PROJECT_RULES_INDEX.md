# Project Rules Index

Successor windows read the following order before acting:

1. `AGENTS.md`
2. `governance/PROJECT_RULES_INDEX.md`
3. `governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md`
4. `governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md`
5. `governance/PROJECT_STATE.json`
6. `governance/V0_FAST_LAUNCH_PROGRAM.json`
7. `governance/POST_PR46_FIRST_LAUNCH_STATE_AND_NEXT_GATE_V1.md`
8. `governance/FIRST_LAUNCH_MINIMUM_RECOVERY_READINESS_V1.md`
9. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_LOWEST_PRIORITY_BACKLOG_RULING_V1.md`
10. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md`
11. `governance/FIRST_LAUNCH_HOST_QUALIFICATION_AUTOMATION_ABANDONMENT_RULING_V1.md`
12. `governance/TRADER_ASSIST_ENGINEERING_WORKFLOW_V3_2026-07-22.md`
13. current live GitHub and CI state

Live GitHub objects override stale chat snapshots and stale PR-body snapshots. Future windows
must resolve live GitHub state before relying on historical text.

PR #35 and PR #44 are salvage inputs, not merged authority. PR #42, PR #43 and PR #45 are
superseded. PR #48 is a frozen failed-design and historical research reference; it is not
merged authority and has no fourth-commit authority.

No governance file independently grants host, deployment, runtime, smoke, account or
exchange-write authority. Product authority, engineering authority and Project Control
execution authority remain separate.

## Mandatory engineering preflight / convergence gate

For every material engineering route, architecture decision, runtime/persistence/provider design,
cross-layer repair, technical selection, Writer task package or implementation prompt, apply
`governance/MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md` before Writer
dispatch.

No material Writer prompt may be issued unless `ENGINEERING_PREFLIGHT_GATE=PASS` is supported by:

- resolved live GitHub authority;
- independent analysis;
- external mature-solution research where applicable;
- explicit synthesis;
- root-cause and affected-authority analysis;
- frozen cross-layer invariants;
- future continuity / replaceability analysis;
- provider/scale/freshness analysis where applicable;
- attack matrix;
- repair stage and stop condition.

If a task repeatedly produces local blockers, do not continue adding conditionals. After one
normal repair plus one exceptional repair, or earlier when the failure proves a cross-layer/global
abstraction problem, stop coding and enter `HOLISTIC_CONVERGENCE_GATE`.

Critical permanent rules must be moved into the canonical successor-window read path; chat memory,
an Issue comment, or an unmerged Draft PR alone is not a sufficient long-term rule location.

If a new architecture-critical requirement is discovered after a Writer prompt was issued but
before it was executed, void the old prompt and regenerate one complete replacement prompt. Do not
make the user assemble critical prompt addenda.

## Mandatory research / evidence / decision method

For every applicable research, planning, strategy, product, engineering, architecture, technology,
framework, provider, or other material direction-setting task, use
`governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md` without requiring the user
to restate it.

The mandatory sequence is:

1. independent analysis and preliminary position;
2. broad external research, including mature solutions, validated cases, counterexamples and
   disconfirming evidence;
3. explicit synthesis showing what the external evidence confirms, modifies, rejects, or leaves
   uncertain before issuing the final recommendation.

Do not browse external conclusions first and later present the result as independent reasoning.
Do not search only for evidence that supports the initial view. Purely mechanical execution and
exact state verification are exempt unless they expose a new material design choice.

## Continuity-first / scale-provider rule

Every material technical route must preserve an explicit continuation path into the next expected
development stage. Do not choose a host-specific, launch-size, provider-specific or current-policy
shortcut that predictably forces a near-term rewrite, incompatible authority model or avoidable
migration burden.

Before acceptance state:

- the current bounded need;
- the next expected scale/capability step;
- which interfaces/contracts/authorities remain stable;
- which implementation policy is replaceable;
- which values are tuning parameters rather than architectural constants;
- known migration/lock-in risk.

Prefer stable narrow seams plus one current implementation. Do not build speculative future
platforms merely to claim extensibility.

Before first deployment or a material change to market count, history depth, cadence, provider/API
usage, confirmation/retry count, concurrency, database workload or runtime cohort size, calculate
the provider/scale budget and include a realistic-order-of-magnitude acceptance test when the
bottleneck is scale-dependent. Trading/scanner routes must prove the intended freshness SLA at the
target scale.

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
both fail, do not continue iterative patching. Reduce scope, enter holistic convergence, or start
a clean replacement.

## Terminal and Codex CLI operator-delivery rule

All routine Codex engineering work is performed through **Codex CLI in macOS Terminal**. Do not
refer to a Codex desktop window unless the user explicitly changes this operating model.

Every engineering command handoff must state the execution destination before the copy-ready
block. The operator must never have to infer whether the command is ordinary Terminal work,
whether it launches Codex CLI, which Terminal instance to use, or which repository/worktree is
intended.

### Required execution header

Before every Terminal command block, state all applicable fields in user-visible form:

- `执行方式：Terminal 本地命令` for shell/Git/GitHub/inspection/other commands that do not launch Codex;
- `执行方式：Terminal → Codex CLI` for a block that launches or resumes Codex CLI;
- `Terminal：新开一个 Terminal` when a fresh Terminal instance is required or safer;
- `Terminal：使用原有 Terminal：<specific terminal/session description>` when continuity with a specific existing Terminal is intended;
- `工作目录：<absolute repository/worktree path>` for every repository-dependent command;
- for Codex CLI, additionally state `Codex 会话：新建` or `Codex 会话：续用 <session-id / precisely identified prior session>`.

If an existing Terminal is required, identify it by the task, branch/worktree, or other concrete
operator-visible characteristic. Do not say only `使用原有 Terminal` when more than one Terminal
could plausibly match.

If the command block performs its own `cd` or uses Codex `-C/--cd`, still display the intended
working directory in the header so the operator can verify the target before execution.

### Terminal-only versus Terminal-to-Codex distinction

These are different execution classes even though both begin in macOS Terminal:

1. **Terminal local command** — executes shell, Git, GitHub CLI, tests, inspection, packaging, or
   other local commands directly and does not invoke Codex.
2. **Terminal → Codex CLI** — invokes `codex`, normally through a copy-ready `codex exec` or an
   explicitly selected resume flow, and delegates the engineering task to Codex.

The delivery must label the class explicitly every time.

### Codex CLI session continuity

Terminal-window continuity and Codex-session continuity are separate concepts. Reusing the same
Terminal window does not by itself prove that Codex model context is being reused.

When prior Codex context is materially useful, explicitly resume the intended Codex CLI
session/thread rather than assuming continuity from the Terminal window. When a clean independent
Writer or Reviewer context is required, explicitly start a new Codex session.

The engineering orchestrator should choose between new versus resumed Codex context based on the
current role and review-separation requirements:

- continue the same Writer task: prefer the same authorized worktree and, when safe and useful,
  resume the exact prior Codex session;
- independent review, role separation, provenance uncertainty, or contamination risk: use a new
  Codex session even if the same repository/worktree is inspected;
- never resume a session merely to save tokens when doing so would weaken Writer/Reviewer
  independence or carry stale authority assumptions forward.

### Codex CLI copy-ready delivery

Unless the user explicitly requests prompt text only, every Codex CLI task must be delivered as
one contiguous, directly pasteable macOS Terminal block that launches or resumes Codex CLI
itself. A naked Codex prompt is not the default operator deliverable.

The block must, when material:

1. enter or explicitly target the intended absolute repository/worktree path;
2. invoke `codex exec` or the explicitly selected supported resume form;
3. specify the intended model and reasoning effort;
4. specify sandbox/approval settings;
5. include the complete task prompt in the same Terminal block;
6. include fail-closed preflight checks for material repository, branch, SHA, worktree, Python,
   session, or authority assumptions;
7. preserve the current task's explicit mutation and authority boundaries;
8. state what output the operator should return after execution.

When a prior Codex session is to be resumed, the command block must identify the exact session
rather than relying only on Terminal history. When a new Codex session is required, say so
explicitly.

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