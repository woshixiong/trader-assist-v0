# Trader Assist Three-Phase Plan and Deferred Register V1

**Status:** DRAFT / PERSISTENT PLANNING AUTHORITY AFTER MERGE  
**Project:** Trader Assist V0 / First Launch / Trade OS mainline  
**Purpose:** separate immediate launch work, preserved residual work, and post-launch product/mainline work without silent loss.

## 1. Binding planning model

All planning must be organized into exactly three top-level parts:

1. **PART A — Before First Launch accepted real operation**
2. **PART B — Deferred, residual, and preserved work**
3. **PART C — After First Launch: evidence, V0 product planning, V0 implementation, and mainline development**

The separation is a scheduling boundary, not a deletion boundary.

A finding may leave PART A when:

- it is proven not to affect the current supported product boundary or a concrete current safety invariant; and
- it is either unnecessary under the current human-controlled boundary or entered into PART B with an ID, source, risk, trigger, owner, and acceptance criteria.

No proven current safety blocker may be deferred. Audit completeness, future automated-execution requirements, and institution-grade operational hardening are not automatically current safety blockers.

---

# PART A — Before First Launch accepted real operation

## A1. Product and authority boundary

First Launch remains a restricted public-data, human-controlled signal viability pilot:

- ETH is the primary traded asset;
- public market data only;
- FAST and STANDARD signal paths remain visible under their accepted contracts;
- complete human-readable TradePlan fields remain mandatory;
- account equity and per-trade risk remain explicit external inputs;
- execution remains human manual and discretionary;
- the experienced operator may accept, reject, ignore, or independently override every recommendation;
- no account, wallet, private-key, signing, nonce, order-write, cancellation, or automatic SL/TP authority;
- no autonomous trading;
- one supported dedicated host and one bounded public runtime.

Any change to these boundaries requires Product Authority, Engineering Optimization, independent Review, and separate user authorization.

## A2. Current engineering critical path

Project Control must always reverify the exact live state. The former PR #45 consolidated six-file verifier/evidence route is superseded and must not be reactivated.

The current closure model is:

```text
verify live GitHub state and freeze the superseded PR #45 route
→ issue one executable FIRST_LAUNCH_SIMPLE_STATUS_V1 task
→ create a clean small branch from the accepted main baseline
→ implement one minimal runtime health/freshness producer and one read-only status command
→ run focused deterministic tests
→ publish one small Draft PR
→ exact-head CI
→ one focused independent code/operations Review
→ at most one bounded repair for a proven supported-path blocker
→ merge decision and post-merge CI
→ separately authorized supported-host deployment
→ one real-host status, signal-display, restart, and bounded-log qualification
→ configure the final Mac Terminal shortcuts and deliver the exact operator command list
→ accepted real operation
```

The status command has one product question:

```text
MAY THE OPERATOR RELY ON CURRENT SYSTEM SIGNALS?
```

Its required results are:

- `READY` — current system signals may be considered, subject to human judgment;
- `NOT_READY` — ignore system signals and recheck later;
- `STATUS_UNKNOWN` — ignore system signals and escalate if persistent.

Ordinary NOT_READY does not require service stop. Persistent failure uses the existing systemd restart command. Restart failure uses one bounded journal command and targeted diagnosis.

Forbidden scope expansion before First Launch:

- systemd `Type=notify` integration;
- startup wrapper/env/Bash/Python race reconstruction;
- complete argv/process-identity evidence protocols;
- automated stop, rollback, uninstall, self-healing, or dashboard products;
- 34-field evidence-producer frameworks;
- pre-commit mega-bundles or generalized audit systems;
- notification-expiry automation that duplicates rapid human time/price validation;
- features with no current operational value.

Forbidden shortcuts:

- ignoring a proven supported-path blocker;
- treating static fixtures as real-host proof;
- starting deployment or runtime before exact authority;
- weakening the no-account/no-exchange-write boundary;
- presenting ambiguous status or omitting the operator action;
- allowing the minimal status task to absorb deferred monitoring, audit, rollback, or future automated-trading requirements.

## A3. First Launch completion criteria

Before accepted real operation, the project must have:

