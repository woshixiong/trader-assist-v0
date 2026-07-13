# Pilot Learning Loop

## Required evidence chain

```text
Data Snapshot
-> Signal
-> TradePlan
-> Human Decision
-> Actual Order/Fill Observation
-> Outcome
-> Deviation Analysis
-> Finding
-> Versioned Improvement
```

Every record must retain stable IDs and timestamps sufficient to reconstruct the
decision and match planned versus observed outcomes without silently guessing.

## Required measurements

The pilot measures data staleness, disconnect/reconnect, gaps/conflicts, signal
and alert latency, FAST/STANDARD counts, FAST execution and expiry-before-action
rates, STANDARD execution rate, TAKEN/SKIPPED/REJECTED decisions, decision
latency, planned versus actual entry and size, fees, realized PnL, matching
confidence, incidents, MFE/MAE, R multiple, entry lateness, and WAIT quality.

## Finding taxonomy

Categories are DATA, STRATEGY, RISK, AI_EXPLANATION, UI, HUMAN_DECISION,
MANUAL_EXECUTION, ACCOUNT_OBSERVATION, SYSTEM_RUNTIME, and DEPLOYMENT.

Severity is P0, P1, P2, or P3.

## Improvement gate

Online learning and automatic production mutation are prohibited. Every finding
must become an explicit hypothesis. A change requires a new version, tests,
replay, shadow evaluation, independent review, and release authorization.

A missed FAST trade is not automatically a strategy failure. Analysis must
separate signal validity, operator actionability, human decision, manual
execution, data quality, and system latency.

## Capture Now T1

Active R0 is `CAPTURE_ONLY` and does not authorize the pilot learning runtime,
outcome adjudication, PnL, win rate, Sharpe, MFE/MAE, R multiple, promotion
judgment, strategy runtime, risk sizing, TradePlan, account observation, or
exchange execution. Those Operator Assist and learning-loop semantics are
preserved only as future `R1: ETH_OPERATOR_ASSIST` and remain not implemented in
`T1: CONTRACT_SCHEMA_GOVERNANCE_ONLY`. Runtime capture is
`T2: SEPARATE_FUTURE_ETH_PUBLIC_CAPTURE_RUNTIME`.

Capture replay reports are integrity reports only. They verify Capture-plane
manifest/checkpoint/replay contracts and must not become performance or
promotion evidence.
