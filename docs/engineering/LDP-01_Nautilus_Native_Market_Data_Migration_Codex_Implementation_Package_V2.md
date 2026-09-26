# LDP-01 Nautilus Native Market Data Migration

## Codex Implementation Package V2

Status: Boundary-refrozen implementation package

## Purpose

This package supersedes the assumptions from V1 after Codex Phase 1 exact-base analysis identified that the frozen implementation base does not contain an active MarketTruth runtime implementation.

The goal remains unchanged:

Move duplicated market-data infrastructure responsibility back to Nautilus native market-data contracts while preserving Trader Assist business evidence capabilities.

This package is an implementation contract, not a redesign authorization.

---

## Execution Route

Route C — Large coherent multi-step coding package.

---

## Canonical Base

Base SHA:

`f17d436b222061ab2229d83f09f743182353fe11`

Previous artifacts:

- PR #243 — migration scope
- PR #247 — implementation package V1
- PR #248 — ownership boundary refreeze

---

# Ownership Matrix

| Component | Classification | Decision |
|---|---|---|
| MarketTruth runtime | Not present on frozen base | Do not assume deletion target exists |
| CausalAdmissionLedger | Boundary review required | Do not remove until ownership is frozen |
| continuity_state | Boundary review required | Determine infrastructure vs evidence responsibility |
| admission timestamps | Preserve pending decision | Required for audit/evidence evaluation |
| CaptureSession | Preserve | Business evidence capture capability |
| Evidence storage | Preserve | Trader Assist business capability |
| Replay | Preserve | Historical validation capability |
| Nautilus native market events | Authoritative | Market data contract owner |

---

# Required Decisions Before Implementation

Engineering Control must freeze:

1. Which responsibilities belong to Nautilus native contracts.
2. Which responsibilities remain Trader Assist evidence semantics.
3. Which continuity/recovery states are infrastructure versus audit data.

No code deletion is authorized before these decisions are frozen.

---

# Frozen Migration Principles

REMOVE / ARCHIVE only when ownership is confirmed:

- duplicated market-data correctness authority;
- duplicated freshness decision authority;
- duplicated recovery ownership.

KEEP:

- Capture;
- Evidence;
- Replay;
- Business lifecycle;
- Auditability;
- Strategy compatibility.

---

# Implementation Planning Requirements

Before mutation Codex must provide:

## File Contract

MODIFY:

- To be determined after ownership freeze.

ARCHIVE:

- Only confirmed deprecated implementations.

DELETE:

- Only confirmed obsolete runtime paths.

PRESERVE:

- evidence and replay related capabilities.

DO NOT TOUCH:

- strategy;
- scanner;
- universe configuration;
- deployment;
- production state.

---

# Validation Gates

Required validation:

## Market Data Contract

- timestamps;
- event ordering;
- instrument identity;
- freshness observability.

## Runtime

- live event flow;
- reconnect;
- recovery;
- capture.

## Data

- storage compatibility;
- replay.

## Regression

- scanner unchanged;
- strategy unchanged;
- lifecycle unchanged.

---

# Rollback Boundary

Rollback must remain possible to the clean base commit.

Deprecated artifacts must remain recoverable but must not remain active runtime dependencies.

---

# Explicit Exclusions

Not included:

- strategy changes;
- scanner changes;
- universe expansion;
- unrelated TODO items;
- deployment changes;
- production mutations.
