# Trader Assist / Trade OS — External Mature Solution Selection and Adoption Rule V1

**Status:** TASK-CONDITIONAL PROCEDURE CANDIDATE  
**Effective date:** 2026-09-07  
**Normative owner:** `UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md`  
**Scope:** selection, rejection, composition, bounded customization, adoption, migration, upgrade and re-evaluation of provider-native, standard/official, mature maintained external frameworks, libraries, SDKs, platforms, services and infrastructure components.

This procedure operationalizes the project-wide mature-solution invariants in Unified V2. It is not a second engineering constitution. Unified V2 governs if there is any conflict.

It grants no implementation, Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, wallet/signing, exchange-write, order-submission or autonomous-trading authority.

---

## 1. Objective

Optimize for:

```text
VALIDATED PRODUCT VALUE
/
TOTAL LIFECYCLE ENGINEERING BURDEN
```

Trader Assist / Trade OS differentiates through trading strategy, research, decision logic and project-specific policy. Commodity trading infrastructure should be owned by the best-fitting mature owner whenever one exists.

Selection must be reproducible, evidence-backed and auditable. No framework, SDK, platform or library may be selected because it is fashionable, familiar, popular, easy to start, already partly used or subjectively described as “better”.

The rule is neither `EXTERNAL_FRAMEWORK_FIRST` nor `CUSTOM_FIRST`. The target is:

```text
PROJECT_DIFFERENTIATION_OWNED_BY_US
+
COMMODITY_INFRASTRUCTURE_OWNED_BY_BEST_FITTING_MATURE_OWNER
+
THIN_REPLACEABLE_BOUNDARIES
+
ONE_AUTHORITY_PER_RESPONSIBILITY
```

---

## 2. Mandatory capability classification

Before candidate search or Writer dispatch, classify the responsibility:

```text
CAPABILITY_CLASS=
STRATEGY_DIFFERENTIATOR
| COMMODITY_INFRASTRUCTURE
| THIN_INTEGRATION
```

Classification follows responsibility semantics, not file, module or class names.

If one current module contains both project-specific strategy and generic infrastructure, record `MIXED_BOUNDARY` as an observed condition and separate the responsibilities analytically before selection. A mixed file is not a fourth permanent capability class and must not be used to disguise commodity responsibility as strategy IP.

### 2.1 Strategy Decision Engine — project-owned core IP

`STRATEGY_DECISION_ENGINE` means project-specific trading intelligence and policy, including as applicable:

- Setup and signal semantics;
- Scanner, ranking and opportunity selection;
- Thesis / Attempt semantics where actually defined by current project authority;
- entry, exit, re-entry and winner-management policy;
- strategy-specific sizing and risk policy;
- strategy-specific features, regime logic, research and evidence semantics;
- economic decisions specific to the project.

A mature framework may host, call or execute these decisions, but project-specific strategy semantics should remain independently understandable, testable and replaceable where practical.

### 2.2 Trading Infrastructure Engine — commodity by default

`TRADING_INFRASTRUCTURE_ENGINE` means generic trading/runtime infrastructure, including as applicable:

- REST / WebSocket transport and session management;
- subscriptions, acknowledgements, heartbeats, reconnect, backoff and resubscription;
- generic market-data ingestion and normalization;
- generic clocks, scheduling and orchestration;
- generic order management and order lifecycle;
- venue adapters, signing transport and venue mechanics;
- fill, order, position and account reconciliation;
- generic portfolio/account state;
- generic pre-trade limits, kill switches and non-strategy risk enforcement;
- generic persistence, restart, recovery and replay plumbing;
- generic backtest / sandbox / shadow / live runtime mechanics;
- deployment, observability and workflow plumbing.

These examples are not exhaustive.

### 2.3 Thin integration

`THIN_INTEGRATION` is project-owned code whose only purpose is to translate between a mature owner and a stable project contract.

A thin integration must satisfy all applicable conditions:

```text
USES_OFFICIAL_OR_STABLE_EXTENSION_SEAM=YES
OWNS_GENERIC_RECONNECT=NO
OWNS_GENERIC_OMS=NO
OWNS_GENERIC_PORTFOLIO=NO
OWNS_GENERIC_RISK=NO
OWNS_GENERIC_DURABLE_RECOVERY=NO
OWNS_SECOND_AUTHORITATIVE_STATE=NO
REPLACEABLE_WITHOUT_CORE_STRATEGY_REWRITE=YES
```

LOC and file count are warning signals, not the semantic definition.

If integration code starts owning generic reconnect, OMS, portfolio, generic risk, durable recovery or a second authoritative truth, then:

```text
THIN_INTEGRATION -> COMMODITY_INFRASTRUCTURE
MATURE_SOLUTION_GATE_REOPEN=MANDATORY
```

---

## 3. Mature capability no-rebuild gate

Permanent rule:

```text
COMMODITY_INFRASTRUCTURE
+
FITTING_PROVIDER_NATIVE_OR_STANDARD_OR_MATURE_MAINTAINED_SOLUTION_EXISTS
=
MATURE_EXTERNAL_OWNER_REQUIRED
CUSTOM_FROM_SCRATCH_IMPLEMENTATION=PROHIBITED
SECOND_PROJECT_OWNED_IMPLEMENTATION=PROHIBITED
```

Allowed integration order:

```text
CONFIGURATION
-> OFFICIAL CONFIG / EXTENSION / PLUGIN
-> THIN ADAPTER
-> UPSTREAM CONTRIBUTION
-> BOUNDED CUSTOMIZATION ONLY WHEN THIS PROCEDURE ALLOWS IT
-> CUSTOM COMMODITY IMPLEMENTATION ONLY UNDER EXPLICIT EXCEPTION
```

