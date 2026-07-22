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

Credential rollback is a deployment stop, not a supported way to continue a
runtime session. The authoritative final-state proof is the Section 15
`OPERATION="final-state"` mode. Do not substitute display-only process
commands for that proof.

```bash
# Stop synchronously, disable the unit, and remove the credential and permit.
sudo systemctl stop trader-assist-v0-public.service
sudo systemctl disable trader-assist-v0-public.service
sudo rm -f /etc/trader-assist-v0/credentials/notification.json
sudo rm -f /etc/trader-assist-v0/activation-permit

# Run the complete self-contained Section 15 block with:
# OPERATION="final-state"
# It must print PASS before this rollback is considered complete.
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

P4A remains the repository deployment package. The controls in Section 15
govern its use only in a separately authorized P4B deployment/runtime stage;
this runbook grants no P4B, AWS, runtime, or smoke authority. Set
`OPERATION="pre-start"` in the complete Section 15 block and proceed only
when it prints `PASS`.

```bash
sudo systemctl start trader-assist-v0-public.service
```

## 14. Stop Procedure

```bash
sudo systemctl stop trader-assist-v0-public.service
```

## 15. P4B Single-Instance Authority

P4B has one live operational authority: systemd. The only supported P4B live activation path is:

```bash
sudo systemctl start trader-assist-v0-public.service
```

Direct live execution of either
`scripts/p4a/run_restricted_public_runtime.sh` or
`scripts/run_first_launch_public_runtime.py` is unsupported and prohibited.
Do not create or use a second service unit, copied service unit, templated
service instance, or alternate unit that launches the same runtime. Do not use
a second SQLite database path to operate a parallel live runtime; separate
databases do not make parallel P4B runtime operation supported.

The sole direct-Python exception is offline validation with `--validate-only`,
such as the credential-validation commands in Sections 5b and 5c. Validation
only neither authorizes nor starts the live runtime.

The following is the single canonical, self-contained systemd Linux
verification block. Set `OPERATION` to exactly one supported mode before
executing it: `pre-start`, `post-start`, `controlled-restart`, or
`final-state`. It is deliberately constrained to unified cgroup v2. Any
unsupported manager, cgroup, process, or configuration representation is a
`SAFE_STOP`. It does not start a runtime when `OPERATION="pre-start"` or
`OPERATION="final-state"`, and it never kills a process automatically.
Aliases and normal enablement links that resolve to the same literal authorized
`FragmentPath` are one unit identity, not duplicate runtime units.

```bash
set -eu
set -o pipefail

OPERATION="pre-start"
SERVICE="trader-assist-v0-public.service"
AUTHORIZED_FRAGMENT="/etc/systemd/system/trader-assist-v0-public.service"
APPROVED_WRAPPER="/opt/trader-assist-v0/scripts/p4a/run_restricted_public_runtime.sh"
APPROVED_PYTHON="/opt/trader-assist-v0/venv/bin/python"
APPROVED_ENTRYPOINT="/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py"

safe_stop() {
  printf 'SAFE_STOP: %s\n' "$1" >&2
  exit 1
}

read_unit_property() {
  property="$1"
  unit="$2"
  if ! value="$(sudo systemctl show --property="$property" --value "$unit" 2>&1)"; then
    safe_stop "cannot inspect $property for $unit"
  fi
  printf '%s' "$value"
}

assert_active_state() {
  expected_state="$1"
  active_state="$(read_unit_property ActiveState "$SERVICE")"
  test "$active_state" = "$expected_state" || safe_stop "ActiveState is not $expected_state"
  set +e
  is_active_output="$(sudo systemctl is-active "$SERVICE" 2>&1)"
  is_active_status=$?
  set -e
  case "$expected_state:$is_active_status" in
    active:0|inactive:3) ;;
    *) safe_stop "is-active returned an unexpected status" ;;
  esac
  test "$is_active_output" = "$expected_state" || safe_stop "is-active is not exactly $expected_state"
}

