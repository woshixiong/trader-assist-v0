# TRAE IDE SOLO — Direct Activation Preflight

**Mode:** STRICT READ-ONLY  
**Purpose:** Validate current configuration and authority before direct activation.  
**This is not a model-quality or broad capability pilot.**

## Preconditions

- Project: `/Users/minmin/trader-assist-v0-control/`
- `AGENTS.md`: ON
- Project rule `Trader Assist Authority Gate`: ON
- Memory: ON
- `CLAUDE.md`: OFF
- Auto Mode: OFF
- Hooks: OFF
- Project MCP: OFF
- Do not modify PR #40 or any repository

## Prompt

```text
ROLE:
TRAE_IDE_SOLO_PROJECT_CONTROL_ACTIVATION_AUDITOR

MODE:
STRICT_READ_ONLY_DIRECT_ACTIVATION_PREFLIGHT

PROJECT:
TRADER_ASSIST_V0_FIRST_LAUNCH_R3

CONTROL_DIRECTORY:
/Users/minmin/trader-assist-v0-control

Read completely:

1. /Users/minmin/trader-assist-v0-control/AGENTS.md
2. /Users/minmin/trader-assist-v0-control/PROJECT_STATE.json
3. /Users/minmin/trader-assist-v0-control/ACTIVE_STAGE.yaml
4. the active project rule named "Trader Assist Authority Gate"
5. /Users/minmin/trader-assist-v0-control/governance/TRADER_ASSIST_ENGINEERING_WORKFLOW_V3_2026-07-22.md

This is a read-only configuration and authority check.
Do not modify any file.
Do not open or modify an implementation Worktree.
Do not run tests.
Do not create a branch, commit or push.
Do not mutate GitHub.
Do not start runtime, smoke, services, AWS or paid resources.
Do not access credentials, wallets, signing, nonce or exchange authority.
Do not enable Auto Mode, Hooks or MCP.

Verify:

A. exact project directory, AGENTS.md, project rule, ACTIVE_STAGE and current Project Control mode;
B. frozen dual execution workflow and user-only mode switch;
C. IDE SOLO assignment: Project Control, DeepSeek V4 Pro Writer, GLM-5.2 strict read-only Operations Reviewer;
D. Codex assignment: primary Writer only after user declares CODEX_PRIMARY; Desktop APP usable immediately; CLI/SDK later;
E. ChatGPT GPT-5.6 Sol preferred for high-reasoning Security and Final Review;
F. all material authorities blocked;
G. Skills and Commands installation status.

Return exactly:

TRAE_IDE_SOLO_DIRECT_ACTIVATION_PREFLIGHT:
PASS / SAFE_STOP

PROJECT_DIRECTORY:
<absolute path>

AGENTS_MD:
ACTIVE / MISSING

PROJECT_RULE:
ACTIVE / MISSING

ACTIVE_STAGE:
<value>

CURRENT_PROJECT_CONTROL_MODE:
<value>

GOVERNING_WORKFLOW:
<value>

MODE_SWITCH_AUTHORITY:
<value>

IDE_SOLO_PROJECT_CONTROL:
ACKNOWLEDGED / NOT_ACKNOWLEDGED

DEEPSEEK_V4_PRO_WRITER:
ACKNOWLEDGED / NOT_ACKNOWLEDGED

GLM_5_2_OPERATIONS_REVIEW:
ACKNOWLEDGED / NOT_ACKNOWLEDGED

CHATGPT_HIGH_REASONING_REVIEW:
ACKNOWLEDGED / NOT_ACKNOWLEDGED

CODEX_PRIMARY_RULE:
ACKNOWLEDGED / NOT_ACKNOWLEDGED

PROJECT_SKILLS:
INSTALLED / PENDING_INSTALL / UNKNOWN

PROJECT_COMMANDS:
INSTALLED / PENDING_INSTALL / UNKNOWN

REPOSITORY_WRITE_AUTHORITY:
BLOCKED / AUTHORIZED

MARK_READY:
BLOCKED / AUTHORIZED

MERGE:
BLOCKED / AUTHORIZED

RUNTIME:
BLOCKED / AUTHORIZED

SMOKE:
BLOCKED / AUTHORIZED

AWS_OR_PAID_RESOURCES:
BLOCKED / AUTHORIZED

ACCOUNT_OR_TRADING_AUTHORITY:
BLOCKED / AUTHORIZED

FILES_MODIFIED:
NONE

NEXT_ACTION:
WAIT_FOR_PR40_SAFE_STAGE_BOUNDARY_AND_SKILLS_COMMANDS_INSTALL
```

## PASS criteria

PASS requires correct control directory, AGENTS.md and rule active, ACTIVE_STAGE inactive, frozen assignments acknowledged, all authorities blocked, and no files modified. Skills and Commands may be `PENDING_INSTALL`; they become mandatory before the first active IDE SOLO stage.
