# V0 FL R3 P4A Local Deployment Runbook

## 1. Prerequisites

- A systemd-based Linux distribution (Ubuntu 22.04+ or equivalent).
- Python 3.12+ installed.
- Git installed.
- `systemd-analyze` available for unit validation (optional but recommended).

## 2. Dedicated User

Create the dedicated non-root `traderassist` user and group:

```bash
sudo groupadd --system traderassist
sudo useradd --system --gid traderassist --no-create-home --shell /usr/sbin/nologin traderassist
```

## 3. Repository Installation

Deployment authority requires a Project-Control-authorized full 40-character
SHA.  Deployment from floating `main`, mutable branches, abbreviated SHAs,
or any non-exact ref is prohibited.

Set the authorized SHA and install the repository at the exact commit:

```bash
AUTHORIZED_SHA="<full 40-character SHA authorized by Project Control>"

sudo mkdir -p /opt/trader-assist-v0
sudo git clone https://github.com/woshixiong/trader-assist-v0.git /opt/trader-assist-v0
cd /opt/trader-assist-v0

# Exact SHA fetch and detached checkout (no mutable branch, no abbrev)
sudo git fetch origin "$AUTHORIZED_SHA"
sudo git checkout "$AUTHORIZED_SHA"

# Verify exact HEAD equality with the authorized SHA
test "$(git rev-parse HEAD)" = "$AUTHORIZED_SHA"

# Verify clean tree
test -z "$(git status --porcelain)"

sudo chown -R root:root /opt/trader-assist-v0
```

## 4. Virtual Environment

Create the Python virtual environment under `/opt/trader-assist-v0/venv` and
install only the hashed runtime lockfile.  Do not install the development
lockfile, unhashed build dependencies, or an editable (`-e`) install of the
project.  The project is imported exclusively via the forced `PYTHONPATH`
(see Section 8 and the wrapper), never via site-packages.

```bash
cd /opt/trader-assist-v0
sudo python3.12 -m venv venv
sudo venv/bin/pip install --require-hashes -r requirements-runtime.lock
```

Verify `trader_assist_v0` imports exclusively from
`/opt/trader-assist-v0/src/trader_assist_v0` and that the import fails if it
would resolve from site-packages or another checkout:

```bash
# Positive: with forced PYTHONPATH, import must resolve from /opt/src
sudo PYTHONPATH=/opt/trader-assist-v0/src /opt/trader-assist-v0/venv/bin/python -c "
import os, trader_assist_v0
expected = os.path.realpath('/opt/trader-assist-v0/src/trader_assist_v0')
actual = [os.path.realpath(p) for p in (trader_assist_v0.__path__ or [])]
assert actual == [expected], f'import resolved from {actual}, expected [{expected}]'
print('OK: import source verified')
"

# Negative: without PYTHONPATH, import must fail (not installed in site-packages)
sudo /opt/trader-assist-v0/venv/bin/python -c "import trader_assist_v0" \
  && { echo 'FAIL: import succeeded without PYTHONPATH'; exit 1; } \
  || echo 'OK: import correctly fails without PYTHONPATH'
```

## 5. Configuration Directory

```bash
sudo mkdir -p /etc/trader-assist-v0
sudo chown root:root /etc/trader-assist-v0
sudo chmod 755 /etc/trader-assist-v0
```

## 5a. Credential Directory

The notification credential is stored in a separate restricted directory with
owner-only access. The directory mode is 0700 (root:root only).

```bash
sudo mkdir -p /etc/trader-assist-v0/credentials
sudo chown root:root /etc/trader-assist-v0/credentials
sudo chmod 700 /etc/trader-assist-v0/credentials
```

## 5b. Notification Credential Installation

The notification credential content must first be created outside the terminal
through an approved secret manager or approved secure editor/export mechanism.
Never type or paste credential content into terminal commands.  The shell
workflow receives only the path to the already-prepared secure source file.

The operator must prepare a secure source file (e.g. at
`/root/secure/notification.json`) that satisfies:

- absolute path;
- not a symlink;
- regular file;
- owner-only permissions (0600).

Then install the credential into the production path:

