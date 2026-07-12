# V0-01 Scope

## Preserved completed implementation

The following implementation sequence is frozen and unchanged:

```text
V0-01A0 BRONZE_AND_OFFLINE_REPLAY
V0-01A1 SOURCE_ENVELOPE_TRANSPORT_ENTRY_CONTRACT_FREEZE
V0-01A2 NO_NETWORK_PUBLIC_OBSERVATION_INGRESS_CONTRACT
V0-01A3 PUBLIC_READONLY_TRANSPORT_PREFLIGHT_CONTRACT
V0-01A4 OFFICIAL_RATE_LIMIT_AUTHORITY_FREEZE
V0-01A5 OFFLINE_CANDLE_PAYLOAD_EXTRACTION_CONTRACT
V0-01A6 OFFLINE_CANDLE_CROSS_SOURCE_RECONCILIATION_CONTRACT
```

A0 remains the offline immutable Bronze and replay authority. A1 through A4
remain the source, envelope, public read-only transport-entry, preflight, and
official rate-limit authorities. A5 remains the offline exact candle extraction
authority. A6 remains the offline exact WebSocket/Info reconciliation authority.
No code, contract, generated V0 schema, test, dependency, or CI behavior from
A0 through A6 is modified by the Fast Launch governance freeze.

```text
LAST_COMPLETED_IMPLEMENTATION: V0-01A6-OFFLINE-CANDLE-CROSS-SOURCE-RECONCILIATION-CONTRACT
LAST_COMPLETED_IMPLEMENTATION_PR: 11
LAST_POLICY_STATE_PR: 12
```

## Current program authority

```text
PROGRAM: V0-FAST-LAUNCH
FIRST_RELEASE: V0-R0
ACTIVE_MILESTONE: V0-FLP0-PILOT-AND-LONG-TERM-ROADMAP-AUTHORITY-FREEZE
ACTIVE_IMPLEMENTATION: NONE
ACTIVE_WRITE_LEASE: NONE
NEXT_GATE: V0-FLP1-OPERATOR-ASSIST-PILOT-SCOPE-FREEZE
```

The prior generic A7-only next step is superseded by the explicit Fast Launch
program. This does not retroactively authorize A7, FLP1, or any runtime.

## V0-R0 first-release boundary

R0 is an Operator Assist Pilot for ETH and one active strategy,
`ETH-LDAR-v0.1`.

```text
EXECUTION_MODE: MANUAL_EXECUTION_WITH_SYSTEM_ASSISTANCE
AUTOMATIC_EXCHANGE_WRITE: PROHIBITED
AI_ROLE: EXPLANATION_AND_CHECKLIST_ONLY
ALL_VALID_SIGNALS_VISIBLE: YES
POST_LAUNCH_LEARNING_LOOP: MANDATORY
```

The target decision flow is:

```text
real-time public read-only data
-> DataQualityState
-> ETH-LDAR-v0.1
-> LONG / SHORT / WAIT
-> deterministic risk sizing
-> TradePlan
-> FAST / STANDARD signal card
-> TAKEN / SKIPPED / REJECTED
-> manual Hyperliquid execution
-> read-only order/fill observation
-> plan/outcome matching
-> replay
-> findings and versioned iteration
```

This flow is a frozen product requirement, not present runtime authority.

## Required R0 capability set

R0 requires ETH 5m and 15m candles, mark/mid reference, ETH OI, Funding,
timestamps, freshness, gap/conflict state, heartbeat, reconnect, bounded
backoff, replay, WATCH, PREPARE, TRIGGERED_FAST, TRIGGERED_STANDARD, EXPIRED,
LONG/SHORT/WAIT, entry zone, maximum entry boundary, invalidation, fixed stop,
TP1, TP2, exact size, notional, risk amount, risk percent, expiry, compact
signal card, copy controls, TAKEN/SKIPPED/REJECTED, read-only account/order/fill
observation, automatic system-side records, CSV/XLSX fallback import, and a
minimal pilot review.

R0 forbids API wallets, private keys, signing, nonce authority, exchange writes,
automatic entry/cancel/SL/TP, transfers, withdrawals, multiple active strategies
or assets, automatic strategy routing, online learning, and automatic production
parameter mutation.

## Signal-speed policy

FAST and STANDARD are speed classes of `ETH-LDAR-v0.1`.

```text
WATCH
-> PREPARE
-> TRIGGERED_FAST / TRIGGERED_STANDARD
-> EXECUTED / SKIPPED / EXPIRED
```

All valid FAST signals must alert and display `FAST / OPTIONAL`, short expiry,
maximum entry boundary, and `DO NOT CHASE`. A missed FAST trade is not
automatically a strategy failure; actionability is measured.

All valid STANDARD signals must alert with a longer expiry and allow normal human
review and order entry. Accepted STANDARD signals are expected to be executed.

The minimum pattern set is:

- `LIQUIDITY_SWEEP_RECLAIM_FAST`;
- `LIQUIDITY_SWEEP_PULLBACK_STANDARD`.

## Long-term roadmap

The final direction is unchanged:

```text
FL1 TRUSTED_DATA_RUNTIME
FL2 SIGNAL_AND_RISK_ENGINE
FL3 HUMAN_REVIEW_SURFACE
FL4 HUMAN_CONFIRMED_EXECUTION
```

R0 delivers the minimum vertical subset of FL1 through FL3. R1 is
human-confirmed automated execution and requires a dedicated limited-capital
subaccount, dedicated API wallet, secret isolation, official SDK signing, nonce
authority, immutable hashed OrderIntent, cloid idempotency, expiry,
pre-submit revalidation, ALO/post-only, bounded-slippage IOC, submit/cancel,
partial-fill handling, actual-fill sizing, mandatory automatic stop, fixed
multi-stage automatic TP, reduce-only protection, protection verification,
`POSITION_UNPROTECTED` emergency handling, kill switch, dead-man protection,
audit, Testnet, shadow, limited-capital Mainnet canary, and separate Mainnet
authorization.

Autonomous entry remains prohibited. Future automated execution requires human
confirmation of the complete TradePlan and OrderIntent.

## Authorization state

```text
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
```

No product requirement in this document overrides those false gates.
