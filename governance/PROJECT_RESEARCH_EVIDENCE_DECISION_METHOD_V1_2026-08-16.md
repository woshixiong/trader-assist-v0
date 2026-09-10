# Trader Assist / Trade OS — Research, Evidence and Decision Procedure V1

**Status:** TASK-CONDITIONAL PROCEDURE CANDIDATE  
**Effective date:** 2026-08-16  
**Last material amendment candidate:** 2026-09-10  
**Normative owner:** `UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md`

This file is a reusable **procedure and output template** for material direction-setting research. It does not create a second project-wide engineering authority. Unified V2 governs if there is any conflict.

Use this procedure when a task materially sets or changes product, strategy, engineering route, architecture, provider, framework, tool, migration, optimization or other direction on which meaningful engineering time/risk will depend.

Do not require it for purely mechanical execution of an already-frozen plan. If a mechanical task exposes a new material decision, apply this procedure to that decision.

When the material decision selects, rejects, composes, customizes, adopts, upgrades or re-evaluates an external mature solution, or proposes project-owned commodity infrastructure, also use:

- `governance/EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md`

That specialized procedure defines the mandatory candidate/P0/evidence/total-burden/Stage-0/Tiny-Spike path. This research procedure does not replace it.

---

## 1. Mandatory three-stage sequence

```text
PHASE 1 — INDEPENDENT ANALYSIS
PHASE 2 — EXTERNAL / MATURE EVIDENCE
PHASE 3 — SYNTHESIS / DECISION
```

Do not reverse or collapse the order.

### Phase 1 — Independent analysis

Before consulting external conclusions, record a short pre-research position:

```text
PROBLEM=
USER_OR_PROJECT_OBJECTIVE=
KNOWN_FACTS=
ASSUMPTIONS=
UNKNOWNS=
DECISION_CRITERIA=
CAUSAL_OR_MECHANICAL_MODEL=
CANDIDATE_ROUTES=
EXPECTED_BENEFITS=
EXPECTED_FAILURE_MODES=
EVIDENCE_THAT_WOULD_CONFIRM_OR_FALSIFY=
```

Independent reasoning still uses live project facts and GitHub state; it simply forms the analytical position before external recommended solutions anchor it.

For architecture/framework/provider/tool selection, Phase 1 should freeze the required responsibility boundary, current bounded need, next expected product stage and P0 requirements before candidate scores or preferences are known.

### Phase 2 — External evidence

Prioritize:

1. official specifications, provider docs and first-party source repositories;
2. primary research, inspectable datasets and reproducible benchmarks;
3. mature maintained frameworks and credible production cases/postmortems;
4. high-quality independent technical analysis;
5. community discussion only as supplementary evidence.

Research competing approaches and disconfirming evidence, not only support for the preliminary view.

Check freshness where it matters. Distinguish measured evidence from marketing/opinion. Evaluate mature solutions against actual Trader Assist / Trade OS constraints rather than adopting them by popularity.

Before recommending custom commodity engineering, explicitly check accepted project capability, provider-native, standard/official, mature maintained full-framework, mature modular-component, thin-adapter and mature-composition alternatives.

For a material external-solution choice, evidence confidence and candidate selection must follow the external mature-solution selection rule. Popularity, star count, familiarity or marketing cannot substitute for functional/safety/operational evidence.

### Phase 3 — Synthesis / decision

Record:

```text
WHAT_EXTERNAL_EVIDENCE_CONFIRMS=
WHAT_IT_MODIFIES=
WHAT_IT_REJECTS=
RESIDUAL_UNCERTAINTY=
REJECTED_ROUTES_AND_WHY=
SELECTED_ROUTE=
WHY_IT_FITS_PROJECT_CONSTRAINTS=
VALIDATION_EXPERIMENT_OR_REHEARSAL_REQUIRED=
```

Final route status should be one of:

```text
INDEPENDENTLY_DERIVED_EXTERNALLY_CONFIRMED
INDEPENDENTLY_DERIVED_EXTERNALLY_MODIFIED
PRELIMINARY_ROUTE_REJECTED_BY_EVIDENCE
UNRESOLVED_REQUIRES_EXPERIMENT_OR_MORE_EVIDENCE
```

Research must converge. Do not keep searching indefinitely around the same failing design.

When the external-solution rule applies, Phase 3 must preserve its typed Stage 0 disposition (`SELECT_MATURE_ROUTE`, `SELECT_MODULAR_COMPOSITION`, `ONE_BLOCKER_FEASIBILITY_SPIKE`, `UNRESOLVED_TRADEOFF`, `REJECT_CANDIDATE`, `NO_FITTING_MATURE_ROUTE`, or `SAFE_STOP`) rather than paraphrasing an unresolved comparison into an implementation recommendation.

---

## 1A. Research frontier / value-of-information / complexity gate

