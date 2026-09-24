# VNext Qualification Dry Run Checklist

## Purpose

Validate the candidate governance flow before activation without changing the active governance baseline.

## Core Path

1. Preflight package creation
2. Codex Plan-only execution
3. Pre-code review routing
4. Codex implementation
5. Deterministic CI validation
6. Repair loop if required
7. Fresh independent final review
8. Human protected gate

## Validation Requirements

Each stage must record:

- current state
- decision
- destination
- exact next action
- authority requirement

## Failure Validation

- Plan failure -> revise plan or return to Control for scope decisions
- Review failure -> explicit routing destination
- CI failure -> bounded repair
- Final review failure -> Engineering Control replan
- Interrupted execution -> checkpoint resume

## Activation Rule

Dry run results must be reviewed before switching from V4 active governance to VNext active governance.
