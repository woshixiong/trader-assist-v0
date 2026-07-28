# Project Rules Index

Successor windows read the following order before acting:

1. `AGENTS.md`
2. `governance/PROJECT_RULES_INDEX.md`
3. `governance/SIMPLICITY_FIRST_ENGINEERING_AND_PROBLEM_SOLVING_RULE_V1.md`
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

## Mandatory project-wide simplicity gate

The binding rule is:

`governance/SIMPLICITY_FIRST_ENGINEERING_AND_PROBLEM_SOLVING_RULE_V1.md`

It applies to First Launch, V0, mainline and all later development, research, review, deployment,
operations, recovery and higher-authority stages.

After the minimum real safety, authority, correctness and recovery boundary is preserved, every
problem must use the simplest viable route. Simplicity is measured across total cost, including:

- implementation and calendar time;
- operator actions and attention;
- diagnosis, evidence, review and testing;
- deployment, rollback and recovery;
- recurring maintenance;
- external services, credentials, credits, quotas and outages;
- future replacement and migration.

Every material task must include a compact `SIMPLICITY_GATE` that identifies:

1. the single exact current question;
2. the selected minimum route;
3. the fewest necessary components, hops, credentials and operator actions;
4. the minimum safety boundaries that cannot be removed;
5. total cost rather than code-writing cost alone;
6. success, failure, maximum-attempt and replacement conditions;
7. optional work excluded from the current critical path.

The normal verification order is:

1. one-component or direct-connectivity test;
2. bounded pairwise integration;
3. minimum required failure-semantics test;
4. controlled end-to-end test;
5. broader regression only when the changed boundary requires it.

Do not start with a full multi-component workflow when a smaller test answers the current question.
Do not require a long manual production-shaped payload when a built-in fixture or short synthetic
command can prove the same boundary.

Third-party UI is not a stable source of truth. Instructions must use the operator's actual current
interface, and an assumed or remembered control must not become the only test route. Button
inactivity, syntax highlighting and layout differences are not proof of a code defect.

For one bounded route, one evidence-based correction plus one exceptional correction is the
maximum. After two ineffective attempts, the route must be reduced, replaced or abandoned unless
new evidence proves that one small and specific correction will close it immediately. Sunk effort
does not authorize continued complexity.

A third-party service may enter a critical path only after its credits, quotas, exhaustion
behavior, rate limits, outage risk, credential scope, rotation and direct alternative have been
assessed. A generic relay must not be inserted when a safe direct integration with a bounded
adapter is simpler.

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

Efficiency is the primary optimization target after the minimum real safety boundary is preserved.

Before developing automation, determine:

- event frequency;
- active guided human time;
- whether an existing accepted capability can complete the task;
- actual risk reduction;
- implementation, operator, review, testing, maintenance and recovery cost;
- third-party quota, credit and outage exposure.

Do not build product-grade or institution-grade functionality for a low-frequency event that one
operator can complete safely with limited guided work.

Use this preferred order:

1. existing accepted capability or command;
2. direct provider-native interface, API or webhook;
3. short checklist or one-off command;
4. minimal task-specific script or adapter;
5. maintained external tool only when it reduces total complexity;
6. small permanent component after repeated use proves net value;
7. framework or service only when scale, authority, availability or compliance requires it.

## Today-first launch scheduling rule

The user has fixed the immediate objective as completing First Launch within the current day.

Current priority:

`FIRST_LAUNCH_ACTIVATION_P0__NO_NEW_ONE_DAY_OR_LONGER_DEVELOPMENT_ON_CRITICAL_PATH`

Any new task expected to require one calendar day or more must move after First Launch unless it is
demonstrated to be a direct launch-safety blocker. Deferred work is retained; it is not abandoned.

The minimum local automatic `ta-status` shortcut may be prepared only because it is bounded to
approximately 20-45 minutes, uses the already accepted command and is not a launch blocker. If the
direct Discord adapter, credential ingress, Stage 4F, smoke or recovery closeout encounters delay,
the shortcut moves immediately after First Launch.

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

For the immediate First Launch and ordinary low-frequency deployment events, use one fixed host,
one exact SHA, existing P4A guidance, `ta-status`, one controlled restart, 3+3 readiness
observations and a temporary host-specific command bundle.

