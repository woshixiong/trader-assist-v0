# VNext Failure Routing Final Matrix

## Purpose

Ensure every failure produces a deterministic next destination.

## Routes

### Preflight failure
Destination:
Engineering Control

### Codex Plan failure
Destination:
Codex plan revision unless scope or architecture changed.

### Pre-code Review failure
- PLAN_REVISE -> Codex
- CONTROL_REPLAN -> Engineering Control

### Implementation failure
Destination:
Codex bounded repair.

### CI failure
Destination:
Existing execution route with bounded repair.

### Final Review failure
Destination:
Engineering Control.

Reviewer never modifies implementation.

## Required output

Every transition must include:

- Current state
- Decision
- Destination
- Exact next command
- Required authority
