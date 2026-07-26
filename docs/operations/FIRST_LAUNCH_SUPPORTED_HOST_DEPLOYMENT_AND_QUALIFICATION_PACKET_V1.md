# First Launch Supported-Host Deployment and Qualification Packet V1

## 1. Purpose and authority

This packet is a plan and command packet only for one controlled First Launch
host. It does not authorize any command in this document to be run against a real host.

```text
PLANNING_AUTHORIZED
HOST_ACCESS_NOT_AUTHORIZED
DEPLOYMENT_NOT_AUTHORIZED
RUNTIME_AND_SMOKE_NOT_AUTHORIZED
```

Each later phase needs its own explicit authorization. Completing an earlier
phase never activates a later phase.

## 2. Supported-host profile

The one supported profile is a controlled Ubuntu, or equivalent
systemd-based Linux, host with all of the following:

- a dedicated `traderassist` user;
- Python 3.12 or newer and Git;
- systemd and `systemd-analyze`;
- sufficient disk and memory for the existing one-process runtime;
- outbound HTTPS/WebSocket connectivity only to the approved public-data and
  notification destinations, with no inbound application port requirement;
- no account or exchange credential;
- one runtime process, one SQLite database, and ETH only.

No hostname, address, cloud account, instance identifier, region, or
credential is assumed by this packet. A candidate host is not a supported
host until the separately authorized read-only preflight passes.

## 3. Separate authority phases

| Phase | Name | Required authority | Result |
| --- | --- | --- | --- |
| 0 | `READ_ONLY_HOST_PREFLIGHT` | Separate host-access authorization | Establish only whether the candidate matches the profile. |
| 1 | `DEPLOYMENT` | Separate deployment authorization | Perform the existing P4A deployment runbook at one authorized SHA. |
| 2 | `RUNTIME_AND_QUALIFICATION` | Separate runtime and supervised-smoke authorization | Run the bounded qualification attempt. |
| 3 | `ACCEPTED_REAL_OPERATION` | Separate final user acceptance | Decide whether real operation may begin. |

No row grants authority for the next row. A failed, incomplete, stale, or
unreconciled result permits no new risk.

## 4. PHASE 0 — READ_ONLY_HOST_PREFLIGHT

Run this one self-contained procedure only after separate host-access
authorization. It reads the specified host facts and paths only; it does not
install, mutate, start, stop, access credentials, print configuration, or
inspect PID 1. Its failure and unknown flags are monotonic, so a later success
cannot overwrite an earlier failure. It prints exactly one final classification.

