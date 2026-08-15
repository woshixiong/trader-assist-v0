# Three Setup Operations Plan V1

Status: FROZEN OPERATIONS BASELINE / CURRENT SHADOW STAGE
Date: 2026-08-15
Repository: `woshixiong/trader-assist-v0`

This document freezes the minimum operations direction for the upcoming Three Setup Shadow release. It is deliberately small. It does not authorize deployment, runtime mutation, AWS mutation, credential mutation, production DB writes, account/private API access, signing, wallet/key use, exchange writes, or order submission.

Live GitHub/code/CI and the final production bootstrap remain the authority for actual paths and release identity.

## 1. Operating principle

The project uses minimum safe operations:

- mature/provider-native capability first;
- one small supervised host while execution remains human-controlled;
- exact-SHA reproducible deployment;
- durable data off-host and independently recoverable;
- simple health/readiness and logs before observability platforms;
- measure real production behavior before increasing complexity;
- no institution-grade infrastructure unless a later authority/risk requirement objectively needs it.

The operations design must support frequent releases, replacement hosts, future Lightsail-to-EC2 migration, and incremental future expansion without replacing the backup/deployment foundation.

## 2. Frozen current-stage architecture

### Compute

Current Shadow stage uses one replaceable Lightsail host.

`CURRENT_MULTI_HOST_HA_REQUIRED=NO`

The host is not a durable asset. A failed/replaced host is rebuilt from GitHub and off-host recovery material.

### Code and deployment identity

`SOURCE_RECOVERY=GITHUB_EXACT_40_CHAR_SHA`

Do not depend on floating `main`, mutable branches, machine-local source copies, or instance snapshots as the primary rebuild authority.

### Service lifecycle

Use systemd and existing project lifecycle mechanisms. Do not add a process supervisor platform.

A bounded `Restart=on-failure` policy may be adopted only if the deployment review shows it is a small, safe change with explicit start-rate limits and no restart loop. It is not independently authorized by this document and is not allowed to delay first live Shadow merely to add automation.

### Operational backup and disaster recovery

The merged Restic V1 route remains the long-term backup/restore foundation.

`BACKUP_ARCHITECTURE=RESTIC_V1`

Default off-host provider candidate:

`PRIMARY_OFF_HOST_PROVIDER=BACKBLAZE_B2_S3_COMPATIBLE`

Cloudflare R2 remains a fallback only if a real B2 backup/restore qualification is unstable or operationally too slow. A comparative performance benchmark is not a pre-launch requirement.

Operational Restic recovery material remains encrypted. Recovery credentials must exist outside the production host and outside Git.

### Host migration

The normal migration route is:

`CLEAN_HOST -> EXACT_SHA_REBUILD -> CONFIG/CREDENTIAL_RESTORE -> RESTIC_RESTORE -> QUALIFICATION -> CUTOVER`

This route must work for Lightsail-to-EC2 and later host replacements without changing backup architecture. Provider machine-image/snapshot migration may be used as an optional convenience/fallback, not as the durable recovery design.

## 3. Frozen data lifecycle principles

Every durable object must be classified as one of:

1. `RECOVERY_DATA` — required to recover current authoritative operation; keep in operational Restic backup.
2. `RESEARCH_ARCHIVE` — no longer required for current operation but potentially useful for future research; eligible for later cold archive.
3. `REPRODUCIBLE_DATA` — can be regenerated reliably from Git/provider/public sources; do not retain indefinitely unless re-acquisition cost justifies it.

Actual future data scale and storage cost are not forecast contracts.

`DATA_SCALE_POLICY=OBSERVE_REAL_DATA_THEN_DECIDE`

No further pre-launch data-scale/cost architecture work is authorized.

## 4. Frozen cold-archive direction

`COLD_ARCHIVE_CURRENTLY_REQUIRED=NO`

When real data growth later justifies cold archive:

- operational/private/strategy-bearing recovery data stays inside encrypted Restic or an equivalent approved secure recovery store;
- public-only/reproducible historical market data may be exported manually to a Mac/local disk and uploaded to Quark Cloud or Baidu Cloud;
- public-only archives do not require an additional confidentiality-encryption layer if they contain no private, credential, strategy, human-review, execution, account, or configuration data;
- public-only archives still require a manifest and cryptographic checksum (for example SHA-256) for integrity;
- automation/API integration with Quark/Baidu is not required for low-frequency archive work;
- archive format/mechanics are selected only when this lifecycle is actually activated.

The current design must not make future archival impossible, but no cold-archive implementation belongs to the current release.

## 5. Current Three Setup pre-launch minimum

Only the following items may block first live Shadow on operations grounds.

### OPS-1 — Durable asset binding

Derive the actual production durable asset inventory from final bootstrap/service/config wiring. At minimum resolve:

- MultiAsset EvidenceStore production path;
- Market Registry production path/root;
- whether legacy `/var/lib/trader-assist-v0/runtime.db` remains a required dependency of the new production runtime;
- `public.env`;
- `risk-configuration.json`;
- any other non-reproducible durable asset actually used by the new production runtime.

Output: `THREE_SETUP_DURABLE_ASSET_MANIFEST`.

Do not invent paths. Current `EvidenceStore` is a separate database and explicitly does not open/migrate legacy `runtime.db`; final production wiring must decide the legacy DB disposition.

### OPS-2 — Deployment/service readiness

Adapt the existing First Launch deployment reference rather than building a new deployment platform. Verify:

- exact release SHA and source provenance;
- dependency installation;
- production paths and permissions;
- non-secret configuration;
- credential ingress;
- service install/start/stop/graceful shutdown;
- activation/preflight;
- safe stop procedure;
- post-start readiness verification.