- accepted exact code and documentation scope for `FIRST_LAUNCH_SIMPLE_STATUS_V1`;
- no unresolved Blocker or High finding within that supported scope;
- no supported-path acceptance-blocking Medium finding;
- successful exact-head CI;
- accepted focused independent Review;
- deterministic deployment and exact-SHA/clean-checkout binding;
- credential preparation and validation without secret disclosure;
- one real-host qualification proving the service, current process, health snapshot, READY state, approved mode/scope, and market-data freshness are coherently reported;
- a simple status result that always tells the operator whether current signals may be relied upon;
- human-visible actionable signal output that prominently includes direction, speed, setup type, created time, expiry time, reference or mark price, entry zone, planned entry, chase limit, stop, TP1, TP2, quantity, notional, planned risk, manual execution, and NOT_SUBMITTED status;
- confirmation that FAST remains valid for 180 seconds and STANDARD for 900 seconds under the existing contract;
- confirmation that the operator can rapidly compare signal price/time with the live market and reject stale or moved-away opportunities;
- an exact daily and recovery command list;
- a short recovery route: recheck → existing systemd restart → bounded journal output → engineering escalation;
- Mac Terminal shortcut configuration included in the launch task list and completed before routine daily use, without creating a new UI or service;
- no account or exchange-write authority introduced.

The following are not First Launch completion requirements under the current human-controlled boundary:

- automatic service stop on NOT_READY;
- complete rollback or uninstall automation;
- complete process-transition proof;
- complete audit manifest or review-bundle framework;
- automatic notification expiry suppression;
- web dashboard, phone app, or FinalShell-specific integration;
- autonomous recovery.

## A4. Current parallel non-code work

The following may run in parallel but must not mutate the active code branch or block the code critical path:

- preparation of the exact operator command list;
- preparation of the Mac Terminal SSH/function configuration with real values supplied at deployment time;
- preparation of focused Review criteria;
- deferred-register and product-planning intake maintenance;
- exact-head Review packet preparation while CI runs.

Minimum V0 transition work and post-launch architecture work remain deferred unless separately reactivated.

## A5. Resource constraint

Codex is reserved for the small proven code-critical status task. Documentation, command-list preparation, planning, read-only Review, and deferred-register maintenance must use ordinary ChatGPT or TRAE where appropriate.

Open-ended repair loops, additive task-packet revisions, speculative hardening, and implementation prompts that cannot be stated clearly and concisely are prohibited.

If two substantive task-packet Reviews fail, the task returns to necessity, blocking detail, direct solution, alternative, human-assisted control, and bypass analysis. It does not receive another additive packet revision.

## A6. Human-machine operating model

Software responsibilities:

- continuously collect and validate public ETH market data;
- calculate signals and complete TradePlans;
- preserve the manual-only and NOT_SUBMITTED boundaries;
- expose a simple current usability result;
- expose signal time, price, entry, risk, and invalidation information.

Operator responsibilities:

- periodically refresh status during active trading;
- ignore all system signals when status is not READY or is unknown;
- compare signal creation/expiry and reference price with the live market;
- reject moved-away, stale, contextually weak, or personally unsuitable trades;
- decide whether, when, and how to execute manually;
- continue discretionary trading independently when the assistant is unavailable;
- use restart and bounded-log commands only when persistent failure requires recovery or diagnosis.

This allocation is an intentional First Launch product design, not unfinished automation. Before automatic or one-click execution is introduced, every operator-dependent safety control must be re-evaluated and replaced where automatic financial exposure could otherwise occur.

---

# PART B — Deferred, residual, and preserved work

## B1. Register rules

Each item must retain:

- ID;
- title and domain;
- source/provenance;
- exact description;
- reason deferred;
- First Launch blocker status;
- risk if never completed;
- V0 value;
- mainline value;
- activation trigger;
- dependencies;
- owner authority window;
- acceptance criteria;
- status;
- final disposition.

Initial status is `DEFERRED_PRESERVED` unless explicitly stated otherwise.

## B2. Product, execution, and evidence backlog

### DFR-01 — Human-confirmed order execution chain

