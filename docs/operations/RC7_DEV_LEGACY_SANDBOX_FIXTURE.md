# Disposable native Sandbox engineering fixture

`DEV-MUSE-THREE-ORIGINAL-SANDBOX-v1` is **DEV_ONLY_DO_NOT_USE_FOR_RESEARCH**,
not a forward profile, E3 economic change, live natural signal, or deployment.
It is never registered by the public capture runner/systemd unit. Explicit
`create_dev_fixture(..., dev_only=True)` requires a new `*.dev-only.sqlite`.
The existing immutable ShadowLedger is reused; a prior/research ledger is refused.

Authority: [Issue #352 decision 6283815433](https://github.com/woshixiong/trader-assist-v0/issues/352#issuecomment-6283815433).
Fixture provenance is frozen to Muse Git blobs, not a moving strategy import:

- [100 USD and ETH 4.32 bps/side assumptions](https://github.com/woshixiong/muse/blob/39d9c5c2df75b6a373be140fefca330fc77eb829/shadow/shadow.py).
- [three-original structural stop, 3 ATR trail, no fixed TP](https://github.com/woshixiong/muse/blob/b6aa5e04d8bd78f8c7219f83f4c05abe694c15a2/shadow/shadow_track.py).

One **synthetic frozen long opportunity** is linked to a typed closed 5m bar;
this is not a port or qualification of Muse's signal detector. The fixture uses
100 USD / current ask, rounded down to 0.001 ETH, one GTC limit attempt, and
native reduce-only market exit. Stop 1990 and ATR 5 are synthetic input values.
The 3 ATR trail observes executable quotes after native fills, not retrospectively
known candle extremes. It is derived from legacy exit references, not historical
fill parity. No touched price is a fill. Passive-entry and insufficient-collateral
cases are explicit test faults. Native fees use a configured 0.000432 maker/taker
rate for development only. Native zero latency is not the old 1000ms assumption
or a production measurement. Funding and realistic queue position are unqualified.

The finite offline test harness uses the official Python DataClient typed input
seam, an isolated LiveNode with enabled native RiskEngine and only the official
SandboxExecutionClientFactory. It has no HTTP/WebSocket or exchange client.
Fake 100000 USD/USDC balances are separate; no USD/USDC conversion is inferred.
The insolvency negative replaces USDC collateral with 0.01 USDC. Sandbox owns
matching, accepted/rejected/partial/canceled/fill events, account and PnL.
Source hashes, native clocks, opportunity/attempt IDs, order/parent IDs and
native event/commission links use the existing immutable ledger. Native Feather
source is retained/read back on fixture close; production writer is untouched.

Run only in the pinned Linux CPython 3.13 rc7 environment:

```sh
python -m pytest -q tests/test_nautilus_rc7_dev_fixture.py
```

The official native API exposes `Controller.create_strategy_from_config`,
`start_strategy`, `stop_strategy`, `market_exit_strategy`, and `remove_strategy`;
LiveNode supports initial Python/native strategy registration. These API names
do **not** establish safe hot replacement of an active strategy with open orders,
durable state and writer continuity. `NATIVE_STRATEGY_HOT_SWAP_UNVERIFIED` until
that exact running-node lifecycle is proven. No custom manager/daemon/plugin or
capture restart is introduced. Native Controller lifecycle qualification is a
separate operator decision; this offline fixture does not depend on hot swap.

`REAL_STRATEGY_SHADOW_QUALIFIED=NO`, `AWS_DEPLOYED=NO`. Later selected strategy
economics, natural causal signals, recurring Parquet archive acceptance, review,
merge and host activation remain separate gates. Do not promote this dev ledger
to forward evidence or copy probe quantities/balances into a research profile.
