# Trader Assist Project Rules Index

**Status:** DRAFT GOVERNANCE CONSOLIDATION  
**Version:** V1  
**Effective only after:** independent documentation review and merge to `main`  
**Repository:** `woshixiong/trader-assist-v0`

## 1. Purpose

This file is the single startup index for ordinary ChatGPT Product Planning, Engineering Optimization, Project Control, Writer, Reviewer, Codex, TRAE, and OpenCode contexts.

GitHub is the canonical shared source of truth for persistent project decisions. Chat history and local control files are not sufficient permanent records.

Every project window must begin by reading:

1. `AGENTS.md`;
2. this index;
3. every document marked `REQUIRED` for the current phase;
4. the current GitHub and CI state relevant to the active task.

Mutable repository, pull-request, branch, commit, and CI state must always be reverified. Narrative in an old PR body never overrides current GitHub objects.

## 2. Authority separation

| Authority | Owns | Must not own |
|---|---|---|
| Product Function and Priority | Product scope, user value, feature selection, priority, deferral, product acceptance, post-launch direction | Engineering decomposition, Writer routing, repository mutation |
| Engineering Optimization | Architecture, largest safe task granularity, Agent/model/harness routing, allowlists, commit budgets, tests, Review design, token/resource optimization | Product scope or daily Project Control |
| Project Control | Live-state verification, task activation, branch/worktree/packet routing, Writer/Reviewer coordination, PR/CI/finalization execution | Product or engineering-policy redefinition |
| User | Mode switch, stage activation, material exceptions, Mark Ready, merge, runtime, smoke, paid cloud, account/trading authority | Routine Agent message transport |

Binding flow:

```text
Product Function and Priority
→ Engineering Optimization
→ Project Control
→ Writer / Reviewers
→ Project Control classification
→ product findings return to Product Authority
→ engineering-process findings return to Engineering Optimization
```

## 3. Current three-phase planning model

`REQUIRED`:

- `governance/PROJECT_THREE_PHASE_PLAN_AND_DEFERRED_REGISTER_V1.md`

The project must always distinguish:

1. work required before First Launch accepted real operation;
2. deferred and residual work preserved for V0/mainline replanning;
3. post-First-Launch evidence, product planning, V0 implementation, and mainline work.

No item may disappear merely because it is not a current First Launch blocker.

## 4. Engineering and Agent rules

`REQUIRED` for Engineering Optimization, Project Control, Writer, and Reviewer contexts:

- `governance/TRADER_ASSIST_ENGINEERING_WORKFLOW_V3_2026-07-22.md`;
- `governance/TRADER_ASSIST_ENGINEERING_OPTIMIZATION_SUCCESSOR_HANDOFF_V2_2026-07-22.md`;
- `governance/ENGINEERING_WORKFLOW_MODEL_ROUTING_AND_RESOURCE_POLICY_V1.md`.

Workflow V3 supplies the persistent workflow architecture. Its date-bound transition narrative, including the former PR #40 transition section, is historical after that transition completed. Current task, next gate, active PR, branch, base/head, mode, and authority state must come from live GitHub objects, current merged Project State, and the current accepted stage packet—not from a stale transition paragraph.

Additional merged references:

- `governance/FASTSAFE_V1_MASTER_CONTROL_CONTRACT.md`;
- `governance/ENGINEERING_AUTOMATION_TRACK_V1.md`;
- `governance/TRAE_IDE_SOLO_DIRECT_ACTIVATION_PREFLIGHT_2026-07-22.md`.

Historical Draft inputs requiring reconciliation rather than blind reuse:

- PR #33 — engineering optimization, multi-Agent workflow, and three-window constitution;
- PR #35 — First Launch product baseline, deferred capability registry, and post-launch decision gate.

After this consolidation is accepted, PR #33 and PR #35 must be reviewed for supersession or bounded content migration. They must not remain competing authorities indefinitely.

## 5. GitHub persistence rule

`REQUIRED` for all authority windows:

- `governance/GITHUB_CANONICAL_RULE_PERSISTENCE_POLICY_V1.md`.

User phrases such as the following are persistence requests, not chat-memory requests:

- “同步固定对齐”;
- “固定下来”;
- “定规则”;
- “固定规则”;
- “以后都按这个执行”;
- “让其他窗口继承”;
- equivalent language expressing durable cross-window authority.

Persistent decisions must be written to versioned GitHub governance documents, indexed here, independently reviewed, and merged at a safe point. Direct commits to `main` remain prohibited.

## 6. V0 product-planning entry

`REQUIRED` when First Launch has reached accepted real operation and the user begins V0 planning:

- `governance/V0_PRE_DEVELOPMENT_PRODUCT_PLANNING_INTAKE_V1.md`;
- `governance/PROJECT_THREE_PHASE_PLAN_AND_DEFERRED_REGISTER_V1.md`;
- First Launch final baseline and residual report;
- Workstream A Minimum V0 transition package;
- Gate B real-operation evidence;
- prior V0 plans and current mainline architecture.

The Product Function and Priority window must produce `V0_PRODUCT_SCOPE_DECISION_V1` before Engineering Optimization may create V0 implementation packages.

## 7. Precedence and conflict handling

Precedence order:

1. current explicit user ruling;
2. current merged machine-enforced governance and safety authority;
3. current merged versioned governance documents indexed here;
4. accepted exact-head task contract and Review evidence;
5. active identified governance Draft PR awaiting a safe merge point;
6. historical merged documents;
7. historical Draft PRs and external design inputs;
8. chat summaries and local cache copies.

A later document supersedes an earlier document only when it explicitly names the earlier authority and states the bounded supersession. Silence is not supersession.

When two accepted sources conflict:

- stop affected activation;
- record the conflict;
- return it to the owning authority window;
- do not resolve it by Agent inference.

## 8. Security and authority invariants

Unless separately authorized and reviewed, no governance document grants:

- credentials, wallets, private keys, signing, or nonce authority;
- account access;
- Testnet or Mainnet exchange writes;
- order submission, cancellation, or automatic SL/TP;
- runtime or service start;
- AWS or paid-resource activation;
- unrestricted network access;
- autonomous trading or automatic production-rule mutation.

Secrets, account identifiers, sensitive host information, databases, raw payloads, and transient logs must never be stored in governance documents.

## 9. Status vocabulary

Deferred items use only:

- `DEFERRED_PRESERVED`;
- `READY_FOR_PLANNING`;
- `PLANNED`;
- `ACTIVE`;
- `ACCEPTED`;
- `REJECTED_WITH_REASON`;
- `SUPERSEDED_WITH_REFERENCE`.

A persistent item may not be removed without an explicit final disposition.

## 10. Current Draft-PR boundary

This index does not itself authorize First Launch code publication, Mark Ready, merge, deployment, runtime, smoke, V0 implementation, account access, or exchange writes.

Until this governance consolidation is merged, ordinary windows may read its Draft PR as an identified shared planning source, but merged `main` and live GitHub state continue to control executable authority.