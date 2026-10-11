# Hyperliquid public raw proof — Issue #322

This is a bounded foreground recorder, not a persistent host service. It discovers
the actual active HIP3 SKHX coin through public `perpDexs` and per-DEX `meta`, plus
native ETH, then subscribes to public `trades`, `bbo`, and `l2Book`. It uses existing
`websockets==16.1` and Python 3.12, with no SDK, dependency or lock changes. There is
no account, key, wallet, signer, order or private subscription interface.

```sh
PYTHONPATH=src python scripts/hyperliquid_raw_capture.py --output /tmp/i322-public-proof --duration 60
PYTHONPATH=src python scripts/hyperliquid_raw_capture.py --output /tmp/i322-public-proof --readback
```

Use a writable directory outside the repository. Capture duration is capped at
180 seconds; this package does not install or enable a service. Exit 0 means
transport/storage proof; exit 2 means INCOMPLETE. Exceptions fail the run closed.
Do not repeatedly rerun an unexpected failure: preserve the files and checkpoint
and return to Engineering Control. Quiet SKHX families are INCOMPLETE, not fabricated
data or a subscription failure. Full SKHX family coverage is a separate claim.

## File contract and limitations

One foreground process holds an exclusive advisory `flock` on `.capture.lock` for
the output directory. Cooperating concurrent writers are rejected. Do not delete
the lock file while a writer runs. Each session creates new uniquely named NDJSON
segments; previous sessions are never overwritten or deleted. Rotation occurs at
64 MiB or UTC date change; a single frame and segment markers may exceed the size
boundary. Every complete line is flushed. Segment closure and normal bounded
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

After shutdown, files are reopened and validated as an offline source. The compact
result includes hashes, reopened line count, acknowledged subscriptions, observed
frames and OBSERVED/INCOMPLETE per-family coverage. ETH real frames plus all six
real acknowledgments establish the narrow transport/storage proof; an ack alone
does not establish any data family. Raw files are not committed to Git.

## Qualification and retained gates

`tests/test_hyperliquid_raw_capture.py` exercises original-object readback,
cross-process ownership, clean subprocess shutdown, rotation/fsync, failure-stop
and reconnect/fresh-ack/gap behavior. Its single 60-second public proof runs only
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
`scripts/rc5_public_data_receipt.py` is therefore unnecessary. Typed RC5/Parquet
conversion, history/backtest #323 and sandbox #324 do not block this package.

Official metadata and WebSocket contracts:
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint/perpetuals
https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/websocket/subscriptions

Draft publication, exact-head CI and a fresh independent Final Review precede
Control closeout. Mark Ready, merge, deployment, target-host service start/enable
and any private/trading action retain separate current human gates. Target-host
readiness and persistent collection remain unverified until separately authorized.
