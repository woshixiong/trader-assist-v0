---
name: trade-os-independent-review-bundle
description: Build a deterministic, hash-manifested local evidence bundle for strongest-ChatGPT independent review when GitHub-only evidence is insufficient.
---

# Trade OS Independent Review Bundle

Use only when T4 independent review needs local execution/inspection evidence that the ordinary ChatGPT review window cannot obtain directly from GitHub/connectors.

## Objective

Generate evidence, not an acceptance judgment.

Authority-bearing final review must occur in a **new ordinary ChatGPT conversation/window** distinct from the Engineering Control/Writer conversation. A same-conversation self-check may inform readiness but is never independent acceptance.

Preferred flow:

```text
LOCAL DETERMINISTIC EVIDENCE
-> REVIEW BUNDLE
-> HASH MANIFEST
-> independent strongest-appropriate ChatGPT review
```

## Compact Review Manifest

Before adding evidence, freeze a compact manifest:

```text
REVIEW_TARGET
EXACT_BASE / HEAD / TREE
EXACT_CHANGED_PATHS / DIFF_REF
FROZEN_ACCEPTANCE_CRITERIA
REQUIRED_SAFETY_BOUNDARIES
DECISIVE_CI / ARTIFACT / SOURCE / UPSTREAM_REFS
UNTRUSTED_PRIOR_CONCLUSIONS
OUTPUT_CONTRACT
AUTHORITY_BOUNDARY
```

The reviewer loads in that order. Full Issue/PR history, full governance corpus and unchanged accepted code are not default inputs. Any concrete missing/ambiguous fact triggers a targeted canonical read; unresolved uncertainty prohibits PASS.

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

Default review progression:

```text
EXACT IDENTITY
-> EXACT DELTA
-> ACCEPTANCE / SAFETY CONTRACT
-> DECISIVE CI / ARTIFACT
-> NECESSARY UPSTREAM
-> TARGETED HISTORY ONLY FOR A CONCRETE UNRESOLVED QUESTION
```

Context reduction must never remove a required acceptance criterion, blocker, negative case or safety boundary. Quality/correctness outrank context economy.

If the ChatGPT review stream is interrupted, do not infer review failure or repeat any final write blindly. Re-read the Review Manifest and exact live target/status; if no authoritative final result exists, resume/restart the read-only adjudication from the compact manifest. This recovery must not require replaying the full prior review transcript.

## Review context budget and idempotent egress

One authority-bearing Review uses one fresh review window. After the final result is written/read back, retire that window for authority-bearing review work.

If evidence collection itself threatens context integrity, freeze a bounded evidence-verification checkpoint and use a fresh adjudication window rather than carrying the whole proof chain in one conversation.

Derive before final write:

```text
REVIEW_RESULT_KEY =
  REVIEW_CLASS
  + TARGET_IDENTITY
  + CANDIDATE_OR_PACKET_IDENTITY
  + EXACT_HEAD_OR_TREE
```

Immediately before authority-bearing writeback:
1. fresh-read the canonical target thread;
2. search for the same Review Result Key;
3. if present, consume that canonical result ID and do not write again;
4. if absent, write exactly once and read back the created result.

After stream interruption/reconnect, read-before-write is mandatory. Blind duplicate result writes are prohibited.

## Compact authoritative Review Result

Prefer:

```text
VERDICT
EXACT_REVIEWED_IDENTITY
ACCEPTANCE_MATRIX
MATERIAL_BLOCKERS + EXACT_EVIDENCE
NEXT_ALLOWED_ACTION
AUTHORITY_BOUNDARY
```

Do not repeat long lists of already-proven PASS facts, raw logs or unchanged historical narrative. Compact output is allowed only after the reviewer has actually checked every required criterion; output brevity is not review-scope reduction.

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