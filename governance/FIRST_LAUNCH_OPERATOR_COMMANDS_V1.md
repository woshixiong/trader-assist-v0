# Trader Assist First Launch Operator Commands V1

**Status:** PLANNED — final aliases become active after supported-host deployment and Mac Terminal configuration  
**Audience:** experienced human operator  
**Purpose:** preserve one canonical, copyable source for daily status checks and the shortest supported recovery path.

## 1. Daily commands

```bash
# Check whether current system signals may be considered.
ta-status

# Refresh status every 30 seconds.
ta-watch

# Exit continuous refresh.
# Press:
Ctrl+C
```

## 2. Status meanings

### `READY`

Current system output may enter the human judgment process.

The operator still decides whether to trade. Before using a signal, rapidly compare:

1. created time;
2. expiry time;
3. reference price or Mark Price;
4. current market price;
5. entry zone;
6. chase limit;
7. stop and targets;
8. quantity and planned risk;
9. current market context.

`READY` never means that a trade is mandatory.

### `NOT_READY`

Current system signals must be ignored.

The operator may continue discretionary trading independently and recheck later:

```bash
ta-status
```

Ordinary `NOT_READY` does not require stopping the service.

### `STATUS_UNKNOWN`

The current system state cannot be trusted or confirmed.

Ignore system signals and check again:

```bash
ta-status
```

If the condition persists, use the recovery sequence below.

## 3. Recovery sequence

```bash
# Level 1 — Recheck.
ta-status

# Level 2 — If the system remains unavailable for several minutes, restart it.
ta-restart

# Level 3 — If restart does not restore READY, collect bounded recent logs.
ta-logs
```

For engineering escalation, provide the complete output of:

```bash
ta-status
ta-logs
```

Do not prebuild a generalized automatic repair system. Diagnose and repair the concrete observed failure.

## 4. Planned Mac command behavior

The following aliases/functions are configured during First Launch deployment, not during planning.

### `ta-status`

Uses SSH from the Mac Terminal to run the supported read-only status command on the Lightsail host.

### `ta-watch`

Repeatedly runs `ta-status` every 30 seconds using the native shell; no GNU `watch`, Homebrew package, web UI, or FinalShell-specific integration is required.

### `ta-restart`

Runs the existing systemd restart command, waits briefly, and checks status again.

### `ta-logs`

Returns only the recent bounded service journal needed for diagnosis.

Mac Terminal is the primary interface. FinalShell is only a backup SSH, file-browsing, or long-log interface.

## 5. Server-side fallback commands

The final deployment copy must use the exact installed service name and paths. The currently planned commands are:

```bash
# Direct status check.
sudo /opt/trader-assist-v0/bin/ta-status

# Direct restart.
sudo systemctl restart trader-assist-v0-public.service

# Direct bounded logs.
sudo journalctl \
  -u trader-assist-v0-public.service \
  --since "-15 minutes" \
  -n 120 \
  --no-pager
```

Before routine use, Project Control must verify these values against the actual deployed host and remove every unresolved placeholder.

## 6. Actions not required during ordinary operation

Do not perform these actions merely because status is `NOT_READY`:

- stop the service;
- delete the database;
- delete credentials;
- modify the systemd unit;
- interpret PID, cgroup, wrapper, Bash, or procfs races;
- execute rollback or uninstall;
- attempt manual low-level repair.

## 7. Trading rules

```text
READY          → the signal may be considered by the trader.
NOT_READY      → ignore system signals and recheck later.
STATUS_UNKNOWN → ignore system signals; recover or escalate if persistent.
```

Additional fixed rules:

- Price beyond the chase limit: do not chase.
- Expired signal: do not use.
- Market context materially changed: reject the signal even if status is READY.
- The assistant being unavailable does not prevent discretionary trading.
- No command or status result grants automatic order authority.

## 8. Future transition

These human-assisted controls are valid only while execution remains manual and no account, signing, nonce, private-key, or exchange-write authority exists.

Before automatic or one-click execution is introduced, status, stale-data protection, order controls, kill-switch behavior, and automated recovery must be re-evaluated as hard machine-enforced safety requirements.