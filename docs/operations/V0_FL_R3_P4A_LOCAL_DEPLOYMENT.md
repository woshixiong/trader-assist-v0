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

Clone the repository to `/opt/trader-assist-v0`:

```bash
sudo git clone https://github.com/woshixiong/trader-assist-v0.git /opt/trader-assist-v0
sudo chown -R root:root /opt/trader-assist-v0
```

## 4. Virtual Environment

Create the Python virtual environment under `/opt/trader-assist-v0/venv` and install
dependencies using the original hashed lockfiles:

```bash
cd /opt/trader-assist-v0
sudo python3.12 -m venv venv
sudo venv/bin/pip install --require-hashes -r requirements-runtime.lock
```

## 5. Configuration Directory

```bash
sudo mkdir -p /etc/trader-assist-v0
sudo chown root:root /etc/trader-assist-v0
sudo chmod 755 /etc/trader-assist-v0
```

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
- `TRADER_ASSIST_V0_WEBHOOK_URL` must contain a valid HTTPS webhook URL.
- `TRADER_ASSIST_V0_DATABASE_PATH` must point to a path under `/var/lib/trader-assist-v0`.
- `TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH` must point to a path under `/etc/trader-assist-v0`.

## 9. Risk Configuration

Copy the risk configuration example:

```bash
sudo cp deploy/p4a/config/risk-configuration.json.example /etc/trader-assist-v0/risk-configuration.json
sudo chown root:root /etc/trader-assist-v0/risk-configuration.json
sudo chmod 600 /etc/trader-assist-v0/risk-configuration.json
```

Edit `/etc/trader-assist-v0/risk-configuration.json` with reviewed operator values.
The example file fails closed and is incapable of activating the runtime unchanged.

## 10. Default-Off Proof

Before creating the activation permit, verify the service is inactive:

```bash
sudo systemctl is-active trader-assist-v0-public.service
```

Expected output: `inactive`.

## 11. Activation Permit Boundary

The service uses `ConditionPathExists=/etc/trader-assist-v0/activation-permit` to remain
default-off. The permit file must be created by the operator:

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
```

## 13. Start Procedure

```bash
sudo systemctl start trader-assist-v0-public.service
```

## 14. Stop Procedure

```bash
sudo systemctl stop trader-assist-v0-public.service
```

## 15. Controlled Restart Procedure

Exactly one controlled restart is permitted:

```bash
sudo systemctl stop trader-assist-v0-public.service
sudo systemctl start trader-assist-v0-public.service
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

## 19. Read-Only SQLite Health Queries

Using Python stdlib only (no external tools required):

```bash
sudo -u traderassist /opt/trader-assist-v0/venv/bin/python -c "
import sqlite3
conn = sqlite3.connect('file:/var/lib/trader-assist-v0/runtime.db?mode=ro', uri=True)
print('journal_mode:', conn.execute('PRAGMA journal_mode').fetchone()[0])
print('integrity_check:', conn.execute('PRAGMA integrity_check').fetchone()[0])
conn.close()
"
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

To roll back the deployment:

```bash
sudo systemctl stop trader-assist-v0-public.service
sudo systemctl disable trader-assist-v0-public.service
sudo rm /etc/systemd/system/trader-assist-v0-public.service
sudo systemctl daemon-reload
sudo rm -f /etc/trader-assist-v0/activation-permit
```

## 25. Uninstall

```bash
sudo systemctl stop trader-assist-v0-public.service || true
sudo systemctl disable trader-assist-v0-public.service || true
sudo rm /etc/systemd/system/trader-assist-v0-public.service
sudo systemctl daemon-reload
sudo rm -rf /etc/trader-assist-v0
sudo rm -rf /var/lib/trader-assist-v0
sudo rm -rf /opt/trader-assist-v0
sudo userdel traderassist || true
sudo groupdel traderassist || true
```

## 26. Proof That No Runtime Remains

```bash
sudo systemctl is-active trader-assist-v0-public.service || echo "inactive"
pgrep -f run_restricted_public_runtime.sh || echo "no wrapper process"
pgrep -f run_first_launch_public_runtime.py || echo "no Python process"
```

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

Validate the systemd unit syntax:

```bash
sudo systemd-analyze verify /etc/systemd/system/trader-assist-v0-public.service
```

LOCAL/NON_AWS SMOKE IS NOT AUTHORIZED BY THIS WRITE LEASE.