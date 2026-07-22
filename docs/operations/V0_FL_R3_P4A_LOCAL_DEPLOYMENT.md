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
runtime session. Set `OPERATION="credential-rollback"` in the complete
self-contained Section 15 block. That fail-fast mode stops and disables the
unit, requires the authoritative final-state proof, and only then deletes the
credential and activation permit. Do not substitute display-only process
commands for that proof.

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

After this systemd-only command returns, set `OPERATION="post-start"` in the
same complete Section 15 block. Its bounded 30-second stabilization waits for
the `Type=simple` wrapper-to-Python exec transition before the complete
post-start proof. This is bounded exec-transition evidence, not a universal
runtime-readiness guarantee.

## 14. Stop Procedure

```bash
sudo systemctl stop trader-assist-v0-public.service
```

## 15. P4B Single-Instance Authority

P4B has one live operational authority: systemd. The only supported P4B live activation path is:

`sudo systemctl start trader-assist-v0-public.service`

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
`final-state`, `credential-rollback`, `deployment-rollback`, or
`uninstall`. It is deliberately constrained to unified cgroup v2. Any
unsupported manager, cgroup, process, or configuration representation is a
`SAFE_STOP`. It does not start a runtime when `OPERATION="pre-start"` or
`OPERATION="final-state"`, and it never kills a process automatically.
Aliases and normal enablement links that resolve to the same literal authorized
`FragmentPath` are one unit identity, not duplicate runtime units.
Mark Ready or repository/CI evidence only establishes reviewed-artifact state;
supported-host operational evidence is a later, separately authorized stage
and does not grant P4B, AWS, runtime, or smoke authority.

