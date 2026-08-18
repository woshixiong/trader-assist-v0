---
name: trade-os-writer-preflight
description: Verify a frozen Trader Assist Writer Task Packet, exact Git/worktree identity, authority attestations, scope and stop conditions before DeepSeek Harness performs any task action.
whenToUse: Load at the start of every Trader Assist / Trade OS DeepSeek Harness task before repository mutation or material execution.
user-invocable: true
disable-model-invocation: false
---

# Trade OS Writer Preflight

Use this skill mechanically. It does not grant or create engineering authority.

Before any task action:

1. Read the frozen Task Packet exactly as supplied. Do not paraphrase control fields.
2. Verify `executor.kind=DEEPSEEK_HARNESS`, expected DSH version, `provider=deepseek-official`, explicit model/reasoning, agent preset, permission preset and session mode.
3. Verify repository/worktree identity with read-only Git commands: repository root, expected branch/detached state, exact base/expected HEAD, and clean/declared worktree state.
4. Verify the packet contains `PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS`; for material Writer tasks also require `ENGINEERING_PREFLIGHT_GATE=PASS`.
5. Verify allowed paths, prohibited scope, tests, repair stage, stop conditions, output contract and user-retained gates are explicit.
6. Read only the narrow authority/source files explicitly referenced by the packet unless a discovered conflict requires escalation.
7. Record the preflight facts before mutation.

Fail closed and return `L1_DECISION_REQUIRED` without implementation when any of these occurs:

- Task Packet missing/ambiguous/stale;
- repo/worktree/HEAD drift;
- model/executor/permission/session ambiguity;
- allowlist expansion required;
- new dependency/service/provider required;
- new material architecture/product/strategy/security decision required;
- authority conflict or governance mismatch;
- repair route/stage change not frozen;
- any requested action crosses Mark Ready, merge, deploy, runtime/cloud, credential/private-API, signing/wallet, exchange-write/order/trading gates without current explicit authority.

Do not solve a fail-closed condition by weakening validation, changing the route, picking another executor/model, or silently expanding scope.
