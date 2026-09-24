# VNext Core Files Migration Specification

## Purpose

Define the transition from distributed VNext preparation documents into the final executable governance core.

## Target files

1. ENGINEERING_GOVERNANCE_VNEXT.md
   - Stable engineering constitution.
   - Contains principles, roles, authority boundaries, and invariants.

2. ACTIVE_GOVERNANCE_MANIFEST_VNEXT.json
   - Single routing entry point.
   - Points to active constitution and triggered procedures.

3. AGENTS_VNEXT.md
   - Minimal project entry router.
   - Loads canonical governance references.

## Migration constraints

- V4 remains active until qualification succeeds.
- No silent governance switch.
- Historical documents cannot override the active manifest.
- Runtime details remain separated from governance principles.
