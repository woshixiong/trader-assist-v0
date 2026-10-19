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

## Continuous public capture candidate

One native LiveNode runs until an operator stop, genuine failure or fatal archive
admission error. No duration is passed by the disabled systemd artifact. There
is no planned 900-second cycle, writer close or collector restart. Native
Hyperliquid reconnect/resubscribe and stale-stream recovery stay enabled.
Use the locked Linux CPython3.13/rc7 environment, without credentials:

```sh
PYTHONPATH=src:. python -m scripts.rc7.run_public \
  --provider-coins ETH xyz:SKHX --root /path/to/isolated-capture
```

`--duration-seconds 420` is an explicit isolated qualification stop, never the
normal service mode. The CI-only reconnect probe sends one **official native
DataActor.reconnect_socket** command; it adds no recovery loop or transport.
The optional public CI proof uses one process/writer for 420 seconds, checks
sealed data while that writer remains open, and requires fresh native events
after the native disconnect/reconnect. It submits no orders.

## Native archive query lag and integrity

The live policy uses `RotationConfig.interval(300_000_000_000)`, no promotion
interval, **promote_on_close=False**, and retained Feather. The tagged official
`writer/feather.rs` checks interval rotation **on a write for that data family**,
after appending it. Passing wall time or flushing alone does not seal a quiet
family. Thus a five-minute interval is **not a five-minute visibility SLA**.
Under active traffic it seals at the first family write after the deadline;
quiet data can remain unavailable to staged readers indefinitely. Families
rotate independently and may contain several instruments. Instruments themselves
are not returned as market Data by the native run reader.

Use the official sealed-stage reader, including while capture is active:

```sh
PYTHONPATH=src:. python -m scripts.rc7.catalog stage \
  --root /path/to/isolated-capture --instance-id INSTANCE_ID
```

This delegates to `ParquetDataCatalog.read_live_run()`. Native recovery skips
writer-locked `.feather.partial` files, recovers abandoned unlocked partials,
and reads sealed Feather only. The latest unsealed tail is absent, not silently
certified complete. The API loads available run data in memory and sorts by
`ts_init`; it is not a transactional snapshot or a global ordering guarantee
across different families at equal timestamps. Tests preserve per-family order,
original clocks, equal-time rows and CLEAR/book values across segment boundaries.

**Promoted Parquet Catalog queries are separate.** No automatic promotion runs,
including on close, so their lag is unbounded until an explicit successful
native conversion. Rotation can split equal-ts_init groups; native conversion
can reject overlapping closed catalog intervals. The source remains retained,
and no integrity check is weakened. `catalog recover` is an explicit stopped-run
conversion attempt, not a safe rolling promoter or guaranteed conversion of all
rotated runs. Existing unrotated native close/promotion/readback and deterministic
Backtest fixtures remain tested. Never run conversion against an active writer.

Startup invokes native stage recovery/readback before starting a new writer.
Corruption, locked prior writers, or an incomplete stopped run fail closed.
Active-stage readback reports SEALED_STAGE_READABLE with open partials listed;
it never reports Parquet/catalog PASS. Stopped stage readback requires the full
native tail to have sealed. Source remains after crash/truncated-tail recovery.

The existing 8GiB whole-root / 1GiB free-disk checks remain minimum admission
and stop thresholds, not hard filesystem quotas or automatic retention. They
are sampled and can overshoot. Fatal archive/capacity/config errors exit 78;
no automatic restart follows. Fuller alerts, backup/DR and retention are deferred.
Staging activity is not writer integrity or live HEALTHY. Strategy evaluation
uses live native callbacks and never waits for Parquet promotion.

## Disconnect and gap evidence

Socket acknowledgement alone never re-arms freshness. Native disconnect clears
the continuity epoch; each instrument/stream needs valid fresh native events.
Stale receive intervals and missing closed-bar periods also create explicit
CAPTURE_GAP metadata with prior/next original `ts_event` and `ts_init`. Later
bars are never shifted or reindexed. Exact lost-event counts remain UNKNOWN.
Gap/history-request facts reuse the existing immutable `ShadowLedger` in
`coverage.sqlite`; this stores metadata/hashes, not a second market-data archive.

The adapter owns reconnect/resubscribe and book snapshot reset. Supported native
bar requests and bounded recent-trade requests are used after observed gaps.
Closed historical responses are recorded as evidence; they do not re-arm live
freshness, feed the live strategy, or certify complete archive backfill. The
recent-trade snapshot can lack historical depth or return empty when the indexer
is unavailable. No historical quote/depth recovery guarantee is exposed here.
Unproven intervals remain explicit UNKNOWN coverage. No event is synthesized.

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

The ETH protocol fixture declares **100000 USDC and 100000 USD as separate
simulated balances**. Tagged native Hyperliquid metadata quotes perps in USD
and settles ETH in USDC; the native fee/PnL APIs debit USD. No USD/USDC exchange
rate or real account collateral equivalence is asserted. Funding other HIP-3
collateral/order mappings is outside this ETH-only order fixture. Source
artifacts are packed as tar.gz because GitHub artifact paths reject the colon
in genuine native HIP-3 instrument names; catalog filenames stay unchanged.

| Changed capability | Required evidence / current boundary |
| --- | --- |
| ETH + existing HIP-3 metadata | Actual native provider resolution; public CI artifact required |
| Quote/trade/L2 book/closed 1m+5m | Nonzero per-instrument counts; no unavailable-provider PASS |
| Close/restart/recovery | Native crash fixture, idempotent promotion, typed hashes, clean restart proof |
| Native quote replay | Same catalog definitions, two causal deterministic Engine runs |
| Sandbox lifecycle/fees/PnL | Native events and account snapshots in isolated public proof; report observed types only |
| Approved strategy orders | **NOT QUALIFIED:** registered evaluator lacks accepted native order sizing/mapping |
| Continuous archive queries | Native sealed Feather only; write-triggered lag, no fixed SLA; promoted Parquet remains unqualified |
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
snapshot. It uses official **systemd 255** `Restart=on-failure`, 15-second
restart delay and a three-start/300s limit for genuine native failures. Fatal
archive/config exit 78, argument exit 2, manual SIGINT exit 130 and clean
termination signals are restart-prevented. Manager-requested stop never restarts.
The unit remains uninstalled/disabled with an unshipped authorization marker.
No service or AWS mutation is authorized by this document. Native
`systemd-analyze verify` validates a CI copy without installing/starting it.

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
