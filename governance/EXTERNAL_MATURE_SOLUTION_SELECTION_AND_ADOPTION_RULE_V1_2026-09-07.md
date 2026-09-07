# Trader Assist / Trade OS — External Mature Solution Selection and Adoption Rule V1

**Status:** TASK-CONDITIONAL PROCEDURE CANDIDATE  
**Effective date:** 2026-09-07  
**Normative owner:** `UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md`  
**Scope:** selection, rejection, composition, bounded customization, adoption, upgrade and re-evaluation of provider-native, standard/official, mature maintained external frameworks, libraries, SDKs, platforms, services and infrastructure components.

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

The project differentiates through trading strategy, research and decision logic. It must not spend scarce engineering effort rebuilding commodity infrastructure that a fitting mature solution can own more safely and economically.

Selection must be reproducible and auditable. A future Engineering Control or Writer must not choose a framework because it is fashionable, familiar, popular, easy to start, already partially used, or subjectively described as “better”.

---

## 2. Mandatory capability classification

Before candidate search or Writer dispatch, classify the responsibility being considered:

```text
CAPABILITY_CLASS=
STRATEGY_DIFFERENTIATOR
| COMMODITY_INFRASTRUCTURE
| THIN_INTEGRATION
```

### 2.1 Strategy Decision Engine — project-owned core IP

`STRATEGY_DECISION_ENGINE` means project-specific trading intelligence and policy, including as applicable:

- Setup / signal semantics;
- Scanner, ranking and opportunity selection;
- Thesis / Attempt semantics;
- entry, exit, re-entry and winner-management policy;
- strategy-specific sizing and risk policy;
- strategy-specific features, research and evidence semantics;
- strategy-specific regime logic and economic decisions.

A mature framework may host or execute these decisions, but the project may preserve and develop their semantics independently.

### 2.2 Trading Infrastructure Engine — commodity by default

`TRADING_INFRASTRUCTURE_ENGINE` means generic infrastructure commonly needed by trading systems, including as applicable:

- REST / WebSocket transport and session management;
- subscriptions, heartbeats, reconnect, backoff and resubscription;
- generic market-data ingestion and normalization;
- generic clocks, scheduling and orchestration;
- order management and order lifecycle;
- exchange adapters, signing transport and venue mechanics;
- fill, order, position and account reconciliation;
- generic portfolio/account state;
- generic pre-trade limits, kill switches and non-strategy risk enforcement;
- generic persistence, restart, recovery and replay plumbing;
- generic backtest / sandbox / live runtime mechanics;
- deployment, observability and workflow plumbing.

These examples are not exhaustive. Classification follows responsibility semantics, not file or class names.

### 2.3 Thin integration

`THIN_INTEGRATION` is project-owned code whose purpose is only to translate between a mature owner and a stable project contract. It must not silently become a second runtime, second OMS, second portfolio, second reconnect manager, second persistence authority or competing risk authority.

---

## 3. Mature capability no-rebuild gate

Permanent decision rule:

```text
COMMODITY_INFRASTRUCTURE
+
FITTING_PROVIDER_NATIVE_OR_STANDARD_OR_MATURE_MAINTAINED_SOLUTION_EXISTS
=
MATURE_EXTERNAL_OWNER_REQUIRED
CUSTOM_FROM_SCRATCH_IMPLEMENTATION=PROHIBITED
SECOND_PROJECT_OWNED_IMPLEMENTATION=PROHIBITED
```

Allowed project integration order:

```text
CONFIGURATION
-> OFFICIAL EXTENSION / PLUGIN
-> THIN ADAPTER
-> UPSTREAM CONTRIBUTION
-> BOUNDED CUSTOMIZATION ONLY WHEN THIS PROCEDURE ALLOWS IT
```

A fitting mature route may not be rejected merely because the project already has custom code or because migration is inconvenient.

A long-lived invasive fork of a mature framework core is prohibited by default. A proposal that requires maintaining a material private fork is treated as a new custom commodity implementation and must pass the custom-exception gate.

---

## 4. Prohibited mature-route rejection reasons

None of the following is sufficient to reject a fitting mature solution:

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

A dependency can reduce total complexity when it replaces a larger project-owned responsibility. Total lifecycle burden, not dependency count, is the governing metric.

---

## 5. Standard selection workflow

For every material external-solution decision use:

