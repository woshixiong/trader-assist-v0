# Practical Human-Machine Engineering Lessons and Successor Handoff V1

**Status:** DRAFT PERSISTENT GOVERNANCE INPUT  
**Date:** 2026-07-25  
**Project:** Trader Assist V0 / First Launch / Trade OS mainline  
**Audience:** Product Authority, Engineering Optimization, Project Control, Writer, Reviewer, successor windows

## 1. Incident and correction

A First Launch verifier/evidence task expanded into one unstable contract covering runtime startup, process identity, database errors, deployment safety, evidence schemas, rollback, uninstall, operational collection, and review-artifact integrity.

Repeated packet review failed before implementation could safely start. This was primarily a task-design, product-boundary, and human-machine allocation failure—not a coding-model failure.

```text
INCIDENT_TYPE:
ENGINEERING_TASK_DESIGN_AND_DECOMPOSITION_FAILURE

FAILED_ROUTE:
PR #45 CONSOLIDATED SIX-FILE VERIFIER / EVIDENCE REPAIR

PRIMARY_CAUSE:
UNNECESSARY COUPLING OF SEPARABLE PROBLEMS

CORRECTIVE_DIRECTION:
PRACTICAL HUMAN-CONTROLLED FIRST LAUNCH
```

The old route is historical. Do not reactivate it through another larger prompt, another V3/V4 packet, or a framework intended to close every old finding at once.

## 2. Core product identity

Trader Assist is initially a practical decision-support system for an experienced trader. The current goal is not institution-grade autonomy. It is the simplest, fastest, most stable minimum system that creates real trading value and can be improved from real-operation evidence.

```text
CURRENT USER VALUE
→ SIMPLEST ADEQUATE CONTROL
→ HUMAN-MACHINE RESPONSIBILITY SPLIT
→ MINIMUM RELIABLE IMPLEMENTATION
→ REAL-OPERATION EVIDENCE
→ LATER AUTOMATION AND HARDENING
```

A theoretically complete system that misses the launch window and cannot be operated simply is less useful than a smaller system that safely supports the experienced operator now.

## 3. Mandatory complex-problem method

Before assigning a difficult task, answer in order:

1. **Necessity** — What concrete current failure does it prevent? Is it required in this phase?
2. **Blocking detail** — Which exact detail creates the obstacle?
3. **Smallest direct fix** — What minimum change removes it?
4. **Alternative** — Can an existing platform function, simpler interface, or different boundary solve it?
5. **Human-assisted control** — Can the experienced operator perform a simple, explicit, low-friction action safely?
6. **Bypass or deferral** — Can it leave the critical path without weakening a current safety invariant?
7. **Automation trigger** — What future authority, frequency, scale, or financial exposure makes machine enforcement mandatory?

If an AI Writer prompt cannot be concise, bounded, and internally consistent, the task is not implementation-ready. Return to design and decomposition.

## 4. Human participation is a system component

### Software responsibilities

- collect and validate public ETH market data;
- calculate signals and complete TradePlans;
- preserve manual-only and `NOT_SUBMITTED` boundaries;
- expose simple current usability status;
- expose time, price, entry, chase, stop, target, size, and risk information;
- never present a non-READY state as usable.

### Operator responsibilities

- refresh status during active trading;
- ignore all system signals when status is not READY or is unknown;
- compare signal time and price with the live market in seconds;
- reject moved-away, stale, contextually weak, or personally unsuitable trades;
- decide whether, when, and how to execute manually;
- continue discretionary trading independently when the assistant is unavailable;
- restart after persistent failure;
- capture bounded logs for targeted diagnosis.

### Value created by the operator

- prevents an advisory error from automatically becoming a position;
- supplies market-context judgment that is expensive to encode early;
- detects stale signals through rapid time/price comparison;
- allows premature monitoring, recovery, audit, and UI frameworks to be deferred;
- keeps the First Launch critical path small without removing current safety;
- produces real-operation evidence for later priorities.

This is intentional product design, not unfinished automation.

## 5. When human-assisted control is valid

It may replace disproportionate automation only when all are true:

- execution is manual;
- no account, wallet, private-key, signing, nonce, or exchange-write authority exists;
- status and required action are simple and unambiguous;
- the action is low-frequency or naturally part of trading supervision;
- omission or delay cannot automatically create or enlarge a position;
- the system clearly states when output must be ignored;
- a short recovery and escalation path exists.

It must not excuse hidden state, interpretation of low-level races, timing-critical repair, frequent work that interferes with trading, automatic exchange-write risk, or missing hard controls after automatic or one-click execution is introduced.

## 6. Current First Launch route

```text
freeze PR #45
→ create one clean small branch from accepted main
→ implement FIRST_LAUNCH_SIMPLE_STATUS_V1
→ reuse existing runtime health authority
→ expose minimum health and market-data freshness
→ provide one read-only ta-status command
→ focused deterministic tests
→ one focused independent Review
→ exact-head CI
→ separately authorized real-host deployment and qualification
→ configure Mac Terminal shortcuts
→ deliver exact operator command list
→ accepted real operation
```

The status command answers only:

```text
MAY THE OPERATOR RELY ON CURRENT SYSTEM SIGNALS?
```

- `READY` — signals may be considered, subject to human judgment.
- `NOT_READY` — ignore signals and recheck later.
- `STATUS_UNKNOWN` — ignore signals; recover or escalate if persistent.

Ordinary `NOT_READY` does not require a stop feature.