<!-- PHASE0_HOST_PREFLIGHT_BEGIN -->
```bash
set -u

SERVICE_UNIT="/etc/systemd/system/trader-assist-v0-public.service"
FAIL=0
UNKNOWN=0

mark_fail() { FAIL=1; }
mark_unknown() { UNKNOWN=1; }

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    printf '%s_MISSING\n' "$2"
    mark_fail
    return
  fi
  printf '%s_PRESENT\n' "$2"
}

require_command python3 PYTHON3
APPROVED_PYTHON_BIN="$(command -v python3 || true)"
if test -z "$APPROVED_PYTHON_BIN"; then
  printf 'APPROVED_PYTHON_BIN=UNAVAILABLE\n'
  printf 'APPROVED_PYTHON_VERSION=UNAVAILABLE\n'
  mark_fail
elif test "${APPROVED_PYTHON_BIN#/}" = "$APPROVED_PYTHON_BIN" || \
  test ! -x "$APPROVED_PYTHON_BIN"; then
  printf 'APPROVED_PYTHON_BIN=INVALID\n'
  printf 'APPROVED_PYTHON_VERSION=UNAVAILABLE\n'
  mark_fail
else
  printf 'APPROVED_PYTHON_BIN=%s\n' "$APPROVED_PYTHON_BIN"
  if APPROVED_PYTHON_VERSION="$("$APPROVED_PYTHON_BIN" -c \
    'import platform; print(platform.python_version())' 2>/dev/null)"; then
    printf 'APPROVED_PYTHON_VERSION=%s\n' "$APPROVED_PYTHON_VERSION"
  else
    printf 'APPROVED_PYTHON_VERSION=UNAVAILABLE\n'
    mark_fail
  fi
  if ! "$APPROVED_PYTHON_BIN" -c \
    'import sys; raise SystemExit(0 if sys.version_info >= (3, 12) else 1)' \
    >/dev/null 2>&1; then
    mark_fail
  fi
fi

require_command git GIT
if ! GIT_VERSION="$(git --version 2>/dev/null)"; then
  printf 'GIT_RESULT=FAIL\n'
  mark_fail
else
  printf 'GIT_VERSION=%s\n' "$GIT_VERSION"
  printf 'GIT_RESULT=PASS\n'
fi

require_command systemctl SYSTEMCTL
if ! SYSTEMD_VERSION="$(systemctl --version 2>/dev/null)"; then
  printf 'SYSTEMD_VERSION=UNAVAILABLE\n'
  mark_fail
else
  printf 'SYSTEMD_VERSION=%s\n' "$SYSTEMD_VERSION"
fi

require_command systemd-analyze SYSTEMD_ANALYZE
if ! systemd-analyze --version >/dev/null 2>&1; then
  printf 'SYSTEMD_ANALYZE_RESULT=FAIL\n'
  mark_fail
else
  printf 'SYSTEMD_ANALYZE_RESULT=PASS\n'
fi

if OS_VERSION="$(grep '^PRETTY_NAME=' /etc/os-release 2>/dev/null)"; then
  printf 'OS_VERSION=%s\n' "$OS_VERSION"
else
  printf 'OS_VERSION=UNAVAILABLE\n'
  mark_unknown
fi
if ARCHITECTURE="$(uname -m 2>/dev/null)"; then
  printf 'ARCHITECTURE=%s\n' "$ARCHITECTURE"
else
  printf 'ARCHITECTURE=UNAVAILABLE\n'
  mark_unknown
fi
if KERNEL_VERSION="$(uname -r 2>/dev/null)"; then
  printf 'KERNEL_VERSION=%s\n' "$KERNEL_VERSION"
else
  printf 'KERNEL_VERSION=UNAVAILABLE\n'
  mark_unknown
fi

if DISK_CAPACITY_RESULT="$(df -Pk / 2>/dev/null)" && test -n "$DISK_CAPACITY_RESULT"; then
  printf 'DISK_CAPACITY_RESULT=%s\n' "$DISK_CAPACITY_RESULT"
else
  printf 'DISK_CAPACITY_RESULT=UNRESOLVED\n'
  mark_unknown
fi
if MEMORY_CAPACITY_RESULT="$(grep '^MemAvailable:' /proc/meminfo 2>/dev/null)" && \
  test -n "$MEMORY_CAPACITY_RESULT"; then
  printf 'MEMORY_CAPACITY_RESULT=%s\n' "$MEMORY_CAPACITY_RESULT"
else
  printf 'MEMORY_CAPACITY_RESULT=UNRESOLVED\n'
  mark_unknown
fi

for path in \
  /opt/trader-assist-v0 \
  /etc/trader-assist-v0 \
  /var/lib/trader-assist-v0 \
  "$SERVICE_UNIT"; do
  if test -e "$path"; then
    printf 'PRESENT %s\n' "$path"
  else
    printf 'ABSENT %s\n' "$path"
  fi
done

if test -e "$SERVICE_UNIT"; then
  if systemd-analyze verify "$SERVICE_UNIT" >/dev/null 2>&1; then
    printf 'UNIT_VERIFY_RESULT=PASS\n'
  else
    printf 'UNIT_VERIFY_RESULT=FAIL\n'
    mark_fail
  fi
else
  printf 'UNIT_VERIFY_RESULT=NOT_PRESENT_PRE_DEPLOYMENT\n'
fi

if test "$FAIL" -ne 0; then
  printf 'HOST_PROFILE_FAIL\n'
  exit 1
elif test "$UNKNOWN" -ne 0; then
  printf 'HOST_PROFILE_UNKNOWN\n'
  exit 2
else
  printf 'HOST_PROFILE_PASS\n'
  exit 0
fi
```
<!-- PHASE0_HOST_PREFLIGHT_END -->