- **Source:** accepted product direction and First Launch deferral.
- **Scope:** direction, entry, stop, targets, quantity, TIF, post-only, confirmation, submission, and pre-submit risk validation.
- **Why deferred:** First Launch remains manual and public-data only.
- **Risk if omitted permanently:** persistent manual latency and missed opportunities; no controlled path toward V0 execution.
- **Trigger:** Gate B proves signal value and material manual-execution gap.
- **Owner:** Product Authority first, then Engineering Optimization.

### DFR-02 — Order lifecycle and protective controls

Includes idempotency, duplicate-submit prevention, acknowledgement, partial fill, cancellation, timeout, recovery, protective SL/TP, and emergency stop.

- **Risk:** exchange-state inconsistency and unmanaged exposure if execution is later added without lifecycle closure.
- **Trigger:** before any Testnet or Mainnet order-write authority.

### DFR-03 — Signal, shadow, decision, order, fill, and outcome closure

- **Scope:** stable identifiers and correspondence from signal through outcome, including fees, slippage, MFE/MAE, and attribution.
- **Risk:** unverifiable performance and weak learning loop.
- **Trigger:** V0 scope selection or any real-order pilot.

### DFR-04 — Gate B real-operation evidence and product replanning

Collect signal quality, frequency, expectancy, drawdown, regime coverage, manual execution loss, runtime reliability, notification reliability, and user judgment.

- **Trigger:** First Launch accepted real operation.
- **Rule:** evidence informs the next product configuration; it does not automatically authorize any feature.

### DFR-05 — Additional strategies and market coverage

Includes complementary strategies, low-frequency mitigation, BTC, ETHBTC, and regime-specific coverage.

- **Trigger:** Gate B demonstrates a material strategy-quality, frequency, or regime-coverage gap.
- **Rule:** ETH remains primary unless Product Authority changes it.

### DFR-06 — Microstructure and contextual data

Includes BBO, L2, trades, OFI, CVD, liquidation context, fuller OI/Funding, and adaptive timeframe inputs.

- **Risk:** overbuilding before evidence; conversely, permanent omission may limit signal precision.
- **Trigger:** product evidence and a bounded source-authority design.

### DFR-07 — Reporting, dashboard, and automated learning loop

Includes performance reports, EV/DD, strategy/version attribution, visualization, and controlled improvement proposals.

- **Trigger:** sufficient accepted evidence sample.
- **Rule:** automatic production-rule mutation remains prohibited without separate governance.

## B3. Runtime, data, and operational backlog

### DFR-08 — Database lifecycle

Backup, restore, migration, corruption recovery, disk capacity, retention, abnormal-shutdown recovery, and future schema versioning.

- **Risk:** data loss and inability to evolve persistence safely.
- **Trigger:** immediately after launch planning; before schema-changing V0 work.

### DFR-09 — Monitoring, alerting, SLO, and escalation

Process/session health, data freshness, WebSocket reconnect state, latency, missing/duplicate candles, OI/Funding staleness, notification failure, database failure, resource use, and operator escalation.

- **Trigger:** post-launch operations hardening; critical portions may be promoted earlier if host evidence exposes a real blocker.

### DFR-10 — Credential lifecycle

Rotation, revocation, expiry, least privilege, audit, leakage response, future multiple credentials, and deployment-system integration.

- **Trigger:** after First Launch secret ingress is proven stable; mandatory before account or signing credentials.

### DFR-11 — Real Ubuntu/systemd integration automation

Automated supported-host tests for unit installation, credential directory behavior, wrapper-to-Python transition, cgroup identity, start/stop/restart, rollback, and uninstall.

- **Risk:** host behavior remains partly manual and expensive to revalidate.
- **Trigger:** after current manual supported-host acceptance stabilizes.

### DFR-12 — Versioned evidence schema and producer/consumer mapping

Machine-readable evidence versions, producer identity, consumer rules, bundle hashes, compatibility, and audit retention.

- **Trigger:** when more than one stable consumer or repeated operator evidence mapping exists.
- **Rule:** do not preserve unnecessary placeholder fields merely to justify a framework.

### DFR-13 — Data quality, replay, backfill, and historical validation

Missing/duplicate/stale data, timestamp drift, open/closed candle boundaries, replay, backfill, source reconciliation, historical regime coverage, and sample-size guidance.

- **Trigger:** post-launch evidence and any new data source.

### DFR-14 — Shared runtime/path-validation architecture

