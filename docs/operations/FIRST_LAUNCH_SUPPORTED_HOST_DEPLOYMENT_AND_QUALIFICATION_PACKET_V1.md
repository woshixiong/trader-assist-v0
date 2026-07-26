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

Run the following commands only after separate host-access authorization. They
read the specified host facts, do not print environment variables,
configuration, or credential contents, and do not install, create, modify,
start, or stop anything.

```bash
cat /etc/os-release
uname -m
uname -r
systemd --version
python3 --version
git --version
systemd-analyze --version
df -h / /opt /etc /var/lib
grep '^MemAvailable:' /proc/meminfo

for path in \
  /opt/trader-assist-v0 \
  /etc/trader-assist-v0 \
  /var/lib/trader-assist-v0 \
  /etc/systemd/system/trader-assist-v0-public.service; do
  if test -e "$path"; then
    printf 'PRESENT %s\n' "$path"
  else
    printf 'ABSENT %s\n' "$path"
  fi
done

if test -e /etc/systemd/system/trader-assist-v0-public.service; then
  sudo systemd-analyze verify /etc/systemd/system/trader-assist-v0-public.service
else
  printf 'UNIT_NOT_PRESENT_PRE_DEPLOYMENT\n'
fi
```

Classify the result as follows:

- `HOST_PROFILE_PASS`: every required platform capability is present; Python
  is 3.12 or newer; disk and memory are adequate for the existing runtime; and
  either the unit is not yet present before deployment or every present unit
  validates successfully.
- `HOST_PROFILE_FAIL`: Python is missing or below 3.12; systemd or
  `systemd-analyze` is unavailable; the profile is incompatible; or a present
  unit fails `systemd-analyze verify`. These conditions fail closed.
- `HOST_PROFILE_UNKNOWN`: the authorized read-only evidence cannot establish a
  required fact. Do not proceed until separately authorized targeted
  diagnosis resolves it.

Path absence is recorded for Phase 1 planning; it never authorizes creating a
path. A unit that is present but cannot be validated is incompatible and is a
`HOST_PROFILE_FAIL`.

## 5. PHASE 1 — DEPLOYMENT

After separate deployment authorization, use the existing
[P4A local deployment runbook](V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md). This packet
does not duplicate or broaden it. The authorization must name one full
40-character deployment SHA after this packet has merged; it must not use this
planning branch SHA.

The authorized deployment must use a detached checkout with exact `HEAD`
equality and a clean repository, install only the hashed runtime lock without
an editable install, retain the root-owned source installation and existing
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
authorization. It is manual, single-host, single-process, ETH-only, and has
no automatic retry or self-healing.

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
14. Capture only a bounded redacted journal segment and record its SHA-256.
15. Verify no credential or token appears in evidence.
16. Finish with the service stopped, disabled, and with no runtime process
    remaining.
17. Require a separate acceptance decision before real operation.

Every scheduled status result must be `READY`; any other classification fails
that qualification attempt. The start, midpoint, and end status captures are
mandatory for both 30-minute windows.

## 8. Qualification acceptance

- `QUALIFICATION_PASS`: every mandatory item completed, every scheduled
  status was `READY`, all final stopped/disabled/no-process proof is present,
  and no safety or authority violation remains unresolved.
- `QUALIFICATION_FAIL`: a mandatory check fails, a scheduled status is not
  `READY`, evidence contains a credential or token, or an authority boundary
  is violated.
- `QUALIFICATION_INCOMPLETE`: the authorized attempt ends without all
  mandatory evidence. It is not a pass and does not activate real operation.

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