```bash
# Verify the source file meets all preconditions
SOURCE="/root/secure/notification.json"
test -f "$SOURCE" || { echo "ERROR: source not found"; exit 1; }
test "${SOURCE#/}" != "$SOURCE" || { echo "ERROR: source must be absolute"; exit 1; }
test ! -L "$SOURCE" || { echo "ERROR: source must not be a symlink"; exit 1; }
test "$(stat -c '%a' "$SOURCE")" = "600" || { echo "ERROR: source must be 0600"; exit 1; }

# Create same-directory temporary destination
sudo install -m 600 -o root -g root "$SOURCE" /etc/trader-assist-v0/credentials/notification.json.tmp

# Run the production offline validation-only path
sudo /opt/trader-assist-v0/venv/bin/python \
  /opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py \
  --validate-only \
  --notification-credential-file /etc/trader-assist-v0/credentials/notification.json.tmp \
  --webhook-timeout-seconds 10 \
  && echo "PASS: credential validation succeeded" \
  || { echo "FAIL: credential validation failed"; \
       sudo rm -f /etc/trader-assist-v0/credentials/notification.json.tmp; exit 1; }

# Atomically rename only after successful validation
sudo mv /etc/trader-assist-v0/credentials/notification.json.tmp \
       /etc/trader-assist-v0/credentials/notification.json

# Securely remove the external source according to operator policy
# (operator is responsible for secure removal of the source file)
```

The credential file:
- Path: `/etc/trader-assist-v0/credentials/notification.json`
- Owner: `root:root`
- Mode: `0600`
- systemd supplies a private per-service runtime copy via `LoadCredential`.
- The wrapper receives the credential at `$CREDENTIALS_DIRECTORY/notification.json`.
- No webhook URL, authorization header name or value appear in process argv.

## 5c. Credential Rotation

To rotate the credential without disrupting active runtime sessions:

1. Prepare a new secure source file outside the terminal (see Section 5b).
2. Copy to a same-directory temporary destination (`notification.json.new`).
3. Validate with the production offline validation-only path.
4. Atomically rename only after successful validation.
5. Clean up the temporary file on validation failure.
6. Restart the service only under separate runtime authorization.

```bash
SOURCE="/root/secure/notification-rotated.json"
test -f "$SOURCE" || { echo "ERROR: source not found"; exit 1; }
test "${SOURCE#/}" != "$SOURCE" || { echo "ERROR: source must be absolute"; exit 1; }
test ! -L "$SOURCE" || { echo "ERROR: source must not be a symlink"; exit 1; }
test "$(stat -c '%a' "$SOURCE")" = "600" || { echo "ERROR: source must be 0600"; exit 1; }

sudo install -m 600 -o root -g root "$SOURCE" /etc/trader-assist-v0/credentials/notification.json.new

sudo /opt/trader-assist-v0/venv/bin/python \
  /opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py \
  --validate-only \
  --notification-credential-file /etc/trader-assist-v0/credentials/notification.json.new \
  --webhook-timeout-seconds 10 \
  && echo "PASS: rotated credential validation succeeded" \
  || { echo "FAIL: rotated credential validation failed"; \
       sudo rm -f /etc/trader-assist-v0/credentials/notification.json.new; exit 1; }

# Atomically replace
sudo mv /etc/trader-assist-v0/credentials/notification.json.new \
       /etc/trader-assist-v0/credentials/notification.json
```

## 5d. Credential Rollback

Credential removal is performed only after the final-state verifier passes in
the ordered rollback procedure in Section 24.  Do not use a direct wrapper or
Python invocation as an operational substitute for the systemd unit.

## 6. SQLite State Directory

```bash
sudo mkdir -p /var/lib/trader-assist-v0
sudo chown traderassist:traderassist /var/lib/trader-assist-v0
sudo chmod 750 /var/lib/trader-assist-v0
```

## 7. Ownership and Permissions

- `/opt/trader-assist-v0`: owned by `root:root`, mode 755.
- `/opt/trader-assist-v0/venv`: owned by `root:root`, mode 755.
- `/etc/trader-assist-v0`: owned by `root:root`, mode 755.
- `/var/lib/trader-assist-v0`: owned by `traderassist:traderassist`, mode 750.
- All Python sources and scripts under `/opt/trader-assist-v0`: owned by `root:root`, mode 644 (scripts mode 755).
- The wrapper script at `scripts/p4a/run_restricted_public_runtime.sh`: owned by `root:root`, mode 755.

## 8. Environment Configuration

Copy the environment example to the configuration directory:

```bash
sudo cp deploy/p4a/systemd/trader-assist-v0-public.env.example /etc/trader-assist-v0/public.env
sudo chown root:root /etc/trader-assist-v0/public.env
sudo chmod 600 /etc/trader-assist-v0/public.env
```

Prepare the real environment configuration by editing `/etc/trader-assist-v0/public.env`
with operator-reviewed values. At minimum:

- `TRADER_ASSIST_V0_ENABLE` must be set to `1` for activation.
- `TRADER_ASSIST_V0_MODE` must be exactly `RESTRICTED_PUBLIC_LIVE_SHADOW`.
- `TRADER_ASSIST_V0_DATABASE_PATH` must point to a path under `/var/lib/trader-assist-v0`.
- `TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH` must point to a path under `/etc/trader-assist-v0`.

