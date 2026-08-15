# Three Setup Operations Plan V1

Status: FROZEN OPERATIONS BASELINE / CURRENT SHADOW STAGE  
Date: 2026-08-15  
Repository: `woshixiong/trader-assist-v0`

This document freezes the minimum reusable Operations/SRE direction for the upcoming Three Setup Shadow release. It does not authorize deployment, runtime/AWS mutation, credential mutation, production DB writes, account/private API access, signing, wallet/key use, exchange writes, order submission, Mark Ready, or merge.

Live GitHub/code/CI and the final production bootstrap remain authority for exact release identity and actual production paths.

## 1. Long-term operating architecture

The project uses **minimum safe operations**:

- mature/provider-native capability first;
- exact-SHA reproducible deployment;
- one replaceable supervised host while execution remains human-controlled;
- authoritative durable data separated from reproducible source/cache data;
- encrypted off-host recovery with independently recoverable credentials;
- systemd + journal + Linux/provider-native health before observability platforms;
- real 24h/7d/30d evidence before capacity, retention, archive, or host-migration expansion;
- no platform build without an evidence-backed requirement.

The reusable foundation is:

`GITHUB EXACT SHA + SYSTEMD + SQLITE DURABLE STORES + RESTIC + OFF-HOST OBJECT STORAGE + RESTORE QUALIFICATION`

Future V0 / Trade OS versions should normally update only the durable-asset manifest, profile inventory, capacity limits, backup cadence/retention, and gates required by new authority. They must not replace this foundation unless a demonstrated requirement cannot be satisfied by it.

`ARCHITECTURE_REPLAN_REQUIRED=NO`

## 2. Current compute and source recovery

Current Shadow stage uses one replaceable Lightsail host.

`CURRENT_MULTI_HOST_HA_REQUIRED=NO`

The host is not a durable asset. Normal host replacement/migration is:

`CLEAN_HOST -> EXACT_SHA_REBUILD -> CONFIG/CREDENTIAL_RESTORE -> RESTIC_RESTORE -> QUALIFICATION -> CUTOVER`

This route is intentionally compatible with future Lightsail-to-EC2 migration.

`SOURCE_RECOVERY=GITHUB_EXACT_40_CHAR_SHA`

Do not use floating `main`, mutable branches, machine-local source copies, or instance snapshots as primary rebuild authority.

## 3. Service lifecycle foundation

Use systemd and the existing First Launch safety boundary where still applicable:

- dedicated `traderassist` user/group;
- root-owned source/config;
- activation permit / default-off behavior;
- `EnvironmentFile` for reviewed non-secret configuration;
- `LoadCredential` for notification secrets;
- forced approved source provenance / PYTHONPATH;
- filesystem containment;
- `StateDirectory` / `RuntimeDirectory`;
- systemd hardening;
- journal output;
- SIGTERM and bounded graceful stop.

Do not build a new process supervisor or deployment platform.

Current default for First Live remains `Restart=no`. A bounded `Restart=on-failure` may be adopted later, or in the current release only if the production-binding implementation makes controlled-shutdown versus unexpected-failure exit semantics explicit and the additional tests remain genuinely small. It is not an independent launch blocker.

## 4. Current Three Setup engineering boundary

The accepted MultiAsset library/composition already contains Runtime, Registry, provider-finalized 5m authority, Scanner, Strategy, Planning, EvidenceStore, Formal/ShadowOrder, Outcome, Bootstrap/reconciliation, reconnect recovery, public providers, and notification machinery.

Do not redesign those components.

Current pre-launch engineering is bounded to:

### B01 — Thin Three Setup production binding

Create the minimum production composition that:

- binds actual production paths;
- instantiates Registry + ClosedBarStore/DataAuthority + public client + existing `MultiAssetProductionBootstrap`;
- binds exact release SHA and reviewed non-secret config;
- composes the existing notification outbox/dispatcher/secure credential path with no new notification engine;
- installs graceful shutdown;
- emits minimal structured journal visibility for startup, Registry identity, readiness, ready/failed markets, latest finalized 5m, boundary/Scanner/Strategy progress/failure, reconnect state, and shutdown;
- preserves public-data-only / no-account / no-signing / no-exchange-write boundaries and `ShadowOrder=NOT_SUBMITTED`.

Reuse/adapt the existing First Launch service/wrapper safety controls where this is smaller and safer than reimplementing them.

### B02 — Exact Three Setup recovery profile

Restic V1 architecture remains accepted. Add an additive Three Setup-specific recovery profile after B01 freezes the real durable asset manifest. Do not continue using the legacy `full-multi-asset` inventory as the long-term Three Setup authority merely because it is a superset.

`LEGACY_RUNTIME_DB_REQUIRED_FOR_THREE_SETUP=NO`

The Three Setup profile must include only actual non-reproducible recovery assets and reviewed required non-secret configuration, and must exclude legacy-unused assets, secrets, activation permit, Git-reproducible source, and reproducible data.

No Restic redesign, custom storage adapter, backup service, tar/rclone/age route, retention platform, Object Lock, or second provider belongs to the current release.

## 5. Durable asset classification

Every production object must be classified as one of:

1. `RECOVERY_DATA` — required to recover authoritative operation; included in the current recovery profile.
2. `RESEARCH_ARCHIVE` — no longer required for current operation but potentially valuable research history; eligible for later archive.
3. `REPRODUCIBLE_DATA` — reliably regenerated from Git/provider/public sources; normally excluded from operational recovery.

B01 must freeze `THREE_SETUP_DURABLE_ASSET_MANIFEST` including at least:

- `EVIDENCE_STORE_PATH` — independent SQLite; must not reuse legacy `runtime.db`;
- `REGISTRY_ROOT` — persistent Registry tree (`versions`, `validations`, `current`, `pending`, `history` as applicable);
- `CLOSED_BAR_STORE_PATH` — independent SQLite;
- `CLOSED_BAR_STORE_BACKUP_CLASSIFICATION`;
- actual required Three Setup non-secret config assets;
- secret assets explicitly excluded;
- `LEGACY_RUNTIME_DB_REQUIRED=NO`.

Do not invent final production filenames before B01 binds them.

Secrets such as notification credential, B2 storage credential, and Restic repository password/key must remain outside Git and outside the Restic application payload and must have an independently recoverable copy outside the production host.

Activation permit is not Recovery Data. A clean host must remain default-off until an operator explicitly reactivates it.

## 6. ClosedBarStore recovery qualification

ClosedBarStore is not yet proven reproducible merely because market OHLCV is public.

Current classification:

`CLOSED_BAR_STORE_CLASSIFICATION=PROVISIONALLY_REPRODUCIBLE_OPERATIONAL_STATE__QUALIFICATION_REQUIRED`

The store retains canonical hash, Registry identity, finality identity, finalized time, and normalized provider evidence that can participate in retained Strategy/Evidence authority.

Pre-launch acceptance must include a deterministic recovery scenario:

`RESTORED_REGISTRY + RESTORED_NONEMPTY_EVIDENCE_STORE + EMPTY_NEW_CLOSED_BAR_STORE + PUBLIC_HISTORY_REWARMUP + BOOTSTRAP_RECONCILIATION`

It must prove:

- required history rewarms;
- Registry/readiness become valid;
- retained Scanner/Strategy/Formal/Outcome authority does not conflict;
- no duplicate authoritative records are produced;
- canonical/provenance mismatch does not break reconciliation;
- the next live boundary can continue normally;
- operational readiness can be reached.

If PASS, classify ClosedBarStore as reproducible and exclude it from recovery payload. If FAIL, classify it as Recovery Data and include it in the Three Setup profile. Do not redesign ClosedBar identity solely to force a PASS.

A real empty-store cold-start proof must be repeated during target-host qualification.

## 7. Backup and disaster recovery

