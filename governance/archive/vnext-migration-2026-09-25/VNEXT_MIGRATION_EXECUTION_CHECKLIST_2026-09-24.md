# VNext Migration Execution Checklist

Status: preparation only.

## Before Activation

- Complete consolidation of governance documents.
- Validate routing and failure paths.
- Verify no active development checkpoint depends on VNext-only rules.

## Activation Sequence

1. Activate manifest pointer.
2. Activate constitution.
3. Update thin AGENTS entry.
4. Update project instruction reference.
5. Run qualification workflow.

## Rollback

If qualification fails, keep V4 active and repair VNext preparation artifacts without mutating production workflow.
