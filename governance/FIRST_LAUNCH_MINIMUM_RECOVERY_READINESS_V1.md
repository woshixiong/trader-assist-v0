# First Launch Minimum Recovery Readiness V1

## 1. Decision

A complete automated host-qualification or disaster-recovery framework is not required before
First Launch.

However, it is unsafe to wait until a disaster to create every recovery prerequisite.

Binding state:

`MINIMUM_RECOVERY_READINESS_REQUIRED_BEFORE_ACCEPTED_REAL_OPERATION`

This is a small operational preparation task. It is not a product feature, permanent verifier,
multi-host framework or replacement for PR #48.

## 2. Why some preparation must exist before a disaster

Repository code and service files can be recreated later from an exact approved Git commit.

The following cannot be recreated after loss unless an independent source already exists:

- cloud-account access and recovery credentials;
- the external source for the notification credential;
- accumulated SQLite runtime state and history;
- knowledge of the exact deployed release and host-specific paths;
- any provider snapshot that was never created.

Therefore, the project may defer automation but may not defer all recovery anchors.

## 3. Required before accepted real operation

### 3.1 Administrative recovery access

Confirm that the cloud account can be recovered without relying on the running host.

At minimum:

- account login is available;
- MFA recovery material is available through an approved secure method;
- the operator can recreate a host or restore a snapshot;
- SSH access can be re-established for a replacement host.

Do not store private keys, recovery codes or secrets in GitHub.

### 3.2 External credential source

The production notification credential must have an approved recoverable source outside the
host.

The production host copy is not the backup.

Record only the recovery method and responsible location class, never the secret value.

### 3.3 Exact release and path card

Record a concise non-secret recovery card containing:

- exact deployed 40-character Git SHA;
- repository;
- service unit name;
- fixed Python executable path;
- repository path;
- configuration directory;
- SQLite database path;
- risk-configuration path;
- credential destination path;
- default recovery route.

The default route is:

`CLEAN_HOST + EXACT_SHA_REBUILD + SECURE_CREDENTIAL_RESTORE + SQLITE_RESTORE + SUPERVISED_QUALIFICATION`

### 3.4 SQLite backup and restore method

Use a SQLite-consistent method.

Preferred low-cost choices:

1. stop the service and copy the database while it is closed; or
2. use the Python standard-library SQLite backup API while the source database is available.

Do not treat an uncontrolled copy of a live database as a verified backup.

After supervised qualification and before accepted real operation:

- create one backup;
- open the backup read-only;
- run `PRAGMA integrity_check`;
- record only PASS/FAIL, backup time and non-secret location;
- keep the backup outside the single production-host failure boundary.

The backup is primarily for runtime history and operational continuity. Because First Launch
has no account or exchange-write authority, loss of the database does not create an unmanaged
exchange position, but it can destroy evidence and history.

### 3.5 Provider snapshot decision

A provider instance or volume snapshot is optional but useful for faster recovery.

Choose one of:

- `SNAPSHOT_SELECTED`: create one after successful qualification and before accepted real
  operation; or
- `REBUILD_ONLY_ACCEPTED`: rely on exact-SHA recreation plus credential and database restore.

A snapshot is not the only backup and does not replace GitHub, credential recovery or database
backup.

## 4. What may wait until the event

The following do not need to be built before First Launch:

- permanent host-qualification automation;
- permanent disaster-recovery scripts;
- event-specific migration commands;
- a second-host full restore drill;
- scheduled snapshot automation;
- multi-host orchestration;
- retained journal-evidence pipelines;
- generalized Python trust or host-audit frameworks.

At a real migration, major redeployment or disaster-recovery event, generate a temporary,
host-specific command bundle from the then-current exact release and actual target host.

## 5. Minimum verification level

Before accepted real operation, the recovery-readiness gate is PASS only when:

1. cloud-account recovery access is confirmed;
2. the external credential source is confirmed;
3. the exact release and path card is complete;
4. the SQLite backup method is approved;
5. one post-qualification backup passes read-only open and integrity check;
6. snapshot or rebuild-only policy is explicitly selected.

A full second-host recovery exercise is not required for this First Launch gate.

## 6. Maintenance after launch

Use the minimum adequate policy:

- create a fresh SQLite backup before major upgrades, migrations or risky maintenance;
- create additional backups at a low frequency justified by the value of accumulated history;
- update the exact release card after each accepted deployment;
- reconsider snapshots when the host changes materially;
- activate the lowest-priority automation backlog only when repeated use proves net value.

## 7. Authority

This document records preparation requirements only.

It does not authorize:

- cloud-account access;
- host access or SSH;
- snapshot creation;
- database access or copying;
- credential access;
- deployment;
- service mutation;
- runtime or smoke;
- account access;
- exchange write;
- Mark Ready;
- merge.

Each operational action requires separate current authorization.
