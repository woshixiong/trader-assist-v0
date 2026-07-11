# Executor Instructions

## Repository state

```text
LAST_COMPLETED_SLICE: V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT
LAST_MERGED_PR: #11
ACTIVE_IMPLEMENTATION_SLICE: NONE
ACTIVE_IMPLEMENTATION_WRITE_LEASE: NONE
A7_SCOPE_FROZEN: NO
A7_IMPLEMENTATION_AUTHORIZED: NO
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
```

## Current bounded implementation task

`NONE`

A6 is the last completed slice and was merged via PR #11. There is no active bounded implementation task or implementation write lease. Do not modify repository files without a new exact write lease and file allowlist. Codex must not choose, name, or implement A7 scope; the next gate is independent read-only A7 scope-freeze planning.

## Allowed files

- None. A future bounded implementation task must provide its own exact write lease and file allowlist.

## Last completed A6 behavior

- require exact `CandlePayloadExtractionV0` inputs with frozen WS and Info roles;
- independently revalidate both A5 extraction hashes, nested candle authorities, endpoint, operation, and envelope shape;
- require identical source, coin, and interval identities;
- use each A5 `candle_logical_key` as the sole cross-source identity;
- compare the logical-key union in `(open_time_ms, candle_logical_key)` order;
- compare only close time, OHLC, base volume, and trade count in the frozen field order;
- embed both complete A5 extraction authorities while retaining matching scalar event/hash authority;
- derive comparisons, source authority, counts, identity, and the report hash only from those two exact extractions through one deterministic contract-layer authority;
- reconstruct the complete logical-key union during every report validation and reject coherently rehashed omissions, injections, substitutions, or membership changes;
- emit only `MATCH`, `CONFLICT`, `WS_ONLY`, and `INFO_ONLY` with exact counts and a domain-separated report hash covering both complete extractions;
- use `AuthorityClass.model_validate_json(...)` as the sole A6 raw JSON boundary: its canonical precheck runs before Pydantic and requires input bytes to equal `canonical_json_bytes(authority)` exactly;
- validate only those already-approved canonical bytes with a one-shot isolated Pydantic JSON-mode validator, preserving native Pydantic JSON semantics for `strict=None`, `strict=False`, and `strict=True`;
- keep the permissive copied schema, validator, walker, and closures inside the isolated call on both success and failure: none may escape through a return value, exception, traceback frame, context, or cause;
- convert one-shot validation failures to new sanitized errors built only from neutral non-executable data after clearing and detaching the original exception graph, validator, schema, and sensitive frames;
- expose no persistent caller-settable capability that can authorize class/core JSON validation, and reject duplicate object keys at every depth, `-0`, float/exponent/non-finite tokens, non-UTF-8/BOM input, alternate encodings, truncation, trailing material, and every other noncanonical raw representation before Pydantic validation;
- support decoded Python `model_validate`, base-class `model_validate`, `TypeAdapter.validate_python`, and core `validate_python` paths only as authentication of the current decoded representation, without claiming raw-wire provenance;
- keep inherited/core JSON, all string-validation, and all partial-validation paths fail closed; they are not alternative raw authority boundaries;
- keep generated Schema root WS/Info extraction roles, comparison role/status, required embedded A5 fields, integer-difference value kinds, and portable absolute-end patterns in parity with runtime;
- keep Schema validation structural and JSON-Schema-expressible only; runtime remains authoritative for hashes, exact A5 authority, membership, ordering, counts, differences, and complete logical-key union proof;
- allow empty/empty inputs without sentinel/default evidence;
- keep tolerance, source priority, latest-wins, finality, revisions, canonical winner, normalization, and Silver promotion out of scope.

## Forbidden

- modifications to A5 contracts/extractor, source catalog code/documentation, `events.py`, `ingress.py`, `bronze.py`, or `replay.py`;
- modifications to existing tests, existing schemas, fixtures, dependencies, lockfiles, `pyproject.toml`, or CI workflows;
- HTTP or WebSocket clients, sockets, DNS, async runtime, event loop, live endpoint connection, polling, reconnect, heartbeat, health, backfill, REST request execution, or soak runtime;
- payload parsing or reading payload bytes from `payload_ref` or any filesystem path;
- Bronze or manifest writes, database or cloud storage;
- numeric rate-limit values or a transition away from `UNRESOLVED_OFFICIAL_LIMIT`;
- credentials, account addresses, wallets, signing, nonces, exchange writes, order mutation, Testnet/Mainnet execution configuration;
- tolerance, latest-wins, revision ordering, finality inference, source priority, or canonical winner selection;
- `NormalizedEventV0` emission, Silver normalization/persistence, strategy candidates, AI recommendations, risk sizing, dashboards, or later V0 slices;
- raw operational payloads, logs, caches, databases, source archives, private/user/account data, secrets, or unredacted live observations in Git;
- modifications to `woshixiong/trade-os`.

## Future bounded-task checks

Every future slice requires an independent exact-main scope freeze, explicit write lease and file allowlist, applicable local checks, exact-head CI, external independent review, and separate finalization authorization. Never report a check as passed unless it was executed and observed.
