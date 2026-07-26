# Post-PR46 First Launch State and Next Gate

## Accepted state

- Accepted main and merge SHA: `414bb1df413ab877856a7aa3bb25e7b262aeab4a`
- Accepted task: `FIRST_LAUNCH_SIMPLE_STATUS_V1`
- PR: #46
- Accepted reviewed Head: `3e616d146e8bc6dd3db83fcb2b3a0453eb976096`
- Exact-head CI: `V0 contracts CI / Run 282 / Run ID 30130875992 / SUCCESS`
- Post-merge CI: `V0 contracts CI / Run ID 30131815661 / SUCCESS`

## `ta-status` behavior

The merged command reads only the strict local status snapshot and systemd state for
`trader-assist-v0-public.service`; it does not open the runtime database. `READY` means
the signal may be considered, while the human trader remains independently responsible
for the trade decision. `NOT_READY` means ignore system signals and recheck later.
`STATUS_UNKNOWN` means ignore system signals and investigate or escalate if persistent.
`READY` does not guarantee profitability, strategy correctness, or execution safety.

The system provides restricted public-data decision support. The experienced human trader
decides whether to act, may reject any signal, and executes manually. Non-`READY` states
require ignoring the signal. No account or exchange-write authority exists.

## Bounded recovery

1. Recheck status with `ta-status`.
2. For persistent failure, use the supported one controlled restart:
   `sudo systemctl stop trader-assist-v0-public.service` then
   `sudo systemctl start trader-assist-v0-public.service`.
3. If readiness is not restored, inspect one bounded journal window:
   `sudo journalctl -u trader-assist-v0-public.service --since "30 minutes ago" --no-pager`.
4. Escalate for targeted diagnosis.

## PR #48 failed qualification-packet route

PR #48 attempted to convert the supported-host and First Launch qualification process into
a repository-backed documentation, evidence, and offline-test package. It remained Draft
and was not merged. Its final reviewed Head was
`0451afee4285d41b7e95f0b3a2bc458c6ec16c6c`; exact-head CI Run 288 / Run ID
`30204735266` succeeded, but full Operations, Security and Final Acceptance Reviews all
failed.

The route received two repair rounds, including one exceptional third commit. No fourth
commit is authorized. PR #48 is frozen as a failed-design and research reference until a
replacement route is technically accepted. It must not be used as deployment authority.

The core failure was architectural rather than a runtime defect: documented shell commands,
separate test harnesses, evidence sanitization, interpreter trust checks, and closeout checks
became competing or incompletely verified implementations. Continuing to patch the same
route would recreate generalized verifier and evidence-framework work that was explicitly
deferred for First Launch.

See `governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md` for the
full record, operator comparison, unresolved questions, and deferred V2 proposal.

## Current minimum First Launch direction

The preferred immediate route is a bounded, human-controlled deployment and qualification
session for one fixed supported host, assisted by exact copy-ready commands generated for
the authorized host and deployment SHA.

This direction does not authorize host access or deployment. When separately authorized, it
should rely on the existing P4A deployment runbook, the merged `ta-status` command, one
controlled restart, and direct operator confirmation of the minimum acceptance conditions.
It must not add a generalized host-verifier, journal-evidence, or automation framework before
First Launch.

Minimum operator acceptance conditions remain:

1. approved host and fixed Python 3.12+ path confirmed;
2. exact deployment SHA and clean tree confirmed;
3. systemd unit verification succeeds;
4. `ta-status` is executable and reaches `READY`;
5. three `READY` checks are observed in the initial window;
6. exactly one operator-controlled restart is performed;
7. three `READY` checks are observed after restart;
8. final service state is inactive and disabled, with no remaining runtime process;
9. any unresolved result is not accepted as PASS;
10. separate user acceptance is required before real operation.

Bounded journal output is for targeted diagnosis only when readiness remains abnormal. It is
not a mandatory retained or hashed First Launch qualification artifact.

## Updated remaining First Launch P0 sequence

1. Canonical state synchronization — complete through PR #47.
2. PR #48 qualification-packet V1 — failed and frozen; no further repair.
3. Decide and document the minimum guided manual deployment checklist.
4. Separately authorize read-only host identification and preflight.
5. Generate one host-specific, copy-ready command bundle for the approved host and SHA.
6. Separately authorize deployment.
7. Separately authorize runtime and supervised public smoke.
8. Perform the 3+3 `ta-status` qualification and one controlled restart.
9. Finalize the exact Mac Terminal shortcut and operator command card.
10. Reach the separate accepted-real-operation gate.
11. After First Launch, reconsider the deferred scripted qualification V2 only if repeated
    deployments, a second host, or materially reduced manual reliability justify it.

## Deferred host-qualification backlog

### First Launch P0 — continue now

- minimum human-readable checklist;
- fixed-host and fixed-Python assumptions;
- exact SHA, clean tree, unit verification, and `ta-status` checks;
- one guided deployment session;
- one controlled restart and 3+3 readiness checks;
- final inactive / disabled / no-process confirmation;
- operator command card and Mac shortcut.

### Post-First-Launch — deferred research and implementation

- executable supported-host preflight script;
- executable bounded journal-evidence script;
- tests executing the exact scripts rather than independent behavioral models;
- trusted Python path ownership, mode, symlink, canonical-path, and digest checks;
- deterministic allowlisted journal transformation;
- normalized resource evidence;
- explicit connectivity-probe authority and result handling;
- reusable deployment qualification for repeated or additional hosts.

The deferred design proposed two short single-purpose scripts and a bounded six-file
replacement PR. It is retained as a future option, not current First Launch scope.

## Next gate and authority

The canonical JSON state still names
`FIRST_LAUNCH_SUPPORTED_HOST_DEPLOYMENT_AND_QUALIFICATION_PACKET_V1`. This document records
the later failed-route and deferred-work decision without silently rewriting strict JSON,
Schema, or evidence bindings.

Current practical next work is the minimum guided manual checklist decision and later
separately authorized host session.

`PLANNING_AUTHORIZED__HOST_ACCESS_NOT_AUTHORIZED__DEPLOYMENT_NOT_AUTHORIZED__RUNTIME_AND_SMOKE_NOT_AUTHORIZED`

Planning authority does not activate execution authority.

## Prior PR disposition

- PR #35: salvage input / not merged authority
- PR #42: superseded
- PR #43: superseded
- PR #44: salvage input / not merged authority
- PR #45: superseded and rejected implementation route
- PR #48: frozen failed-design and research reference / not merged authority

## Deferred complexity

The current manual, public-data-only route rejects or defers generalized host-verifier and
evidence frameworks, shared-host and multi-instance generalization, autonomous recovery,
automatic trading, account and exchange-write integration, unnecessary stop-command work,
and institution-grade automation not required for First Launch.