assert_numeric_nonzero_pid() {
  candidate_pid="$1"
  case "$candidate_pid" in
    ''|0|*[!0-9]*) safe_stop "MainPID is not one nonzero numeric PID" ;;
  esac
}

assert_no_lifecycle_job() {
  if ! lifecycle_jobs="$(sudo systemctl list-jobs --no-legend --no-pager 2>&1)"; then
    safe_stop "cannot inspect systemd jobs"
  fi
  matching_job_count="$(printf '%s\n' "$lifecycle_jobs" | awk -v unit="$SERVICE" '$2 == unit { count++ } END { print count + 0 }')"
  test "$matching_job_count" = "0" || safe_stop "P4B lifecycle job is already in progress"
}

assert_effective_unit_identity() {
  load_state="$(read_unit_property LoadState "$SERVICE")"
  fragment_path="$(read_unit_property FragmentPath "$SERVICE")"
  transient="$(read_unit_property Transient "$SERVICE")"
  drop_in_paths="$(read_unit_property DropInPaths "$SERVICE")"
  exec_start="$(read_unit_property ExecStart "$SERVICE")"
  test "$load_state" = "loaded" || safe_stop "LoadState is not loaded"
  test "$fragment_path" = "$AUTHORIZED_FRAGMENT" || safe_stop "FragmentPath is not the authorized installed unit"
  test "$transient" = "no" || safe_stop "Transient unit state is active"
  test -z "$drop_in_paths" || safe_stop "DropInPaths is not empty"
  exec_path="$(printf '%s\n' "$exec_start" | awk 'NR == 1 { prefix = "{ path="; if (index($0, prefix) == 1) { value = substr($0, length(prefix) + 1); sub(/ ;.*/, "", value); print value } }')"
  exec_argv="$(printf '%s\n' "$exec_start" | awk 'NR == 1 { marker = "argv[]="; position = index($0, marker); if (position > 0) { value = substr($0, position + length(marker)); sub(/ ;.*/, "", value); print value } }')"
  exec_path_count="$(printf '%s\n' "$exec_start" | awk -F 'path=' '{ print NF - 1 }')"
  test "$exec_path_count" = "1" || safe_stop "ExecStart does not contain exactly one command"
  test "$exec_path" = "$APPROVED_WRAPPER" || safe_stop "ExecStart path is not the approved wrapper"
  test "$exec_argv" = "$APPROVED_WRAPPER" || safe_stop "ExecStart argv is not exactly the approved wrapper"

  if ! manager_units="$({
    sudo systemctl list-units --type=service --all --no-legend --plain --no-pager | awk 'NF { print $1 }'
    sudo systemctl list-unit-files --type=service --no-legend --no-pager | awk 'NF { print $1 }'
  } | LC_ALL=C sort -u)"; then
    safe_stop "cannot enumerate manager-known service units"
  fi
  test -n "$manager_units" || safe_stop "manager-known service-unit list is empty"
  while IFS= read -r candidate_unit; do
    case "$candidate_unit" in *.service) ;; *) safe_stop "manager returned an unsupported service-unit name" ;; esac
    candidate_load="$(read_unit_property LoadState "$candidate_unit")"
    candidate_fragment="$(read_unit_property FragmentPath "$candidate_unit")"
    candidate_exec="$(read_unit_property ExecStart "$candidate_unit")"
    case "$candidate_load" in
      loaded)
        test -n "$candidate_fragment" || safe_stop "loaded service has no FragmentPath"
        test -n "$candidate_exec" || safe_stop "loaded service has no inspectable ExecStart"
        ;;
      not-found)
        test -z "$candidate_exec" || safe_stop "not-found service has an effective ExecStart"
        continue
        ;;
      *) safe_stop "service unit has unsupported LoadState" ;;
    esac
    test "$candidate_fragment" = "$AUTHORIZED_FRAGMENT" && continue
    if printf '%s\n' "$candidate_exec" | grep -Fq "path=$APPROVED_WRAPPER"; then safe_stop "another manager-known unit launches the approved wrapper"; fi
    if printf '%s\n' "$candidate_exec" | grep -Fq "argv[]=$APPROVED_WRAPPER"; then safe_stop "another manager-known unit launches the approved wrapper"; fi
    if printf '%s\n' "$candidate_exec" | grep -Fq "path=$APPROVED_ENTRYPOINT"; then safe_stop "another manager-known unit launches the approved Python entrypoint"; fi
    if printf '%s\n' "$candidate_exec" | grep -Fq "/opt/trader-assist-v0/"; then safe_stop "another manager-known unit launches a Trader Assist runtime path"; fi
  done <<EOF