`HOST_PROFILE_PASS` has exit code 0, `HOST_PROFILE_FAIL` has exit code 1, and
`HOST_PROFILE_UNKNOWN` has exit code 2. Missing `python3`, Python below 3.12,
missing Git, missing `systemctl`, missing `systemd-analyze`, or failed
verification of an already present unit is a fail-closed `HOST_PROFILE_FAIL`.
Unresolved disk or memory collection is `HOST_PROFILE_UNKNOWN`; it never
permits deployment. The observed nonzero capacity values are evidence only;
the separately authorized deployment decision confirms they remain sufficient
for its selected SHA.

`APPROVED_PYTHON_BIN` must be an absolute executable path and is the exact
interpreter approved during preflight. Record it, `APPROVED_PYTHON_VERSION`,
and every result in the qualification evidence. The later deployment
authorization must explicitly supply that exact absolute path. A different
interpreter path requires a new preflight; it must never be silently
substituted.

## 5. PHASE 1 — DEPLOYMENT

After separate deployment authorization, use the existing
[P4A local deployment runbook](V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md). This packet
does not duplicate or broaden it. The authorization must name one full
40-character deployment SHA after this packet has merged; it must not use this
planning branch SHA.

The authorized deployment must use a detached checkout with exact `HEAD`
equality and a clean repository, install only the hashed runtime lock without
an editable install, use the exact authorization-supplied
`APPROVED_PYTHON_BIN` path recorded in preflight, retain the root-owned source installation and existing
`LoadCredential` path, and preserve the default-off activation permit. Verify
the service unit before activation. Credentials must not enter Git,
environment variables, process argv, journals, or qualification evidence.

## 6. Exact operator commands and bounded recovery

The primary status command is:

```bash
sudo /opt/trader-assist-v0/bin/ta-status
```

| Classification | Exit code | Operator meaning |
| --- | ---: | --- |
| `READY` | 0 | Signals may be considered. |
| `NOT_READY` | 1 | Ignore system signals. |
| `STATUS_UNKNOWN` | 2 | Ignore system signals and investigate if persistent. |

The only supported recovery sequence is:

1. Rerun `sudo /opt/trader-assist-v0/bin/ta-status`.
2. Perform exactly one controlled restart:

   ```bash
   sudo systemctl stop trader-assist-v0-public.service
   sudo systemctl start trader-assist-v0-public.service
   ```

3. Rerun `sudo /opt/trader-assist-v0/bin/ta-status`.
4. If it remains non-`READY`, run one bounded diagnostic command:

   ```bash
   sudo journalctl -u trader-assist-v0-public.service --since "30 minutes ago" --no-pager
   ```

5. Stop and escalate for targeted diagnosis.

Do not add a stop feature. Manual `systemctl stop` remains available only for
the controlled restart, qualification closeout, and rollback. Mac Terminal
aliases and remote shortcuts are deferred to the later operator-command
finalization gate.

## 7. PHASE 2 — RUNTIME_AND_QUALIFICATION

Run this procedure only after separate runtime and supervised-smoke
authorization. It is manual, single-host, single-process, and ETH-only. There
is no automatic systemd service restart, automatic host repair, automatic
deployment, or unbounded autonomous recovery. The existing bounded
public-transport reconnect and durable-notification retry remain; exactly one
operator-controlled service restart is supported.

1. Prove the service is default-off.
2. Validate the installed unit with `systemd-analyze verify`.
3. Verify the exact deployed SHA and clean tree.
4. Verify expected owners and modes.
5. Verify secure credential ingress without revealing credential content.
6. Start only after the separate runtime authorization.
7. Obtain `READY` through `sudo /opt/trader-assist-v0/bin/ta-status`.
8. Observe at least 30 minutes after initial `READY`; capture `ta-status` at
   the start, midpoint, and end of this initial window.
9. Perform exactly one controlled stop/start restart using the commands in
   Section 6.
10. Obtain `READY` again through `sudo /opt/trader-assist-v0/bin/ta-status`.
11. Observe at least 30 minutes after post-restart `READY`; capture
    `ta-status` at the start, midpoint, and end of this post-restart window.
12. Target a total observation time of 60 minutes. The maximum bounded extension is 90 minutes.
13. Perform one read-only SQLite integrity check using the existing P4A
    runbook command.
14. Capture only a bounded sanitized journal segment and record its SHA-256.
15. Verify no credential or token appears in evidence.
16. Finish with the service stopped, disabled, and with no runtime process
    remaining.
17. Require a separate acceptance decision before real operation.

