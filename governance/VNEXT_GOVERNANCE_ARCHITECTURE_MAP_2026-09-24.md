# Trader Assist / Trade OS — VNext Governance Architecture Map

Status: PREPARATION

Purpose: define the target governance architecture before activation. This document does not activate VNext governance.

## Target hierarchy

```text
ChatGPT Project Instruction
        |
        v
AGENTS.md (thin repository entry)
        |
        v
governance/ACTIVE_GOVERNANCE_MANIFEST.json (single active routing authority)
        |
        v
VNext Constitution (single engineering rule source)
        |
        +--> Procedures / Skills (loaded only by trigger)
        |
        +--> Codex runtime policy
        |
        +--> Deterministic execution controls
```

## Design goals

1. One active constitution.
2. One machine-readable governance entry point.
3. Thin human-facing entry files.
4. Procedures separated from immutable principles.
5. Execution state separated from semantic decisions.

## Responsibility boundaries

### Engineering Control

Owns:
- task decomposition;
- architecture and scope freeze;
- acceptance invariants;
- routing decisions;
- repair versus replan decisions.

### Codex

Owns:
- implementation within frozen scope;
- plan generation;
- coding;
- bounded validation;
- execution handoff artifacts.

### Review

Owns:
- independent evidence verification;
- exact-head validation;
- PASS/FAIL decision.

### Human

Retains:
- protected approvals;
- final review judgment;
- merge/production authority where required.

## Migration rules

- Do not activate until consistency checks pass.
- Do not keep duplicate active rules across multiple files.
- Historical documents remain reference only.
- Do not introduce a generic agent framework unless a demonstrated need exists.

## Next implementation stage

Prepare:

1. VNext constitution draft.
2. Updated manifest schema.
3. Thin AGENTS router.
4. Codex runtime consolidation.
5. Validation simulation matrix.
