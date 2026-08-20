# Trader Assist / Trade OS — Codex CLI Engineering Usage Profile V1

**Status:** SPECIALIZED GOVERNANCE PROPOSAL  
**Effective date:** 2026-08-20  
**Repository:** `woshixiong/trader-assist-v0`  
**Executor:** `CODEX_CLI`  
**Model family:** current Codex-supported OpenAI model explicitly selected per bounded task or coherent stage by the user/L1.

This file is the **version-independent Codex CLI workflow core**. Current model-specific guidance lives at the stable path:

`governance/CODEX_CURRENT_MODEL_PROFILE.md`

A newer Codex/OpenAI model should normally update only that current-model profile. Do not rewrite this workflow core or the three-executor switching architecture merely because the model name changes.

This profile specializes the Unified Engineering Governance and the task-level executor-routing rule. It grants no Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, signing/wallet, exchange-write, order-submission/cancellation or trading authority.

---

## 1. Stable architecture — executor core separate from current model

```text
LAYER A — EXECUTION-CLASS + L2 EXECUTOR ROUTING
ENGINEERING_EXECUTOR_SELECTION_AND_TOOL_PROFILE_ROUTING...
stable GPT-control-first routing plus three peer L2 coding executors

LAYER B — VERSION-INDEPENDENT CODEX CLI CORE
THIS FILE
stable execution mode, session identity, prompt/context discipline,
permissions, evidence transport, validation and token-efficiency rules

LAYER C — CURRENT CODEX MODEL SNAPSHOT / MATRIX
governance/CODEX_CURRENT_MODEL_PROFILE.md
refreshable current models, reasoning/service-tier guidance and current factual limits
```

The exact Codex model and reasoning effort are task-level state, not architecture.

Before a material Codex Writer stage, Engineering freezes:

```text
CURRENT_USER_SELECTED_EXECUTOR=CODEX_CLI
CURRENT_USER_SELECTED_MODEL=
CURRENT_REASONING_EFFORT=
CURRENT_SERVICE_TIER=
CURRENT_CODEX_MODEL_PROFILE=governance/CODEX_CURRENT_MODEL_PROFILE.md
MODEL_PROFILE_LAST_VERIFIED_AT=
MODEL_SPECIFIC_ASSUMPTIONS=NONE_UNLESS_VERIFIED
```

A model upgrade alone does not change worktree rules, independent review, publication routing, user-retained gates or the complete Task Packet contract.

---

## 2. Independent position

Codex should be used where local codebase semantic inspection, mutation, debugging or code-test iteration provides real value. It should not be paid/agentic transport for deterministic publication or GitHub operations that Engineering Control can perform directly or encode in a mechanical Terminal block.

For actual Codex work, the principal efficiency risks are:

1. using a stronger model/reasoning tier than the task needs;
2. repeatedly injecting large governance/history instead of reading canonical repository authority;
3. opening a fresh session when coherent trusted context should be resumed, or resuming stale context merely to chase cache hits;
4. varying stable prompt/tool/config prefixes and losing reusable context;
5. using interactive or orchestration surfaces when native `codex exec` already satisfies the bounded workflow;
6. enabling unnecessary tools, network, plugins, Fast mode or broad permissions.

The default solution is:

```text
GPT-CONTROL-FIRST EXECUTION-CLASS ROUTING
+ PROVIDER-NATIVE CODEX EXEC FOR REAL CODING WORK
+ VERSION-INDEPENDENT CLI CORE
+ REFRESHABLE CURRENT-MODEL PROFILE
+ ONE COMPLETE BOUNDED TASK PACKET
+ SMALL STABLE AGENTS / REPOSITORY AUTHORITY
+ EXACT LOCAL CONTEXT DISCOVERY BY CODEX
+ EXPLICIT TASK-LOCAL MODEL / REASONING / SANDBOX
+ EXACT SESSION RESUME ONLY INSIDE ONE TRUSTWORTHY STAGE
+ JSONL PASSIVE USAGE/EVIDENCE CAPTURE
+ DETERMINISTIC MECHANICS OUTSIDE MODEL TOKENS
```