$manager_units
EOF
}

collect_dedicated_user_pids() {
  if ! DEDICATED_UID="$(id -u traderassist 2>&1)"; then safe_stop "cannot resolve the dedicated traderassist UID"; fi
  case "$DEDICATED_UID" in ''|*[!0-9]*) safe_stop "dedicated traderassist UID is invalid" ;; esac
  set +e
  DEDICATED_PIDS="$(sudo pgrep -u "$DEDICATED_UID" 2>&1)"
  pgrep_status=$?
  set -e
  case "$pgrep_status" in 0|1) ;; *) safe_stop "cannot inspect processes owned by traderassist" ;; esac
  test "$pgrep_status" = "0" || DEDICATED_PIDS=""
}

collect_approved_runtime_pids() {
  set +e
  WRAPPER_PIDS="$(sudo pgrep -f '[r]un_restricted_public_runtime.sh' 2>&1)"
  wrapper_status=$?
  PYTHON_PIDS="$(sudo pgrep -f '[r]un_first_launch_public_runtime.py' 2>&1)"
  python_status=$?
  set -e
  case "$wrapper_status" in 0|1) ;; *) safe_stop "cannot inspect approved wrapper processes" ;; esac
  case "$python_status" in 0|1) ;; *) safe_stop "cannot inspect approved Python processes" ;; esac
  test "$wrapper_status" = "0" || WRAPPER_PIDS=""
  test "$python_status" = "0" || PYTHON_PIDS=""
}

line_count() {
  printf '%s\n' "$1" | awk 'NF { count++ } END { print count + 0 }'
}

sole_pid() {
  printf '%s\n' "$1" | awk 'NF { print; exit }'
}

