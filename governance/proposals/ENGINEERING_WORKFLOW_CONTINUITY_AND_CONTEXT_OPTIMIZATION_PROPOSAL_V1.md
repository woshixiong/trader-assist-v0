# ENGINEERING_WORKFLOW_CONTINUITY_AND_CONTEXT_OPTIMIZATION_PROPOSAL_V1

## Status
Proposal only. No authority model changes.

## Objective
Optimize V3 engineering workflow continuity while preserving existing governance boundaries.

## Design Changes

### 1. Workflow Bootstrap Pointer
Provide every engineering window with a stable pointer to:
- current canonical workflow entry;
- current governance epoch;
- active Control Capsule;
- current Task Packet.

### 2. Canonical Egress Requirement
Material engineering state must not exist only in chat.
Required durable outputs:
- Task Packet;
- Decisions;
- Evidence;
- Review Results;
- Completed Work Ledger.

### 3. Continuous Execution Until Authority Boundary
When a stage is authorized, the executor continues through all permitted routine transitions.
Stop only at:
- user authority gate;
- missing permission;
- rule conflict;
- material scope expansion;
- safety boundary.

### 4. Next Stage Packet
Every completed stage produces the minimum artifact required to continue without replaying history.

### 5. Context Minimization Policy
Default context loading:

Normal window:
- Bootstrap pointer;
- Current state;
- Task Packet;
- Relevant authority.

Codex/executor:
- Task Packet;
- required code scope;
- validation contract;
- evidence contract.

Do not provide full historical context unless required by a concrete conflict.

### 6. Executor Routing Preservation
Preserve existing routing:

- deterministic work -> scripts/tools;
- bounded mechanical changes -> ordinary Writer;
- open semantic engineering -> Executor Selection.

Possible executors remain governed by existing routing:
- Codex;
- Trae;
- DeepSeek Harness.

No automatic override of user-selected executor.

### 7. Executor Launch Configuration Disclosure
Before providing any execution prompt or launcher command, the Engineering Control window must first provide an explicit configuration block.

Required fields:

```text
EXECUTION_SURFACE:
- Ordinary ChatGPT Writer
- Codex
- Other approved executor

REPOSITORY:
<repository>

BRANCH:
<branch name>

EXECUTION_CLASS:
<M0/M1/M2/M3 classification>

MODEL:
<exact available model identifier/version when applicable>

REASONING_LEVEL:
<Low/Medium/High/Extra High or provider equivalent>

MODE:
<implementation/review/research/etc>

PERMISSIONS:
<allowed capabilities>

FORBIDDEN_ACTIONS:
<explicit boundaries>
```

The word "Codex" alone is not sufficient model identification when a specific model/version selector exists. The same rule applies to ordinary ChatGPT windows: the launch prompt must explicitly state that it is intended for a normal GPT window and must identify the expected model/reasoning configuration when relevant.

This requirement exists to prevent execution interruptions caused by missing environment information and to ensure the user can configure the correct execution surface before starting work.

## Compatibility
This proposal does not change:
- Unified Engineering Governance authority;
- Writer / Reviewer / Finalizer isolation;
- merge authority;
- deployment authority;
- runtime authority gates.

## Simulation Checklist
Required validation scenarios:

PASS:
- ordinary GPT execution;
- Codex execution;
- Review APPROVE;
- Review REQUEST_CHANGES;
- user authority gate.

FAIL-CLOSED:
- Codex unavailable;
- GitHub write unavailable.

Validation objectives:
- reduced context load;
- reduced token consumption;
- no workflow loops;
- no identity drift;
- no unauthorized execution.

## Next Step
Independent review and governance routing required before adoption.