Potential reusable path validation, process identity, verifier interfaces, and operator tooling.

- **Trigger:** at least two accepted consumers demonstrate real duplication.
- **Rule:** no speculative framework before justified reuse.

## B4. Engineering process, Agent, and configuration backlog

### DFR-15 — Codex configuration package intake and activation

Known external design inputs include current-state audit, target configuration, skill architecture, model routing matrix, token-efficiency standard, packet templates, benchmark plan, implementation packet, validator, package index, and manifest.

- **Current status:** external reviewed design input; not automatically installed or canonical.
- **Required action:** perform exact package intake, provenance check, accepted-version selection, and bounded activation after First Launch or at a safe engineering checkpoint.
- **Risk:** inconsistent Codex behavior and repeated token waste if left unresolved.

### DFR-16 — TRAE Skills/Commands and IDE SOLO operationalization

- **Source:** merged Workflow V3 and direct-activation preflight.
- **Scope:** install project Skills/Commands, confirm project context, exact model selection, worktree control, authority isolation, and fallback behavior.
- **Trigger:** safe stage boundary and explicit user mode selection.

### DFR-17 — Engineering Agent capability registry and routing matrix

Track harness/model strengths, limitations, read/write authority, prompt-size limits, benchmark provenance, and accepted routing.

- **Current status:** deferred by prior engineering governance.
- **Trigger:** accepted checkpoint after First Launch; update only from observed evidence.

### DFR-18 — OpenCode plus DeepSeek V4 Pro fallback route

- **Scope:** user-owned API configuration, bounded repository access, model identity, logging/secret boundaries, and write authorization.
- **Trigger:** Codex quota below threshold, Codex unavailable, or a deliberately selected safe stage boundary.

### DFR-19 — Engineering automation M1.2, M1.3, M2 and launch/handoff reduction

- **Source:** PR #24 retrospective.
- **Problem:** M1.1 did not eliminate manual launch, window selection, handoff, and stale PR-body work.
- **Trigger:** after First Launch; select only automation with measurable interaction or cycle-time benefit.

### DFR-20 — Token and repair-budget governance

Track per-stage quota use, repeated repair causes, context churn, maximum repair rounds, emergency reserve, and model-switch thresholds.

- **Trigger:** continuous engineering governance; update after each expensive failure.

### DFR-21 — Writer/Reviewer test-harness quality standard

Bounded deterministic harnesses, realistic command status, no assertion rewriting, no command-status bypass, no mock-proves-mock tests, and external watchdogs where needed.

- **Trigger:** all future operational or subprocess test work.

### DFR-22 — Root-cause compression and stage granularity standard

One root cause may have many tests but must not become many Writers, commits, or microtasks by default.

- **Trigger:** all repair planning.

## B5. Historical technical debt and follow-ups

### DFR-23 — PR #42 / PR #43 / replacement-line disposition

After the accepted replacement is merged and stable:

- preserve failure evidence and lessons;
- identify the canonical implementation;
- close superseded Draft PRs;
- clean branches/worktrees only with authority;
- prevent failed code from being reused as canonical.

### DFR-24 — PR #33 and PR #35 governance reconciliation

These Draft PRs contain valuable engineering and product decisions but are stale relative to current `main`.

- **Action:** migrate accepted content into the consolidated governance set, independently review, then close or explicitly supersede the old Drafts.

### DFR-25 — `CODEX.md` stale-current-task cleanup

`CODEX.md` contains historical task-specific state and must not remain the default current authority indefinitely.

- **Action:** convert it into a stable executor entrypoint pointing to `AGENTS.md`, `PROJECT_RULES_INDEX.md`, current Project State, and active task packet.

### DFR-26 — Rate-limit authority conflict and blocking unknowns

Historical governance records an unresolved official-source variant conflict and mandatory unknowns.

- **Risk:** unsafe future live-transport/account assumptions.
- **Trigger:** before any authority depending on disputed rate limits.
- **Rule:** remain fail closed until independently resolved.

### DFR-27 — Runtime hardening follow-ups

Preserve known non-blocking items such as early-exception SQLite cleanup coverage and exact authorization-header type/control-character validation.

### DFR-28 — Deployment-package residuals

Preserve `systemd-analyze verify` on Linux, same-UID TOCTOU residual, and older misleading/early-exit test debt.

