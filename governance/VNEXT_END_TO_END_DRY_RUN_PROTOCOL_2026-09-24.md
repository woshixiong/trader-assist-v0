# VNext End To End Dry Run Protocol

## Purpose

Validate the complete governance workflow before activation.

## Main Flow

Preflight
-> Codex Plan
-> Pre-code Review
-> Execution
-> CI
-> Repair Loop
-> Independent Final Review
-> Human Protected Gate

## Required Evidence

Each stage records:

- current state
- decision
- destination
- exact next action
- authority requirement

## Failure Routing

Review failures return to the defined owner:

- planning/design issue: Engineering Control
- implementation issue: Codex bounded repair
- final review failure: Engineering Control

## Success Criteria

The workflow must minimize manual routing decisions while preserving protected human gates.
