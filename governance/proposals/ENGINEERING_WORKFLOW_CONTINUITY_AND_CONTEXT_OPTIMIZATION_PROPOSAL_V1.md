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

### 4. Execution Handoff Format

Before every launcher prompt, provide only the information required for execution.

For ordinary ChatGPT:
- specify new window or existing window;
- provide the prompt.

For Codex:
- model;
- reasoning level;
- new Session or existing Session;
- repository;
- branch;
- provide the prompt.

Do not include unnecessary internal explanations.

Executor identity, model identity, and session identity must remain separate.

### 5. Session Selection Requirement

Engineering Control must choose whether execution continues in an existing session or starts a new session.

Session selection must preserve:
- Codex token efficiency and context reuse;
- ordinary ChatGPT workflow continuity;
- reviewer independence.

Review tasks should normally use a fresh independent window.

### 6. Review Handoff Lifecycle

Before requesting review:

1. Write canonical review target and evidence to GitHub.
2. State the required review window type.
3. Provide a short review launcher immediately.
4. Include @GitHub at the beginning of every generated engineering window prompt.
5. Reviewer reads GitHub canonical state directly.
6. Reviewer writes result back to GitHub.
7. Engineering Control verifies review object before continuing.

No manual context relay is required when GitHub contains the canonical information.

### 7. GitHub Capability Bootstrap

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
- new versus existing session selection;
- review handoff;
- review result retrieval;
- authority boundary handling.

Success criteria:
- reduced context transfer;
- reduced token usage;
- no identity drift;
- no unauthorized execution.
