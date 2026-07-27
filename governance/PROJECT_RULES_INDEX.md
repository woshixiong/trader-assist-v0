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

## Today-first launch scheduling rule

The user has fixed the immediate objective as completing First Launch within the current day.

Current priority:

`FIRST_LAUNCH_ACTIVATION_P0__NO_NEW_ONE_DAY_OR_LONGER_DEVELOPMENT_ON_CRITICAL_PATH`

Any new task expected to require one calendar day or more must be moved after First Launch unless
it is demonstrated to be a direct launch safety blocker. Deferred work is retained; it is not
abandoned.

The minimum local automatic `ta-status` shortcut may be prepared only because it is bounded to
approximately 20-45 minutes, uses the already accepted command and is not a launch blocker. If
Pipedream, Discord, credential ingress, Stage 4F, smoke or recovery closeout encounters delay, the
shortcut moves immediately after First Launch.

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

## Selected minimum automatic `ta-status` shortcut

The user has selected the minimum automatic refresh form because it reduces repeated manual work
and reduces the risk of forgetting to refresh.

Decision:

`USER_SELECTED__OPTIONAL_SAME_DAY_OPERATOR_SHORTCUT__NOT_A_LAUNCH_BLOCKER`

The minimum form is not a new notification system and does not mean simulated keyboard input. It
is one operator-started Mac Terminal shortcut that:

- establishes one persistent SSH/Terminal session;
- periodically executes the already accepted remote `ta-status` command;
- uses a bounded interval, initially 5-10 seconds;
- displays the current refresh timestamp;
- displays the existing `READY`, `NOT_READY` or `STATUS_UNKNOWN` result and reason;
- keeps exit codes 0, 1 and 2 as normal classifications rather than terminating the loop;
- stops manually with `Ctrl+C`;
- overwrites or clears any old `READY` result if SSH, sudo or command execution stops;
- displays an unmistakable fail-closed stopped message such as
  `STATUS MONITOR STOPPED | IGNORE SYSTEM SIGNALS`.

The minimum shortcut must not:

- modify server runtime code, strategy, notification outbox or trading authority;
- add a server daemon or systemd service;
- add macOS login auto-start or LaunchAgent;
- add background autonomous reconnection;
- add desktop notification;
- require a product-code PR merely to create the local shortcut;
- replace Pipedream, Discord, Stage 4F, smoke, 3+3 checks or one controlled restart.

Expected work:

- command or shell-function preparation: about 5-15 minutes;
- local setup and operator-card integration: about 5-15 minutes;
- controlled validation on the approved host: about 10-20 minutes;
- total active time: approximately 20-45 minutes.

Scheduling:

- prepare only after the primary Pipedream/Discord launch path is moving normally, or in parallel
  without consuming the critical operator;
- do not hold First Launch acceptance for this shortcut;
- if the main launch path slips, move this item immediately after First Launch.

## Post-First-Launch formal automatic-status backlog

The expanded formal version is retained for later development and is not abandoned.

Backlog status:

`POST_FIRST_LAUNCH_BACKLOG__NO_CURRENT_CRITICAL_PATH_AUTHORITY`

Candidate capabilities to evaluate later:

1. a repository-backed and tested `ta-watch` script;
2. automatic start at macOS login;
3. LaunchAgent lifecycle management;
4. background operation;
5. bounded automatic SSH reconnection;
6. Mac sleep/wake recovery;
7. stale-screen detection and explicit last-success age;
8. single-instance locking;
9. local desktop notification on state transition;
10. structured local logs with retention limits and no secrets;
11. installation, upgrade, uninstall and rollback procedures;
12. test coverage for READY, NOT_READY, STATUS_UNKNOWN, SSH failure, sudo failure, sleep/wake and
    reconnect behavior;
13. operator documentation and support boundary;
14. later evaluation of whether a dashboard or private web/PWA replaces the Terminal watcher.

Before activating this backlog, Product Function and Priority Control must determine which
capabilities are actually required. Engineering Optimization must then compare the smallest
script, provider-native tooling and any maintained open-source alternative. The formal version
must not be assumed to require all listed capabilities.

## Notification and operator-access deferred-options register

Recorded options, with no V0/mainline selection or implementation authority:

1. maintained external relay to a desktop/mobile messaging endpoint for the fastest First Launch
   activation;
2. the selected bounded minimum Mac Terminal health/freshness shortcut;
3. the post-First-Launch formal automatic-status backlog;
4. custom Mac Terminal notification and local desktop notification;
5. local or self-hosted operator dashboard reusing durable notification data;
6. private desktop-and-mobile web/PWA access for V0 monitoring;
7. authenticated human confirm/reject/expiry flow that is separate from notification delivery;
8. confirmed-order execution with server-side revalidation, idempotency and audit evidence;
9. higher-authority automatic trading with independent runtime, risk, execution and emergency
   controls;
10. direct maintained provider adapters where they reduce risk and maintenance compared with a
    generic relay.

Future product planning must keep these meanings separate:

- notification delivered or displayed;
- operator viewed or acknowledged;
- operator approved or rejected a specific plan;
- server accepted an execution authorization;
- order submission, acknowledgement, fill and protective-action state.

No current `DELIVERED`, Terminal output, webhook success or message receipt may be reinterpreted
as trading approval or exchange-write authority.

## Current unresolved and backlog register

### Immediate First Launch P0

1. configure and validate the temporary Pipedream-to-Discord workflow;
2. prove that Discord success occurs before Pipedream returns 2xx;
3. prove that controlled downstream Discord failure is not acknowledged as successful delivery;
4. create, preserve, install and validate the real notification credential without disclosure;
5. authorize and complete Stage 4F runtime and notification smoke;
6. complete the initial 3 `ta-status` READY observations;
7. perform exactly one controlled restart;
8. complete the post-restart 3 READY observations;
9. close out inactive, disabled and no-runtime-process state;
10. create and verify the minimum SQLite backup outside the single-host failure boundary;
11. finish the recovery card and snapshot-or-rebuild decision;
12. complete accepted-real-operation review and explicit user authorization.

### Optional same-day, non-blocking

13. prepare the minimum local `ta-watch` or equivalent shortcut;
14. validate READY, NOT_READY, STATUS_UNKNOWN and SSH-failure behavior;
15. add the one-command startup instruction to the Mac operator command card.

### Governance and window transition

16. independently review PR #51 at its current exact Head;
17. decide Mark Ready and merge only under later separate user authorization;
18. start a fresh Project Control window using the current handoff;
19. start a fresh Engineering Optimization window using the current handoff.

### Post-First-Launch backlog

20. evaluate and schedule the formal automatic-status capabilities listed above;
21. revisit the final V0 notification and provider architecture;
22. revisit desktop/mobile access and dashboard/PWA options;
23. revisit authenticated human confirmation and expiry;
24. later evaluate confirmed-order execution and automatic trading under separate risk and
    authority design;
25. retain the PR #48 replacement host-qualification research at lowest priority;
26. address other deferred V0 and mainline work only through the product-decision gate.
