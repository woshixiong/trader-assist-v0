# Mandatory Engineering Preflight and Convergence Gate V1

Effective: 2026-08-17

## Purpose

Prevent locally reasonable engineering work from violating project-wide rules, creating avoidable near-term rewrites, or entering repeated repair loops because a Writer task was dispatched before the whole architecture, authority model, future continuation path, realistic workload and stop conditions were checked.

This rule is mandatory for every material engineering route, architecture decision, runtime/persistence/provider design, cross-layer repair, technical selection, Writer task package and final implementation prompt.

It complements the mandatory research/evidence/decision method and `HOLISTIC_ENGINEERING_VERIFICATION_CONTINUITY_AND_RELEASE_METHOD_V1_2026-08-31.md`. It grants no merge, deployment, runtime, cloud, credential, account/private API, signing, wallet, exchange-write or order-submission authority.

## 1. Why this rule exists

PR #106 exposed a governance execution failure rather than a lack of engineering rules. Several correct rules existed, but they were distributed across merged files, Draft governance PRs and Issue comments. During repeated local repairs, the task repeatedly optimized the current blocker before re-running the complete project-wide route checks. That allowed new cross-layer issues to appear after each repair.

The permanent lesson is:

- global rules must be applied before local code reasoning;
- architecture invariants must be frozen before dispatching a Writer on a cross-layer problem;
- current implementation and future continuation must be reviewed together;
- realistic provider/scale/freshness constraints must be reviewed before implementation acceptance;
- verification topology and validation environment must match the authority actually being claimed;
- one repair loop must not become sunk-cost continuation;
- a critical project rule must not exist only in chat memory or an obscure Issue comment.

## 2. Mandatory order of operations

For every MATERIAL technical task, the engineering orchestrator must execute this order before producing any implementation prompt:

1. **Load canonical rules** — `AGENTS.md`, `governance/PROJECT_RULES_INDEX.md`, this file, `governance/HOLISTIC_ENGINEERING_VERIFICATION_CONTINUITY_AND_RELEASE_METHOD_V1_2026-08-31.md`, the research/evidence/decision method, the active bounded issue, current accepted architecture, and live GitHub/CI state.
2. **Classify the task** — purely mechanical/exact-state work or material design work. Any new architecture, authority, provider, persistence, lifecycle, concurrency, recovery, scale, performance or cross-layer choice is material.
3. **Independent analysis first** — identify the problem, root cause candidates, affected authorities, invariants and likely routes before reading external conclusions.
4. **External mature-solution research** — for material route choices, check authoritative docs, mature frameworks/patterns, validated cases, competing approaches and disconfirming evidence.
5. **Synthesis** — state what external evidence confirms, modifies, rejects or leaves uncertain.
6. **Global Architecture Compatibility Gate** — verify current correctness, authority preservation, future continuity, replaceability, migration/lock-in risk and overengineering risk.
7. **Scale / Provider / Freshness Gate** — calculate target-scale request/database workload and prove realistic-size behavior where production scale matters.
8. **Holistic Verification / Validation-Environment Gate** — freeze applicable contract-closure, admitted-input-totality, production-path, incident-convergence, canonical validation-command, authoritative platform/environment, exact-release and evidence-checkpoint plans.
9. **Attack matrix** — define the important normal, failure, restart/replay, boundary and mixed-state cases before implementation.
10. **Repair budget and stop condition** — state whether this is initial implementation, normal repair or exceptional repair, and what event forces a holistic stop.
11. **Only then dispatch Writer** — issue one complete self-contained task package. Do not append architecture-critical requirements later as an afterthought.

If any mandatory step is unresolved, Writer dispatch is prohibited.

## 3. Mandatory preflight record

Before a Writer implementation prompt is issued for a MATERIAL task, the orchestrator must have a complete preflight record with the following fields:

```text
ENGINEERING_PREFLIGHT_GATE=PASS/FAIL
TASK_CLASS=MATERIAL/MECHANICAL
LIVE_REPO=
LIVE_MAIN_SHA=
ACTIVE_ISSUE_OR_PR=
EXACT_START_HEAD=

INDEPENDENT_ANALYSIS_DONE=YES/NO
EXTERNAL_RESEARCH_DONE=YES/NO/NOT_REQUIRED
SYNTHESIS_DONE=YES/NO

ROOT_CAUSE_LEVEL=LOCAL/CROSS_LAYER/ARCHITECTURAL/UNKNOWN
AFFECTED_AUTHORITIES=
FROZEN_INVARIANTS=
CURRENT_ROUTE=
MATURE_ALTERNATIVES_CONSIDERED=

CURRENT_NEED=
NEXT_EXPECTED_STAGE=
STABLE_INTERFACES=
REPLACEABLE_IMPLEMENTATION_SEAMS=
KNOWN_REWRITE_OR_LOCKIN_RISK=
OVERENGINEERING_CHECK=PASS/FAIL

PROVIDER_SCALE_BUDGET=PASS/FAIL/NOT_APPLICABLE
REALISTIC_SCALE_TEST_PLAN=
FRESHNESS_OR_LATENCY_GATE=

HOLISTIC_METHOD_APPLICABLE=YES/NO
CROSS_LAYER_CONTRACT_CLOSURE_PLAN=
ADMITTED_INPUT_TOTALITY_PLAN=
PRODUCTION_PATH_FIDELITY_PLAN=
INCIDENT_TO_INVARIANT_PLAN=
CANONICAL_VALIDATION_COMMANDS=
VALIDATION_PLATFORM_CLASS=PLATFORM_NEUTRAL/MACOS/LINUX/TARGET_HOST_SPECIFIC/OTHER/NOT_APPLICABLE
AUTHORITATIVE_VALIDATION_ENVIRONMENT=
KNOWN_ENVIRONMENT_MISMATCHES=
FALLBACK_VALIDATION_SURFACE=
EVIDENCE_CHECKPOINT_PLAN=
EXACT_RELEASE_VERIFICATION_PLAN=
CONTINUITY_CLASSIFICATION=

ATTACK_MATRIX_FROZEN=YES/NO
REPAIR_STAGE=INITIAL/NORMAL_REPAIR/EXCEPTIONAL_REPAIR/HOLISTIC_CONVERGENCE
STOP_CONDITION=

WRITER_SCOPE=
PROHIBITED_SCOPE=
ROLLBACK_OR_SAFE_STOP=
```

`ENGINEERING_PREFLIGHT_GATE=PASS` is allowed only when every applicable mandatory field is resolved. Use `NOT_APPLICABLE` explicitly where a holistic field genuinely does not apply.

For mechanical work, the record may be shortened, but if the work exposes a new material design choice it must immediately reclassify to MATERIAL and run the full gate.

## 4. Global Architecture Compatibility Gate

Every material route must answer all of the following before implementation:

### Current correctness

- Does the route solve the root cause rather than only the observed symptom?
- Are state transitions and cross-layer authority relationships explicit?
- Is there a smaller mature/provider-native route that removes custom complexity?

### Authority preservation

- Which existing authorities remain unchanged?
- Does the route create a second authority, hidden cache, parallel truth or retrospective action path?
- Do restart/replay and duplicate wakeups preserve the same authority model?

### Future continuity

State explicitly:

- current bounded need;
- next expected scale/capability step;
- interfaces/contracts/authorities intended to remain stable;
- concrete implementation policy that may later be replaced;
- what can be retuned versus what requires redesign;
- known migration or lock-in risk.

A bounded implementation must not be chosen merely because it is smallest today if it predictably forces a near-term architecture rewrite.

At the same time, continuity is not permission to build speculative future platforms. Prefer **stable narrow seams + one current implementation** over generalized frameworks.

### Replaceability test

When a provider/finality/storage/execution implementation is expected to change later, require at least one test or proof that a deterministic substitute can be injected/replaced without rewriting unrelated upper layers.

### No hard-coded launch accident

Launch-specific values such as current market count, current host, current provider pacing or current implementation policy must not become architectural constants unless the product contract itself makes them permanent.

## 5. Scale / Provider / Freshness Gate

Before first deployment or any material change to market count, history depth, cadence, REST/WS load, confirmation/retry count, concurrency, database workload or runtime cohort size, calculate the relevant budget.

At minimum where applicable:

```text
market_count × calls_per_market × provider_weight × cadence
market_count × history_points × database_operations
```

Also estimate or measure:

- provider headroom including retries;
- p50/p95/worst-case completion/freshness latency;
- CPU/memory/database operation order of magnitude;
- event-loop/shutdown responsiveness;
- whether the intended trading freshness SLA is still achievable.

Unit correctness at a tiny fixture is insufficient when the real workload is materially larger. Include one realistic-order-of-magnitude acceptance test when the bottleneck class is scale-dependent.

Do not turn this into a general capacity platform unless evidence requires one.

## 6. Repair budget / anti-local-loop rule

Default repair budget for one bounded design route:

1. initial implementation;
2. at most one normal bounded repair;
3. at most one explicitly authorized exceptional repair.

If the route still fails independent acceptance after that, or if a new blocker proves the problem crosses previously assumed authority/layer boundaries, STOP implementation immediately.

Enter:

`HOLISTIC_CONVERGENCE_GATE`

The orchestrator must then:

- stop Writer coding;
- review base→HEAD and the whole affected state machine/authority path;
- identify the common root cause behind repeated symptoms;
- re-run the mandatory research and continuity gates;
- prefer reduction, replacement, a mature external pattern or a cleaner abstraction over more local conditionals;
- present the revised route before authorizing more code.