The more complete automated qualification capability remains in the backlog at the lowest
priority:

`DEFERRED_LOWEST_PRIORITY__NO_CURRENT_IMPLEMENTATION_AUTHORITY`

It must not displace First Launch, real-operation stability, strategy, risk-control or required
account/execution safety work. It may be reconsidered when development capacity exists or when a
real migration, major redeployment, disaster recovery, multi-host, multi-operator,
higher-authority or compliance need justifies it.

When reconsidered, evaluate provider snapshots, images, maintained external tools and other
standard solutions before custom development. Use a clean task from current main; do not resume or
patch PR #48.

The former permanent-abandonment ruling is superseded but retained as historical decision context.
The failed implementation, review findings, RR-01 through RR-08 and proposed two-script
architecture remain preserved for future research.

## Current First Launch notification direction

The user has rejected the unnecessary Pipedream relay after the workflow configuration and testing
route imposed excessive UI complexity and repeated ineffective manual steps.

Selected minimum direction:

`Trader Assist durable outbox -> Discord Incoming Webhook -> private Discord channel`

Decision status:

`USER_SELECTED__REMOVE_PIPEDREAM_FROM_FIRST_LAUNCH_P0__MINIMUM_DIRECT_DISCORD_ADAPTER`

This is a First Launch activation direction. It does not select the final V0 or mainline
notification, mobile-access or execution-confirmation architecture. Implementation still requires a
separately bounded engineering task, review, CI and separately authorized deployment/smoke.

The minimum direct route must satisfy:

1. Reuse the existing durable notification outbox and retry classifications; do not redesign the
   persistence or strategy chain.
2. Convert the approved internal notification payload into the minimum Discord-compatible
   `content` or `embeds` request. Do not send incompatible raw internal JSON directly.
3. Use Discord's confirmed-response behavior and mark delivery successful only after Discord
   returns an accepted response with a valid created-message identity.
4. Preserve retryable status for timeout, rate-limit, network and eligible server failures; do not
   falsely acknowledge delivery.
5. Treat the Discord webhook URL as a credential. It must not enter Git history, PR text,
   screenshots, logs, shell history or ordinary evidence.
6. Use a private server/channel and dedicated webhook with the smallest practical scope, external
   recoverability and revoke/rotate procedure.
7. Keep the payload restricted to the already-approved public-data TradePlan and operator card. It
   must contain no exchange account, wallet, private key, signing, nonce or order-write data.
8. Prove one controlled success path and one minimum controlled failure path before accepted real
   operation.
9. `DELIVERED` means Discord accepted and created the message; it does not mean the operator viewed,
   approved or traded it.
10. Do not add a Discord bot, OAuth application, generic relay, new daemon, framework or separate
    service for First Launch.

Pipedream is removed from the current P0 path. Its prior setup may be retained only as historical
evidence and must not consume further launch-critical effort.

## Selected minimum automatic `ta-status` shortcut

The user has selected the minimum automatic refresh form because it reduces repeated manual work
and the risk of forgetting to refresh.

Decision:

`USER_SELECTED__OPTIONAL_SAME_DAY_OPERATOR_SHORTCUT__NOT_A_LAUNCH_BLOCKER`

The minimum form is one operator-started Mac Terminal shortcut that:

- establishes one persistent SSH/Terminal session;
- periodically executes the already accepted remote `ta-status` command;
- uses a bounded interval, initially 5-10 seconds;
- displays the current refresh timestamp;
- displays the existing `READY`, `NOT_READY` or `STATUS_UNKNOWN` result and reason;
- keeps exit codes 0, 1 and 2 as normal classifications rather than terminating the loop;
- stops manually with `Ctrl+C`;
- overwrites or clears any old `READY` result if SSH, sudo or command execution stops;
- displays an unmistakable fail-closed stopped message.

The minimum shortcut must not:

- modify server runtime code, strategy, notification outbox or trading authority;
- add a server daemon or systemd service;
- add macOS login auto-start or LaunchAgent;
- add background autonomous reconnection;
- add desktop notification;
- require a product-code PR merely to create the local shortcut;
- replace direct Discord delivery, Stage 4F, smoke, 3+3 checks or one controlled restart.

