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
release_sha=1d8e8ca08f4f526f72b2253acf3c9a71defdbe7b
release_tree=2daee287c155fa33e8af5894f3825d7eddb09e70
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

## Accepted-contract candidate: isolated replay-only diagnostic deployment

> **Effective status:** This subsection is a **proposed Operations contract
> amendment** until its one-file Draft PR has passed fresh Final Independent
> Review, received distinct current human Mark Ready and merge authorizations,
> been merged into `main`, and received a fresh independent Operations
> acceptance. A Plan V2 PASS, artifact build, staging verification, this text on
> an unmerged branch, and any earlier host inventory confer **no** target action.
> The operator's executable FinalShell block must be generated and independently
> checked **only after** contract effectiveness and the specific human gate.
> No command in this section authorizes present deployment or replay.

### Purpose, legal scope, and terminal status

`REPLAY_ONLY_ISOLATED_DIAGNOSTIC_DEPLOYMENT` is a narrowly defined, new,
diagnostic-only form of deployment: a hash-verified repaired release is placed
in a *new*, uniquely owned staging root; its exact locked Python 3.12/rc5
runtime is installed entirely inside that root and independently verified;
the repaired source is available **only** for subsequent offline replay of
the retained, original failed-run native log. It does not replace, install
into, or run the predecessor service. Only after this Operations amendment is
effective, separately accepted and the deployment is actually verified on
target may `REPLAY_ONLY_DIAGNOSTIC_DEPLOYMENT_ACCEPTED=YES` satisfy the
existing phrase "after ... deployment of this repair" **solely for this
historical diagnostic replay prerequisite**. A copied archive, hash check,
`--verify`, or an unaccepted staged root alone does **not** satisfy it.

At every point on this route record `NORMAL_RELEASE_DEPLOYED=NO`,
`NORMAL_TARGET_QUALIFICATION=NO`, `SERVICE_START_AUTHORIZED=NO`,
`REPLAY_AUTHORIZED=NO` until a later *separate*, current human replay gate.
`--install` against the occupied normal roots is **PROHIBITED**. In
particular `--verify` is **staged integrity/default-off proof**, never
installation or acceptance of a replacement deployment. A diagnostic replay
result, even a structural PASS, is never `qualification.json`, startup TTL,
a target-live 2400s qualification, or an exchange/trading authorization.
These definitions do not amend Product/Security limits or the normal deployment
and service-start gates elsewhere in this document.

### Frozen identity and independent authority inputs

Do not substitute control `main`, a later rebuilt artifact, or the
archive's own `handoff/anchors.env` for these **external** identities:

| Object | Exact frozen identity |
| --- | --- |
| Repaired product release commit | `1d8e8ca08f4f526f72b2253acf3c9a71defdbe7b` |
| Repaired product release tree | `2daee287c155fa33e8af5894f3825d7eddb09e70` |
| Successful bundle workflow | Run `37566655478`, attempt `1`, job `112615806940` |
| Single GitHub artifact | ID `11459171241`, `three-setup-release-1d8e8ca08f4f526f72b2253acf3c9a71defdbe7b-37566655478-1` |
| Exact artifact expiry | `2026-10-21T03:26:20Z`; unavailable/expired means replan, **not** alternate download |
| Independent release SHA anchor | `1d8e8ca08f4f526f72b2253acf3c9a71defdbe7b` |
| Independent release tree anchor | `2daee287c155fa33e8af5894f3825d7eddb09e70` |
| Independent canonical release-manifest digest | `008abcd4ca9e1b95327e226de577665f292b55cffb6054b680916869ee31f85a` |
| Independent raw bundle-manifest SHA256 | `55917a384abe6f8ea6251068d59293620a26036d8298d31decfb41ac943efc75` |
| Independent raw remote-qualification.sh SHA256 | `eb537d6ad26b05f09c4fa6f6c2c38c0d745806e57ccfea28a1630dff463dfb36` |

