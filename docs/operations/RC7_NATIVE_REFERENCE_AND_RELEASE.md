# Native reference feeds and exact rc7 release candidate

Issue #352 control 6289012825 authorizes public-only engineering, not installation,
service activation or deployment. Keep Draft PR #353 and the existing service disabled.

The original HL Final20 registry, adapter, writer and nine requested families are
unchanged. `--reference-venues` opts the existing single LiveNode into first-party
Binance Spot **JSON** and OKX **SWAP** data factories. The default service remains
HL-only. Candidate symbols live once in `native_reference.CANDIDATES`; they are
requirements, not asserted live listings. The actor admits only actual native
provider instruments, subscribes quote/trade/external closed 1m, and records exact
per-venue identity, currency, precision, increments and multiplier in coverage.
No HL price, token/share equivalence, contract conversion, synthetic symbol or
fallback instrument is introduced. A missing candidate remains explicitly missing;
an unresolved provider is distinguished from observed provider inventory.

Binance's default SBE path needs Ed25519 credentials: this composition explicitly
uses `BinanceSpotMarketDataMode.Json`, no keys and no commission query. Its native
parser emits a generic Bar plus Arrow-supported BinanceBar only when `is_closed`.
Generic Bar `ts_event` is the inclusive close millisecond. OKX's public/business
clients need no credentials; native candles emit only `confirm=Closed`, with
`ts_event` at candle open. The reader checks each venue's actual finality convention
against native `ts_init` and knowledge time, without rewriting either clock.

The research consumer keeps one latest typed input/hash per instrument/family.
It uses existing NativeHealth gap evidence, rejects unknown/stale/noncausal/
duplicate/out-of-order inputs, wrong tick/size and first input across a detected
gap. It never generates orders or research opportunities. Socket state alone
cannot qualify a feed. Restart boundaries restore through existing NativeHealth;
the first valid event closes the explicit unknown-coverage gap and is rejected
by the research consumer, rather than silently bridging it. Reference coverage
and freshness are included in the
existing runtime health report; `NATIVE_INPUTS_OBSERVED` is not live HEALTHY.
Reference mode rejects Sandbox and strategy manifests before loading either.

Native StreamingConfig is the only event store. Existing interval segments,
Feather retention, locks/recovery and the rolling-promotion limitations remain.
The finite proof closes/seals a bounded isolated node, uses existing official
native conversion and typed queries, verifies source/readback multisets, original
callback hashes and native instrument contracts, then passes records to the same
nontrading reader. Unsealed tails, source >64MiB, absent families, bad contracts or
missing callback/source linkage cannot qualify. This is a finite proof bound,
not a memory SLA or continuous incremental catalog publisher. Extended BinanceBar
source remains retained; generic quote/trade/Bar are the required consumer inputs.
No source files are deleted or copied into a second archive engine.

Deterministic native tests use synthetic records and say nothing about listing
availability. One opt-in `reference_probe` GitHub workflow attempt captures 75s
per venue with the official client/provider; venues are isolated sequentially
so a blocked Binance endpoint cannot erase OKX evidence. This is a qualification
script, not a daemon, production restart cycle or another collector. Its separate
`reference-public-qualification` check is distinct from the five required code
checks. Inspect its per-symbol/family report; subscription ACKs or green code CI
are insufficient. Unavailable endpoints/listings remain unqualified.

## Minimal exact release preparation (instructions only)

Only after separate current deployment authorization, prepare a Linux x86_64
host (glibc >=2.34) with CPython3.13, the existing unprivileged `tradeos` identity
and approved paths. Do not alter a Python3.12 environment or use the old rc5 bundle.
Use the **exact reviewed PR commit from the canonical checkpoint**, not a branch tip:

```sh
set -eu
RELEASE_SHA='REPLACE_WITH_EXACT_REVIEWED_SHA_FROM_ISSUE_352'
test "${#RELEASE_SHA}" -eq 40
case "$RELEASE_SHA" in *[!0-9a-f]*) exit 78 ;; esac
cd /opt/tradeos-rc7/repository
git fetch origin "$RELEASE_SHA"
git checkout --detach "$RELEASE_SHA"
test "$(git rev-parse HEAD)" = "$RELEASE_SHA"
python3.13 -m venv /opt/tradeos-rc7/venv
/opt/tradeos-rc7/venv/bin/python -m pip install --require-hashes --only-binary=:all: \
  -r requirements-runtime-py313.lock -r requirements-nautilus-pilot.lock
/opt/tradeos-rc7/venv/bin/python -m pip check
```

The source checkout plus the unit's PYTHONPATH is the source installation; no
unlocked package build, new installer/platform or dev dependency installation is
needed. pip verifies the official cp313 Linux rc7 wheel SHA256
`b3928f37d75d57508030a421dc762186ad1f9ffc5d5420d7daf1d2c6badb8044`.
Official tag `v2.0.0rc7` resolves to source commit
`55c0e82053142bce3a5cba4de4221d3929c2d3bc`; record that independently of the
application's reviewed release SHA. Runtime identity is in NAUTILUS_RC7_RUNTIME.json.

The reviewed provider-bound, hash-valid PIT snapshot belongs at
`/etc/tradeos/approved-pit-universe.json`; data belongs at `/var/lib/tradeos/rc7`,
owned by `tradeos:tradeos`, with the existing disk budget/free-space admission.
Do not manufacture or approve snapshot metadata from candidate names. Native
HL startup validates it against provider metadata. The supplied unit expects
`/opt/tradeos-rc7/repository`, `/opt/tradeos-rc7/venv`, User/Group `tradeos`, and only
the data path writable. No authorization marker, enable/start or restart command
is shipped here. Installation/identity/path changes and the marker remain protected
operations. Do not activate optional references until their scoped evidence is accepted.

AllDex JSON Arrow archival, Yahoo/macro, rolling Parquet guarantees, #358 range
research, approved-strategy Shadow and real execution remain separate gates.


Pinned capability sources: [Binance public client](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/adapters/binance/src/spot/data.rs),
[Binance closed-kline parser](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/adapters/binance/src/spot/websocket/public_json/parse.rs),
[OKX public client](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/adapters/okx/src/data.rs),
[OKX confirmed-candle parser](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc7/crates/adapters/okx/src/websocket/parse.rs).
