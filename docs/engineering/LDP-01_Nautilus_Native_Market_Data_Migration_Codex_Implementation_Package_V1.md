# LDP-01 Nautilus Native Market Data Migration
## Codex Implementation Package V1

Status: Implementation package candidate
Execution route: C — Large coherent multi-step coding package
Base SHA: f17d436b222061ab2229d83f09f743182353fe11

## 1. Objective

Remove duplicated market-data infrastructure responsibility from Trader Assist by migrating active market-data truth ownership to Nautilus native market-data contracts.

The migration preserves Trader Assist business capabilities:

- capture
- evidence storage
- replay
- business lifecycle context
- strategy compatibility

## 2. Frozen Scope

### Remove / Archive

- custom MarketTruth validation authority
- custom freshness decision authority
- duplicated market-data truth state
- duplicated recovery ownership

### Keep

- Capture layer
- Evidence storage
- Replay capability
- Strategy and business lifecycle behavior

### Adapt

- consumers currently coupled to MarketTruth
- interfaces between Nautilus events and Trader Assist consumers

## 3. Explicit Exclusions

Not included:

- strategy changes
- scanner changes
- universe expansion
- unrelated TODO items
- deployment changes
- production runtime mutation

## 4. Implementation Sequence

1. Inventory active MarketTruth dependencies.
2. Classify dependencies as remove, archive, adapt, or preserve.
3. Migrate consumers to Nautilus native contracts.
4. Archive deprecated implementation outside runtime import paths.
5. Remove obsolete active imports and ownership paths.
6. Update tests and validation coverage.
7. Execute regression validation.

## 5. File Change Contract

Before implementation, Codex must produce an exact changed-file plan.

Required categories:

- MODIFY
- DELETE
- ARCHIVE
- PRESERVE
- DO NOT TOUCH

No scope expansion without returning to Engineering Control.

## 6. Nautilus Compatibility Rules

Required:

- use public Nautilus contracts only
- avoid private framework internals
- preserve future Nautilus upgrade portability

Forbidden:

- recreate Nautilus market-data truth ownership
- introduce another truth layer
- introduce custom freshness authority

## 7. Validation Gates

### Market Data Contract

Validate:

- event timestamps
- ordering assumptions
- instrument identity
- freshness observability

### Runtime Flow

Validate:

- live event flow
- reconnect behavior
- recovery behavior
- capture path

### Data

Validate:

- storage compatibility
- replay capability

### Regression

Validate:

- scanner unchanged
- strategy unchanged
- lifecycle unchanged

## 8. Rollback Boundary

Implementation must preserve a clean rollback point before removing active MarketTruth ownership.

Archive artifacts must remain recoverable but must not participate in runtime execution.

## 9. Acceptance Criteria

PASS requires:

- no active duplicated market-data truth authority
- no active MarketTruth runtime dependency
- preserved evidence and replay capability
- deterministic validation commands documented
- regression coverage passes

## 10. Codex Execution Notes

This package is an implementation contract, not permission to redesign architecture.

Codex must follow the frozen boundary and escalate unresolved architecture decisions.