Sunk cost is never justification for another repair.

## 7. Global-before-local abstraction check

Before repairing multiple symptoms in the same subsystem, ask:

> Are several local failures manifestations of one incorrectly placed global responsibility?

Typical warning signs include:

- whole-cohort behavior driven by per-market callbacks;
- global state changes activated by a single local event;
- repeated special cases around the same state transition;
- increasing test count without a stable invariant/state model;
- Writer and Reviewer repeatedly discovering new mixed-state combinations;
- fixes that require more exceptions in adjacent layers.

If these signs appear, stop adding local guards and model the correct global boundary/invariant first.

## 8. Complete-prompt rule / no architecture-critical addenda

A Writer task must be complete before the user executes it.

After a Writer prompt has been issued:

- if only formatting or non-semantic clarification is needed, a small clarification is allowed;
- if a new project-wide rule, architecture invariant, future-continuity requirement, provider constraint, authority boundary or major attack case is discovered, the old prompt is VOID;
- regenerate one complete replacement prompt instead of asking the user to append a patch/addendum.

This prevents "马后炮" task construction and keeps the Writer working from one coherent contract.

## 9. Canonical-rule location rule

Critical project-wide engineering rules must be discoverable from the mandatory successor-window read path.

Do not rely on chat memory alone.
Do not rely on an Issue comment alone for a permanent rule.
Do not leave a critical rule only in an unmerged Draft governance PR indefinitely.

When a new permanent rule is discovered:

1. record an immediate live coordination note if needed;
2. create/reconcile a canonical governance-file change from current main;
3. add the file to `AGENTS.md` / `PROJECT_RULES_INDEX.md` mandatory read path;
4. explicitly disposition stale/superseded governance proposals;
5. require successor-window handoffs to name any still-unmerged canonical governance proposal until it is merged or rejected.

## 10. Writer / Reviewer separation

Writer self-reported PASS is not independent acceptance.

Reviewer must verify actual diff, exact head, relevant authority seams, attack tests and exact-head CI.

However, repeated full rereview is not a substitute for a correct route. After the repair budget is exhausted, Reviewer must trigger holistic convergence rather than simply request another patch.

## 11. User-facing escalation

When confidence in the technical route is materially limited, present the user with the decision at the ROUTE level rather than burying uncertainty inside another implementation prompt.

The concise escalation must state:

- what is failing;
- why the current route may be wrong;
- the mature/simple alternatives;
- time/cost/risk tradeoffs;
- the recommended route;
- whether development should pause.

The user may then make the final route decision.

## 12. Holistic verification / validation-environment gate

`HOLISTIC_ENGINEERING_VERIFICATION_CONTINUITY_AND_RELEASE_METHOD_V1_2026-08-31.md` is the mandatory detailed authority for the following decisions:

```text
CROSS_LAYER_CONTRACT_CLOSURE
ADMITTED_INPUT_TOTALITY
PRODUCTION_PATH_FIDELITY
INCIDENT_TO_INVARIANT_CONVERGENCE
BALANCED_G0_TO_G12_VERIFICATION_RESPONSIBILITIES
EXACT_RELEASE_AND_STAGED_ARTIFACT_VERIFICATION
VALIDATION_ENVIRONMENT_FIDELITY
CODE_CONTINUITY_CLASSIFICATION
```

Before dispatching a Writer or accepting a material implementation, establish which repository/CI validation commands are canonical and which platform class makes each result authoritative.

Permanent rules:

```text
CANONICAL_VALIDATION_COMMAND_REUSE=REQUIRED
PLATFORM_SENSITIVE_VALIDATION_ON_NONAUTHORITATIVE_OS=PROHIBITED
KNOWN_ENVIRONMENT_MISMATCH_REUSE=REQUIRED
NO_LOCAL_RETRY_AFTER_PROVEN_PLATFORM_MISMATCH=REQUIRED
POST_WRITER_EVIDENCE_CHECKPOINT_BEFORE_NONDECISIVE_TAIL=REQUIRED
```

Do not invent a stricter ad-hoc validation command and treat its environment-specific failure as a new application blocker. Do not erase or rerun a completed semantic Writer merely because a later platform-sensitive validation tail ran on the wrong OS when the exact Writer delta remains provable.

## 13. Permanent engineering objective

Optimize in this order:

1. real safety and authority correctness;
2. root-cause correctness;
3. trading/data freshness and real usefulness;
4. smallest mature/reusable route;
5. future continuation without near-term rewrite;
6. implementation/review/maintenance cost;
7. optional sophistication.

The project should reach useful operation quickly, but never by installing a shortcut that predictably creates the next critical rewrite.