```text
S0 REQUIREMENT + RESPONSIBILITY FREEZE
-> S1 CANDIDATE DISCOVERY
-> S2 SOURCE / IDENTITY AUTHENTICATION
-> S3 P0 HARD-GATE SCREEN
-> S4 EVIDENCE CONFIDENCE CHECK
-> S5 QUALITY / TOTAL-BURDEN COMPARISON
-> S6 DECISION-STABILITY CHECK
-> S7 SELECT / COMPOSE / ONE-BLOCKER-SPIKE / REJECT
-> S8 ADOPTION CONTROLS
-> S9 PERIODIC / TRIGGERED RE-EVALUATION
```

Do not start product implementation before the applicable stages above are complete.

---

## 6. S0 — Stage 0 no-product-code audit

Stage 0 is the default first step for a new commodity capability or a reopened legacy custom capability.

```text
STAGE_0_PRODUCT_CODE=PROHIBITED
```

Freeze before searching:

```text
CURRENT_BOUNDED_NEED
NEXT_EXPECTED_PRODUCT_STAGE
RESPONSIBILITY_BOUNDARY
CAPABILITY_CLASS
P0_REQUIREMENTS
IMPORTANT_QUALITY_ATTRIBUTES
AUTHORITY_AND_SAFETY_BOUNDARIES
EXPECTED_SCALE / LATENCY / FRESHNESS
DEPLOYMENT / PLATFORM CONSTRAINTS
STRATEGY_CONTINUITY_REQUIREMENTS
ACCEPTABLE_EXTENSION_SEAMS
EXIT / REPLACEMENT_REQUIREMENT
```

Stage 0 uses documentation, first-party source, security/provenance evidence, existing project facts and inspectable examples. It does not build three competing product prototypes.

If strong evidence already decides the route, stop Stage 0 and select/reject. Do not create a spike merely to feel more certain.

---

## 7. S1 — candidate discovery

Search broadly enough to avoid anchoring on one familiar option. At minimum consider, when applicable:

```text
REUSE_ACCEPTED_PROJECT_CAPABILITY
PROVIDER_NATIVE
STANDARD / OFFICIAL
MATURE MAINTAINED FULL FRAMEWORK
MATURE MAINTAINED MODULAR COMPONENT
CREDIBLE COMPOSITION OF MATURE COMPONENTS
```

`REUSE_ACCEPTED_PROJECT_CAPABILITY` means it must still pass current requirements. Historical acceptance and sunk cost do not create a permanent preference.

Candidate discovery must search for competing approaches and negative evidence, not only evidence supporting the current favorite.

Candidate count is not a target. Stop expanding the longlist when credible category coverage is complete and new candidates do not add materially different capability or risk profiles.

---

## 8. S2 — source and identity authentication

For every shortlisted candidate record as applicable:

```text
CANONICAL_PROJECT / VENDOR
OFFICIAL_REPOSITORY_OR_DISTRIBUTION
EXACT_VERSION / RELEASE / COMMIT
RELEASE_DATE
LICENSE
MAINTENANCE_STATUS
SUPPORTED_LANGUAGE / RUNTIME / PLATFORM
PACKAGE_OR_ARTIFACT_ORIGIN
SECURITY_POLICY / VULNERABILITY_REPORTING
PROVENANCE / SIGNATURE / SBOM / SLSA SIGNALS WHEN AVAILABLE
```

Do not evaluate an unofficial fork, stale mirror or ambiguous package as though it were the canonical project.

---

## 9. S3 — P0 hard gates

A candidate cannot be selected when a mandatory P0 field is `FAIL`. `UNKNOWN` is not PASS.

Default P0 gates, tailored only by explicit `NOT_APPLICABLE` with rationale:

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
```

For a trading-system foundation, `P0_NEXT_STAGE / V0_ROADMAP_FIT` must explicitly consider the known path toward automated order submission, automated execution behavior, position/account reconciliation, risk enforcement, replay/backtest/shadow/live continuity and the market/provider scope relevant to the roadmap. A framework need not implement project-specific strategy semantics.

Do not downgrade a P0 requirement merely to preserve a preferred candidate.

---

## 10. Concrete P0 blockers

A mature candidate may be rejected only for a documented blocker in one or more of these classes:

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
```

The record must state the exact requirement, exact evidence and why configuration, official extension, thin adapter, modular composition or upstream contribution does not resolve it economically.

---

## 11. S4 — evidence confidence

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

