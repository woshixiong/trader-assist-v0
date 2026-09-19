# Trader Assist / Trade OS — Unified Engineering Governance and Execution Standard V2

**Status:** CANONICAL GOVERNANCE CANDIDATE  
**Effective date:** 2026-09-01  
**Last material amendment candidate:** 2026-09-10  
**Repository:** `woshixiong/trader-assist-v0`  
**Authority intent:** on independent acceptance and merge, this file becomes the **single project-wide normative engineering ruleset**. Task-specific Product / Strategy / Operations / Security authority and narrow executor/tool/deployment contracts may be stricter in their own domain, but they must not become competing engineering constitutions.

This document consolidates the durable engineering rules previously spread across the Unified V1 standard, the mandatory preflight rule, the research/evidence method, Issue #139 holistic verification work, generated-command reliability incidents, tool-onboarding lessons and accepted workflow practice.

It grants no Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, wallet/signing, exchange-write, order-submission or autonomous-trading authority.

---

## 1. Governance architecture and precedence

### 1.1 One normative engineering constitution

Project-wide engineering rules have one normative owner: this document.

The documentation architecture is:

```text
AGENTS.md
= compact entry map

PROJECT_RULES_INDEX.md
= navigation / active-authority index

UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md
= sole project-wide normative engineering constitution

MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md
= executable checklist / record derived from this constitution

PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md
= task-conditional research procedure / examples; no competing authority

EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md
= task-conditional mature-solution selection/adoption procedure; no competing authority

GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md
= task-conditional operator-command procedure / incident catalogue; no competing authority

executor / model / tool / FinalShell / Hermes profiles
= narrow task-conditional contracts after route selection
```

Maps and checklists point to rules; they do not redefine them. A specialized contract may add stricter requirements for its exact executor, deployment surface or safety domain, but cannot weaken this file without an explicit governance change.

### 1.2 Source of truth

GitHub is the canonical engineering source of truth.

Before material work, resolve from live GitHub as applicable:

```text
LIVE_REPOSITORY
LIVE_MAIN_SHA
ACTIVE_ISSUE_OR_PR
EXACT_BASE / EXACT_HEAD
EXACT_CHANGED_PATHS
EXACT_HEAD_CI
CURRENT_PRODUCT_STRATEGY_OPERATIONS_SECURITY_AUTHORITY
```

Actual code, exact diffs, accepted artifacts and current GitHub objects override stale chat summaries, old prompts, old PR bodies and remembered SHAs.

### 1.3 Precedence

When rules appear to conflict, use:

1. explicit current user authority and safety boundary;
2. current accepted Product / Strategy / Security / Operations authority for the narrow domain;
3. this Unified Engineering Governance V2;
4. the current material-task preflight record and frozen Task Packet;
5. applicable narrow executor/tool/deployment contracts;
6. historical governance, superseded ADR-like decisions and chat narrative as rationale only.

A less strict rule never weakens a stricter authority or safety requirement.

---

## 2. Universal engineering objective

Optimize for **validated useful progress per unit of total engineering effort**.

Order of preference:

```text
REAL SAFETY / AUTHORITY CORRECTNESS
-> ROOT-CAUSE CORRECTNESS
-> PRODUCT / TRADING / DATA USEFULNESS
-> SIMPLE MATURE REUSABLE ROUTE
-> CONTINUITY / REPLACEABILITY
-> VALIDATION QUALITY
-> LOW HUMAN RELAY / LOW REWORK
-> TOKEN / QUOTA / WALL-CLOCK EFFICIENCY
-> OPTIONAL SOPHISTICATION
```

Free, cheap, fashionable or technically interesting solutions never override correctness or fit.

Total engineering burden includes implementation, tests, independent review, CI/release, operator actions, model/token cost, debugging/evidence, maintenance, recovery, migration and future replacement cost.

`NO_NEW_DEPENDENCY` is not a simplicity proof. A mature dependency may reduce total burden when it replaces a larger project-owned responsibility. Dependency count, LOC count and current familiarity are inputs, never substitutes for total lifecycle burden.

---

## 3. Mandatory end-to-end workflow

For material engineering work use this sequence:

```text
LOAD LIVE STATE + CANONICAL RULES
-> CLASSIFY TASK / AUTHORITY / CAPABILITY
-> INDEPENDENT ANALYSIS
-> IF MATURE-SOLUTION / COMMODITY DECISION APPLIES:
     STAGE 0 REQUIREMENT + P0 FREEZE
     + EXTERNAL MATURE-SOLUTION SELECTION PROCEDURE
-> EXTERNAL / MATURE-SOLUTION EVIDENCE WHEN DIRECTION-SETTING
-> SYNTHESIS / ROUTE DECISION
-> RESEARCH-INVESTMENT / EVIDENCE-CONVERGENCE GATE WHEN A MATERIAL RESEARCH FRONTIER IS REACHED
-> ONE-BLOCKER / CHEAP SAFE DECISIVE PRE-WRITER GO/NO-GO EXPERIMENT WHEN APPLICABLE
-> GLOBAL ARCHITECTURE + CONTRACT + CONTINUITY PREFLIGHT
-> SCALE / PROVIDER / FRESHNESS PREFLIGHT WHEN APPLICABLE
-> STAGE CLAIM LADDER + VERIFICATION + VALIDATION-ENVIRONMENT PLAN
-> FREEZE ATTACK MATRIX / REPAIR BUDGET / TASK PACKET
-> ONE COHERENT WRITER STAGE
-> CHEAPEST DECISIVE VALIDATION OUTWARD
-> EXACT ARTIFACT / EXACT HEAD
-> AUTHORITATIVE CI / ENVIRONMENT-SPECIFIC PROOF
-> INDEPENDENT REVIEW
-> BOUNDED REPAIR OR REPLAN
-> SEPARATE USER PUBLICATION / DEPLOYMENT / RUNTIME GATES
-> INCIDENT / LESSON CAPTURE
```

The specialized mature-solution procedure must preserve the project research ordering: independent analysis first, external evidence second, synthesis/decision third.

Every bounded task ends in an explicit disposition:

```text
PROCEED
PASS_TO_PUBLICATION
REPAIR
REPLAN
DEFER
REPLACE
MERGED
SAFE_STOP
CANCELLED
```

An intermediate test, CI or Reviewer PASS is not task completion unless the active task contract explicitly defines it as terminal.

### Task-completion truth gate

Whole-task completion is distinct from completion of any intermediate stage. Writer completion, a CI pass, an independent Review pass, publication completion, or PR merge is not by itself whole-task completion. When the active task contract requires post-merge readback or verification, a merged PR remains intermediate until that required gate passes.

The project-wide task-completion predicate is:

```text
TASK_COMPLETION_TRUTH_GATE=PASS
IFF
USER_REQUEST_SCOPE_TERMINAL_OBJECTIVE_REACHED=YES
AND ACTIVE_TASK_CONTRACT_TERMINAL_DISPOSITION_REACHED=YES
AND ALL_REQUIRED_INDEPENDENT_REVIEWS_TERMINAL=PASS_OR_NOT_APPLICABLE
AND REQUIRED_PR_TERMINAL_DISPOSITION=PASS_OR_NOT_APPLICABLE
AND REQUIRED_LIVE_MAIN_READBACK=PASS_OR_NOT_APPLICABLE
AND REQUIRED_POST_MERGE_OR_POST_PUBLICATION_VERIFICATION=PASS_OR_NOT_APPLICABLE
AND REQUIRED_LINKED_TASK_TERMINALITY_READBACK=PASS_OR_NOT_APPLICABLE
AND REQUIRED_OPEN_PR_OR_SUPERSEDED_WORK_SWEEP=PASS_OR_NOT_APPLICABLE
AND NO_REQUIRED_NEXT_GATE_IS_SILENTLY_OMITTED=YES
```

Applicability is derived from the current user-request scope and the active bounded-task contract. That contract controls terminality. Every applicable required gate must pass; every non-applicable gate must be recorded as `NOT_APPLICABLE` and must not block completion. A gate may not be skipped when applicable, and an unconditional false or safe-stop gate may not replace contract-scoped applicability.

The mere existence or continued activity of an umbrella Issue, PR, or other linked artifact does not make its closure or terminality a universal prerequisite. An umbrella Issue may remain open or advance to a separate explicit next stage when the current bounded user-request scope and active task contract are terminal and every applicable required gate for that bounded task passes. Conversely, a linked or superseded artifact that is part of the bounded task must receive its applicable readback or sweep.

Any pending user-retained gate required by the active task contract prohibits `TASK_COMPLETION_TRUTH_GATE=PASS`. Mark Ready and merge remain separate user-retained gates. This predicate grants no authority to execute either gate and grants no deployment, runtime, credential, private-API, wallet, signing, exchange, trading, or capital authority. An accepted merged PR may still close or advance its linked task as governed by the reviewed-PR closeout procedure.

Required consequences include:

```text
MERGE_IN_ACTIVE_TASK_CONTRACT=YES
AND LIVE_MAIN_READBACK != PASS
=> TASK_COMPLETION_TRUTH_GATE=FAIL

POST_MERGE_VERIFICATION_REQUIRED_BY_ACTIVE_TASK_CONTRACT=YES
AND POST_MERGE_OR_POST_PUBLICATION_VERIFICATION != PASS
=> TASK_COMPLETION_TRUTH_GATE=FAIL

NO_PR_IN_ACTIVE_TASK_CONTRACT
=> LINKED_PR_STATE_READBACK=NOT_APPLICABLE
=> OPEN_PR_OR_SUPERSEDED_WORK_SWEEP=NOT_APPLICABLE
   unless a linked or superseded PR is part of this bounded task

UMBRELLA_ISSUE_CONTINUES_TO_SEPARATE_NEXT_STAGE
AND CURRENT_BOUNDED_TASK_IS_TERMINAL
=> ISSUE_CLOSURE_IS_NOT_A_UNIVERSAL_COMPLETION_PREREQUISITE
```

If `TASK_COMPLETION_TRUTH_GATE != PASS`, user-facing whole-task words such as `complete`, `done`, or `已完成` are prohibited. Report only the exact stage reached, the failed or pending applicable gates, and the next required gate.

---

## 4. Task classification and mandatory preflight

### 4.1 Material vs mechanical

A task is MATERIAL when it creates or changes a substantive decision involving architecture, authority, provider, persistence, lifecycle, concurrency, recovery, scale, security, release semantics, model/tool route, cross-layer contract or meaningful product/strategy behavior.

Purely mechanical exact-state work may use a shortened preflight. If mechanical work exposes a new material choice, reclassify immediately.

### 4.2 Required gates

