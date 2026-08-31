# Trader Assist / Trade OS — Research, Evidence and Decision Procedure V1

**Status:** TASK-CONDITIONAL PROCEDURE CANDIDATE  
**Effective date:** 2026-08-16  
**Normative owner:** `UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V2_2026-09-01.md`

This file is a reusable **procedure and output template** for material direction-setting research. It does not create a second project-wide engineering authority. Unified V2 governs if there is any conflict.

Use this procedure when a task materially sets or changes product, strategy, engineering route, architecture, provider, framework, tool, migration, optimization or other direction on which meaningful engineering time/risk will depend.

Do not require it for purely mechanical execution of an already-frozen plan. If a mechanical task exposes a new material decision, apply this procedure to that decision.

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

### Phase 2 — External evidence

Prioritize:

1. official specifications, provider docs and first-party source repositories;
2. primary research, inspectable datasets and reproducible benchmarks;
3. mature maintained frameworks and credible production cases/postmortems;
4. high-quality independent technical analysis;
5. community discussion only as supplementary evidence.

Research competing approaches and disconfirming evidence, not only support for the preliminary view.

Check freshness where it matters. Distinguish measured evidence from marketing/opinion. Evaluate mature solutions against actual Trader Assist / Trade OS constraints rather than adopting them by popularity.

Before recommending custom commodity engineering, explicitly check accepted project capability, provider-native, standard/official and mature maintained alternatives.

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

---

## 2. Minimum deliverable

A material research/route decision should be auditable from five compact sections:

1. **Independent view** — problem, mechanics, assumptions, candidate routes;
2. **External evidence** — strongest primary/mature sources plus counterexamples;
3. **Synthesis** — confirmation/modification/rejection;
4. **Decision** — selected route and rejected alternatives;
5. **Residual uncertainty / validation plan**.

The format may be compressed for time-critical work, but the three-stage sequence remains visible.

---

## 3. Anti-patterns

Do not:

- search first and later present the external consensus as independent reasoning;
- select a preferred answer and search only for confirmation;
- cite many sources without causal analysis;
- adopt a fashionable/complex framework without comparing simpler mature routes;
- ignore negative cases or project-specific constraints;
- recommend custom commodity infrastructure before mature-solution comparison;
- allow research itself to become an endless substitute for a decision or experiment.

---

## 4. Authority boundary

Research conclusions do not independently authorize implementation, commit/push, Mark Ready, merge, deployment, runtime/cloud mutation, credential/private API, wallet/signing, exchange write/order submission or trading action. Those remain governed by Unified V2 and current user/domain authority.