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

## Mandatory product-function decision gate

Engineering Optimization owns feasibility, decomposition, cost, risk, reliability, testing,
review and implementation-path analysis. It does not own product-function selection.

Before a task contract, branch, Writer assignment or implementation is authorized, Engineering
Optimization must identify every decision point that could change:

- the operator's normal workflow or number of required actions;
- notification channel, delivery semantics or device availability;
- user interface, dashboard, Terminal interaction or mobile access;
- the market, account, strategy, risk or execution information shown to the user;
- human confirmation, rejection, expiry or approval behavior;
- account, order, cancellation, protective-order or automatic-trading authority;
- deployment topology, third-party service dependency or recurring operating burden;
- which current work is temporary, reusable, deferred, replaced or part of the future product path.

For each such point, Engineering Optimization must return a compact decision packet containing:

1. the exact product question;
2. the smallest viable options;
3. implementation and calendar cost;
4. reliability, security and maintenance tradeoffs;
5. reuse value and expected replacement cost;
6. effect on the First Launch, V0 and mainline critical paths;
7. its engineering recommendation, explicitly labeled as non-authoritative.

The packet is routed to Product Function and Priority Control. Development may proceed only after
an explicit product-direction ruling is returned and recorded. Project Control may execute the
accepted direction but may not infer or choose one.

A pure defect correction that preserves already accepted product behavior does not require a new
product decision. Any behavior, workflow, channel, authority, external dependency or future-path
change does.

If a product decision point is discovered after work begins, the active lane must safe-stop,
preserve the current evidence and return the decision point before further implementation. Sunk
engineering effort, an existing partial implementation or launch pressure does not authorize an
implicit product decision.

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

## Current First Launch notification direction

The user has selected a maintained external relay as the temporary fastest First Launch route.
The currently expected chain is:

`Trader Assist durable outbox -> Pipedream HTTPS trigger -> private Discord webhook/channel`

This is a temporary First Launch activation decision. It is not the selected V0 or mainline
notification, mobile-access or execution-confirmation architecture.

The temporary relay must satisfy all of the following:

1. Pipedream must complete the downstream Discord send before returning a success response to
   Trader Assist. A default or early `200 OK` before downstream success is prohibited.
2. When the Discord send fails, the workflow must not return a success response. The Trader Assist
   notification must remain retryable rather than being falsely recorded as delivered.
3. The Pipedream trigger, Discord webhook and any authorization values are credentials. They must
   not enter Git history, PR text, screenshots, logs, shell history or ordinary evidence bundles.
4. Use a private Discord server/channel and a dedicated webhook with the smallest practical scope.
   Preserve a recoverable external credential source and a revoke/rotate procedure.
5. The payload remains restricted to the already-approved public-data TradePlan and operator card.
   It must contain no exchange account, wallet, private key, signing, nonce or order-write data.
6. One controlled end-to-end test must prove the actual success path. One controlled failure test
   must prove that a downstream Discord failure is not acknowledged as successful delivery.
7. `DELIVERED` under this temporary route means only that the configured relay completed the
   accepted downstream send. It does not prove that the operator viewed, approved or traded it.
8. Stage 4F, runtime, smoke and credential installation remain separately authorized operations.
   Selecting the route does not itself authorize those actions.

## Low-cost automatic `ta-status` candidate

The proposed automatic refresh does not mean a new notification system and does not mean simulated
keyboard input. It means one operator-started Terminal session periodically executes the already
accepted `ta-status` command and displays the latest health and data-freshness result.

The smallest future form is:

- one persistent SSH/Terminal session rather than opening a new SSH connection for every poll;
- a bounded interval such as 5-10 seconds, subject to later product and operations review;
- manual start and stop by the operator;
- display of the existing `READY`, `NOT_READY` or `STATUS_UNKNOWN` result and reason;
- no server runtime-code, strategy, notification-outbox or trading-authority change.

Potential benefits:

- removes repeated manual typing while the operator is already trading on the computer;
- keeps health and freshness continuously visible when a Discord notification arrives;
- can expose stale data, disconnects and service failures sooner;
- has very low implementation and maintenance cost if kept as an operator shortcut.

Limitations:

- it is not a notification transport and cannot replace Pipedream or Discord;
- it does not prove that a specific notification was delivered or viewed;
- it is not trading approval or execution authorization;
- it does not replace 3+3 readiness observations, controlled restart evidence or formal smoke;
- aggressive polling or repeated SSH handshakes are prohibited.

Current status:

`DEFERRED_CANDIDATE__NO_CURRENT_IMPLEMENTATION_AUTHORITY__NOT_A_FIRST_LAUNCH_BLOCKER`

The user will provide separate research before any implementation decision.

## Notification and operator-access deferred-options register

Current user direction:

- do not authorize a custom Terminal notification implementation during the immediate First
  Launch finalization merely to avoid a maintained external relay;
- do not spend additional First Launch time selecting or designing the final V0 notification,
  mobile-access or execution-confirmation architecture;
- preserve the current durable notification/outbox work and record future options for later
  product planning;
- the user will provide separate research before any later implementation decision;
- automatic invocation of existing `ta-status` or equivalent health/freshness checks is a future
  candidate, not current implementation authority.

Recorded options, with no V0/mainline selection or implementation authority:

1. maintained external relay to a desktop/mobile messaging endpoint for the fastest First Launch
   activation;
2. bounded automatic Mac Terminal health/freshness monitoring using the existing status command;
3. custom Mac Terminal notification and local desktop notification;
4. local or self-hosted operator dashboard reusing durable notification data;
5. private desktop-and-mobile web/PWA access for V0 monitoring;
6. authenticated human confirm/reject/expiry flow that is separate from notification delivery;
7. confirmed-order execution with server-side revalidation, idempotency and audit evidence;
8. higher-authority automatic trading with independent runtime, risk, execution and emergency
   controls;
9. direct maintained provider adapters where they reduce risk and maintenance compared with a
   generic relay.

Future product planning must keep these meanings separate:

- notification delivered or displayed;
- operator viewed or acknowledged;
- operator approved or rejected a specific plan;
- server accepted an execution authorization;
- order submission, acknowledgement, fill and protective-action state.

No current `DELIVERED`, Terminal output, webhook success or message receipt may be reinterpreted
as trading approval or exchange-write authority.

## Current unresolved register

The following remain open and require their own accepted authority or later product decision:

1. configure and validate the temporary Pipedream-to-Discord workflow and its failure semantics;
2. create, preserve, install and validate the real notification credential without disclosure;
3. authorize and complete Stage 4F runtime, notification smoke, 3+3 checks, one controlled restart
   and final inactive/disabled/no-process closeout;
4. finish the minimum SQLite backup, off-host verification, recovery card and snapshot-or-rebuild
   closeout required before accepted real operation;
5. independently review and later decide Mark Ready and merge for this governance Draft PR;
6. revisit automatic `ta-status`, final notification architecture, desktop/mobile access, human
   confirmation and execution only after Product Function and Priority Control accepts a later
   decision packet.
