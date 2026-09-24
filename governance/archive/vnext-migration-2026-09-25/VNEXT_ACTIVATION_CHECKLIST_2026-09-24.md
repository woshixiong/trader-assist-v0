# Trade OS VNext Governance Activation Checklist

Status: PREPARATION ONLY

This checklist defines the transition gate from V4 active governance to VNext.

## Preconditions

- Current development workflow has no unfinished V4 execution checkpoint.
- VNext constitution, manifest, index, and entry router are internally consistent.
- No active PR depends on old governance semantics.
- Governance consistency checks pass.

## Migration order

1. Update the active governance manifest pointer.
2. Activate the VNext constitution.
3. Replace AGENTS.md with the final thin router.
4. Update PROJECT_RULES_INDEX.md references.
5. Replace ChatGPT Project Instruction bridge.
6. Validate Codex runtime policy and routing.
7. Run an end-to-end qualification task.

## Rollback

If qualification fails, restore the previous active manifest pointer and retain
all migration artifacts for diagnosis.

## Non-goals

- No production code change.
- No automatic merge authority expansion without explicit governance approval.
- No removal of final independent review.
