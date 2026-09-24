# VNext Final Candidate Validation Checklist

## Purpose

Define the final validation gates before any VNext governance activation.

## Validation Areas

### Governance Integrity

- Constitution contains principles only.
- Procedures contain operational details only.
- Runtime configuration does not contain authority decisions.

### Routing Integrity

- Preflight routes deterministic work correctly.
- Codex tasks have explicit handoff boundaries.
- Review failures have deterministic return paths.

### Human Boundary Integrity

Protected actions remain explicit:

- MARK_READY
- MERGE
- DEPLOYMENT
- Production mutations

### Recovery Integrity

Validate:

- interrupted sessions;
- quota pauses;
- CI failures;
- transport failures;
- stale checkpoints.

## Activation Requirement

No activation until all validation evidence is recorded and reviewed.
