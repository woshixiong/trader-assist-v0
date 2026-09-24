# VNext Governance Simulation Scenarios

## Purpose
Validate the proposed governance flow before activation without changing active governance.

## Scenario Matrix

### Normal Delivery
Preflight -> Codex Plan -> Review -> Implementation -> CI -> Final Review -> Human Protected Gate.

Expected: continuous flow with only retained human gates.

### Pre-code Review Failure
Reviewer must return:
- decision;
- failure category;
- destination (`PLAN_REVISE` or `CONTROL_REPLAN`);
- exact next command.

### CI Failure
CI remains deterministic owner. The implementation route receives bounded failure evidence and performs scoped repair.

### Final Review Failure
Return to Engineering Control. Reviewer remains read-only and does not implement fixes.

### Interruption Recovery
Resume from durable GitHub state. Do not restart semantic work after transport/UI/quota interruption.

## Success Criteria
The workflow must minimize human routing decisions while preserving protected authority boundaries.
