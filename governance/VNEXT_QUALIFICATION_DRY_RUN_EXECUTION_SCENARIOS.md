# VNext Qualification Dry Run Execution Scenarios

## Objective

Validate that the proposed governance can route normal and failed workflows without ambiguity.

## Scenarios

### Normal
Preflight -> Plan -> Review -> Execute -> CI -> Final Review -> Human Gate

### Pre-code Review Failure
- PLAN_REVISE returns to Codex planning.
- CONTROL_REPLAN returns to Engineering Control.

### Implementation Failure
Return to bounded repair route with preserved checkpoint.

### CI Failure
Use deterministic CI evidence and bounded repair.

### Final Review Failure
Return to Engineering Control. Reviewer remains read-only.

### Interruption
Resume from durable state; do not restart semantic work.
