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
exchange-write authority. Product, Strategy, Engineering and Operations are four peer domain
windows. The user retains final authority for cross-domain priority, Mark Ready, merge,
deployment, runtime/cloud mutation, credential/account access, signing and exchange-write actions.

## Four-window governance and Operations Window

Trader Assist / Trade OS uses four long-lived peer specialist windows. No specialist window is
hierarchically above another. Each owns decisions in its domain and must hand cross-domain work to
the appropriate peer instead of silently absorbing that authority.

### Product Window

Owns product purpose and scope: why a capability exists, user value, launch scope, priority,
feature inclusion/deferral/cancellation, product acceptance criteria and product-level release
readiness. It does not dictate strategy research conclusions, implementation details or production
operations procedures.

### Strategy Window

Owns trading/research logic: Setup definitions, signal semantics, research hypotheses, evidence
requirements, strategy parameters and economic interpretation. It does not own deployment,
infrastructure, credentials, service lifecycle or engineering implementation authority.

### Engineering Window

Owns implementation and technical execution assistance: architecture within frozen product and
strategy contracts, code, schemas, integration, tests, CI, bounded repairs, exact-artifact review,
release engineering and operator-ready execution commands. Engineering does not independently set
product goals, trading semantics or long-term operations policy.

### Operations Window

Owns the strategy, standards, runbooks and gate design for operating the system safely after code
exists. Its standing domain includes:

- deployment and release operations;
- production configuration and service lifecycle;
- systemd/process ownership and restart/start/stop procedures;
- readiness, health checks, telemetry, logs, monitoring and alerting;
- host/network/provider operational qualification and capacity verification;
- backups, off-host storage, disaster recovery, restore qualification and retention policy;
- rollback, incident response, recovery drills and decommissioning;
- credential installation/rotation/recovery procedures and non-secret configuration lifecycle;
- operational security boundaries, least privilege and separation of recoverable credentials;
- storage/runtime housekeeping, evidence retention and operational data growth controls;
- cloud/provider resource lifecycle and recurring operational cost review;
- routine maintenance cadence, runbooks and operator checklists.

The Operations Window is a **planning and operations-policy authority**, not an automatic production
mutation authority. It may inspect live state when the current task permits read access and may
produce exact execution plans, but it must not infer permission to deploy, restart, mutate AWS,
change production databases, access private/account APIs, rotate credentials, delete snapshots or
perform trading/exchange writes. Those actions require the user's explicit task authorization.

When Operations determines that new code, scripts, schemas, tests or integration are required, it
hands a bounded engineering requirement to the Engineering Window. Engineering implements and
reviews it. When an operations choice changes product behavior or launch scope, Product must rule.
When an operations choice changes strategy/evidence semantics, Strategy must rule. Operations
should prefer provider-native and mature maintained capabilities over custom infrastructure and
should minimize ongoing operator toil without building unnecessary platform machinery.

### Current Operations handoff — 2026-08-15

The following snapshot is a handoff for the newly created Operations Window. Live repository,
GitHub, host and provider state override this snapshot when they differ.

1. **Legacy currently deployed runtime** — the user reports that the old online version has produced
   no useful trading notifications or valuable durable trading data and has not been meaningfully
   used for many days. Do not spend effort qualifying Restic backups merely to preserve this empty
   legacy runtime. The user has stated that the old Lightsail snapshot may be deleted; actual AWS
   deletion remains a separately authorized mutation and should be handled only under an explicit
   decommission action.
2. **Upcoming three-Setup Shadow release** — this is the first release that is expected to generate
   valuable Scanner/Strategy/Formal/Shadow/Outcome/research evidence and is therefore the real
   target for production backup and disaster-recovery qualification.
3. **Restic V1 implementation** — the bounded Restic off-host backup/recovery capability was merged
   through PR #90. Current merged main immediately after that merge is
   `2bfb6f5dd6923a03d507f8ab2ff8514427a19b22`, and the post-merge `V0 contracts CI` run passed.
   The mechanism is intended to be reused by later V0 / Trade OS releases rather than redesigned
   each time; future releases normally extend or change the durable-asset inventory, not the core
   backup architecture.
4. **Restic V1 current recovery boundary** — First Launch fixed assets are `runtime.db`, `public.env`
   and `risk-configuration.json`. Full MultiAsset recovery additionally expects explicit
   MultiAsset EvidenceStore and Market Registry paths. At the time Restic V1 was accepted, those
   MultiAsset production paths were not yet bound. Therefore
   `FULL_MULTI_ASSET_DISASTER_RECOVERY_QUALIFIED=NO` until the upcoming release binds and verifies
   the real production durable assets and completes a real off-host recovery qualification.
5. **Existing deployment material** — `docs/operations/V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md` is an
   existing First Launch/systemd deployment reference. Operations must assess what can be reused
   for the upcoming MultiAsset three-Setup release and must not assume the legacy runbook is an
   exact production procedure for the new runtime.
6. **Reconnect/recovery code** — the consecutive reconnect-budget repair has already been merged
   through PR #88. Older Issue #80 text that still lists PR #69/#70 as unresolved predeployment
   blockers is stale and must be reconciled against live GitHub before planning.
7. **Stale backup route** — Draft PR #70 is the superseded age/rclone backup route. Do not resume or
   patch it. PR #90 / current-main Restic V1 is the active backup/recovery implementation.

### Operations Window first assignment

Before the upcoming three-Setup production activation, Operations should produce one consolidated
`THREE_SETUP_OPERATIONS_PLAN_V1` for user review. It should be a plan, not production execution,
and should classify each item as `PRE_LAUNCH_REQUIRED`, `IMMEDIATE_POST_LAUNCH`, or `DEFERRED`.
At minimum it must resolve:

- the exact authoritative durable-asset inventory and production paths for the three-Setup release;
- whether legacy `runtime.db`, `public.env` and `risk-configuration.json` remain authoritative and
  how MultiAsset EvidenceStore / Registry are bound;
- the off-host Restic repository/provider choice using mature/provider-native capabilities first;
- repository credential and Restic recovery-password custody, including an independently
  recoverable copy outside the production host;
- first real backup qualification: normal `restic check`, at least one deep `check --read-data`,
  temporary restore, metadata/hash/SQLite/Registry/config validation and exact-Git-SHA rebuild
  procedure;
- backup cadence, retention/maintenance policy, failure alerting and a minimal mature scheduler
  such as systemd timer if appropriate;
- release installation, exact-SHA deployment, service/config/credential installation, start/restart
  gates, health/readiness verification and rollback;
- target-host public-network, provider connectivity, fixed-universe capacity/load and recovery
  verification appropriate to the real release;
- logs, telemetry, alerting and operator-visible health needed to detect stalled data, reconnect
  loops, failed notifications, backup failures and disk/storage growth;
- credential rotation/recovery, host replacement, incident response and disaster-recovery drills;
- cloud/provider resource inventory, cost controls, snapshot lifecycle and legacy-runtime
  decommission steps;
- what can safely wait until after first live Shadow evidence exists, so operations work does not
  delay launch through unnecessary infrastructure expansion.

The Operations Window should return an execution-ready operations strategy to the user and
Engineering Window. It should not itself redefine Product scope or Strategy semantics, and it
should not perform production mutation without a separate user authorization.

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
