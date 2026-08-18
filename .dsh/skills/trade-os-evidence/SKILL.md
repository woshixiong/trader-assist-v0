---
name: trade-os-evidence
description: Collect concise raw Trader Assist implementation evidence such as exact HEAD, status, changed paths, diff scope and observed test results without making engineering acceptance decisions.
whenToUse: Load near task completion or when the frozen Task Packet requires an evidence checkpoint.
user-invocable: true
disable-model-invocation: false
---

# Trade OS Evidence Collection

Collect facts; do not adjudicate engineering acceptance.

Prefer deterministic read-only evidence:

- repository/worktree path;
- branch or detached state;
- exact HEAD/base identities;
- `git status --porcelain`;
- exact changed filenames;
- bounded `git diff --stat` and task-relevant diff excerpts;
- commands/tests actually run and their exit/result states;
- artifacts/hashes explicitly required by the packet;
- residual failures/blockers;
- whether any commit/push/GitHub mutation was authorized and actually performed.

Preserve raw authority-bearing outputs outside model summaries when the Task Packet requests them. Do not hide failures, normalize unexpected output into PASS or claim CI/review results that were not observed.

If evidence shows HEAD drift, out-of-scope files, secret material, unauthorized mutation or a new material decision, return the evidence and `L1_DECISION_REQUIRED`.
