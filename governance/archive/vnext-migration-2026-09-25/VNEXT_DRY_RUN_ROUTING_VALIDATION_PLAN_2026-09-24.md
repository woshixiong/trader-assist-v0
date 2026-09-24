# VNext Dry Run Routing Validation Plan

## Purpose
Validate that the proposed VNext governance flow produces deterministic routing before activation.

## Validation Scope

1. Preflight to Codex Plan handoff
- Input: approved development package
- Output: exact Codex startup command and bound execution context

2. Pre-code review routing
- PASS -> execution
- FAIL with implementation clarification -> Codex plan revision
- FAIL with scope/architecture issue -> Engineering Control replanning

3. Execution and CI loop
- CI owner remains GitHub/deterministic tooling
- Failures return to bounded repair path

4. Final review routing
- PASS -> retained human protected gate
- FAIL -> Engineering Control replanning

## Required Output Contract
Every transition must provide:
- current state
- decision
- destination
- exact next action
- authority requirement

V4 remains active until qualification is complete.
