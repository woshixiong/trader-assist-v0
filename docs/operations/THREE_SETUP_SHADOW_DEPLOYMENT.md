# FIRST_LAUNCH_20 Shadow exact-release handoff

This procedure prepares the L0 public-data-only release. The profile is
`FIRST_LAUNCH_20_DATA_COLLECTION_ONLY`: absent accepted cost authority means
`DATA_COLLECTION_ONLY`, Strategy `NOT_EVALUABLE` with reason
`COST_AUTHORITY_ABSENT`, and submission `NOT_SUBMITTED`. No Formal, ShadowOrder,
or approval package may be created from missing cost authority. Example or zero
cost coefficients are not authority. Notification delivery is disabled; normal
L0 startup requires no notification credential and performs no notification send.

Deployment, target runtime qualification, and service start retain their current
Human Gates. A source, CI, bundle or qualification PASS does not authorize any
protected action. Keep activation absent, enable off and service stopped until
separately authorized. No private API, execution client, wallet/signing, exchange
write or real-capital path is part of L0. NautilusTrader remains exactly
`2.0.0rc5`, using the hash-locked CPython 3.12 Linux x86_64 wheel.

## Generate and download the exact GitHub artifact

Use **Three Setup exact-release bundle**
(`.github/workflows/three-setup-release-bundle.yml`) on its accepted workflow
ref after the separate publication/merge gates. It has only `workflow_dispatch`
and builds on Ubuntu 24.04 / Linux x86_64 / CPython 3.12. The frozen inputs are:

```text
release_sha=ea565fd51793904de33523c7c621f81904331c03
release_tree=ba5050f82ea0bc5305ba271ce898768ed68719b0
```

The workflow checks out the control HEAD at the dispatch run's `github.sha` in
`control/` and this historical product release in `release/`. A later control
HEAD must not substitute its source, builders, locks or tree for the product
release. Record both identities from the exact successful run's summary.
It reuses the release's hashed locks, exact rc5 wheel and existing
`scripts/build_multi_asset_registry_seed.py` and
`scripts/build_three_setup_shadow_deployment_bundle.py`. All generated files
stay outside product source. No local Intel Mac native generation is needed.

The existing canonical resolver must resolve every market without substitution:

```text
BTC ETH HYPE SOL SKHX MU SNDK XYZ100 SP500 WTIOIL
DRAM SPCX SILVER NVDA SMSN EWY GOLD XRP TSLA GOOGL
```

Official metadata and actual rc5 provider instrument objects bind Registry/PIT
identities. Missing, delisted, duplicate or ambiguous identities stop generation.
The output includes `registry-seed.json`, the existing staged/pending Registry,
`e4/run-manifest.json`, `e4/pit-universe-snapshot.json` and `bar-types.json`.
There must be exactly 40 unique external LAST streams: one 1m and one 5m bar
for each of the canonical 20 markets. The manifest binds release SHA/tree,
Registry hash, PIT hash, provider instruments, all bar types and subscription
policy. Generation does not activate the Registry current pointer.

The v3 L0 bundle consumes that complete identity without legacy bar-pair or
cost overrides. Generated config has `cost_model: null` and
`qualification_digest: NOT_QUALIFIED`, enable `0`, mode `DISABLED`, and no
qualification artifact or activation permit. Unqualified configuration cannot
authorize normal startup. Current public metadata and observation timestamps
can differ across builds; each run is independently hash-bound.

From the exact successful Actions run, download artifact
`three-setup-release-<full-release-sha>-<run-id>-<run-attempt>`. The Actions page
provides a download; alternatively use one local download command, substituting
the exact recorded run/artifact and a new download directory:

```sh
gh run download <exact-run-id> --repo woshixiong/trader-assist-v0 \
  --name <exact-artifact-name> --dir <new-download-directory>
```

The outer artifact contains only `three-setup-release-bundle.tar.gz`. Its inner
payload contains `bundle/` and `handoff/{anchors.env,provenance.json}`. Never add
handoff files to `bundle/`: the existing verifier requires an exact file set.
GitHub upload-artifact normalizes outer filesystem permissions; preserve the
tar.gz intact so its inner `remote-qualification.sh` retains mode `0750`.
Artifact PASS grants no deployment/runtime/service authority. A successful
GitHub build is not target qualification or permission to start a service.

## Verify the transfer and install only under its Human Gate