```bash
set -eu
set -o pipefail

# This outer timeout deliberately does not use --foreground: GNU timeout then
# owns the proof command's process group.  Its 28-second TERM deadline plus
# its two-second forced-KILL grace is the complete, hard 30-second cap.
OPERATION="pre-start"
TIMEOUT_BIN="$(command -v timeout || true)"
safe_stop() { printf 'SAFE_STOP: %s\n' "$1" >&2; exit 1; }
test -n "$TIMEOUT_BIN" || safe_stop "supported host lacks timeout"
if ! "$TIMEOUT_BIN" --help 2>&1 | grep -F -- '--kill-after' >/dev/null; then
  safe_stop "timeout lacks required kill-after facility"
fi
sudo -v || safe_stop "cannot refresh sudo credentials before proof"

set +e
"$TIMEOUT_BIN" --signal=TERM --kill-after=2s 28s bash -s -- "$OPERATION" "$TIMEOUT_BIN" <<'P4B_PROOF'
set -euo pipefail

OPERATION="$1"
TIMEOUT_BIN="$2"
SERVICE="trader-assist-v0-public.service"
AUTHORIZED_FRAGMENT="/etc/systemd/system/trader-assist-v0-public.service"
APPROVED_WRAPPER="/opt/trader-assist-v0/scripts/p4a/run_restricted_public_runtime.sh"
APPROVED_PYTHON="/opt/trader-assist-v0/venv/bin/python"
APPROVED_ENTRYPOINT="/opt/trader-assist-v0/scripts/run_first_launch_public_runtime.py"
SYSTEM_PYTHON="/usr/bin/python3"
EXEC_PROPERTIES=(ExecCondition ExecStartPre ExecStart ExecStartPost ExecReload ExecStop ExecStopPost)
proof_started=$SECONDS
proof_deadline=$((proof_started + 28))
test -x "$SYSTEM_PYTHON" || safe_stop "supported host lacks the reviewed executable-property parser"

safe_stop() { printf 'SAFE_STOP: %s\n' "$1" >&2; exit 1; }

# Every command that can wait is given the absolute remaining budget.  The
# nested timeout is foreground-only so it cannot escape the outer process
# group; it reserves one second for its own KILL and never extends the cap.
remaining_seconds() {
  remaining=$((proof_deadline - SECONDS))
  test "$remaining" -gt 1 || safe_stop "hard 30-second transition-proof deadline exhausted"
  printf '%s' "$remaining"
}

bounded_capture() {
  destination="$1"; shift
  remaining="$(remaining_seconds)"
  command_seconds=$((remaining - 1))
  set +e
  output="$("$TIMEOUT_BIN" --foreground --signal=TERM --kill-after=1s "${command_seconds}s" "$@" 2>&1)"
  command_status=$?
  set -e
  case "$command_status" in
    0) ;;
    124|137) safe_stop "hard 30-second transition-proof timeout or forced kill" ;;
    *) safe_stop "bounded command failed or returned partial output" ;;
  esac
  printf -v "$destination" '%s' "$output"
}

bounded_run() {
  ignored=""
  bounded_capture ignored "$@"
  test -z "$ignored" || safe_stop "bounded command produced unexpected output"
}

bounded_best_effort() {
  remaining="$(remaining_seconds)"
  command_seconds=$((remaining - 1))
  set +e
  output="$("$TIMEOUT_BIN" --foreground --signal=TERM --kill-after=1s "${command_seconds}s" "$@" 2>&1)"
  command_status=$?
  set -e
  case "$command_status" in
    0) test -z "$output" || safe_stop "best-effort cleanup produced unexpected output"; return 0 ;;
    124|137) safe_stop "hard 30-second transition-proof timeout or forced kill" ;;
    *) return 1 ;;
  esac
}

bounded_capture_status() {
  destination="$1"; allowed_statuses="$2"; shift 2
  remaining="$(remaining_seconds)"
  command_seconds=$((remaining - 1))
  set +e
  output="$("$TIMEOUT_BIN" --foreground --signal=TERM --kill-after=1s "${command_seconds}s" "$@" 2>&1)"
  command_status=$?
  set -e
  case "$command_status" in 124|137) safe_stop "hard 30-second transition-proof timeout or forced kill" ;; esac
  case " $allowed_statuses " in *" $command_status "*) ;; *) safe_stop "bounded command returned an unexpected status" ;; esac
  printf -v "$destination" '%s' "$output"
  BOUNDED_STATUS="$command_status"
}

read_property() {
  property="$1"; unit="$2"
  bounded_capture value sudo -n systemctl show --property="$property" --value "$unit"
  case "$value" in *$'\n'*) safe_stop "manager returned multiline or partial $property" ;; esac
  printf '%s' "$value"
}

require_service_name() { case "$1" in *.service) ;; *) safe_stop "manager returned a non-service identity" ;; esac; }
require_scalar() { case "$1" in *$'\n'*|*$'\r'*) safe_stop "manager returned an ambiguous scalar" ;; esac; }
assert_nonzero_pid() { case "$1" in ''|0|*[!0-9]*) safe_stop "MainPID is not one nonzero numeric PID" ;; esac; }
assert_unified_cgroup_v2() { test -r /sys/fs/cgroup/cgroup.controllers || safe_stop "P4B verification requires unified cgroup v2"; }

# This is the explicitly supported, reviewed systemd serialization only:
# zero or more complete `{ path=... ; argv[]=... ; ignore_errors=... ;
# start_time=[...] ; stop_time=[...] ; pid=... ; code=... ; status=... }`
# records, separated solely by whitespace.  The parser rejects every other
# manager format, parses every record and every shlex argv field structurally,
# and emits no command arguments.
EXEC_PARSER='import os,re,shlex,sys
s=os.environ["EXEC_SERIALIZED"]
mode=os.environ["EXEC_MODE"]
prop=os.environ["EXEC_PROPERTY"]
wrapper=os.environ["APPROVED_WRAPPER"]
entry=os.environ["APPROVED_ENTRYPOINT"]
p=re.compile(r"\\{ path=([^ ;{}\\n]+) ; argv\\[\\]=([^{}\\n]*?) ; ignore_errors=(yes|no) ; start_time=\\[([^]\\n]*)\\] ; stop_time=\\[([^]\\n]*)\\] ; pid=([0-9]+) ; code=([^ ;{}\\n]+) ; status=([^ ;{}\\n]+) \\}")
records=[]; pos=0
while pos < len(s):
    while pos < len(s) and s[pos] in " \\t": pos += 1
    if pos == len(s): break
    m=p.match(s,pos)
    if not m: raise SystemExit(1)
    try: argv=shlex.split(m.group(2), posix=True, comments=False)
    except ValueError: raise SystemExit(1)
    if not argv: raise SystemExit(1)
    records.append((m.group(1),argv)); pos=m.end()
def trader_path(v): return v == wrapper or v == entry or v.startswith("/opt/trader-assist-v0/")
if mode == "authorized":
    if prop == "ExecStart":
        if len(records) != 1 or records[0][0] != wrapper or records[0][1] != [wrapper]: raise SystemExit(1)
    elif records: raise SystemExit(1)
else:
    for path,argv in records:
        if trader_path(path) or any(trader_path(arg) for arg in argv): raise SystemExit(1)
'

parse_exec_property() {
  serialized="$1"; mode="$2"; property="$3"
  bounded_capture parser_output env \
    EXEC_SERIALIZED="$serialized" EXEC_MODE="$mode" EXEC_PROPERTY="$property" \
    APPROVED_WRAPPER="$APPROVED_WRAPPER" APPROVED_ENTRYPOINT="$APPROVED_ENTRYPOINT" \
    "$SYSTEM_PYTHON" -c "$EXEC_PARSER"
  test -z "$parser_output" || safe_stop "executable-property parser emitted unexpected output"
}

inspect_exec_properties() {
  unit="$1"; mode="$2"
  for property in "${EXEC_PROPERTIES[@]}"; do
    serialized="$(read_property "$property" "$unit")"
    parse_exec_property "$serialized" "$mode" "$property"
  done
}

compare_alias_exec_properties() {
  alias_unit="$1"; canonical_unit="$2"; canonical_mode="$3"
  for property in "${EXEC_PROPERTIES[@]}"; do
    alias_value="$(read_property "$property" "$alias_unit")"
    canonical_value="$(read_property "$property" "$canonical_unit")"
    test -z "$alias_value" || test "$alias_value" = "$canonical_value" || safe_stop "alias executable property conflicts with canonical identity"
    test -z "$alias_value" || parse_exec_property "$alias_value" "$canonical_mode" "$property"
  done
}

assert_active_state() {
  expected="$1"; active="$(read_property ActiveState "$SERVICE")"
  test "$active" = "$expected" || safe_stop "ActiveState is not $expected"
  bounded_capture_status active_output '0 3' sudo -n systemctl is-active "$SERVICE"
  case "$expected:$BOUNDED_STATUS:$active_output" in active:0:active|inactive:3:inactive) ;; *) safe_stop "is-active representation conflicts with ActiveState" ;; esac
}

