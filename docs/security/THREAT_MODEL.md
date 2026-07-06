# V0 Threat Model

## Assets

- source and normalized evidence;
- account/position/order state;
- proposal and human-decision integrity;
- future API-wallet credentials;
- execution permit uniqueness;
- append-only audit evidence;
- strategy-promotion allowlists.

## Trust boundaries

1. external market/context sources to collectors;
2. collectors to normalization/health;
3. deterministic strategy output to AI explanation;
4. server to browser/human session;
5. approval service to future execution gateway;
6. future gateway to venue;
7. V0 evidence export to TraderOS import.

## Principal threats and controls

| Threat | Control floor |
|---|---|
| Stale, gapped, spoofed, or future-skewed data | Canonical health state machine, source provenance, hashes, mandatory-feed `LIVE` gate |
| Prompt injection or hallucinated evidence | Typed AI input/output, immutable evidence IDs, AI is advisory and cannot authorize |
| Proposal or order-package tampering | SHA-256 binding across proposal, decision, permit, account snapshot, and promotion record |
| Approval replay | Single-use permit contract, expiry, exact subject/action binding; runtime store deferred |
| Duplicate/ambiguous venue outcome | Idempotent client identity and reconciliation required before execution implementation |
| Partial-fill over-protection | Future protection quantity derived only from observed fills |
| Credential theft | No credentials in V0-00; future isolated API wallet, secrets manager, least privilege, revocation |
| Strategy auto-promotion | Versioned promotion record, reviewer/evidence binding, environment allowlist |
| Evidence alteration | Append-only semantics, file hashes, manifest, corrections as new events |
| Supply-chain compromise | Minimal dependencies, pinned major ranges, CI, dependency review before deployment |
| Secret leakage in source/logs | `.gitignore`, custom secret scan, no production fixtures or raw headers |

## V0-00 residual risk

Contracts do not prove future service correctness. Permit atomic consumption, venue reconciliation, immutable persistence, session security, and credential operations require separate implementation and independent review.
