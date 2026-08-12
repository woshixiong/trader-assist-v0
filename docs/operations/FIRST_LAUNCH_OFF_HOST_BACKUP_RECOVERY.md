# First Launch Off-Host Backup and Recovery

This is a bounded local backup helper for the First Launch runtime. It does not
start or stop the service, create cloud storage, access credentials, deploy,
delete Lightsail snapshots, or restore anything into production.

The recovery model remains:

```text
CLEAN_HOST + EXACT_SHA_REBUILD + SECURE_CREDENTIAL_RESTORE + SQLITE_RESTORE
+ SUPERVISED_QUALIFICATION
```

Use it only after separate authorization for the relevant host, configuration,
existing encryption identity, and off-host storage destination.

## Required existing tools and inputs

- Python 3.12+ with this exact approved checkout;
- maintained [`age`](https://age-encryption.org/) installed by the operator;
- maintained [`rclone`](https://rclone.org/) already configured with an
  independently authorized private destination; and
- an `age` recipient public key plus an identity file kept outside the production
  host and outside the destination containing the backup objects.

The helper never accepts an object-storage secret on its command line. Configure
`rclone` beforehand through the approved operator process. Do not put a private
key, token, webhook URL, or storage secret in a manifest, Git repository, shell
history, or support chat.

## Asset selection

The current legacy asset set is:

- `/var/lib/trader-assist-v0/runtime.db`
- `/etc/trader-assist-v0/public.env`
- `/etc/trader-assist-v0/risk-configuration.json`

The encrypted package can later include the separate multi-asset database or
registry/configuration without a redesign: add each with
`--additional-database NAME=PATH` or `--additional-config NAME=PATH`. `NAME`
must be lowercase letters, digits, `_`, or `-`. Do not package the runtime
credential source; restore it from its separately approved secure source.

## Create an encrypted local artifact

Run this only against the actual, separately authorized paths and exact deployed
SHA. The source SQLite database remains available while Python's standard-library
online backup API creates a consistent copy. The helper runs `quick_check` and
`integrity_check` on that copy before packaging it, writes `manifest.json` and
`SHA256SUMS`, creates a temporary plaintext package, encrypts it with `age`, then
removes the temporary plaintext workspace.

```bash
APPROVED_SHA="<exact 40-character deployed SHA>"
AGE_RECIPIENT="<approved age recipient public key>"
BACKUP_OBJECT="/secure-local-staging/trader-assist-backup-$(date -u +%Y%m%dT%H%M%SZ).tar.gz.age"

PYTHONPATH=src /opt/trader-assist-v0/venv/bin/python scripts/first_launch_backup_recovery.py create \
  --database /var/lib/trader-assist-v0/runtime.db \
  --public-env /etc/trader-assist-v0/public.env \
  --risk-configuration /etc/trader-assist-v0/risk-configuration.json \
  --output "$BACKUP_OBJECT" \
  --repository woshixiong/trader-assist-v0 \
  --deployed-sha "$APPROVED_SHA" \
  --service-name trader-assist-v0-public.service \
  --python-executable /opt/trader-assist-v0/venv/bin/python \
  --storage-destination-class independent-object-storage \
  --age-recipient "$AGE_RECIPIENT"
```

Record the printed encrypted SHA-256 and manifest SHA-256 in an approved
non-secret operations record. The encrypted artifact is intentionally not
overwritten; choose a new UTC-named path for every run.

## Transfer and independently verify

`rclone` is only an adapter. It does not create a bucket, remote, or account.
The object destination must already be private, minimally privileged, and outside
the production-host failure boundary.

```bash
REMOTE_OBJECT="approved-remote:private-trader-assist-backups/<new-artifact>.tar.gz.age"
ENCRYPTED_SHA256="<value printed by create>"
AGE_IDENTITY_FILE="/approved-external-key-location/trader-assist-backup-age-key.txt"

PYTHONPATH=src /opt/trader-assist-v0/venv/bin/python scripts/first_launch_backup_recovery.py upload \
  --artifact "$BACKUP_OBJECT" \
  --remote-destination "$REMOTE_OBJECT"

PYTHONPATH=src /opt/trader-assist-v0/venv/bin/python scripts/first_launch_backup_recovery.py verify-remote \
  --remote-source "$REMOTE_OBJECT" \
  --expected-encrypted-sha256 "$ENCRYPTED_SHA256" \
  --age-identity-file "$AGE_IDENTITY_FILE" \
  --workspace-parent /secure-local-restore-verification
```

The verification command downloads to a new temporary file, checks the encrypted
SHA-256, decrypts to a temporary workspace, checks every payload hash, opens each
declared SQLite database read-only, and runs both SQLite integrity checks. It
removes its temporary downloaded/decrypted workspace on both pass and failure.
`restore_verification=PASS` is a local/off-host artifact verification only; it
does not restore to a host and does not qualify a production service.

## Restore event checklist

At a separately authorized recovery event, use a new host-specific command bundle:

1. Rebuild a clean host from the exact approved 40-character Git SHA.
2. Install only the approved, hashed runtime dependencies.
3. Download and verify a new encrypted copy with the command above.
4. Restore the SQLite file only while the intended target service is stopped under
   explicit runtime authority; do not overwrite a live database.
5. Restore notification credentials from their independent secure source, not from
   this package.
6. Apply only reviewed configuration and complete supervised qualification.

## Lightsail snapshot gate

The existing Lightsail snapshot remains protected. Do not delete it. A separate
human authorization is required even after all of the following are confirmed:

- consistent SQLite backup and local integrity checks;
- encrypted artifact and off-host upload;
- fresh download, checksum, decryption, read-only open, and integrity checks;
- independent notification-credential recovery source; and
- a verified secondary local/external copy and recovery runbook.

Until then: `LIGHTSAIL_SNAPSHOT_DELETE=PROHIBITED`.
