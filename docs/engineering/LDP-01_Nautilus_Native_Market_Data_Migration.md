# LDP-01 Nautilus Native Market Data Migration

## Decision

Migrate market-data freshness handling to Nautilus native market data contracts.

The custom MarketTruth validation layer is deprecated as an active runtime dependency.

Authoritative market-data flow:

```
Exchange
  -> Nautilus Adapter
  -> Nautilus DataEngine
  -> Native Market Events
      -> Strategy
      -> Capture / Evidence / Replay
```

## Scope

### Remove from active runtime

- Custom MarketTruth validation authority
- Custom freshness decision layer
- Custom market-data truth state machine
- Duplicate recovery logic owned by Nautilus

### Preserve

- Capture layer
- Evidence storage
- Replay capability
- Strategy logic
- Business lifecycle data

The migration removes duplicated infrastructure responsibility, not Trader Assist business functionality.

## Archive Policy

Deprecated implementation must not be deleted without preservation.

Archive should contain:

- deprecated source code
- related tests
- design rationale
- migration notes

Archived code must not remain in active import paths.

## Migration Principles

1. Nautilus owns market-data correctness and lifecycle.
2. Trader Assist owns evidence, decision context, and business workflows.
3. Freshness remains observable, but not reimplemented as a truth authority.

Recommended observability fields:

- ts_event
- ts_init
- event_age_ms
- feed status
- sequence metadata

## Migration Phases

### Phase 1: Impact Analysis

Classify existing MarketTruth-related code:

- Delete/archive
- Keep
- Adapt

### Phase 2: Interface Migration

Move consumers from custom MarketTruth objects to Nautilus native event flow.

### Phase 3: Archive Deprecated Code

Preserve historical implementation outside runtime paths.

### Phase 4: Validation

Validate:

- market-data contract
- strategy integration
- capture/storage
- replay
- reconnect/recovery behavior
- regression coverage

## Future Compatibility

The design must avoid dependency on Nautilus private internals.

Use stable public contracts to preserve future Nautilus version upgrade paths.
