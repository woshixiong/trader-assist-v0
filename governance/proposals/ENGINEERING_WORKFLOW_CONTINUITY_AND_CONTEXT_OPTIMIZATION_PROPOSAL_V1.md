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
EXECUTION_SURFACE
REPOSITORY
BRANCH
EXECUTION_CLASS
MODEL
REASONING_LEVEL
MODE
PERMISSIONS
FORBIDDEN_ACTIONS
```

"Codex" alone is not sufficient when a specific model/version selector exists. Ordinary ChatGPT launch instructions must explicitly state that they are for an ordinary GPT window and include expected model/reasoning configuration when relevant.

### 8. Canonical Review Handoff Optimization
Review handoff must use GitHub as the durable source of truth.

The proposal, implementation evidence, changed files, validation state and review requirements must already exist in canonical GitHub locations before requesting review.

The user should not be required to copy a long review prompt containing information already stored in GitHub.

Default review handoff format:

1. Provide a short reviewer launcher immediately when review boundary is reached.
2. Include only:
   - repository;
   - PR/commit locator;
   - reviewer role;
   - review objective;
   - required output format.
3. Reviewer performs fresh GitHub reads to load canonical evidence.
4. Reviewer writes review result back to GitHub.
5. Engineering Control verifies the GitHub review object before continuing.

Long context transfer is prohibited by default when equivalent canonical GitHub evidence exists.

### 9. GitHub Capability Bootstrap Requirement
All generated prompts that create new engineering windows must begin with:

```text
@GitHub
```

This applies to:
- implementation windows;
- review windows;
- research windows;
- validation windows;
- any other engineering execution surface requiring GitHub interaction.

The purpose is to ensure the new window initializes with the GitHub connection path required to access canonical engineering state.

The @GitHub marker does not grant additional authority. Authority remains defined by the execution role, permissions, and governance rules included in the launcher.

Generated launchers must still explicitly define:
- repository;
- branch or review target;
- execution surface;
- permissions;
- authority boundary.

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
- short review handoff from GitHub canonical state;
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
