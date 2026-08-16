# Hermes Trae Computer Use Profile V1

**PROFILE_ID:** `HERMES-TRAE-COMPUTER-USE-V1-2026-08-16`  
**PARENT_CONTRACT:** `HERMES-EXECUTION-OPERATOR-V1-2026-08-16`

## Decision

Hermes **may directly operate Trae through Computer Use**. A Trae CLI is not required for this workflow.

The reason CLI remains preferable where available is reliability and observability, not authority: UI automation has more state (window, project, model, session, dialogs, login/update state). This profile makes that extra state explicit and fail-closed.

## Mandatory Hermes mode

For Trae pilot execution use Hermes Computer Use **bounded permission mode** with a reviewed capability manifest.

Required configuration direction:

```yaml
computer_use:
  permission_mode: bounded
  capability_manifest: <reviewed manifest path>
```

Do not use `/yolo`, unrestricted mode, or approvals-off for Trader Assist automation.

The capability manifest must be reviewed before launch and should allow only the specific Trae application/window/tool actions needed by the current pilot. Anything outside the manifest must fail closed.

## Allowed Trae UI actions

Only when the frozen Task Packet specifies `EXECUTOR=TRAE_COMPUTER_USE`, Hermes may:

1. locate/open Trae;
2. verify the expected workspace/worktree;
3. verify the exact pre-authorized model/mode;
4. verify or create the exact session mode specified by L1;
5. paste the exact loader instruction or exact Task Packet;
6. submit once;
7. wait;
8. capture raw Trae output;
9. collect explicitly authorized local Git/status evidence.

## Forbidden UI actions

Hermes must not:

- select a different model because the requested one is unavailable;
- choose or switch project/worktree on its own;
- enlarge scope;
- accept an unexpected permission/security dialog;
- log into a new account or change account settings;
- install/update extensions or Trae itself;
- respond substantively to a Trae clarification that requires judgment;
- approve commit/push/merge/deploy unless a separate later authority explicitly permits that exact action;
- retry a failed coding task with a changed prompt;
- use Computer Use to work around a blocked capability manifest.

## Stop conditions

Return `HUMAN_OR_L1_DECISION_REQUIRED` immediately if:

- workspace/worktree cannot be proven;
- authorized model/mode is unavailable;
- Trae shows an unexpected dialog, login, update, permission request, or conflicting state;
- exact Task Packet transport cannot be verified;
- Trae requests a route/scope/design decision;
- the requested UI action is outside the reviewed capability manifest.

## Pilot boundary

Initial Trae Computer Use tasks must use an isolated non-production worktree and must not expose production credentials or production host controls.

This profile does not authorize Hermes to decide whether Trae should receive a task. The L1 Engineering layer must freeze `EXECUTOR=TRAE_COMPUTER_USE` and the exact model/mode first.