A long-lived invasive private fork of mature framework core is prohibited by default. A material private fork is treated as project-owned commodity infrastructure and must pass the custom-exception gate.

---

## 4. Prohibited mature-route rejection reasons

None of the following is sufficient by itself to reject a fitting mature route:

```text
SUNK_COST
EXISTING_CUSTOM_CODE
MIGRATION_INCONVENIENCE_ALONE
NO_NEW_DEPENDENCY_PREFERENCE
LAUNCH_PROXIMITY
ARCHITECTURAL_FAMILIARITY
NOT_100_PERCENT_IDENTICAL_TO_CURRENT_INTERNAL_API
PREFERENCE_TO_CONTROL_EVERY_IMPLEMENTATION_DETAIL
BELIEF_THAT_ONE_MORE_REPAIR_MAY_WORK
WRITER_FAMILIARITY_WITH_THE_CUSTOM_ROUTE
```

Also:

```text
NO_NEW_DEPENDENCY != SIMPLICITY_PASS
```

A dependency may reduce total complexity when it replaces a larger project-owned responsibility. Total lifecycle burden, not dependency count or current LOC, is the governing metric.

---

## 5. Formal definitions: Mature and Fitting

### 5.1 Mature Qualification Gate

An external route may be described as `MATURE_MAINTAINED_SOLUTION` only after an applicability-scaled qualification checks:

```text
CANONICAL_SOURCE_VERIFIED
EXACT_PROJECT_OR_VENDOR_VERIFIED
OFFICIAL_REPOSITORY_OR_DISTRIBUTION_VERIFIED
CURRENT_MAINTENANCE_STATUS
RELEASE_HEALTH
SECURITY_DISCLOSURE_PATH
LICENSE_CLARITY
DOCUMENTATION_QUALITY
API_OR_VERSION_POLICY
TEST_OR_CI_PRACTICE
DEPENDENCY_HEALTH
PRODUCTION_OR_REAL_USAGE_EVIDENCE_WHEN_RELEVANT
END_OF_LIFE_STATUS
```

For provider-native or official-standard capability, broad community adoption is not required merely to establish authority. Authenticity, support status, security, license, version and operational fit still require evidence.

For a third-party framework/component, an abandoned project, unclear fork, experimental toy or marketing-only package does not qualify as mature merely because it has historical popularity.

### 5.2 Fitting Mature Solution

`MATURE` does not mean `FITTING`.

A candidate is a fitting mature solution only when:

```text
AUTHENTICATED=YES
MATURE_QUALIFICATION=PASS
ALL_APPLICABLE_P0=PASS
STRATEGY_CONTINUITY=PASS
AUTHORITY_OWNERSHIP=PASS
INTEGRATION_BURDEN=BOUNDED
SECURITY_AND_LICENSE=PASS
CURRENT_AND_NEXT_STAGE_FIT=PASS
```

Therefore:

```text
FITTING_MATURE_SOLUTION=YES
=> CUSTOM_COMMODITY_BUILD=BLOCKED
```

A high comparative score cannot make a non-fitting candidate fitting.

---

## 6. Standard S0-S9 selection lifecycle

For every material external-solution decision:

```text
S0 REQUIREMENT + RESPONSIBILITY FREEZE
-> S1 CANDIDATE DISCOVERY
-> S2 SOURCE / IDENTITY / MATURITY AUTHENTICATION
-> S3 P0 HARD-GATE SCREEN
-> S4 EVIDENCE CONFIDENCE CHECK
-> S5 QUALITY / TOTAL-LIFECYCLE-BURDEN COMPARISON
-> S6 DECISION-STABILITY CHECK
-> S7 SELECT / COMPOSE / ONE-BLOCKER-SPIKE / REJECT
-> S8 ADOPTION / MIGRATION CONTROLS
-> S9 PERIODIC / TRIGGERED RE-EVALUATION
```

Do not start product implementation before the applicable stages are complete.

---

## 7. S0 — Stage 0 no-product-code audit

Stage 0 is the default first step for a new commodity capability or a reopened legacy custom capability.

```text
STAGE_0_PRODUCT_CODE=PROHIBITED
```

Before candidate scoring or preference formation, freeze:

```text
DECISION_SCOPE=FOUNDATIONAL_INFRASTRUCTURE|MATERIAL_COMPONENT|BOUNDED_COMPONENT
CURRENT_BOUNDED_NEED
NEXT_EXPECTED_PRODUCT_STAGE
RESPONSIBILITY_BOUNDARY
CAPABILITY_CLASS
MUST_HAVE_REQUIREMENTS
SHOULD_HAVE_REQUIREMENTS
OPTIONAL_REQUIREMENTS
P0_REQUIREMENTS
IMPORTANT_QUALITY_ATTRIBUTES
AUTHORITY_AND_SAFETY_BOUNDARIES
EXPECTED_SCALE / LATENCY / FRESHNESS
DEPLOYMENT / PLATFORM CONSTRAINTS
PERSISTENCE / RECOVERY / REPLAY REQUIREMENTS
TESTABILITY / OBSERVABILITY REQUIREMENTS
STRATEGY_CONTINUITY_REQUIREMENTS
ACCEPTABLE_EXTENSION_SEAMS
EXIT / REPLACEMENT / DATA_PORTABILITY_REQUIREMENT
```

All `MUST_HAVE_REQUIREMENTS` become P0 unless explicitly shown to be non-applicable.

Candidate results must not be used to relax a frozen P0 requirement. If the business requirement itself materially changes, reopen S0 and record the reason before rescoring.

Stage 0 uses project facts, documentation, first-party source, security/provenance evidence and inspectable examples. It does not build multiple competing product prototypes.

If strong evidence already decides the route, stop Stage 0 and select/reject. Do not create a spike merely to feel more certain.

---

