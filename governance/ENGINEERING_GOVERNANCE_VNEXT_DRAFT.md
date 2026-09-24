# Trader Assist / Trade OS — Engineering Governance VNext Draft

Status: DRAFT — migration review only

This document is a candidate replacement constitution. It does not become active until the active manifest is switched and validation is complete.

## 1. Source of truth

GitHub repository state is canonical. Chat history, copied prompts, summaries, and stale execution output are not canonical state.

Required resolution order:

```text
AGENTS.md
-> ACTIVE_GOVERNANCE_MANIFEST.json
-> PROJECT_RULES_INDEX.md
-> active constitution
```

## 2. Separation of responsibilities

### Engineering Control

Owns:
- scope definition;
- execution routing;
- frozen acceptance criteria;
- escalation decisions.

### Writer / Codex

Owns:
- implementation within frozen scope;
- tests and validation evidence.

### Independent Reviewer

Owns:
- fresh evidence-based verification;
- PASS/FAIL decision only.

### Human

Owns retained protected actions.

## 3. Execution routing

Prefer the lowest-cost capable execution path:

```text
Deterministic/mechanical -> tools
Small semantic -> lightweight model
Large coherent coding -> Codex package
Architecture/security ambiguity -> Engineering Control
```

## 4. Handoff rule

Every stage completion must provide:

```text
DECISION:
NEXT DESTINATION:
NEXT ACTION:
READY-TO-USE COMMAND:
```

No ambiguous continuation state is allowed.

## 5. Failure routing

Pre-code review failure:

- implementation/design issue inside frozen package -> return to Codex plan revision;
- scope/architecture/authority issue -> return to Engineering Control.

Final review failure:

- return to Engineering Control for new repair routing.

## 6. Human gates

Human approval remains required for protected actions:

- merge;
- deployment;
- production mutation;
- credentials;
- trading or financial actions.

## 7. Cost control principle

Use deterministic validation before model reasoning where possible. Avoid spending high-capability model tokens on mechanical state checking.

## 8. Activation requirements

This draft requires:

- manifest update;
- router update;
- simulation of success/failure flows;
- migration qualification run;
- explicit activation decision.
