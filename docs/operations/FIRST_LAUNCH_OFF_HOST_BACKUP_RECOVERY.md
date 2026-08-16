# First Launch off-host backup and recovery — Restic V1

## Scope and ownership

This is a bounded disaster-recovery preparation tool. It stages only the fixed durable asset
allowlist below, then asks [Restic](https://restic.readthedocs.io/en/stable/) to create, encrypt,
store, lock, check, and restore a repository snapshot. It does not provision a repository,
select a cloud provider, connect to AWS, start or stop a service, overwrite production, or run
retention maintenance.

Trader Assist owns the consistent SQLite copies, fixed allowlist, metadata binding and local
post-restore validation. Restic owns encrypted repository storage, content addressing and
deduplication, locking/concurrency, backend transport, snapshot identity, and repository
integrity. There is no age, rclone, tar, custom remote publication, custom archive parser,
`forget`, or `prune` implementation in this route.

Restic supports local, SFTP, REST, S3-compatible, B2, Azure, GCS and other documented backend
locations. Supply the repository location externally and prefer a native Restic backend unless a
later provider requirement says otherwise. Ordinary encrypted off-host storage is enough for V1.
Ransomware/delete resistance is a later hardening gate: do not assume a credential that merely
denies delete is a correct append-only Restic repository, because Restic locking and maintenance
have their own semantics. A future review may evaluate rest-server append-only mode, provider
Object Lock/immutability, and separately controlled maintenance credentials.

## Fixed recovery profiles

`first-launch` contains exactly:

- `first-launch-runtime`: `/var/lib/trader-assist-v0/runtime.db` as a SQLite snapshot.
- `first-launch-public-env`: `/etc/trader-assist-v0/public.env`.
- `first-launch-risk-config`: `/etc/trader-assist-v0/risk-configuration.json`.

These three sources are fixed at both the operator CLI and public library boundary; no First
Launch source-path override exists.

`full-multi-asset` contains those three plus explicitly supplied paths for:

- `multi-asset-evidence`: a SQLite snapshot.
- `multi-asset-registry`: the Registry root, copied as an ordinary regular-file/directory tree.

No generic asset argument exists. The tool rejects a missing required item, a symlink, and any
FIFO, socket, device, or other special Registry entry. It never follows links. It cannot include
notification credentials, webhook secrets, Restic passwords, backend credentials, account/API
credentials, wallets, signing material, or private keys because none is in the allowlist.

Current main has not bound production paths for MultiAsset EvidenceStore or MarketRegistryManager.
For that reason, operator-supplied paths are required for `full-multi-asset`, and:

`FULL_MULTI_ASSET_DISASTER_RECOVERY_QUALIFIED=NO`

until a separately authorized deployment phase binds and verifies their production locations. A
First Launch-only snapshot must not be described as complete current MultiAsset recovery.

`three-setup-shadow` is the fixed recovery profile for the Three Setup Shadow Release. It contains
exactly the production EvidenceStore at
`/var/lib/trader-assist-v0/three-setup-shadow/evidence.sqlite`, the Registry root at
`/var/lib/trader-assist-v0/three-setup-shadow/registry`, and the non-secret canonical production
configuration at `/etc/trader-assist-v0/three-setup-shadow.json`. It excludes legacy
`/var/lib/trader-assist-v0/runtime.db`, all credentials/secrets, the activation permit, source,
and the closed-bar store. The closed-bar store is excluded only because the deterministic local
recovery acceptance establishes it as
`PROVISIONALLY_REPRODUCIBLE_OPERATIONAL_STATE__QUALIFICATION_REQUIRED`. The profile has no
source-path override.

## Snapshot contract

Each SQLite source is opened read-only and copied with `sqlite3.Connection.backup`, which includes
committed WAL content without checkpointing, migrating, or otherwise modifying the source. Each
copy must pass `PRAGMA quick_check` and `PRAGMA integrity_check`. Databases are captured in order,
not as one global transaction:

`PER_DATABASE_CONSISTENCY=YES`

`CROSS_DATABASE_ATOMIC_SNAPSHOT=NO`

The temporary plaintext staging root contains only:

```text
recovery/
  recovery-metadata.json
  first-launch-runtime/database.sqlite
  first-launch-public-env/file
  first-launch-risk-config/file
  multi-asset-evidence/database.sqlite          # full profile only
  multi-asset-registry/tree/...                 # full profile only
  three-setup-evidence/database.sqlite          # Three Setup profile only
  three-setup-registry/tree/...                  # Three Setup profile only
  three-setup-config/file                        # Three Setup profile only
```

`recovery-metadata.json` is canonical JSON. It records the schema, repository identity
`woshixiong/trader-assist-v0`, exact lowercase 40-character deployed Git SHA, UTC capture time,
profile, exact logical inventory, payload SHA-256 values, SQLite validation results and capture
order/time, and the two consistency declarations. It contains no source production paths and no
secrets. Plain staging is removed after both success and failure.

## Restic credentials and key recovery

Restic encrypts repositories and permits multiple repository access keys/passwords. Loss of all
repository passwords/keys makes recovery impossible. Keep repository access credentials
independently from the production host, never in the production SQLite/config backup, Git, or
metadata. When operationally appropriate, maintain at least two separately controlled repository
access keys/passwords using Restic key management. A clean-host qualification must prove that an
independently stored recovery credential opens the repository.

The wrapper accepts one standard Restic ingress mechanism: `--restic-password-file` or
`--restic-password-command`. It passes that ingress to Restic as argv; it never puts a password in
metadata or prints a password, backend credential, or command output.

## Operator commands

Run these only under a separately authorized operational procedure. They are examples, not
authorization to create a real backup, restore production, or access a repository. Substitute
the externally managed repository location, externally stored password source, and reviewed SHA.

```text
scripts/first_launch_backup_recovery.py backup \
  --repository "$RESTIC_REPOSITORY" \
  --restic-password-file /secure/external/restic-password-file \
  --deployed-git-sha <exact-40-lowercase-sha> \
  --profile first-launch
```

The `backup` command invokes Restic with an argv equivalent to `restic --repo ... --json backup`,
with tags `trader-assist`, `recovery-profile=<profile>`, and `git-sha=<sha>`. It accepts success
only when Restic exits zero and its JSON-lines summary supplies a concrete full snapshot ID. Tags
are discovery conveniences; restored metadata is the authority.

For a full MultiAsset candidate, add both explicit paths:

```text
  --profile full-multi-asset \
  --multi-asset-evidence /reviewed/evidence.sqlite \
  --multi-asset-registry /reviewed/registry-root
```

For the fixed Three Setup release profile, use no asset-path flags:

```text
  --profile three-setup-shadow
```

Normal repository integrity check:

```text
scripts/first_launch_backup_recovery.py check \
  --repository "$RESTIC_REPOSITORY" \
  --restic-password-file /secure/external/restic-password-file
```

Deep qualification check (separate and deliberately heavier):

```text
scripts/first_launch_backup_recovery.py check --read-data \
  --repository "$RESTIC_REPOSITORY" \
  --restic-password-file /secure/external/restic-password-file
```

`check --read-data` may read the whole repository; do not make it part of each normal backup.
Neither command schedules `forget` or `prune`.

## Restore verification

Verification restores an exact 64-character snapshot ID via Restic into a fresh temporary target.
It does not parse a custom archive, overwrite production, qualify a deployment, start a runtime,
or claim READY. It locates exactly one restored metadata file, verifies schema/repository/SHA/
profile/exact inventory, recomputes payload hashes, opens every SQLite copy read-only for both
checks, validates Registry/file trees, rejects undeclared top-level recovery assets, and then
removes the restore workspace.

```text
scripts/first_launch_backup_recovery.py verify \
  --repository "$RESTIC_REPOSITORY" \
  --restic-password-file /secure/external/recovery-password-file \
  --snapshot-id <exact-64-lowercase-snapshot-id> \
  --expected-git-sha <exact-40-lowercase-sha> \
  --profile first-launch
```

The only PASS string is:

`RESTIC_SNAPSHOT_RECOVERY_ARTIFACT_VERIFIED`

Before any later authorization to delete a Lightsail snapshot, qualification must include a real
off-host snapshot, independently stored recovery credential access, normal check, at least one
`check --read-data`, clean temporary/qualification restore, metadata/SQLite/Registry/config
validation, exact Git SHA rebuild plan, and supervised qualification. Until then:

`LIGHTSAIL_SNAPSHOT_DELETE=PROHIBITED`
