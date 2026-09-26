# LDP-01 Nautilus Native Market Data Migration Boundary Refreeze V2

## Purpose

This document refines the LDP-01 implementation boundary after Route C Codex Phase 1 discovered that the frozen GitHub base does not contain an active MarketTruth runtime implementation.

This is a boundary clarification, not a redesign.

## Blocking Discovery

The previous implementation package assumed an active MarketTruth removal path.

Exact-base validation found:

- no active MarketTruth class/module/runtime import on the frozen base;
- existing Trader Assist ownership around continuity, admission timestamps, capture recovery, and evidence semantics.

Therefore the implementation boundary must be re-frozen before code mutation.

## Open Ownership Questions

Engineering Control must classify:

| Component | Current Role | Decision Required |
|---|---|---|
| CausalAdmissionLedger | continuity/admission state | Infrastructure duplication or business evidence? |
| continuity_state | ordering/recovery state | Nautilus-owned or Trader Assist evidence? |
| admission timestamps | freshness observability | Preserve or replace? |
| CaptureSession recovery | replay/evidence continuity | Preserve boundary |

## Frozen Principles

REMOVE / ARCHIVE only when confirmed:

- duplicated market-data correctness authority;
- duplicated freshness decision authority;
- duplicated recovery ownership.

PRESERVE:

- Capture;
- Evidence storage;
- Replay;
- Business lifecycle;
- Auditability.

## Implementation Route

Route C remains correct after boundary clarification.

Execution must not begin until:

1. Ownership matrix is approved.
2. Exact file allowlist is frozen.
3. Delete/archive/keep/adapt classification is updated.
4. Validation gates are updated.

## Explicit Non-Goals

Not included:

- strategy changes;
- scanner changes;
- universe expansion;
- deployment changes;
- new market truth framework.

## Next Required Artifact

A revised LDP-01 Codex Implementation Package must reference this boundary decision before implementation.
