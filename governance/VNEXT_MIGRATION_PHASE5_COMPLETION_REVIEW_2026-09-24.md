# VNext Governance Migration — Phase 5 Completion Review

## Purpose

Consolidate the governance preparation work completed before activation.

## Completed Design Areas

- Constitution layer design
- Active manifest routing design
- Thin AGENTS entry design
- Procedure routing model
- Codex execution policy
- Token optimization policy
- Handoff contract
- Final review and protected gate flow
- Qualification run planning

## Activation Preconditions

Before switching from V4 active governance:

1. Validate all routing references.
2. Validate no active legacy checkpoint depends on V4-only behavior.
3. Run qualification workflow.
4. Update active manifest atomically.
5. Update project instruction after GitHub governance activation.

## Migration Principle

Do not expand governance complexity. Prefer:

- one source of truth;
- explicit routing;
- deterministic state transfer;
- minimal human decision points;
- preserved protected gates.
