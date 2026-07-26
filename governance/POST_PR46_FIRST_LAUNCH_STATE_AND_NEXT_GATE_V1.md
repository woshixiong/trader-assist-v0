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

The automated host qualification capability remains at the last priority in the future backlog:

`DEFERRED_LOWEST_PRIORITY__NO_CURRENT_IMPLEMENTATION_AUTHORITY`

It is useful mainly for host migration, major-version full redeployment, disaster recovery,
repeated deployments, multiple hosts or operators, higher account or exchange authority, and
retained-evidence or compliance requirements.

It must not consume current First Launch capacity. Future implementation requires a fresh
cost-benefit review, explicit user authorization and a clean replacement task from then-current
main. PR #48 must not be resumed.

The binding disposition is in
`governance/FIRST_LAUNCH_HOST_QUALIFICATION_LOWEST_PRIORITY_BACKLOG_RULING_V1.md`.
The previous permanent-abandonment ruling is retained only as a superseded historical record.

## Minimum pre-launch recovery readiness

The complete PR #48-style automation is deferred, but recovery preparation cannot be deferred
entirely until after a disaster.

Before accepted real operation, establish the following minimum recovery anchors:

1. cloud-account access and recovery remain available independently of the host;
2. the notification credential has an approved recoverable source outside the host;
3. the deployed exact SHA, service name, fixed Python path and important filesystem paths are
   recorded without secret values;
4. the SQLite database has a defined safe backup and restore method;
5. after qualification and before accepted real operation, one backup is created and verified
   by opening the backup read-only and running an integrity check;
6. the default recovery strategy is recorded as exact-SHA rebuild plus secure credential and
   database restoration;
7. a provider snapshot or image is an optional recovery-speed layer, not the only recovery
   source.

The items above are a small operational safety gate, not a new product feature or verifier
framework.

Event-specific migration or recovery commands, permanent automation, scheduled snapshot
automation, multi-host support and a full second-host restore drill may wait until a real event
or later backlog activation.

The binding minimum is documented in
`governance/FIRST_LAUNCH_MINIMUM_RECOVERY_READINESS_V1.md`.

## Current minimum First Launch direction

Do not develop another repository qualification feature before First Launch.

At the deployment event, prepare one temporary, host-specific, visible command bundle for one
fixed supported host and one exact deployment SHA. The user executes bounded blocks under
step-by-step guidance and returns non-secret outputs before proceeding.

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

## Reorganized remaining First Launch P0 sequence

1. Finalize the documentation-only PR #49 decision package:
   - verify its exact-head CI and independent documentation review;
   - merge only under separate user authorization;
   - do not merge PR #48.
2. Complete the minimum recovery-readiness decisions that do not require host mutation:
   - confirm cloud-account recovery access;
   - confirm an external recoverable credential source;
   - choose exact-SHA rebuild as the default recovery route;
   - approve the small SQLite backup/restore method;
   - decide whether a provider snapshot will be used as an optional speed layer.
3. Identify and approve one fixed First Launch host profile.
4. Separately authorize and perform read-only host confirmation.
5. Generate one temporary host-specific, exact-SHA deployment and qualification command bundle.
6. Separately authorize deployment.
7. Deploy the exact approved SHA and verify clean tree, fixed Python, hashed runtime
   dependencies, configuration paths, secure credential ingress, default-off state, systemd
   unit and executable `ta-status`.
8. Separately authorize runtime and supervised public smoke.
9. Perform the initial 3-check `READY` window, exactly one controlled restart and the second
   3-check `READY` window.
10. Stop and close out the qualification run; confirm inactive, disabled and no remaining
    runtime process.
11. Create the first verified SQLite backup and, if separately selected, a provider snapshot.
12. Finalize the Mac Terminal shortcut and concise operator command card.
13. Complete the separate accepted-real-operation review and user authorization.

PR #42, PR #43, PR #44 and PR #45 cleanup is governance housekeeping and must not block the
deployment critical path. PR #48 remains frozen and may be closed later under separate
authorization.

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
the later failed-route, minimum recovery-readiness and backlog decisions without silently
rewriting strict JSON, Schema or evidence bindings.

Current practical next work is the documentation-only PR #49 finalization decision followed by
the separately authorized fixed-host preflight and deployment session.

`PLANNING_AUTHORIZED__HOST_ACCESS_NOT_AUTHORIZED__DEPLOYMENT_NOT_AUTHORIZED__RUNTIME_AND_SMOKE_NOT_AUTHORIZED`

Planning authority does not activate execution authority.

## Prior PR disposition

- PR #35: salvage input / not merged authority
- PR #42: superseded
- PR #43: superseded
- PR #44: salvage input / not merged authority
- PR #45: superseded and rejected implementation route
- PR #48: frozen failed-design and historical research reference / no fourth commit
- PR #49: documentation-only current decision package / Draft until separately finalized

## Deferred complexity

The current manual, public-data-only route rejects generalized host-verifier and evidence
frameworks, shared-host and multi-instance generalization, autonomous recovery, automatic
trading, account and exchange-write integration, unnecessary stop-command work, and
institution-grade automation not required for First Launch.
