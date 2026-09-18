# Trader Assist / Trade OS — Codex CLI Engineering Usage Profile V2

**Status:** HOLISTIC-CONVERGENCE GOVERNANCE CANDIDATE  
**Effective date:** 2026-08-23  
**Current locally verified CLI:** `codex-cli 0.149.0`

This is the stable, version-independent Codex execution core. Current model facts live in `governance/CODEX_CURRENT_MODEL_PROFILE.md`. Task/model routing lives in `governance/ENGINEERING_EXECUTOR_ROUTER_V2_2026-08-23.md`.

It grants no Mark Ready, merge, deployment, runtime/cloud mutation, credentials/private API, signing/wallet, exchange write, order submission/cancellation or trading authority.

## 1. Optimization objective

```text
MAXIMIZE = ACCEPTED_USEFUL_ENGINEERING_WORK / TOTAL_BURDEN
TOTAL_BURDEN =
  MODEL_TOKENS
  + RETRIES
  + REWORK
  + REVIEW
  + HUMAN_RELAY
  + LATENCY
  + CONTEXT_DISCOVERY
```

Correctness and authority are hard constraints. Token reduction that removes necessary scope, invariants, negative cases, validation or stop conditions is prohibited.

## 2. Stable architecture

```text
LAYER A  ENGINEERING_EXECUTOR_ROUTER_V2
         task class / model / executor / quota choice

LAYER B  THIS FILE
         stable Codex CLI workflow, context, cache, session, skill,
         permission, validation and evidence rules

LAYER C  CODEX_CURRENT_MODEL_PROFILE.md
         refreshable current models/reasoning/service-tier facts

LAYER D  FROZEN TASK PACKET
         exact current task / identities / scope / tests / authorities
```

A model upgrade should normally change Layer C, not rewrite this file.

## 3. Default execution surface

For bounded Writer work use provider-native non-interactive:

```text
codex exec
```

Prefer interactive TUI only for deliberate pair-programming/exploration. For material/resumable automated work enable:

```text
--json
```

and retain the exact `thread_id` plus `turn.completed.usage` values. This obtains `input_tokens`, `cached_input_tokens`, `output_tokens` and `reasoning_output_tokens` without another model turn.

Use an exact session ID for resume. `resume --last` may be used manually, but it is not an automation identity because the wrong most-recent session can be selected.

## 4. Repository instructions — map, not encyclopedia

The root `AGENTS.md` is a compact routing/authority map. Do not duplicate the full governance corpus there.

Do not create a project constitution in global `~/.codex/AGENTS.md`. The user's current audit shows no global AGENTS or override file; keep that clean unless a genuinely cross-repository preference is later needed.

Do not add `CODEX.md` to `project_doc_fallback_filenames`. The historical root `CODEX.md` is stale and is retired by this V2 route.

Detailed rules belong in indexed governance files and on-demand skills. The frozen Task Packet names only the exact deeper authorities needed for the current stage.

## 5. Context-loading discipline — controller-resolved, progressive disclosure

Engineering Control resolves live GitHub identity, governance applicability, architecture/research decisions and Task Packet authority **before Codex starts**.

Default Codex Writer input:

```text
AUTO_LOADED_ROOT_AGENTS
-> FROZEN COMPACT TASK PACKET
-> PREFLIGHT ATTESTATION
-> EXACT AUTHORITY COMMENT / FILE / SECTION LOCATORS
-> EXACT AFFECTED FILES / FUNCTIONS / TESTS
-> SMALL RELATED DIRECTORY ONLY WHEN NEEDED
```

Do not ask Codex to repeat control-plane work already frozen by Engineering Control.

Default prohibited context expansion:

```text
READ_FULL_UNIFIED_V2=NO
READ_FULL_MANDATORY_PREFLIGHT=NO
READ_FULL_PROJECT_RULES_INDEX=NO
READ_FULL_ISSUE_OR_PR_HISTORY=NO
BROAD_RG_GOVERNANCE_DOCS=NO
BROAD_REPO_SEARCH_WHEN_EXACT_SURFACES_ARE_KNOWN=NO
REPEAT_L1_ARCHITECTURE_RESEARCH=NO
```

A concrete conflict, missing fact or semantic ambiguity may justify the minimum targeted read. A material conflict returns to Engineering Control instead of turning the Writer into a second L1 research window.

The Task Packet should contain the exact already-resolved invariants rather than instructions to rediscover them. Passing paths/hashes/comment IDs is preferred over pasting full historical bodies.

```text
FULL_GOVERNANCE_CORPUS_IS_AUTHORITY_NOT_DEFAULT_MODEL_CONTEXT=YES
CONTEXT_DISCOVERY_BUDGET_IS_PART_OF_TOTAL_BURDEN=YES
```

## 6. Cache-preserving stage invariant — mandatory

Prompt caching is an optimization, never correctness authority. Within one coherent Codex Writer stage keep the following stable unless a real boundary requires a new stage:

```text
MODEL
REASONING_EFFORT
SERVICE_TIER
CWD / EXACT WORKTREE
SANDBOX MODE
APPROVAL POLICY
ENABLED TOOL / MCP / PLUGIN SHAPE
CONTROL PREFIX
OUTPUT CONTRACT SHAPE
```

