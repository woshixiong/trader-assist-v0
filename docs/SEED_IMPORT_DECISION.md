# Canonical Seed Import Decision

## Decision

No historical runtime source file is imported into `src/` during the initial V0-00 contract bootstrap.

The V3.5 implementation remains the sole runtime `SEED`, not authority. Selected files are recorded in `archive/manifests/seed_provenance.json` as `SEED_NOT_IMPORTED` or `REFERENCE_ONLY`.

## Rationale

Contracts must be reviewed before old behavior is ported. The historical implementation contains useful concepts, but also Testnet adapters, mutable persistence patterns, old data-state vocabulary, implicit thresholds, and execution assumptions that cannot enter the new authority path by copying files.

## Candidate future ports

- pure data-health assessment concepts;
- candidate envelope concepts;
- one-time approval concepts;
- explicit no-order guard concepts.

Each future port requires a bounded issue/PR recording retained behavior, removed behavior, new contract mapping, tests, and security impact.

## Explicitly excluded from V0-00

- Hyperliquid Testnet adapter;
- execution API/ticket executor;
- old risk engine and position-sizing authority;
- mutable journals and reconciliation implementation;
- strategy scorers and signal loops;
- configuration containing execution-mode switches.
