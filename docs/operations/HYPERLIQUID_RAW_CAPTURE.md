# Hyperliquid public raw capture — bounded proof and explicit continuous mode

The default is a bounded foreground proof. A separate explicit continuous mode
records until cooperative SIGTERM/SIGINT shutdown or fatal failure. The supplied
systemd unit is default OFF; this source package does not deploy or start it. It discovers
the actual active HIP3 SKHX coin through public `perpDexs` and per-DEX `meta`, plus
native ETH, then subscribes to public `trades`, `bbo`, and `l2Book`. It uses existing
`websockets==16.1` and Python 3.12, with no SDK, dependency or lock changes. There is
no account, key, wallet, signer, order or private subscription interface.

```sh
PYTHONPATH=src python scripts/hyperliquid_raw_capture.py --output /tmp/i322-public-proof --duration 60
PYTHONPATH=src python scripts/hyperliquid_raw_capture.py --output /tmp/i322-public-proof --readback
```

Use a writable directory outside the repository. Capture duration is capped at
180 seconds and defaults to 180 when no mode flag is supplied. Bounded exit 0
means transport/storage proof; exit 2 means INCOMPLETE. Exceptions fail nonzero.
`--duration`, `--continuous` and `--readback` are mutually exclusive; omission
never opts into continuous mode.
Do not repeatedly rerun an unexpected failure: preserve the files and checkpoint
and return to Engineering Control. Quiet SKHX families are INCOMPLETE, not fabricated
data or a subscription failure. Full SKHX family coverage is a separate claim.

## Continuous mode and clean stop

```sh
PYTHONPATH=src python scripts/hyperliquid_raw_capture.py --output /var/lib/trader-assist-v0-hyperliquid-raw-capture --continuous
```

Use an explicitly authorized writable output directory. Continuous mode performs
no archive-wide readback/hash and retains only the current segment path/counter,
not a list growing with the archive. Exit 0 and `clean_requested_stop` mean that
requested shutdown joined discovery, closed the socket if active, finalized and
fsynced the writer and released flock. They are not a public receipt/coverage proof.
An error exits nonzero; `Restart=no` deliberately leaves it stopped for diagnosis.

SIGTERM and SIGINT set one thread-safe stop intent; repeated signals do not reset
the deadline. Discovery checks request admission between public HTTP calls,
finishes or times out the single admitted 10-second call, validates its response
and admits no new requests after stop. It owns one worker, never an abandoned
`asyncio.to_thread` default-executor job. Normal discovery shutdown joins that
worker within 12 seconds of the first signal; a concurrent HTTP/JSON/metadata
error takes precedence over deliberate stop. No subscriptions start after stop.
Receive shutdown cancels/drains the owned receiver and closes its socket with the
existing 5-second close timeout. These are separate phases, not additive waits.

Normal stop targets 25 seconds inside the unit's 30-second grace, leaving 5 seconds
margin. The 10-second urllib request timeout is not an absolute wall-clock bound
for pathological DNS/OS/slow-response stalls. If the worker misses the join budget,
the process fails nonzero, attempts unclean writer finalization and releases flock;
a daemon worker is only a backstop for this stuck-call failure, never clean-stop
proof. There is no unbounded join or default-executor shutdown wait. OS/fsync stalls
can also exceed grace. Forced systemd termination, SIGKILL and power loss are not
clean shutdown; partial tails may remain. A `stop(clean=true)` record describes
shutdown intent before final fsync: alone it is not a durability certificate. An
observable finalization failure is marked `clean=false` best effort and never
produces a successful CLI termination result.

Readback is an explicit offline operation after shutdown; the existing CLI scans
all NDJSON in its chosen output directory. Use a closed bounded directory/selection
for bounded verification, not an ever-growing active archive. Rotation does not
delete files or enforce a disk quota. Operators own space monitoring and separately
authorized retention/export policy; permission errors, disk full and fsync/close
faults fail stopped rather than deleting raw evidence or reconnecting on disk errors.

## Default-OFF systemd source and future host qualification

Unit: `deploy/p4a/systemd/trader-assist-v0-hyperliquid-raw-capture.service`.
It has no `[Install]` target, uses `Restart=no`, and requires the dedicated missing
by default `/etc/trader-assist-v0/hyperliquid-raw-capture-permit`. No unrelated Three
Setup permit/env/credential is reused. It uses journald, strict system protection,
no privileges/capabilities, and a separate 0700 systemd StateDirectory owned by
`traderassist:traderassist` at `/var/lib/trader-assist-v0-hyperliquid-raw-capture`.

Literal future layout assumptions:

- Interpreter: `/opt/trader-assist-v0/venv/bin/python` (existing locked dependencies).
- Script: `/opt/trader-assist-v0/scripts/hyperliquid_raw_capture.py`.
- `PYTHONPATH=/opt/trader-assist-v0/src`.
- `ExecStart` passes `--continuous --output /var/lib/trader-assist-v0-hyperliquid-raw-capture`.
- Existing host user/group `traderassist`; never substitute root or create a user silently.

