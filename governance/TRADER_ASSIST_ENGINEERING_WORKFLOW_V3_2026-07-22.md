# Trader Assist V0 — Engineering Workflow V3

**Status:** FROZEN  
**Effective date:** 2026-07-22  
**Project:** `TRADER_ASSIST_V0_FIRST_LAUNCH_R3`  
**Repository:** `woshixiong/trader-assist-v0`  
**Governing protocol:** `TRADER_ASSIST_AUTONOMOUS_STAGE_CONTROL_PROTOCOL_V2`

## 1. Governing outcome

```text
ONE COHERENT STAGE OBJECTIVE
→ ONE PRIMARY WRITER EXECUTES CONTINUOUSLY
→ EXACT-HEAD PARALLEL VERIFICATION
→ INDEPENDENT HIGH-REASONING CHATGPT REVIEW
→ AT MOST ONE NORMAL CONSOLIDATED REPAIR
→ HUMAN RETURNS ONLY AT MATERIAL AUTHORITY GATES
```

The user must not be used as a routine message bus between Agents.

## 2. Fixed authority separation

### Product Function and Priority Authority

Separate product window. Owns product scope, priority, acceptance criteria and deferrals.

### Engineering Optimization Authority

Separate ordinary ChatGPT GPT-5.6 Sol window. Owns architecture, stage design, largest safe task granularity, Writer/model/harness assignment, allowlists, commit budgets, engineering exceptions, escalation boundaries, Review classification and process optimization. It does not act as daily Project Control.

### Project Control Authority

Preferred after direct guarded activation: `TRAE IDE SOLO`.
Fallback: dedicated ordinary ChatGPT Project Control window.

Project Control executes approved stages, verifies mutable state, routes Writer and Reviewers, consolidates evidence, controls authorized repair and stops at user gates. It must not redefine product or engineering authority.

### User Authority

The user retains explicit control over execution-mode switch, stage activation, Mark Ready, merge, runtime, smoke, AWS or paid resources, and account/trading authority.

## 3. Dual execution modes

The user is the sole mode-switch authority. A switch takes effect only at the next safe stage boundary.

### 3.1 CODEX_PRIMARY

Activation phrase:

```text
EXECUTION_MODE_SWITCH:
CODEX_PRIMARY

EFFECTIVE_FROM:
NEXT_SAFE_STAGE_BOUNDARY
```

Assignment:

```text
PRIMARY_WRITER:
Codex

CURRENT_INTERACTIVE_INTERFACE:
Codex desktop APP

AUTOMATED_INTERFACE_WHEN_READY:
Codex CLI

PROGRAMMATIC_INTERFACE_LATER:
Codex SDK

DEEPSEEK_V4_PRO:
Fallback Writer

GLM_5_2:
Auxiliary or fallback Operations Reviewer
```

Codex CLI is not required before using Codex as the primary Writer. Global auto-commit, auto-push, auto-merge and unrestricted network access remain disabled. Write, commit and push authority are granted only by the current stage bundle.

### 3.2 IDE_SOLO_PRIMARY

Activation phrase:

```text
EXECUTION_MODE_SWITCH:
IDE_SOLO_PRIMARY

EFFECTIVE_FROM:
NEXT_SAFE_STAGE_BOUNDARY
```

Assignment:

```text
PROJECT_CONTROL:
TRAE IDE SOLO

PRIMARY_WRITER:
DeepSeek V4 Pro

OPERATIONS_REVIEW:
GLM-5.2 / STRICT_READ_ONLY

CODEX:
Reserved, unavailable or fallback as explicitly assigned
```

No separate broad capability pilot is required. TRAE desktop and IDE SOLO are treated as the same harness/model family for DeepSeek V4 Pro and GLM-5.2. A short activation preflight remains mandatory to confirm current configuration and authority, not to re-evaluate model quality.

## 4. Independent ChatGPT Review layer

High-reasoning Reviews should normally use ordinary ChatGPT GPT-5.6 Sol windows because they preserve Codex execution quota, provide independent reasoning and reduce Writer self-review bias.

Normal engineering stage:

```text
OPERATIONS REVIEW:
Independent Codex read-only task or GLM-5.2

FINAL REVIEW:
One new ordinary ChatGPT GPT-5.6 Sol window
```

Security, credential, authority, runtime, cloud or trading boundary stage:

```text
SECURITY REVIEW:
One independent ordinary ChatGPT GPT-5.6 Sol window

FINAL REVIEW:
A different independent ordinary ChatGPT GPT-5.6 Sol window
```

Where possible, Reviews run in parallel after an exact head exists. The user copies one complete Review Packet per stage, not one prompt per finding or file.

## 5. Stage granularity

```text
ONE STAGE
=
ONE COHERENT ENGINEERING OBJECTIVE
+ ONE PRIMARY WRITER
+ ONE EXACT FILE/SOURCE ALLOWLIST
+ ONE COMMIT BUDGET
+ ONE EXACT HEAD
+ PARALLEL VERIFICATION
+ AT MOST ONE NORMAL CONSOLIDATED REPAIR
```

Split a stage when it crosses product rulings, runtime authority, local versus AWS authority, public read-only versus account/trading-write authority, incompatible Writer ownership, or an unreviewable allowlist/diff boundary. Do not split merely by file, function, test, command or individual finding.

