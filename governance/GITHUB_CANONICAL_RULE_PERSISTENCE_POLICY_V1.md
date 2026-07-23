# GitHub Canonical Rule Persistence Policy V1

**Status:** DRAFT / EFFECTIVE AFTER MERGE  
**Purpose:** make durable project rules readable by every ordinary ChatGPT, Product Planning, Engineering Optimization, Project Control, Writer, and Reviewer window.

## 1. Canonical source

GitHub is the canonical shared source of truth for persistent:

- product decisions;
- engineering rules;
- project governance;
- cross-window operating instructions;
- deferred work and risk registers;
- phase transitions;
- model and Agent routing;
- resource and token policies;
- accepted post-launch planning inputs.

Chat history and local control files are not sufficient permanent records.

Local files may exist as caches, generated packets, evidence copies, or execution aids. They must reference the canonical GitHub path and commit SHA and may not independently redefine project rules.

## 2. Persistence trigger language

The following user language, and equivalent expressions, must be interpreted as a request to persist the accepted decision to GitHub governance:

- “同步固定对齐”;
- “固定下来”;
- “定规则”;
- “固定规则”;
- “以后都按这个执行”;
- “写入项目规则”;
- “让其他窗口继承”;
- “统一整理并同步”;
- “不要遗漏” when referring to future project planning or governance.

The assistant or authority window must not represent a chat-only note as fully synchronized.

## 3. Classification

Before persistence, classify the material as one or more of:

- `PRODUCT_DECISION`;
- `ENGINEERING_POLICY`;
- `PROJECT_CONTROL_RULE`;
- `SECURITY_OR_AUTHORITY_BOUNDARY`;
- `DEFERRED_RISK_REGISTER`;
- `MODEL_OR_AGENT_ROUTING`;
- `RESOURCE_OR_TOKEN_POLICY`;
- `PHASE_PLAN`;
- `POST_LAUNCH_PLANNING_INPUT`.

Place it in the narrowest existing versioned document. Create a new document only when no coherent accepted owner exists.

## 4. Persistence workflow

```text
accepted user ruling
→ classify
→ inspect current merged authority and active Draft governance PRs
→ update the correct versioned document
→ update governance/PROJECT_RULES_INDEX.md
→ update AGENTS.md when startup reading changes
→ create documentation-only branch
→ open Draft PR
→ independent read-only documentation Review
→ wait for a safe merge point
→ user merge authorization
→ merge to main
→ post-merge verification
→ main version becomes canonical
```

Direct commits to `main`, force-push, auto-merge, and hidden local-only rule replacement are prohibited.

## 5. Draft PR authority

A clearly identified active governance Draft PR may be used as a shared pending source before merge when all of the following are true:

- the PR is documentation/governance only;
- it does not mutate product runtime or trading authority;
- its base, head, and scope are explicit;
- all windows are told that it is pending rather than merged authority;
- live `main` and machine-enforced governance continue to control executable actions;
- conflicts are returned to the owning authority window.

A Draft PR is not authority to Mark Ready, merge, start runtime, access cloud resources, or change product scope.

## 6. Safe merge point

A governance consolidation is at a safe merge point only when merging it will not invalidate or force unnecessary rework in an active exact-base critical path.

Project Control must verify at least:

- active code task and PR state;
- current `main` SHA;
- whether an active unpublished or published task is exact-base bound;
- whether the governance diff overlaps active changed files;
- whether any machine-enforced governance/schema/test updates are required;
- exact-head CI and Review requirements for the governance PR;
- whether stale Draft PRs will be superseded or reconciled.

If merge would create avoidable base drift, keep the governance PR Draft and notify the user when the safe point is reached.

## 7. Reminder requirement

When the user asks to be reminded at the safe merge point, create a condition-based monitor tied to the exact governance PR and repository state.

The notification must occur only when the condition is actually met. It must identify:

- the governance PR;
- current `main`;
- the active First Launch critical-path state;
- why the merge is now safe;
- any Review or CI still required;
- the exact user authority requested.

## 8. Index and startup contract

Every persistent governance PR must update `governance/PROJECT_RULES_INDEX.md` when it adds, replaces, or changes a required document.

`AGENTS.md` must direct every project window to read:

1. `AGENTS.md`;
2. `governance/PROJECT_RULES_INDEX.md`;
3. documents marked `REQUIRED` for the current phase;
4. current GitHub/CI state.

A successor Engineering Optimization or Product Planning window must not rely on the previous chat window as its sole inheritance mechanism.

## 9. Supersession

A rule is superseded only when the new document:

- names the old document or PR;
- identifies the exact accepted content retained;
- identifies the content changed or rejected;
- states the effective point;
- updates the central index;
- preserves relevant historical evidence.

Old Draft PRs must not remain competing authorities indefinitely. After accepted content is migrated, they must be closed or explicitly marked superseded at an authorized safe point.

## 10. No-silent-loss rule

Any known work or risk that is removed from the current critical path but has V0/mainline, security, reliability, data, trading-closure, or maintainability value must be added to the persistent deferred register before exclusion.

Required fields:

- stable ID;
- source;
- reason deferred;
- risk if never completed;
- activation trigger;
- dependencies;
- owner authority;
- acceptance criteria;
- final disposition.

`UNRECORDED_KNOWN_DEFERRED_ITEMS` must be zero at phase closeout.

## 11. Sensitive information prohibition

Never persist the following in governance documents:

- credentials or secrets;
- private keys or seed phrases;
- account identifiers not already intentionally public;
- webhook secret values;
- real authorization headers;
- raw private market/account data;
- databases or logs;
- sensitive host IPs or access details;
- local personal filesystem details when a repository-relative abstraction is sufficient.

## 12. User and authority boundaries

Persistence does not itself authorize:

- implementation;
- Mark Ready or merge;
- runtime or service start;
- AWS or paid-resource use;
- credentials;
- account access;
- signing or nonce management;
- exchange writes;
- order mutation;
- autonomous trading.

Those remain separate explicit authority gates.

## 13. Completion report

Every persistence action must report:

```text
CLASSIFICATION:
CANONICAL_FILES:
INDEX_UPDATED:
AGENTS_UPDATED:
BRANCH:
COMMIT_OR_HEAD:
DRAFT_PR:
REVIEW_STATUS:
SAFE_MERGE_POINT:
CURRENT_AUTHORITY:
SUPERSEDED_INPUTS:
UNRECORDED_KNOWN_ITEMS:
NEXT_ACTION:
```

No persistence action may claim completion when the material remains only in chat or an unshared local file.