assert_no_lifecycle_job() {
  bounded_capture jobs sudo -n systemctl list-jobs --no-legend --no-pager
  job_count="$(printf '%s\n' "$jobs" | awk -v unit="$SERVICE" 'NF { if (NF < 2) exit 2; if ($2 == unit) n++ } END { print n+0 }')" || safe_stop "malformed lifecycle-job output"
  test "$job_count" = 0 || safe_stop "P4B lifecycle job is already in progress"
}

collect_manager_units() {
  bounded_capture loaded sudo -n systemctl list-units --type=service --all --no-legend --plain --no-pager
  bounded_capture files sudo -n systemctl list-unit-files --type=service --no-legend --no-pager
  manager_units="$(printf '%s\n%s\n' "$loaded" "$files" | awk 'NF { if ($1 !~ /^[A-Za-z0-9@_.-]+\\.service$/) exit 2; print $1 }' | LC_ALL=C sort -u)" || safe_stop "manager service enumeration is malformed"
  test -n "$manager_units" || safe_stop "manager-known service-unit list is empty"
}

assert_authorized_identity() {
  test "$(read_property LoadState "$SERVICE")" = loaded || safe_stop "authorized LoadState is not loaded"
  test "$(read_property FragmentPath "$SERVICE")" = "$AUTHORIZED_FRAGMENT" || safe_stop "authorized FragmentPath is not exact"
  test "$(read_property Transient "$SERVICE")" = no || safe_stop "authorized Transient is not no"
  test -z "$(read_property DropInPaths "$SERVICE")" || safe_stop "authorized DropInPaths is not empty"
  inspect_exec_properties "$SERVICE" authorized
}

assert_manager_known_executables() {
  collect_manager_units
  seen_canonical='|'
  while IFS= read -r candidate; do
    require_service_name "$candidate"
    current="$candidate"; aliases=''; depth=0
    while :; do
      depth=$((depth + 1)); test "$depth" -le 8 || safe_stop "alias following exceeded depth 8"
      require_service_name "$current"
      load="$(read_property LoadState "$current")"
      following="$(read_property Following "$current")"
      case "$load" in
        masked|not-found)
          test -z "$following" || safe_stop "non-loadable unit has Following identity"
          inspect_exec_properties "$current" other
          current=''; break
          ;;
        loaded|merged) ;;
        *) safe_stop "manager returned unsupported LoadState" ;;
      esac
      if test -z "$following"; then canonical="$current"; break; fi
      require_service_name "$following"
      case "|$aliases|" in *"|$following|"*) safe_stop "alias Following cycle detected" ;; esac
      aliases="${aliases}${aliases:+|}$current"; current="$following"
    done
    test -n "${current:-}" || continue
    canonical_load="$(read_property LoadState "$canonical")"
    test "$canonical_load" = loaded || safe_stop "canonical service is not loaded"
    canonical_transient="$(read_property Transient "$canonical")"
    case "$canonical_transient" in yes|no) ;; *) safe_stop "canonical Transient is unknown" ;; esac
    canonical_fragment="$(read_property FragmentPath "$canonical")"
    if test "$canonical" = "$SERVICE"; then
      test "$canonical_fragment" = "$AUTHORIZED_FRAGMENT" || safe_stop "authorized canonical FragmentPath conflicts"
    else
      case "$canonical_transient" in
        yes) : ;; # Empty FragmentPath is valid only after complete inspection.
        no) test -n "$canonical_fragment" || safe_stop "non-transient loaded unit has no reliable FragmentPath" ;;
      esac
    fi
    case "$seen_canonical" in *"|$canonical|"*) : ;; *)
      if test "$canonical" = "$SERVICE"; then canonical_mode=authorized; else canonical_mode=other; fi
      inspect_exec_properties "$canonical" "$canonical_mode"
      seen_canonical="${seen_canonical}${canonical}|"
      ;;
    esac
    IFS='|'; for alias_unit in $aliases; do
      test -n "$alias_unit" || continue
      compare_alias_exec_properties "$alias_unit" "$canonical" "$canonical_mode"
      alias_fragment="$(read_property FragmentPath "$alias_unit")"
      test -z "$alias_fragment" || test "$alias_fragment" = "$canonical_fragment" || safe_stop "alias FragmentPath conflicts with canonical identity"
    done; unset IFS
  done <<EOF
