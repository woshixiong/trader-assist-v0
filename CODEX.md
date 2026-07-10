# Executor Instructions

## Repository state

```text
LAST_COMPLETED_SLICE: V0-01A4-OFFICIAL-RATE-LIMIT-AUTHORITY-FREEZE
ACTIVE_IMPLEMENTATION_SLICE: NONE
ACTIVE_IMPLEMENTATION_WRITE_LEASE: NONE
RATE_LIMIT_STATUS: UNRESOLVED_OFFICIAL_LIMIT
LIVE_TRANSPORT_AUTHORIZED: FALSE
```

## Current bounded task

`V0-01A4D1 — POSTMERGE_DOC_AUTHORITY_CONSISTENCY_SYNC`

This is a documentation/governance synchronization task only. It does not authorize a new implementation slice.

## Allowed

Only these files may change:

- `README.md`;
- `CODEX.md`;
- `docs/V0_01_SCOPE.md`;
- `docs/V0_01_OFFICIAL_SOURCE_CATALOG.md`;
- `docs/architecture/V0_01_DATA_PLANE.md`.

The task may only:

- mark A4 as completed;
- state that no implementation slice or implementation write lease is active;
- align documentation with existing executable hash/version authorities;
- restore the documented fixed `SOURCE_CATALOG_HASH`;
- document the A4 rate-limit authority insertion point;
- preserve unresolved, fail-closed live-transport gating.

## Forbidden

- Python source or test changes;
- schema, fixture, dependency, lockfile, script, or CI-workflow changes;
- HTTP or WebSocket clients, sockets, DNS, async runtime, live endpoint connection, polling, reconnect, heartbeat, health, backfill, or soak runtime;
- numeric rate-limit values or a transition away from `UNRESOLVED_OFFICIAL_LIMIT`;
- credentials, public account addresses, wallets, signing, nonces, exchange writes, order mutation, Testnet/Mainnet execution configuration;
- extractor/normalizer implementation, strategy candidates, AI recommendations, risk sizing, Silver, dashboards, databases, cloud storage, or later V0 slices;
- raw operational payloads, logs, caches, databases, source archives, private/user/account data, secrets, or unredacted live observations in Git;
- modifications to `woshixiong/trade-os`.

## New implementation gate

No implementation work may begin from this task. Any later V0 slice requires all of the following before writing code:

1. project-control scope freeze on the then-current exact `main` head;
2. an explicit bounded write lease;
3. a dedicated branch and Draft PR;
4. required CI success on the exact head;
5. external independent exact-head review;
6. separate finalization authorization.

## Required checks

The Draft PR must pass the repository's full standard CI. The executor must also verify:

```text
changed files are exactly the five allowed documentation files
git diff --check
no executable hash/version value differs from source authority
RATE_LIMIT_STATUS remains UNRESOLVED_OFFICIAL_LIMIT
live transport remains unauthorized
```

Never report a check as passed unless it was executed and observed.