### 1A.1 When this gate applies

Apply this gate whenever the research team says, explicitly or effectively:

```text
CURRENT_EVIDENCE_EXHAUSTED=YES
AND FURTHER_PROGRESS_REQUIRES=
  NEW_DATA
  | NEW_DATA_RETENTION
  | NEW_PROVIDER_OR_INFRASTRUCTURE_WORK
  | MATERIAL_NEW_EXPERIMENT
  | MORE_ADAPTIVE_SEARCH_ON_EXISTING_HISTORY
  | NEW_INDEPENDENT_OOS_OR_FORWARD_EVIDENCE
```

A `DATA_BLOCKED_FRONTIER` is a research state, not an engineering order. Do not translate “more data could help” into “build the data path.”

### 1A.2 Required decision record

Before any new material research/data Writer is dispatched, record:

```text
RESEARCH_FRONTIER_REACHED=YES|NO
CURRENT_BEST_CANDIDATE=
CURRENT_CANDIDATE_READINESS=
MISSING_EVIDENCE_OR_DATA=
DECISION_THAT_THE_NEW_INFORMATION_COULD_CHANGE=
DECISION_CRITICALITY=HARD_BLOCKER|MATERIAL_OPTIMIZATION|OPTIONAL
EXPECTED_DECISION_IMPACT=LOW|MEDIUM|HIGH|BOUNDED_ESTIMATE
EXPECTED_UNCERTAINTY_REDUCTION=LOW|MEDIUM|HIGH|BOUNDED_ESTIMATE
TOTAL_RESEARCH_BURDEN=
  acquisition
  + integration
  + validation
  + storage/operations
  + independent review
  + maintenance/migration
DIRECT_DATA_OR_PROVIDER_COST=
DELAY_OPPORTUNITY_COST=
COMPLEXITY_OVERFIT_COST=
DATA_PERISHABILITY_OR_RECONSTRUCTABILITY=
NEXT_STAGE_REVERSIBILITY_AND_RISK=
FORWARD_OR_INDEPENDENT_EVIDENCE_VALUE=
MATURE_OR_PROVIDER_NATIVE_ROUTE_AVAILABLE=YES|NO|UNKNOWN
RESEARCH_INVESTMENT_DISPOSITION=
REOPEN_TRIGGER_IF_DEFERRED_OR_PARKED=
```

Do not fabricate a precise dollar value when the evidence supports only ordinal judgment. A concise LOW/MEDIUM/HIGH comparison with causal rationale is preferable to false precision.

Conceptual decision aid:

```text
EXPECTED_NET_RESEARCH_VALUE
≈ EXPECTED_DECISION_VALUE_OF_INFORMATION
  - TOTAL_RESEARCH_BURDEN
  - DELAY_OPPORTUNITY_COST
  - COMPLEXITY / OVERFIT COST
```

Safety, authority, correctness, data-integrity, causal-validity and authoritative next-stage-claim blockers remain hard gates. They may not be traded away because their research cost is inconvenient.

### 1A.3 Exactly four research-investment dispositions

Every material frontier item resolves to exactly one:

```text
ACQUIRE_BEFORE_NEXT_GATE
CAPTURE_CHEAP_OPTIONALITY
PROCEED_WITH_CURRENT_BEST_AND_DEFER
PARK_OR_REJECT
```

If one nominal frontier contains multiple separable missing-evidence items that could change different material decisions, decompose them before assigning dispositions. Each material item gets exactly one disposition. Do not blend an optional item with a hard blocker to force acquisition of everything, and do not hide a hard blocker inside a broader deferred item.

#### A. `ACQUIRE_BEFORE_NEXT_GATE`

Choose when at least one is true:

- the missing evidence is required to establish safety, correctness, data integrity or causal validity;
- the next authoritative claim cannot be made without it;
- the evidence is likely to change a material decision and expected value is high relative to total burden.

Rules:

```text
CHEAPEST_DECISIVE_EVIDENCE_ONLY=YES
MATURE_PROVIDER_NATIVE_FIRST=YES_WHEN_COMMODITY
SCOPE_MUST_MAP_TO_EXACT_UNRESOLVED_DECISION=YES
SPECULATIVE_DATA_PLATFORM=NO
```

After evidence is acquired, return to the research question. Acquisition does not itself validate the hypothesis.

#### B. `CAPTURE_CHEAP_OPTIONALITY`

Choose when the data is not required to make the current decision, but:

- it is ephemeral or difficult/impossible to reconstruct later;
- there is a credible future research question;
- capture has low total lifecycle burden;
- capture does not create a second authority, major persistent platform or material operational coupling.

Rules:

