# VNext Final Review and Protected Gate Flow

## Purpose

Define the final delivery path after implementation and CI completion.

## Flow

```text
Implementation
  ↓
Deterministic CI
  ↓
Fresh Independent Final Review
  ↓
PASS
  ↓
Human authorization
  ↓
MARK_READY
  ↓
MERGE
```

## Final Review Role

The final reviewer:

- is read-only;
- uses exact GitHub evidence;
- does not trust Writer or Engineering Control conclusions;
- does not modify code;
- does not perform protected actions.

## PASS Routing

When PASS:

Output:

1. exact reviewed head;
2. validation evidence;
3. protected action request;
4. ready-to-use authorization command.

## FAIL Routing

When FAIL:

Return to Engineering Control.

Engineering Control decides:

- bounded repair;
- new package;
- scope clarification;
- stop condition.

## Human Gates

Remain explicit:

- MARK_READY;
- MERGE;
- DEPLOYMENT;
- production mutation.

No historical approval inheritance is allowed.
