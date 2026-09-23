---
name: trade-os-v4-review
description: Enforce the V4 distinction between read-only Codex Code Review and fresh ordinary-ChatGPT final Independent Review, including exact-head and COMMENT_ONLY rules.
---

# Trade OS V4 Review

## Codex Code Review

For a large Codex package, use a fresh `code_reviewer` child only when the
actual spawned child model and reasoning are runtime-verifiable and match the
frozen Terra/Medium internal-review route. If runtime identity cannot be proven,
skip the Codex child reviewer rather than silently inheriting or falling back
to the parent/default Sol/High profile. When used, it is read-only and reviews
exact base/head/diff for correctness, regressions, safety/security, scope,
authority, and missing decisive tests. It cannot edit or become final
independent acceptance. Final authority-bearing Independent Review remains a
fresh ordinary ChatGPT context with High reasoning.

Ordinary in-scope findings return to the same Writer. New architecture,
security, dependency, scope, authority, or root cause returns to Engineering
Control.

## Final Independent Review

After exact-head CI is green, use one fresh ordinary ChatGPT context that did
not control or implement the candidate. Permission is read-only; reasoning is
High or the strongest appropriate current level. Supply a compact manifest:

```text
REVIEW_RESULT_KEY
PR / EXACT BASE / HEAD / TREE
EXACT CHANGED PATHS / DIFF
FROZEN ACCEPTANCE CRITERIA
REQUIRED SAFETY / AUTHORITY BOUNDARIES
EXACT-HEAD CI / ARTIFACT LOCATORS
EXPLICITLY UNTRUSTED PRIOR CONCLUSIONS
```

Fresh-read the PR/head before result egress and deduplicate by Review Result
Key. A changed head requires a new fresh Reviewer.

Precompute `CAN_SUBMIT_NATIVE_REVIEW`. If YES, submit the appropriate native
review. If the authenticated PR owner cannot self-approve, write canonical
exact-head evidence with `REVIEW_SUBMISSION_MODE=COMMENT_ONLY`. COMMENT_ONLY is
review evidence, not a second identity. Neither mode authorizes Mark Ready,
merge, deployment, runtime changes, credentials, exchange writes, or trading.