assert_unified_cgroup_v2() {
  test -r /sys/fs/cgroup/cgroup.controllers || safe_stop "P4B verification requires unified cgroup v2"
  SERVICE_CGROUP="$(read_unit_property ControlGroup "$SERVICE")"
  case "$SERVICE_CGROUP" in /*) ;; *) safe_stop "ControlGroup is not an absolute cgroup-v2 path" ;; esac
  case "$SERVICE_CGROUP" in *'..'*) safe_stop "ControlGroup contains an unsupported path component" ;; esac
  SERVICE_CGROUP_DIR="/sys/fs/cgroup$SERVICE_CGROUP"
}

assert_empty_service_cgroup() {
  assert_unified_cgroup_v2
  if [ -e "$SERVICE_CGROUP_DIR" ]; then
    test -d "$SERVICE_CGROUP_DIR" || safe_stop "ControlGroup is not a directory"
    test -r "$SERVICE_CGROUP_DIR/cgroup.procs" || safe_stop "cannot inspect ControlGroup processes"
    if ! cgroup_pids="$(sudo cat "$SERVICE_CGROUP_DIR/cgroup.procs" 2>&1)"; then safe_stop "cannot read ControlGroup processes"; fi
    test -z "$cgroup_pids" || safe_stop "authorized service cgroup is populated"
  fi
}

assert_pre_start() {
  assert_effective_unit_identity
  assert_active_state inactive
  main_pid="$(read_unit_property MainPID "$SERVICE")"
  test "$main_pid" = "0" || safe_stop "MainPID is not 0 before start"
  assert_no_lifecycle_job
  collect_dedicated_user_pids
  test -z "$DEDICATED_PIDS" || safe_stop "traderassist owns unexplained process(es)"
  collect_approved_runtime_pids
  test -z "$WRAPPER_PIDS" || safe_stop "approved wrapper process exists before start"
  test -z "$PYTHON_PIDS" || safe_stop "approved Python runtime process exists before start"
  assert_empty_service_cgroup
}

assert_post_start() {
  assert_effective_unit_identity
  assert_active_state active
  MAIN_PID="$(read_unit_property MainPID "$SERVICE")"
  assert_numeric_nonzero_pid "$MAIN_PID"
  test -d "/proc/$MAIN_PID" || safe_stop "MainPID does not exist in /proc"
  collect_dedicated_user_pids
  test "$(line_count "$DEDICATED_PIDS")" = "1" || safe_stop "expected exactly one traderassist process"
  DEDICATED_PID="$(sole_pid "$DEDICATED_PIDS")"
  test "$DEDICATED_PID" = "$MAIN_PID" || safe_stop "sole traderassist PID is not MainPID"
  if ! approved_python_exe="$(sudo readlink -f "$APPROVED_PYTHON" 2>&1)"; then safe_stop "cannot resolve approved Python executable"; fi
  if ! runtime_python_exe="$(sudo readlink -f "/proc/$MAIN_PID/exe" 2>&1)"; then safe_stop "cannot inspect MainPID executable"; fi
  test "$runtime_python_exe" = "$approved_python_exe" || safe_stop "MainPID executable is not the approved Python executable"
  if ! runtime_argv="$(sudo sh -c 'tr "\\000" "\\n" < "$1"' sh "/proc/$MAIN_PID/cmdline" 2>&1)"; then safe_stop "cannot inspect MainPID argv"; fi
  runtime_argv0="$(printf '%s\n' "$runtime_argv" | awk 'NR == 1 { print; exit }')"
  runtime_argv1="$(printf '%s\n' "$runtime_argv" | awk 'NR == 2 { print; exit }')"
  test "$runtime_argv0" = "$APPROVED_PYTHON" || safe_stop "MainPID argv[0] is not the approved Python executable"
  test "$runtime_argv1" = "$APPROVED_ENTRYPOINT" || safe_stop "MainPID argv[1] is not the approved Python entrypoint"
  assert_unified_cgroup_v2
  test -d "$SERVICE_CGROUP_DIR" || safe_stop "authorized service cgroup does not exist after start"
  if ! runtime_cgroup="$(sudo cat "/proc/$MAIN_PID/cgroup" 2>&1)"; then safe_stop "cannot inspect MainPID cgroup"; fi
  expected_cgroup_line="0::$SERVICE_CGROUP"
  test "$runtime_cgroup" = "$expected_cgroup_line" || safe_stop "MainPID cgroup is not literally the service ControlGroup"
  if ! cgroup_pids="$(sudo cat "$SERVICE_CGROUP_DIR/cgroup.procs" 2>&1)"; then safe_stop "cannot inspect populated service cgroup"; fi
  test "$cgroup_pids" = "$MAIN_PID" || safe_stop "service cgroup does not contain exactly MainPID"
  collect_approved_runtime_pids
  test -z "$WRAPPER_PIDS" || safe_stop "approved wrapper remains after exec"
  test "$(line_count "$PYTHON_PIDS")" = "1" || safe_stop "expected exactly one approved Python runtime process"
  test "$(sole_pid "$PYTHON_PIDS")" = "$MAIN_PID" || safe_stop "approved Python runtime PID is not MainPID"
}

assert_final_state() {
  assert_effective_unit_identity
  assert_active_state inactive
  main_pid="$(read_unit_property MainPID "$SERVICE")"
  test "$main_pid" = "0" || safe_stop "MainPID is not 0 in final state"
  unit_file_state="$(read_unit_property UnitFileState "$SERVICE")"
  test "$unit_file_state" = "disabled" || safe_stop "UnitFileState is not exactly disabled"
  assert_no_lifecycle_job
  assert_empty_service_cgroup
  collect_approved_runtime_pids
  test -z "$WRAPPER_PIDS" || safe_stop "approved wrapper process exists in final state"
  test -z "$PYTHON_PIDS" || safe_stop "approved Python runtime process exists in final state"
  collect_dedicated_user_pids
  test -z "$DEDICATED_PIDS" || safe_stop "traderassist owns process(es) in final state"
}

controlled_restart() {
  assert_effective_unit_identity
  assert_active_state active
  ORIGINAL_PID="$(read_unit_property MainPID "$SERVICE")"
  assert_numeric_nonzero_pid "$ORIGINAL_PID"
  assert_post_start
  test "$MAIN_PID" = "$ORIGINAL_PID" || safe_stop "original MainPID identity changed before stop"
  if ! ORIGINAL_START_TICKS="$(sudo awk '{ print $22 }' "/proc/$ORIGINAL_PID/stat" 2>&1)"; then safe_stop "cannot record original process start ticks"; fi
  case "$ORIGINAL_START_TICKS" in ''|*[!0-9]*) safe_stop "original process start ticks are invalid" ;; esac
  printf 'EVIDENCE: original_pid=%s original_start_ticks=%s\n' "$ORIGINAL_PID" "$ORIGINAL_START_TICKS"
  sudo systemctl stop "$SERVICE"
  test ! -e "/proc/$ORIGINAL_PID" || safe_stop "original PID still exists after synchronous stop"
  assert_active_state inactive
  main_pid="$(read_unit_property MainPID "$SERVICE")"
  test "$main_pid" = "0" || safe_stop "MainPID is not 0 after stop"
  collect_dedicated_user_pids
  test -z "$DEDICATED_PIDS" || safe_stop "traderassist process remains after stop"
  collect_approved_runtime_pids
  test -z "$WRAPPER_PIDS" || safe_stop "approved wrapper process remains after stop"
  test -z "$PYTHON_PIDS" || safe_stop "approved Python runtime process remains after stop"
  assert_pre_start
  sudo systemctl start "$SERVICE"
  assert_post_start
  NEW_PID="$MAIN_PID"
  test "$NEW_PID" != "$ORIGINAL_PID" || safe_stop "new MainPID equals original PID"
  printf 'PASS: controlled restart recorded new_pid=%s; original identity was absent before start, so no overlap was observed\n' "$NEW_PID"
}

case "$OPERATION" in
  pre-start) assert_pre_start; printf 'PASS: effective unit verified; inactive; MainPID=0; no job, cgroup, runtime, or traderassist process\n' ;;
  post-start) assert_post_start; printf 'PASS: active MainPID, approved Python argv, and literal cgroup identity verified\n' ;;
  controlled-restart) controlled_restart ;;
  final-state) assert_final_state; printf 'PASS: loaded disabled unit is inactive with MainPID=0 and no cgroup, runtime, or traderassist process\n' ;;
  *) safe_stop "OPERATION must be pre-start, post-start, controlled-restart, or final-state" ;;
esac
```

The dedicated `traderassist` account is reserved for the authorized service,
so any unexplained process owned by that UID requires `SAFE_STOP`. The checks
are bounded operational checks, not universal detection of arbitrarily
disguised processes, unrelated UIDs, arbitrary implementations, PID reuse, or
every possible race. Detection of an out-of-band live wrapper or Python
process, duplicate/copied/templated/alternate runtime unit, multiple matching
runtime processes, a matching process outside the literal authorized service
cgroup, an alternate live database-backed runtime, or an unresolved lifecycle
command requires `SAFE_STOP` before deployment, runtime activation, or
continued smoke. Stop the workflow and obtain Project Control and Engineering
Optimization review.

Concurrent execution can cause SQLite write contention, delayed writes,
database-locked operational failures, competing runtime-session records,
duplicate processing, unique-constraint conflicts, notification-delivery
races, and duplicate semantic output. Do not claim SQLite corruption unless
independent evidence demonstrates it.

## 16. Controlled Restart Procedure

Exactly one controlled restart is permitted during separately authorized
supervised smoke. Set `OPERATION="controlled-restart"` in the self-contained
Section 15 block. That mode establishes the original authorized process
identity and start ticks, stops synchronously, proves the original identity
absent, invokes the complete pre-start checks in the same shell sequence, and
then performs the systemd-only start and post-start identity proof. It prints
`PASS` only after the new PID differs and the absence-before-start proof
establishes that no overlap was observed.

## 17. Status Procedure

```bash
sudo systemctl status trader-assist-v0-public.service
```

## 18. Journald Observation

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

## 19. Bounded Journal Extraction

Extract a time-bounded journal segment for evidence:

```bash
sudo journalctl -u trader-assist-v0-public.service \
  --since "YYYY-MM-DD HH:MM:SS" --until "YYYY-MM-DD HH:MM:SS" \
  --no-pager > /tmp/trader-assist-v0-journal-evidence.txt
```

## 20. Configured Database Read-Only Integrity Evidence

Use this bounded parser and read-only check before and after separately
authorized smoke. It does not source or execute `public.env`; it accepts
exactly one unquoted `TRADER_ASSIST_V0_DATABASE_PATH=` assignment, requires a
regular configured database file below the approved state directory, retrieves
the complete `PRAGMA integrity_check` result set, and prints `PASS` only for
exactly one `ok` row.

```bash
set -eu
set -o pipefail

ENVIRONMENT_FILE="/etc/trader-assist-v0/public.env"
STATE_ROOT="/var/lib/trader-assist-v0"
DATABASE_KEY="TRADER_ASSIST_V0_DATABASE_PATH"
assignment_count=0
database_path=""

test -r "$ENVIRONMENT_FILE" || { echo "SAFE_STOP: public.env is not readable" >&2; exit 1; }
while IFS= read -r line || test -n "$line"; do
  case "$line" in
    "$DATABASE_KEY"=*)
      assignment_count=$((assignment_count + 1))
      database_path="$(printf '%s\n' "$line" | cut -d= -f2-)"
      ;;
    *"$DATABASE_KEY"*) echo "SAFE_STOP: malformed database-path assignment" >&2; exit 1 ;;
  esac
done < "$ENVIRONMENT_FILE"

test "$assignment_count" = "1" || { echo "SAFE_STOP: expected exactly one database-path assignment" >&2; exit 1; }
case "$database_path" in
  /*) ;;
  *) echo "SAFE_STOP: database path is not absolute" >&2; exit 1 ;;
esac
if ! printf '%s\n' "$database_path" | LC_ALL=C grep -Eq '^[[:alnum:]./_-]+$'; then
  echo "SAFE_STOP: database-path assignment is quoted or unsupported" >&2
  exit 1
fi

state_root="$(realpath -e "$STATE_ROOT" 2>&1)" || { echo "SAFE_STOP: state root cannot canonicalize" >&2; exit 1; }
database_canonical="$(realpath -e "$database_path" 2>&1)" || { echo "SAFE_STOP: configured database file cannot canonicalize" >&2; exit 1; }
test -f "$database_canonical" || { echo "SAFE_STOP: configured database path is not a regular file" >&2; exit 1; }
relative_path="$(realpath --relative-to="$state_root" "$database_canonical" 2>&1)" || { echo "SAFE_STOP: cannot compare configured database path" >&2; exit 1; }
case "$relative_path" in
  ""|"."|".."|"../"*|/*) echo "SAFE_STOP: configured database is outside the approved state directory" >&2; exit 1 ;;
esac

sudo -u traderassist /opt/trader-assist-v0/venv/bin/python - "$database_canonical" <<'PY'
from pathlib import Path
import sqlite3
import sys

path = Path(sys.argv[1])
try:
    connection = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)
    try:
        rows = connection.execute("PRAGMA integrity_check").fetchall()
    finally:
        connection.close()
except Exception:
    raise SystemExit("SAFE_STOP: read-only integrity inspection failed")

if rows != [("ok",)]:
    raise SystemExit("SAFE_STOP: integrity_check did not return exactly one ok row")
print(f"PASS: database_path={path} integrity_check_rows={rows!r}")
PY
```

Record the exact `database_path` and complete successful result before and
after smoke. A failed fail-closed result is evidence requiring review; do not
claim SQLite corruption without that or other independent evidence.

## 21. READY Verification

The runtime is READY when the journal shows the session activation message:

```
session=<uuid> mode=RESTRICTED_PUBLIC_LIVE_SHADOW scope=ETH_ONLY
```

## 22. STOPPING Verification

The runtime is STOPPING when a SIGTERM is delivered and the journal shows the
shutdown sequence.

## 23. STOPPED Verification

For an operational final-state proof, use the complete self-contained
Section 15 block with `OPERATION="final-state"`. A display of inactive state
alone is not sufficient evidence.

## 24. Runtime Session Verification

- **Open session**: Journal contains `session=<uuid> mode=RESTRICTED_PUBLIC_LIVE_SHADOW scope=ETH_ONLY` without a subsequent shutdown message.
- **Closed session**: Journal contains the shutdown message after the session activation.

## 25. Rollback

Stop and disable the unit, then use the authoritative final-state proof before
removing the installed unit:

```bash
sudo systemctl stop trader-assist-v0-public.service
sudo systemctl disable trader-assist-v0-public.service
sudo rm -f /etc/trader-assist-v0/activation-permit

# Run the complete self-contained Section 15 block with:
# OPERATION="final-state"
# Proceed only when it prints PASS.

sudo rm /etc/systemd/system/trader-assist-v0-public.service
sudo systemctl daemon-reload
```

## 26. Uninstall

`OPERATION="final-state"` in Section 15 is the sole authoritative final
process proof. Run it after stop/disable and before removing the unit or
deleting deployment paths. Do not use `|| true` to turn inspection or
cleanup failures into a successful proof.

```bash
sudo systemctl stop trader-assist-v0-public.service
sudo systemctl disable trader-assist-v0-public.service
sudo rm -f /etc/trader-assist-v0/activation-permit

# Run the complete self-contained Section 15 block with:
# OPERATION="final-state"
# Proceed only when it prints PASS.

sudo rm /etc/systemd/system/trader-assist-v0-public.service
sudo systemctl daemon-reload
sudo rm -rf /etc/trader-assist-v0
sudo rm -rf /var/lib/trader-assist-v0
sudo rm -rf /opt/trader-assist-v0
sudo userdel traderassist || true
sudo groupdel traderassist || true
```

## 27. Proof That No Runtime Remains

Use only the complete self-contained Section 15 block with
`OPERATION="final-state"`. It fails closed unless the unit is loaded and
inspectable, exactly inactive and disabled with `MainPID=0`, no lifecycle
job, no populated surviving cgroup, no approved wrapper or Python runtime,
and no process owned by `traderassist`.

## 28. P4-A / P4-B Separation

P4-A (this package) is the local deployment package for a single supervised Linux
instance. P4-B is a separate, later-bounded workstream for continuous LIVE_SHADOW
deployment. P4-A does not authorize or configure P4-B.

## 29. P4-B / Continuous LIVE_SHADOW Separation

The continuous LIVE_SHADOW deployment (P4-B) is a separately authorized workstream.
P4-A prepares only the P4-A local deployment package. No P4-B configuration,
deployment, or runtime is included.

## 30. Future Smoke Plan

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
- record the original `MainPID` before the controlled stop;
- use Section 15 `OPERATION="controlled-restart"` exactly once; record its
  original PID/start-tick evidence and new MainPID evidence;
- record that the original identity was absent before the new systemd-only
  start, so no overlap was observed;
- run the configured-path, read-only Section 20 integrity procedure before
  and after smoke, recording its exact database path and complete result;
- finish with the final service stopped and final service disabled;
- use Section 15 `OPERATION="final-state"` to prove no runtime remains.

LOCAL/NON_AWS SMOKE IS NOT AUTHORIZED BY THIS WRITE LEASE.

## 31. Service Validation

Validate the systemd unit syntax:

```bash
sudo systemd-analyze verify /etc/systemd/system/trader-assist-v0-public.service
```

LOCAL/NON_AWS SMOKE IS NOT AUTHORIZED BY THIS WRITE LEASE.