No material Writer implementation begins until:

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
```

The preflight must establish, where applicable:

```text
LIVE_REPO / MAIN / ISSUE_OR_PR / START_HEAD
ROLE / TASK_CLASS / USER_AUTHORITY_REQUIRED_NOW
ROOT_CAUSE_LEVEL
AFFECTED_AUTHORITIES
FROZEN_INVARIANTS
CURRENT_ROUTE
CAPABILITY_CLASS
MATURE_ALTERNATIVES
MATURE_SOLUTION_SELECTION_DISPOSITION
CUSTOM_COMMODITY_EXCEPTION_USER_AUTHORITY
RESEARCH_FRONTIER / RESEARCH_INVESTMENT_DISPOSITION WHEN APPLICABLE
STAGE_CLAIM_LADDER / AUTHORITATIVE_PROOF_SURFACE_FOR_EACH_STAGE
MINIMUM_REPRESENTATIVE_TOPOLOGY / COMPLEXITY_ESCALATION_ORDER
PRE_WRITER_GO_NO_GO_EXPERIMENT
DETERMINISTIC_BRANCH_PROOF_PLAN / REAL_EXTERNAL_BOUNDARY_PROOF_PLAN
CURRENT_NEED / NEXT_EXPECTED_STAGE
STABLE_INTERFACES / STABLE_AUTHORITIES
REPLACEABLE_IMPLEMENTATION_SEAMS
PROVIDER_SCALE_FRESHNESS_BUDGET
ATTACK_MATRIX
CANONICAL_VALIDATION_COMMANDS
VALIDATION_PLATFORM_CLASS
AUTHORITATIVE_VALIDATION_ENVIRONMENT
KNOWN_ENVIRONMENT_MISMATCHES
FALLBACK_VALIDATION_SURFACE
EXACT_RELEASE_VERIFICATION_PLAN
EVIDENCE_CHECKPOINT_PLAN
WRITER_SCOPE / PROHIBITED_SCOPE
REPAIR_STAGE / STOP_CONDITION
```

`NOT_APPLICABLE` is explicit; unresolved applicable fields prohibit Writer dispatch.

---

### 4.3 Controller-resolved authority and progressive Writer context

Canonical authority and model context are different concerns.

Engineering Control resolves live GitHub identity, applicable governance, authority ownership, route, scope, evidence topology and material preflight before semantic Writer dispatch.

The frozen Writer packet must bind the control result:

```text
TASK_PACKET_HASH=REQUIRED
GOVERNANCE_ATTESTATION_MAIN_OR_BASE_SHA=REQUIRED
PREFLIGHT_ATTESTATION=REQUIRED
NORMALIZED_REQUIRED_AUTHORITY_ASSERTIONS=REQUIRED
AUTHORITY_PROVENANCE_LOCATORS=REQUIRED
```

The controller supplies the bounded authority facts the Writer actually needs; provenance locators identify their canonical source. A locator by itself is not a demand that a tool-limited Writer rediscover full Issue/file history.

Default Writer context:

```text
ROOT_AGENTS_MAP
+ FROZEN_TASK_PACKET
+ BOUND_PREFLIGHT_GOVERNANCE_ATTESTATION
+ NORMALIZED_REQUIRED_AUTHORITY_ASSERTIONS_WITH_PROVENANCE
+ EXACT_AFFECTED_CODE_TEST_SURFACES
+ TASK_CONDITIONAL_EXECUTOR_PROFILE
```

Default prohibitions:

```text
FULL_UNIFIED_V2_RELOAD_BY_WRITER=NO
FULL_MANDATORY_PREFLIGHT_RELOAD_BY_WRITER=NO
FULL_PROJECT_RULES_INDEX_RELOAD_BY_WRITER=NO
FULL_ISSUE_OR_PR_HISTORY_RELOAD_BY_WRITER=NO
BROAD_GOVERNANCE_DOCS_SEARCH_BY_WRITER=NO
REPEAT_L1_RESEARCH_ALREADY_FROZEN_BY_CONTROL=NO
```

Exceptions are narrow:
- a concrete conflict, missing material fact, stale identity or ambiguous authority -> read the minimum canonical source or return to Engineering Control;
- a governance-maintenance task whose object is the governance corpus may read the exact governance files it changes/reviews, but not unrelated history merely because it exists.

Identity drift between the bound attestation/Task Packet and the actual worktree/head invalidates the attestation.

```text
PROGRESSIVE_GOVERNANCE_DISCLOSURE=REQUIRED
COMPACT_EXACT_TASK_PACKET=REQUIRED
CANONICAL_GOVERNANCE_DETAIL_MAY_REMAIN_FULL=YES
WRITER_CONTEXT_NE_CANONICAL_CORPUS=YES
CONTEXT_BLOAT_WITHOUT_INCREMENTAL_DECISION_VALUE=PROHIBITED
```

### 4.4 Project-wide context architecture

Progressive disclosure applies to Engineering Control, semantic Writers and independent Reviewers, not only to the Writer.

```text
L1_ALWAYS_ON_CORE=
  root authority map + rules index/navigation + live identity

L2_ACTIVE_STATE=
  current durable stage checkpoint / Task Packet / Review Manifest

L3_TARGETED_CANONICAL_RETRIEVAL=
  minimum exact source needed for a concrete unknown, conflict, drift or supersession question

L4_COLD_HISTORY_AND_RAW_EVIDENCE=
  complete historical Issues/PRs/logs/artifacts retained outside model context by default
```

The active durable checkpoint must preserve, as applicable:

```text
CURRENT_STAGE
EXACT_MAIN / BASE / HEAD / TREE
ACTIVE_AUTHORITY_AND_PROVENANCE
ACCEPTED_DECISIONS
SUPERSEDED_OR_REJECTED_ROUTES
UNRESOLVED_BLOCKERS
WRITE / READ SCOPE
ACCEPTANCE_CRITERIA
NEXT_AUTHORIZED_ACTION
REVIEW_REQUIRED
STOP_CONDITIONS
```

Every compressed assertion that materially affects execution must either carry its exact canonical provenance locator or be directly fresh-verifiable from live state. Compression is not permission to omit an authority, blocker, negative constraint or safety boundary.

```text
CHAT_HISTORY_IS_NOT_ENGINEERING_STATE=YES
GITHUB_DURABLE_CHECKPOINT_IS_ENGINEERING_STATE=YES
NO_CRITICAL_ENGINEERING_STATE_ONLY_IN_CHAT=YES
FULL_ISSUE_PR_HISTORY_RELOAD_BY_CONTROL=NO_BY_DEFAULT
FULL_GOVERNANCE_CORPUS_RELOAD_BY_CONTROL=NO_BY_DEFAULT
FULL_ISSUE_PR_HISTORY_RELOAD_BY_REVIEWER=NO_BY_DEFAULT
RAW_LONG_LOG_IN_MODEL_CONTEXT=NO_BY_DEFAULT
QUALITY_AND_CORRECTNESS_GT_CONTEXT_ECONOMY=YES
```

If the compact state is insufficient, perform a targeted canonical read. If the material fact remains unresolved, fail closed; never guess to save context.

Large single-file retrieval follows the same escalation ladder:

```text
KNOWN_SYMBOL / HEADING / RANGE
-> TARGETED RANGE FIRST
-> ADJACENT SECTION IF NEEDED
-> FULL FILE ONLY WHEN WHOLE-FILE SEMANTICS ARE MATERIALLY REQUIRED
```

### 4.5 Engineering-window lifecycle and automatic rotation

Every Engineering Control conversation/window must declare at entry:

```text
WINDOW_SCOPE=
ROTATION_TRIGGER=
ACTIVE_CHECKPOINT_REF=
```

Rotation is event-driven; it does not depend on the user seeing an internal token/context meter. Default triggers include:

- completion of the current material stage;
- material replan, authority change or ownership boundary;
- independent-review handoff;
- command-family holistic regeneration;
- product context warning or loss of context trust;
- repeated transport/stream interruption that creates transcript-integrity risk.

On trigger:

```text
FREEZE_AND_VERIFY_GITHUB_CHECKPOINT
-> GENERATE_COMPLETE_SUCCESSOR_WINDOW_PROMPT
-> STOP CURRENT_WINDOW_BEFORE_NEXT_MATERIAL_STAGE
```

The successor verifies live identity plus the predecessor checkpoint before material work. It starts from the checkpoint, not by replaying the whole predecessor transcript. Failure to produce/verify the checkpoint or successor prompt blocks transition into the next material stage.

## 5. Research, evidence and decision method

Material direction-setting work uses a strict three-stage method.

### Phase 1 — independent analysis first

Before reading external conclusions, establish from project facts and first principles:

- exact problem and user objective;
- facts, assumptions and unknowns;
- causal/mechanical model;
- decision criteria and constraints;
- candidate routes;
- expected benefits, failure modes and trade-offs;
- evidence that could confirm, weaken or falsify the preliminary view.

Preserve a short pre-research position for material decisions.

For a framework/provider/platform/tool selection, freeze the responsibility boundary, capability class, current bounded need, next expected product stage and hard P0 requirements before candidate scoring.

### Phase 2 — external evidence and mature solutions

Then consult the strongest relevant evidence, prioritizing:

1. official specifications, provider docs, first-party source repositories;
2. primary research, inspectable data and reproducible benchmarks;
3. mature maintained frameworks and validated production cases/postmortems;
4. high-quality independent technical analysis;
5. community anecdotes only as supplemental evidence.

Search for competing approaches, limitations, negative cases and disconfirming evidence. Check freshness when it matters.

When a material decision selects, rejects, composes, customizes, adopts, upgrades or re-evaluates an external mature solution, or proposes project-owned commodity infrastructure, the task must load `EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md`. Its candidate authentication, P0, evidence-confidence, total-burden, decision-stability, Stage 0, Tiny Spike, adoption and re-evaluation requirements are mandatory procedure under this constitution.

### Phase 3 — synthesis and route freeze

Explicitly record:

```text
WHAT_EXTERNAL_EVIDENCE_CONFIRMS
WHAT_IT_MODIFIES
WHAT_IT_REJECTS
RESIDUAL_UNCERTAINTY
REJECTED_ROUTES_AND_WHY
SELECTED_ROUTE_AND_PROJECT_FIT
VALIDATION_OR_EXPERIMENT_REQUIRED
```

Research must converge to a decision. Endless research around the same failed design is prohibited.

For a mature-solution decision, preserve the typed selection disposition rather than paraphrasing an unresolved comparison into a Writer instruction.

### Research-investment, complexity and evidence-convergence gate

A material research frontier is reached when the current evidence has been used as far as it can support a defensible decision and further progress would require one or more of:

- materially new data or a new data-retention surface;
- new provider/infrastructure work;
- a materially larger experiment;
- additional model/rule/parameter search on substantially the same historical evidence;
- a new source of independent OOS/Forward evidence.

Reaching that frontier **does not** automatically authorize more research, more data engineering or a new infrastructure project. The next step must be selected by comparing the expected decision value of additional information with its total burden and with the value of proceeding to the next safe evidence stage.

Record, at an applicability-scaled level:

```text
RESEARCH_FRONTIER_REACHED=YES|NO
MISSING_EVIDENCE_OR_DATA=
DECISION_CRITICALITY=HARD_BLOCKER|MATERIAL_OPTIMIZATION|OPTIONAL
EXPECTED_DECISION_IMPACT=LOW|MEDIUM|HIGH|BOUNDED_ESTIMATE
EXPECTED_UNCERTAINTY_REDUCTION=LOW|MEDIUM|HIGH|BOUNDED_ESTIMATE
TOTAL_RESEARCH_BURDEN=
DELAY_OPPORTUNITY_COST=
COMPLEXITY_OVERFIT_COST=
DATA_PERISHABILITY_OR_RECONSTRUCTABILITY=
NEXT_STAGE_REVERSIBILITY_AND_RISK=
FORWARD_OR_INDEPENDENT_EVIDENCE_VALUE=
RESEARCH_INVESTMENT_DISPOSITION=
```

The conceptual decision rule is:

```text
EXPECTED_NET_RESEARCH_VALUE
≈ EXPECTED_DECISION_VALUE_OF_INFORMATION
  - TOTAL_RESEARCH_BURDEN
  - DELAY_OPPORTUNITY_COST
  - COMPLEXITY / OVERFIT COST