Every scheduled status result must be `READY`; any other classification fails
that qualification attempt. The start, midpoint, and end status captures are
mandatory for both 30-minute windows.

The qualification manifest records `initial_status_checks` and
`post_restart_status_checks`, each containing exactly three entries in this
order: `START`, `MIDPOINT`, and `END`. Every entry contains exactly `point`,
`timestamp`, `full_ta_status_output`, and `exit_code`.

At closeout, run this read-only check after the service is stopped:

```bash
systemctl is-enabled trader-assist-v0-public.service
```

Record `final_active_state`, `final_enabled_state`, and
`final_runtime_process_result` separately. The required values prove inactive,
disabled, and no runtime process remaining. `systemctl start` does not enable
the unit; an enabled result fails qualification.

For the one authorized bounded journal interval only, use this sequence. It
does not print matches or put secret values in argv:

```bash
umask 077
JOURNAL_EVIDENCE_DIR="$(mktemp -d)"
RAW_JOURNAL="$JOURNAL_EVIDENCE_DIR/raw-journal.txt"
SANITIZED_JOURNAL="$JOURNAL_EVIDENCE_DIR/sanitized-journal.txt"

sudo journalctl -u trader-assist-v0-public.service \
  --since "$AUTHORIZED_JOURNAL_SINCE" --until "$AUTHORIZED_JOURNAL_UNTIL" \
  --no-pager > "$RAW_JOURNAL"
chmod 0600 "$RAW_JOURNAL"

if grep -Eqi 'Authorization|Bearer|api_key|token|secret|webhook|-----BEGIN [A-Z ]*PRIVATE KEY-----' \
  "$RAW_JOURNAL"; then
  rm -f "$RAW_JOURNAL"
  rmdir "$JOURNAL_EVIDENCE_DIR"
  printf 'EVIDENCE_SECRET_SCAN_RESULT=FAIL\n'
  exit 1
fi
printf 'EVIDENCE_SECRET_SCAN_RESULT=PASS\n'
cp "$RAW_JOURNAL" "$SANITIZED_JOURNAL"
chmod 0600 "$SANITIZED_JOURNAL"
SANITIZED_JOURNAL_SHA256="$(sha256sum "$SANITIZED_JOURNAL" | awk '{print $1}')"
rm -f "$RAW_JOURNAL"
printf 'BOUNDED_JOURNAL_SANITIZED_SHA256=%s\n' "$SANITIZED_JOURNAL_SHA256"
```

The raw artifact is never accepted evidence and is deleted after sanitization;
only the sanitized artifact is hashed. `evidence_bundle_sha256` is the
SHA-256 of a separately assembled sanitized evidence bundle, not a hash of a
JSON manifest containing its own hash.

## 8. Qualification acceptance

- `QUALIFICATION_PASS`: every mandatory item completed, every scheduled
  status was `READY`, all final stopped/disabled/no-process proof is present,
  and no safety or authority violation remains unresolved.
- `QUALIFICATION_FAIL`: a mandatory check fails, a scheduled status is not
  `READY`, evidence contains a credential or token, or an authority boundary
  is violated.
- `QUALIFICATION_INCOMPLETE`: the authorized attempt ends without all
  mandatory evidence. It is not a pass and does not activate real operation.

The `qualification_result` evidence field has exactly three allowed operational
values: `PASS`, `FAIL`, and `INCOMPLETE`.

## 9. Human-machine responsibility matrix

| System | Human trader |
| --- | --- |
| Publishes bounded public-data status and signals. | Refreshes status and ignores signals unless it is `READY`. |
| Fails closed when state is stale, malformed, or unavailable. | Independently judges the market and manually executes or rejects trades. |
| Never submits an order. | Performs the one supported restart when needed and escalates persistent faults. |

## 10. Rollback and no-authority statement

Use the rollback commands in the existing [P4A local deployment
runbook](V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md#24-rollback) only when separately
authorized. Rollback planning does not authorize executing rollback commands
on a real host.

No account, wallet, private key, signing, nonce, order, cancellation,
automatic SL/TP, or exchange-write authority exists in this packet.

## 11. PHASE 3 — ACCEPTED_REAL_OPERATION

Only separate final user acceptance may decide whether a completed
qualification attempt becomes accepted real operation. This packet does not
grant that acceptance.
