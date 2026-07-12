# V0 Authority Boundary

## Decision and execution chain

```text
validated source evidence
-> normalized data products and DataQualityState
-> deterministic features
-> versioned strategy
-> LONG / SHORT / WAIT
-> deterministic risk sizing
-> immutable TradePlan
-> AI explanation and checklist
-> human decision
-> manual execution in R0
-> read-only order/fill observation
-> plan/outcome matching
```

R0 creates no exchange-write authority. AI cannot approve risk, mutate a
TradePlan, access credentials, sign, create a nonce, submit/cancel an order, or
change a position.

## Governance levels

- G0: noncritical documentation and presentation.
- G1: metrics, AI explanation, and backtest presentation.
- G2: live public data, Canonical Market State, and strategy.
- G3: risk calculation, TradePlan, human decision, account/order/fill
  observation, and matching.
- G4: credentials, signing, nonce, exchange write, SL/TP, and actual position
  mutation.

FLP1 is at least G3. FL4 requires a separate G4 implementation and independent
security review.

## R0 authority

The R0 Operator Assist Pilot may eventually provide trusted data, deterministic
signals and risk, signal cards, human-decision capture, read-only matching,
replay, and learning findings after separate implementation authorization.

It may not provide API-wallet custody, signing, nonce authority, exchange writes,
automatic entry/cancel/SL/TP, transfers, withdrawals, autonomous entry, online
learning, or automatic production mutation.

## R1 authority

R1 may execute only after a human confirms the complete TradePlan and immutable
OrderIntent. It requires separate limited-capital account isolation, official SDK
signing, nonce and idempotency authority, pre-submit revalidation, fill-aware
automatic protection, kill switch, dead-man protection, audit, Testnet, shadow,
limited-capital canary, and Mainnet authorization.

Autonomous entry remains prohibited.

## Fail-closed rule

Mandatory data not live, invalid correlation, stale or conflicting state,
expired signal, entry beyond the maximum boundary, changed TradePlan or
OrderIntent, expired/revoked authorization, unresolved account/order state, or
unverified position protection blocks new risk.

## Current authorization

```text
LIVE_TRANSPORT_AUTHORIZED: FALSE
ACCOUNT_READONLY_RUNTIME_AUTHORIZED: FALSE
TESTNET_EXECUTION_AUTHORIZED: FALSE
MAINNET_EXECUTION_AUTHORIZED: FALSE
FLP1_IMPLEMENTATION_AUTHORIZED: FALSE
```