Optimize accepted useful work per total model/credit/rework/review/human-relay cost, not minimum prompt characters in isolation.

---

## 3. First-party evidence basis

External research was performed after the independent pass. Current first-party OpenAI/Codex material checked includes:

- `https://developers.openai.com/codex/noninteractive`
- `https://developers.openai.com/codex/cli/reference`
- `https://developers.openai.com/codex/config-reference`
- `https://developers.openai.com/codex/guides/agents-md`
- `https://developers.openai.com/codex/skills`
- `https://developers.openai.com/codex/speed`
- `https://developers.openai.com/api/docs/models`
- `https://developers.openai.com/api/docs/guides/latest-model`
- `https://developers.openai.com/api/docs/guides/prompt-caching`
- current OpenAI Codex/GPT-5.6 help-center availability/rate material.

Relevant current first-party facts support:

- `codex exec` as the native non-interactive mode for scripts, pipelines and CLI workflows;
- explicit `--model`, `--cd`, `--sandbox`, approval and per-invocation `-c key=value` overrides;
- exact `codex exec resume <SESSION_ID>` continuation;
- JSONL event output including `thread_id` and token usage including `cached_input_tokens`;
- `AGENTS.md` loading once per run/session with root-to-CWD layering and a 32 KiB default combined project-instruction ceiling;
- Skills progressive disclosure: metadata first, full `SKILL.md` only when used;
- prompt-cache reuse requiring exact stable prefixes and mutable content late;
- current GPT-5.6 model/reasoning/service-tier differences documented in the refreshable current-model profile.

The project uses these provider-native seams before adding SDK/App Server/MCP/custom orchestration.

---

## 4. Default execution surface

For bounded Engineering-Control-issued Codex Writer tasks:

```text
CODEX_DEFAULT_EXECUTION_MODE=codex exec
CODEX_INTERACTIVE_TUI=OPT_IN_FOR_HUMAN_PAIR_PROGRAMMING_OR_EXPLORATION
CODEX_SDK=FUTURE_REPLACEABLE_SEAM_ONLY_IF_CLI_BECOMES_INSUFFICIENT
CODEX_APP_SERVER_OR_MCP_ORCHESTRATION=NOT_CURRENT_DEFAULT
```

`codex exec` should be launched from the one-paste Terminal block and return control to the ordinary shell when complete.

Do not launch the TUI merely because Codex is the selected executor. Use interactive mode only when live human steering itself is the objective.

---

## 5. Task-local configuration beats hidden global state

Engineering Control freezes the effective settings in the generated Terminal block rather than relying on remembered user defaults.

For normal project Writer runs, explicitly encode where applicable:

```text
MODEL
REASONING_EFFORT
WORKING_DIRECTORY
SANDBOX
APPROVAL_POLICY
SERVICE_TIER
NETWORK/EXTRA-WRITE NEED IF ANY
```

Current CLI supports task-local `--model/-m`, `--cd/-C`, `--sandbox/-s`, `--ask-for-approval/-a`, and `-c key=value` overrides. Explicit launch choices take precedence over ordinary model/config defaults.

Default principle:

```text
DO_NOT_MUTATE_GLOBAL_~/.codex/config.toml_FOR_ONE_PROJECT_TASK=YES
TASK_LOCAL_OVERRIDES=YES
```

When current CLI supports it and the task does not intentionally rely on verified user-level Codex configuration, Engineering may use `--ignore-user-config` to remove irrelevant hidden user config while preserving authentication. If a task requires a user-level MCP/plugin/config capability, do not ignore it blindly; freeze the dependency explicitly and verify it before execution.

Use `--strict-config` when relying on configuration keys whose silent rejection would invalidate the frozen task.

---

## 6. Permission and approval policy

Execution mode never grants authority.

Normal non-interactive local Writer baseline:

```text
SANDBOX=workspace-write WHEN WRITES ARE REQUIRED
SANDBOX=read-only FOR READ-ONLY CODE INSPECTION/REVIEW WHEN SUFFICIENT
APPROVAL_POLICY=never FOR PRE-FROZEN NONINTERACTIVE TASKS
DANGER_FULL_ACCESS=NOT_DEFAULT
YOLO=PROHIBITED_AS_NORMAL_PROJECT_ROUTE
EXTRA_WRITABLE_DIRS=USE --add-dir ONLY WHEN EXPLICITLY REQUIRED
NETWORK=OFF/UNNEEDED BY DEFAULT; FREEZE EXPLICITLY WHEN REQUIRED
```