- `E0` cannot make a P0 gate PASS.
- Important safety, authority, execution or persistence P0 claims should normally require E3+ and use E4/E5 when documentation is ambiguous.
- Community evidence is valuable for discovering failure modes but does not overrule current primary evidence without reproduction or corroboration.
- Conflicting evidence remains `UNKNOWN` until resolved or explicitly accepted as residual risk under the governing authority.

---

## 12. S5 — quality and total-burden comparison

Only candidates that pass all applicable P0 hard gates enter the comparative scorecard.

Default weighted dimensions:

```text
CURRENT_FUNCTIONAL_FIT                 20
FUTURE_V0_AND_ROADMAP_CONTINUITY       15
RELIABILITY_RECOVERY_EXECUTION          15
INTEGRATION_EXTENSIBILITY_BURDEN        15
SECURITY_SUPPLY_CHAIN_LICENSE           10
MAINTENANCE_MATURITY                     10
OPERATIONS_OBSERVABILITY_PERFORMANCE    10
REPLACEABILITY_API_STABILITY_LOCKIN       5
TOTAL                                   100
```

Score each dimension from `0` to `4` using stated evidence:

```text
0 = materially inadequate
1 = weak / high burden
2 = acceptable with meaningful trade-offs
3 = strong
4 = excellent for project requirements
```

The scorecard is a decision aid, not an authority override. A P0 FAIL cannot be compensated by a high weighted score.

### 12.1 Weight discipline

The default weights are reused unless the bounded task has a genuine different business driver. Any weight change must be frozen **before candidate results are scored**, with rationale and a total of 100.

Changing weights after seeing candidate scores to manufacture a preferred winner is prohibited.

### 12.2 Total burden

Comparison must include, over the expected lifecycle:

```text
ADOPTION / MIGRATION
ADAPTER / EXTENSION CODE
TESTS / VERIFICATION
CI / RELEASE
OPERATOR / DEPLOYMENT
DEPENDENCY MANAGEMENT
UPGRADES / API BREAKS
SECURITY RESPONSE
DEBUGGING / EVIDENCE
RECOVERY / INCIDENT RESPONSE
CUSTOM FORK MAINTENANCE IF ANY
EXIT / REPLACEMENT COST
EXPECTED FUTURE CHANGE AMPLIFICATION
```

Do not compare only initial LOC or initial setup time.

---

## 13. S6 — decision-stability check

A narrow numeric winner is not automatically a stable architecture decision.

For the leading P0-pass candidates, vary the non-P0 comparison weights within a predeclared bounded range, normally `±20% relative` per dimension while re-normalizing to 100. If reasonable weight changes repeatedly change the winner, record:

```text
DECISION_STABILITY=LOW
DISPOSITION=UNRESOLVED_TRADEOFF
```

Do not fabricate certainty from an unstable score.

When two candidates remain effectively tied, prefer in this order when requirements remain satisfied:

```text
LOWER_TOTAL_LIFECYCLE_BURDEN
-> THINNER_PROJECT_SEAM
-> FEWER_AUTHORITATIVE_OWNERS
-> LOWER_LOCKIN / EASIER_REPLACEMENT
-> STRONGER_PRIMARY_EVIDENCE
```

---

## 14. S7 — allowed Stage 0 dispositions

Stage 0 ends with one of:

```text
SELECT_MATURE_ROUTE
SELECT_MODULAR_COMPOSITION
ONE_BLOCKER_FEASIBILITY_SPIKE
REJECT_CANDIDATE
NO_FITTING_MATURE_ROUTE
SAFE_STOP
```

It must not end with an implicit “custom build” merely because no favorite was selected.

---

## 15. One-Blocker Tiny Spike

A Tiny Spike is allowed only when all are true:

```text
EXACTLY_ONE_MATERIAL_P0_UNCERTAINTY_REMAINS=YES
CHEAP_SAFE_NONAUTHORITATIVE_TEST_CAN_DECIDE_IT=YES
DOCUMENTATION / SOURCE REVIEW_CANNOT_DECIDE_IT_EFFICIENTLY=YES
SPIKE_DOES_NOT_REQUIRE_PRODUCT_ARCHITECTURE=YES
```

Its purpose is to answer one question, not to start implementation.

Default budget:

```text
ONE_CANDIDATE
ONE_UNRESOLVED_P0_QUESTION
ONE_WRITER_STAGE
PRODUCT_IMPLEMENTATION=NO
NEW_DATABASE=NO
NEW_RUNTIME=NO
NEW_PERSISTENCE_SYSTEM=NO
NEW_GENERAL_HARNESS_FRAMEWORK=NO
PRODUCTION_DEPLOYMENT=NO
PRIVATE_ACCOUNT_API=NO
EXCHANGE_WRITE=NO
TARGET_PROJECT_OWNED_ADAPTER_LOC<=250
TARGET_CHANGED_FILES<=4
AT_MOST_ONE_SMALL_MECHANICAL_CORRECTION
```

The LOC/file targets are stop signals for a feasibility experiment, not universal production architecture limits. Any task-specific override must be frozen before the spike, with a concrete reason why the experiment remains cheap and decisive.

If the spike reveals a second semantic uncertainty, requires a new commodity subsystem, or exceeds its frozen budget:

```text
SPIKE_RESULT=TOO_EXPENSIVE_OR_NONDECISIVE
STOP
REASSESS_CANDIDATE_OR_NEXT_MATURE_ROUTE
```

Do not convert the spike into Repair 2/3 product development.

---

## 16. Modular composition

Using multiple mature solutions is allowed when it reduces total burden and preserves authority clarity.

Permanent rule:

```text
MODULAR_COMPOSITION=ALLOWED
ONE_AUTHORITATIVE_OWNER_PER_RESPONSIBILITY=REQUIRED
OVERLAPPING_DURABLE_STATE_OMS_POSITION_RISK_AUTHORITY=PROHIBITED
```

Before accepting a composition, publish an ownership map for at least:

```text
MARKET_DATA
CLOCK / EVENT LOOP
ORDERS / OMS
FILLS
POSITIONS
PORTFOLIO / ACCOUNT STATE
GENERIC RISK
STRATEGY RISK POLICY
PERSISTENCE / RECOVERY
BACKTEST / REPLAY
LIVE EXECUTION
```

`NOT_APPLICABLE` is allowed where a component does not own the responsibility.

A composition that requires synchronization between two competing authorities for the same durable truth fails the gate unless one is explicitly non-authoritative/read-only and that status is mechanically preserved.

---

## 17. Bounded customization

Small customization is allowed when it preserves the mature component as the clear owner.

Prefer:

```text
CONFIGURATION
OFFICIAL PLUGIN / EXTENSION
THIN ADAPTER
UPSTREAM CONTRIBUTION
```

Custom integration must state:

```text
CUSTOM_SCOPE
WHY_IT_IS_PROJECT_SPECIFIC_OR_THIN
UPSTREAM_SEAM_USED
STATE_OWNED_BY_CUSTOM_CODE
AUTHORITY_OWNED_BY_CUSTOM_CODE
MIGRATION / EXIT SEAM
EXPECTED_MAINTENANCE_BURDEN
```

If custom code starts owning generic reconnect, OMS, portfolio, generic risk, durable recovery or another commodity responsibility already owned by the mature platform, reclassify it as `COMMODITY_INFRASTRUCTURE` and reopen this procedure.

---

## 18. Custom commodity exception

If every credible mature route has a proven P0 blocker, Engineering Control or a Writer may recommend a custom commodity implementation but **may not authorize or begin it**.

Required exception packet:

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

Writer self-PASS, Engineering Control preference, prior custom code, schedule pressure or sunk cost cannot substitute for this authority.

---

## 19. Adoption controls

Before an external solution becomes accepted project infrastructure, record as applicable:

```text
CANONICAL_SOURCE
EXACT_ACCEPTED_VERSION / COMMIT / ARTIFACT
PACKAGE_OR_IMAGE_ORIGIN
LOCK / PIN POLICY
LICENSE
SECURITY_POLICY
KNOWN_CRITICAL_VULNERABILITIES / RESPONSE
PROVENANCE / SIGNATURE / SBOM / SLSA EVIDENCE WHEN AVAILABLE
DIRECT_AND_MATERIAL_TRANSITIVE_DEPENDENCY_RISK
OFFICIAL_EXTENSION_SEAM
PROJECT_ADAPTER_CONTRACT
AUTHORITY_OWNERSHIP_MAP
ROLLBACK / DISABLE PLAN
EXIT / REPLACEMENT SEAM
UPGRADE_POLICY
OBSERVABILITY / HEALTH SIGNALS
REPRESENTATIVE_ACCEPTANCE_PROOF
INDEPENDENT_REVIEW_REQUIREMENT
```

