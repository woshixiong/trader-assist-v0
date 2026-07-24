# Practical Human-Machine Engineering Lessons and Successor Handoff V1

**Status:** DRAFT PERSISTENT GOVERNANCE INPUT  
**Date:** 2026-07-25  
**Project:** Trader Assist V0 / First Launch / Trade OS mainline  
**Audience:** Product Authority, Engineering Optimization, Project Control, Writer, Reviewer, future successor windows

## 1. Why this document exists

A First Launch verifier/evidence task expanded into a large, unstable contract that combined runtime startup, process identity, database failure handling, deployment safety, evidence schemas, rollback, uninstall, operational collection, and review-artifact integrity.

Repeated task-packet review failed before implementation could safely begin. The failure was not primarily a coding-capability failure. It was a task-design, product-boundary, and human-machine allocation failure.

This document preserves the resulting correction so that a window change does not recreate the same mistake.

## 2. Incident conclusion

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

The old route must remain historical. Do not reactivate it by producing another larger prompt, another V3/V4 packet, or another framework intended to close every previous finding at once.

## 3. Core product identity

Trader Assist is initially a practical decision-support system for an experienced trader.

The current objective is not institution-grade autonomy. It is the simplest, fastest, most stable minimum system that provides real trading value and can be validated through real use.

The governing development order is:

```text
CURRENT USER VALUE
→ SIMPLEST ADEQUATE CONTROL
→ HUMAN-MACHINE RESPONSIBILITY SPLIT
→ MINIMUM RELIABLE IMPLEMENTATION
→ REAL-OPERATION EVIDENCE
→ LATER AUTOMATION AND HARDENING
```

A theoretically complete system that misses the launch window and cannot be operated simply is less useful than a smaller system that safely supports the experienced operator now.

## 4. Mandatory complex-problem decision method

When a problem is difficult, entangled, or expensive, do not assume it must be solved through deeper implementation.

Before assigning a Writer, answer in order:

1. **Necessity** — What concrete current product failure does the problem prevent? Is it required in this phase?
2. **Blocking detail** — Which exact technical detail creates the obstacle?
3. **Smallest direct fix** — What is the minimum correction that removes that detail?
4. **Alternative** — Can an existing platform function, a different interface, or a different boundary solve it more simply?
5. **Human-assisted control** — Can the experienced operator perform a simple, explicit, low-friction action safely?
6. **Bypass or deferral** — Can the obstacle leave the critical path without weakening a concrete supported-path safety invariant?
7. **Automation trigger** — What future authority or product change makes machine enforcement mandatory?

A difficult task is not implementation-ready merely because it is important. If an AI Writer prompt cannot be made concise, bounded, and internally consistent, return to design and decomposition.

## 5. Human participation is a first-class system component

The experienced operator is not an external inconvenience. The operator is part of the supported system architecture.

### Current software responsibilities

- continuously collect and validate public ETH market data;
- calculate signals and complete TradePlans;
- preserve manual-only and `NOT_SUBMITTED` boundaries;
- expose a simple current usability result;
- expose time, price, entry, chase, stop, target, size, and risk information;
- avoid presenting a non-READY state as usable.

### Current operator responsibilities

- periodically refresh status during active trading;
- ignore every system signal when status is not READY or is unknown;
- compare signal time and price with the live market in seconds;
- reject moved-away, stale, contextually weak, or personally unsuitable trades;
- decide whether, when, and how to execute manually;
- continue discretionary trading independently when the assistant is unavailable;
- restart the service after persistent failure;
- capture bounded logs for targeted engineering diagnosis.

### Value created by the human role

- prevents an advisory error from automatically becoming a position;
- provides rapid market-context judgment that is expensive to encode early;
- identifies stale signals through direct time/price comparison;
- allows the project to defer premature monitoring, recovery, audit, and UI frameworks;
- keeps the First Launch critical path small without removing current safety;
- supplies real-operation feedback for later automation priorities.

This is intentional product design, not unfinished automation.

## 6. Conditions under which human-assisted control is valid

Human-assisted control may replace disproportionately expensive automation only when all are true:

- execution is manual;
- no account, wallet, private-key, signing, nonce, or exchange-write authority exists;
- the status and required action are simple and unambiguous;
- the task is low-frequency or naturally aligned with normal trading supervision;
- omission or delay cannot automatically create or enlarge a position;
- the system clearly states when output must be ignored;
- a short recovery and escalation path exists.

Human participation must not be used to excuse:

- hidden or ambiguous state;
- repeated interpretation of shell, procfs, cgroup, or systemd races;
- timing-critical low-level recovery;
- frequent work that materially interferes with trading;
- automatic exchange-write risk;
- missing hard risk controls after automatic or one-click execution is introduced.

## 7. First Launch route produced by this review

The accepted planning direction is:

```text
freeze PR #45
→ create one clean small branch from accepted main
→ implement FIRST_LAUNCH_SIMPLE_STATUS_V1
→ reuse the existing runtime health authority
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

The status question is only:

```text
MAY THE OPERATOR RELY ON CURRENT SYSTEM SIGNALS?
```

Allowed results:

- `READY` — signals may be considered, subject to human judgment;
- `NOT_READY` — ignore signals and recheck later;
- `STATUS_UNKNOWN` — ignore signals and recover or escalate if persistent.

Ordinary `NOT_READY` does not require a new stop feature.

Persistent failure uses:

```text
recheck
→ existing systemd restart
→ bounded journal output
→ targeted diagnosis of the concrete failure
```

## 8. Explicitly rejected First Launch expansion

Do not add the following merely to make the system appear complete:

- systemd `Type=notify` integration;
- reconstruction of wrapper/env/Bash/Python startup races;
- complete 17-argv or process-identity evidence protocols;
- automatic stop on ordinary NOT_READY;
- automatic rollback, uninstall, or self-healing;
- web dashboard or FinalShell-specific integration;
- generalized monitoring or evidence frameworks;
- 34-field producer/consumer manifests;
- pre-commit mega-bundles and detached integrity systems;
- automatic notification-expiry systems that duplicate rapid human time/price validation;
- any feature with no current operational value.

These items may be preserved in the deferred register with an explicit future trigger. They must not silently re-enter the current queue.

## 9. Task-design rules learned from the failure

1. One Writer task has one primary engineering outcome.
2. Separate product/runtime, verifier, deployment/operations, evidence/audit, and governance layers by default.
3. Stabilize producers before consumers and evidence aggregation.
4. Do not block runtime value on an unrelated audit-format framework.
5. No more than three tightly coupled blockers unless indivisibility is proven.
6. Two substantive task-packet failures trigger decomposition, not another additive revision.
7. A new subsystem, schema, collector, or generalized framework triggers scope reset.
8. Writer Agents implement frozen semantics; they do not invent missing architecture.
9. Deadline pressure is handled by reducing coupling and using legitimate human controls, not by combining unrelated work or deleting core tests.
10. Compare automation cost and risk against operator burden before automating an edge case.
11. Existing platform functions such as systemd restart, SSH, Terminal, and journal output should be preferred over new products when adequate.
12. The simplest adequate interface is normally superior to a new dashboard during First Launch.
13. Preserve deferred work, but do not confuse preservation with immediate implementation.
14. Real-operation evidence determines later V0 and mainline priorities.

## 10. Signal-display conclusions

The underlying TradePlan already includes created time, expiry time, reference price, Mark Price, entry zone, planned entry, chase limit, stop, targets, quantity, notional, and planned risk.

Before First Launch acceptance, verify the actual human-visible delivery surface, not merely the stored payload.

The operator-facing first view should prominently show:

- direction;
- FAST or STANDARD;
- setup type;
- created time;
- expiry time;
- reference price or Mark Price;
- entry zone;
- planned entry;
- chase limit;
- stop;
- TP1 and TP2;
- quantity and notional;
- planned risk;
- manual execution required;
- `NOT_SUBMITTED`.

If reference or Mark Price is absent from the actual receiving interface, use one separate tiny display-only task. Do not combine it with the status task or redesign strategy, persistence, or notification transport.

## 11. Operator commands and manual evidence

The canonical command source is:

- `governance/FIRST_LAUNCH_OPERATOR_COMMANDS_V1.md`

The operator agreed to keep a minimal manual record during the initial real-operation period. Record only meaningful events:

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

## 12. Successor engineering-optimization window intake

A new Engineering Optimization window should begin by reading:

1. `AGENTS.md`;
2. `governance/PROJECT_RULES_INDEX.md`;
3. `governance/PROJECT_THREE_PHASE_PLAN_AND_DEFERRED_REGISTER_V1.md`;
4. `governance/ENGINEERING_WORKFLOW_MODEL_ROUTING_AND_RESOURCE_POLICY_V1.md`;
5. this document;
6. `governance/FIRST_LAUNCH_OPERATOR_COMMANDS_V1.md`;
7. live PR #44 and PR #45 state;
8. the current main HEAD and active First Launch implementation PRs;
9. the Project Control output for `FIRST_LAUNCH_SIMPLE_STATUS_V1`.

It must reverify all mutable GitHub, CI, branch, and worktree facts. Snapshot SHAs in this document are historical orientation only.

The successor must not reopen the complete PR #45 repair merely because individual old findings remain recorded.

## 13. Current authority boundary at handoff

This governance record does not authorize:

- code implementation outside the separately accepted status task;
- Mark Ready or merge;
- deployment or runtime start;
- smoke execution;
- AWS or credential access;
- account access;
- signing or nonce handling;
- order submission, cancellation, or automatic SL/TP;
- autonomous trading.

Project Control is responsible for live-state verification and exact execution. Engineering Optimization owns architecture, scope, task executability, and complexity control.

## 14. Future automatic-trading transition

Human judgment remains valuable in a future automated system for supervision, risk limits, anomaly response, performance review, strategy suspension, deployment authority, and incident recovery.

However, once automatic or one-click execution can create financial exposure, the following may no longer depend only on human observation:

- stale-data blocking;
- maximum position and exposure limits;
- order-price deviation;
- duplicate and idempotency controls;
- protective order lifecycle;
- automatic trading suspension;
- kill switch;
- watchdog and alerting;
- safe recovery and reconciliation.

The human role changes; it does not disappear.

## 15. Final invariant

```text
DO NOT AUTOMATE COMPLEXITY MERELY BECAUSE AUTOMATION IS POSSIBLE.

BUILD THE SMALLEST RELIABLE ASSISTANT THAT CREATES CURRENT USER VALUE.

USE THE EXPERIENCED OPERATOR WHERE HUMAN JUDGMENT IS SIMPLE, SAFE, AND FAST.

AUTOMATE ONLY WHEN CURRENT VALUE, SCALE, FREQUENCY, OR FINANCIAL AUTHORITY REQUIRES IT.
```