Preserve all five emitted `EXPECTED_*` anchors in the canonical reviewed
handoff independently of the transfer folder: release SHA, release tree,
release-manifest canonical digest, bundle-manifest SHA256 and remote-script
SHA256. The exact run summary emits these five keys and no sixth anchor:

```text
EXPECTED_RELEASE_SHA
EXPECTED_RELEASE_TREE
EXPECTED_RELEASE_MANIFEST_CANONICAL_DIGEST
EXPECTED_BUNDLE_MANIFEST_SHA256
EXPECTED_REMOTE_QUALIFICATION_SHA256
```

Bind those values to the exact successful run in the canonical reviewed
Operations handoff before transfer. The archive's `anchors.env` is a convenience
copy, not independent authority. Upload the single unchanged tar.gz through
FinalShell SFTP/file manager. Under separate current Operations authority, use
one contiguous block in the already-connected FinalShell server Terminal to
check archive paths/types, extract into a new staging directory, and confirm
`bundle/remote-qualification.sh` mode `0750`. Never rebuild on the Mac or infer
expected anchors from the transferred archive/folder.

Before executing uploaded code, verify the raw bundle-manifest and remote-script
hashes against those independent anchors. Invoke the generated
`remote-qualification.sh --verify` with the four independent release/bundle
arguments. It checks the regular-file path set, hashes/sizes, retained release
identity, exact wheel compatibility and stopped/default-off state. No uploaded
code may run before the independent hash checks.

Installation requires separate current deployment authorization and the same
independent anchors. The installer does not stop, start, restart or enable a
service. Existing installation/config paths are refused; do not work around
that refusal by deleting source or durable evidence. Replacement requires
Engineering Control's bounded predecessor/rollback disposition while the
service is already stopped and the activation permit is absent. Retain the
old release and E4 lineage intact. A failed or unproven rollback returns to
Engineering Control. The locked runtime/pilot environment excludes operator
installation; target imports must resolve to the exact staged source.

## Qualify the target before any normal start

Under separate current target-runtime authority, qualify the full candidate
on the bound Tokyo host using the existing rc5 capture and production paths.
A single-instrument connectivity probe is not full-launch qualification.
Historical bars and callback counts cannot establish live interval completeness
or provider headroom. Every required unknown remains `INCOMPLETE`.

The explicit default-off target qualification route is:

```sh
python scripts/e4_nautilus_public_data_probe.py --qualify-l0 \
  --config-path /etc/trader-assist-v0/three-setup-shadow.json \
  --evidence-path /var/lib/trader-assist-v0/three-setup-shadow/qualification-NEW-RUN \
  --result-path /var/lib/trader-assist-v0/three-setup-shadow/qualification.json \
  --run-seconds 2400
```

This command requires separate current runtime authority. It reuses the existing
production node and consumer with new isolated evidence; it does not control a
service. Keep the generated Registry/E4 identity intact. Qualification alone
sets instrument refresh to zero and uses public rc5 `LoggerConfig` /
`FileWriterConfig` through `LiveNodeBuilder.with_logging` for a dedicated,
non-rotating TRACE JSONL file. Normal Shadow logging is unchanged.

The qualification LiveNode name is the digest-bound current-run identity marker.
The first dedicated-file record must be the native startup-header separator with
that exact component. Pre-marker content, missing/duplicate/mixed identities,
malformed or unmatched native evidence and setup/write/sync/path/truncation
ambiguity are `INCOMPLETE`. No synthetic pre-build or end marker is required.
Sync the complete regular file through `logging_sync_to_disk`; retain its exact
path, device/inode and SHA256 in the qualification report. Raw HTTP TRACE bodies are not authority. B1d accepts control TRACE only
from `nautilus_network::websocket::client`, with exact `Received ping frame
(<integer> bytes)` and `Received pong` messages. Each rolling 60s window adds
automatic pongs, protocol-pong receipts plus at most two data-connection epochs
as the automatic-ping upper bound, and at most two planned-close controls to
the native outbound forecast. The result must remain <=1000. Missing or
ambiguous control evidence cannot PASS.

The exact clean rc5 metadata startup sequence is `spotMeta`, `allPerpMetas`,
`outcomeMeta`, `allPerpMetas`, `perpDexs`: five Info requests / 100 base weight.
Any retry, fallback, transport failure or unexpected metadata request prevents
PASS. Each of the 40 warmup dispatches must match exactly one native completion.
Filtered callback/completion bar counts prove successful data delivery only.
Native CandleSnapshot extra-weight debits determine actual weight; absence of a
debit proves extra=0 only in a complete successful current-run log. Require
actual weight <= its conservative reservation and rolling-60s warmup <=400.

