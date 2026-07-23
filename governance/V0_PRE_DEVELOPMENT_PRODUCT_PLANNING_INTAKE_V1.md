# V0 Pre-Development Product Planning Intake V1

**Status:** SKELETON / PENDING FIRST LAUNCH ACCEPTED REAL OPERATION  
**Authority owner:** Product Function and Priority window  
**Implementation authority:** `FALSE`

## 1. Purpose

This document is the single entrypoint for V0 product planning after First Launch reaches accepted real operation.

It prevents the Product Function and Priority window from planning V0 from an incomplete chat history, one old roadmap, or one current engineering task. It requires unified intake of:

- prior V0 product plans;
- First Launch final product and technical baseline;
- all First Launch residual and deferred work;
- Gate B real-operation evidence;
- Workstream A Minimum V0 transition analysis;
- current V0/mainline architecture and authority boundaries;
- accepted engineering and resource constraints.

This document does not preselect V0 features.

## 2. Activation gate

The planning intake becomes active only after:

```text
FIRST_LAUNCH_ACCEPTED_REAL_OPERATION = TRUE
DEFERRED_REGISTER_AVAILABLE = TRUE
FIRST_LAUNCH_FINAL_BASELINE_AVAILABLE = TRUE
WORKSTREAM_A_AVAILABLE_OR_EXPLICITLY_UNAVAILABLE = TRUE
GATE_B_EVIDENCE_AVAILABLE_OR_EXPLICITLY_INSUFFICIENT = TRUE
```

Insufficient Gate B evidence does not permit invented conclusions. The Product window may decide to continue evidence collection.

## 3. Required startup reading order

The Product Function and Priority window must read:

1. `AGENTS.md`;
2. `governance/PROJECT_RULES_INDEX.md`;
3. `governance/PROJECT_THREE_PHASE_PLAN_AND_DEFERRED_REGISTER_V1.md`;
4. current First Launch final baseline and residual report;
5. Workstream A Minimum V0 transition package;
6. Gate B real-operation evidence;
7. prior accepted V0 product plans and roadmaps;
8. current architecture and authority-boundary documents;
9. current Project State and live GitHub status;
10. any active identified governance Draft PR that has not yet reached a safe merge point.

The window must report every missing input and its consequence.

## 4. Inputs to finalize after launch

### 4.1 First Launch final baseline

Must include:

- exact product scope operated;
- exact main/merge SHA;
- deployed version;
- accepted CI, Reviews, host gate, and smoke evidence;
- runtime and notification behavior;
- known operational limitations;
- account/trading authorities that remain prohibited.

### 4.2 Gate B evidence

Must include, when available:

- signal count and valid-signal visibility;
- FAST versus STANDARD behavior;
- signal quality and expectancy;
- MFE/MAE and drawdown;
- regime coverage;
- missed/manual execution opportunities;
- notification latency and failure;
- data freshness and continuity;
- runtime reliability;
- user qualitative judgment;
- sample size and confidence limitations.

### 4.3 Deferred register

Every item in `PROJECT_THREE_PHASE_PLAN_AND_DEFERRED_REGISTER_V1.md` must receive one planning disposition. No item may be silently omitted.

### 4.4 Prior V0 plan

The Product window must distinguish:

- still-valid product intent;
- assumptions invalidated by First Launch;
- capabilities already implemented;
- capabilities deferred for evidence;
- capabilities moved to mainline;
- rejected or superseded ideas.

### 4.5 Mainline constraints

Include:

- authority boundaries;
- data and strategy lifecycle;
- execution/security gates;
- persistence and evidence architecture;
- repository ownership boundaries;
- compatibility with Trade OS production authority.

## 5. Product questions to answer

The Product window must decide:

1. What exact user problem must V0 solve beyond First Launch?
2. Which First Launch gaps are proven by evidence?
3. Is the primary next constraint signal quality, signal frequency, regime coverage, manual execution latency, runtime reliability, data quality, or evidence closure?
4. Which features are mandatory for a coherent V0 rather than isolated enhancements?
5. Which capabilities belong to the Trade OS mainline rather than V0?
6. Which items require more evidence before activation?
7. What remains explicitly out of scope?
8. What product acceptance evidence will prove V0 success?
9. What account, credential, execution, or capital authority changes are requested?
10. What can be delivered without creating irreversible architecture or unsafe authority?

## 6. Mandatory classification

Every candidate item must be classified as exactly one of:

- `V0_REQUIRED`;
- `MAINLINE_REQUIRED`;
- `EVIDENCE_TRIGGERED`;
- `OPTIONAL`;
- `REJECTED_WITH_REASON`.

Each classification must include:

- user value;
- evidence;
- reason now or later;
- dependency;
- risk if omitted;
- authority change;
- acceptance criteria;
- whether engineering discovery is needed.

## 7. Required product output

The formal output is:

```text
V0_PRODUCT_SCOPE_DECISION_V1
```

It must contain:

- V0 objective;
- target user workflow;
- selected features;
- selected deferred closures;
- explicitly excluded features;
- accepted evidence and uncertainties;
- V0 versus mainline boundary;
- product priorities;
- dependencies;
- product acceptance criteria;
- requested authority changes;
- post-V0 evidence plan;
- final disposition of every deferred item.

The output must state:

```text
UNRECORDED_KNOWN_DEFERRED_ITEMS = 0
```

or stop and list the omissions.

## 8. Handoff to Engineering Optimization

Engineering Optimization may begin only after Product Authority accepts `V0_PRODUCT_SCOPE_DECISION_V1`.

Engineering Optimization then defines:

- coherent stage sequence;
- architecture and interfaces;
- exact allowlists;
- dependencies;
- Agent/model/harness routing;
- commit and repair budgets;
- tests and Reviews;
- token/resource budget;
- rollout, rollback, and authority gates.

Engineering may challenge feasibility, safety, dependency, or resource assumptions, but may not silently remove or add product scope.

## 9. Handoff to Project Control

Project Control activates only accepted engineering stages. It must not begin V0 coding directly from this intake skeleton or from an old roadmap.

Required activation chain:

```text
V0_PRODUCT_SCOPE_DECISION_V1 accepted
→ V0_ENGINEERING_STAGE_PLAN accepted
→ exact Project Control activation
→ bounded Writer and Review execution
```

## 10. Safety boundary

No V0 planning document automatically grants:

- account access;
- credentials or private keys;
- signing or nonce authority;
- Testnet/Mainnet writes;
- order submission or cancellation;
- automatic protective orders;
- autonomous strategy activation;
- production rule mutation;
- paid cloud activation.

Every such capability requires separate product, engineering, security, Testnet/canary, and user authority gates.

## 11. Update rule

After First Launch accepted real operation, Project Control must update this skeleton with exact references to:

- final baseline document and SHA;
- Gate B evidence package and SHA;
- Workstream A package and SHA;
- deferred-register version;
- prior V0 planning sources;
- current architecture sources;
- Product Planning session identifier;
- final `V0_PRODUCT_SCOPE_DECISION_V1` path and SHA.

The updated version must be persisted through the GitHub canonical rule workflow and independently reviewed.