Do not casually switch Terra→Sol, reasoning level, CWD, sandbox, approval policy, MCP/tool configuration or other prefix-shaping settings mid-stage. These changes can reduce prefix reuse and can also change execution semantics.

When one of these must change materially:

```text
FREEZE CURRENT EVIDENCE
-> CLOSE CURRENT STAGE
-> RE-RUN ROUTER/PREFLIGHT AS APPLICABLE
-> START A NEW STAGE / SESSION WITH THE NEW SHAPE
```

This rule must be frozen by Engineering Control before Codex dispatch.

## 7. Stable prefix + mutable tail

Construct every material packet in this order:

```text
A. STABLE CONTROL PREFIX
   role / project / executor / authority boundary
   one-primary-Writer rule
   retained user gates
   SAFE_STOP semantics
   output contract

B. STABLE TASK CONTRACT
   goal / scope / invariants / accepted baseline
   allowed/prohibited paths
   attack/negative cases
   exact validation plan
   done-when

C. MUTABLE EVIDENCE TAIL
   live main/base/head
   current CI/run/log ids
   temporary evidence paths
   current narrow blocker
```

Keep headings/order stable where practical. Put volatile facts late.

## 8. Model/reasoning economy

Engineering Control selects the model/reasoning before dispatch; the Writer does not self-upgrade.

Current default policy is defined in `CODEX_CURRENT_MODEL_PROFILE.md`. Stable principles:

- start at the lowest reasoning/model tier expected to preserve the required quality;
- normal material coding should not automatically use maximum reasoning;
- upgrade because task complexity/consequence requires it, not because the task is merely labeled material;
- if a model/reasoning upgrade is needed after meaningful work has begun, prefer a clean stage boundary rather than silently changing the current stage shape.

## 9. Project `.codex/config.toml`

Repository config contains only stable low-noise defaults that should be identical across Codex tasks. It deliberately does **not** pin model, reasoning effort, sandbox or approval policy because those are task-level Router decisions and project config has higher precedence than selected profiles.

Stable project defaults:

```text
service_tier = default
model_verbosity = low
model_reasoning_summary = none
web_search = disabled
multi-agent = disabled by default
```

External research normally belongs to Engineering Control before Writer dispatch. Enable web/MCP/extra tools only for a bounded task that genuinely needs them.

Multi-agent is off by default because project governance requires one primary Writer for shared authority and because unnecessary subagents increase token/tool context. L1 may explicitly authorize a separable parallel discovery/review task.

## 10. User config and profiles

User-level `~/.codex/config.toml` is a cross-project fallback, not Trader Assist project governance.

Recommended neutral fallback:

```text
model = gpt-5.6-terra
model_reasoning_effort = medium
service_tier = default
```

Keep task-specific upgrades in named user profiles or explicit CLI overrides, not as a permanent global high-reasoning default.

Do not overwrite unrelated user config/MCP/provider/auth settings when changing these three keys. Always back up before a local edit.

## 11. Skills — progressive disclosure

Use repo-scoped skills under:

```text
.agents/skills/
```

Keep the set small and single-purpose so the initial skill metadata does not crowd context. Full skill instructions are loaded only when needed.

Trader Assist V2 standard skills:

```text
$trade-os-writer-preflight
$trade-os-local-gates
$trade-os-evidence
$trade-os-result-packet
```

They are executor-neutral. They may be used by Codex and later other compatible agents. Do not copy DeepSeek-specific provider/model assumptions into these shared skills.

Skill use:

- Writer start: `$trade-os-writer-preflight`.
- Validation phase: `$trade-os-local-gates`.
- Evidence freeze: `$trade-os-evidence`.
- Final handoff: `$trade-os-result-packet`.

Do not create a skill for every command. Add a new skill only when a repeated procedural capability has stable value.

## 12. Permission and sandbox policy

Use the minimum capability required for the frozen stage.

```text
READ/REVIEW STAGE -> read-only sandbox
WRITER STAGE      -> workspace-write when local file mutation is required
APPROVAL POLICY   -> fail-closed/noninteractive for a fully frozen packet where supported
```

Broad danger/full-access modes are not normal Trader Assist routes. A permission failure does not grant authority to expand scope.

Do not hard-code commit/push prohibition into a generic Codex installation: some coherent stages may explicitly authorize them. Publication authority remains task-specific and never implies Mark Ready/merge/deploy.

## 13. Validation and log economy

Within an authorized semantic Writer stage:

```text
IMPLEMENT
-> SMALLEST DECISIVE FOCUSED TEST
-> REQUIRED RELEVANT REGRESSION
-> LINT/TYPE/COMPILE WHEN APPLICABLE
-> DIFF/SCOPE/SECRET CHECK
-> EXACT RESULT PACKET
```

Keep passing command output bounded. Preserve raw logs outside the model context when evidence is needed; send decisive excerpts/status back into context rather than entire successful logs.

Codex local validation is for **iteration on the semantic change**, not for reproducing every repository proof:

```text
FOCUSED_LOCAL_TESTS_FOR_CHANGED_SEMANTICS=YES
FULL_REPOSITORY_SUITE_IN_CODEX_SESSION=NO_BY_DEFAULT
LOCKED_DEPENDENCY_FULL_CI=GITHUB_ACTIONS_BY_DEFAULT
LINUX_SPECIFIC_PROOF=GITHUB_ACTIONS_BY_DEFAULT
INSTALL_EXTRA_FULL_SUITE_DEPS_ON_USER_MAC_FOR_CI_PARITY=NO_BY_DEFAULT
```

After the semantic checkpoint is frozen, move full-suite / exact-lock / Linux / status / artifact validation to the canonical GitHub workflow unless the task is genuinely local or no equal-fidelity remote surface exists.

A failing test caused by an in-scope implementation defect may be repaired only inside the frozen repair/stage authority. New root cause, new dependency, allowlist expansion, authority change or repair-budget exhaustion => `SAFE_STOP`.

## 14. Session policy

Reuse the exact Codex session only when all remain true:

```text
SAME PRIMARY WRITER
SAME COHERENT STAGE
SAME WORKTREE / ARTIFACT
SAME AUTHORITY
SAME OBJECTIVE
SAME MODEL / REASONING / TOOL SHAPE
CONTEXT TRUSTWORTHY
INDEPENDENCE NOT REQUIRED
```

Start a new session for a materially new task/stage, authority change, worktree change, different Reviewer role, significant model/tool/sandbox shape change, or accumulated stale/conflicting context.

Long context is capacity, not a target. Do not keep unrelated work in one session merely to avoid starting a new one.

## 15. Semantic Writer vs operator tail

Codex quota should pay for semantic code work. Deterministic tail work may be delegated to free OpenCode or, after qualification, Hermes.

Recommended boundary:

```text
CODEX:
  inspect -> reason -> implement -> in-scope tests -> self-check -> evidence freeze

GITHUB / ENGINEERING CONTROL / QUALIFIED OPERATOR:
  remaining already-authorized deterministic status/diff/evidence/publication/CI mechanics
```

This does not require a handoff after every Codex task. If Codex can finish a tiny authorized tail more cheaply than creating a new handoff, it may do so. Optimize total burden.

The handoff must carry exact worktree/artifact/head and frozen packet identity; the operator must not reinterpret the code task.

## 16. Independent review

Writer self-check is mandatory but not independent acceptance.

When GitHub exact diff/artifacts and exact-head CI are sufficient, use a separate strong ordinary ChatGPT review window. Do not spend Codex quota on a duplicate local Reviewer solely for ceremony.

Use a different local strong agent only when independent validation genuinely requires execution/inspection that the ChatGPT review window cannot access.

## 17. Telemetry — passive, not synthetic

For each real material Codex task, retain where naturally available:

```text
CODEX_VERSION
MODEL
REASONING
SERVICE_TIER
NEW_OR_EXACT_RESUME
THREAD_ID
INPUT_TOKENS
CACHED_INPUT_TOKENS
OUTPUT_TOKENS
REASONING_OUTPUT_TOKENS
ELAPSED_TIME
RETRY_COUNT
REWORK_COUNT
FINAL_INDEPENDENT_ACCEPTANCE
```

Do not create synthetic paid tasks just to maximize a cache-hit percentage. Track accepted work per total token/rework/human-relay cost.

## 18. Avoided configuration surfaces

Do not add these without evidence of need:

- giant global `~/.codex/AGENTS.md`;
- `AGENTS.override.md` as permanent project governance;
- `CODEX.md` fallback loading;
- model-instructions replacement files;
- many MCP servers/tools enabled by default;
- generic hooks framework;
- project-wide hard-coded model/reasoning/sandbox/approval;
- automatic multi-agent spawning;
- project-specific memories as authority.

Prefer the smallest stable harness plus task-local explicit state.

## 19. Final V2 invariants

```text
CODEX_EXEC_DEFAULT=NONINTERACTIVE_EXEC
MATERIAL_RUN_JSONL=YES
EXACT_SESSION_ID_RESUME=YES
RESUME_LAST_AUTOMATION_IDENTITY=NO
ROOT_AGENTS_IS_MAP_NOT_MANUAL=YES
GLOBAL_PROJECT_RULE_DUPLICATION=NO
REPO_SKILLS_PROGRESSIVE_DISCLOSURE=YES
STABLE_STAGE_MODEL_REASONING_CWD_SANDBOX_APPROVAL_TOOL_SHAPE=YES
STABLE_PREFIX_MUTABLE_TAIL=YES
PROJECT_CONFIG_DOES_NOT_PIN_MODEL_OR_REASONING=YES
WEB_SEARCH_DEFAULT_OFF_FOR_LOCAL_WRITER=YES
MULTI_AGENT_DEFAULT_OFF=YES
BOUNDED_TEST_OUTPUT=YES
FREE_OPERATOR_TAIL_WHEN_IT_REDUCES_TOTAL_BURDEN=YES
PASSIVE_TOKEN_CACHE_TELEMETRY=YES
WRITER_SELF_CHECK_NE_INDEPENDENT_ACCEPTANCE=YES
```