`PYTHONPATH` must NOT be defined or overridden in `public.env`.  The production
wrapper forces `PYTHONPATH=/opt/trader-assist-v0/src` so `trader_assist_v0`
imports exclusively from the approved source tree.

SECURE NOTIFICATION CREDENTIAL INGRESS:

The webhook URL and optional authorization header are supplied via a versioned
JSON credential file at `/etc/trader-assist-v0/credentials/notification.json`
(see Sections 5a-5d).  systemd provides a private per-service runtime copy via
`LoadCredential`.  The wrapper passes only the credential file path to Python.
No webhook URL, token, authorization header name or authorization header value
may appear in this environment file or in process argv.

## 9. Risk Configuration

Copy the risk configuration example:

```bash
sudo cp deploy/p4a/config/risk-configuration.json.example /etc/trader-assist-v0/risk-configuration.json
sudo chown root:root /etc/trader-assist-v0/risk-configuration.json
sudo chmod 600 /etc/trader-assist-v0/risk-configuration.json
```

Edit `/etc/trader-assist-v0/risk-configuration.json` with reviewed operator values.
The example file fails closed and is incapable of activating the runtime unchanged.

## 10. Default-Off Requirement

The service must remain default-off before the operator creates an activation
permit. After unit installation in Section 12, run the installed and pre-start
verifiers before creating or using the permit. A verifier `SAFE_STOP` is
evidence that the dedicated host is not in an approved state.

## 11. Activation Permit Boundary

The service uses `ConditionPathExists=/etc/trader-assist-v0/activation-permit` to remain
default-off. Complete Section 12 and obtain both verifier `PASS` results
before creating the permit below. The permit file must be created by the
operator:

```bash
sudo touch /etc/trader-assist-v0/activation-permit
sudo chown root:root /etc/trader-assist-v0/activation-permit
sudo chmod 644 /etc/trader-assist-v0/activation-permit
```

The wrapper script and service unit never create the activation permit.

## 12. Service Installation

Install the systemd unit:

```bash
sudo cp deploy/p4a/systemd/trader-assist-v0-public.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo /opt/trader-assist-v0/scripts/p4a/verify_first_launch_runtime_state.sh installed
sudo /opt/trader-assist-v0/scripts/p4a/verify_first_launch_runtime_state.sh pre-start
```

The verifier is read-only. It validates only
`trader-assist-v0-public.service`: reviewed and installed unit equality,
owner/mode, exact fragment, no drop-ins, dedicated User/Group, and
`systemd-analyze verify`. It does not audit unrelated services or mutate any
lifecycle state.

## 12a. Database Evidence Selection

Use the database verifier, never an inline SQLite program. It parses
`public.env` as inert text and opens SQLite read-only. Choose exactly one
pre-start path:

```bash
# Existing reviewed database
sudo /opt/trader-assist-v0/venv/bin/python /opt/trader-assist-v0/scripts/p4a/verify_first_launch_database.py existing-before-smoke

# Fresh approved database path, before the first start
sudo /opt/trader-assist-v0/venv/bin/python /opt/trader-assist-v0/scripts/p4a/verify_first_launch_database.py fresh-pre-start
```

The fresh path must be absent at this point. The existing path must have
exactly one `ok` integrity result. Record the selected phase and result in the
evidence manifest without recording credential contents.

## 13. Start Procedure

```bash
sudo /opt/trader-assist-v0/scripts/p4a/verify_first_launch_runtime_state.sh pre-start
sudo systemctl start trader-assist-v0-public.service
sudo /opt/trader-assist-v0/scripts/p4a/verify_first_launch_runtime_state.sh post-start
```

For a fresh database, immediately record creation evidence:

```bash
sudo /opt/trader-assist-v0/venv/bin/python /opt/trader-assist-v0/scripts/p4a/verify_first_launch_database.py fresh-post-creation
```

## 14. Stop Procedure

```bash
sudo systemctl stop trader-assist-v0-public.service
sudo /opt/trader-assist-v0/scripts/p4a/verify_first_launch_runtime_state.sh pre-start
```

## 15. Controlled Restart Procedure

Exactly one controlled restart is permitted:

```bash
sudo systemctl stop trader-assist-v0-public.service
sudo /opt/trader-assist-v0/scripts/p4a/verify_first_launch_runtime_state.sh pre-start
sudo systemctl start trader-assist-v0-public.service
sudo /opt/trader-assist-v0/scripts/p4a/verify_first_launch_runtime_state.sh post-start
```

## 16. Status Procedure

```bash
sudo systemctl status trader-assist-v0-public.service
```

## 17. Journald Observation

View runtime logs:

```bash
sudo journalctl -u trader-assist-v0-public.service -f
```

View bounded recent logs:

```bash
sudo journalctl -u trader-assist-v0-public.service --since "30 minutes ago" --no-pager
```