The five external anchor **source** is Issue #163 exact comment
[`6030468275`](https://github.com/woshixiong/trader-assist-v0/issues/163#issuecomment-6030468275),
bound to that successful run/job, not the transferred archive. The separately
reported outer GitHub **ZIP** SHA256 is
`b138ba4d4e4b2bf5e8cd90d436d5d2fe8808d82d7dcbb0ef884fdafc4ef34783`;
it is **not** the inner `three-setup-release-bundle.tar.gz` SHA256, nor
a sixth release anchor. Before *any* FinalShell SFTP/transfer, download
only the exact artifact into a new local directory, independently inspect the
one-member outer ZIP, measure the **inner tar.gz** SHA256 over its actual bytes,
bind the tar name/hash/size and artifact ID/run/attempt to a canonical GitHub
pre-transfer evidence record outside both archives, and verify that record
again on target. A missing inner digest or a mismatch stops **before SFTP**.

The failed-run **predecessor evidence** must remain a different immutable
identity: old release `ea565fd51793904de33523c7c621f81904331c03`,
old tree `ba5050f82ea0bc5305ba271ce898768ed68719b0`,
original `e4/run-manifest.json` **recorded `manifest_hash` field**
`9d13c0ee77dd3c123b667ac0151ce24d681357d0429ad8116182eb945aa7bdf4`
(the field was read but its canonical digest was **not** independently
recomputed), and original `native.jsonl` **379189199 bytes**, SHA256
`453d725caa6cdbcc47003417fc1cb8545dd28359e14914f068debcd5c3d57155`.
These are historical identities; the new bundle's `e4/run-manifest.json`
must **never** be used as the replay `--manifest`. Record the repaired
verifier's source SHA256 separately.

### Phase D0 — contractual and read-only target preflight

Require all of: effective merged Operations contract; fresh independent
Operations acceptance; separately recorded, **current exact-scoped human
authorization for isolated diagnostic target deployment** (including new
path creation, transfer, private namespace mount and isolated dependency
installation); renewed read-only host inventory and available artifact.
No preauthorization is inferred from Phase A build, Plan/Review PASS or an
earlier deployment attempt. The operator surface is the already-configured
FinalShell Tokyo host (`ip-172-26-10-127`), *subject to fresh host identity
verification*. No deployment or download/transfer to host is allowed before
this phase's gate; the local artifact digest is measured before transfer.

Preflight the entire path chain using `lstat`/`openat`-style non-following
checks and retained filesystem/mount identity. The following paths must not
preexist in **any** form (including dangling symlink), alias an existing
device/inode, be a mountpoint, or traverse an untrusted symlink:

* New stage: `/opt/trader-assist-v0-replay-only-37566655478-1`.
* Separate new persistent replay container root:
  `/var/tmp/trade-os-replay-37566655478-1`. It is an ordinary host-filesystem
  container and is **never** itself the replay tmpfs mountpoint.

Require trusted, non-symlink parents, safe mount boundaries, no hardlink or
bind-mount alias, verified free memory/disk/inodes, a preexisting
`traderassist` account/group and an operator with exactly the capabilities
needed for the later separately authorized actions. Require the original
predecessor service currently **inactive/dead and disabled**, absent
activation permit, default-off configuration, and unmodified original
release/log/E4 state. A host-state mismatch, path collision, missing kernel
namespace or runtime facility, insufficient resources or unprovable ownership
is `CONTROL_REPLAN` **before any mutation**. Never create/clear an old root
to make the installer work.

After the gate, make only the two *new* roots with `O_EXCL`/non-following
creation and immediately capture dev/inode/owner/group/mode/mount identities.
Stage must be `root:traderassist`, mode `0750`; all stage subdirectories
are confined under it. The replay container root is newly owned, inaccessible
to other users and initially empty. Its later `work/` and `proof/` children
are created only after the separate replay human gate and fresh replay preflight;
the root itself remains persistent host storage rather than a mountpoint. Grant
replay-only data access through
existing permitted read rights, not by `chmod`/`chown` of historical files.
Preserve, without byte, timestamp, permission or service changes:
`/opt/trader-assist-v0`, `/etc/trader-assist-v0`,
`/var/lib/trader-assist-v0`, all old E4 lineage/native logs, systemd units,
environment/credentials and any activation permit state. Do not reload,
enable, start, stop or restart any service.

### Phase D1 — one exact archive, inspect before extraction, hash before code

Only the independently hashed inner `three-setup-release-bundle.tar.gz`
may be transferred intact through FinalShell SFTP into the owned new stage.
Verify its exact recorded SHA256 and byte size on target against the **outside**
GitHub pre-transfer evidence. Do not trust the archive's own anchors.

Using **trusted host-provided Python 3.12 standard-library archive inspection**
(not transferred code), enumerate all tar members **before extracting any**;
reject absolute paths, `..`/`.`/empty components, backslashes, duplicate or
case-ambiguous normalized names, links of either kind, devices, FIFOs, sockets,
sparse/PAX path overrides, unknown types, setuid/setgid/sticky bits, unexpected
owners/modes, excessive names/count/sizes and any path not underneath the
exact `bundle/` or `handoff/` prefixes. Require only regular files and
directories, at most 4096 members, per-file at most 512 MiB and cumulative
declared regular-file bytes at most 1 GiB; enforce these limits *while
streaming extraction*, not merely from untrusted headers. Refuse all existing
destinations and create files exclusively without following links; ignore
archive numeric owner/group, apply the new stage's accepted ownership and
least privileges. Extraction may touch **only** the new root. The expected
payload is `bundle/` plus external-authority-free
`handoff/{anchors.env,provenance.json}`; `handoff` has no execution or
authority status.

Before *any* transferred script/bytecode/module executes, check **raw bytes**
of `bundle/bundle-manifest.json` =
`55917a384abe6f8ea6251068d59293620a26036d8298d31decfb41ac943efc75`,
and `bundle/remote-qualification.sh` =
`eb537d6ad26b05f09c4fa6f6c2c38c0d745806e57ccfea28a1630dff463dfb36`.
Then, with a **trusted external** verifier, parse the raw manifest and enforce
the complete manifest-declared regular-file path set, hashes, byte sizes, no
unlisted/duplicate file or directory symlink, the canonical repaired release
SHA/tree/manifest digest, exact Linux wheel hash, and remote-script mode
**0750**. Recheck owner/inode/path ancestry after extraction. If these
prerequisites fail, **no transferred code may run**. Never modify/re-sign the
archive, verifier, signed script, embedded manifest, dependencies or installer.

### Phase D2 — strictly contained Python 3.12 / NautilusTrader rc5

The exact extracted repaired source is
`STAGE/bundle/payload/src` (with script source beneath
`STAGE/bundle/payload/scripts`), never the old
`/opt/trader-assist-v0`. Here `STAGE` denotes the *new, preflighted*
stage root, not an unrestricted shell variable. Within **that same root only**
create:

* `runtime-venv/`: dedicated CPython **3.12**, created with
  `python3.12 -m venv --without-pip`; runtime distributions **only**
  from the entire immutable `payload/requirements-runtime.lock` and
  `payload/requirements-nautilus-pilot.lock` (no `pip`/tooling distribution
  inside this exact-runtime venv). Every runtime requirement is version-pinned
  with SHA256; install from checked hashes and wheels only, never an sdist.
* `pip-tool-venv/`: separate, contained **installation/verification tooling
  only** using CPython 3.12 + its supplied `ensurepip`; it must never
  enter runtime `sys.path`, `PYTHONPATH` or native replay execution.
  Independently retain its interpreter/`pip --python` capability, command
  origin and tooling provenance. The tool environment is an implementation
  aid within the same approved new root, **not** a second runtime, product
  release or provider. If this bounded separation is unavailable, fail closed.

The no-`pip` runtime is necessary because the frozen
`check_dependency_lock.py --verify-target-runtime-installed` rejects
**all** distributions outside the exact runtime+rc5 locks. The frozen
`--pip-check-with` implementation needs an interpreter **with pip** to
invoke `pip --python <runtime-interpreter> check`; supply the accepted
**isolated pip-tool-venv interpreter** for that argument, not the old venv
or a host/global/user-site runtime. Use the pip tool's
`pip --python <runtime-venv>` for installation and pip-check. No global
`pip install` and no package insertion into the original root. Reject a
pip version unable to check the pip-free venv this way.

Set and prove `HOME`, `TMPDIR`, `PIP_CACHE_DIR`,
`XDG_CACHE_HOME`, `PYTHONPYCACHEPREFIX` (or
`PYTHONDONTWRITEBYTECODE=1`), `PYTHONNOUSERSITE=1`,
`PIP_CONFIG_FILE=/dev/null`, `PIP_DISABLE_PIP_VERSION_CHECK=1`,
`PIP_NO_INPUT=1`, `PYTHONSAFEPATH=1`, and pip index / trusted-host
configuration so **every** cache/temp/download/build/write target is an owned
new stage path; disable unapproved extra indexes, proxy credential helpers
and private package APIs. Public pinned/hash-verified Python wheels may be
fetched only from the explicitly accepted public index with no secrets.
Install runtime lock with `--require-hashes --only-binary=:all:` and the
exact rc5 `nautilus-trader==2.0.0rc5` **Linux x86_64 CPython 3.12 wheel**
with SHA256
`eab45fafd2312deda1236554c49a9798bfc76bc8465af864878e2f70189ebebe`
using `--require-hashes --no-deps --only-binary=:all: --no-index` and
`--find-links` restricted to the independently checked inner bundle.
No wheel substitution, new lock, unreviewed network or user-site package.

**Mandatory signed-script interpreter seam:** the immutable
`remote-qualification.sh --verify` calls `python3.12` **by name** three
times; its first call uses `-I -B` and ignores `PYTHONPATH`.
For the entire signed `--verify` invocation, set a sanitized explicit
`PATH` with `STAGE/runtime-venv/bin` first; invalidate shell command
hashing and prove `command -v python3.12` resolves **inside the approved
runtime-venv/bin**. Run that exact command both with normal flags and
`-I -B` and independently prove `sys.executable`/its invoked venv
entrypoint, `sys.version_info[:2] == (3,12)`, `sys.prefix` equals the
approved runtime venv, `sys.base_prefix` is the inspected trusted base
interpreter, user-site disabled and `sys.path` has **no** predecessor,
global third-party or tool-venv packages. A venv's symlink to its trusted
CPython executable and base standard library is permitted; **importing
third-party code from the base interpreter is not**. A mismatched
`python3.12` command resolution immediately stops; never patch the
signed script or mask the mismatch with only `PYTHONPATH`.

Only **after** D1 hashes and D2 interpreter preflight, run the existing
signed script **unchanged** with exactly these four independently retained
arguments (no `--install`):

~~~sh
# Future gated operator recipe fragment ONLY; not an authorization to execute.
bundle/remote-qualification.sh --verify \
  1d8e8ca08f4f526f72b2253acf3c9a71defdbe7b \
  2daee287c155fa33e8af5894f3825d7eddb09e70 \
  008abcd4ca9e1b95327e226de577665f292b55cffb6054b680916869ee31f85a \
  55917a384abe6f8ea6251068d59293620a26036d8298d31decfb41ac943efc75
~~~

Run it with cwd/physical `BUNDLE_ROOT=STAGE/bundle` as the script computes,
the controlled runtime-venv-first `PATH`, trusted no-secret environment and
no implicit `sudo` environment reset. Then run the frozen exact
`payload/scripts/check_dependency_lock.py
--verify-target-runtime-installed --staged-source STAGE/bundle/payload/src
--pip-check-with STAGE/pip-tool-venv/bin/python3.12` **using
`STAGE/runtime-venv/bin/python3.12`**, cwd
`STAGE/bundle/payload` (so the lock-relative reads are exact), and set
`PYTHONPATH` exclusively to the verified
`STAGE/bundle/payload/src:STAGE/bundle/payload`. Independently execute
the pip-tool interpreter's `-m pip --python
STAGE/runtime-venv/bin/python3.12 check`. Capture a fresh full
`sys.path`, `site`, `importlib.metadata` distribution closure, runtime
`sys.prefix`, rc5 version/module/wheel origin, project import
`trader_assist_v0.__file__` under the checked extracted source, verified
source binding and absence of `/opt/trader-assist-v0` or any global/user-site
third-party import. Reconfirm `Restart=no`, default enable=0/mode=DISABLED,
inactive/disabled unit and **absent** activation permit. Unknown import
origin, pip error, stale artifact or altered source is `CONTROL_REPLAN`.

### Phase D3 — separate replay gate, original-file immutability and real disk cap

**After** D0–D2 actually pass and a complete, independently accepted target
deployment record exists in GitHub, Engineering Control may record
`REPLAY_ONLY_DIAGNOSTIC_DEPLOYMENT_ACCEPTED=YES`
(`NORMAL_RELEASE_DEPLOYED=NO` still). This is *not* replay permission.
Acquire a **new, explicit current human authorization for the original
379189199-byte log replay**, with fresh host/resource/old-log preflight and
a separately specified output path. Neither deployment authorization nor
an earlier Plan/Review grants this second gate.

Use only the **old** `native.jsonl` and **old** `e4/run-manifest.json`
opened read-only from their resolved original locations. Under non-following
open/stat checks, prove original manifest's recorded SHA/tree and
`manifest_hash` field; separately recompute and retain the canonical
manifest digest (do not silently treat the original recorded field as an
independently verified digest). Verify native log's exact 379189199-byte
SHA256 and stream-bound dev/inode/size/mtime/ctime at **pre-open, open,
per-pass and post-close**. Reject symlinks, hardlinks/path alias or changed
content and any unproven source/manifest mapping. No alteration of old
timestamps, mode or source; if historic read access is unavailable, stop for
Control, not `chmod`/copy-to-live.

The accepted replay root remains the already-created, exclusively controlled
host directory from D0:

~~~text
REPLAY_ROOT=/var/tmp/trade-os-replay-37566655478-1
WORK=$REPLAY_ROOT/work
DURABLE_PROOF=$REPLAY_ROOT/proof
~~~

This Operations amendment installs **one active replay-controller contract** for
this route. After this amendment is independently reviewed, merged and accepted,
the earlier private-namespace / complete remaining WORK-tree byte-export recipe
is no longer an alternate execution path. For this replay-controller route only,
the **complete-WORK byte-copy contract is superseded** by a complete
surviving-WORK inventory with streaming SHA256 plus the bounded authoritative
durable artifacts below. Scratch SQLite/index/journal bytes are non-authoritative
intermediates: inventory their surviving identities and hashes, but do not copy
their bytes into `DURABLE_PROOF`.

The exact release must contain
`scripts/p4a/run_e4_replay_diagnostic.py`. It is the only future D3 replay
launcher. It creates no static systemd unit, daemon, container, new Linux
account, custom mount namespace or seccomp framework. Direct invocation of
`scripts/e4_nautilus_public_data_probe.py` for the target retained-log replay is
superseded by this controller route.

Before any transient unit start, the controller must fail closed unless all of
the following are true:

* production `trader-assist-v0-three-setup.service` is exactly inactive and
  disabled, and the activation permit is absent;
* exact staged Python, exact unchanged verifier source and exact staged
  controller are regular files under the accepted staged root;
* original `native.jsonl` and original historical `e4/run-manifest.json`
  have frozen non-following path/dev/inode/size/mode/uid/gid/mtime/ctime and
  full SHA256 bindings; an optional authentic replay-facts document receives the
  same binding;
* `/proc/meminfo` reports `MemAvailable >= 1408 MiB`;
* `REPLAY_ROOT` is the accepted existing root while `WORK` and
  `DURABLE_PROOF` are still absent;
* the pre-existing replay identity is exactly `UID=999`, `GID=988`; no account
  creation or permission repair is allowed.

The controller may then create `WORK` and root-only `DURABLE_PROOF` and start
one transient `systemd-run` service with the frozen mature systemd controls:

~~~text
ProtectSystem=strict
BindReadOnlyPaths=<STAGE>
BindReadOnlyPaths=<ORIGINAL_NATIVE_JSONL>
BindReadOnlyPaths=<ORIGINAL_E4_RUN_MANIFEST_JSON>
BindReadOnlyPaths=<OPTIONAL_AUTHENTIC_REPLAY_FACTS_JSON>
TemporaryFileSystem=<WORK>:size=768M,nosuid,nodev,noexec,mode=0770,uid=0,gid=988
ReadWritePaths=<DURABLE_PROOF>
ProtectHome=yes
PrivateNetwork=yes
PrivateDevices=yes
NoNewPrivileges=yes
CapabilityBoundingSet=CAP_SETUID CAP_SETGID CAP_KILL
MemoryMax=1280M
TasksMax=16
RuntimeMaxSec=2400s
Restart=no
PrivateTmp=no
~~~

`RuntimeMaxSec=2400s` is an emergency outer backstop only. The controller owns
the normal verifier deadline. Do **not** add `SystemCallFilter`,
`RestrictNamespaces`, `RestrictAddressFamilies`, `SystemCallArchitectures`,
`MemoryDenyWriteExecute`, `LockPersonality` or `RestrictRealtime`; the failed
spike does not authorize a third synthetic start or a new hardening experiment.

Inside the already-created systemd filesystem boundary, before verifier launch,
a bounded child using the exact replay credentials must prove:

~~~text
UID=999
GID=988
SUPPLEMENTARY_GROUPS=EMPTY
CAPABILITIES=EMPTY
NO_NEW_PRIVILEGES=YES
~~~

For both original inputs, `O_RDONLY|O_NOFOLLOW|O_CLOEXEC` must succeed and
`fstat` dev/inode must equal the frozen host binding. Separate
`O_WRONLY|O_NOFOLLOW|O_CLOEXEC` and `O_RDWR|O_NOFOLLOW|O_CLOEXEC` opens, with
no `O_TRUNC` and no `O_CREAT`, must fail **exactly with `EROFS`**. Any success
or any other denial stops before verifier launch. The same replay identity must
also be unable to create a file in root-only `DURABLE_PROOF`.

The verifier child uses the identical UID/GID/empty-groups/no-new-privileges
state and the unchanged
`scripts/e4_nautilus_public_data_probe.py`. Its exact argv is limited to the
staged Python/verifier and replay-only flags. It uses `stdin=/dev/null`,
`shell=False`, `close_fds=True`, no credential/private-API environment, and an
explicit minimal environment. `TMPDIR`, `TMP`, `TEMP`, `SQLITE_TMPDIR`,
`HOME` and `XDG_CACHE_HOME` all resolve under `WORK`;
`PYTHONDONTWRITEBYTECODE=1` and `PYTHONNOUSERSITE=1`. `WORK` is the only
child-writable filesystem.

The verifier gets a normal **1800-second** deadline. On timeout the controller
sends `SIGTERM`, waits at most 10 seconds, then sends `SIGKILL` if required and
reaps the child. Ordinary timeout or verifier failure does not skip evidence
retention. After child completion, a reserved **300-second** evidence window is
used for post-source hashing, inventory, durable writes, fsync and readback.
The service cgroup remains `MemoryMax=1280 MiB`, `TasksMax=16`, with zero
accepted swap activity; the verifier's existing independent semantic
`VmHWM/RSS <=256 MiB` criterion remains unchanged.

`stdout` and `stderr` are continuously drained. Each durable retained log is
hard-capped at **8 MiB**, while the controller still computes the SHA256 and
byte count of the **full** stream and records whether truncation occurred. A
truncated retained log must carry `TRUNCATED=YES` in `child-exit.json`; no
unbounded stream buffer or complete-log requirement is permitted.

After the child is reaped and no controller writer is active, generate a
**complete surviving-WORK inventory** using non-following traversal. Only
directories and regular files are accepted. Record relative path, mode, uid,
gid and size for every entry, and streaming SHA256 for every regular file.
Symlink, special-file or unexpected regular-file hardlink ambiguity is evidence
failure. A verifier scratch/index/journal that has already been cleaned is not
fabricated; a surviving one is inventoried and hashed but its bytes are not
duplicated to durable proof.

The bounded durable proof set is:

~~~text
controller-result.json
replay-diagnostic.json
replay-verifier-resources.json
child-exit.json
source-binding.json
unit-properties.json
child.stdout.log
child.stderr.log
work-inventory.json
proof-manifest.json
~~~

Only `replay-diagnostic.json`, `replay-verifier-resources.json` and the two
capped logs are copied from `WORK`. The controller-created JSON evidence is
written directly by the root supervisor. `proof-manifest.json` records each
durable file's size/SHA256, proof-directory fsync completion, post-fsync
readback SHA256 equality, original input pre/post bindings, requested/read-back
unit properties, controller/verifier identities and
`DURABLE_EVIDENCE_EXPORT=PASS|FAIL`. Original inputs are re-opened,
re-stat'ed and fully re-hashed after the verifier; any drift invalidates the
evidence.

No replay result may advance unless `DURABLE_EVIDENCE_EXPORT=PASS`. Verifier
exit failure with intact durable evidence remains a diagnostic failure with
retained proof, not an excuse to rerun. If the supervisor or outer
`RuntimeMaxSec` backstop is lost before durable completion, classify
`REPLAY_EVIDENCE_RETENTION_UNPROVEN`; never infer PASS and never blind-rerun.
No controller path copies historical source bytes, mutates predecessor roots,
starts the production service, deploys a release, or grants any live/trading
authority.

Historical semantic facts, if used, must be **authentic independently retained**
`l0-native-replay-facts/v1`, <=1 MiB, with original `manifest_hash`,
`native_sha256`, the original `dispatches`, `sync_succeeded` and
available `epochs`, `outbound_forecast`, `close_reserve`,
`native_constant_upper_bound`, `planned_reconnect_request_ns`, each
supplied fact bound to a nonempty durable locator. Missing/uncertain facts
mean **structural-only**, preserve `unavailable_facts` and
`UNAVAILABLE_FACTS_REQUIRE_CONTROL_DISPOSITION`, and return to
Engineering Control before any semantic promotion or new 2400s qualification.
Do not fabricate facts or interpret structural PASS as historical semantic
or live-ready PASS.

### Evidence packet, stop conditions, preservation and future gates

Serialize to canonical GitHub evidence **before** moving to each subsequent
gate: this merged Operations amendment and independent acceptance; exact
operator/human deployment approval; host/parent and old-root identities;
exact artifact/run/attempt, **five external anchors**, measured independent
inner tar.gz SHA256 and transfer match; inspected member set/limits/modes;
pre-execution raw hashes; new stage dev/inode/ownership; exact
runtime/pip-tool venv identities, locked distribution closure and rc5 wheel;
full `python3.12` resolution under signed `-I` and normal execution;
raw source/import origins; signed `--verify` output and default-off state.

Only then distinguish `REPLAY_ONLY_DIAGNOSTIC_DEPLOYMENT_ACCEPTED=YES`
from permanent `NORMAL_RELEASE_DEPLOYED=NO` and record the **separate current
human replay approval**. After replay, canonical durable evidence must come
from `DURABLE_PROOF`, not a vanished tmpfs path, and must include all of:

* original native/manifest pre/post path/dev/inode/metadata/full-SHA256
  bindings, plus optional authentic facts binding when used;
* exact `UID=999/GID=988`, empty supplementary groups, zero child capabilities,
  no-new-privileges and exact `EROFS` write-open denial proof;
* transient systemd requested/read-back property evidence, `WORK` tmpfs identity
  and enforced `<=768 MiB` allocation, `MemoryMax=1280 MiB`, `TasksMax=16`,
  outer `RuntimeMaxSec=2400s`, and prestart `MemAvailable>=1408 MiB`;
* replay child's exact exit/timeout/signal disposition and zero accepted swap
  activity;
* bounded stdout/stderr retained bytes plus each full-stream SHA256/byte count
  and deterministic truncation marker;
* complete surviving-WORK inventory, exact entry/file counts, modes/owners,
  per-regular-file sizes/SHA256 and total regular-file bytes;
* durable proof manifest for the bounded authoritative proof set, per-file
  fsync, proof-directory fsync and post-fsync full readback SHA256 equality;
* `DURABLE_EVIDENCE_EXPORT=PASS` as a mandatory precondition before **any**
  replay result may advance;
* final diagnostic result and complete verifier resource trail, including the
  unchanged verifier's `VmHWM/RSS <=256 MiB` decision and missing-fact
  disposition.

`UNAVAILABLE_FACTS_REQUIRE_CONTROL_DISPOSITION` remains mandatory whenever
historical semantic facts are absent or uncertain. No example, unsigned
`anchors.env`, tmpfs-only path, partial export or previous PASS fills absent
proof.

`FAIL_CLOSED/CONTROL_REPLAN` is required on any new Architecture/Operations
authority issue; main/product/artifact drift; expired artifact; signature,
transfer, archive, manifest, code or wheel mismatch; path/link/mount collision;
missing transient-systemd/cgroup/tool/host capacity; mixed runtime import; original
file/inode/hash/metadata drift; inability to enforce the total cap;
service/permit/default-off state deviation; undocumented network/write;
Replay structural/semantic resource blocker; or absent independent human gate.
At failure leave service **inactive/disabled**, permit **absent** and the
predecessor, `/etc`, `/var/lib`, log and all retained E4 history untouched.
Do **not** use `--install`, replace old roots, restart, roll back *through*
the predecessor, or automatically delete partly created new stage/scratch.
Contain and retain the new, exclusively owned paths for investigation; any
cleanup is a **different, scoped human-authorized** action requiring fresh
owner/dev/inode/mount and path confinement proof. No cleanup of old material
is ever implicit.

A later normal release replacement/deployment, 2400-second **live**
qualification, service activation/enable/restart, private-API activity,
exchange/order actions and trading each remain **distinct** human/authority
gates. Neither an accepted isolated replay nor this Operations amendment
removes their original safety and validation contracts.


## Mandatory retained-log replay before another live qualification

After separately authorized merge, release and deployment of this repair,
replay the retained approximately 379,189,199-byte failed-run native log before
any second 2400-second live qualification. Bind the original failed-run
manifest, not the repaired release's manifest. The replay reports the verifier
source SHA256 separately from historical release SHA/tree.

Resolve the exact accepted staged release, original retained inputs and accepted
`REPLAY_ROOT` under the future Engineering Control operator block. The target
replay must invoke the exact-release controller, **not** the verifier directly.
The following remains a non-executable contract template until the separate
current human replay gate and exact target paths are frozen:

~~~sh
: "${STAGE:?resolve accepted replay-only stage}"
: "${REPLAY_ROOT:?resolve accepted replay root}"
: "${RETAINED_NATIVE_LOG:?resolve original native.jsonl}"
: "${RETAINED_MANIFEST:?resolve original failed-run manifest}"

sudo "$STAGE/runtime-venv/bin/python3.12" -B \
  "$STAGE/bundle/payload/scripts/p4a/run_e4_replay_diagnostic.py" \
  --execute-authorized-replay \
  --unit-name trade-os-e4-replay-diagnostic.service \
  --replay-root "$REPLAY_ROOT" \
  --stage-root "$STAGE" \
  --staged-python "$STAGE/runtime-venv/bin/python3.12" \
  --verifier "$STAGE/bundle/payload/scripts/e4_nautilus_public_data_probe.py" \
  --native-log "$RETAINED_NATIVE_LOG" \
  --manifest "$RETAINED_MANIFEST"
# Add --replay-facts "$AUTHENTIC_REPLAY_FACTS" only when independently bound.
~~~

The controller itself creates the dedicated verifier scratch below transient
`WORK`, enforces the read-only source probe and process boundary, and retains
canonical evidence under root-only `DURABLE_PROOF`. Direct replay-verifier
commands, a custom `unshare` namespace recipe, a static service or a complete
scratch byte export are not alternate target paths.

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