If an operation exceeds the frozen sandbox or authority, Codex must fail/stop and return to L1. Do not convert a permission failure into silent `danger-full-access` or a broader scope.

`approval_policy=never` prevents unattended runs from waiting for ad-hoc command approval; it does not authorize Mark Ready, merge, deployment, runtime, cloud, credentials, signing, exchange write or trading.

---

## 7. One complete Task Packet — stable prefix, mutable tail

For material Codex coding work, Engineering generates one complete packet in this semantic order:

```text
A. STABLE CONTROL PREFIX
   ROLE / MODE
   PROJECT
   EXECUTOR=CODEX_CLI
   canonical GitHub authority pointers
   Writer != Independent Reviewer
   no silent redesign / scope expansion
   retained user authority boundary
   output/evidence contract shape

B. CURRENT TASK CONTRACT
   TASK_ID
   selected model / reasoning / service tier
   exact repository/worktree/branch
   live main/base/head/artifact identities
   objective / accepted root cause
   allowed files and prohibited scope
   must-preserve authorities/semantics
   attack / negative cases
   exact validation commands
   SAFE_STOP conditions
   repair stage/budget

C. MUTABLE EVIDENCE TAIL
   current hashes
   current CI/run IDs
   one-off artifact/log paths
   timestamps/current blocker IDs
```

Keep stable headings/order/text byte-stable where practical. Put volatile facts late.

Do not repaste the full project history, old chats, old PR bodies or full governance corpus when the current `AGENTS.md` and canonical repository paths are sufficient.

Prompt brevity never permits removal of scope, exact identities, attack cases, tests, stop conditions or authority gates.

---

## 8. Repository context discipline

Codex has local repository access when selected; use it rather than copying source files into the prompt.

Prefer Task Packets that identify exact paths, symbols, artifact fingerprints and accepted boundaries, then let Codex inspect the local workspace under the frozen scope.

```text
EXACT FILE / SYMBOL / ARTIFACT
→ SMALL RELATED DIRECTORY
→ BOUNDED REPOSITORY SEARCH
→ BROADER WORKSPACE ONLY WHEN DISCOVERY IS ACTUALLY REQUIRED
```

Keep root `AGENTS.md` small and stable. Detailed specialized rules belong in GitHub-resident profiles rather than an oversized always-loaded instruction file.

Do not create new Codex Skills merely to reproduce static governance. Skills are appropriate only after repeated real tasks show a reusable workflow that benefits from provider-native progressive disclosure. No speculative skill/plugin/MCP work is required by this profile.

---

## 9. Session identity and continuation

A CLI process ending does not mean its persisted Codex thread must be discarded.

### Resume exact

Use:

```text
codex exec resume <EXACT_SESSION_ID> <follow-up-task>
```

only when all are true:

```text
SAME_PRIMARY_WRITER=YES
SAME_TASK=YES
SAME_COHERENT_STAGE=YES
SAME_WORKTREE_ARTIFACT=YES
SAME_AUTHORITY=YES
SAME_OBJECTIVE=YES
CONTEXT_REMAINS_TRUSTWORTHY=YES
INDEPENDENCE_REQUIRED=NO
ACTIVE_WRITER_COLLISION=NO
```

A deterministic test/Git/CI check between Writer turns does not itself force a new session if all conditions remain true.

### New session

Start a new session when any is true:

- new bounded task;
- different Writer/Reviewer role;
- material stage or authority change;
- different worktree/artifact;
- clean-route adjudication after failed architecture;
- security/authority review;
- independent final review;
- stale/unrelated context or instruction drift becomes material.

### Never use contextual last-session identity as automation authority

`codex exec resume --last` is a valid human convenience but is prohibited as the project automation/default handoff identity. When continuation matters, capture and pass the exact session/thread ID.

