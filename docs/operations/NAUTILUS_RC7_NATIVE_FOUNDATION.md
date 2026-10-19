# rc7 native foundation candidate — Issue #352

This release uses official NautilusTrader **2.0.0rc7**, CPython **3.13**, Linux
x86_64/glibc >=2.34. Exact wheel, dependency locks, native semantics and source
references are recorded in `NAUTILUS_RC7_RUNTIME.json`. The official wheel/hash
and API smoke passed on Python 3.13.16/Linux at `faa4d1c`; later changes require
their own exact-head CI. No production environment has been replaced.

## Shared root and native owner

The old active composition was rc5/Python 3.12, lacked native streaming and
execution composition, and coupled public startup/reconnect to historical
prewarm. rc7 owns Hyperliquid transport/recovery, its `OrderBookDepth` objects,
Feather staging, catalog promotion/recovery, Sandbox matching and native
RiskEngine/OMS/Account/Portfolio. The candidate has no new WebSocket client,
matching engine, reconnect controller or full duplicate market-data store.
Historical rc4/rc5 evidence remains readable; rc6 findings remain unchanged.

`native_runtime.build_native_node` composes public-only capture or the official
Sandbox factory. `scripts.rc7.run_public` validates an approved hash-bound PIT
snapshot against native provider instrument callbacks before subscribing immediately
to Quote/Trade/Book/closed external 1m and 5m. It requires ETH and a HIP-3 expression;
it does not invent a symbol or substitute SKHX. Missing metadata fails closed.
The tagged Hyperliquid handler emits the previous cached candle when its period
changes; its parser uses candle open time for `ts_event`. Admission checks the
corresponding close against `ts_init` and the current clock. Actual public
provider and 5m coverage still require bounded evidence.

## Bounded isolated development quickstart

Use the exact locked Linux x86_64/Python 3.13 environment; this is not an AWS or
service activation instruction. The default has no execution client. Discovery
accepts only coins already in `multi_asset_shadow.resolution.INITIAL_40` and
resolves native IDs/precision through the official provider. There is no symbol
fallback if `xyz:SKHX` is missing.

```sh
capture_root="$(mktemp -d)"
PYTHONPATH=src:. python -m scripts.rc7.run_public \
  --provider-coins ETH xyz:SKHX --root "$capture_root" --duration-seconds 420
```

Inspect `resolved-pit-universe.json`, `health.json`, `close-proof.json` and
`recovery-proof.json`. `close-proof.json` separates typed catalog integrity from
per-instrument public stream coverage; catalog PASS alone is insufficient.
The health report says `CAPTURING_CATALOG_PENDING_CLOSE` while the catalog has
not been verified and `STOPPED` after termination. Neither means live HEALTHY.
Missing instruments/events, bad clocks, disk errors and native close failures
remain visible and cannot be certified as usable provider coverage.

After the writer is stopped, use the instance ID from the close proof:

```sh
PYTHONPATH=src:. python -m scripts.rc7.catalog replay \
  --root "$capture_root" --instance-id INSTANCE_ID
```

This reads typed catalog quotes/instrument definitions and runs two official
BacktestEngines, checking causal clocks, complete typed event hashes and repeat
ordering. It submits no orders and does not establish strategy profitability.
`catalog recover` invokes official unlocked-partial recovery and promotion;
complete source batches remain retained. Restarting capture on the same root
first recovers/verifies prior runs and fails on corrupt or missing archive data.
Do not run recovery against an active writer or remove failed source files.

The existing rc7 CI workflow has a manually dispatched `public_probe=true`
option for an isolated Ubuntu runner. It performs a 420-second initial capture,
a 60-second clean restart, typed readback, deterministic replay, and the official
ExecTester routed exclusively to Sandbox with declared simulated fee rates.
It retains native sources and `public-qualification.json`, including failures.
Unavailable provider access is a failed/unqualified public proof, never PASS.
This fixture is separate from the registered strategy and adds no alpha signals.

## Storage/recovery and health limits

The pinned official guide warns that rotation or interval promotion can split
equal `ts_init` rows, causing overlapping closed catalog intervals. This candidate
uses explicit no rotation/no interval promotion, retaining source Feather and
promoting on close. Do not represent that conservative policy as qualified
continuous 24×7 live catalog promotion. During capture, catalog/writer verification
is UNKNOWN and health stays DEGRADED; stop-time successful typed readback does
not retroactively make the live process healthy. Live rotation/promotion and
bounded disk retention remain acceptance gaps.

`verify_promoted_run` checks the complete native sink lifecycle against typed
Parquet count and event-multiset hashes, retaining duplicates, precision and
both native timestamps. It does not compare the shorter Actor RUNNING window to
the longer native writer lifetime. It does not claim exchange wire-receive time.
Close/readback failures propagate; staged files must remain intact. Native
recovery reads unlocked `.feather.partial` files and retains complete batches.
Do not delete Feather/catalog data to make a failed promotion appear successful.

Native health uses stream-specific actual event age, continuity epochs,
monotonic source order, native socket state, free disk, writer/catalog evidence
and report timestamp. File mtime is never a freshness predicate. Reconnect ACK
alone cannot restore feed health. Out-of-order/unknown-clock faults latch until
reviewed recovery; no automatic execution re-arm is provided.

## Shadow and execution boundaries

The existing canonical `nautilus_pilot.strategy_package` registers the frozen
Three Setup Champion evaluator. Its economics must remain unchanged. A full
live-public-feed-to-approved-strategy-to-Sandbox execution binding is not yet
qualified by config construction or synthetic ledger fixtures.