$manager_units
EOF
}

assert_effective_unit_identity() { assert_authorized_identity; assert_manager_known_executables; }

line_count() { printf '%s\n' "$1" | awk 'NF { n++ } END { print n+0 }'; }
sole_pid() { printf '%s\n' "$1" | awk 'NF { print; exit }'; }
collect_pids() {
  pattern="$1"; destination="$2"
  set +e
  remaining="$(remaining_seconds)"; command_seconds=$((remaining - 1))
  output="$("$TIMEOUT_BIN" --foreground --signal=TERM --kill-after=1s "${command_seconds}s" sudo -n pgrep -f "$pattern" 2>&1)"; status=$?
  set -e
  case "$status" in 0) ;; 1) output='' ;; 124|137) safe_stop "hard 30-second transition-proof timeout or forced kill" ;; *) safe_stop "cannot enumerate runtime processes" ;; esac
  printf -v "$destination" '%s' "$output"
}
collect_approved_runtime_pids() { collect_pids '[r]un_restricted_public_runtime.sh' WRAPPER_PIDS; collect_pids '[r]un_first_launch_public_runtime.py' PYTHON_PIDS; }
collect_dedicated_user_pids() {
  bounded_capture DEDICATED_UID id -u traderassist; case "$DEDICATED_UID" in ''|*[!0-9]*) safe_stop "dedicated traderassist UID is invalid" ;; esac
  set +e
  remaining="$(remaining_seconds)"; command_seconds=$((remaining - 1)); output="$("$TIMEOUT_BIN" --foreground --signal=TERM --kill-after=1s "${command_seconds}s" sudo -n pgrep -u "$DEDICATED_UID" 2>&1)"; status=$?
  set -e
  case "$status" in 0) ;; 1) output='' ;; *) safe_stop "cannot enumerate traderassist processes" ;; esac
  DEDICATED_PIDS="$output"
}

