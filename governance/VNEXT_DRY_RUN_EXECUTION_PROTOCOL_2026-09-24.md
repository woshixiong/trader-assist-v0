# VNext Dry Run Execution Protocol

## Objective

Validate the complete workflow before activation.

## Scenario Matrix

1. Normal path
2. Plan rejection
3. Pre-code review failure
4. CI failure and repair
5. Final review failure
6. Interrupted execution recovery
7. Quota interruption recovery

## Required Output Contract

Every stage must provide:

- Current state
- Decision
- Next destination
- Exact next command
- Required authority

## Success Criteria

The workflow completes without requiring manual state interpretation between stages.
