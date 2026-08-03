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

## Mature-solution-first and cumulative-delivery rule

The project must not spend its limited engineering capacity rebuilding mature generic
infrastructure when a maintained external solution can satisfy the current authority,
correctness, operational, licensing and lifecycle requirements.

The fixed solution hierarchy is:

```text
REUSE MATURE MAINTAINED SOLUTION
→ USE PROVIDER-NATIVE CAPABILITY
→ ADD THE THINNEST PRACTICAL ADAPTER
→ IMPLEMENT SMALL PROJECT-OWNED DOMAIN LOGIC
→ BUILD CUSTOM INFRASTRUCTURE ONLY AS A DOCUMENTED LAST RESORT
```

Before authorizing custom infrastructure, the current engineering stage must identify the
relevant external tools, frameworks, libraries, provider-native capabilities or proven design
patterns and record:

- the exact candidates reviewed;
- the capability that can be reused;
- the remaining fit gap;
- data-correctness and authority implications;
- operational and deployment implications;
- license and maintenance implications;
- the smallest bounded spike that can confirm or reject the candidate;
- why custom development remains necessary if every acceptable candidate is rejected.

A mature external solution that passes those gates must be reused rather than reimplemented.
External adoption must remain bounded by thin project adapters so that project-owned contracts
and proprietary strategy logic are not surrendered to a framework.

Project-owned development and research capacity should be concentrated on the project's unique
advantages:

- Scanner and market-selection logic;
- Setup and Market Event semantics;
- asset-neutral Strategy Kernel;
- PlanDraft / TradeIntent;
- strategy evidence, T/S/R and Outcome;
- strategy research, validation and rapid iteration.

Generic high-difficulty infrastructure work is prohibited unless a bounded spike demonstrates
that no acceptable maintained solution exists and the capability is necessary for the current
approved stage. Technical difficulty, novelty or architectural ambition are not product value by
themselves.

Development investment must also be proportional to expected reuse. Prefer work that can remain
valid across shadow validation, human-confirmed execution and future automated execution. For a
one-time or low-frequency task, use an existing command, checklist, temporary script or maintained
external tool instead of creating permanent product-grade automation.

The fixed delivery loop is:

```text
TEST SMALL
→ OBSERVE REAL EVIDENCE
→ REVIEW
→ DECIDE
→ IMPLEMENT THE MINIMUM COHERENT CHANGE
→ FORWARD VALIDATE
→ ITERATE
```

Do not attempt to build a perfect system or complete trading engine in one stage. Each stage should
close only a small number of high-certainty uncertainties, preserve the reusable results, and avoid
large speculative commitments. Major investment before a bounded spike is prohibited. Multiple
small, independently validated capabilities should accumulate into the larger system without
requiring broad rewrites.

Every proposed stage must answer:

- Does a mature maintained solution already exist?
- What is the thinnest integration that preserves project authority?
- Must this capability be built now?
- Will the result remain reusable in later stages?
- Can a smaller spike close the uncertainty first?
- Does the work create a new long-term maintenance burden?
- Is the work primarily advancing proprietary strategy value or rebuilding generic infrastructure?

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