## 6. Standard stage lifecycle

### Block A — Stage-sized implementation

Project Control issues one complete `STAGE_EXECUTION_BUNDLE` containing exact task, repository, PR, base, branch, expected head, Worktree, Python environment, Writer/model, allowlists, commit budget, implementation objective, local gates, CI, repair authority, safe-stop conditions and next human gate.

### Block B — Exact-head parallel verification

After an exact head exists, run exact-head CI, Operations Review and Security Review where applicable concurrently when possible.

### Block C — Independent high-reasoning Review

Project Control prepares one complete Review Packet with exact state, ordered commits, complete diff, rulings, Writer report, local gates, CI and prior Review reports.

### Block D — Consolidated repair

All in-scope blocking findings are consolidated into one repair packet for the same Writer. One finding per prompt, one file per prompt and serial Reviewer-specific repairs are prohibited. A second repair round requires a new engineering exception.

### Block E — Final authority gates

After Reviews and CI pass: user authorizes Mark Ready, separately authorizes merge, and Project Control verifies post-merge CI. Runtime, smoke, AWS and account/trading authority remain separate stages.

## 7. Human interaction budget

Normal target: stage activation, one complete Review Packet handoff, and final authority decision. A fourth interaction is allowed for one consolidated repair or a genuine escalation.

## 8. Worktree and environment policy

```text
REUSE VALID CLEAN AUTHORIZED WORKTREE
REUSE VALID PYTHON ENVIRONMENT
```

Changing model, Agent, harness or chat window is not a reason to rebuild. Recreate only when missing, wrong, dirty, in-use, invalid or insufficiently isolated. A missing Worktree must be created with `git worktree add`, never ordinary `mkdir`.

## 9. TRAE and Codex transport rules

TRAE and Codex are desktop applications unless a separately installed CLI is explicitly used. Do not instruct the user to launch desktop TRAE or desktop Codex from Terminal.

```text
TRAE_MAXIMUM_DIRECT_INPUT:
18,000 characters

TRAE_PROMPT_FILE_MODE:
Mandatory above 18,000 characters
```

## 10. IDE SOLO direct guarded activation

The former broad capability pilot is retired.

Required activation sequence:

1. reach a safe stage boundary;
2. install project Skills and Commands;
3. run the read-only Direct Activation Preflight;
4. confirm project context, model assignments and blocked authorities;
5. activate IDE SOLO as Project Control;
6. start the next stage only after user activation.

If exact model selection, project context, Worktree control or role isolation is absent at activation, `SAFE_STOP` and use the dedicated ordinary ChatGPT Project Control fallback.

## 11. Absolute authority boundaries

Without separate current authorization, do not Mark Ready, merge, start runtime/services, execute smoke, access AWS/paid resources, access credentials/private keys/wallet secrets, sign, manage nonce, mutate orders, write to an exchange or enable unrestricted automated trading.

## 12. Engineering escalation boundaries

Return to Engineering Optimization when allowlists expand, dependency/lockfile/workflow changes are required, commit authority is exhausted, Writer substitution is required, product scope changes, an unresolved Blocker/High cannot be repaired in scope, or runtime/cloud/trading authority is requested.

## 13. Persistent control state

```text
/Users/minmin/trader-assist-v0-control/
├── AGENTS.md
├── PROJECT_STATE.json
├── ACTIVE_STAGE.yaml
├── governance/
├── agent-packets/
├── results/
├── .agents/skills/
└── .trae/commands/
```

GitHub remains authoritative for mutable repository and CI state. Chat history is not the sole source of truth. No secrets may be stored in the control directory.

## 14. Current transition rule

PR #40 must complete through its existing closeout process without a workflow switch.

After PR #40 merge and post-merge CI:

1. import TRAE Skills and Commands;
2. run Direct Activation Preflight;
3. activate IDE SOLO Project Control;
4. select `CODEX_PRIMARY` or `IDE_SOLO_PRIMARY` based on the user's explicit instruction;
5. start the next approved stage.

## 15. Frozen ruling

```text
ENGINEERING_PROCESS_OPTIMIZATION:
FROZEN

WORKFLOW_ARCHITECTURE:
DUAL_EXECUTION_MODE_WITH_INDEPENDENT_CHATGPT_REVIEW

MODE_SWITCH_AUTHORITY:
USER_ONLY

CODEX_PRIMARY_MODE:
APPROVED_WHEN_USER_DECLARED

IDE_SOLO_PRIMARY_MODE:
APPROVED_WHEN_USER_DECLARED

TRAE_SOLO_BROAD_CAPABILITY_PILOT:
RETIRED

TRAE_SOLO_DIRECT_ACTIVATION_PREFLIGHT:
REQUIRED

HIGH_REASONING_REVIEW:
ORDINARY_CHATGPT_WINDOWS_PREFERRED

REVIEW_FREQUENCY:
ONE_EXACT_HEAD_BOUNDARY_PER_STAGE

STAGE_GRANULARITY:
LARGEST_SAFE_COHERENT_ENGINEERING_MODULE

NORMAL_REPAIR_LIMIT:
ONE_CONSOLIDATED_ROUND

WORKTREE_AND_ENVIRONMENT:
REUSE_BY_DEFAULT
```
