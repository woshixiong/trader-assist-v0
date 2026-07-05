## Purpose

Establish the contract-first Trader Assist V0 repository baseline for TraderOS Issue #56.

## Scope

- project/agent rules and threat model;
- canonical data-health enum and transition table;
- Bronze/Silver/Gold event envelopes;
- strategy candidate and promotion contracts;
- AI recommendation, proposal, human decision, order package and execution-permit contracts;
- evidence bundle and seed provenance contracts;
- generated JSON schemas with drift check;
- compile, lint, type, tests and secret scan CI.

## Boundaries

- no historical runtime source copied into `src/`;
- no data collector or exchange adapter;
- no credential, wallet, signing or order submission;
- no Testnet/Mainnet enablement;
- no strategy implementation or risk sizing;
- no change to TraderOS Issue #47.

## Validation

- fresh editable install succeeded;
- compile succeeded;
- schema drift check succeeded;
- secret scan clean;
- Ruff passed;
- Mypy passed for 12 source files;
- Pytest: 18 passed.

## Review focus

1. Canonical health enum and legal transitions.
2. Hash/ID/time bindings across candidate, proposal, decision, promotion and permit.
3. Fail-closed Mainnet permit requirements.
4. No hidden runtime authority or historical source import.
5. Provenance manifest accuracy and future port-by-contract boundary.
