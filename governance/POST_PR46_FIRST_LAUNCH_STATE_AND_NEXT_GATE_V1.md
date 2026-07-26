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
`trader-assist-v0-public.service`; it does not open the runtime database. `READY` means the
signal may be considered, while the human trader remains independently responsible for the
trade decision. `NOT_READY` means ignore system signals and recheck later. `STATUS_UNKNOWN`
means ignore system signals and investigate or escalate if persistent.

The system provides restricted public-data decision support. No account or exchange-write
authority exists.

## Bounded recovery

1. Recheck status with `ta-status`.
2. For persistent failure, use the supported one controlled restart:
   `sudo systemctl stop trader-assist-v0-public.service` then
   `sudo systemctl start trader-assist-v0-public.service`.
3. If readiness is not restored, inspect one bounded journal window.
4. Escalate for targeted diagnosis.

## PR #48 failed qualification-automation route

PR #48 attempted to convert supported-host and First Launch qualification into a
repository-backed documentation, evidence and offline-test system. It remained Draft and was
not merged. Its final reviewed Head was
`0451afee4285d41b7e95f0b3a2bc458c6ec16c6c`; exact-head CI Run 288 / Run ID
`30204735266` succeeded, but the full Operations, Security and Final Acceptance Reviews all
failed.

The route consumed the normal repair and one exceptional third commit. No fourth commit is
authorized. PR #48 is frozen as a failed-design and historical research reference and must not
be used as deployment authority.

The core failure was architectural rather than a trading-runtime defect: documented shell
commands, separately rewritten tests, evidence sanitization, interpreter trust checks and
closeout checks became competing or incompletely verified implementations. Continuing to
repair the same design would build a low-frequency host-audit system rather than complete the
minimum personal First Launch.

Detailed history remains in
`governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md`.

## Current backlog ruling

The automated host qualification capability is used mainly during:

- host migration;
- major-version full redeployment;
- disaster recovery or complete host replacement;
- repeated deployments;
- multi-host or multi-operator operation;
- materially higher account or exchange authority;
- retained-evidence or compliance requirements.

These events are currently infrequent, so the capability is not active First Launch scope and
must not consume current development capacity.

Current status:

`DEFERRED_LOWEST_PRIORITY__NO_CURRENT_IMPLEMENTATION_AUTHORITY`

The capability remains at the last priority in the future backlog. It may be researched when
higher-priority work is complete or when a real activation condition exists, but implementation
requires a fresh user authorization and a clean replacement task from the then-current main.

The binding disposition is in
`governance/FIRST_LAUNCH_HOST_QUALIFICATION_LOWEST_PRIORITY_BACKLOG_RULING_V1.md`.
The previous permanent-abandonment ruling is retained only as a superseded historical record.

## Current minimum First Launch direction

Do not develop another repository qualification feature before First Launch.

At the actual deployment event, prepare one temporary, host-specific, visible command bundle
for one fixed supported host and one exact deployment SHA. The user executes bounded blocks
under step-by-step guidance and returns non-secret outputs before proceeding.

The session relies on the existing P4A deployment runbook, the merged `ta-status` command, one
controlled restart and direct operator confirmation of the minimum acceptance conditions.

Minimum operator acceptance conditions:

1. approved fixed Ubuntu/systemd host confirmed;
2. one fixed system Python 3.12+ path confirmed;
3. exact deployment SHA and clean tree confirmed;
4. systemd unit verification succeeds;
5. `ta-status` is executable and reaches `READY`;
6. three `READY` checks are observed in the initial window;
7. exactly one operator-controlled restart is performed;
8. three `READY` checks are observed after restart;
9. final service state is inactive and disabled, with no remaining runtime process;
10. any unresolved result is not accepted as PASS;
11. separate user acceptance is required before real operation.

Bounded journal output is for targeted diagnosis only when readiness remains abnormal. It is
not a mandatory retained or hashed First Launch qualification artifact.

## Low-cost alternatives for later deployment events

Before activating the backlog item, use the least expensive adequate option:

1. existing P4A runbook and exact commands;
2. a short migration or recovery checklist;
3. a temporary host-specific script generated for the event;
4. repository-based recreation from an exact approved commit;
5. cloud-provider instance or volume snapshot where separately evaluated and authorized;
6. secure restoration of credentials and database backups;
7. provider-native or maintained external tools before custom framework development.

These alternatives can support migration, major redeployment and disaster recovery without
requiring the full PR #48-style automation.

## Updated remaining First Launch P0 sequence

1. Canonical state synchronization — complete through PR #47.
2. PR #48 qualification-automation V1 — failed and frozen; no further repair.
3. At the actual deployment event, identify and approve one fixed host profile.
4. Separately authorize read-only host confirmation.
5. Generate one temporary host-specific, exact-SHA command bundle.
6. Separately authorize deployment.
7. Separately authorize runtime and supervised public smoke.
8. Perform the 3+3 `ta-status` qualification and one controlled restart.
9. Finalize the exact Mac Terminal shortcut and operator command card.
10. Reach the separate accepted-real-operation gate.

## Lowest-priority future backlog

- evaluate migration and disaster-recovery frequency after real operation;
- evaluate provider snapshots, images and maintained external tools;
- research RR-01 through RR-08 only when justified;
- reconsider the two-script design as one candidate, not a predetermined solution;
- use a clean replacement task rather than continuing PR #48;
- preserve a strict file, commit and anti-expansion budget;
- schedule only after higher-value product, stability, strategy and risk-control work.

## Efficiency-first engineering rule

Before building automation, compare event frequency, guided manual effort, risk reduction and
total build-and-maintenance cost.

When a low-frequency task can be completed safely by one operator with a short checklist or
temporary visible script, do not build a perfect, reusable or institution-grade feature.

Preferred order:

1. existing command;
2. short checklist;
3. temporary host-specific script;
4. provider-native or maintained external tool;
5. small permanent script only after repeated use proves net value;
6. framework only when scale, authority or compliance objectively requires it.

After the normal repair and one exceptional repair fail, continued patching of the same design
is prohibited. Reduce scope or create a clean replacement route.

## Next gate and authority

The canonical JSON state still names
`FIRST_LAUNCH_SUPPORTED_HOST_DEPLOYMENT_AND_QUALIFICATION_PACKET_V1`. This document records
the later failed-route and backlog decision without silently rewriting strict JSON, Schema or
evidence bindings.

Current practical next work occurs at the separately authorized fixed-host deployment session,
not through additional qualification-feature development.

`PLANNING_AUTHORIZED__HOST_ACCESS_NOT_AUTHORIZED__DEPLOYMENT_NOT_AUTHORIZED__RUNTIME_AND_SMOKE_NOT_AUTHORIZED`

Planning authority does not activate execution authority.

## Prior PR disposition

- PR #35: salvage input / not merged authority
- PR #42: superseded
- PR #43: superseded
- PR #44: salvage input / not merged authority
- PR #45: superseded and rejected implementation route
- PR #48: frozen failed-design and historical research reference / no fourth commit

## Deferred complexity

The current manual, public-data-only route rejects generalized host-verifier and evidence
frameworks, shared-host and multi-instance generalization, autonomous recovery, automatic
trading, account and exchange-write integration, unnecessary stop-command work, and
institution-grade automation not required for First Launch.
