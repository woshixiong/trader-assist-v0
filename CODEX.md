# Executor Instructions

## Repository state

```text
PROGRAM: V0-FAST-LAUNCH
TASK_ID: V0-T2-ETH-PUBLIC-CAPTURE-RUNTIME
MAIN_BASE_SHA: 16963297e0ce27ed3919f52e1e536ff730f5a5b9
BASE_PROVENANCE: origin/main merge of PR #16
LAST_COMPLETED_IMPLEMENTATION: V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT
LAST_COMPLETED_IMPLEMENTATION_PR: 11
LAST_POLICY_STATE_PR: 15
ACTIVE_IMPLEMENTATION: V0-T2-ETH-PUBLIC-CAPTURE-RUNTIME-CANDIDATE
ACTIVE_WRITE_LEASE: V0-T2-ETH-PUBLIC-CAPTURE-RUNTIME-WRITE-LEASE-1
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
NEXT_GATE: V0-FLP1-OPERATOR-ASSIST-PILOT-SCOPE-FREEZE
```

## Current bounded implementation task

`V0-T2-ETH-PUBLIC-CAPTURE-RUNTIME`

A6 remains the last completed offline evidence implementation. T1 remains the
historical Capture contract/schema authority. This branch is the bounded T2
implementation candidate under write lease
`V0-T2-ETH-PUBLIC-CAPTURE-RUNTIME-WRITE-LEASE-1`, based exactly on
`16963297e0ce27ed3919f52e1e536ff730f5a5b9`.

The fixed ETH public Capture runtime remains default-off. Implementation and
tests make no real endpoint connection and create no real permit. A controlled
Capture launch requires a later explicit operation with separate project-control
approval and one externally supplied single-use permit. T2 does not implement an
AI signal or claim the user-facing First Launch.

## Allowed files

- `CODEX.md`
- `docs/V0_FLP0_CAPTURE_NOW_AUTHORITY.md`
- `src/trader_assist_v0/data/ingress.py`
- `src/trader_assist_v0/runtime/__init__.py`
- `src/trader_assist_v0/runtime/eth_public_capture.py`
- `scripts/run_eth_public_capture.py`
- `tests/test_v0_t2_eth_public_capture_runtime.py`
- `pyproject.toml`
- `requirements-runtime.lock`
- `requirements-dev.lock`

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

## Fast Launch frozen authority

`V0-R0` is the ETH-only `V0-FLP1-DECISION-TO-OUTCOME-OPERATOR-ASSIST-PILOT` with one active strategy, `ETH-LDAR-v0.1`.

FAST and STANDARD are signal-speed classes of that one strategy. Every valid signal is visible. FAST is optional, short-lived, maximum-entry-bounded, and marked `DO NOT CHASE`. STANDARD permits normal human review and expected execution after acceptance. Execution remains manual. AI is explanation and checklist only.

The long-term capability sequence remains FL1 trusted data, FL2 signal and risk, FL3 human review, and FL4 human-confirmed execution. R1 and FL4 require separate G4 implementation, security review, Testnet, shadow, limited-capital canary, and Mainnet authorization. Autonomous entry remains prohibited.

## Forbidden

- modifications outside the exact T2 allowlist above;
- real endpoint connection, DNS, socket creation, or a real permit during implementation;
- HTTP, Info `candleSnapshot`, polling, automatic reconnect/retry/restart,
  backfill, proxy use, or library-managed WebSocket Ping keepalive;
- payload parsing or reading payload bytes from `payload_ref` or any filesystem path;
- Bronze or manifest writes, database or cloud storage;
- numeric rate-limit values or a transition away from `UNRESOLVED_OFFICIAL_LIMIT`;
- credentials, account addresses, wallets, signing, nonces, exchange writes, order mutation, Testnet/Mainnet execution configuration;
- tolerance, latest-wins, revision ordering, finality inference, source priority, or canonical winner selection;
- `NormalizedEventV0` emission, Silver normalization/persistence, strategy runtime, AI recommendation runtime, risk runtime, dashboards, or later V0 runtime slices;
- raw operational payloads, logs, caches, databases, source archives, private/user/account data, secrets, or unredacted live observations in Git;
- modifications to `woshixiong/trade-os`;
- Mark Ready, merge, branch deletion, or later-phase execution without separate authorization.

## Future bounded-task checks

Every future slice requires an independent exact-main scope freeze, explicit write lease and file allowlist, applicable local checks, exact-head CI, external independent review, and separate finalization authorization. Never report a check as passed unless it was executed and observed.
