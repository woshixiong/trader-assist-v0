# Native HL context usability pilot (rc7 / Python 3.13)

Scope: canonical `multi_asset_shadow.resolution.FIRST_LAUNCH_20` is the sole
selection source, updated under Issue #352 decision 6287497814. WTIOIL remains
`xyz:CL`; official native instruments must resolve before acceptance. No invented
symbols, fallback identity, credentials, account, strategy or execution client.

The existing public native node now subscribes to MarkPriceUpdate,
IndexPriceUpdate, FundingRateUpdate and Arrow-registered HyperliquidOpenInterest.
Native adapter owns transport/recovery; native StreamingConfig owns Feather.
Source ts_event/ts_init and native identity are retained exactly. Asset-context
clocks are the native adapter's context/receive clocks, not a claim of exchange
match timestamps. Changes-only context feeds do not establish liveness from a
socket ACK; quiet/unchanged values may become stale under the explicit policy.

`ContextResearchReader` consumes only resolved, causal, fresh native typed inputs;
it rejects stale, unresolved, duplicate and out-of-order evidence. It retains at
most one typed record per instrument/family and hash references, not a second
market-data archive. Existing native health/gap evidence remains separate.

A bounded isolated context proof closes its test node once, reads sealed native
mark/index/funding records, and uses official `convert_stream_to_data` plus
`query_custom_data` for OpenInterest. All four callback identities must actually
occur in sealed readback and reach the causal research reader. Locked partials,
multiple OI source boundaries or any missing family fail closed. Feather remains
retained. This is NOT safe recurring rolling Parquet qualification, bounded live
query latency, 24h uptime, strategy/Shadow deployment or a normal restart cycle.

Native `HyperliquidAllDexsAssetCtxs` is explicitly JSON-backed with no Arrow
persistence registration: DEFERRED, no custom JSON archiver is introduced.

Binance Spot / OKX SWAP remain NOT_USABLE / DEFERRED in this pilot. Official rc7
first-party factories exist, but no canonical approved 12-Spot / 8-SWAP mapping
set was found in the current repo/scope. Existing four-symbol Binance Vision
USD-M research archives and generic PIT mapping schemas are not those mappings.
No inferred cross-venue ticker or Muse transport is substituted. Required next
input: exact native product/symbol/association set and official metadata binding;
then each native source -> retained typed storage -> reader must be qualified.

Existing rc7 SHA-pinned Linux wheel/Python3.13 CI and disabled systemd/venv paths
remain authoritative. No rc5 installation tooling is used. No host install,
service control, AWS/Muse interaction, Ready/Merge or exchange write is performed.

The Python binding must call official `register_custom_data_class(HyperliquidOpenInterest)`
before constructing Python `CustomData`: the rc7 adapter module registers a Rust
extractor factory, while this public API activates the extractor used by
`CustomData`. Without activation, Python construction falls back to
`PythonCustomDataWrapper`, which the native OI Arrow encoder correctly rejects.
The regression asserts `custom_data_backend_kind(...) == "native"`, then writes,
seals, converts and reads through the original native persistence APIs. It does
not replace or override the native encoder.

Pinned source: [CustomData constructor](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/model/src/python/data/custom.rs),
[class registration](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/model/src/python/data/mod.rs),
[Hyperliquid module registration](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/adapters/hyperliquid/src/python/mod.rs).

Issue #358 foundation boundary: the synthetic 24-bar regression exercises saved
native closed 5m `Bar` identity/clocks -> native typed Parquet readback -> native
BacktestEngine/DataActor `register_indicator_for_bars` -> `on_bar`, using
DonchianChannel(20), EfficiencyRatio(14), AverageTrueRange(14). Premature knowledge
time and unsupported period are rejected by existing admission. This is an
indicator wiring fixture, not a range-identification definition, RangeSnapshot,
strategy, forward signal, PnL result, or real-history qualification. Native
indicator availability does not imply that a range classifier is approved.

Native OI Arrow uses Decimal128(38,16): numeric value is exact, source decimal
scale is not retained. The causal hash therefore uses sorted typed JSON with
only redundant fractional zeros removed from the OI decimal text; it never
rounds, converts to float or alters stored native values/timestamps. Readback
must also equal the original Decimal, instrument and both clocks. A changed
16th fractional digit or timestamp must change identity.
Source: [native decimal encoding/decoding](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/serialization/src/arrow/mod.rs).
