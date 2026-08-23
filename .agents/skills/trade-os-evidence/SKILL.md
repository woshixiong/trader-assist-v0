---
name: trade-os-evidence
description: Collect concise deterministic Trader Assist implementation evidence such as exact HEAD, status, changed paths, diff scope and observed test results without making acceptance decisions.
---

# Trade OS Evidence

Collect facts; do not adjudicate acceptance.

Prefer deterministic evidence:

- repository/worktree and branch/detached state;
- exact base/HEAD;
- `git status --porcelain`;
- exact changed filenames and bounded diff stat/excerpts;
- commands/tests actually run and observed exit/result state;
- required artifacts/hashes;
- residual failures/blockers;
- whether commit/push/GitHub mutation was authorized and performed.

Keep large raw logs outside model context when possible and return decisive references/excerpts. HEAD drift, out-of-scope files, secret material, unauthorized mutation or a new material decision => evidence plus `L1_DECISION_REQUIRED`.