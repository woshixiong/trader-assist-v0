# ENGINEERING WORKFLOW CONTINUITY OPTIMIZATION V4

## Status
Proposal only. No authority model changes.

## Version Alias

Operational alias:

`V4`

Canonical GitHub document remains source of truth.

## Objective

Optimize engineering workflow continuity while preserving governance boundaries.

## Core Rules

### 1. Canonical GitHub State

Engineering state must exist in GitHub, not only chat.

Required durable outputs:
- Task Packet;
- Decisions;
- Evidence;
- Review Results;
- Completed Work Ledger.

### 2. Continuous Execution Boundary

Authorized stages continue automatically until:
- user authority gate;
- missing permission;
- rule conflict;
- scope expansion;
- safety boundary.

### 3. Context Minimization

Normal windows receive only required canonical state.

Executors receive only:
- Task Packet;
- required code scope;
- validation contract;
- evidence contract.

### 4. Execution Handoff Format

Before every launcher:

Ordinary ChatGPT:
- specify new window or existing window;
- provide prompt.

Codex:
- model;
- reasoning level;
- session choice;
- repository;
- branch;
- provide prompt.

Do not include unnecessary internal explanations.

### 5. Session Selection Requirement

Engineering Control selects new or existing session according to:
- Codex context/token efficiency;
- ordinary ChatGPT continuity;
- reviewer independence.

### 6. Review Handoff Lifecycle

Before review:

1. Write canonical review target and evidence to GitHub.
2. State required window type.
3. Provide short launcher immediately.
4. Include @GitHub in generated engineering prompts.
5. Reviewer reads GitHub canonical state.
6. Reviewer writes result back to GitHub.
7. Engineering Control verifies review object.

### 7. GitHub Capability Initialization Pattern

Generated engineering window prompts begin with:

`@GitHub`

First action:

`Check available GitHub capability.`

Capability availability must be established before GitHub-dependent execution.

### 8. CI Watch And Post-Review Progression

When a PR enters CI pending state after required review:

The authorized Engineering Control window should periodically check:
- PR state;
- exact HEAD;
- CI checks;
- required validation evidence.

When all required checks pass and no authority gate remains:

Engineering Control may automatically continue:

CI PASS
→ make PR ready for review
→ merge preparation
→ merge execution only when existing merge authority rules allow it.

No user polling should be required for states already covered by granted authority.

Merge/deployment/runtime authority boundaries remain unchanged.

### 9. Authorized Progression Hard Gate

When authority has already been granted, Engineering Control must execute all covered next actions.

Forbidden:
- stopping at status explanation;
- asking for repeated authorization;
- waiting for user polling;
- presenting already-authorized actions as future suggestions.

Stop only when a new authority boundary is reached.

### 10. CI Monitoring Continuity

For PRs under active Engineering Control ownership:

After review completion and before merge completion:

Engineering Control maintains CI state awareness through periodic checks.

When CI and required validation conditions become satisfied, the workflow continues automatically according to existing authority rules.

## Compatibility

No changes to:
- Unified Engineering Governance authority;
- Writer / Reviewer / Finalizer isolation;
- merge authority;
- deployment authority;
- runtime authority gates.

## Simulation Requirements

Validate:
- ordinary GPT execution;
- Codex execution;
- session selection;
- review handoff;
- review result retrieval;
- CI monitoring;
- authority boundary handling;
- authorized progression enforcement.

Success criteria:
- reduced context transfer;
- reduced token usage;
- no identity drift;
- no unauthorized execution.