## 8. S1 — candidate discovery

Search broadly enough to avoid anchoring. Consider when applicable:

```text
REUSE_ACCEPTED_PROJECT_CAPABILITY
PROVIDER_NATIVE
STANDARD / OFFICIAL
MATURE_MAINTAINED_FULL_FRAMEWORK
MATURE_MAINTAINED_MODULAR_COMPONENT
CREDIBLE_COMPOSITION_OF_MATURE_COMPONENTS
```

`REUSE_ACCEPTED_PROJECT_CAPABILITY` must still pass current requirements. Historical acceptance and sunk cost create no permanent preference.

Candidate discovery must search for:

```text
COMPETING_ROUTES
NEGATIVE_EVIDENCE
KNOWN_FAILURES
LIMITATIONS
MIGRATION_PROBLEMS
SECURITY_HISTORY
BREAKING_CHANGE_HISTORY
```

Candidate count is not a target. Stop expanding the longlist when credible category coverage is complete and new candidates add no materially different capability, ownership or risk profile.

---

## 9. S2 — source, identity and maturity authentication

For every shortlisted candidate record as applicable:

```text
CANONICAL_PROJECT / VENDOR
OFFICIAL_REPOSITORY_OR_DISTRIBUTION
OFFICIAL_PACKAGE / IMAGE / ARTIFACT
EXACT_VERSION / RELEASE / COMMIT
RELEASE_DATE
LICENSE
MAINTENANCE_STATUS
SUPPORTED_LANGUAGE / RUNTIME / PLATFORM
PACKAGE_OR_ARTIFACT_ORIGIN
SECURITY_POLICY / VULNERABILITY_REPORTING
PROVENANCE / SIGNATURE / SBOM / SLSA SIGNALS WHEN AVAILABLE
MATURE_QUALIFICATION_RESULT
```

Do not evaluate an unofficial fork, stale mirror or ambiguous package as though it were the canonical project.

Framework evaluation must bind claims to an exact relevant version whenever the behavior may differ materially by version.

---

## 10. S3 — P0 hard gates

Each P0 is exactly one of:

```text
PASS
FAIL
UNKNOWN
NOT_APPLICABLE
```

Rules:

```text
FAIL => CANDIDATE_CANNOT_BE_SELECTED
UNKNOWN != PASS
NOT_APPLICABLE => EXPLICIT_RATIONALE_REQUIRED
```

Default P0 gates:

```text
P0_CURRENT_FUNCTIONAL_FIT
P0_NEXT_STAGE / V0_ROADMAP_FIT
P0_STRATEGY_CONTINUITY_FIT
P0_SAFETY_AND_AUTHORITY_ISOLATION
P0_DATA / TIME / EXECUTION_SEMANTIC_FIDELITY
P0_RESTART_RECOVERY_RECONCILIATION
P0_STABLE_OFFICIAL_EXTENSION_SEAM
P0_DEPLOYMENT_AND_OPERATOR_FIT
P0_SCALE_LATENCY_FRESHNESS_FIT
P0_ACTIVE_MAINTENANCE_AND_RELEASE_HEALTH
P0_SECURITY_AND_SUPPLY_CHAIN_FIT
P0_LICENSE_AND_LEGAL_FIT
P0_API_VERSION_STABILITY
P0_TESTABILITY_AND_OBSERVABILITY
P0_SINGLE_AUTHORITY_OWNERSHIP_FIT
P0_BOUNDED_INTEGRATION_BURDEN
P0_EXIT_AND_PORTABILITY
```

### 10.1 Current functional fit

For each material current requirement record:

```text
REQUIREMENT -> CANDIDATE_CAPABILITY -> EVIDENCE -> P0_RESULT
```

“May support later” or “can probably be customized” is not a PASS.

### 10.2 Next-stage / V0 roadmap fit

For foundational trading infrastructure, explicitly consider roadmap-relevant capability such as:

```text
PUBLIC_MARKET_DATA
AUTOMATED_ORDER_SUBMISSION
ORDER_LIFECYCLE
PARTIAL_FILL
CANCEL / REPLACE
TRIGGER / STOP ORDERS
REDUCE_ONLY
TIME_IN_FORCE
POSITION_RECONCILIATION
ACCOUNT_RECONCILIATION
GENERIC_RISK
KILL_SWITCH
PERSISTENCE
RESTART
RECOVERY
REPLAY
BACKTEST
SHADOW
LIVE
MULTI_MARKET
MULTI_PROVIDER_WHEN_ROADMAP_RELEVANT
```

The candidate need not implement project-specific strategy semantics. The selection must not obviously block the next expected product stage.

### 10.3 Strategy continuity fit

The project must be able to preserve relevant Strategy Decision Engine semantics behind a stable boundary. A candidate that requires core project strategy logic to become deeply inseparable from framework internals, untestable independently and impractical to migrate has a material strategy-continuity blocker.

### 10.4 Safety and authority isolation

Publish an ownership map for every applicable authoritative responsibility. Two components must not both own the same durable truth.

### 10.5 Data / time / execution semantic fidelity

Market-data evaluation should include, as applicable:

```text
TIMESTAMP_SEMANTICS
EVENT_ORDERING
BAR_CLOSE / FINALITY
GAP_HANDLING
DUPLICATE_HANDLING
HISTORICAL_LIVE_CONSISTENCY
RECONNECT_SEMANTICS
```

Execution-capable foundation evaluation should include, as applicable:

```text
ORDER_IDENTITY
CLIENT_ORDER_IDENTITY
PARTIAL_FILL
CANCEL
REPLACE
TRIGGER
REDUCE_ONLY
TIME_IN_FORCE
RETRY / IDEMPOTENCY
DISCONNECT
RECONCILIATION
RESTART_RECOVERY
```