```

This is a decision aid, not a demand for false numerical precision. Qualitative evidence or bounded estimates are acceptable when exact monetization is not defensible.

A safety, authority, correctness, data-integrity, causal-validity or next-stage-claim blocker is a hard gate and may not be traded away merely because research is expensive. Otherwise, uncertainty alone is not sufficient reason to continue research.

Every material frontier must end in exactly one of these research-investment dispositions:

```text
ACQUIRE_BEFORE_NEXT_GATE
CAPTURE_CHEAP_OPTIONALITY
PROCEED_WITH_CURRENT_BEST_AND_DEFER
PARK_OR_REJECT
```

#### `ACQUIRE_BEFORE_NEXT_GATE`

Use when the missing evidence is required for safety/correctness/causal validity or for the authoritative next-stage claim, or when the expected decision impact is materially high relative to total burden. Acquire only the cheapest decisive evidence needed for the unresolved decision. Provider-native, accepted or mature capability remains preferred for commodity data/infrastructure.

#### `CAPTURE_CHEAP_OPTIONALITY`

Use when the data is not required for the current decision but is ephemeral or difficult to reconstruct later, has credible future research value, and can be captured with low total lifecycle burden without creating a second authority or speculative platform. Capture is non-authoritative research evidence by default; collecting a field does not authorize using it in the current Strategy/policy or promotion claim. If capture itself becomes material infrastructure, this disposition no longer applies and the requirement must be re-gated.

#### `PROCEED_WITH_CURRENT_BEST_AND_DEFER`

Use when the current candidate is coherent, deterministic, versioned where applicable, causally defined, testable and safe/correct for the next authorized stage; the missing information is optimization-level rather than a hard blocker; and the expected value of independent OOS/Forward/real-environment evidence is at least as valuable as another historical/data-engineering cycle. Freeze known unknowns and deferred hypotheses explicitly. This disposition never bypasses a required promotion, Shadow, Testnet, safety, deployment or real-capital gate.

#### `PARK_OR_REJECT`

Use when expected decision impact is low, the requirement is stale/obsolete, counterevidence is strong, or total burden/complexity is disproportionate to plausible value. Record a concrete re-open trigger when one exists; do not retain zombie TODOs that silently consume planning attention.

#### Simplicity, adaptive research and strategy overfitting control

For trading Strategy research, the target is **not the most optimized historical strategy**. The target is the simplest strategy that is sufficiently effective and robust for the next evidence stage, after realistic costs and under current evidence.

Permanent Strategy research principles:

```text
EFFECTIVENESS_BEFORE_SIMPLICITY=YES
SIMPLEST_AMONG_MATERIALLY_COMPARABLE_VALIDATED_CANDIDATES=YES
MINIMUM_NECESSARY_PARAMETERS_FEATURES_STATES_DATA_DEPENDENCIES=TARGET
DISCRETIONARY_ECONOMIC_COMPLEXITY_REQUIRES_INCREMENTAL_VALUE=YES
HISTORICAL_IN_SAMPLE_GAIN_ALONE_DOES_NOT_JUSTIFY_COMPLEXITY=YES
OOS_OR_FORWARD_INCREMENTAL_VALUE_REQUIRED_FOR_MATERIAL_DISCRETIONARY_ECONOMIC_COMPLEXITY_PROMOTION=YES
TRIAL_AND_ADAPTIVITY_LEDGER=REQUIRED
```

Do not impose a universal numeric parameter-count cap: an arbitrary cap can underfit a real mechanism. Instead, every material discretionary economic parameter, feature, state, conditional branch or data dependency needs a pre-specified causal hypothesis and an incremental-value test against a simpler baseline. When simpler and more complex candidates are materially comparable on independent/OOS/Forward evidence, prefer the simpler candidate because it reduces estimation error, overfit surface, maintenance and future change amplification.

Complexity independently required for safety, correctness, authority, data integrity or causal validity is governed by those hard gates and is not conditioned on an economic-uplift experiment. Such required complexity must still be validated for the actual safety/correctness/authority/data-integrity/causal claim it exists to satisfy.

Repeatedly trying rules, parameters, feature definitions or data interpretations on the same history increases selection bias and backtest overfitting risk. OOS data also loses independence when it is repeatedly inspected and used adaptively to redesign the candidate. Therefore track the effective search/trial history and do not treat a repeatedly consulted holdout as pristine evidence.

After substantial historical adaptivity, a frozen version tested on genuinely later/independent Forward evidence can have higher decision value than another round of historical optimization. Forward evidence is not an excuse to skip cheap decisive correctness tests; it is the preferred next information source when the remaining uncertainty is optimization-level and the next stage is authorized and sufficiently reversible/non-authoritative.

For Strategy candidates entering Forward Shadow or equivalent prospective evaluation:

```text
FREEZE_VERSION_BEFORE_FORWARD_EVIDENCE=YES
ANY_MATERIAL_STRATEGY_SEMANTIC_OR_EVIDENCE_AFFECTING_CHANGE=>NEW_IMMUTABLE_VERSION
MATERIAL_CHANGE_INCLUDES=RULE|PARAMETER|FEATURE|FEATURE_OR_DATA_DEFINITION|STATE|CONDITIONAL_BRANCH|DATA_DEPENDENCY
FORWARD_EVIDENCE_CLOCK_STARTS_AT_NEW_VERSION_ACTIVATION=YES
NO_RETROACTIVE_FORWARD_EVIDENCE_CREDIT=YES
```

#### Recursion and convergence guard

`DATA_BLOCKED_FRONTIER` or equivalent is not automatic data-engineering authority.

```text
RESEARCH_FRONTIER
-> RESEARCH_INVESTMENT_GATE
-> EXACTLY_ONE_RESEARCH_INVESTMENT_DISPOSITION
-> ONLY_THEN_NEXT_ACTION
```

A repeated pre-Forward acquisition/research cycle for the same strategy/problem family is presumptively disfavored once marginal information value is declining. Each new cycle must identify a **new material decision** and pass this gate again. “Another potentially useful enhancement exists” is not by itself a new material decision and should normally resolve to `PROCEED_WITH_CURRENT_BEST_AND_DEFER` or `PARK_OR_REJECT` unless a real safety/correctness/causal blocker has emerged.

Do not set an arbitrary maximum number of research cycles; a genuinely new high-value blocker may justify another cycle. The stop rule is declining expected decision value relative to total burden and the availability of a better independent evidence stage, not calendar impatience or a fixed iteration count.

### Pre-Writer GO/NO-GO feasibility experiment

```text
PRE_WRITER_GO_NO_GO_EXPERIMENT=WHEN_CHEAP_SAFE_AND_DECISIVE
```

When a material route depends on unresolved feasibility and a cheap, safe, read-only/non-authoritative experiment can decisively validate or falsify it, run that experiment before the semantic Writer or full implementation. A failed feasibility experiment requires `REPLAN` or `REPLACE`; do not consume the application repair budget patching an implementation for a route that was not proven feasible.

Do not require an experiment when the route is already sufficiently established or the experiment would add more burden or risk than decisive evidence.

For external mature-solution selection, a feasibility experiment is specifically a **One-Blocker Tiny Spike**: one candidate, one unresolved decisive P0 question, one bounded Writer stage. It must not become product implementation, a generalized test harness or a repair chain.

---

## 6. Mature capability no-rebuild, simplicity and build-vs-buy

### 6.1 Capability classification and terminology

Every material capability decision classifies the responsibility as:

```text
CAPABILITY_CLASS=
STRATEGY_DIFFERENTIATOR
| COMMODITY_INFRASTRUCTURE
| THIN_INTEGRATION
```

Use these terms consistently:

```text
STRATEGY_DECISION_ENGINE
= project-owned differentiated trading intelligence and policy

