# V0 Authority Boundary

```text
Validated source evidence
-> normalization and health
-> deterministic features/regime
-> strategy candidate
-> deterministic risk sizing and TradePlan
-> AI explanation (advisory)
-> human decision
-> manual execution in R0
-> read-only order/fill observation and matching
-> execution permit (future deterministic service)
-> execution gateway (future, separately reviewed G4 authority)
```

V0-00 defines data shapes only. It creates no runtime authority. A0 through A6 remain the current implemented offline evidence authority. The Fast Launch program freezes later product and governance direction but does not itself implement runtime.

## Governance levels

- G0: noncritical documentation and presentation.
- G1: metrics, AI explanation, and backtest presentation.
- G2: live public data, Canonical Market State, and strategy.
- G3: risk calculation, TradePlan, human decision, account/order/fill observation, and matching.
- G4: credentials, signing, nonce, exchange write, SL/TP, and actual position mutation.

FLP1 is at least G3. FL4 requires a separate G4 execution implementation and independent security review.

## R0 authority boundary

After the Capture Now T1 amendment, active `V0-R0` is `CAPTURE_ONLY`.
It fixes ETH as the first-launch primary asset, `active_strategy_count = 0`,
`capture_contracts_authorized = true`, and false network runtime, strategy
runtime, signal recommendation, risk sizing, TradePlan, account runtime, and
exchange execution authority.

Release authority is `R0: CAPTURE_ONLY`, `R1: ETH_OPERATOR_ASSIST`,
`T1: CONTRACT_SCHEMA_GOVERNANCE_ONLY`, and
`T2: SEPARATE_FUTURE_ETH_PUBLIC_CAPTURE_RUNTIME`.

`RAW_PUBLIC_EVIDENCE_PLANE` remains the A0-A6 raw evidence authority.
`CAPTURE_AUTHORITY_PLANE` is separate contract/schema authority for Capture
records and does not connect to RawEvent, Bronze, ingress, replay runtime,
strategy, AI, risk, dashboard, account observation, Testnet/Mainnet execution,
or exchange writes.

## Future R1 authority boundary

R1 is the future ETH-only Operator Assist Pilot using `ETH-LDAR-v0.1` or a
separately approved future ETH strategy. It targets trusted data, deterministic
`LONG`/`SHORT`/`WAIT`, deterministic risk, an immutable TradePlan,
FAST/STANDARD signal cards, human decision capture, manual execution,
read-only matching, replay, and findings. R1 is not implemented and not
authorized in T1.

FAST and STANDARD are speed classes of one strategy. Every valid signal is visible. FAST is optional, short-lived, maximum-entry-bounded, and marked `DO NOT CHASE`. STANDARD is intended for normal human review and execution.

R0 creates no API-wallet, key, signing, nonce, exchange-write, automatic entry/cancel/SL/TP, transfer, withdrawal, autonomous entry, online-learning, or automatic-production-mutation authority.

## Future human-confirmed execution boundary

Human-confirmed automated execution is deferred under
`future_human_confirmed_execution`, has no assigned release, and may execute only
after the human confirms the complete TradePlan and immutable OrderIntent. It
requires separate limited-capital account isolation, official SDK signing, nonce
and idempotency authority, pre-submit revalidation, fill-aware automatic
protection, kill switch, dead-man protection, audit, Testnet, shadow,
limited-capital canary, and Mainnet authorization.

Autonomous entry remains prohibited.

## Non-authorities

- AI cannot approve risk, create a permit, access credentials, or call an exchange.
- Strategy candidates cannot create orders.
- The dashboard cannot calculate authoritative risk or sign commands.
- Historical V3.5 code is not authority.
- Evidence imported into TraderOS is evidence, not an automatic promotion decision.
- Product requirements do not override false runtime authorization gates.

## Fail-closed rule

Mandatory data not `LIVE`, invalid correlation, stale or conflicting data, expired signal, entry beyond the maximum boundary, expired/revoked promotion, changed TradePlan/proposal/order package, expired permit, unresolved account/order state, or unverified position protection blocks new risk.

## Current authorization

```text
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
CONFLICT_STATE: OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED
SUPERSESSION_STATE: EFFECTIVE_VARIANT_UNDETERMINED
```