### DFR-29 — Action SHA and schema/tooling maintenance

Preserve GitHub Action SHA refresh, possible byte-based schema drift checks, tuple-permutation regressions, and future runtime actor-continuity decisions.

### DFR-30 — Superseded PR #30 salvage provenance

Keep the historical PR and external salvage hashes as evidence only. Do not treat uncommitted/unreviewed salvage as accepted source.

## B6. No-silent-loss requirement

Before any non-blocking finding is excluded from current scope, Project Control must report:

```text
DEFERRED_ITEM_ID:
REGISTER_UPDATED:
SOURCE_RECORDED:
RISK_IF_NEVER_COMPLETED:
ACTIVATION_TRIGGER:
ACCEPTANCE_CRITERIA:
```

`UNRECORDED_KNOWN_DEFERRED_ITEMS` must equal `0` at every major phase closeout.

---

# PART C — After First Launch

## C1. Immediate post-launch sequence

```text
FIRST LAUNCH ACCEPTED REAL OPERATION
→ controlled observation
→ Gate B evidence collection
→ First Launch final baseline and residual report
→ deferred-register reconciliation
→ V0 pre-development product-planning intake
→ Product Function and Priority decision
→ Engineering Optimization decomposition
→ Project Control activation
→ V0 implementation stages
```

There is no automatic fixed feature sequence after First Launch.

## C2. Product-planning gate

The Product Function and Priority window must read:

- `AGENTS.md`;
- `governance/PROJECT_RULES_INDEX.md`;
- this register;
- `governance/V0_PRE_DEVELOPMENT_PRODUCT_PLANNING_INTAKE_V1.md`;
- First Launch final product/technical baseline;
- Gate B evidence;
- Workstream A Minimum V0 transition package;
- prior V0 plans;
- current V0/mainline architecture and authority boundaries.

It must classify every candidate as:

- `V0_REQUIRED`;
- `MAINLINE_REQUIRED`;
- `EVIDENCE_TRIGGERED`;
- `OPTIONAL`;
- `REJECTED_WITH_REASON`.

The required output is `V0_PRODUCT_SCOPE_DECISION_V1`.

## C3. Engineering planning gate

Only after the product decision may Engineering Optimization define:

- coherent stage objectives;
- dependencies;
- exact file/source allowlists;
- Writer/model/harness routing;
- commit and repair budgets;
- tests and Reviews;
- resource and token budgets;
- rollout and rollback;
- authority gates.

Every V0 and mainline task must first apply the practical problem sequence: necessity, blocking detail, smallest direct fix, alternative, human-assisted control, and safe bypass. No one-finding-per-task, one-file-per-Writer, speculative framework expansion, or open-ended investment into a deeply entangled problem is allowed.

## C4. V0 and mainline execution

Project Control executes accepted product and engineering decisions. It must not activate all deferred items automatically.

Priorities must be evidence- and dependency-driven. Likely early domains include:

- operational reliability and monitoring;
- database lifecycle;
- Gate B evidence closure;
- signal-to-outcome correspondence;
- human-confirmed execution only if product evidence supports it;
- complementary strategies only if product evidence supports them;
- credential and order-lifecycle safety before any exchange write;
- shared architecture only after repeated accepted duplication.

The experienced operator remains part of the product design even as automation increases. Human judgment must not be removed merely to satisfy architectural purity; it is replaced only where measured value and automatic financial exposure justify a harder machine control.

## C5. Governance closure after launch

After the consolidated governance PR is merged and First Launch is stable:

- update final baseline and residual documents;
- reconcile and close or supersede PR #33 and PR #35;
- close superseded implementation PRs after preserving evidence;
- update `PROJECT_RULES_INDEX.md`;
- update `CODEX.md` stable entrypoint;
- keep every deferred item until explicit disposition;
- maintain GitHub as the cross-window canonical source.

## C6. Final invariant

First Launch scope reduction is temporary scheduling, not permanent product erasure.

V0 planning must begin with:

```text
UNRECORDED_KNOWN_DEFERRED_ITEMS = 0
```

and may begin implementation only after the Product Function and Priority window has issued an accepted `V0_PRODUCT_SCOPE_DECISION_V1`.