`BACKUP_ARCHITECTURE=RESTIC_V1`

Primary off-host provider:

`PRIMARY_OFF_HOST_PROVIDER=BACKBLAZE_B2_S3_COMPATIBLE`

`CLOUDFLARE_R2=FALLBACK_ONLY`

Do not benchmark providers pre-emptively. Re-open R2 only if real B2 backup/restore is unstable or restore time is operationally unacceptable.

Before First Live/valuable Evidence, prepare:

- private B2 bucket/repository endpoint;
- scoped least-privilege storage credential;
- Restic repository/password/key arrangement;
- independent recovery credential copy outside production host;
- reviewed Three Setup recovery profile matching the frozen durable-asset manifest.

After the first meaningful real Evidence appears, immediately perform the first real DR qualification:

`THREE_SETUP BACKUP -> RESTIC CHECK -> ONE CHECK --READ-DATA -> EXACT SNAPSHOT TEMP RESTORE -> VERIFY`

Verification must cover recovery metadata, exact Git SHA, payload hashes, SQLite quick/integrity checks, Registry validation, and required config assets. Record backup duration/logical size and restore/verification duration.

Only then:

`THREE_SETUP_DISASTER_RECOVERY_QUALIFIED=YES`

`check --read-data` is for first/low-frequency deep qualification, not every routine backup.

Routine automation is not a pre-launch blocker. After real operating evidence, prefer an existing Restic command first and a small systemd timer only when recurring automation is clearly worthwhile. Do not build a Backup Service.

## 8. Accepted residual: cross-asset snapshot atomicity

Restic V1 gives per-database consistent SQLite snapshots but not one cross-database/global transaction across EvidenceStore, optional ClosedBarStore, Registry, and config assets.

`PER_DATABASE_CONSISTENCY=YES`

`CROSS_DATABASE_ATOMIC_SNAPSHOT=NO`

For the current Shadow/research stage this is an accepted residual only because application authority is immutable/idempotent/reconcilable and every real DR qualification must prove the restored combination can reconcile safely.

Escalation triggers:

- any real restore qualification fails because assets represent incompatible moments;
- future application authority introduces state that cannot reconcile safely across independently captured assets;
- before fully autonomous execution if cross-asset inconsistency could create market/account risk.

If triggered, evaluate coordinated/quiesced application-consistent capture before replacing Restic or the off-host architecture. This is an extension point, not a current architecture rewrite.

## 9. Minimum operator health

Do not build Prometheus/Grafana/ELK/Datadog or a monitoring service.

Use existing Runtime/Bootstrap health information exposed through structured journal plus:

- `systemctl`;
- `journalctl`;
- `scripts/multi_asset_registry.py status`;
- Linux native CPU/memory/disk/file commands;
- Lightsail native metrics/alarms;
- Restic metadata/check output.

The current ETH-only `ta-status` is not MultiAsset authority. Do not rewrite it pre-launch unless real operator use proves journal + existing commands insufficient.

## 10. Target-host qualification

`CURRENT_LIGHTSAIL_HOST_SUFFICIENT=UNDETERMINED_PENDING_REAL_QUALIFICATION`

This is an Operations gate, not a capacity-platform development task. Qualify only the actual First Live selected universe and public-data route for:

- CPU/RAM/disk/network headroom;
- provider connectivity, WS/REST, reconnect behavior;
- finalized 5m progression;
- Scanner/Strategy cycle completion before the next 5m boundary;
- relevant Outcome 1m demand;
- EvidenceStore/SQLite health;
- no sustained backlog or obvious rate/resource exhaustion;
- real empty-ClosedBar cold-start recovery proof.

Do not test future full-universe or automated-trading capacity now.

## 11. Triggered observations and decisions

The canonical Operations trigger ledger is GitHub Issue #93. Deferred tasks must be triggered by evidence/state, not human memory.

Required gates:

- **Before every major deployment:** exact SHA/CI, durable-asset manifest drift, config/credential readiness, disk headroom, last successful real-data backup if one exists, restore-qualification age.
- **First Live:** record exact timestamp, SHA, Registry identity, selected universe, host identity.
- **First meaningful Evidence:** immediately run first real B2/Restic backup + full DR qualification.
- **T+24h:** runtime stability, CPU/RAM/disk, Evidence size, ready/failed markets, Scanner/Strategy progression.
- **T+7d:** Evidence growth, Restic growth, backup duration, reconnect/provider failures, initial backup cadence/timer decision.
- **T+30d:** storage growth/cost, retention, Lightsail suitability, EC2 migration timing, archive trigger review.
- **Before automatic execution is planned:** reopen HA/Multi-AZ/execution authority/fencing/reconciliation/kill-control and cross-asset snapshot consistency research.

## 12. Legacy/decommission deletion gates

Legacy assets must not remain forever merely because earlier backup profiles referenced them. Issue #93 tracks explicit deletion eligibility reviews.

### Legacy `runtime.db`

Review for deletion when all are true:

1. B01 proves Three Setup has no runtime dependency on it;
2. the Three Setup recovery profile no longer references it;
3. no unique data has been intentionally designated for preservation;
4. rollback/decommission policy does not require the legacy runtime.

Then notify the user that it is eligible for a separately authorized deletion. Never delete automatically.

### Legacy First Launch config files

Review individually after B01 freezes the actual Three Setup config manifest. A file is deletion-eligible only if the new service does not consume it, the recovery profile does not require it, and any needed replacement/non-secret configuration is already preserved. Secrets follow their own revoke/rotation procedure.

### Legacy Lightsail snapshot / host resources

The user has expressed intent to delete the old snapshot because the old runtime has no valuable operating data. Before any AWS deletion, perform a lightweight decommission check for unique config/credential/log assets and ongoing rollback need, then request separate AWS mutation authorization. Do not block old-snapshot cleanup on backing up an empty legacy DB.

### Future obsolete resources

At T+30d and before host migration, review unused snapshots, old hosts, old Restic profiles/keys, stale config, and other recurring-cost resources. Remove only after dependency/recovery evidence says they are no longer required and after the required mutation authority is granted.

## 13. Research / engineering TODO ownership map

To prevent duplicate reminders:

- **Issue #93** — canonical Operations/SRE trigger ledger: deployment, health, B2/DR, observations, deletion/decommission, host migration, future operations-risk triggers.
- **Issue #80** — current Engineering/post-live research-evidence sequencing. Historical P0 text may be stale; current pre-launch production/DR authority is Issue #93 plus this document.
- **Issue #85** — canonical post-live Shadow/Forward strategy research matrix; trigger only when enough real evidence exists.
- Other focused research/backlog issues remain source-specific and must not be promoted into the current release unless Product/Strategy/Operations explicitly triggers them.

A reminder/monitor must surface a task only when its stated trigger becomes true or a time gate is due; it should not repeatedly notify about dormant future backlog.

## 14. Explicitly deferred from current release

Do not promote these without a new evidence-backed requirement:

- multi-host HA / Multi-AZ execution;
- automated failover;
- automated-execution operations implementation;
- Prometheus/Grafana/ELK/Datadog;
- Kubernetes/distributed orchestration;
- Terraform/Ansible platform solely for this Shadow release;
- cold archive implementation;
- Quark/Baidu automation;
- B2-vs-R2 benchmark when B2 works acceptably;
- full-universe capacity engineering;
- speculative retention tuning;
- custom backup/monitoring service;
- Object Lock/append-only hardening;
- second backup provider.

## 15. Change rule

This plan is intentionally reusable. Future versions may evolve paths, durable assets, config, data scale, cadence, or execution authority. Those changes should update the manifest/profile/gates rather than replace the underlying exact-SHA + systemd + SQLite + Restic + off-host restore architecture.

Any proposal to replace that foundation must demonstrate a concrete requirement that cannot be safely met by an incremental extension.
