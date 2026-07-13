# V0 FLP0 Capture Now Authority

## Authority Snapshot

```text
TASK_ID: V0-FLP1B0B-CAPTURE-NOW-AUTHORITY-AMENDMENT
STATE_BASE_SHA: 78d2d37bfe5a4f3f1d382a2a96e57896ae9676ae
R0: CAPTURE_ONLY
R1: ETH_OPERATOR_ASSIST
FIRST_LAUNCH_PRIMARY_ASSET: ETH
BTC_FIRST_LAUNCH_REQUIREMENT: NONE
BTC_FIRST_LAUNCH_BLOCKER: NO
T1: CONTRACT_SCHEMA_GOVERNANCE_ONLY
T2: SEPARATE_FUTURE_ETH_PUBLIC_CAPTURE_RUNTIME
NEXT_GATE: V0-FLP1B0B-EXTERNAL-INDEPENDENT-REVIEW
```

T1 freezes the Capture Now authority contract, generated JSON Schema, governance
state, and documentation. It starts no runtime, opens no socket, performs no DNS
or endpoint connection, writes no database or filesystem evidence, and grants no
strategy, risk, account, credential, or exchange execution authority.

## Plane Boundary

`RAW_PUBLIC_EVIDENCE_PLANE` remains the A0-A6 offline raw-evidence authority:
canonical JSON, SHA-256, `RawEventV0` identity, content-addressed evidence,
manifest, checkpoint, replay, and root-wide single-writer rules.

`CAPTURE_AUTHORITY_PLANE` is a separate Capture-only contract plane. It may
reference evidence IDs and hashes, but T1 does not connect it to RawEvent,
Bronze, ingress, replay runtime, normalized events, Silver, strategy, AI, risk,
dashboard, account observation, Testnet/Mainnet execution, or exchange writes.

## R0 and R1

R0 is `CAPTURE_ONLY`:

- `release_id = V0-R0`
- `primary_asset = ETH`
- `active_strategy_count = 0`
- `capture_contracts_authorized = true`
- `network_runtime_authorized = false`
- `strategy_runtime_authorized = false`
- `signal_recommendation_authorized = false`
- `risk_sizing_authorized = false`
- `trade_plan_authorized = false`
- `account_runtime_authorized = false`
- `exchange_execution_authorized = false`

R1 preserves the former future ETH Operator Assist semantics: ETH-only,
ETH-LDAR or separately approved future ETH strategy, `LONG`/`SHORT`/`WAIT`,
deterministic risk, TradePlan, FAST/STANDARD presentation, human review, manual
execution, read-only account/order/fill observation, plan/outcome matching,
replay, and learning loop. In T1 it remains future, not implemented, and not
authorized.

The former human-confirmed automated execution controls are deferred under
`future_human_confirmed_execution`, with no release assigned, release authority
false, status `DEFERRED_SEPARATE_G4_GATE`, autonomous entry prohibited, human
confirmation required, implementation unauthorized, Testnet unauthorized, and
Mainnet unauthorized.

## Capture Contract

`CaptureRecordV0` is a `record_type` tagged union containing exactly
`SignalCaptureV0`, `CapturePlanV0`, `ShadowOrderIntentV0`,
`HumanObservationV0`, `MarketPathEvidenceV0`, `CaptureLifecycleEventV0`,
`RuntimeControlEventV0`, and `CaptureKillStateV0`. The schema `$defs` contains
all 15 Capture objects, including manifest, checkpoint, replay, local safety,
and endpoint allowlist contracts.

Capture plans are minimal non-executable evidence. They are not TradePlans and
cannot carry size, notional, leverage, risk, authoritative entry, stop, take
profit, order type, submit, execute, or permit fields. `WAIT` allows zero or one
non-actionable CapturePlan and zero ShadowOrderIntent records. Shadow intents
are shadow-only, non-executable, and never exchange-submittable.

Market-path evidence freezes finalized append-only windows and ordered,
non-overlapping missing ranges. Later data must be appended as a new record. It
does not adjudicate PnL, MFE, MAE, R multiple, winners, or outcomes.

Lifecycle events and runtime-control events have different `record_type`,
different hash domains, different legal event kinds, and different validators.
Lifecycle events cannot carry start permits, connection, kill, resume, or
recovery authority. Runtime-control events cannot masquerade as signal, plan,
shadow, human observation, or market-path evidence.

Kill state fails closed. Resume requires a new single-use permit reference, an
integrity-check reference, and an append-only runtime-control event reference.

Manifest entries, checkpoints, and replay reports freeze Capture-plane integrity
contracts only. They perform no I/O. Replay reports do not contain PnL, win
rate, Sharpe, MFE/MAE, or promotion judgment.

## Local Safety and Endpoint Allowlist

`CaptureLocalSafetyPolicyV0` is a local safety policy, not a Hyperliquid
official fact. It fixes one active WebSocket connection, one connection attempt
per manual durable single-use non-replayable start permit, no automatic
reconnect, no automatic backfill, no active probes, and no Info HTTP requests.
It adds no cooldown, automatic resume, or permit reuse.

`CaptureEndpointAllowlistV0` is ratified contract-only and runtime unauthorized.
It allows only `hyperliquid-public-mainnet` endpoint `hl-ws-mainnet-public`,
WebSocket public read-only observation, operation `candle`, coin `ETH`,
intervals `5m` and `15m`, capture mode `WS_TEXT_UTF8_APPLICATION_PAYLOAD`,
source catalog version `hyperliquid-public-mainnet.0.1.0`, and source catalog
hash `0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7`.
It rejects BTC, Info HTTP, `candleSnapshot`, `1m`, `3m`, `1h`, other endpoints
or operations, private/account/exchange surfaces, credentials, reconnect,
backfill, and `runtime_authorized = true`.

## Rate-Limit Authority

```text
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
CONFLICT_STATE: OFFICIAL_SOURCE_VARIANT_CONFLICT_DETECTED
SUPERSESSION_STATE: EFFECTIVE_VARIANT_UNDETERMINED
AUTHORITY_HASH: 0e327e566589d8030ff00d4d009eb4b6827679ab508133d66840b2c245dc53df
SOURCE_CATALOG_HASH: 0ca27f650f399f8fa481ad9421eab4183c1c13812c71dfa8daaf878719bd99b7
SOURCE_COUNT: 2
FACT_COUNT: 25
UNKNOWN_COUNT: 14
```

The following gates remain false: `transition_eligible`,
`live_transport_authorized`, `account_readonly_runtime_authorized`,
`testnet_execution_authorized`, `mainnet_execution_authorized`, and
`flp1_implementation_authorized`. The T1 write lease is not runtime or product
implementation authority.
