# RC7 native quality and archive policy — code-stage only

Issue352 control6306061820, existing Draft PR353. No deployment, production retention
migration, pruning, credential, strategy, Shadow or order authorization is granted.

## Proven roots and native owner

- OI: tagged `DataActorCore.subscribe_data` returns after a local-topic subscription
  when client_id is absent; it never sends SubscribeCustomData. The observer now
  supplies official HYPERLIQUID_CLIENT_ID. Native HL activates OpenInterest on its
  existing activeAssetCtx subscription; no new stream or collector is introduced.
- Funding: `interval=60` means settlement minutes. Tagged parse_ws_asset_context
  sets funding ts_event=ts_init at local native receipt, not the settlement time.
  Its handler emits only changed values; mark/index/OI are also change-driven.
  No positive fixed heartbeat bound is exposed by these typed outputs. Existing
  30/60-second limits remain conservative admission/delivery limits, not assertions
  of feed cadence. Do not increase funding freshness to an hour.
- An old change-only value is CURRENT_VALUE_UNVERIFIED, rather than a fabricated
  STALE receive gap. A sibling mark never refreshes funding/OI timestamps. The
  native input eligibility remains false while required currentness is unproven.
  This explicitly preserves an rc7 limit: unchanged-value silence cannot provide
  a trade-grade heartbeat certificate. No new timer/feed/controller is added to
  manufacture one. No claim of fully qualified automated trading is made.
- Native stale-stream reconnect/resubscribe/book recovery remains enabled in the
  existing Hyperliquid config. Socket ACK alone cannot re-arm inputs. Reject stale,
  future/noncausal, duplicate and invalid events. The first fresh event after a gap
  records FRESH_EVENTS_RESUMED but remains quarantined; the next distinct fresh
  event (next contiguous closed bar for bars) can reestablish current eligibility.
  Historical lost counts and gap coverage remain UNKNOWN, even after re-arming.
  This is an input-readiness certificate, not an order authorization or new strategy.
- Writer file progress is activity evidence only. Reports separate OBSERVED activity
  from UNVERIFIED writer integrity and catalog integrity. Native typed sealed
  readback remains necessary; active files or socket-connected are insufficient.

## Explicit native archive profiles

`--archive-profile FULL_NATIVE` is the unchanged default. No service unit or host
arguments are changed. Opt-in `--archive-profile LEAN` selects native StreamingConfig
`data_types` returned by native_catalog.archive_data_types: generic Bar (subscribed
closed 1m/5m), MarkPriceUpdate, IndexPriceUpdate, FundingRateUpdate, and native
Custom("HyperliquidOpenInterest"). It does not persist generic quotes/trades/depth
or other custom families, but does not unsubscribe or filter incoming callbacks.
The native filter is family-global across instruments/providers, not per-symbol.
Native instrument metadata remains required for causal replay: LEAN explicitly
includes NautilusInstrumentType("CryptoPerpetual") and ("CurrencyPair") through
instrument_types. A data_types-only whitelist excluded metadata in the first native
fixture; the assertion was retained and the native selectors added.

Both profiles explicitly select native DataCatalogConfig compression="zstd".
Continuous mode retains five-minute native Feather rotation, no automatic promotion,
no close promotion, and delete_feather_after_promotion=False. Existing AWS raw files
remain untouched. No copier, dedup engine, cron, promoter, scheduler or second writer.
A lean policy must be deliberately selected for a separately approved release/root;
existing bytes are not retrospectively compressed/deleted by selecting it.

Rotation is write-triggered for each family: quiet families have no five-minute
visibility bound. Equal ts_init rows can cross sealed-file boundaries and native
promotion then rejects overlapping intervals. The existing equal-time/CLEAR/L2
negative fixtures remain gates. Preserve all source and stop on integrity/capacity
failure; never bypass disjoint checks or shift timestamps. Native no-rotation finite
close promotion is tested; repeatable continuous rolling publication is UNQUALIFIED.
Native DataCatalogConfig ZSTD compresses promoted Parquet, not retained live Feather.
Thus LEAN reduces source families, but does not solve unlimited retention by itself.
Existing finite disk budget still fails closed; no 24/7 or MB/week promise.

