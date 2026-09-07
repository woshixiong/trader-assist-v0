# Trader Assist / Trade OS — Research, Evidence and Decision Procedure V1

**Status:** TASK-CONDITIONAL PROCEDURE CANDIDATE  
**Effective date:** 2026-08-16  
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

When the external-solution rule applies, Phase 3 must preserve its typed Stage 0 disposition (`SELECT_MATURE_ROUTE`, `SELECT_MODULAR_COMPOSITION`, `ONE_BLOCKER_FEASIBILITY_SPIKE`, `REJECT_CANDIDATE`, `NO_FITTING_MATURE_ROUTE`, or `SAFE_STOP`) rather than paraphrasing an unresolved comparison into an implementation recommendation.

---

## 2. Minimum deliverable

A material research/route decision should be auditable from five compact sections:

1. **Independent view** — problem, mechanics, assumptions, candidate routes;
2. **External evidence** — strongest primary/mature sources plus counterexamples;
3. **Synthesis** — confirmation/modification/rejection;
4. **Decision** — selected route and rejected alternatives;
5. **Residual uncertainty / validation plan**.

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
- allow research itself to become an endless substitute for a decision or experiment.

---

## 4. Authority boundary

Research conclusions do not independently authorize implementation, commit/push, Mark Ready, merge, deployment, runtime/cloud mutation, credential/private API, wallet/signing, exchange write/order submission or trading action. Those remain governed by Unified V2 and current user/domain authority.

A custom commodity implementation additionally requires the explicit current user authority defined by Unified V2 and the external mature-solution selection rule.