Do not resume solely to chase cache hits. Correct context boundary dominates cache optimization.

---

## 10. JSONL evidence and Result Packet transport

For material or resumable Codex Writer runs, prefer:

```text
codex exec --json ...
```

Capture the JSONL stream in ephemeral/non-repository evidence storage. Do not commit raw Codex logs.

Mechanically retain when exposed:

```text
thread.started.thread_id
turn completion/failure
input_tokens
cached_input_tokens
output_tokens
reasoning_output_tokens
command/file-change status needed by the task
final agent result
elapsed_time
retry/rework count
```

`--output-last-message` is an optional convenience. `--output-schema` is appropriate when a downstream machine workflow genuinely needs stable final fields; it is not mandatory for every human-assisted task.

No additional model turn may be created merely to obtain telemetry.

---

## 11. Token and cache efficiency

Target total cost:

```text
INPUT + CACHED/UNCACHED COST + OUTPUT + REASONING + RETRIES + REWORK + REVIEW + HUMAN RELAY
```

Rules:

- stable project/tool/control prefix; mutable task/evidence tail;
- keep model, tool surface and permission shape stable through one coherent stage unless authority requires change;
- no repeated full governance/history;
- after accepted baseline, use accepted fingerprint + exact delta + relevant bypass/regression checks;
- deterministic shell/Git/test facts outside model tokens;
- no synthetic paid cache benchmark;
- no arbitrary cache-hit threshold;
- cache hit is optimization evidence, never correctness authority.

Current Codex JSONL exposes `cached_input_tokens`; capture it passively. Do not invent `cache_write_tokens`, prompt-cache keys or explicit breakpoints on the Codex CLI surface unless a later first-party CLI/config contract exposes them.

The underlying OpenAI API has additional GPT-5.6 cache controls, but API-only controls are not automatically Codex CLI controls.

Exact-session resume is permitted for coherent continuation, but the project does not assume RESUME is always cheaper than NEW. Compare real-task total token/cache/time/rework evidence over time.

---

## 12. Model/reasoning/service-tier selection

The current model matrix and current verified model-specific controls live only in:

`governance/CODEX_CURRENT_MODEL_PROFILE.md`

Durable rules:

1. Use the least expensive model/reasoning tier likely to complete the bounded task correctly in one pass.
2. Escalate capability because of task complexity/risk or observed insufficiency, not habit.
3. Do not silently change the user/L1-frozen model or reasoning effort mid-stage.
4. Fast/Priority service is latency policy, not intelligence. It is off by default when usage/credit efficiency is the objective and is enabled only for a real time-critical need.
5. Highest reasoning, Pro-like modes, Max/Ultra/subagent behavior are exceptional and require current surface verification plus an explicit L1 reason.
6. Model names/limits/pricing/availability belong in Layer C and are refreshed without rewriting this file by default.

---

## 13. Correct task size

Default unit:

```text
ONE_CODEX_WRITER_SESSION = ONE_COHERENT_BOUNDED_ENGINEERING_STAGE
```

A stage may include:

```text
identity/worktree preflight
→ bounded code inspection
→ implementation
→ in-scope test correction
→ focused tests
→ required regression/static gates
→ diff/scope/secret checks
→ Result Packet
```

Do not split one coherent stage into one prompt per file/test/lint finding merely to appear cautious; that increases duplicated context and human relay.

Do not combine unrelated architecture, implementation, publication and deployment into one Codex session. Publication is normally routed back to Engineering Control once the exact artifact is accepted.

---

## 14. Publication handoff

Codex is not the default publication operator.

When Codex finishes an implementation stage:

```text
FREEZE EXACT ARTIFACT / HEAD / DIRTY HASH
→ RETURN RESULT PACKET
→ INDEPENDENT REVIEW / REQUIRED GATES
→ ENGINEERING CONTROL ROUTES PUBLICATION SEPARATELY
```

If the accepted artifact only needs deterministic local commit/push, Engineering Control should normally issue a deterministic one-paste Terminal block without another Codex turn.

If the branch is already pushed and publication is GitHub-side (Draft PR/update/CI observation/review metadata, or Mark Ready/merge after separate explicit user authority), Engineering Control should use its GitHub capability directly when available.