TRADING_INFRASTRUCTURE_ENGINE
= commodity trading/runtime infrastructure owned by mature external capability by default
```

`STRATEGY_DECISION_ENGINE` includes project-specific Setup/signal semantics, Scanner/ranking, Thesis/Attempt, entry/exit/re-entry/winner-management policy, strategy-specific sizing/risk policy, project-specific features, research and evidence semantics.

`TRADING_INFRASTRUCTURE_ENGINE` includes generic transport/session management, subscriptions/reconnect/heartbeat, generic market-data plumbing, generic OMS/order lifecycle, fill/order/position/account reconciliation, generic portfolio/account state, generic pre-trade limits/kill switches, generic persistence/recovery/replay, generic backtest/sandbox/live runtime mechanics, deployment, observability and workflow plumbing.

Names do not control classification; responsibility semantics do.

### 6.2 Mandatory ownership order

For nontrivial commodity capability use this order:

```text
REUSE_ACCEPTED_PROJECT_CAPABILITY  # must still pass current requirements; sunk cost creates no preference
-> PROVIDER_NATIVE
-> STANDARD / OFFICIAL
-> MATURE MAINTAINED EXTERNAL FULL FRAMEWORK
-> MATURE MAINTAINED EXTERNAL MODULAR COMPONENT / COMPOSITION
-> CONFIGURATION / OFFICIAL EXTENSION
-> THIN PROJECT ADAPTER
-> UPSTREAM CONTRIBUTION
-> CUSTOM COMMODITY INFRASTRUCTURE ONLY UNDER EXPLICIT EXCEPTION
```

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

A fitting mature solution therefore blocks unnecessary custom commodity engineering. Project-specific strategy semantics and genuinely thin integration remain valid project-owned work.

### 6.3 Engineering Control / Writer constraint

Engineering Control and Writers may discover candidates, perform the governed analysis, recommend selection, recommend rejection and recommend a custom exception. They **may not self-authorize** a custom commodity build.

If every credible mature route has a proven P0 blocker and custom commodity infrastructure is proposed:

```text
CUSTOM_COMMODITY_EXCEPTION_USER_AUTHORITY=REQUIRED
```

Without explicit current user authority:

```text
ENGINEERING_PREFLIGHT_GATE=FAIL
CUSTOM_WRITER_DISPATCH=PROHIBITED
```

### 6.4 Invalid mature-route rejection reasons

None of the following is a valid blocker by itself:

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

A mature route may be rejected only for a concrete P0 blocker such as functional fit, safety/authority, data/execution semantics, reliability/recovery, scale/performance, platform/operations, security/supply-chain, license/legal, extensibility/strategy continuity, integration burden or overlapping authority.

### 6.5 Stage 0 — no-product-code selection audit

Before product Writer work on a commodity capability, run a Stage 0 audit under the specialized selection rule:

```text
STAGE_0_PRODUCT_CODE=PROHIBITED
```

Stage 0 freezes current/next need, responsibility boundary, P0 requirements, safety/authority, quality attributes, strategy continuity, scale/latency and acceptable extension/exit seams; then authenticates and screens credible mature alternatives.

If strong documentation/source/evidence already decides the route, select/reject without a spike. Do not build multiple full prototypes to compare mature solutions.

### 6.6 One-Blocker Tiny Spike

A Tiny Spike is allowed only when exactly one material P0 uncertainty remains and a cheap, safe, non-authoritative experiment can decide it more efficiently than additional source/document review.

Default rule:

```text
ONE_CANDIDATE
ONE_UNRESOLVED_P0_QUESTION
ONE_WRITER_STAGE
NO_PRODUCT_IMPLEMENTATION
NO_NEW_DATABASE_RUNTIME_PERSISTENCE_OR_GENERAL_HARNESS
NO_PRODUCTION_DEPLOYMENT_PRIVATE_API_OR_EXCHANGE_WRITE
AT_MOST_ONE_SMALL_MECHANICAL_CORRECTION
SECOND_SEMANTIC_PROBLEM => STOP / REASSESS / NEXT_MATURE_ROUTE
```

The specialized selection procedure owns the default LOC/file budget and allowed pre-frozen override semantics. A Tiny Spike may not silently become Repair 2/3 implementation.

### 6.7 Modular composition and customization

Mature solutions may be composed when the composition lowers total burden and preserves authority clarity:

```text
MODULAR_COMPOSITION=ALLOWED
ONE_AUTHORITATIVE_OWNER_PER_RESPONSIBILITY=REQUIRED
OVERLAPPING_DURABLE_STATE_OMS_POSITION_RISK_AUTHORITY=PROHIBITED
```

Prefer configuration, official plugin/extension, thin adapter and upstream contribution. A long-lived invasive fork of mature framework internals is prohibited by default and is treated as custom commodity infrastructure for this gate.

If project integration code begins owning generic reconnect, OMS, portfolio, generic risk, durable recovery or another mature platform responsibility, reclassify the code as `COMMODITY_INFRASTRUCTURE` and reopen this gate.

### 6.8 Legacy custom decisions expire

For project-owned commodity infrastructure, prior `KEEP_CUSTOM`, `DEFER_MIGRATION`, `NO_FRAMEWORK_CHANGE` or equivalent decisions expire before another semantic repair when any occurs:

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

This does not automatically force migration after every bug. It prevents stale build-vs-buy decisions from authorizing more custom commodity investment without fresh evidence.

### 6.9 External-solution decision quality

Selection must use hard P0 gates first and comparative scoring only among P0-pass candidates. Popularity, stars, marketing or familiarity alone cannot make a P0 gate pass. Score/weight choices must be frozen before candidate results are known, and unstable winners must be reported as unresolved trade-offs rather than false certainty.

The specialized selection procedure defines exact evidence grades, default quality/burden dimensions, decision-stability checks, adoption controls, re-evaluation triggers and the custom-exception packet.

Prefer the simplest route that preserves safety, authority, correctness, recovery, strategy continuity, future V0 fit and replaceability. Do not build institution-grade infrastructure for a rare bounded task.

---

## 7. Architecture, authority and cross-layer contract rules

### 7.1 Global root cause before local patch loops

Repeated adjacent-layer fixes, growing special cases, mixed-state failures, duplicate authority conflicts or repeated Reviewer discoveries trigger:

```text
STOP LOCAL PATCHING
-> MODEL GLOBAL STATE / AUTHORITY / CONTRACT
-> RE-RUN RESEARCH + SIMPLICITY + CONTINUITY GATES
-> REOPEN MATURE-SOLUTION GATE WHEN THE FAILED RESPONSIBILITY IS COMMODITY
-> REPLAN OR REPLACE THE FAILED RESPONSIBILITY BOUNDARY
```

When strict immutable authority correctly exposes duplicate/conflicting work, fix the duplicate work; never weaken authority validation merely to silence the conflict.

### 7.2 Cross-layer contract closure

For adjacent authoritative layers:

```text
UPSTREAM_ACCEPTED_DOMAIN ⊆ DOWNSTREAM_SUPPORTED_DOMAIN
```

or the downstream owner must explicitly map legitimate admitted states to a typed semantic result such as:

```text
NO_ACTION
DEFER
UNAVAILABLE
DATA_INVALID
OWNER_LEVEL_BOUNDED_RETRY
```

Incidental arithmetic/parsing/assertion exceptions are not policy.

### 7.3 Admitted-input totality

Every legitimate provider/contract-admitted input must yield a deterministic typed outcome. Truly contradictory, corrupt or authority-invalid input remains fail-closed.

Strict helper functions may retain narrow preconditions when their owning layer correctly maps valid outer-domain cases before invoking them.

### 7.4 Authority model

For material cross-layer work freeze:

- canonical source of truth for each state;
- prohibited second caches/queues/authorities;
- state transitions and precedence;
- restart/replay/reopen semantics;
- idempotency/duplicate behavior;
- freshness/time boundaries;
- supersession/epoch semantics;
- unauthorized/malformed input behavior.

External mature-solution composition does not relax this rule. Each authoritative responsibility must have one owner; read-only observers/adapters must remain mechanically non-authoritative.

---

## 8. Continuity-first development

Every material implementation must consider both the current bounded need and the next expected stage.

Record:

```text
CURRENT_BOUNDED_NEED
NEXT_EXPECTED_STAGE
STABLE_AUTHORITIES
STABLE_INTERFACES
REPLACEABLE_IMPLEMENTATION_SEAMS
TUNING_PARAMETERS
PERSISTED_REPRESENTATION_VERSIONING
KNOWN_CHANGE_AMPLIFICATION_HOTSPOTS
MIGRATION_OR_LOCKIN_RISK
```

Prefer:

```text
STABLE NARROW CONTRACT
+ ONE CURRENT IMPLEMENTATION
+ REPLACEABLE POLICY
```

Avoid both throwaway shortcuts that force near-term rewrites and speculative generalized platforms for hypothetical future needs.

Do not split modules merely because they are large. A large integration hotspot triggers seam-extraction review when a new unrelated responsibility would otherwise increase change amplification.

Preserve backward-readable/versioned durable state when practical. Migrate incrementally behind stable seams rather than big-bang replacement.

For a mature external owner, preserve a narrow project contract and explicit exit/replacement seam where practical. Continuity means preserving project value and stable semantics; it does not mean preserving a custom commodity implementation merely because it already exists.

---

## 9. Scale, provider and freshness

Before first release or a material change to market count, history depth, cadence, retry/confirmation count, REST/WS use, concurrency, database workload or cohort size, calculate the relevant order-of-magnitude budget.

At minimum where applicable:

```text
market_count × calls_per_market × provider_weight × cadence
market_count × history_points × database_operations
```

Estimate or measure provider headroom, p50/p95/worst-case completion/freshness latency, CPU/memory/database load, event-loop/shutdown responsiveness and the intended trading/scanner freshness SLA.

Tiny-fixture correctness is insufficient for scale-dependent behavior. Include a realistic-order-of-magnitude acceptance test when production scale materially differs.

Do not respond by building a generic capacity platform unless evidence requires one.

---

## 10. Writer stage, Task Packet and active ownership

### 10.1 One coherent Writer

```text
PARALLELIZE INDEPENDENT WORK
SERIALIZE SHARED AUTHORITY
ONE_PRIMARY_WRITER_PER_COHERENT_SHARED_AUTHORITY_STAGE=YES
```

Do not create competing Writers against the same durable truth or release branch. Split only at real contract, authority, worktree or independence boundaries.

### 10.2 Complete Task Packet

Before execution freeze one complete self-contained packet containing as applicable:

```text
ROLE / MODE / TASK_ID
REPOSITORY / BASE / HEAD / BRANCH / WORKTREE
OBJECTIVE / ROOT_CAUSE
CURRENT_AUTHORITIES / FROZEN_INVARIANTS
CAPABILITY_CLASS / MATURE_SOLUTION_SELECTION_DISPOSITION
CUSTOM_COMMODITY_EXCEPTION_USER_AUTHORITY
ALLOWED_FILES / PROHIBITED_SCOPE
REQUIRED_BEHAVIOR / MUST_REMAIN_BEHAVIOR
CONTINUITY / SCALE REQUIREMENTS
ATTACK_MATRIX
CANONICAL_TEST / LINT / TYPE / COMPILE COMMANDS
VALIDATION_ENVIRONMENT
COMMIT / PUSH AUTHORITY
REVIEW_REQUIREMENT
REPAIR_STAGE / SAFE_STOP CONDITIONS
OUTPUT_CONTRACT
FINAL_USER_AUTHORITY_BOUNDARY
```

If a new architecture invariant, provider constraint, authority boundary, mature-solution P0 blocker or major attack case is discovered before execution, regenerate one complete replacement packet. Architecture-critical prompt addenda assembled by the user are prohibited.

### 10.3 Active task ownership

The current control/orchestration role owns the bounded task until terminal disposition or explicit acknowledged handoff.

At intermediate gates it must execute every safe authorized next action, prepare the minimum blocked next step, minimize user relay and stop only the specific unauthorized/external action. A blocked action does not abandon the task.

The user is not the routine Writer/CI/Reviewer information bus when exact evidence can be carried directly.

### 10.4 Lossless authority-bearing handoff

Authoritative handoffs must preserve exact meaning, authority and control fields.

Do not use this as the execution-authority path when the transformation could change scope, permissions, acceptance criteria, stop conditions, route, executor or authority:

```text
AUTHORITATIVE TASK
-> INTERMEDIARY SUMMARY / PARAPHRASE
-> DOWNSTREAM EXECUTOR
```

Prefer a lossless propagation path:

```text
EXACT TASK PACKET OR EXACT IMMUTABLE POINTER
+ INTEGRITY IDENTITY (HASH / EXACT SHA WHEN APPLICABLE)
-> DOWNSTREAM READS THE EXACT AUTHORITATIVE PAYLOAD
-> IDENTITY / AUTHORITY ACKNOWLEDGEMENT
-> EXECUTION
-> RAW EVIDENCE RETURN
```

An intermediary summary may improve readability or navigation, but it is not a substitute downstream execution authority when any authoritative field could be changed, omitted or weakened. The exact packet, immutable pointer and raw evidence remain authoritative over intermediary summaries or paraphrases.

Where a selected specialized operator/handoff contract is stricter, such as a lossless task-packet schema, the stricter contract additionally applies and may not weaken this project-wide rule.

### 10.5 Authority-bearing review-result egress

Before dispatching an authority-bearing independent review whose result is consumed downstream, the owning controller must have direct access to the exact result. Provider-native direct writeback is preferred when available; when it exists, routine user copy/paste relay is prohibited. Strict-read-only/no-mutation review remains valid when the complete authority-bearing result is directly readable through another exact surface; otherwise the handoff must permit the minimum bounded final-result writeback needed to satisfy the output contract. Terminal-verdict-only output is valid only when the complete result already exists on an exact controller-readable surface. Output-content requirements and mutation/output permissions must be jointly satisfiable; no single transport is mandated.

```text
AUTHORITY_BEARING_REVIEW_RESULT_DIRECT_CONTROLLER_READABLE=REQUIRED
USER_RELAY_REQUIRED_WHEN_DIRECT_RESULT_SURFACE_AVAILABLE=NO
REVIEW_OUTPUT_AND_PERMISSION_CONTRACT_JOINTLY_SATISFIABLE=REQUIRED
PROVIDER_NATIVE_DIRECT_WRITEBACK=PREFERRED_WHEN_AVAILABLE
SINGLE_TRANSPORT_MANDATED=NO
TERMINAL_VERDICT_ONLY_REQUIRES_EXISTING_EXACT_FULL_RESULT=YES
STRICT_READ_ONLY_REVIEW_ALLOWED_WITH_ALTERNATE_EXACT_DIRECT_RESULT_SURFACE=YES
```

---

## 11. Model/executor/tool routing — general rules

Detailed model capabilities and current model names live in task-conditional Router/profile files; this constitution owns the durable routing principles.

Before every model-backed launch freeze:

```text
ROLE
EXECUTOR_SURFACE
PROVIDER
MODEL
REASONING_OR_EQUIVALENT
WEB_SEARCH_OR_TOOL_STATE
SESSION_POLICY
RESOURCE_STATE
SELECTION_REASON
```

Where exposed, record actual executor/provider/model/reasoning/tool/session identity.

Permanent rules:

```text
QUALITY_FIRST=YES
USER_MANUAL_OVERRIDE=ALWAYS_AVAILABLE
SILENT_SUBSTITUTION_OR_FALLBACK=PROHIBITED
UNAUTHORIZED_RETRY_OR_RESUME=PROHIBITED
REQUESTED_VS_ACTUAL_REQUIRED_IDENTITY_MISMATCH=ROUTER_INCIDENT
ONE_PRIMARY_WRITER_PER_SHARED_AUTHORITY_STAGE=YES
WRITER_SELF_PASS_IS_NOT_INDEPENDENT_ACCEPTANCE
ENGINEERING_CONTROL_SELF_PASS_IS_NOT_INDEPENDENT_ACCEPTANCE
FINAL_INDEPENDENT_REVIEW_REQUIRES_NEW_CHAT_CONTEXT=YES
T4_DEFAULT=NEW_INDEPENDENT_STRONGEST_APPROPRIATE_CHATGPT_WINDOW
```

Quota, points, free availability and wall-clock time are routing inputs, never authority to lower required quality.

A Router incident fails closed, prohibits automatic rerun and produces one complete Tooling Control escalation record; the user is not asked to diagnose raw model logs.

### Tool onboarding

A new engineering executor/operator/orchestrator or material tool-configuration change requires:

```text
BOUNDED_CANDIDATE
-> EXACT CONFIG / ARTIFACT IDENTITY
-> REPRESENTATIVE CAPABILITY + SAFETY EVIDENCE
-> SEPARATE INDEPENDENT REVIEW
-> USER ACTIVATION / PUBLICATION AUTHORITY
-> FIRST REAL TASK
```

Installed/free/popular does not equal accepted infrastructure. Multi-step automation must be checkpointed and human-recoverable; hidden semantic retries are prohibited.

The mature-capability no-rebuild gate and external mature-solution selection procedure apply to custom commodity tooling as well as trading infrastructure.

---

## 12. Verification architecture — development and testing as one system

Testing is not a downstream ceremony. The implementation route and verification route must be designed together from the same contracts and authority topology.

### 12.1 Production-path fidelity

A test may claim production-path coverage only when it drives the real application composition and authority seams relevant to the claim. A fake substitute that bypasses the boundary under test does not prove that boundary.

A harness, fake, adapter wrapper or test double that remains on the claimed production path must satisfy the exact seam contract it replaces or decorates, including input/output types, encoding/serialization ownership, error/exception semantics, state/resource ownership, observation phase/lifecycle state and temporal state validity. Before expensive external/provider or one-shot proof, establish that boundary fidelity at a cheaper deterministic layer when practical. A harness-caused contract mismatch invalidates the higher-level proof; it must not be promoted into an application/provider failure.

For transient or ephemeral state, evidence must be captured at the authoritative observation phase. If shutdown, teardown, reconnect cleanup or another reset legitimately clears or normalizes the state under test, preserve the proof before reset using a pre-reset immutable snapshot, monotonic event/counter, durable log/record or equivalent teardown-surviving evidence. Post-teardown normalized state must not be used to retroactively deny a pre-teardown readiness or state transition already proven unless the governing contract explicitly defines that semantics.

### 12.2 Balanced verification portfolio

Use the cheapest decisive layer outward:

```text
G0  PURE_UNIT
G1  CONTRACT_DOMAIN
G2  PROPERTY_BASED
G3  STATEFUL_SEQUENCE
G4  COMPONENT_INTEGRATION
G5  PRODUCTION_COMPOSITION
G6  CANONICAL_INCIDENT_CORPUS
G7  REALISTIC_SCALE
G8  EXACT_RELEASE_ARTIFACT_SYSTEM_TEST
G9  PUBLIC_PROVIDER_FULL_APPLICATION_REHEARSAL
G10 EXACT_HEAD_CI_AND_INDEPENDENT_T4
G11 TARGET_HOST_ENVIRONMENT_QUALIFICATION
G12 BOUNDED_REAL_MARKET_SHADOW_SOAK
```

Labels are conceptual unless a task/runbook adopts them, but responsibilities remain distinct.

Rules:

- cheap deterministic gates catch semantic defects before expensive host runs;
- target-host qualification must not be the first meaningful execution of core application semantics when a safer rehearsal exists;
- canary/Shadow supplements deterministic tests and never replaces them;
- public-provider rehearsal uses public/read-only data with no account/private API, wallet/signing or exchange write;
- exact-head CI is authoritative for the CI platform; local platform mismatches do not override it.

### 12.3 Property/stateful tests

Use property-based tests for meaningful valid domains such as zero/flat/degenerate-but-valid data, denominator boundaries, numeric extremes inside contract, arbitrary alignment/prefix phases and serialization/restore equivalence.

Use stateful testing for bounded lifecycle models such as startup/activation, reconnect, provider recovery, duplicate/idempotency, successor/epoch transition, restart/reopen/reconcile and shutdown/interruption.

Generated/shrunk failures become deterministic regression examples. Correctness must not depend on random rediscovery or one seed.

Stateful testing is not permission to build a second application inside the test suite.

### 12.4 Canonical incident corpus

For material historical incidents preserve:

```text
INCIDENT_ID
OBSERVED_HIGH_LEVEL_FAILURE
LOWEST_REPRODUCIBLE_CONTRACT
GENERALIZED_INVARIANT
PRODUCTION_COMPOSITION_SCENARIO
RELEASE_OR_HOST_RELEVANCE
FIXED_REGRESSION_ID
```

A high-stack incident should converge:

```text
INCIDENT
-> LOWEST DECISIVE REPRODUCTION
-> GENERALIZED INVARIANT / PROPERTY
-> RELEVANT PRODUCTION-COMPOSITION REGRESSION
-> INCIDENT RECORD
```

The incident corpus is evidence/history, not a second architecture authority.

### 12.5 Claim-based progressive verification

```text
CLAIM_BASED_STAGE_SUCCESS=REQUIRED
PROGRESSIVE_REPRESENTATIVE_PROOF=REQUIRED
ONE_MATERIAL_COMPLEXITY_DIMENSION_AT_A_TIME_WHEN_PRACTICAL=YES
DETERMINISTIC_AND_REAL_EXTERNAL_PROOF_COMPLEMENT=WHEN_APPLICABLE
```

Every material stage must define the exact claim it is trying to prove and the authoritative proof surface for that claim. Implementation complete, Writer PASS, local tests, CI and review are checkpoints or evidence; none is stage success unless it actually proves the frozen stage claim. For release/runtime stages, implementation completion alone never proves production-path readiness. A failed earlier claim blocks promotion to a later complexity stage.

Before adding material complexity, prove the cheapest/smallest topology that is semantically representative and useful for the current claim. When practical, increase complexity progressively and preserve failure attribution by changing one material dimension at a time, such as provider class, entity/cohort size, concurrency/scale, persistence/restart or platform/host. Do not introduce a smaller stage when it cannot provide semantically useful evidence or would create artificial delay.

A smaller topology must never claim semantics it cannot express. In particular, single-entity proof cannot prove cohort, cross-sectional, ranking or scale semantics. Promotion requires explicit PASS of the preceding claim; failure requires stopping and replanning at the failed responsibility boundary rather than continuing outward.

For externally driven or nondeterministic systems, deterministic production-composition scenarios and real external/provider rehearsals are orthogonal proofs when both claims apply. Deterministic scenarios must force required and rare semantic branches so correctness does not depend on natural occurrence. Real external/provider rehearsal proves wire, boundary, transport, freshness and provider semantics. Neither proof substitutes for the other when both claims apply.

Stage failure handling is claim-scoped:

```text
FREEZE CLAIM
-> RUN MINIMUM REPRESENTATIVE PROOF
-> IF FAIL: STOP OUTWARD PROMOTION
-> CLASSIFY FAILED RESPONSIBILITY BOUNDARY
-> REPRODUCE AT LOWEST DECISIVE LAYER
-> REPRODUCE AT RELEVANT PRODUCTION-COMPOSITION LAYER WHEN APPLICABLE
-> REPAIR ONLY THE PROVEN BOUNDARY OR REPLAN / REPLACE
-> RE-RUN THE SAME FAILED CLAIM
-> ONLY AFTER CLAIM PASS PROMOTE TO THE NEXT COMPLEXITY STAGE
```

Do not infer that a higher-scale failure proves a scale problem while cheaper lower-complexity claims that can isolate provider, semantic, lifecycle, persistence or environment responsibility remain unproven. Conversely, a lower-stage PASS proves only its frozen claim and does not imply unexpressed cohort, ranking, scale, provider or host semantics.

For every material post-stage report, record when applicable:

```text
IMPLEMENTATION_CHECKPOINT
CLAIM_UNDER_TEST
AUTHORITATIVE_PROOF_SURFACE
CLAIM_RESULT=PASS|FAIL|UNPROVEN
NEXT_PROMOTION_ALLOWED=YES|NO
FAILED_RESPONSIBILITY_BOUNDARY
RESIDUAL_UNPROVEN_CLAIMS
```

Broad `PASS`, `DONE`, `READY`, or equivalent wording must not overstate a higher-level claim that has not been proven on its authoritative proof surface. Unrun or non-representative proof remains `UNPROVEN`, never implicit PASS.

---

## 13. Verification topology and validation-environment fidelity

Verification is authoritative only when both the **command topology** and **execution environment** match the claim.

Before material validation freeze:

```text
CANONICAL_VALIDATION_COMMANDS
VALIDATION_PLATFORM_CLASS=PLATFORM_NEUTRAL|MACOS|LINUX|TARGET_HOST_SPECIFIC|OTHER
AUTHORITATIVE_VALIDATION_ENVIRONMENT
KNOWN_ENVIRONMENT_MISMATCHES
LOCAL_ENVIRONMENT_FIT
FALLBACK_VALIDATION_SURFACE
```

Permanent invariants:

```text
CANONICAL_VALIDATION_COMMAND_REUSE=REQUIRED
VERIFICATION_TOPOLOGY_MUST_MATCH_AUTHORITY_TOPOLOGY=REQUIRED
VALIDATION_ENVIRONMENT_FIDELITY=REQUIRED
PLATFORM_SENSITIVE_VALIDATION_ON_NONAUTHORITATIVE_OS=PROHIBITED
KNOWN_ENVIRONMENT_MISMATCH_REUSE=REQUIRED
NO_LOCAL_RETRY_AFTER_PROVEN_PLATFORM_MISMATCH=REQUIRED
```

If repository configuration or CI already defines a canonical command, reuse it unless a narrower command is explicitly proven semantically equivalent for the exact claim.

Do not invent a stricter/narrower local command and promote its environment-specific failure into an application blocker.

When semantics depend on `sys.platform`, filesystem permissions, Linux utilities, systemd, kernel behavior or another OS-specific capability, run the proof on the authoritative platform class. macOS cannot replace Ubuntu/Linux CI for Linux-sensitive proof; Ubuntu CI cannot replace target-host qualification for host-specific behavior.

Use the narrowest adequate fallback surface:

```text
LOCAL_PLATFORM_WHEN_FIT
-> EXISTING_GITHUB_ACTIONS_UBUNTU
-> ISOLATED_AUTHORIZED_LINUX_ENVIRONMENT_WHEN_HOST_LIKE_BEHAVIOR_IS_REQUIRED
-> CURRENT_TARGET_HOST_ONLY_FOR_TARGET_HOST_SPECIFIC_PROOF_UNDER_CURRENT_AUTHORITY
```

The production host is not a generic development sandbox.

### 13.1 Authoritative remote/provider-native execution preference

The fallback ordering above is a fidelity ladder, not a rule that the user's workstation must be tried first. When an accepted GitHub/provider-native remote surface can execute the bounded task or proof with **equal or higher claim fidelity**, exact source/head identity, reproducible evidence and lower human relay/rework, prefer that remote surface over user-operated local emulation.

```text
AUTHORITATIVE_REMOTE_EXECUTION_SURFACE_PREFERRED_WHEN_EQUAL_OR_HIGHER_FIDELITY=YES
USER_LOCAL_WORKSTATION_NOT_DEFAULT_FOR_CI_OR_LINUX_PROOF=YES
REMOTE_EXECUTION_MUST_PRESERVE_FROZEN_EXECUTOR_MODEL_TOOL_AND_AUTHORITY=YES
REMOTE_EXECUTION_CREDENTIAL_OR_PRIVATE_API_AUTHORITY_MUST_BE_EXPLICIT=YES
```

Apply this claim-by-claim:

- Linux/CI-specific proof should normally run on the accepted exact-head GitHub Actions/Linux surface rather than on macOS or a user-maintained local Linux emulation.
- Deterministic GitHub control-plane work such as exact branch/PR/head/CI/artifact state should be carried directly through GitHub when the connector/workflow already has the required authority, rather than requiring the user to relay or reproduce it locally.
- A cheap faithful local unit/contract check may still run before CI when it is already available and reduces total burden without meaningful user relay; remote-first does not mean replacing every deterministic unit test with CI.
- Local execution remains appropriate when the claim is irreducibly local, depends on an already-authorized local authenticated session/tool, requires local-only files/hardware, or when no accepted remote surface can preserve the frozen executor/capability contract.
- Target-host-specific claims still require the target host; GitHub does not become a substitute for a different authoritative environment merely because it is remote.

Remote preference never grants new secrets or permissions. If the remote path requires a provider API key, GitHub secret, private API, credential, signing capability or broader token permission not already authorized for the bounded stage, stop at that exact authority boundary. Do not silently create, transfer, infer or reuse credential authority merely to avoid a local step.

A canonical exact GitHub ref/head already proven through the control plane must not be redundantly transformed into a requirement that the user's local repository already contains the same Git object. If a genuinely local Writer is still required, acquire and verify the exact canonical remote ref in an isolated workspace through the already-authorized Git transport; local object preexistence is not a substitute safety invariant.

---

### 13.2 Deterministic / GitHub-first execution economy

Use the cheapest sufficient **authoritative** execution surface. Cost never overrides correctness, fidelity or safety, but a scarce model executor is not used for deterministic work merely because quota is available.

Default order:

```text
AUTHORITATIVE_GITHUB_CONNECTOR / GITHUB_ACTIONS / PROVIDER_NATIVE / DETERMINISTIC_TOOL
-> ENGINEERING_CONTROL DIRECT READ/WRITE WHEN NO CODING AGENT IS NEEDED
-> CODEX WHEN A SEMANTIC CODING WRITER IS REQUIRED AND THE USER'S CODEX ROUTE IS AVAILABLE
-> ACCEPTED NON-CODEX SEMANTIC WRITER ONLY WITH EXPLICIT BOUNDED USER SELECTION/FALLBACK AUTHORITY
```

Permanent rules:

```text
HEALTHY_CODEX_QUOTA_ALONE_DOES_NOT_CREATE_WORK=YES
REQUIRED_SEMANTIC_CODING_PLUS_USABLE_CODEX=>CODEX_DEFAULT=YES
CODEX_QUOTA_FAILURE_DOES_NOT_AUTHORIZE_EXECUTOR_FALLBACK=YES
CODEX_FOR_GITHUB_STATUS_DIFF_ARTIFACT_CI_EVIDENCE=NO_BY_DEFAULT
CODEX_FOR_FULL_REPOSITORY_TEST_SUITE=NO_BY_DEFAULT
CODEX_FOR_DUPLICATE_CONTROL_PLANE_DISCOVERY=NO_BY_DEFAULT
GITHUB_ACTIONS_DEFAULT_FOR_LOCKED_FULL_SUITE_AND_LINUX_CI=YES
USER_MAC_FULL_SUITE_DEFAULT=NO_WHEN_GITHUB_CI_IS_EQUAL_OR_HIGHER_FIDELITY
FOCUSED_LOCAL_TESTS_DURING_SEMANTIC_EDIT=ALLOWED_WHEN_CHEAP_AND_FIT
```

A model-backed Writer may run the smallest decisive focused tests needed to iterate on its semantic change. Once an exact semantic checkpoint exists, deterministic full-suite, exact-lock, Linux, status, diff, artifact and CI mechanics move to GitHub/Engineering Control unless the claim is genuinely local.

Reuse an existing accepted canonical GitHub workflow when one already proves the claim. Do not create a new CI workflow merely to avoid a cheap platform-neutral focused local check; new workflow surface requires its own engineering value and governance fit.

No per-task prose essay is required to justify not using Codex. Router classification applies this policy mechanically.

## 14. Exact release, staged artifact and deployment topology

Keep strict separation:

```text
SOURCE + LOCKS
-> BUILD / EXACT RELEASE ARTIFACT
-> STAGED EXACT-ARTIFACT SYSTEM TEST
-> PUBLIC-PROVIDER FULL-APPLICATION REHEARSAL
-> PUBLICATION / EXACT-HEAD CI / INDEPENDENT T4
-> EXACT-RELEASE TARGET-HOST QUALIFICATION
-> BOUNDED REAL-MARKET SHADOW SOAK
-> SEPARATELY AUTHORIZED FIRST LIVE
```

Release identity binds the exact source tree plus every release-sensitive surface required by the active deployment contract. Prefer one canonical release-identity source over duplicated literals.

### Manifest creation vs staged verification

When Git is the candidate identity authority, manifest creation may require a clean exact Git HEAD.

Verification of an already-created staged artifact must match the actual deployment transport. For a non-Git exact-artifact/SFTP deployment:

```text
STAGED_ARTIFACT_GIT_CHECKOUT_REQUIRED=NO
RETAINED_CANONICAL_MANIFEST_REQUIRED=YES
EXPLICIT_EXPECTED_RELEASE_SHA_REQUIRED=YES
MANIFEST_SCHEMA_MATCH=REQUIRED
EMBEDDED_RELEASE_SHA_MATCH=REQUIRED
SELECTED_PATH_SET_MATCH=REQUIRED
HASH_AND_SIZE_MATCH=REQUIRED
MISSING_OR_MUTATED_SELECTED_CONTENT=FAIL_CLOSED
```

Do not infer release identity from a non-Git staged filesystem and do not turn the verifier into a second deployment/package authority.

Persisted-state snapshots, checkpoint copies and manifests must follow the owning component's durability semantics. Filename suffixes, temporary-file appearance or convenience heuristics do not define canonical state. If an engine splits committed state across multiple files, the snapshot/copy contract must preserve that durability set or use an engine-supported consistent snapshot. Never blanket-exclude a persistence file merely because its name appears auxiliary.

---

## 15. Generated commands and operator efficiency

Human-operated engineering commands are part of the engineering system and must be engineered with the same care as application code.

### 15.1 One-paste default

When user-operated macOS engineering work is genuinely required by the selected authoritative route, default to one contiguous ordinary-Terminal paste when safe. Do not require the user to manually reconstruct paths, prompts, hashes or stage routing when they can be encoded deterministically.

Do not route work to the user's workstation merely because a local command can be generated. Apply §13.1 first: an accepted remote/provider-native surface with equal or higher fidelity and lower relay is preferred when it does not require unauthorized credentials or weaken the frozen executor/claim contract.

An extra human step is allowed only when technically unavoidable or required by a real authority/security boundary.

Long/critical/model-launch/one-shot workflows default to file-backed scripts with a short hash-verify/execute launcher rather than fragile giant interactive heredocs.

### 15.1A Known-incident non-regression and transport monotonicity

Before delivering any nontrivial human-executed command or harness, compare its planned failure surface against the canonical generated-command incident catalogue and relevant prior incidents.

```text
KNOWN_COMMAND_INCIDENT_CLASSES_REVIEWED=YES
KNOWN_INCIDENT_NONREGRESSION_GATE=PASS
```

A known avoidable failure class may not be reintroduced merely because the exact command text, encoding or wrapper differs. Repeating a known class without a specific preventive control is a pre-delivery reliability failure.

File-backed execution must **reduce** operator-input complexity. It is not sufficient to place a long script into a file by embedding the same payload as a giant Base64/hex/escaped literal, giant quoted `shell -c` string, long nested heredoc/subshell or equivalent fragile representation in the same interactive paste. The operator-visible bootstrap must be materially simpler than the payload and parse-complete on its own. If the current surface cannot satisfy that, use a robust transfer/artifact surface, an accepted repository-owned launcher, or an explicitly safe phase split.

Interactive shell behavior that affects parsing cannot be assumed from user startup state. Comments, aliases, shell options, history expansion and emulation modes must either be explicitly established or avoided. A command that parses correctly only under an unproven interactive option does not pass the reliability gate.

### 15.2 Target environment is evidence

Before delivery establish the actual OS, shell, CLI/tool versions, privilege model, filesystem/deployment shape and evidence-return surface when those facts affect correctness.

Do not assume GNU tools on macOS, Git checkout on an artifact-only target, or a CLI argument meaning merely because a flag exists.

### 15.3 Exact CLI invocation contract proof

For a versioned material CLI freeze as applicable:

```text
CLI_NAME / VERSION / SUBCOMMAND
POSITIONAL_ARGUMENT_SEMANTICS
FILE_ARGUMENT_SEMANTICS
STDIN_SEMANTICS
WORKING_DIRECTORY_SEMANTICS
MODEL_PROVIDER_ID_SEMANTICS
OUTPUT_MODE_SEMANTICS
EXACT_INVOCATION_SHAPE
```

`--help` proving flag existence is insufficient when argument semantics are ambiguous. Prefer provider-native documented invocation plus installed-version evidence.

Model-backed executors must not share stdin with the shell/heredoc program that launched them. Prompt/launcher transport must be explicitly separated.

### 15.4 No false SAFE_STOP

Every fail-closed command gate maps to a real authority, identity, safety, state or correctness invariant.

Before a semantic Writer launch, classify each proposed pre-semantic gate as either a true semantic prerequisite or a later publication/egress prerequisite:

```text
SEMANTIC_START_DEPENDENCY_MINIMIZATION=REQUIRED
SEMANTIC_READINESS_NE_PUBLICATION_READINESS=YES
PRE_SEMANTIC_GATE_REQUIRES_DISTINCT_REAL_INVARIANT=YES
```

GitHub CLI authentication, push permission, PR creation, publication dry-runs, result-comment egress and other publication mechanics must not block semantic start unless the semantic stage genuinely requires that exact capability to obtain/verify its source or satisfy another real pre-mutation invariant. When exact canonical identity is already established through the control plane and an exact local/source artifact is available, redundant lower-reliability GitHub network/auth probes are prohibited before semantic start.

Prohibited false exactness includes:

- implementation-shape checks unrelated to the real invariant;
- redundant less-reliable network proof after fresh authoritative control-plane identity already exists without added safety value;
- treating missing convenience tooling as safety failure when a validated alternative provides the same proof;
- interpreting an allowlist as requiring every permitted path to change;
- self-generated expected hashes/identities that were not themselves derived or independently verified from the exact object they gate.

Unless the semantic contract explicitly requires specific paths to change:

```text
CHANGED_PATHS ⊆ ALLOWLIST
```

is the scope proof.

### 15.5 Checkpoint before non-decisive tails

After a semantic Writer completes and exact mutation scope/identity is provable, preserve the evidence needed to retain that semantic attempt **before** environment-sensitive lint/type/evidence-packaging tails.

A later wrapper, network, platform or evidence failure does not erase a completed Writer delta and does not authorize a semantic rerun.

### 15.6 Command repair budget

```text
INITIAL_GENERATED_COMMAND
-> AT MOST ONE BOUNDED CORRECTION
-> SECOND AVOIDABLE COMMAND/WRAPPER DEFECT IN SAME STAGE
   => TERMINATE_CURRENT_LAUNCHER_FAMILY
   => COMMAND_RELIABILITY_HOLISTIC_REGENERATION
