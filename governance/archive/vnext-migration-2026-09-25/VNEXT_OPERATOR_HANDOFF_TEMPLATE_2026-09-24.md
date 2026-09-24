# VNext Operator Handoff Template

Every stage transition must provide:

## State
- current phase;
- exact task/base/head binding;
- completed validation.

## Decision
- PASS / FAIL;
- routing decision.

## Next action
- destination role;
- exact command or prompt;
- required authority.

## Forbidden ambiguity

Never require the human to infer whether the next step belongs to Control, Codex, Writer, or Reviewer.