If publication uncovers a failing gate that requires code judgment or edits, stop publication and create a new bounded L2 coding task; do not let a mechanical publication step silently become a repair stage.

---

## 15. Routes not selected by default

### Persistent interactive TUI

Useful for pair programming/exploration; not the normal bounded Writer transport.

### New Codex session for every turn

Simple but needlessly discards coherent trustworthy context. Use NEW at the actual task/stage/authority/independence boundary.

### Resume every turn for cache savings

Rejected. Stale context can cost more in rework than it saves in cached input.

### Codex SDK

Provider-native future seam if repeated automation needs exceed `codex exec --json`. Do not add an SDK dependency merely to reproduce CLI functionality.

### App Server / MCP / plugin orchestration

Not current project default. Add only after a measured requirement cannot be met by the narrower CLI seam.

### Fast mode as default

Rejected for efficiency-first work. Current service-tier economics belong in the refreshable model profile.

### Max/Ultra/subagents as default

Rejected. Use only after current-surface verification and explicit task-level need.

---

## 16. Attack / counterexample matrix

Every implementation packet must consider the applicable subset of:

- wrong repo/CWD or stale main/base/head;
- selected model differs from effective model;
- reasoning/service tier differs from frozen value;
- hidden user config changes tool/permission/model behavior;
- same session ID points to different worktree/authority;
- `--last` resumes the wrong task;
- stale session context biases a repair/review;
- prompt/history grows while relevant context shrinks in salience;
- stable prefix is accidentally changed every turn and cache reuse collapses;
- extra plugin/MCP/tool surface adds irrelevant context or permission;
- Fast mode consumes extra credits without a latency requirement;
- broad sandbox/network is enabled merely to avoid a failure;
- Writer PASS is mistaken for independent acceptance;
- publication is needlessly assigned to Codex;
- publication failure actually requires a new coding repair;
- retained user release/runtime/account/exchange gate is crossed.

Fail closed on material mismatch.

---

## 17. Current one-paste Writer shape

Engineering owns the exact generated script; users should not manually assemble flags or prompts. A normal new Codex Writer invocation conceptually freezes:

```text
codex exec
  --cd <EXACT_ISOLATED_WORKTREE>
  --model <L1_FROZEN_MODEL>
  --sandbox workspace-write
  --ask-for-approval never
  -c model_reasoning_effort='<L1_FROZEN_EFFORT>'
  --json
  <ONE_COMPLETE_TASK_PACKET>
```

Add `--ignore-user-config`, `--strict-config`, `--add-dir`, network, service-tier or other overrides only according to the verified current CLI surface and the task contract. Do not cargo-cult flags.

The actual Terminal block must also perform deterministic repo/SHA/worktree/authority preflight before invoking Codex and preserve the project one-paste rule.

---

## 18. Current decision

```text
CODEX_VERSION_INDEPENDENT_CORE=THIS_FILE
CODEX_CURRENT_MODEL_PROFILE=governance/CODEX_CURRENT_MODEL_PROFILE.md
DEFAULT_EXECUTION_SURFACE=codex exec
DEFAULT_INTERACTIVE_TUI=NO
TASK_LOCAL_MODEL_AND_REASONING_FREEZE=YES
DEFAULT_WRITER_SANDBOX=workspace-write_WHEN_WRITE_REQUIRED
DEFAULT_NONINTERACTIVE_APPROVAL=never
EXACT_SESSION_RESUME_ONLY=YES
RESUME_LAST_AS_PROJECT_AUTOMATION=NO
JSONL_FOR_MATERIAL_OR_RESUMABLE_WRITER=YES
STABLE_PREFIX_MUTABLE_TAIL=YES
ROOT_AGENTS_SMALL_STABLE=YES
NEW_SPECULATIVE_SKILLS_PLUGINS_MCP=NO
FAST_MODE_DEFAULT=OFF
MAX_ULTRA_DEFAULT=OFF
CODEX_DEFAULT_PUBLICATION_OPERATOR=NO
INDEPENDENT_REVIEW_REQUIRED=YES
RETAINED_USER_GATES_UNCHANGED=YES
```