```text
CAPTURED_DATA_AUTHORITY=NONAUTHORITATIVE_RESEARCH_BY_DEFAULT
CURRENT_POLICY_USE_AUTHORIZED_BY_CAPTURE=NO
PROMOTION_CREDIT_FROM_CAPTURE_ALONE=NO
```

If the capture path becomes material infrastructure, stop and reclassify under the normal research-investment and mature-solution gates.

#### C. `PROCEED_WITH_CURRENT_BEST_AND_DEFER`

Choose when:

- the current candidate is coherent, deterministic, causally defined and testable;
- it is versioned/frozen where the next stage requires identity;
- all mandatory safety/correctness/authority gates for the next stage are satisfied;
- missing information is optimization-level rather than a hard blocker;
- another historical/data-engineering cycle has uncertain or declining marginal value;
- independent OOS/Forward/real-environment evidence is the more valuable next source of information.

Record known unknowns and deferred hypotheses. Do not silently treat them as resolved.

For trading Strategy work, this can authorize progression only to the next **already-authorized research/Shadow evidence stage**. It does not authorize real-capital execution, account/private API access, signing or exchange writes.

#### D. `PARK_OR_REJECT`

Choose when:

- expected decision impact is low;
- the requirement has become stale or obsolete;
- disconfirming evidence materially weakens the hypothesis;
- acquisition/complexity burden dominates plausible benefit;
- the requested feature/data is interesting but does not map to a current material decision.

Give it a concrete re-open trigger when one is known. Otherwise reject it. Do not preserve indefinite zombie TODOs merely because they once sounded useful.

### 1A.4 Trading Strategy research objective: simplest effective validated candidate

For Strategy research, do not optimize for a perfect historical strategy or the maximum backtest score.

Target:

```text
MAXIMIZE VALIDATED AFTER-COST TRADING USEFULNESS
PER UNIT OF
STRATEGY COMPLEXITY + RESEARCH / ENGINEERING BURDEN
```

Subject to mandatory safety, correctness and authority constraints.

Default preference:

```text
EFFECTIVENESS_BEFORE_SIMPLICITY
-> AMONG MATERIALLY COMPARABLE VALIDATED CANDIDATES
-> CHOOSE THE SIMPLER ONE
```

Simplicity includes fewer or narrower:

- free parameters and thresholds;
- features and data dependencies;
- policy states and conditional branches;
- market/regime-specific exceptions;
- repeated-attempt special cases;
- model classes and tuning dimensions;
- required provider/storage/operational surfaces.

Do not impose an arbitrary universal parameter-count cap. A genuine mechanism can require complexity, and a rigid small-number rule can underfit. Instead every **material discretionary economic** feature, parameter, state, branch or data dependency must have:

```text
PRESPECIFIED_CAUSAL_HYPOTHESIS=YES
SIMPLE_BASELINE=DEFINED
INCREMENTAL_VALUE_TEST=DEFINED
TRIAL_LEDGER_UPDATED=YES
MATERIAL_OOS_OR_FORWARD_ADVANTAGE_REQUIRED_FOR_PROMOTION=YES
```

Historical/in-sample improvement alone does not earn permanent discretionary economic complexity. Complexity required independently for safety, correctness, authority or causal validity remains governed by those hard gates and is not rejected merely because it lacks an economic uplift experiment.

### 1A.5 Adaptive-search / holdout contamination control

Repeated rule, parameter, feature and data-definition search on the same history increases selection bias and backtest-overfitting risk. Repeatedly inspecting OOS/holdout results and changing the candidate in response also makes that holdout adaptive and less independent.

Maintain a trial/adaptivity ledger sufficient to answer:

```text
HOW_MANY_MATERIAL_VARIANTS_HAVE_BEEN_TRIED=
WHICH_DATA_WAS_USED_TO_PROPOSE_EACH_CHANGE=
WHICH_DATA_WAS_USED_TO_SELECT_THE_WINNER=
WHICH_EVIDENCE_REMAINS_GENUINELY_LATER_OR_INDEPENDENT=
```

Do not label a repeatedly consulted OOS set as pristine independent evidence.

For material variants tried before this prospective ledger rule was adopted, do not invent an exact historical trial count. Record the best-known lower bound or `UNKNOWN_LEGACY_INCOMPLETE`, identify known adaptations where practical, and conservatively downgrade the independence/strength of historical and repeatedly consulted OOS evidence. Legacy incompleteness alone is not a safety/correctness blocker and must not create an endless historical reconstruction project merely to make the ledger look complete. If the candidate is otherwise safe/correct for a reversible non-authoritative next stage, legacy incompleteness increases the value of freezing the version and obtaining genuinely later Forward evidence.

From adoption of this rule forward, every new material Strategy variant or material discretionary economic rule/parameter change must be logged prospectively. A knowingly unlogged new material variant makes the affected adaptivity/evidence claim `FAIL` until the missing trial identity is recovered; it is not silently treated as pristine evidence.