Native HTTP proof does not prove WebSocket outbound control counts. Missing
provider/queue/drop/resource evidence remains `INCOMPLETE`; do not fill it with
zero, a callback count, a forecast from another transport or an example. A
non-PASS report cannot authorize normal startup.

Record the exact 40 bar registrations plus 20 BBO, 20 trade and 20 Depth10 native
registrations, and the rc5 request/source proof or actual counters where public.
The metadata cohort independently requires REST weight <=600 per 60s, zero
429/throttle events, followed by a full 60s quiet interval. L0 only delays the
existing Nautilus history requests with a rolling-60s reservation budget of
400; the hard maximum remains 600 with 200 reserved headroom. Reserve each
CandleSnapshot conservatively as 20 + floor(raw maximum response rows / 60).
Do not replace or bypass the rc5 client or limiter.

After all historical warmup streams are ready, opt into exactly one bounded
qualification reconnect through `Strategy.reconnect_socket` for
`HYPERLIQUID_CLIENT_ID` and `hyperliquid-data-streams`. A returned call is not
recovery proof: retain matching DISCONNECTED then CONNECTED transitions and
all 40 streams fresh within 60s, followed by 15 consecutive live minutes.
Each market requires at least 15 completed 1m and three completed 5m bars,
p95 close-to-authority <=30s and maximum <=60s, with no missing, conflicting,
future or unexplained duplicate finalized bars.

Retain the frozen provider, CPU/memory/swap/disk, storage/drop and queue evidence.
The rc5 runner queues are unbounded: physical occupancy percent is
`NOT_APPLICABLE_UNBOUNDED`. Use public queue-state evidence and actual resource/
storage evidence. Real finite authority-bearing buffers must show their actual
capacity and <=80% maximum / <=20% end occupancy. Missing proof cannot PASS.

Persist the resulting digest-bound `qualification.json`. Its existing `end_ns`
is the sole completion-time authority and is included in the report digest.
Bind the report to the candidate release SHA/tree, manifest, PIT snapshot,
profile, PASS status and empty blockers; bind its digest in the v3 config.
Use the non-secret qualification evidence example to retain observed results,
independent anchors and protected-gate state. Never manufacture a PASS report
from examples, defaults, callback counts or unavailable provider measurements.

## Post-run verifier resources and production disk growth

Native evidence is bound with incremental SHA256, exact path/device/inode/size/
mtime/ctime checks before/open/after each pass, final LF, and current-run startup
identity. Canonical-envelope SHA256 keys in a private SQLite index reject
repeated envelopes; duplicate JSON keys fail before canonicalization. HTTP and
WS passes recheck the same immutable binding. No raw whole-log object or
all-record collection is retained.

Verifier budgets are 64 KiB input chunks, 1 MiB envelopes, a 4 MiB SQLite cache,
a 512 MiB database, bounded journal/transactions, and 64 ordinary WS diagnostic
windows plus the exact peak and first failing window. Every candidate rolling
window is evaluated; diagnostic retention does not limit the proof. Budget,
index, mutation, parse or scratch-cleanup failures cannot PASS.

The separately persisted `verifier-resources.json` records PRE_NATIVE_BIND,
POST_NATIVE_BIND, POST_HTTP_VERIFY, POST_WS_VERIFY and PRE_REPORT_WRITE. It
contains RSS, process-lifetime VmHWM, MemTotal/MemAvailable, swap capacity and
counters/deltas, native-log/index bytes, timestamps and elapsed time. Periodic
checks retain scalar maxima only. Missing evidence, host memory above 80%, swap
activity or trail-write failure blocks qualification. These samples never pad
or alter the original >=900-second live resource window.

Actual root usage still measures the whole filesystem, including TRACE and
scratch. Seven-day projected additional growth excludes only the exact owned
qualification TRACE identity and exact tracked temporary index artifacts.
Production E4/evidence/database/WAL and unknown files remain included, even
when their basenames resemble diagnostics. Identity ambiguity fails closed.
The final disk check preserves the live rate denominator and conservative
projection; verifier time cannot dilute durable growth. The resource trail
itself remains included durable output.

## Mandatory retained-log replay before another live qualification