validate_cgroup_path() { case "$1" in /*) ;; *) safe_stop "ControlGroup is not absolute" ;; esac; case "$1" in *..*|*'//'*) safe_stop "ControlGroup is ambiguous" ;; esac; }
assert_cgroup_absent_or_empty() {
  path="$1"; test -n "$path" || return 0; assert_unified_cgroup_v2; validate_cgroup_path "$path"; directory="/sys/fs/cgroup$path"
  if test -e "$directory"; then test -d "$directory" || safe_stop "ControlGroup is not a directory"; bounded_capture cgroup_pids sudo -n cat "$directory/cgroup.procs"; test -z "$cgroup_pids" || safe_stop "service cgroup is populated"; fi
}
assert_inactive_service_cgroup() { assert_unified_cgroup_v2; inactive_cgroup="$(read_property ControlGroup "$SERVICE")"; test -z "$inactive_cgroup" || assert_cgroup_absent_or_empty "$inactive_cgroup"; }
assert_active_service_cgroup() { assert_unified_cgroup_v2; SERVICE_CGROUP="$(read_property ControlGroup "$SERVICE")"; test -n "$SERVICE_CGROUP" || safe_stop "active service has no ControlGroup"; validate_cgroup_path "$SERVICE_CGROUP"; SERVICE_CGROUP_DIR="/sys/fs/cgroup$SERVICE_CGROUP"; }

derive_runtime_configuration() {
  bounded_capture config_values sudo -n bash -c '
set -eu
f=/etc/trader-assist-v0/public.env
test -r "$f" || exit 1
database_count=0; risk_count=0; webhook_count=0; acknowledgement_count=0; session_count=0
while IFS= read -r line || test -n "$line"; do
  case "$line" in ""|\#*) continue ;; esac
  case "$line" in *=*) key=${line%%=*}; value=${line#*=} ;; *) exit 1 ;; esac
  case "$key" in
    TRADER_ASSIST_V0_DATABASE_PATH) database_count=$((database_count + 1)); database_path=$value ;;
    TRADER_ASSIST_V0_RISK_CONFIGURATION_PATH) risk_count=$((risk_count + 1)); risk_path=$value ;;
    TRADER_ASSIST_V0_WEBHOOK_TIMEOUT_SECONDS) webhook_count=$((webhook_count + 1)); webhook_timeout=$value ;;
    TRADER_ASSIST_V0_ACKNOWLEDGEMENT_TIMEOUT_SECONDS) acknowledgement_count=$((acknowledgement_count + 1)); acknowledgement_timeout=$value ;;
    TRADER_ASSIST_V0_SESSION_TIMEOUT_SECONDS) session_count=$((session_count + 1)); session_timeout=$value ;;
    *) continue ;;
  esac
  case "$value" in *["'"'"'\\\\[:space:]]*) exit 1 ;; esac
done < "$f"
test "$database_count" = 1 || exit 1; test "$risk_count" = 1 || exit 1
for count in "$webhook_count" "$acknowledgement_count" "$session_count"; do case "$count" in 0|1) ;; *) exit 1 ;; esac; done
printf "%s\\n%s\\n%s\\n%s\\n%s" "$database_path" "$risk_path" "${webhook_timeout:-10}" "${acknowledgement_timeout:-30}" "${session_timeout:-21600}"
'
  mapfile -t config_array <<<"$config_values"; test "${#config_array[@]}" = 5 || safe_stop "configuration parser returned partial output"
  DATABASE_PATH="${config_array[0]}"; RISK_PATH="${config_array[1]}"; WEBHOOK_TIMEOUT="${config_array[2]}"; ACK_TIMEOUT="${config_array[3]}"; SESSION_TIMEOUT="${config_array[4]}"
  case "$DATABASE_PATH" in /var/lib/trader-assist-v0/*) ;; *) safe_stop "configured database path is outside approved state root" ;; esac
  case "$RISK_PATH" in /etc/trader-assist-v0/*) ;; *) safe_stop "configured risk path is outside approved configuration root" ;; esac
  for value in "$WEBHOOK_TIMEOUT" "$ACK_TIMEOUT" "$SESSION_TIMEOUT"; do case "$value" in ''|*[!0-9]*) safe_stop "configured timeout is invalid" ;; esac; done
}

read_credential_directory() {
  pid="$1"
  bounded_capture CREDENTIALS_DIRECTORY sudo -n bash -c '
count=0; value=""
while IFS= read -r -d "" entry; do case "$entry" in CREDENTIALS_DIRECTORY=*) count=$((count+1)); value=${entry#CREDENTIALS_DIRECTORY=} ;; esac; done < "/proc/$1/environ"
test "$count" = 1 || exit 1
case "$value" in /*) ;; *) exit 1 ;; esac
case "$value" in *$"\n"*|*"//"*|*".."*) exit 1 ;; esac
printf %s "$value"
' bash "$pid"
  case "$CREDENTIALS_DIRECTORY" in /*) ;; *) safe_stop "credential directory representation is invalid" ;; esac
}

# This one shared verifier is used by stabilization and the final assertion.
# It reads the NUL-delimited array without printing it, and requires precisely
# 17 positional entries (0 through 16), including the manager credential path.
assert_complete_runtime_argv() {
  pid="$1"
  bounded_capture approved_python_exe sudo -n readlink -f "$APPROVED_PYTHON"
  bounded_capture runtime_python_exe sudo -n readlink -f "/proc/$pid/exe"
  test "$runtime_python_exe" = "$approved_python_exe" || return 1
  derive_runtime_configuration
  read_credential_directory "$pid"
  bounded_capture argv_lines sudo -n bash -c 'mapfile -d "" -t argv < "/proc/$1/cmdline"; printf "%s\\n" "${#argv[@]}"; printf "%s\\n" "${argv[@]}"' bash "$pid"
  mapfile -t argv <<<"$argv_lines"; test "${#argv[@]}" = 18 || return 1; test "${argv[0]}" = 17 || return 1
  expected=("$APPROVED_PYTHON" "$APPROVED_ENTRYPOINT" --enable-restricted-public-runtime --mode RESTRICTED_PUBLIC_LIVE_SHADOW --database-path "$DATABASE_PATH" --risk-configuration-path "$RISK_PATH" --notification-credential-file "$CREDENTIALS_DIRECTORY/notification.json" --webhook-timeout-seconds "$WEBHOOK_TIMEOUT" --acknowledgement-timeout-seconds "$ACK_TIMEOUT" --session-timeout-seconds "$SESSION_TIMEOUT")
  for index in "${!expected[@]}"; do test "${argv[$((index + 1))]}" = "${expected[$index]}" || return 1; done
}

assert_pre_start() {
  assert_effective_unit_identity; assert_active_state inactive; test "$(read_property MainPID "$SERVICE")" = 0 || safe_stop "MainPID is not 0 before start"; assert_no_lifecycle_job
  collect_dedicated_user_pids; test -z "$DEDICATED_PIDS" || safe_stop "traderassist owns unexplained process(es)"; collect_approved_runtime_pids; test -z "$WRAPPER_PIDS" || safe_stop "wrapper exists before start"; test -z "$PYTHON_PIDS" || safe_stop "Python runtime exists before start"; assert_inactive_service_cgroup
}

stabilize_post_start() {
  while test "$SECONDS" -lt "$proof_deadline"; do
    active="$(read_property ActiveState "$SERVICE")"; sub="$(read_property SubState "$SERVICE")"
    case "$active:$sub" in active:running) ;; failed:*|inactive:*|*:failed|*:dead) safe_stop "service failed during wrapper-to-Python transition" ;; *) bounded_run sleep 1; continue ;; esac
    pid="$(read_property MainPID "$SERVICE")"; case "$pid" in 0) bounded_run sleep 1; continue ;; *[!0-9]*|'') safe_stop "MainPID is malformed during transition" ;; esac
    test -d "/proc/$pid" || { bounded_run sleep 1; continue; }
    if ! assert_complete_runtime_argv "$pid"; then bounded_run sleep 1; continue; fi
    collect_approved_runtime_pids; test -z "$WRAPPER_PIDS" || { bounded_run sleep 1; continue; }; return 0
  done
  safe_stop "hard 30-second transition proof timed out"
}

assert_post_start() {
  assert_effective_unit_identity; assert_active_state active; MAIN_PID="$(read_property MainPID "$SERVICE")"; assert_nonzero_pid "$MAIN_PID"; test -d "/proc/$MAIN_PID" || safe_stop "MainPID does not exist"
  assert_complete_runtime_argv "$MAIN_PID" || safe_stop "MainPID does not satisfy the exact 17-entry argv contract"
  collect_dedicated_user_pids; test "$(line_count "$DEDICATED_PIDS")" = 1 || safe_stop "expected exactly one traderassist process"; test "$(sole_pid "$DEDICATED_PIDS")" = "$MAIN_PID" || safe_stop "dedicated PID is not MainPID"
  assert_active_service_cgroup; test -d "$SERVICE_CGROUP_DIR" || safe_stop "service cgroup does not exist"; bounded_capture runtime_cgroup sudo -n cat "/proc/$MAIN_PID/cgroup"; test "$runtime_cgroup" = "0::$SERVICE_CGROUP" || safe_stop "MainPID cgroup differs"; bounded_capture cgroup_pids sudo -n cat "$SERVICE_CGROUP_DIR/cgroup.procs"; test "$cgroup_pids" = "$MAIN_PID" || safe_stop "cgroup does not contain exactly MainPID"
  collect_approved_runtime_pids; test -z "$WRAPPER_PIDS" || safe_stop "wrapper remains after exec"; test "$(line_count "$PYTHON_PIDS")" = 1 || safe_stop "expected exactly one Python runtime"; test "$(sole_pid "$PYTHON_PIDS")" = "$MAIN_PID" || safe_stop "Python PID is not MainPID"
}

assert_final_state() {
  assert_effective_unit_identity; assert_active_state inactive; test "$(read_property MainPID "$SERVICE")" = 0 || safe_stop "MainPID is not 0 in final state"; test "$(read_property UnitFileState "$SERVICE")" = disabled || safe_stop "UnitFileState is not disabled"; assert_no_lifecycle_job; assert_inactive_service_cgroup; collect_approved_runtime_pids; test -z "$WRAPPER_PIDS$PYTHON_PIDS" || safe_stop "runtime remains in final state"; collect_dedicated_user_pids; test -z "$DEDICATED_PIDS" || safe_stop "traderassist process remains in final state"
}

stop_disable_and_verify_final_state() { bounded_run sudo -n systemctl stop "$SERVICE"; bounded_run sudo -n systemctl disable "$SERVICE"; assert_final_state; }
credential_rollback() { stop_disable_and_verify_final_state; bounded_run sudo -n rm -f /etc/trader-assist-v0/credentials/notification.json; bounded_run sudo -n rm -f /etc/trader-assist-v0/activation-permit; printf 'PASS: credential rollback removed credential and activation permit after final-state proof\n'; }
deployment_rollback() { stop_disable_and_verify_final_state; bounded_run sudo -n rm -f /etc/trader-assist-v0/activation-permit; bounded_run sudo -n rm /etc/systemd/system/trader-assist-v0-public.service; bounded_run sudo -n systemctl daemon-reload; printf 'PASS: deployment rollback removed permit and unit after final-state proof\n'; }
uninstall_runtime() { stop_disable_and_verify_final_state; bounded_run sudo -n rm -f /etc/trader-assist-v0/credentials/notification.json; bounded_run sudo -n rm -f /etc/trader-assist-v0/activation-permit; bounded_run sudo -n rm /etc/systemd/system/trader-assist-v0-public.service; bounded_run sudo -n systemctl daemon-reload; bounded_run sudo -n rm -rf /etc/trader-assist-v0; bounded_run sudo -n rm -rf /var/lib/trader-assist-v0; bounded_run sudo -n rm -rf /opt/trader-assist-v0; if ! bounded_best_effort sudo -n userdel traderassist; then printf 'WARNING: traderassist user cleanup failed after successful proof-bearing removal\n' >&2; fi; if ! bounded_best_effort sudo -n groupdel traderassist; then printf 'WARNING: traderassist group cleanup failed after successful proof-bearing removal\n' >&2; fi; printf 'PASS: uninstall removed unit and deployment paths after final-state proof; user/group cleanup is best effort only\n'; }
controlled_restart() { assert_post_start; ORIGINAL_PID="$MAIN_PID"; ORIGINAL_CONTROL_GROUP="$SERVICE_CGROUP"; bounded_capture ORIGINAL_START_TICKS sudo -n awk '{ print $22 }' "/proc/$ORIGINAL_PID/stat"; case "$ORIGINAL_START_TICKS" in ''|*[!0-9]*) safe_stop "original start ticks are invalid" ;; esac; printf 'EVIDENCE: original_pid=%s original_start_ticks=%s\n' "$ORIGINAL_PID" "$ORIGINAL_START_TICKS"; bounded_run sudo -n systemctl stop "$SERVICE"; test ! -e "/proc/$ORIGINAL_PID" || safe_stop "original PID remains after stop"; assert_cgroup_absent_or_empty "$ORIGINAL_CONTROL_GROUP"; assert_pre_start; bounded_run sudo -n systemctl start "$SERVICE"; stabilize_post_start; assert_post_start; test "$MAIN_PID" != "$ORIGINAL_PID" || safe_stop "new MainPID equals original PID"; printf 'PASS: controlled restart recorded new_pid=%s; original identity was absent before start, so no overlap was observed\n' "$MAIN_PID"; }

case "$OPERATION" in
  pre-start) assert_pre_start; printf 'PASS: effective unit verified; inactive; MainPID=0; no job, cgroup, runtime, or traderassist process\n' ;;
  post-start) stabilize_post_start; assert_post_start; printf 'PASS: bounded wrapper-to-Python transition and exact 17-entry argv identity verified\n' ;;
  controlled-restart) controlled_restart ;;
  final-state) assert_final_state; printf 'PASS: loaded disabled unit is inactive with MainPID=0 and no cgroup, runtime, or traderassist process\n' ;;
  credential-rollback) credential_rollback ;;
  deployment-rollback) deployment_rollback ;;
  uninstall) uninstall_runtime ;;
  *) safe_stop "OPERATION must select a supported verification or teardown mode" ;;
esac
P4B_PROOF
proof_status=$?
set -e
case "$proof_status" in
  0) ;;
  124|137) safe_stop "hard 30-second transition-proof timeout or forced kill" ;;
  *) safe_stop "bounded proof failed" ;;
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

This proof is restricted to supported systemd Linux hosts with unified cgroup
v2 and the explicitly reviewed manager and executable-property serialization
used by the block. Unknown fields, a different serialization, truncated or
partial manager output, malformed command records, or any ambiguous result
requires `SAFE_STOP`. In particular, an unrelated transient unit is not
exempt: it can pass only after complete inspection of all seven executable
properties and every command record. The proof is bounded operational evidence,
not a mathematical singleton guarantee. It does not universally detect
malicious root activity, copied or disguised implementations, unrelated UIDs,
every PID reuse, every race, or arbitrary alternate implementations. It adds
no wrapper lock, Python lock, PID-file authority, or Unix-socket authority.

The transition check proves only the approved wrapper-to-Python exec transition
and exact process identity; it is not application `READY`. It may inspect the
credential-path identity but never prints credential content, authorization
values, the complete environment, or the complete argv. Static CI does not
exercise a real systemd manager, privileged boundaries, cgroup allocation,
transient services, live exec transition, restart, or timeout behavior.
Supported-host evidence remains a later separately authorized gate: this
runbook grants no AWS, deployment, runtime, or smoke authority.

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

Run this bounded parser and evidence check in an explicit privileged shell.
The production `public.env` is root-owned and mode 0600, so merely adding
`sudo` to an outer readability test would be insufficient: shell redirection
and parsing must also occur inside the elevated process. The parser treats the
file only as inert text; it never sources or executes it, and it never prints
unrelated environment lines or secret values.

Set `DATABASE_EVIDENCE` to exactly one supported phase:

- `existing-before-smoke`: an existing configured database must pass the
  read-only integrity check before separately authorized smoke.
- `fresh-pre-start`: the configured path must be absent and its existing
  canonical parent must be inside the approved state directory. Do not create
  an alternate or unreviewed database manually.
- `fresh-post-creation`: only after a separately authorized systemd-only
  runtime has created the exact configured database, run the first read-only
  integrity check before controlled restart or smoke acceptance.
- `final-post-smoke`: run the final read-only integrity check after smoke
  and final stop.

The fresh path records pre-start absence separately from first-created-database
and final post-smoke integrity evidence. This Writer task does not authorize or
execute any start, creation, or smoke action.

```bash
set -eu
set -o pipefail

DATABASE_EVIDENCE="existing-before-smoke"
sudo /usr/bin/env bash -s -- "$DATABASE_EVIDENCE" <<'ROOT_EVIDENCE'
set -euo pipefail

safe_stop() {
  printf 'SAFE_STOP: %s\n' "$1" >&2
  exit 1
}

evidence_phase="$1"
environment_file="/etc/trader-assist-v0/public.env"
state_root="/var/lib/trader-assist-v0"
database_key="TRADER_ASSIST_V0_DATABASE_PATH"
assignment_count=0
database_path=""

test -r "$environment_file" || safe_stop "public.env is not readable by the privileged parser"
while IFS= read -r line || test -n "$line"; do
  case "$line" in
    "$database_key"=*)
      assignment_count=$((assignment_count + 1))
      database_path="$(printf '%s\n' "$line" | cut -d= -f2-)"
      ;;
    *"$database_key"*) safe_stop "malformed database-path assignment" ;;
  esac
done < "$environment_file"

test "$assignment_count" = "1" || safe_stop "expected exactly one database-path assignment"
case "$database_path" in /*) ;; *) safe_stop "database path is not absolute" ;; esac
if ! printf '%s\n' "$database_path" | LC_ALL=C grep -Eq '^[[:alnum:]./_-]+$'; then
  safe_stop "database-path assignment is quoted or unsupported"
fi
state_root_canonical="$(realpath -e "$state_root" 2>&1)" || safe_stop "state root cannot canonicalize"

assert_inside_state_root() {
  candidate_path="$1"
  containment_mode="$2"
  relative_path="$(realpath --relative-to="$state_root_canonical" "$candidate_path" 2>&1)" || safe_stop "cannot compare configured database path"
  case "$relative_path" in
    ""|".."|"../"*|/*) safe_stop "configured database is outside the approved state directory" ;;
    ".") test "$containment_mode" = "parent" || safe_stop "configured database is outside the approved state directory" ;;
  esac
}

run_read_only_integrity() {
  database_canonical="$1"
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
}

case "$evidence_phase" in
  existing-before-smoke|fresh-post-creation|final-post-smoke)
    database_canonical="$(realpath -e "$database_path" 2>&1)" || safe_stop "configured database file cannot canonicalize"
    test -f "$database_canonical" || safe_stop "configured database path is not a regular file"
    assert_inside_state_root "$database_canonical" file
    run_read_only_integrity "$database_canonical"
    ;;
  fresh-pre-start)
    test ! -L "$database_path" || safe_stop "fresh configured database path must not be a symlink"
    test ! -e "$database_path" || safe_stop "fresh configured database path is already present"
    database_parent="$(dirname "$database_path")"
    database_parent_canonical="$(realpath -e "$database_parent" 2>&1)" || safe_stop "fresh database parent cannot canonicalize"
    test -d "$database_parent_canonical" || safe_stop "fresh database parent is not a directory"
    assert_inside_state_root "$database_parent_canonical" parent
    database_name="$(basename "$database_path")"
    case "$database_name" in ""|"."|"..") safe_stop "fresh database path has an invalid filename" ;; esac
    printf 'PASS: fresh_database_path_absent=%s parent=%s\n' "$database_path" "$database_parent_canonical"
    ;;
  *) safe_stop "DATABASE_EVIDENCE must select a supported evidence phase" ;;
esac
ROOT_EVIDENCE
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

Set `OPERATION="deployment-rollback"` in the complete self-contained
Section 15 block. That independently executable, fail-fast mode requires
successful stop and disable, passes final-state proof before deleting the
activation permit or unit file, and reports any later cleanup failure.

## 26. Uninstall

Set `OPERATION="uninstall"` in the complete self-contained Section 15 block.
That independently executable, fail-fast mode proves final state before
deleting credentials, permit, unit, or deployment paths. User and group
deletion are only best-effort cleanup after those proof-bearing removals
succeed; their failure is reported as a warning, never as proof-bearing
success.

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
- for an existing database, run Section 20
  `DATABASE_EVIDENCE="existing-before-smoke"` before smoke;
- for a fresh database, record Section 20
  `DATABASE_EVIDENCE="fresh-pre-start"` before the separately authorized
  systemd-only first start, then record
  `DATABASE_EVIDENCE="fresh-post-creation"` immediately after creation and
  before controlled restart or smoke acceptance;
- in either path, record Section 20
  `DATABASE_EVIDENCE="final-post-smoke"` after smoke/final stop, including
  its exact database path and complete result;
- finish with the final service stopped and final service disabled;
- use Section 15 `OPERATION="final-state"` to prove no runtime remains.

LOCAL/NON_AWS SMOKE IS NOT AUTHORIZED BY THIS WRITE LEASE.

## 31. Service Validation

Validate the systemd unit syntax:

```bash
sudo systemd-analyze verify /etc/systemd/system/trader-assist-v0-public.service
```

LOCAL/NON_AWS SMOKE IS NOT AUTHORIZED BY THIS WRITE LEASE.
