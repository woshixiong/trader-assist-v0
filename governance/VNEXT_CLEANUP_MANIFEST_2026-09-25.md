# VNext Cleanup Manifest

## Purpose

Define the final cleanup boundary before activation preparation.

## KEEP: Runtime Governance Assets

- `AGENTS_VNEXT.md`
- `governance/ENGINEERING_GOVERNANCE_VNEXT.md`
- `governance/ACTIVE_GOVERNANCE_MANIFEST_VNEXT.json`

## ARCHIVE: Migration Process Artifacts

Move to archive when cleanup commit is executed:

- Draft documents
- Templates
- Simulation documents
- Planning documents
- Checklist documents
- Validation matrices
- Temporary comparison documents

## DELETE: Duplicate Candidates

Remove only files proven to be superseded by final runtime assets.

## Safety Rules

- Do not change active governance.
- Do not modify current AGENTS routing during preparation.
- Do not activate VNext in this cleanup phase.
- Preserve rollback capability.

## Next Step

After cleanup verification, create the activation PR separately.