When substantial adaptive historical search has already occurred and the current candidate is safe/correct for a reversible non-authoritative next stage, freezing the candidate and obtaining genuinely later Forward evidence should normally be preferred to opening another optimization cycle unless the research-investment gate finds a new high-value blocker.

For Forward Strategy evidence:

```text
FREEZE_VERSION_BEFORE_FORWARD_EVIDENCE=YES
ANY_MATERIAL_STRATEGY_SEMANTIC_OR_EVIDENCE_AFFECTING_CHANGE=>NEW_IMMUTABLE_VERSION
MATERIAL_CHANGE_INCLUDES=RULE|PARAMETER|FEATURE|FEATURE_OR_DATA_DEFINITION|STATE|CONDITIONAL_BRANCH|DATA_DEPENDENCY
FORWARD_EVIDENCE_CLOCK_STARTS_AT_NEW_VERSION_ACTIVATION=YES
NO_RETROACTIVE_FORWARD_EVIDENCE_CREDIT=YES
```

### 1A.6 Recursion / diminishing-return stop rule

A research frontier may recur, but it may not become an automatic loop.

```text
RESEARCH_FRONTIER
-> RESEARCH_INVESTMENT_GATE
-> EXACTLY_ONE_DISPOSITION_PER_MATERIAL_FRONTIER_ITEM
-> EXECUTE_ONLY_THAT_DISPOSITION
```

For the same strategy/problem family, repeated pre-Forward acquisition cycles are presumptively disfavored as marginal expected information value declines. A new cycle must identify a **new material decision** that the requested information could realistically change.

The statement “one more feature/data source might improve the strategy” is insufficient. Without a new blocker or high-value decision, default toward:

```text
PROCEED_WITH_CURRENT_BEST_AND_DEFER
OR
PARK_OR_REJECT
```

Do not set a fixed maximum number of cycles: a genuine new safety/correctness/causal blocker can justify another round. Convergence is determined by marginal decision value versus total burden and the availability of a better independent evidence stage, not by arbitrary iteration count.

---

## 2. Minimum deliverable

A material research/route decision should be auditable from five compact sections:

1. **Independent view** — problem, mechanics, assumptions, candidate routes;
2. **External evidence** — strongest primary/mature sources plus counterexamples;
3. **Synthesis** — confirmation/modification/rejection;
4. **Decision** — selected route and rejected alternatives;
5. **Residual uncertainty / validation plan**.

When a material research frontier is reached, add a sixth section:

6. **Research-investment disposition** — current candidate, unresolved decision, missing information, expected value/burden, one of the four dispositions, and re-open trigger where applicable. If the frontier contains multiple separable material decisions, list the decomposed frontier items and one disposition for each.

The format may be compressed for time-critical work, but the three-stage sequence remains visible.

For an external mature-solution decision, the durable decision record additionally includes the P0 matrix, evidence grades, total-burden comparison, decision-stability result and authority ownership map defined by the specialized rule.

---

## 3. Anti-patterns

Do not:

- search first and later present the external consensus as independent reasoning;
- select a preferred answer and search only for confirmation;
- cite many sources without causal analysis;
- adopt a fashionable/complex framework without comparing simpler mature routes;
- ignore negative cases or project-specific constraints;
- recommend custom commodity infrastructure before mature-solution comparison;
- allow an Engineering Control/Writer to self-authorize custom commodity infrastructure after rejecting mature candidates;
- reject a mature route because of sunk cost, existing custom code, migration inconvenience alone, a preference for no new dependency, launch proximity, architecture familiarity or belief that one more repair may work;
- use a weighted score to compensate for a failed hard requirement;
- change framework-selection weights after seeing candidate results;
- use a feasibility spike as product implementation or as the beginning of a repair chain;
- allow research itself to become an endless substitute for a decision or experiment;
- treat `DATA_BLOCKED_FRONTIER` as automatic authorization to build a data platform;
- add parameters/features/states merely because they improve the same historical sample;
- reuse a holdout adaptively and continue calling it pristine OOS evidence;
- maximize backtest score without recording search/trial history;
- fabricate a precise legacy trial count when the historical search record is incomplete;
- make legacy ledger incompleteness itself the reason for an endless reconstruction/research cycle;
- reject a materially stronger robust candidate merely because it is more complex;
- keep researching because perfection remains theoretically possible after the current candidate is good enough for a safer, more independent evidence stage.

---

## 4. Authority boundary

Research conclusions do not independently authorize implementation, commit/push, Mark Ready, merge, deployment, runtime/cloud mutation, credential/private API, wallet/signing, exchange write/order submission or trading action. Those remain governed by Unified V2 and current user/domain authority.

A custom commodity implementation additionally requires the explicit current user authority defined by Unified V2 and the external mature-solution selection rule.