Journald rotation is managed by the system journal configuration. The service
does not configure its own rotation.

## 18. Bounded Journal Extraction

Extract a time-bounded journal segment for evidence:

```bash
sudo journalctl -u trader-assist-v0-public.service \
  --since "YYYY-MM-DD HH:MM:SS" --until "YYYY-MM-DD HH:MM:SS" \
  --no-pager > /tmp/trader-assist-v0-journal-evidence.txt
```

## 19. Read-Only SQLite Health Evidence

At the end of the observation period, run the final evidence phase. This is
read-only and requires exactly one `ok` integrity result.

```bash
sudo /opt/trader-assist-v0/venv/bin/python /opt/trader-assist-v0/scripts/p4a/verify_first_launch_database.py final-post-smoke
```

## 20. READY Verification

The runtime is READY when the journal shows the session activation message:

```
session=<uuid> mode=RESTRICTED_PUBLIC_LIVE_SHADOW scope=ETH_ONLY
```

## 21. STOPPING Verification

The runtime is STOPPING when a SIGTERM is delivered and the journal shows the
shutdown sequence.

## 22. STOPPED Verification

The runtime is STOPPED when:

```bash
sudo systemctl is-active trader-assist-v0-public.service
```

returns `inactive`.

## 23. Runtime Session Verification

- **Open session**: Journal contains `session=<uuid> mode=RESTRICTED_PUBLIC_LIVE_SHADOW scope=ETH_ONLY` without a subsequent shutdown message.
- **Closed session**: Journal contains the shutdown message after the session activation.

## 24. Rollback

The required order is stop → disable → final-state PASS → delete credential,
permit, unit, or deployment files. Do not delete any deployment asset before
the final-state proof succeeds.

```bash
sudo systemctl stop trader-assist-v0-public.service
sudo systemctl disable trader-assist-v0-public.service
sudo /opt/trader-assist-v0/scripts/p4a/verify_first_launch_runtime_state.sh final-state
sudo /opt/trader-assist-v0/venv/bin/python /opt/trader-assist-v0/scripts/p4a/verify_first_launch_database.py final-post-smoke
sudo rm -f /etc/trader-assist-v0/credentials/notification.json
sudo rm -f /etc/trader-assist-v0/activation-permit
sudo rm /etc/systemd/system/trader-assist-v0-public.service
sudo systemctl daemon-reload
```

## 25. Uninstall

```bash
sudo systemctl stop trader-assist-v0-public.service || true
sudo systemctl disable trader-assist-v0-public.service || true
sudo /opt/trader-assist-v0/scripts/p4a/verify_first_launch_runtime_state.sh final-state
sudo rm /etc/systemd/system/trader-assist-v0-public.service
sudo systemctl daemon-reload
sudo rm -rf /etc/trader-assist-v0
sudo rm -rf /var/lib/trader-assist-v0
sudo rm -rf /opt/trader-assist-v0
sudo userdel traderassist || true
sudo groupdel traderassist || true
```

## 26. Proof That No Runtime Remains

Section 24's `final-state` verifier is the required proof. It confirms the
authorized unit is inactive and disabled, has MainPID 0 and no lifecycle job,
and that the dedicated user, wrapper, entrypoint, and authorized cgroup are
absent or empty.

## 27. P4-A / P4-B Separation

P4-A (this package) is the local deployment package for a single supervised Linux
instance. P4-B is a separate, later-bounded workstream for continuous LIVE_SHADOW
deployment. P4-A does not authorize or configure P4-B.

## 28. P4-B / Continuous LIVE_SHADOW Separation

The continuous LIVE_SHADOW deployment (P4-B) is a separately authorized workstream.
P4-A prepares only the P4-A local deployment package. No P4-B configuration,
deployment, or runtime is included.

## 29. Future Smoke Plan

LOCAL/NON_AWS SMOKE IS NOT AUTHORIZED BY THIS WRITE LEASE.

The future smoke plan must specify:

- one Linux instance;
- one process;
- one SQLite database;
- ETH only;
- approved public endpoints only;
- no account credentials;
- no trading credentials;
- at least 30 minutes after initial READY;
- exactly one controlled stop and restart;
- at least 30 minutes after post-restart READY;
- target total of 60 minutes;
- maximum extension to 90 minutes;
- final service stopped;
- final service disabled;
- no runtime remaining.

LOCAL/NON_AWS SMOKE IS NOT AUTHORIZED BY THIS WRITE LEASE.

## 30. Service Validation

The installed-state verifier performs the required systemd syntax validation,
exact unit comparison, and installed-unit authority checks:

```bash
sudo /opt/trader-assist-v0/scripts/p4a/verify_first_launch_runtime_state.sh installed
```

LOCAL/NON_AWS SMOKE IS NOT AUTHORIZED BY THIS WRITE LEASE.