```text
recheck
→ existing systemd restart
→ bounded journal output
→ targeted diagnosis of the concrete failure
```

## 7. Explicitly rejected First Launch expansion

Do not add merely for completeness:

- systemd `Type=notify`;
- wrapper/env/Bash/Python race reconstruction;
- complete argv or process-identity evidence protocols;
- automatic stop on ordinary NOT_READY;
- automatic rollback, uninstall, or self-healing;
- web dashboard or FinalShell-specific integration;
- generalized monitoring or evidence frameworks;
- 34-field producer/consumer manifests;
- pre-commit mega-bundles and detached integrity systems;
- automatic expiry systems that duplicate rapid human time/price validation;
- features with no current operational value.

Preserve legitimate future work in the deferred register with an explicit trigger; do not silently return it to the active queue.

## 8. Task-design rules learned

1. One Writer task has one primary outcome.
2. Separate runtime, verifier, deployment, evidence, and governance layers by default.
3. Stabilize producers before consumers and aggregation.
4. Do not block user value on unrelated audit formats.
5. Use no more than three tightly coupled blockers unless indivisibility is proven.
6. Two substantive packet failures trigger decomposition, not another additive revision.
7. A new subsystem, schema, collector, or generalized framework triggers scope reset.
8. Writers implement frozen semantics; they do not invent architecture.
9. Reduce coupling under deadline pressure; do not combine unrelated work or delete core tests.
10. Compare automation cost against operator burden and safety.
11. Prefer adequate existing tools such as systemd restart, SSH, Terminal, and bounded journal output.
12. Prefer the simplest adequate interface over a new dashboard.
13. Preserve deferred work without treating preservation as immediate implementation.
14. Use real-operation evidence to choose V0 and mainline priorities.

## 9. Signal-display conclusion

The TradePlan already contains created time, expiry time, reference price, Mark Price, entry zone, planned entry, chase limit, stop, targets, quantity, notional, and planned risk.

Before First Launch acceptance, verify the actual human-visible delivery surface, not only stored payloads. The first view should prominently show:

- direction and FAST/STANDARD;
- setup type;
- created and expiry time;
- reference price or Mark Price;
- entry zone and planned entry;
- chase limit;
- stop, TP1, TP2;
- quantity, notional, planned risk;
- manual execution required;
- `NOT_SUBMITTED`.

If reference or Mark Price is absent, use one separate tiny display-only task. Do not combine it with status work or redesign strategy, persistence, or notification transport.

## 10. Commands and initial human evidence

Canonical command source:

- `governance/FIRST_LAUNCH_OPERATOR_COMMANDS_V1.md`

During initial real operation, record only meaningful events:

```text
time
status: READY / NOT_READY / STATUS_UNKNOWN
signal received: yes / no
signal used: yes / no
reason rejected
failure observed
restart performed
```

This is evidence collection, not a new application feature.

## 11. Successor Engineering Optimization intake

A new Engineering Optimization window must begin by reading:

1. `AGENTS.md`;
2. `governance/PROJECT_RULES_INDEX.md`;
3. `governance/PROJECT_THREE_PHASE_PLAN_AND_DEFERRED_REGISTER_V1.md`;
4. `governance/ENGINEERING_WORKFLOW_MODEL_ROUTING_AND_RESOURCE_POLICY_V1.md`;
5. this document;
6. `governance/FIRST_LAUNCH_OPERATOR_COMMANDS_V1.md`;
7. live PR #44 and PR #45 state;
8. current main HEAD and all active First Launch implementation PRs;
9. the latest Project Control output for `FIRST_LAUNCH_SIMPLE_STATUS_V1`.

Reverify all mutable GitHub, CI, branch, and worktree facts. Snapshot SHAs are orientation only. Do not reopen the complete PR #45 repair merely because old findings remain recorded.

The successor window should monitor Project Control execution, review any executability or scope-escalation result, protect the minimum practical route, and intervene only when an actual architectural or supported-path blocker requires Engineering Optimization authority.

## 12. Authority boundary at handoff

This record does not authorize:

- implementation outside the separately accepted status task;
- Mark Ready or merge;
- deployment, service start, runtime, or smoke;
- AWS or credential access;
- account access, signing, or nonce handling;
- order submission, cancellation, or automatic SL/TP;
- autonomous trading.

Project Control owns live-state verification and exact execution. Engineering Optimization owns architecture, task scope, executability, and complexity control.

## 13. Future automatic-trading transition

Human judgment remains important for supervision, risk limits, anomaly response, performance review, strategy suspension, deployment authority, and incident recovery.

Once automatic or one-click execution can create financial exposure, these may no longer depend only on human observation:

- stale-data blocking;
- maximum position and exposure limits;
- order-price deviation;
- duplicate/idempotency controls;
- protective order lifecycle;
- automatic trading suspension and kill switch;
- watchdog and alerting;
- safe recovery and reconciliation.

The human role changes; it does not disappear.

## 14. Final invariant

```text
DO NOT AUTOMATE COMPLEXITY MERELY BECAUSE AUTOMATION IS POSSIBLE.

BUILD THE SMALLEST RELIABLE ASSISTANT THAT CREATES CURRENT USER VALUE.

USE THE EXPERIENCED OPERATOR WHERE HUMAN JUDGMENT IS SIMPLE, SAFE, AND FAST.

AUTOMATE WHEN CURRENT VALUE, FREQUENCY, SCALE, OR FINANCIAL AUTHORITY REQUIRES IT.
```