If the candidate is intended eventually to own automated execution, these are foundation-selection questions, not deferred implementation trivia.

### 10.6 Restart / recovery / reconciliation

Evaluate as applicable:

```text
PROCESS_CRASH
NETWORK_LOSS
RESTART
STATE_REOPEN
ORDER_RECONCILIATION
POSITION_RECONCILIATION
DUPLICATE_EVENT
MISSED_EVENT
STALE_STATE
REPLAY
```

Normal-operation success alone is not infrastructure suitability.

### 10.7 Stable official extension seam

State where project-specific extension belongs:

```text
CONFIG
PLUGIN
HOOK
STRATEGY_API
ADAPTER
EVENT_HANDLER
CUSTOM_COMPONENT
```

A route requiring a long-lived material patch of framework core normally fails this P0 or enters the custom-exception gate.

### 10.8 Deployment and operator fit

Check supported OS/runtime, deployment model, configuration, logs, metrics, health, restart, upgrade, rollback, resource footprint and operator complexity.

### 10.9 Scale / latency / freshness

Evaluate against the relevant Trade OS topology, not marketing benchmarks. Record expected market count/event rate/history/order/reconciliation/state load plus documented/measured behavior and headroom.

### 10.10 Maintenance / security / supply chain

Check active maintenance, release health, security policy, critical vulnerability status, dependency health, package authenticity, provenance signals, maintainer concentration and EOL risk.

Missing SBOM/SLSA/signing alone does not automatically fail a candidate; unverifiable origin or materially unknowable security status cannot silently PASS.

### 10.11 License / legal

Record applicable commercial-use, modification, distribution, notice and service/network restrictions.

### 10.12 API stability

Check versioning policy, breaking-change history, deprecation policy and upgrade path.

### 10.13 Testability / observability

The route must support appropriate independent strategy tests, adapter tests, critical recovery tests and representative composition proof, plus observable health/failure/reconnect/order/reconciliation/latency signals where applicable.

### 10.14 Single authority ownership

```text
ONE_AUTHORITATIVE_OWNER_PER_RESPONSIBILITY=REQUIRED
```

### 10.15 Bounded integration burden

If adopting a “mature” route still requires the project to recreate generic reconnect, OMS, portfolio, persistence, recovery or generic risk that the candidate is supposed to own, the route fails bounded-integration fit unless those responsibilities are intentionally assigned elsewhere under a clean composition.

### 10.16 Exit and portability

For foundational infrastructure record:

```text
PROJECT_STRATEGY_SEMANTICS_PORTABLE
PROJECT_OWNED_DATA_EXPORTABLE
PROJECT_EVIDENCE_REMAINS_USABLE
ADAPTER_BOUNDARY_REPLACEABLE
CORE_STRATEGY_REWRITE_NOT_REQUIRED_FOR_REASONABLE_REPLACEMENT
```

This is a realistic replacement-seam requirement, not a blanket prohibition on lock-in.

---

## 11. Concrete P0 blockers

A mature candidate may be rejected only for a documented blocker, including:

```text
FUNCTIONAL_BLOCKER
SAFETY_OR_AUTHORITY_BLOCKER
DATA_OR_EXECUTION_SEMANTIC_BLOCKER
RELIABILITY_OR_RECOVERY_BLOCKER
SCALE_OR_PERFORMANCE_BLOCKER
PLATFORM_OR_OPERATIONAL_BLOCKER
SECURITY_OR_SUPPLY_CHAIN_BLOCKER
LICENSE_OR_LEGAL_BLOCKER
EXTENSIBILITY_OR_STRATEGY_CONTINUITY_BLOCKER
INTEGRATION_BURDEN_BLOCKER
OVERLAPPING_AUTHORITY_BLOCKER
EXIT_OR_PORTABILITY_BLOCKER
```

The record must state the exact requirement, exact evidence and why configuration, official extension, thin adapter, modular composition or upstream contribution does not resolve it economically.

---

## 12. S4 — evidence confidence

Every material P0 judgment and major comparison score records an evidence grade:

```text
E5 = MEASURED / REPRODUCED ON THE RELEVANT VERSION
E4 = PRIMARY SOURCE CODE / MACHINE-READABLE CONTRACT
E3 = CURRENT OFFICIAL DOCUMENTATION / SECURITY OR PROVENANCE ATTESTATION
E2 = CREDIBLE PRODUCTION CASE / INDEPENDENT TECHNICAL EVIDENCE
E1 = COMMUNITY REPORT / ISSUE / ANECDOTE
E0 = CLAIM / MARKETING / UNVERIFIED
```

Rules:

- `E0` cannot make a P0 PASS.
- Important safety, authority, execution, persistence, recovery and security P0 claims should normally require E3+ and use E4/E5 when official documentation is ambiguous.
- Community evidence is valuable for discovering failure modes but does not overrule current primary evidence without reproduction or corroboration.
- Evidence records should bind `EVIDENCE_DATE`, `EVIDENCE_VERSION` and `CANDIDATE_VERSION` where version drift matters.
- Evidence for an old major version does not automatically prove current-version behavior.
- Conflicting official documentation, source and measured behavior remains `UNKNOWN` until resolved or explicitly accepted as residual risk by the governing authority.
- Resolve material conflicts with exact-version source inspection, reproduction or a qualifying Tiny Spike rather than choosing the evidence that supports a favorite.

---

## 13. S5 — quality and total-lifecycle-burden comparison

Only candidates that pass all applicable P0 gates enter the comparative scorecard.

Default weighted dimensions:

```text
CURRENT_FUNCTIONAL_FIT                  20
FUTURE_V0_AND_ROADMAP_CONTINUITY       15
RELIABILITY_RECOVERY_EXECUTION         15
INTEGRATION_EXTENSIBILITY_BURDEN       15
SECURITY_SUPPLY_CHAIN_LICENSE          10
MAINTENANCE_MATURITY                   10
OPERATIONS_OBSERVABILITY_PERFORMANCE   10
REPLACEABILITY_API_STABILITY_LOCKIN     5
TOTAL                                 100
```

Score each dimension:

```text
0 = materially inadequate
1 = weak / high burden
2 = acceptable with meaningful trade-offs
3 = strong
4 = excellent for project requirements
```

The scorecard is a decision aid, not an authority override. A P0 FAIL cannot be compensated by a high score.

### 13.1 Weight discipline

Default weights are reused unless the bounded task has a genuine different business driver. Any weight change must be frozen before candidate results are scored, with rationale and a total of 100.

Changing weights after seeing results to manufacture a preferred winner is prohibited.

### 13.2 Total burden

Separate at least:

```text
ONE_TIME_TRANSITION_BURDEN
- migration
- adapter / extension work
- data / test / deployment migration
- operator learning
- old-owner decommissioning

RECURRING_OWNERSHIP_BURDEN
- maintenance
- dependency management
- upgrades / breaking changes
- security response
- debugging / evidence
- incident response / recovery
- CI / release / operations
- future-feature change amplification
- custom-fork maintenance if any
- exit / replacement
```

Do not compare only initial LOC or setup time.

### 13.3 No false numeric precision

When reliable dollars, engineer-days or measured rates are unavailable, use evidence-backed ordinal estimates such as:

```text
LOW
MEDIUM
HIGH
VERY_HIGH
UNKNOWN
```

Do not fabricate precise lifecycle-cost numbers from weak evidence.

---

## 14. S6 — decision-stability check

A narrow numeric winner is not automatically stable.

For leading P0-pass candidates, vary non-P0 comparison weights within a predeclared bounded range, normally `±20% relative` per dimension while re-normalizing to 100.

Also evaluate, when relevant:

```text
SCENARIO_A=CURRENT_PRODUCT_PRIORITY
SCENARIO_B=FUTURE_AUTOMATION_PRIORITY
SCENARIO_C=RELIABILITY_SECURITY_OPERATIONS_PRIORITY
```

If reasonable weight or scenario changes repeatedly change the winner:

```text
DECISION_STABILITY=LOW
DISPOSITION=UNRESOLVED_TRADEOFF
SELECT_MATURE_ROUTE=PROHIBITED
SELECT_MODULAR_COMPOSITION=PROHIBITED
ADOPTION=PROHIBITED
PRODUCT_WRITER_DISPATCH=PROHIBITED
```

`DECISION_STABILITY=LOW` is fail-closed for promotion. It may proceed only to a qualifying `ONE_BLOCKER_FEASIBILITY_SPIKE` when exactly one material P0 uncertainty remains and every §16 eligibility/budget gate passes. Otherwise the decision remains `UNRESOLVED_TRADEOFF` and must be resolved by more evidence, a bounded re-analysis, rejection, deferral or `SAFE_STOP`; it cannot be promoted into selection or product implementation.

Do not fabricate certainty from an unstable score.

When candidates remain effectively tied, prefer:

```text
LOWER_TOTAL_LIFECYCLE_BURDEN
-> THINNER_PROJECT_SEAM
-> FEWER_AUTHORITATIVE_OWNERS
-> LOWER_LOCKIN / EASIER_REPLACEMENT
-> STRONGER_EXIT / DATA_PORTABILITY
-> STRONGER_PRIMARY_EVIDENCE
```

---

## 15. S7 — allowed Stage 0 dispositions

Stage 0 ends with one of:

```text
SELECT_MATURE_ROUTE
SELECT_MODULAR_COMPOSITION
ONE_BLOCKER_FEASIBILITY_SPIKE
UNRESOLVED_TRADEOFF
REJECT_CANDIDATE
NO_FITTING_MATURE_ROUTE
SAFE_STOP
```

`UNRESOLVED_TRADEOFF` is non-promotable. It is not an alias for `SELECT_MATURE_ROUTE`, `SELECT_MODULAR_COMPOSITION`, adoption, or Writer dispatch.

It must not end with an implicit custom build merely because no favorite was selected.

---

## 16. One-Blocker Tiny Spike

A Tiny Spike is allowed only when:

```text
EXACTLY_ONE_MATERIAL_P0_UNCERTAINTY_REMAINS=YES
CHEAP_SAFE_NONAUTHORITATIVE_TEST_CAN_DECIDE_IT=YES
DOCUMENTATION_OR_SOURCE_REVIEW_CANNOT_DECIDE_IT_EFFICIENTLY=YES
SPIKE_DOES_NOT_REQUIRE_PRODUCT_ARCHITECTURE=YES
```

Before dispatch freeze:

```text
CANDIDATE
EXACT_P0_QUESTION
HYPOTHESIS
PASS_CONDITION
FAIL_CONDITION
NONDECISIVE_CONDITION
TEST_ENVIRONMENT
MAX_SCOPE
MAX_FILES
MAX_LOC
MAX_WRITER_STAGE
SPIKE_BUDGET_OVERRIDE=NO|BOUNDED_WITH_RATIONALE
SPIKE_BUDGET_OVERRIDE_RATIONALE=
EVIDENCE_OUTPUT
CLEANUP_PLAN
```

The following semantic constraints are non-overridable for a Tiny Spike:

```text
ONE_CANDIDATE=YES
ONE_UNRESOLVED_P0_QUESTION=YES
ONE_WRITER_STAGE=YES
PRODUCT_IMPLEMENTATION=NO
NEW_DATABASE=NO
NEW_RUNTIME=NO
NEW_PERSISTENCE_SYSTEM=NO
NEW_GENERAL_HARNESS_FRAMEWORK=NO
PRODUCTION_DEPLOYMENT=NO
PRIVATE_ACCOUNT_API=NO
EXCHANGE_WRITE=NO
NEW_COMMODITY_SUBSYSTEM=NO
```