`ShadowLedger` is an append-only SQLite evidence log with FULL synchronization,
immutable update/delete triggers and a verified hash chain on reopen. It records
strategy/version, all decisions including REJECT/WAIT/PASS/UNFILLED/LOST, and
native lifecycle facts. It is not an OMS. Native partial fills/cost/PnL and
account/position snapshots must be collected from native behavior; artificial
fixtures are not live Sandbox lifecycle proof.

`--sandbox --sandbox-probe --maker-rate 0.00015 --taker-rate 0.00045` adds only
the official native protocol tester to the bounded development run. Its native
order history (including denied, unfilled, cancelled and amended orders), fills
with native commission, account/position/equity/PnL snapshots are recorded in
`sandbox-probe.sqlite`. Every initialized probe order remains in its decision
denominator. Snapshot/event collection is idempotent; no fees or fills are
invented by the ledger. Actual event counts are reported; rejection, partial
fill, stop/TP and reconciliation coverage must not be inferred from unrelated
events. The approved evaluator still has no qualified sizing/order mapping.

| Changed capability | Required evidence / current boundary |
| --- | --- |
| ETH + existing HIP-3 metadata | Actual native provider resolution; public CI artifact required |
| Quote/trade/L2 book/closed 1m+5m | Nonzero per-instrument counts; no unavailable-provider PASS |
| Close/restart/recovery | Native crash fixture, idempotent promotion, typed hashes, clean restart proof |
| Native quote replay | Same catalog definitions, two causal deterministic Engine runs |
| Sandbox lifecycle/fees/PnL | Native events and account snapshots in isolated public proof; report observed types only |
| Approved strategy orders | **NOT QUALIFIED:** registered evaluator lacks accepted native order sizing/mapping |
| Continuous live Parquet promotion | **NOT QUALIFIED:** retained Feather until explicit close; equal-timestamp overlap constraint |
| Real execution / 24h host | **OFF / NOT RUN:** final-dispatch gate, independent review and host qualification remain open |

`native_execution_contract` constructs only inert official Hyperliquid config,
factory, enabled native RiskEngine (`bypass=False`) and startup reconciliation.
It never builds a signer/client or connects a private API. The pure final-submit
certificate adds instrument/epoch/freshness/signal expiry/account/price checks to
the existing economic guard. This is not proof that every native dispatch route
is bound to that guard. Real execution remains unavailable/default off until
whole-path no-bypass proof and fresh independent order/risk review. Native
cancel/reduce-only behavior must be tested without weakening protective orders.

## Host preparation and separate qualification

The unit in `deploy/systemd/tradeos-rc7-public.service` is an artifact only. It
requires an unshipped `/etc/tradeos/rc7-public-authorized` marker, a dedicated
unprivileged `tradeos` user, isolated venv, writable data root and approved PIT
snapshot. It uses bounded on-failure restart, journal output, SIGINT clean stop
and filesystem confinement. No installation, activation, enable marker or AWS
service action is authorized by this document.

After separately authorized installation and closure of the acceptance gaps,
use the following read-only qualification command on the target host:

```sh
/opt/tradeos-rc7/venv/bin/python -m scripts.rc7.qualify_health \
  --health /var/lib/tradeos/rc7/health.json --duration-seconds 86400 \
  --output /var/lib/tradeos/rc7/qualification.json
```

The command must report FAIL on missing/stale/degraded health, clock failures
or missing stream counts. A short CI run cannot establish target-host 24h
uptime, Testnet/Mainnet acceptance, or real-capital safety. Official Nautilus RC
production warnings remain applicable. No credentials, wallet, private API,
exchange order, deployment, Ready or merge is authorized.

## Execution architecture stop — exact rc7 binding

The inspected official wheel's `live/__init__.pyi` exposes `LiveRiskEngineConfig`
and LiveNode configuration/build methods, but no verified Python runtime
RiskEngine state setter or native final-dispatch interception binding. The
Hyperliquid Python surface exposes an inert config and factory; the tagged Rust
factory constructs the native ExecutionClient. The tagged Rust RiskEngine
initializes `TradingState::Active` and exposes `set_trading_state` in Rust.

This is a **binding/acceptance blocker**, not a claim that Nautilus lacks native
risk functionality. A pure Python certificate check before a queued command
cannot establish the required last-submit stale-data barrier after that queue.
No live client has been constructed and no order has been sent to test it.
Do not enable the inert real-execution contract or call its construction proof
whole-path no-bypass acceptance.

Exact official sources inspected:

- `python/nautilus_trader/live/__init__.pyi` at `v2.0.0rc7`.
- `python/nautilus_trader/adapters/hyperliquid/__init__.pyi` at `v2.0.0rc7`.
- `crates/risk/src/engine/mod.rs` at `v2.0.0rc7` (native state initialization,
  runtime state setter, execution queue path).
- `crates/adapters/hyperliquid/src/factories.rs` at `v2.0.0rc7` (native client construction).

Engineering Control must choose the supported native extension boundary before
further execution wiring: inspect/approve a bounded official native plugin or
ExecutionClientFactory extension using native RiskEngine state control and
last-dispatch enforcement, or retain an explicitly limited public/Sandbox-only
scope. No core monkeypatch, parallel RiskEngine, silent version fallback or
credentialed experiment is authorized as a workaround. Fresh independent
order/risk review remains required.

The optional `--strategy-manifest` attaches the **existing** validated Three
Setup evaluator to native closed 5m callbacks and `ShadowLedger`. It retains
cold-start WAIT, no-signal PASS, and REJECT records for evaluated signals whose
native-order mapping is not qualified. It does not invent entry/size economics
or submit them. A strategy readiness requirement does not block collection.
