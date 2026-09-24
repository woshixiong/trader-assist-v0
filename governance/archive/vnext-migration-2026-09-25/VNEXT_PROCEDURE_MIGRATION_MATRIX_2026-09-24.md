# Trade OS VNext Procedure Migration Matrix

Status: PREPARED

Purpose: define how existing procedures move into the VNext governance model.

## Migration rules

- Constitution owns invariants and authority boundaries.
- Procedures own narrow operational workflows.
- Skills own phase-specific execution guidance.
- Research/history documents cannot enter the mandatory execution path.

## Procedure classes

### Keep as active procedure

Criteria:
- narrow domain;
- triggered by a clear event;
- does not compete with constitution.

### Merge into constitution

Criteria:
- universal invariant;
- authority boundary;
- safety requirement.

### Merge into runtime/controller

Criteria:
- state transition;
- checkpoint handling;
- deterministic routing;
- retry policy.

### Archive

Criteria:
- historical rationale;
- superseded routing;
- obsolete executor assumptions.

## Migration validation

Before VNext activation:

1. Every active procedure has one owner.
2. No duplicate mandatory rule exists in multiple layers.
3. Manifest references only active objects.
4. Historical documents cannot override active governance.