Default numeric/mechanical budget:

```text
TARGET_PROJECT_OWNED_ADAPTER_LOC<=250
TARGET_CHANGED_FILES<=4
AT_MOST_ONE_SMALL_MECHANICAL_CORRECTION
```

LOC/file limits are stop signals rather than architecture definitions. A bounded upward numeric override is allowed only when all of the following are recorded before dispatch:

```text
SPIKE_BUDGET_OVERRIDE=BOUNDED_WITH_RATIONALE
NON_OVERRIDABLE_SPIKE_CONSTRAINTS=PASS
ONE_QUESTION_DECISIVENESS_UNCHANGED=YES
CHEAP_SAFE_NONAUTHORITATIVE_CHARACTER_UNCHANGED=YES
NO_PRODUCT_OR_COMMODITY_AUTHORITY_EXPANSION=YES
EXACT_NUMERIC_OVERRIDE_AND_REASON=
ENGINEERING_CONTROL_OVERRIDE_GATE=PASS
```

An override may adjust numeric/mechanical limits only. It may not relax any non-overridable semantic/safety constraint above. If the proposed override makes the work materially implementation-like, introduces a second uncertainty/authority, or cannot remain cheap and decisive:

```text
SPIKE_BUDGET_OVERRIDE=FAIL
ENGINEERING_PREFLIGHT_GATE=FAIL
TINY_SPIKE_WRITER_DISPATCH=PROHIBITED
```

Spike result:

```text
PASS
FAIL
NONDECISIVE
```

If a second semantic uncertainty appears, a new commodity subsystem is needed, a non-overridable constraint would be violated, or the frozen budget is exceeded:

```text
STOP
SPIKE_RESULT=NONDECISIVE_OR_TOO_EXPENSIVE
REASSESS_CANDIDATE_OR_NEXT_MATURE_ROUTE
```

Do not convert the spike into Repair 2/3 product development.

---

## 17. Modular composition

Multiple mature solutions may be composed when total burden falls and authority remains clear.

Permanent rule:

```text
MODULAR_COMPOSITION=ALLOWED
ONE_AUTHORITATIVE_OWNER_PER_RESPONSIBILITY=REQUIRED
OVERLAPPING_DURABLE_STATE_OMS_POSITION_RISK_AUTHORITY=PROHIBITED
```

Before accepting a composition, publish an ownership matrix for at least:

```text
MARKET_DATA
CLOCK
EVENT_LOOP
ORDERS / OMS
FILLS
POSITIONS
ACCOUNT
PORTFOLIO
GENERIC_RISK
STRATEGY_RISK_POLICY
PERSISTENCE
RECOVERY
REPLAY
BACKTEST
LIVE_EXECUTION
```

A composition requiring two competing authorities to synchronize the same durable truth fails the gate.

A non-authoritative projection/cache is allowed only when:

```text
CACHE_OR_PROJECTION_REBUILDABLE=YES
CANNOT_WRITE_AUTHORITY=YES
LOSS_DOES_NOT_LOSE_CANONICAL_TRUTH=YES
NONAUTHORITATIVE_STATUS_MECHANICALLY_PRESERVED=YES
```

Composition evaluation must also cover data flow, failure propagation, restart ordering, version/upgrade compatibility and recovery ownership.

---

## 18. Bounded customization

Prefer:

```text
CONFIGURATION
OFFICIAL_PLUGIN_OR_EXTENSION
THIN_ADAPTER
UPSTREAM_CONTRIBUTION
```

Custom integration must record:

```text
CUSTOM_SCOPE
WHY_IT_IS_PROJECT_SPECIFIC_OR_THIN
UPSTREAM_SEAM_USED
STATE_OWNED_BY_CUSTOM_CODE
AUTHORITY_OWNED_BY_CUSTOM_CODE
MIGRATION / EXIT_SEAM
EXPECTED_MAINTENANCE_BURDEN
```

If it ceases to satisfy the Thin Integration gate in §2.3, reclassify it as commodity infrastructure and reopen selection.

---

## 19. Custom commodity exception

If every credible mature route has a proven P0 blocker, Engineering Control or a Writer may recommend a custom commodity implementation but may not authorize or begin it.

Required packet:

```text
CANDIDATES_EVALUATED
EXACT_P0_BLOCKERS_AND_EVIDENCE
PROVIDER_NATIVE_CHECK
STANDARD / OFFICIAL_CHECK
MATURE_FULL_FRAMEWORK_CHECK
MATURE_MODULAR_COMPONENT_CHECK
CONFIGURATION / PLUGIN_CHECK
THIN_ADAPTER_CHECK
MODULAR_COMPOSITION_CHECK
UPSTREAM_CONTRIBUTION_CHECK
CUSTOM_TOTAL_BURDEN_CASE
BOUNDED_CUSTOM_SCOPE
STABLE_REPLACEMENT_SEAM
REPAIR / STOP_BUDGET
EXIT_PLAN
```

Then:

```text
CUSTOM_COMMODITY_EXCEPTION_USER_AUTHORITY=REQUIRED
```

Without explicit current user approval:

```text
ENGINEERING_PREFLIGHT_GATE=FAIL
CUSTOM_WRITER_DISPATCH=PROHIBITED
```

Approval is not permanent permission. Any accepted custom commodity route must start with a stable replacement seam, frozen repair budget and exit plan.

---

## 20. S8 — selection is not adoption

`SELECT_MATURE_ROUTE` does not mean `ACCEPTED_PROJECT_INFRASTRUCTURE`.