The interpreter matches the existing installer in
`scripts/build_three_setup_shadow_deployment_bundle.py`, which creates `venv`
without a dot. The current `scripts/verify_exact_release.py:REQUIRED_FILES`
excludes this new CLI and unit; its recursive selection includes only `src`.
Consequently the existing bundle does not yet stage this recorder's complete
entrypoint/service surface. This is a real release-integration prerequisite,
not a host-readiness or live-data claim.

A separate Engineering Control package must minimally extend those two existing
release scripts: select/hash/stage the CLI and unit in the exact-release manifest,
and add default-OFF unit installation plus offline entrypoint/layout verification
to the existing installer. Preserve the dedicated absent permit, no start/enable/
restart, exact identity/hash rejection, and current human host-action gates. No
new generic deploy controller or ad hoc copy from an arbitrary worktree is needed.
Those two release scripts are outside Issue #328's five-path scope and are not
modified by this source package.

These paths are a staged-layout contract, not proof of a current deployed release.
Before installation, Operations must verify the exact accepted release manifest
contains the script/module/unit, locked interpreter/imports, user/group, state
ownership, space and public connectivity. Unit syntax/hardening requires native
Linux `systemd-analyze verify`; source assertions alone do not qualify a host.
Future FinalShell/Operations installation, permit creation, service start/enable
and persistent-host receipt/reopen qualification require separate current human
authority. This source package performs none of them. Do not infer deployment
from CI success or documentation. Mark Ready/merge retain their own human gates.

## File contract and limitations

One foreground process holds an exclusive advisory `flock` on `.capture.lock` for
the output directory. Cooperating concurrent writers are rejected. Do not delete
the lock file while a writer runs. Each session creates new uniquely named NDJSON
segments; previous sessions are never overwritten or deleted. Rotation occurs at
64 MiB or UTC date change; a single frame and segment markers may exceed the size
boundary. Every complete line is flushed. Segment closure and normal bounded or cooperative continuous
shutdown fsync the file. Clean-shutdown survival is tested; no power-loss,
crash-safety, lossless 24/7 or unbounded retention claim is made.

Data envelopes contain `schema_version`, `kind=data`, `channel`, `venue_coin`,
`received_at_utc` (UTC, sampled immediately after receiving the frame), and
`raw_payload` (the complete original parsed JSON object). Numbers/strings are not
converted into Nautilus types. Original wire bytes are not preserved. Trades arrays
remain arrays; receipt counts count frames, not individual trades. Empty trades
messages are markers and do not prove trade arrivals.

Discovery responses, subscription requests/acks, start/stop and segment boundaries
are recorded alongside data. Disconnect/reconnect/resubscription markers describe
unknown missing intervals. Fresh acks close a recorded gap but do not establish
lossless recovery. Transport-standard backoff handles retryable connection failures;
at most two reconnect failures are admitted. Missing/negative acks, invalid routes,
ambiguous metadata and file errors fail closed. There is no historical backfill.

After bounded proof shutdown, files are reopened and validated as an offline source. The compact
result includes hashes, reopened line count, acknowledged subscriptions, observed
frames and OBSERVED/INCOMPLETE per-family coverage. ETH real frames plus all six
real acknowledgments establish the narrow transport/storage proof; an ack alone
does not establish any data family. Raw files are not committed to Git.

## Qualification and retained gates

`tests/test_hyperliquid_raw_capture.py` exercises original-object readback,
cross-process ownership, actual CLI SIGTERM/SIGINT subprocess shutdown during
receipt and multi-DEX discovery, bounded worker failure/error races, rotation/fsync,
write/flush/close faults and reconnect/fresh-ack/gap behavior. Its single 60-second public proof runs only
with explicit `HYPERLIQUID_RAW_PUBLIC_PROOF=1` on Linux or in the exact Issue #322
Ubuntu `contracts` PR job. That job uses existing locked dependencies and workflows;
its bounded `I322_PUBLIC_PROOF` output and step summary report the actual result.
The local WebSocket test uses synthetic protocol fixtures only and cannot establish
real venue receipt. CI disk is ephemeral; CI PASS does not start persistent capture.

Pinned NautilusTrader remains `2.0.0rc5`. The official tagged DataTester is the
native read-only receipt reference:
https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/examples/live/hyperliquid/data_tester.py
Rust `LiveNodeConfig.streaming` is explicitly unsupported in that tag. No
production-compatible native automatic writer is qualified. Direct official WS
receipt/persistence proves the raw objective without requiring typed native receipt
or another actor harness. Native DataTester execution is deferred and unclaimed;
`scripts/rc5_public_data_receipt.py` is therefore unnecessary. Issue #320 separately records accepted native finite Quote/Trade/Depth/Bar and typed
batch ParquetDataCatalog evidence:
https://github.com/woshixiong/trader-assist-v0/issues/320#issuecomment-6109008461
That bounded typed batch evidence is not ongoing lossless raw retention or working
Rust LiveNode automatic streaming. Typed conversion/backtest remains separate and
does not block this raw package; no v1.231.0/RC6 migration is added.

Official metadata and WebSocket contracts:
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions

Draft publication, exact-head CI and a fresh independent Final Review precede
Control closeout. Mark Ready, merge, deployment, target-host service start/enable
and any private/trading action retain separate current human gates. Target-host
readiness and persistent collection remain unverified until separately authorized.