```

This state is derived from the recorded failure lineage, not reset by renaming a ZIP/script or changing wrapper syntax. Once the launcher family is terminated, another incremental bounded correction is prohibited.

Holistic regeneration re-reads the actual environment, canonical workflow and prior failure classes, proves non-regression against the incident catalogue, removes stale assumptions, reclassifies semantic-start versus publication dependencies, reconsiders whether the local launcher is needed at all, and regenerates one complete route. Do not build CONT1/CONT2/CONT3 or R3/R4/R5 patch chains.

### 15.7 Evidence egress

Evidence return is part of workflow acceptance. Prove the intended output path/permissions/transfer surface before expensive work when materially uncertain; after generation prove exact file/hash/size/readability and actual client visibility/download when the workflow requires manual transfer.

If evidence egress fails after the semantic action, repair only the evidence path; never repeat the semantic action merely to recreate a downloadable file.

---

## 16. Failure classification, checkpoint/resume and incident learning

Before issuing another command or repair after a failure classify:

```text
FAILURE_CLASS=
SEMANTIC_ACTION_STARTED=YES|NO
SEMANTIC_ACTION_COMPLETED=YES|NO
MUTATION_STATE=
SAFE_STATE_RESTORED=
LAST_ACCEPTED_CHECKPOINT=
RESUME_FROM=
RERUN_SEMANTIC_ACTION=YES|NO
```

Useful failure classes include environment-capability mismatch, wrong validation environment, CLI/shell transport defect, false gate, artifact identity failure, deployment mechanic failure, wrapper/harness failure, persisted-state copy/identity failure, application/strategy failure, evidence packaging/egress failure and authority/safety block.

Resume from the latest exact accepted checkpoint. Hidden retries and silent reruns are prohibited.

Material incidents must become reusable learning:

```text
WHAT_HAPPENED
ROOT_CAUSE / CONTRIBUTING_CAUSES
WHY_EXISTING_GATES_MISSED_IT
LOWEST_DECISIVE_REPRODUCTION
GENERALIZED_INVARIANT
PREVENTIVE_TEST / PROCESS CHANGE
OWNER / FOLLOW-UP
```

Historical incidents are rationale and regression evidence, not competing active rules. Reusable lessons are absorbed into this constitution or a narrow procedure rather than relying on chat memory.

When a new incident matches an existing durable failure class, record it as a **known-class recurrence** and treat the recurrence as evidence that the preventive gate was not operationally enforced. Do not relabel a repeated class as a novel edge case merely because its wrapper, encoding or exact command differs.

---

## 17. Review, repair budget and convergence

Writer self-PASS is execution evidence only.

Independent Review inspects the actual exact object:

- exact GitHub head; or
- integrity-bound dirty-worktree review packet; or
- exact delta against an independently accepted fingerprint.

Authority-bearing independent review requires a **new ChatGPT conversation/window** that did not control or implement the candidate stage. The Engineering Control conversation may perform self-check/readiness work only; its PASS cannot become independent acceptance.

The reviewer receives a compact Review Manifest containing:

```text
REVIEW_TARGET / EXACT BASE-HEAD-TREE
EXACT_CHANGED_SCOPE / DIFF
FROZEN_ACCEPTANCE_CRITERIA
REQUIRED_SAFETY_BOUNDARIES
DECISIVE_CI / ARTIFACT / SOURCE / UPSTREAM LOCATORS
EXPLICITLY_UNTRUSTED_PRIOR_CONCLUSIONS
OUTPUT / AUTHORITY CONTRACT
```

Default reviewer loading order is:

```text
EXACT IDENTITY
-> EXACT DIFF / CHANGED SURFACES
-> ACCEPTANCE CONTRACT
-> DECISIVE CI / ARTIFACT EVIDENCE
-> NECESSARY UPSTREAM
-> TARGETED CANONICAL HISTORY ONLY IF A CONCRETE QUESTION REMAINS
```

Full Issue/PR history and full governance corpus reload are prohibited by default. This is a context-economy rule, not a relaxation of review quality: any missing material fact triggers targeted retrieval and unresolved uncertainty prohibits PASS.

Once a baseline is independently accepted, default to delta review:

```text
ACCEPTED_BASELINE
+ EXACT_NEW_DELTA
+ TARGETED_REGRESSION / BYPASS CHECKS
```

Do not repeatedly rereview unchanged accepted thousands of lines without a concrete dependency/regression reason.

Default application/design repair budget:

```text
INITIAL IMPLEMENTATION
+ AT MOST ONE NORMAL CONSOLIDATED REPAIR
+ AT MOST ONE EXPLICITLY AUTHORIZED EXCEPTIONAL NARROW REPAIR
```

No routine Repair 3/4/5. New root cause, expanded authority/layer boundary or exhausted budget triggers `HOLISTIC_CONVERGENCE_GATE` and route-level reanalysis. Sunk cost never authorizes another patch.

If the failed responsibility boundary is project-owned commodity infrastructure, reopening the mature-solution selection gate precedes another semantic repair whenever the expiry triggers in §6.8 apply.

---

## 18. Repository, CI and publication discipline

Repository safety:

- no direct commit to `main` for normal engineering work;
- no force-push/shared-history rewrite after review begins;
- one bounded issue/branch/worktree mutation scope unless an explicitly independent disjoint stage is frozen;
- no secrets, credentials, wallets, raw private/account data, production DB/log/cache or real account identifiers committed;
- simulated/default market/account data must never be represented as real evidence.

Acceptance/release identity uses exact base/head/changed paths/artifact/CI run where applicable. CI from another SHA is stale evidence.

GitHub CI verifies exact remote content and the CI platform. It should not replace a faithful cheap deterministic unit/contract gate that is already available with negligible relay, but it **is** preferred over user-operated local emulation for Linux/CI-specific proof when GitHub is the authoritative environment. Do not make the user's workstation reproduce canonical GitHub identity or Linux-specific evidence merely to satisfy a redundant preflight.

Publication order:

```text
EXACT CANDIDATE
-> APPLICABLE LOCAL/SAFE VALIDATION
-> DRAFT PR
-> EXACT-HEAD CI
-> INDEPENDENT REVIEW
-> USER MARK-READY AUTHORITY
-> USER MERGE AUTHORITY
-> POST-MERGE CI / LIVE-MAIN VERIFICATION
```

Mark Ready and merge remain distinct user-retained gates even after technical PASS.

---

## 19. Deployment / runtime / trading authority boundaries

No research, governance, Writer, test, CI, Review or implementation result implicitly authorizes:

```text
MARK_READY
MERGE
BRANCH_DELETION
DEPLOYMENT
PRODUCTION_HOST_OR_CLOUD_MUTATION
SERVICE_START_RESTART_ENABLE_REBOOT
CREDENTIAL_OR_PRIVATE_API_ACCESS
REAL_NOTIFICATION_WHEN_SEPARATELY_GATED
WALLET / SIGNING / NONCE
EXCHANGE_WRITE
ORDER_SUBMISSION_OR_CANCELLATION
AUTONOMOUS_TRADING
```

These require explicit current user authority and cannot be inferred from a previous stage.

Uncertain, stale, gapped, disconnected or conflicted mandatory state means no new risk.

---

## 20. Specialized contracts and progressive loading

Do not make every participant read every tool profile.

After the universal preflight, load only the narrow contract required by the selected route, for example:

- `PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md` for material direction-setting research;
- `EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md` for material external-solution selection/adoption/re-evaluation or a proposed custom commodity implementation;
- `ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md` for model-backed routing;
- Codex/OpenCode/Trae/DeepSeek profiles only when that executor/model is selected;
- `ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md` for new/materially changed tools;
- Local Task Runner profiles only when Runner is selected and compatible;
- Hermes contracts only when Hermes is selected;
- FinalShell target-host workflow only for target-host deployment/qualification;
- current Product / Strategy / Operations / Security authority for the bounded task.

Specialized files contain implementation details and fast-changing profiles. Their general engineering principles are owned here so model/tool/framework churn does not force a new project constitution.

---

## 21. Governance maintenance and decision history

When a new durable lesson appears:

1. determine whether it is project-wide or task-specific;
2. if project-wide, update this single constitution rather than create another overlapping rulebook;
3. preserve detailed incident/decision rationale in Issue/ADR-like history or a narrow procedure;
4. mark superseded decisions explicitly instead of silently editing history into ambiguity;
5. independently review material governance changes before merge;
6. keep `AGENTS.md` and `PROJECT_RULES_INDEX.md` compact and accurate.

A decision record should preserve context, decision and consequences. Accepted historical decisions remain useful as history even when superseded, but successor windows begin from the current canonical rule, not the entire history stack.

External mature-solution decisions are versioned decisions. The specialized selection rule defines security, maintenance, license, product-stage, integration-burden and stronger-alternative triggers that reopen selection rather than letting stale framework decisions become permanent architecture authority.

---

## 22. Frozen concise invariants

```text
GITHUB_CANONICAL_SOURCE=YES
ONE_PROJECT_WIDE_ENGINEERING_CONSTITUTION=YES
MATERIAL_WRITER_REQUIRES_PROJECT_RULESET_PREFLIGHT_PASS=YES
MATERIAL_WRITER_REQUIRES_ENGINEERING_PREFLIGHT_PASS=YES
INDEPENDENT_ANALYSIS_BEFORE_EXTERNAL_CONCLUSIONS=YES
EXTERNAL_MATURE_EVIDENCE_FOR_MATERIAL_DIRECTION_SETTING=YES
SYNTHESIS_BEFORE_ROUTE_FREEZE=YES
RESEARCH_FRONTIER_REQUIRES_INVESTMENT_DISPOSITION=YES
DATA_BLOCKED_FRONTIER_DOES_NOT_AUTO_AUTHORIZE_ENGINEERING=YES
RESEARCH_INVESTMENT_BY_EXPECTED_DECISION_VALUE_MINUS_TOTAL_BURDEN=YES
SAFETY_CORRECTNESS_CAUSAL_BLOCKERS_OVERRIDE_RESEARCH_ROI_DEFER=YES
RESEARCH_INVESTMENT_DISPOSITIONS=ACQUIRE_BEFORE_NEXT_GATE|CAPTURE_CHEAP_OPTIONALITY|PROCEED_WITH_CURRENT_BEST_AND_DEFER|PARK_OR_REJECT
SIMPLEST_EFFECTIVE_VALIDATED_STRATEGY_PREFERRED=YES
STRATEGY_DISCRETIONARY_ECONOMIC_COMPLEXITY_REQUIRES_MATERIAL_INCREMENTAL_OOS_OR_FORWARD_VALUE=YES
HISTORICAL_ADAPTIVITY_AND_TRIAL_COUNT_MUST_BE_RECORDED=YES
REPEATED_PRE_FORWARD_RESEARCH_EXPANSION_REQUIRES_FRESH_INVESTMENT_GATE=YES
FREEZE_STRATEGY_VERSION_BEFORE_FORWARD_EVIDENCE=YES
ANY_MATERIAL_STRATEGY_SEMANTIC_OR_EVIDENCE_AFFECTING_CHANGE_RESETS_FORWARD_EVIDENCE_CLOCK=YES
NO_RETROACTIVE_FORWARD_EVIDENCE_CREDIT_AFTER_MATERIAL_VERSION_CHANGE=YES
PRE_WRITER_GO_NO_GO_EXPERIMENT=WHEN_CHEAP_SAFE_AND_DECISIVE
MATURE_SOLUTION_FIRST=YES
MATURE_CAPABILITY_NO_REBUILD_GATE=REQUIRED
CAPABILITY_CLASSIFICATION_BEFORE_COMMODITY_WRITER=REQUIRED
STRATEGY_DECISION_ENGINE_PROJECT_OWNED=YES
TRADING_INFRASTRUCTURE_ENGINE_MATURE_EXTERNAL_OWNER_BY_DEFAULT=YES
FITTING_MATURE_COMMODITY_CAPABILITY_BLOCKS_CUSTOM_REBUILD=YES
SECOND_PROJECT_OWNED_COMMODITY_IMPLEMENTATION=PROHIBITED_WHEN_FITTING_MATURE_OWNER_EXISTS
ENGINEERING_CONTROL_OR_WRITER_SELF_AUTHORIZED_CUSTOM_COMMODITY_BUILD=PROHIBITED
CUSTOM_COMMODITY_EXCEPTION_REQUIRES_EXPLICIT_CURRENT_USER_AUTHORITY=YES
STAGE_0_NO_PRODUCT_CODE_MATURE_SOLUTION_AUDIT=REQUIRED_WHEN_APPLICABLE
ONE_BLOCKER_TINY_SPIKE_ONLY=YES_WHEN_EXTERNAL_FEASIBILITY_REMAINS_UNRESOLVED
MULTIPLE_FULL_PROTOTYPES_FOR_MATURE_SELECTION=DISFAVORED
INVASIVE_MATURE_FRAMEWORK_FORK=PROHIBITED_BY_DEFAULT
MODULAR_MATURE_COMPOSITION=ALLOWED_WITH_ONE_AUTHORITY_OWNER_PER_RESPONSIBILITY
OVERLAPPING_DURABLE_STATE_OMS_POSITION_RISK_AUTHORITY=PROHIBITED
LEGACY_KEEP_CUSTOM_DECISION_EXPIRY_TRIGGERS=REQUIRED
NO_NEW_DEPENDENCY_IS_NOT_SIMPLICITY_PASS=YES
SIMPLICITY_BY_TOTAL_ENGINEERING_BURDEN=YES
GLOBAL_ROOT_CAUSE_BEFORE_LOCAL_PATCH_LOOPS=YES
CROSS_LAYER_CONTRACT_CLOSURE=REQUIRED
ADMITTED_INPUT_TOTALITY=REQUIRED
STABLE_NARROW_SEAMS_AND_CONTINUITY=REQUIRED
PROVIDER_SCALE_FRESHNESS_GATE=WHEN_APPLICABLE
ONE_PRIMARY_WRITER_PER_SHARED_AUTHORITY_STAGE=YES
COMPLETE_TASK_PACKET_BEFORE_EXECUTION=YES
LOSSLESS_HANDOFF=REQUIRED_FOR_AUTHORITY_BEARING_TASKS
INTERMEDIARY_PARAPHRASE_AS_DOWNSTREAM_AUTHORITY=PROHIBITED
RAW_EVIDENCE_OVERRIDES_INTERMEDIARY_SUMMARY=YES
USER_AS_ROUTINE_MESSAGE_BUS=PROHIBITED
ACTIVE_TASK_OWNERSHIP_UNTIL_TERMINAL_DISPOSITION=YES
NO_SILENT_MODEL_EXECUTOR_FALLBACK=YES
WRITER_PASS_NE_INDEPENDENT_ACCEPTANCE=YES
CLAIM_BASED_STAGE_SUCCESS=REQUIRED
PROGRESSIVE_REPRESENTATIVE_PROOF=REQUIRED
ONE_MATERIAL_COMPLEXITY_DIMENSION_AT_A_TIME_WHEN_PRACTICAL=YES
DETERMINISTIC_AND_REAL_EXTERNAL_PROOF_COMPLEMENT=WHEN_APPLICABLE
FAILED_STAGE_CLAIM_MUST_BE_RERUN_BEFORE_PROMOTION=YES
BROAD_PASS_CANNOT_OVERSTATE_UNPROVEN_CLAIMS=YES
PRODUCTION_PATH_FIDELITY=REQUIRED
HARNESS_BOUNDARY_CONTRACT_FIDELITY=REQUIRED
BALANCED_G0_TO_G12_VERIFICATION=REQUIRED_WHEN_APPLICABLE
INCIDENT_TO_INVARIANT_CONVERGENCE=REQUIRED
VERIFICATION_TOPOLOGY_MUST_MATCH_AUTHORITY_TOPOLOGY=REQUIRED
CANONICAL_VALIDATION_COMMAND_REUSE=REQUIRED
VALIDATION_ENVIRONMENT_FIDELITY=REQUIRED
PLATFORM_SENSITIVE_VALIDATION_ON_WRONG_OS=PROHIBITED
KNOWN_ENVIRONMENT_MISMATCH_REUSE=REQUIRED
AUTHORITATIVE_REMOTE_EXECUTION_PREFERRED_WHEN_EQUAL_OR_HIGHER_FIDELITY=YES
USER_LOCAL_WORKSTATION_NOT_DEFAULT_FOR_CI_OR_LINUX_PROOF=YES
REMOTE_EXECUTION_PRESERVES_FROZEN_EXECUTOR_MODEL_TOOL_AUTHORITY=REQUIRED
REMOTE_EXECUTION_CREDENTIAL_AUTHORITY_MUST_BE_EXPLICIT=YES
CANONICAL_REMOTE_REF_MUST_NOT_REQUIRE_REDUNDANT_LOCAL_OBJECT_PREEXISTENCE=YES
EXACT_RELEASE_STAGED_ARTIFACT_SEPARATION=REQUIRED
PERSISTED_STATE_COPY_MUST_FOLLOW_COMPONENT_DURABILITY_SEMANTICS=YES
MACOS_OPERATOR_ONE_PASTE_DEFAULT=YES_WHEN_LOCAL_OPERATOR_ROUTE_IS_GENUINELY_REQUIRED
KNOWN_COMMAND_INCIDENT_NONREGRESSION_GATE=REQUIRED
OPERATOR_TRANSPORT_MUST_REDUCE_COMPLEXITY_NOT_REENCODE_IT=YES
INTERACTIVE_SHELL_PARSE_ASSUMPTIONS_MUST_BE_PROVEN_OR_AVOIDED=YES
CLI_INVOCATION_CONTRACT_PROOF=REQUIRED_FOR_MATERIAL_VERSIONED_CLI
MODEL_EXECUTOR_AND_OUTER_LAUNCHER_STDIN_SHARING=PROHIBITED
FALSE_SAFE_STOP_GATE=PROHIBITED
ALLOWLIST_MEANS_CHANGED_PATHS_SUBSET_UNLESS_SEMANTIC_MINIMUM_EXPLICIT=YES
POST_WRITER_EVIDENCE_CHECKPOINT_BEFORE_NONDECISIVE_TAIL=REQUIRED
NO_SEMANTIC_RERUN_AFTER_PRESERVED_COMPLETED_CHECKPOINT=YES
GENERATED_COMMAND_SECOND_AVOIDABLE_DEFECT_TRIGGERS_HOLISTIC_REGENERATION=YES
APPLICATION_NORMAL_REPAIR_LIMIT=1
APPLICATION_EXCEPTIONAL_REPAIR_LIMIT=1
REPAIR_3_PLUS_SAME_ROUTE=PROHIBITED
EXACT_ARTIFACT_AND_EXACT_HEAD_REVIEW=REQUIRED_WHEN_APPLICABLE
T4_FINAL_REVIEW_INDEPENDENT=YES
MARK_READY_MERGE_DEPLOY_RUNTIME_CREDENTIAL_ACCOUNT_EXCHANGE=SEPARATE_CURRENT_USER_AUTHORITY
```

---

## 23. Supersession intent

On independent acceptance and merge of this V2 standard:

- `UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md` becomes historical/superseded;
- the project-wide normative portions of `PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md` are incorporated here; that file remains only a task-conditional research procedure/reference;
- `EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md` remains a task-conditional procedure implementing the mature-solution rules owned here, not a second project-wide constitution;
- the project-wide normative portions of `GENERATED_COMMAND_RELIABILITY_AND_OPERATOR_EFFICIENCY_RULE_V1_2026-08-30.md` are incorporated here; that file remains only a task-conditional operator procedure/incident catalogue;
- the Issue #139 holistic verification methodology is incorporated here and does not require a separate competing governance constitution;
- `MANDATORY_ENGINEERING_PREFLIGHT_AND_CONVERGENCE_GATE_V1_2026-08-17.md` remains a compact executable checklist derived from V2, not a separate source of engineering policy.

Future governance changes should edit V2 or a genuinely narrow specialized contract instead of creating another overlapping project-wide rulebook.