Before adoption record as applicable:

```text
CANONICAL_SOURCE
EXACT_ACCEPTED_VERSION / COMMIT / ARTIFACT
PACKAGE_OR_IMAGE_ORIGIN
LOCK / PIN_POLICY
LICENSE
SECURITY_POLICY
KNOWN_CRITICAL_VULNERABILITIES / RESPONSE
PROVENANCE / SIGNATURE / SBOM / SLSA_EVIDENCE_WHEN_AVAILABLE
DIRECT_AND_MATERIAL_TRANSITIVE_DEPENDENCY_RISK
OFFICIAL_EXTENSION_SEAM
PROJECT_ADAPTER_CONTRACT
AUTHORITY_OWNERSHIP_MAP
REPRESENTATIVE_ACCEPTANCE_PROOF
OBSERVABILITY / HEALTH_SIGNALS
ROLLBACK / DISABLE_PLAN
UPGRADE_POLICY
EXIT / REPLACEMENT_SEAM
INDEPENDENT_REVIEW_REQUIREMENT
```

Adoption disposition:

```text
ACCEPT
PILOT_ONLY
REJECT
```

Do not convert an evaluation spike into accepted infrastructure without a separate adoption decision and normal publication/activation gates.

### 20.1 Migration and cutover

When replacing an existing owner, record:

```text
OLD_AUTHORITATIVE_OWNER
NEW_AUTHORITATIVE_OWNER
CUTOVER_POINT
OLD_OWNER_DECOMMISSION_PLAN
ROLLBACK_POINT
```

Shadow/read-only comparison may be used where safe.

```text
DUAL_WRITE_AUTHORITY=PROHIBITED_BY_DEFAULT
```

Any temporary migration mechanism that can mutate overlapping authoritative state requires a separately designed and validated migration contract.

---

## 21. S9 — re-evaluation and decision expiry

External-solution decisions are versioned decisions, not permanent truths.

Reopen full S0-S9 when material:

```text
CRITICAL_SECURITY_OR_SUPPLY_CHAIN_EVENT
UNMAINTAINED / END_OF_LIFE
REPEATED_UPSTREAM_BREAKING_CHANGES
LICENSE_OR_GOVERNANCE_CHANGE
NEW_PRODUCT_STAGE_EXCEEDS_PRIOR_P0_SCOPE
MATERIAL_CUSTOM_FORK_PRESSURE
REPEATED_INTEGRATION_DEFECTS
TOTAL_BURDEN_MATERIALLY_EXCEEDS_SELECTION_ASSUMPTIONS
NEW_MATURE_ROUTE_WITH_MATERIAL_REPLACEMENT_VALUE
AUTHORITY_OR_SAFETY_MODEL_CHANGE
```

For `FOUNDATIONAL_INFRASTRUCTURE`, default to a lightweight delta review at least every 180 days unless a stricter domain cadence applies:

```text
VERSION / RELEASE_HEALTH
MAINTENANCE
SECURITY
LICENSE
ROADMAP_FIT
NEW_MATERIAL_ALTERNATIVES
ACTUAL_VS_ASSUMED_BURDEN
```

The 180-day control is not a mandatory full re-selection. No material change means the prior decision can remain active with a recorded delta review. A material trigger reopens full S0-S9.

### 21.1 Legacy custom-code expiry trigger

For project-owned commodity infrastructure, prior `KEEP_CUSTOM`, `DEFER_MIGRATION`, `NO_FRAMEWORK_CHANGE` or equivalent decisions expire before another semantic repair when any occurs:

```text
MATERIAL_DEFECT_IN_COMMODITY_BOUNDARY
CLEAN_REPLACEMENT_REQUIRED
REPEATED_PROVIDER_OR_QUALIFICATION_FAILURE
VERIFICATION_BURDEN_BECOMES_MATERIAL_OR_COMPARABLE_TO_IMPLEMENTATION
REPAIR_BUDGET_EXHAUSTED
```

Then:

```text
DIRECT_PATCH_AUTHORITY=STOP
PRESERVE_EVIDENCE
MATURE_SOLUTION_GATE_REOPEN=MANDATORY
```

This does not force migration after every bug. It prevents stale build-vs-buy decisions from authorizing endless custom investment.

---

## 22. Selection decision record

Every material selection produces a durable record containing:

```text
DECISION_ID / DATE
CURRENT_LIVE_PROJECT_IDENTITY
TASK / ISSUE
RESPONSIBILITY_BOUNDARY
CAPABILITY_CLASS
DECISION_SCOPE
CURRENT_NEED
NEXT_EXPECTED_STAGE
S0_REQUIREMENTS
CANDIDATE_LONGLIST
AUTHENTICATED_SHORTLIST
MATURE_QUALIFICATION_RESULTS
P0_MATRIX
EVIDENCE_GRADES / VERSION / DATE
WEIGHTS_AND_RATIONALE
SCORECARD
SCENARIO_ANALYSIS
DECISION_STABILITY_RESULT
TOTAL_BURDEN_COMPARISON
AUTHORITY_OWNERSHIP_MAP
SELECTED_ROUTE
REJECTED_ROUTES_AND_EXACT_REASONS
RESIDUAL_RISKS
SPIKE_RESULT_IF_ANY
SPIKE_BUDGET_OVERRIDE_IF_ANY
ADOPTION_REQUIREMENTS
EXIT_PLAN
RE_EVALUATION_TRIGGERS
CUSTOM_EXCEPTION_AUTHORITY_IF_ANY
```

The record may live in the active GitHub Issue/ADR-like history. Do not create a competing project-wide rulebook for every selection.

---

## 23. Independent review anti-gaming checks

Independent review of a material mature-solution decision must check at least:

