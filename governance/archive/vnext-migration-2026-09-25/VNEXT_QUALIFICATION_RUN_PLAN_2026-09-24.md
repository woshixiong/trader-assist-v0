# Trade OS VNext Governance Qualification Run Plan

Status: preparation only

## Purpose

Define the first validation run after VNext governance activation without changing active governance prematurely.

## Qualification goals

- Verify routing decisions are deterministic.
- Verify Codex handoff contains executable next actions.
- Verify review failures have explicit return destinations.
- Verify checkpoint recovery avoids semantic reruns.
- Verify human gates remain limited to required protected actions.

## Test scenarios

1. Normal coding package
2. Pre-code review failure
3. Implementation failure
4. CI failure
5. Final independent review failure
6. Interrupted Codex session recovery
7. Token/quota interruption recovery

## Pass conditions

The workflow must provide:

- one canonical state source;
- one next-action owner;
- one copy-ready continuation command;
- no unnecessary human relay steps.

## Activation rule

This qualification run occurs only after explicit VNext activation and migration completion.
