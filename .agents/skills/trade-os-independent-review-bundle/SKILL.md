---
name: trade-os-independent-review-bundle
description: Build a deterministic, hash-manifested local evidence bundle for strongest-ChatGPT independent review when GitHub-only evidence is insufficient.
---

# Trade OS Independent Review Bundle

Use only when T4 independent review needs local execution/inspection evidence that the ordinary ChatGPT review window cannot obtain directly from GitHub/connectors.

## Objective

Generate evidence, not an acceptance judgment.

Preferred flow:

```text
LOCAL DETERMINISTIC EVIDENCE
-> REVIEW BUNDLE
-> HASH MANIFEST
-> independent strongest-appropriate ChatGPT review
```

## Required bundle identity

Record as applicable:

- review/task ID;
- repository/worktree;
- exact base and HEAD;
- branch/detached state;
- changed-file list;
- exact patch/diff;
- exact task-specific source/config files requested by the frozen review plan;
- commands/tests/static checks actually run plus exit/result state;
- bounded decisive failure excerpts or external raw-log references;
- artifact hashes;
- frozen acceptance criteria and review prompt.

Create a manifest containing the SHA-256 of every included file. Recompute/verify before transport.

## Context economy

Do not include full repo archives, caches, dependencies, virtual environments, successful verbose logs or unrelated governance/history. Include only what the frozen review plan requires.

## Prohibited material

Never bundle secrets, tokens, credentials, cookies, wallets, private account identifiers, production databases, raw private/account data or unredacted sensitive logs.

## Transport

Manual path:

```text
Terminal/tooling builds bundle
-> user uploads exact bundle to a new independent ChatGPT review window
```

Hermes path after qualification:

```text
Hermes verifies exact bundle + manifest
-> verifies a fresh approved ChatGPT review surface and exact L1-frozen reviewer model/reasoning state
-> uploads exact files
-> pastes the frozen review prompt without paraphrase
-> verifies attachments/prompt before submit
-> submits and records transport checkpoints
```

If exact reviewer model/reasoning UI state, attachment identity, manifest, worktree/HEAD or prompt integrity cannot be verified, stop and return the checkpoint ledger. Do not switch to a weaker local reviewer silently.

This skill never declares independent PASS.