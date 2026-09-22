# ENGINEERING WORKFLOW CONTINUITY OPTIMIZATION V4

## Status
Proposal only. No authority model changes.

## Version Alias

This workflow optimization proposal is referenced operationally as:

`V4`

The V4 alias is a human communication shortcut only. The canonical GitHub document remains the source of truth.

## Objective

Optimize engineering workflow continuity while preserving existing governance boundaries.

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

Normal windows receive only:
- Bootstrap pointer;
- Current state;
- Task Packet;
- Relevant authority.

Executors receive only:
- Task Packet;
- required code scope;
- validation contract;
- evidence contract.

### 4. Executor Configuration Disclosure

Before every launcher prompt provide:

- EXECUTION_SURFACE
- REPOSITORY
- BRANCH
- EXECUTION_CLASS
- MODEL
- REASONING_LEVEL
- MODE
- PERMISSIONS
- FORBIDDEN_ACTIONS

Executor identity and model identity must be separated.

### 5. Review Handoff Lifecycle

Before requesting review:

1. Write canonical review target and evidence to GitHub.
2. Immediately provide a short review launcher.
3. Include @GitHub at the beginning of every generated engineering window prompt.
4. Reviewer reads GitHub canonical state directly.
5. Reviewer writes result back to GitHub.
6. Engineering Control verifies review object before continuing.

No manual context relay is required when GitHub contains the canonical information.

### 6. GitHub Capability Bootstrap

All generated engineering window prompts begin with:

`@GitHub`

Applies to:
- implementation windows;
- review windows;
- research windows;
- validation windows.

@GitHub initializes capability discovery only. It does not expand authority.

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
- review handoff;
- review result retrieval;
- authority boundary handling.

Success criteria:
- reduced context transfer;
- reduced token usage;
- no identity drift;
- no unauthorized execution.