## Bounded evidence contract

The native fixture feeds the same typed synthetic data through FULL_NATIVE and LEAN
BacktestEngine/streaming infrastructure (no orders or signal economics), verifies the
actual observer's explicit OI subscription and on_data, quote/trade callbacks,
exact selected family counts/decimal precision/ts_event/ts_init after native close,
retained sealed Feather, native ZSTD Parquet and nonduplicating native recovery.
The pre-promotion stage summary reports native returned type counts only.
Bounded typed-context tests separately check native values and clocks.
`storage-profile.json` records actual file bytes and empirical ratios for this
fixture only; it is not a market-rate or weekly forecast. No generic data store is
implemented in the test. A bounded public context probe is separate evidence and
must state actual observed/missing families; subscription presence is not PASS.

Next gates: Engineering Control resolves the official change-only heartbeat and
rolling retention limits. Any host activation/restart and any old-raw migration or
pruning need separate current user authorization. Real execution remains OFF.

## Exact official sources (v2.0.0rc7)

- [OI example / shared native stream](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/docs/integrations/hyperliquid.md)
- [No-client local-topic-only behavior](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/common/src/actor/data_actor.rs)
- [Changed-value suppression](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/adapters/hyperliquid/src/websocket/handler.rs)
- [Funding timestamps / settlement minutes](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/adapters/hyperliquid/src/websocket/parse.rs)
- [Native family configuration](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/persistence/src/config.rs)
- [Promotion and equal-time limitations](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/docs/how_to/stream_parquet_catalog.md)
- [Native ZSTD catalog](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/docs/concepts/data/catalog.md)

## Control correction: native readback only

The public stopped-stage check now directly uses `ParquetDataCatalog.read_live_run`
and reports returned native type counts. It does not invoke the generic event hash
helper or claim content parity from counts. The attempted CustomData-specific
hash extension was removed. Official `CustomData.data` is an inner typed record,
not a general `to_dict` contract. Existing bounded context tests use native
`convert_stream_to_data` and `query_custom_data`; they do not qualify rolling
publication or an atomic live-stage snapshot. No further reader/codec is added.

## Control6307939213: supported close lifecycle versus continuous visibility

Root: rotation/periodic promotion can split equal `ts_init` rows; later overlapping
promotion is rejected by the native catalog. The official safe finite alternative
is already `streaming_config(root)` (no rotation, no interval promotion, promote
on close, retain source). Native Backtest streaming/end tests now explicitly prove
the open locked source is unavailable and Parquet queries are empty until close,
then exact typed readback and idempotent native recovery. Existing native tests
retain crash/truncated-batch recovery, equal-time CLEAR order and overlap negatives.

Do not replace `streaming_config(root, continuous=True)` silently: no rotation
removes the sealed prefix available to readers, and catalog visibility can wait
indefinitely for shutdown. The continuous runtime therefore remains unchanged.
Engineering Control must choose native staged-prefix access with provisional
Parquet, or close-only publication with unavailable open-tail reads. Neither is
qualified as always-queryable continuous Parquet or bounded indefinite retention.

An opt-in `sandbox_probe` CI input runs the EXISTING built-in ExecTester protocol
fixture on actual public HL ETH quotes with the existing Sandbox factory, native
RiskEngine (bypass false), simulated fees/balances and immutable ledger. This is
DEV_ONLY, not a new strategy or an approved forward-research profile. It uses no
synthetic quotes/opportunities and tests native close/cancel, fees/PnL and finite
source-to-typed-Parquet quote readback after dispose. Legacy Muse development
fixture economics remain unchanged and separately covered by deterministic native
positive/negative tests; no approved real strategy-to-order profile is inferred.

Pinned official examples:
- https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/examples/live/hyperliquid/data_tester.py
- https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/examples/live/sandbox/exec_tester.py

The official Sandbox example bypasses risk; this repository retains bypass=false.
No real execution factory is registered. No production service or restart policy changes.
