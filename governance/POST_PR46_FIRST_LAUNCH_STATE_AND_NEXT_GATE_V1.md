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

## Remaining First Launch P0 sequence

1. Canonical state synchronization.
2. Supported-host deployment and qualification packet planning.
3. Separate authorization before any host access.
4. Separate authorization before deployment.
5. Separate authorization before runtime or supervised smoke.
6. Supported-host qualification.
7. Exact operator command and Mac Terminal shortcut finalization where still applicable.
8. Accepted real-operation gate.

## Next gate

`FIRST_LAUNCH_SUPPORTED_HOST_DEPLOYMENT_AND_QUALIFICATION_PACKET_V1`

`PLANNING_AUTHORIZED__HOST_ACCESS_NOT_AUTHORIZED__DEPLOYMENT_NOT_AUTHORIZED__RUNTIME_AND_SMOKE_NOT_AUTHORIZED`

Planning authority does not activate execution authority.

## Prior PR disposition

- PR #35: salvage input / not merged authority
- PR #42: superseded
- PR #43: superseded
- PR #44: salvage input / not merged authority
- PR #45: superseded and rejected implementation route

## Deferred complexity

The current manual, public-data-only route rejects or defers generalized host-verifier and
evidence frameworks, shared-host and multi-instance generalization, autonomous recovery,
automatic trading, account and exchange-write integration, unnecessary stop-command work,
and institutional-grade automation not required for First Launch.
