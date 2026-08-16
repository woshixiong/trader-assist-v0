# Hermes Trae Computer Use Profile V1

**PROFILE_ID:** `HERMES-TRAE-COMPUTER-USE-V1-2026-08-16`  
**PARENT_CONTRACT:** `HERMES-EXECUTION-OPERATOR-V1-2026-08-16`  
**ACTIVATION:** No Trae Computer Use pilot is authorized until the repaired PR exact head receives independent acceptance and the existing M2 entry gate is separately satisfied.

## Decision

Hermes **may directly operate Trae through Computer Use**. A Trae CLI is not required.

CLI remains preferable where available because it is easier to observe and reproduce, not because Computer Use is disallowed. UI automation carries extra state — window, workspace, model, session, dialogs, login/update state — so this profile makes those states explicit and fail-closed.

## Mandatory machine gate

Trae execution is allowed only when a schema-valid Task Packet contains all of:

```text
stage=H2_BOUNDED_EXECUTOR_LAUNCH
destination=TRAE_APP
executor.kind=TRAE_COMPUTER_USE
executor.model=<exact pre-authorized model>
executor.executor_mode=<exact pre-authorized Trae mode>
executor.session_mode=<NEW or RESUME_EXACT>
executor.target_worktree=<exact isolated worktree>
executor.target_branch=<exact branch>
executor.expected_head_sha=<exact HEAD>
permissions.allowed_paths=<non-empty allowlist>
automation_track_gate.required_milestone=M2
automation_track_gate.m1_entry_condition_satisfied=true
automation_track_gate.evidence_refs=<at least two accepted M1 evidence refs>
```

Session identity is additionally machine-constrained:

```text
IF executor.session_mode=RESUME_EXACT
THEN executor.session_id=<exact non-empty session id> is REQUIRED

IF executor.session_mode=NEW
THEN executor.session_id MUST be absent

executor.session_mode=NOT_APPLICABLE is invalid for H2.
```

Hermes must not infer or fill any of these fields.

The schema validates the shape of `automation_track_gate`, but the acceptance of each M1 evidence reference must be verified by a deterministic validator before H2. Hermes must not interpret free-text evidence refs as accepted evidence.

## Mandatory Hermes permission mode

For Trae pilot execution use Hermes Computer Use **bounded permission mode** with a reviewed capability manifest:

```yaml
computer_use:
  permission_mode: bounded
  capability_manifest: <reviewed manifest path>
```

Do not use `/yolo`, unrestricted mode, or approvals-off for Trader Assist automation.

The capability manifest must be reviewed before launch and should allow only the specific Trae application/window/tool actions needed by the current packet. Anything outside the manifest must fail closed.

## Allowed Trae UI actions

Only from a valid H2 packet may Hermes:

1. locate/open Trae;
2. verify the expected workspace/worktree;
3. verify the exact model/mode;
4. verify the exact session mode and, for `RESUME_EXACT`, the exact session id specified by L1;
5. create a new session only when `session_mode=NEW`, or resume only the exact frozen session when `session_mode=RESUME_EXACT`;
6. paste the verified exact Task Packet or loader instruction;
7. submit once;
8. wait;
9. capture raw Trae output;
10. collect explicitly authorized read-only local Git/status evidence.

## Forbidden UI actions

Hermes must not:

- select a different model because the requested one is unavailable;
- choose or switch project/worktree on its own;
- guess which Trae session to resume;
- enlarge scope or allowed paths;
- accept an unexpected permission/security dialog;
- log into a new account or change account settings;
- install/update extensions or Trae itself;
- respond substantively to a Trae clarification that requires judgment;
- approve commit/push/merge/deploy unless a separate later authority explicitly permits that exact action;
- retry a failed coding task with a changed prompt;
- use Computer Use to work around a blocked capability manifest.

## Stop conditions

Return `HUMAN_OR_L1_DECISION_REQUIRED` immediately if:

- the H2/M2 machine gate is absent or invalid;
- `session_mode` is not `NEW` or `RESUME_EXACT`;
- `RESUME_EXACT` lacks an exact `session_id`, or `NEW` unexpectedly carries one;
- accepted M1 evidence cannot be deterministically verified;
- workspace/worktree/branch/HEAD cannot be proven;
- authorized model/mode is unavailable;
- Trae shows an unexpected dialog, login, update, permission request, or conflicting state;
- exact Task Packet transport cannot be verified;
- Trae requests a route/scope/design decision;
- the requested UI action is outside the reviewed capability manifest.

## Pilot boundary

Initial Trae Computer Use tasks must use an isolated non-production worktree and must not expose production credentials or production-host controls.

This profile does not authorize Hermes to decide whether Trae should receive a task. L1 Engineering must freeze `EXECUTOR=TRAE_COMPUTER_USE` and the exact model/mode before Hermes acts.