After separately authorized merge, release and deployment of this repair,
replay the retained approximately 379,189,199-byte failed-run native log before
any second 2400-second live qualification. Bind the original failed-run
manifest, not the repaired release's manifest. The replay reports the verifier
source SHA256 separately from historical release SHA/tree.

Resolve retained paths and create a new dedicated scratch directory under the
authorized target execution procedure. The result path must be new, inside
that directory, and cannot be named `qualification.json`. The replay rejects
existing outputs, symlinks/hard-link overwrites and live/config arguments. It
constructs no application, opens no provider connection and performs no service
operation. Its only writes are dedicated scratch/resource/result artifacts.

```sh
: "${RETAINED_NATIVE_LOG:?resolve original native.jsonl}"
: "${RETAINED_MANIFEST:?resolve original failed-run manifest}"
: "${DEDICATED_SCRATCH_ROOT:?resolve new dedicated scratch directory}"
: "${DEDICATED_REPLAY_RESULT:?resolve new result inside scratch directory}"
python scripts/e4_nautilus_public_data_probe.py \
  --replay-native-log "$RETAINED_NATIVE_LOG" \
  --manifest "$RETAINED_MANIFEST" \
  --verifier-scratch-root "$DEDICATED_SCRATCH_ROOT" \
  --result-path "$DEDICATED_REPLAY_RESULT"
```

Without historical facts this proves current retained-file structure and
resources only. `unavailable_facts` and
`UNAVAILABLE_FACTS_REQUIRE_CONTROL_DISPOSITION` explicitly preserve the gap;
they are not a waiver or qualification evidence. Add `--replay-facts` only for a
retained, independently located facts document with:

- `schema: l0-native-replay-facts/v1`, original `manifest_hash`, and exact
  `native_sha256`;
- `facts`: original `dispatches`, `sync_succeeded`, and, where available,
  `epochs`, `outbound_forecast`, `close_reserve`,
  `native_constant_upper_bound`, `planned_reconnect_request_ns`;
- `locators`: a nonempty durable evidence locator for each supplied fact.

The facts document is bounded to 1 MiB. Do not manufacture missing facts,
claim a new sync proves historical completion, or replace missing transitions
with defaults. HTTP and WS predicates replay independently where their facts
are available, retaining the original sync requirement and exact source-bound
semantics. A structural PASS cannot conceal a semantic blocker.

Required pre-live disposition is structural binding PASS, process survival,
RSS/HWM <=256 MiB, no evidence mutation, and explicit semantic disposition.
Inspect measured maximum envelope size and index peak demand as well. Any
structural, resource, semantic, missing-fact or budget blocker returns to
Engineering Control before live qualification. A local Mac test skip does not
prove the Linux memory envelope.

Replay has a separate diagnostic schema/status and no qualification digest,
profile or completion `end_ns`. It cannot mint qualification PASS, refresh the
one-hour TTL or replace qualification.json. Replay success does not authorize
live qualification or service activation. Keep the separate runtime gates,
20 markets, 2400-second route and DEFAULT_OFF state intact.

## Revalidate startup and retain the separate service-start gate

Before a separately authorized normal start, run
`scripts/three_setup_shadow_preflight.py` and the runtime's `--validate-only`
mode against the exact staged release, concrete config and independently
expected release anchors. The preflight validates exact E4/Registry identity,
rc5 dependency closure/import origin, qualification digest/identity and B1b.
The wrapper repeats preflight and retains the external activation permit,
explicit enable/mode, exact release checks and `Restart=no`.

Startup requires an exact positive integer `end_ns` (bool is invalid) and
current wall-clock nanoseconds satisfying:

```text
0 <= now_ns - end_ns <= 3_600_000_000_000
```

Age zero and exactly 3600 seconds are permitted. Missing, malformed, nonpositive,
future or older completion times fail closed. Qualification mtimes, config
mtimes, process uptime, chat times and GitHub times are not authority. A stale
qualification requires a fresh target qualification before a later process or
service start. A continuously running process is not automatically stopped
when the one-hour startup TTL elapses; existing continuous health/freshness/
storage gates remain in effect. Every later fresh start checks B1b again.

Only current separate service-start authorization can supply the activation
permit and approved enable/mode and start the service. No notification file or
endpoint is needed. Record first-live UTC, exact release/PIT/Registry identity
and qualification reference, then follow the existing T+2h/T+24h observation
route. Source acceptance, target qualification and service activation remain
separate evidence and authority boundaries.