Do not convert an evaluation spike into accepted infrastructure without a separate adoption decision and the normal publication/activation gates.

---

## 20. Re-evaluation and decision expiry

External-solution decisions are versioned decisions, not permanent truths.

Reopen this procedure when any of the following becomes material:

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

### 20.1 Legacy custom-code expiry trigger

For project-owned commodity infrastructure, any prior `KEEP_CUSTOM`, `DEFER_MIGRATION`, `NO_FRAMEWORK_CHANGE` or equivalent decision expires before another semantic repair when any occurs:

```text
MATERIAL_DEFECT_IN_COMMODITY_BOUNDARY
CLEAN_REPLACEMENT_REQUIRED
REPEATED_PROVIDER_OR_QUALIFICATION_FAILURE
VERIFICATION_BURDEN_BECOMES_MATERIAL_OR_COMPARABLE_TO_IMPLEMENTATION
REPAIR_BUDGET_EXHAUSTED
```

Required consequence:

```text
DIRECT_PATCH_AUTHORITY=STOP
MATURE_SOLUTION_GATE_REOPEN=MANDATORY
```

This does not force migration after every bug. It forces re-evaluation before more custom commodity investment.

---

## 21. Selection decision record

Every material selection produces a durable record containing:

```text
DECISION_ID / DATE
CURRENT_LIVE_PROJECT_IDENTITY
RESPONSIBILITY_BOUNDARY
CAPABILITY_CLASS
CURRENT_NEED
NEXT_EXPECTED_STAGE
P0_REQUIREMENTS
CANDIDATE_LONGLIST
AUTHENTICATED_SHORTLIST
P0_MATRIX
EVIDENCE_GRADES
WEIGHTS_AND_RATIONALE
SCORECARD
DECISION_STABILITY_RESULT
TOTAL_BURDEN_COMPARISON
AUTHORITY_OWNERSHIP_MAP
SELECTED_ROUTE
REJECTED_ROUTES_AND_EXACT_REASONS
RESIDUAL_RISKS
SPIKE_RESULT_IF_ANY
ADOPTION_CONTROLS
RE_EVALUATION_TRIGGERS
CUSTOM_EXCEPTION_AUTHORITY_IF_ANY
```

The record may live in the active GitHub Issue/ADR-like history. Do not create a new competing project-wide rulebook for every selection.

---

## 22. Review anti-gaming checks

Independent review of a material external-solution decision must check at least:

- capability classification was not manipulated to call commodity code “strategy”;
- P0 requirements were frozen before scoring;
- no P0 FAIL was hidden by weighted scoring;
- no important P0 PASS relies only on marketing/popularity;
- candidate discovery included credible competing categories;
- negative evidence and project-specific limitations were searched;
- weights were not changed after seeing results;
- total burden includes maintenance/upgrades/exit, not only first implementation;
- modular composition has one authority owner per responsibility;
- customization remains thin and does not recreate commodity ownership;
- a Tiny Spike answered only its frozen blocker and stayed within budget;
- custom commodity work, if proposed, has explicit current user authority;
- the decision considers the known next product stage, not only the current ticket.

A failure of these checks is a route-decision defect, not a Writer coding defect.

---

## 23. Evidence basis

This procedure is informed by mature external methods and primary guidance, including:

- NIST SSDF / SP 800-218 — third-party component criteria, verification and secure software practices;
- NIST SP 1326 — supplier/product due diligence including provenance, resilience and foundational cyber practices;
- OpenSSF Concise Guide for Evaluating Open Source Software — candidate identification, authenticity, activity, security, API stability, tests, dependency and license checks;
- OpenSSF Scorecard / OSPS Baseline / Best Practices — security and project-practice signals;
- SLSA provenance — verifiable artifact/source/build provenance;
- Semantic Versioning — explicit public API/version compatibility expectations;
- CMU SEI ATAM — structured evaluation of interacting architecture quality attributes and trade-offs;
- ISO/IEC 25010 quality-model vocabulary — consistent software quality evaluation categories;
- AWS Well-Architected — measure overall efficiency and avoid spending project engineering effort on undifferentiated heavy lifting.

These sources provide evaluation principles. They do not choose a Trader Assist framework automatically; project P0 fit and total burden remain decisive.

---

## 24. Authority boundary

This procedure does not authorize:

```text
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