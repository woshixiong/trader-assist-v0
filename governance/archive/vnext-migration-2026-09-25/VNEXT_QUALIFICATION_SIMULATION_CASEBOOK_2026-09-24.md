# VNext Qualification Simulation Casebook

## Objective
Validate that the future workflow closes automatically without unnecessary human routing decisions.

## Cases

1. Normal path
- Preflight PASS
- Plan PASS
- Review PASS
- Execution PASS
- CI PASS
- Final Review PASS

2. Planning failure
- Return destination must be explicit.
- Required action must include executable command.

3. Implementation failure
- Return to bounded repair path.
- Preserve task identity and checkpoint.

4. CI failure
- Use deterministic evidence.
- Avoid model-mediated CI polling.

5. Final Review failure
- Return to Engineering Control.
- Reviewer remains read-only.

6. Interruption
- Resume checkpoint.
- Do not restart semantic work.
