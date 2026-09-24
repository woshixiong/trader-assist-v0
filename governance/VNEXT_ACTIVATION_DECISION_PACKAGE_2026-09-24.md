# VNext Activation Decision Package

## Activation Preconditions

Before switching from V4:

- core governance files generated
- dry run completed
- failure routing validated
- human gate boundaries confirmed

## Activation Order

1. Update governance manifest
2. Update AGENTS entry point
3. Update project instruction reference
4. Run qualification workflow
5. Approve activation

## Rollback

If qualification fails:

- keep V4 active
- preserve VNext artifacts
- fix candidate files
- rerun qualification

No silent activation is allowed.
