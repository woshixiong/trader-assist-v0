# Nautilus rc5 public capture and simulated paper candidate

Status: **ISOLATED UNREVIEWED DRAFT** for Issue #338. No formal ordinary ChatGPT
High Pre-code PASS, deployment qualification, continuous-uptime proof or live
trading acceptance is claimed. Gate D is excluded. No private execution client is
created. Native risk configuration `bypass=False` does not establish HALTED;
the pinned Python LiveNode does not expose the required native state setter.

## Public capture

Use the existing Python 3.12/Linux x86_64 environment with the repository's hashed
`nautilus-trader==2.0.0rc5` lock. Do not rebuild Nautilus on a Mac for parity.
The new entrypoint is explicitly selected; existing E4 strategy/L0/history paths
retain their behavior.

```sh
python scripts/e4_nautilus_public_data_probe.py --foundation-public \
  --run-seconds 300 --evidence-path /tmp/native-public-capture \
  --result-path /tmp/native-public-result.json
```

This is a bounded public-only foreground capture command, not a service install.
It is documented here, not executed during candidate development. Default exact
instruments are `ETH-USD-PERP.HYPERLIQUID` and
`xyz:SKHX-USD-PERP.HYPERLIQUID`, with external 1m/5m bars. Repeat
`--foundation-instrument` to select exact instruments, and `--bar-type` to
select explicit native bar streams. Missing cache instruments stop capture.
No historical request, strategy readiness, semantic CaptureSession, all-market
warmup or old L0 qualification is involved. Public instrument discovery/refresh
and subscriptions belong to HyperliquidDataClientFactory. Optional venue data
families beyond quote/trade/depth10/bar are not qualified by this candidate.

Native stale-stream recovery is enabled; adapter default thresholds/cooldowns
remain in effect. QueueMonitorConfig is enabled with a depth trigger of 1000 and
mean-dispatch trigger of 10ms, clearing at zero. These are observation settings,
not queue-capacity or losslessness guarantees. No application hot queue, worker,
reconnect controller or watchdog is added.

## Catalog and freshness limits

Each process gets a distinct native catalog directory. Native QuoteTick,
TradeTick, OrderBookDepth10 and Bar objects go directly to the matching native
ParquetDataCatalog methods. Batches contain at most 512 events by default
(configurable in the sink up to 4096); a native one-second timer flushes idle
pending data. Synchronous disk operations can delay the native runner. Native
queue observations expose pressure; this is not a throughput qualification.

Each batch is checked using a newly opened native catalog over its timestamp
range. Any write or readback error marks the entire pending batch uncertain,
stops capture and prevents automatic retry. Earlier groups in that batch may
already exist on disk. Keep the directory for inspection; do not delete or
blindly replay uncertain batches. Repeated timestamp ranges across batches or
out-of-order ts_init can fail native disjoint/order checks; do not disable those
checks to make a run pass. No atomic transaction or permanent continuity is
claimed. Instrument definitions are written at startup; evolving instrument
metadata persistence is not qualified.

After a crash, retain the old catalog, inspect it through a fresh
ParquetDataCatalog, and start a new segment. Buffered events may be lost and the
interruption is an unqualified gap. No automatic historical gap repair occurs.
Storage failures including ENOSPC/permission errors are surfaced. Native catalog
serialization, not a custom append log, owns market-data durability.

Freshness is application callback receipt age measured with monotonic time,
keyed by instrument and exact event stream (including full bar type). Quote,
trade and depth thresholds are 120s; bar threshold is 600s. They describe receipt
silence, not exchange activity or provider timestamp validity. Native socket
and queue events are displayed separately. Socket CONNECTED, ACK and pong never
create receipt evidence. A connection break invalidates previous receipts.
The native receive monitor covers its supported BBO/book streams; trade/bar
observations do not imply native targeted recovery for those families.

Systemd, journald, disk/inode monitoring, log retention and deployment remain
separate operations work. No unit or service-control command is included.

## Offline paper lifecycle

`nautilus_g4.runner.run_native_paper_lifecycle()` accepts an offline native
instrument and 3..1024 native QuoteTick objects with strictly increasing ts_init.
It writes/reopens a native catalog, builds the existing supported BacktestNode
composition, and runs a finite technical strategy: MARKET buy, resting LIMIT
buy, limit modification on the second quote, cancellation on the third. Inputs
must keep that limit resting if cancel/modify proof is desired.

Native engines own orders, fills, position/account state and fees. Results
contain actual observed native events and Cache/Portfolio projections; all
fills and result origins are labeled SIMULATED. No fill is fabricated. Partial
fills, STOP/TP/MIT/LIT combinations and persistent engine restore are explicitly
unqualified. Repeated fresh-instance replay is a determinism check, not recovery
of an actual live account. No private API, signer or exchange transport is used.

## Evidence and remaining gates

Historical ETH/SKHX five-family callback/catalog evidence: Issue #320 comment
6173735426, artifact 11701962785. Do not rerun the expensive historical ten-cell
experiment or the 2400-second L0 qualification just to start this composition.
The independent raw recorder PR #336 is a separate optional audit sidecar.

Existing E4 CI selects the new foundation test filename; existing G4 CI selects
the extended runner tests. Native tests must run on the locked Linux rc5
installation. A local skip is not acceptance. Run focused E4/G4 tests, retained
warmup regressions, Ruff, mypy and diff checks before candidate publication.
Exact-head CI and genuine independent review remain pending. Gate D, Mark Ready,
merge, credentials, signing, exchange writes, deployment and service control
require their own current authority and are not granted by this document.