- capability classification was not manipulated to call commodity code strategy;
- P0 requirements were frozen before scoring;
- no P0 FAIL was hidden by weighted scoring;
- no `UNKNOWN` was silently reported as PASS;
- maturity and fitting were evaluated separately;
- candidate discovery covered credible provider-native, official, full-framework, modular and composition routes where applicable;
- negative evidence and project-specific limitations were searched;
- material evidence is current enough and version-bound where required;
- important P0 PASS does not rely only on marketing, popularity or star count;
- evidence conflicts were resolved or remained `UNKNOWN`;
- weights were not changed after seeing results;
- total burden includes transition plus recurring maintenance, upgrade, security, incident and exit burden;
- false numeric precision was not used to manufacture certainty;
- decision stability was tested rather than inferred from one scorecard;
- `DECISION_STABILITY=LOW` did not promote selection, adoption or product Writer dispatch;
- modular composition has one authority owner per responsibility;
- non-authoritative projections are mechanically non-authoritative and rebuildable;
- customization remains thin and does not recreate commodity ownership;
- a Tiny Spike answered only its frozen blocker and stayed within budget;
- any Tiny Spike numeric/mechanical budget override preserved every non-overridable constraint and passed the explicit bounded override gate before dispatch;
- selection and adoption were not collapsed;
- migration does not create overlapping write authority without a separate validated contract;
- custom commodity work, if proposed, has explicit current user authority;
- the decision considers the known next product stage, not only the current ticket;
- exit/replacement and strategy/data portability were assessed for foundational infrastructure.

A material failure is a route-decision defect, not a Writer coding defect:

```text
DISPOSITION=REPAIR_SELECTION_RECORD | REPLAN | SAFE_STOP
```

---

## 24. Evidence basis

This procedure is informed by mature external methods and primary guidance, including:

- NIST SSDF / SP 800-218 — third-party component verification, lifecycle maintenance, secure software practices and supplier/acquirer communication;
- NIST SP 1326 — supplier/product due diligence including provenance, resilience, foundational cyber practices and supply-chain tiers;
- OpenSSF Concise Guide for Evaluating Open Source Software — necessity, candidate authenticity, activity, release health, security, dependencies, licensing, adoption, suitability and practical testing;
- OpenSSF Scorecard / OSPS Baseline / Best Practices — security and project-practice signals;
- SLSA provenance — verifiable source/build/artifact provenance;
- Semantic Versioning and explicit project version policies — compatibility and upgrade expectations;
- CMU SEI ATAM — evaluation of interacting quality attributes, scenarios, risks, sensitivities and trade-offs;
- ISO/IEC 25010 quality-model vocabulary — consistent software-quality dimensions;
- AWS Well-Architected and comparable mature operational guidance — total operational burden and avoiding undifferentiated heavy lifting.

These sources provide evaluation methods and evidence vocabulary. They do not select a Trader Assist framework automatically. Project P0 fit, authority clarity and total lifecycle burden remain decisive.

---

## 25. Authority boundary

This procedure does not authorize:

```text
IMPLEMENTATION_BEFORE_APPLICABLE_SELECTION_GATES
MARK_READY
MERGE
BRANCH_DELETION
DEPLOYMENT
PRODUCTION_RUNTIME_OR_CLOUD_MUTATION
SERVICE_START_RESTART_ENABLE_REBOOT
CREDENTIAL_OR_PRIVATE_API_ACCESS
WALLET / SIGNING / NONCE
EXCHANGE_WRITE
ORDER_SUBMISSION_OR_CANCELLATION
AUTONOMOUS_TRADING
```

Those remain governed by Unified V2 and explicit current user authority.

---

## 26. Frozen concise invariants

```text
MATURE_DOES_NOT_EQUAL_FITTING=YES
FITTING_REQUIRES_ALL_APPLICABLE_P0_PASS=YES
P0_FAIL_CANNOT_BE_OFFSET_BY_SCORE=YES
P0_UNKNOWN_IS_NOT_PASS=YES
EVIDENCE_VERSION_BINDING_WHEN_MATERIAL=REQUIRED
EVIDENCE_CONFLICT_REMAINS_UNKNOWN_UNTIL_RESOLVED=YES
FOUNDATIONAL_EXIT_AND_PORTABILITY_P0=REQUIRED
SCORECARD_AFTER_P0_ONLY=YES
DECISION_STABILITY_AND_SCENARIO_CHECK=REQUIRED
DECISION_STABILITY_LOW_BLOCKS_SELECTION_ADOPTION_AND_PRODUCT_WRITER=YES
UNRESOLVED_TRADEOFF_IS_NONPROMOTABLE=YES
TINY_SPIKE_ONE_BLOCKER_ONLY=YES
TINY_SPIKE_NONOVERRIDABLE_SEMANTIC_SAFETY_CONSTRAINTS=YES
TINY_SPIKE_NUMERIC_OVERRIDE_REQUIRES_BOUNDED_PRE_DISPATCH_GATE=YES
ONE_AUTHORITATIVE_OWNER_PER_RESPONSIBILITY=REQUIRED
NONAUTHORITATIVE_PROJECTION_MUST_BE_REBUILDABLE_AND_NONWRITING=YES
THIN_INTEGRATION_RECLASSIFY_IF_COMMODITY_AUTHORITY_EMERGES=YES
SELECTION_NE_ADOPTION=YES
DUAL_WRITE_AUTHORITY_DURING_MIGRATION=PROHIBITED_BY_DEFAULT
CUSTOM_COMMODITY_EXCEPTION_USER_AUTHORITY=REQUIRED
FOUNDATIONAL_INFRA_DELTA_REVIEW_DEFAULT_MAX_DAYS=180
LEGACY_KEEP_CUSTOM_EXPIRY_TRIGGERS=REQUIRED
```