Only small service-lifecycle corrections proven necessary by the audit belong here.

### OPS-3 — Minimum operator-visible health

Reuse existing runtime health/readiness and OS/provider-native signals. The operator must be able to determine, without a new monitoring platform:

- service/process state;
- runtime data readiness;
- active/ready versus failed markets;
- latest authoritative finalized 5m progress/freshness;
- whether Scanner/Strategy application progress is advancing or visibly failing;
- durable EvidenceStore path and basic size/disk-headroom information;
- meaningful bootstrap/callback/reconnect failure visibility through existing status/logs.

If this can be exposed with a thin read-only status surface, Engineering may implement it. If the audit shows it requires substantial new runtime architecture, reduce the scope to the minimum pre-launch health proof and defer richer status work.

A backup freshness field is not a pre-launch blocker because no valuable legacy data is being protected and the first real backup occurs after live evidence begins.

### OPS-4 — Target-host qualification

Run a bounded real qualification against the actual selected launch universe and production public-data route. Verify only what is needed to answer whether the current Lightsail host can sustain first live Shadow:

- CPU and memory headroom;
- disk headroom;
- public-provider connectivity;
- WebSocket/REST behavior;
- Scanner/Strategy 5m cadence completion;
- Outcome 1m demand behavior where applicable;
- SQLite/Evidence persistence health;
- absence of sustained backlog or obvious rate/resource exhaustion.

Do not test future full-universe/automatic-trading capacity.

### OPS-5 — B2/Restic recovery prerequisites

Before valuable live evidence begins, prepare but do not overbuild:

- private B2 bucket/repository endpoint;
- least-privilege storage credential;
- Restic repository/password/recovery credential arrangement;
- independent recovery credential copy outside production host;
- reviewed `full-multi-asset` paths matching OPS-1.

A real data restore qualification waits for the first real production Evidence snapshot.

## 6. First live and immediate post-live sequence

After OPS-1 through OPS-5 pass and deployment is separately authorized:

1. controlled Three Setup Shadow deployment;
2. verify live readiness and evidence progression;
3. after first meaningful real Evidence exists, create the first real `full-multi-asset` Restic snapshot to B2;
4. run normal `restic check`;
5. run one deep `check --read-data` qualification;
6. restore the exact snapshot into a clean temporary target;
7. verify recovery metadata, exact Git SHA binding, payload hashes, SQLite quick/integrity checks, Registry validation and required config assets;
8. record backup duration and full restore/verification duration;
9. only then declare `THREE_SETUP_DISASTER_RECOVERY_QUALIFIED=YES`.

Routine backup scheduling/retention is then selected from real data. A small systemd timer is preferred if/when recurring automation is justified; no backup service/platform is required.

## 7. Observation-driven decisions

The first live release establishes measurements instead of speculative architecture.

- `T+24h`: runtime stability, CPU/memory/disk headroom, Evidence DB size, failed markets, Scanner/Strategy progress.
- `T+7d`: daily data growth, Restic growth, backup duration, reconnect/provider failure pattern, initial backup cadence decision.
- `T+30d`: annualized growth estimate, storage cost reality, retention review, current Lightsail suitability and EC2 migration timing if needed.
- before each major deployment: durable asset manifest drift, disk headroom, last successful backup where real data exists, restore-qualification age.

These observations should come from existing runtime status/logs, OS commands, Restic metadata/statistics, Lightsail metrics/alarms and provider billing. Do not build an analytics platform. If a small read-only operations snapshot materially reduces recurring operator effort, Engineering may propose the minimum implementation.

## 8. Frozen future automated-execution operations baseline

Status: `FUTURE_RESEARCH_BASELINE_ONLY__NO_CURRENT_IMPLEMENTATION`

The following are starting principles, not a finalized implementation:

- `SERVER_FAILURE_MUST_NOT_CREATE_UNBOUNDED_MARKET_RISK`;
- uncertain critical data/account/risk/authority state must fail closed against increasing market risk;
- exchange-side protective capabilities should be preferred where they reduce dependence on a single application process remaining alive;
- automated execution requires explicit kill/disengage capability, reconciliation, duplicate-order prevention, stale-data guards and pre-trade risk limits;
- multi-host/Multi-AZ redundancy becomes a required cost/benefit research item before automated execution because infrastructure cost may be trivial relative to trading interruption/loss;
- do not assume two identical active execution servers are safe; future research must resolve single execution authority, leader/fencing/takeover semantics and failure reconciliation;
- institutional risk-control principles may be reused, but institution-grade infrastructure complexity is not a project goal.

Future research candidates include active/standby or other strictly single-authority designs, EC2/Multi-AZ recovery options, exchange-side dead-man/protective controls, failover and order/position reconciliation. No selection is frozen now.

## 9. Explicitly deferred from the current release

- second live trading server / HA / Multi-AZ execution;
- automated failover;
- automated-execution operations architecture implementation;
- Prometheus/Grafana/ELK/Datadog or equivalent platform;
- Kubernetes or distributed orchestration;
- Terraform/Ansible solely for this first Shadow release;
- cold archive implementation;
- Quark/Baidu automation;
- B2-vs-R2 benchmark unless B2 qualification is actually inadequate;
- long-term retention tuning before real data exists;
- full-universe capacity engineering;
- backup immutability/Object Lock/append-only hardening unless later risk justifies it.

## 10. Change rule

Future versions should normally update only:

- the durable asset manifest;
- measured capacity limits;
- backup cadence/retention;
- health/incident gates required by new authority.

Do not replace GitHub exact-SHA rebuild + Restic off-host recovery + simple systemd operations without a demonstrated requirement that the existing foundation cannot satisfy.