Expected active work is approximately 20-45 minutes. It must not hold First Launch acceptance and
must move after First Launch if the main activation path slips.

## Post-First-Launch formal automatic-status backlog

The expanded formal version is retained for later development and is not abandoned.

Backlog status:

`POST_FIRST_LAUNCH_BACKLOG__NO_CURRENT_CRITICAL_PATH_AUTHORITY`

Candidate capabilities include a repository-backed `ta-watch`, login startup, LaunchAgent
lifecycle, background operation, bounded reconnect, sleep/wake recovery, stale-screen detection,
single-instance locking, desktop alerts, bounded logs, installation/upgrade/uninstall and broader
tests.

Before activating this backlog, Product Function and Priority Control must determine which
capabilities are actually required. Engineering Optimization must compare the smallest script,
direct provider-native tooling and maintained alternatives. The formal version must not be assumed
to require every candidate capability.

## Notification and operator-access deferred-options register

Recorded options, with no V0/mainline selection or implementation authority:

1. direct maintained provider adapters when they minimize dependencies and maintenance;
2. maintained external relays only when quotas, credits and failure behavior are known and total
   complexity is lower than a direct adapter;
3. the selected bounded minimum Mac Terminal health/freshness shortcut;
4. the post-First-Launch formal automatic-status backlog;
5. custom Mac Terminal notification and local desktop notification;
6. local or self-hosted operator dashboard reusing durable notification data;
7. private desktop-and-mobile web/PWA access for V0 monitoring;
8. authenticated human confirm/reject/expiry flow separate from notification delivery;
9. confirmed-order execution with server-side revalidation, idempotency and audit evidence;
10. higher-authority automatic trading with independent runtime, risk, execution and emergency
    controls.

Future product planning must keep these meanings separate:

- notification delivered or displayed;
- operator viewed or acknowledged;
- operator approved or rejected a specific plan;
- server accepted an execution authorization;
- order submission, acknowledgement, fill and protective-action state.

No current `DELIVERED`, Terminal output, webhook success or message receipt may be reinterpreted as
trading approval or exchange-write authority.

## Current unresolved and backlog register

### Immediate First Launch P0

1. authorize a bounded minimum direct Discord adapter task;
2. implement and review only the Discord-compatible payload transformation and confirmed response;
3. complete exact-head CI;
4. prove one controlled Discord success path;
5. prove one minimum controlled failure path without false delivery acknowledgement;
6. create, preserve, install and validate the real Discord webhook credential without disclosure;
7. authorize and complete Stage 4F runtime and notification smoke;
8. complete the initial 3 `ta-status` READY observations;
9. perform exactly one controlled restart;
10. complete the post-restart 3 READY observations;
11. close out inactive, disabled and no-runtime-process state;
12. create and verify the minimum SQLite backup outside the single-host failure boundary;
13. finish the recovery card and snapshot-or-rebuild decision;
14. complete accepted-real-operation review and explicit user authorization.

### Optional same-day, non-blocking

15. prepare the minimum local `ta-watch` or equivalent shortcut;
16. validate READY, NOT_READY, STATUS_UNKNOWN and SSH-failure behavior;
17. add the one-command startup instruction to the Mac operator command card.

### Governance and window transition

18. independently review PR #51 at its new exact Head;
19. verify the project-wide simplicity rule, direct Discord decision and product-decision gate are
    internally consistent;
20. decide Mark Ready and merge only under later separate user authorization;
21. start fresh Project Control and Engineering Optimization windows from the reviewed authority.

### Post-First-Launch backlog

22. evaluate and schedule only the required formal automatic-status capabilities;
23. revisit the final V0 notification and provider architecture;
24. revisit desktop/mobile access and dashboard/PWA options;
25. revisit authenticated human confirmation and expiry;
26. later evaluate confirmed-order execution and automatic trading under separate risk and authority
    design;
27. retain the PR #48 replacement host-qualification research at lowest priority;
28. address all other V0 and mainline work through both the product-decision gate and the
    project-wide simplicity gate.
