# Trader Assist / Trade OS — Engineering Executor Pool and DeepSeek Harness Profile V1

**Status:** DRAFT GOVERNANCE FOR QUALIFICATION  
**Effective date:** 2026-08-18  
**Repository:** `woshixiong/trader-assist-v0`  
**Base main when drafted:** `4b8719ca44f9ff9d459910690183ca9b790b726d`  
**Scope:** role separation for engineering execution plus the initial bounded operating profile for DeepSeek Harness.

This specialized profile complements the canonical Unified Engineering Governance and the merged Hermes Execution Operator Contract. It does not replace either and grants no Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, signing/wallet, exchange-write, order-submission or trading authority.

---

## 1. Frozen engineering-layer architecture

Trader Assist / Trade OS uses four distinct layers:

```text
L1 — DECISION / CONTROL
Human + high-capability Engineering / Strategy / Product / Operations ChatGPT
        ↓ freezes task, route, executor, model, permissions, acceptance and stop conditions

L2 — CODING EXECUTOR POOL
Codex CLI | Trae | DeepSeek Harness
        ↓ code / tests / Git / authorized PR + CI work

L3 — ROUTINE AUTOMATION / OPERATOR
Hermes + approved low-cost/free model
        ↓ exact Task Packet transport, launch, wait/poll, mechanical status/evidence work

L4 — FOUNDATIONAL TOOLS
Terminal | Git | GitHub | CI | browser | local applications
```

### 1.1 Coding executors are peers

The project retains all three coding tools:

- `CODEX_CLI`;
- `TRAE_COMPUTER_USE` / Trae interactive coding;
- `DEEPSEEK_HARNESS` after qualification.

No tool is permanently designated the universal Writer. L1 assigns the exact executor/model for each bounded task according to capability, expected quality, cost, speed and availability.

For one coherent shared-authority stage there is exactly one primary Writer. Parallel execution is allowed only for read-only analysis or disjoint work whose contracts, worktrees and integration ownership are frozen. Competing Writers must not mutate the same shared authority or release branch.

### 1.2 Hermes is not a fourth coding executor

Hermes plus a low-cost/free model is a separate operator/automation layer. Hermes does not decide which coding executor to use and does not become a technical, research, architecture, repair, review or approval authority.

Hermes may only launch the exact executor/model frozen by L1 in a schema-valid Lossless Task Packet and must preserve raw evidence. Any missing/ambiguous executor, model, route, worktree, permission or acceptance field is fail-closed.

The merged `HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md` remains authoritative for Hermes.

---

## 2. DeepSeek Harness status and qualification boundary

DeepSeek Harness (`dsh`) is the first-party open-source Agent harness from DeepSeek AI. As of this profile it is in **Developer Preview** and its upstream README explicitly warns that compatibility-breaking changes will occur.

Therefore:

```text
DEEPSEEK_HARNESS_ROLE=CODING_EXECUTOR_CANDIDATE
DEEPSEEK_HARNESS_PRODUCTION_CRITICALITY=NONE
DEEPSEEK_HARNESS_QUALIFICATION_REQUIRED=YES
HERMES_TO_DEEPSEEK_H2_DISPATCH_ALLOWED=NO
```

Initial qualification is manual/local and non-production. The first accepted route is:

```text
Web UI qualification
→ read-only repository understanding
→ isolated worktree bounded coding task
→ focused + relevant regression tests
→ scope/diff/evidence review
→ token/cache/cost measurement
→ compare quality/rework/time with existing Writer routes
→ independent acceptance
→ only then consider Hermes headless integration
```

Current Hermes Task Packet schema and operator contract do not yet enumerate `DEEPSEEK_HARNESS`. No Hermes H2 task may launch DeepSeek Harness until a later bounded schema/profile governance change is independently accepted. Qualification does not implicitly authorize that later change.

---

## 3. Provider-native first: use shipped Harness capabilities before custom plugins

DeepSeek Harness follows an **Everything is a Plugin** architecture. For Trader Assist this is a replaceability mechanism, not permission to build a plugin platform.

Use this order:

```text
SHIPPED DSH PROFILE/CAPABILITY
→ DSH SETTINGS / PERMISSION PRESET
→ PROJECT AGENTS.md INSTRUCTIONS
→ PROJECT-LOCAL ON-DEMAND SKILL
→ THIN PROJECT PLUGIN ONLY AFTER REPEATED MEASURED NEED
```

Do not create a custom plugin merely because the architecture permits it. A custom plugin requires a concrete repeated need that cannot be met cleanly by shipped capabilities or a small project skill.

Because upstream is Developer Preview, project-owned DSH integration must stay behind a narrow executor seam and avoid dependence on unstable internal implementation details.

---

## 4. Default DeepSeek Harness coding profile

### 4.1 Mode

For coding work, prefer the shipped **Code Mode** after qualification. The official preset presents the tool registry through generated TypeScript and `run_code`, allowing multiple deterministic tool actions to be composed into one model round trip instead of many individual tool calls.

Use Standard/Plan Mode for exploration and plan approval where appropriate; do not change mode/tool/plugin composition unnecessarily in the middle of a coherent Writer stage.

### 4.2 Permissions

Initial and normal project use:

```text
PERMISSION_PRESET=workspace-write
APPROVAL_POLICY=ask
DANGER_FULL_ACCESS=PROHIBITED_BY_DEFAULT
```

Never choose `danger-full-access` merely to avoid prompts. Production/cloud/account/exchange boundaries remain separately prohibited unless explicitly authorized regardless of Harness permission mode.

### 4.3 Model route

Prefer DeepSeek's first-party `deepseek-official` adapter when available rather than an unnecessary compatibility wrapper.

Model routing policy:

- `deepseek-v4-flash`: default candidate for simple/mechanical coding, repository searches, narrow transformations and low-risk subwork where qualification shows adequate correctness;
- `deepseek-v4-pro`: candidate for material implementation, difficult debugging and tasks where Flash materially increases rework risk;
- reasoning `off/low/high/max` is an explicit L1 task choice; do not default every task to maximum reasoning;
- reserve `max` for genuinely hard architecture/debugging/authority-sensitive coding when the task still belongs to DeepSeek rather than Codex.

The exact model and reasoning setting remain task fields, not Harness-owned routing decisions.

---

## 5. Token and cache-efficiency policy

DeepSeek context caching is automatic and prefix-based. Harness/provider usage exposes cache-hit and cache-miss accounting. Trader Assist therefore optimizes **stable request prefixes** rather than trying to invoke a cache manually.

### 5.1 Keep the stable prefix stable

Prefer this order in model-visible context:

```text
stable Harness/profile/tool schema
→ stable role/safety boundary
→ stable repository AGENTS.md governance pointers
→ stable reusable task/output contract
→ mutable branch/head/blocker/allowlist/current evidence last
```

Rules:

- do not repaste long project history when the repository already contains canonical authority;
- use the same provider/model and same Writer session for the same role + coherent stage + worktree when context remains trustworthy;
- start a new session for independent Reviewer work, clean-route adjudication or role separation;
- avoid changing the visible tool/plugin/mode set mid-stage without need;
- keep volatile timestamps, CI IDs, current SHAs and blocker deltas late in the task packet rather than ahead of reusable instructions;
- append delta facts instead of rewriting stable prefixes where the protocol permits it.

Correctness and independence override cache optimization.

### 5.2 Measure actual provider usage

Use DSH token-meter / provider usage as observability, not as authority. Track at minimum when qualification permits:

```text
uncached_input_tokens
cache_read_tokens / prompt_cache_hit_tokens
cache_miss_tokens
output_tokens
cache_hit_ratio
model
reasoning_effort
session/task id
elapsed time
repair/rework count
```

The Harness token meter uses an approximation when exact provider usage is unavailable; provider-reported usage is the billing evidence.

### 5.3 Compaction and tool-result pruning

Keep the shipped Code Mode compaction and tool-result-pruning defaults initially.

Use compaction at genuine context-pressure or coherent substage boundaries, not after every turn. Compaction itself can require a model call and replaces detailed visible history with a summary; unnecessary compaction can increase cost and reduce useful detail.

Prefer deterministic tool-result pruning before model-backed summarization when large command/test outputs dominate context. Preserve raw external evidence outside the conversational summary when it is authority-bearing.

---

## 6. Project skills policy

DeepSeek Harness project-local skills are the preferred place for **detailed, reusable, on-demand mechanical instructions** that should not inflate every prompt.

Preferred project root after qualification:

```text
.dsh/skills/<skill-name>/SKILL.md
```

DSH exposes only skill names/descriptions in the initial model catalog and loads a full skill body on demand. This is preferable to placing every runbook in `AGENTS.md` or every Task Packet.

### Allowed skill content

Good candidates include:

- local test/gate command recipes;
- repository status/evidence collection;
- deterministic diff/scope/secret checks;
- Result Packet formatting;
- common read-only repository discovery;
- bounded environment/worktree preflight;
- other stable mechanical workflows.

### Prohibited skill authority

A skill must not decide or alter:

- product/strategy/engineering route;
- architecture or authority model;
- Writer/executor/model selection;
- repair/replan/simplification decisions;
- scope/allowlist expansion;
- independent acceptance;
- Mark Ready, merge, deployment, production/runtime, credentials/private API, signing, wallet, exchange write or trading actions.

Keep skill descriptions short and routing-specific. Load the full body only when needed. Do not duplicate identical detailed instructions across `AGENTS.md`, skills and Task Packets.

No project `.dsh/skills` are activated by this governance-only change; skill implementation follows qualification and independent review.

---

## 7. Subagents, workflows and Ralph

DeepSeek Harness includes subagents/workflows and a Ralph fresh-agent loop, but these are not default project execution policy.

Use plain direct Code Mode first. Introduce subagents only where a task has truly separable read-only/disjoint subwork and the parent remains integration owner.

`ralph` is opt-in only when the direct task explicitly calls for a fresh-agent iterative loop. It starts fresh child contexts and pays fresh context each round; worker `complete` is not independent acceptance. It must not be used as a hidden repair loop or as a substitute for the project's repair budget, independent Reviewer or `HOLISTIC_CONVERGENCE_GATE`.

Do not enable optional Codex/Claude-code subagent providers merely because DSH supports them. Existing project executor routing remains controlled by L1.

---

## 8. Cost-aware scheduling / peak-off-peak policy

DeepSeek pricing is time-sensitive and may change. The project policy is:

```text
DEEPSEEK_OFF_PEAK_PREFERRED=YES
DELAY_TOLERANT_DEEPSEEK_WORK=QUEUE_FOR_VERIFIED_OFF_PEAK_WHEN_PRACTICAL
URGENT_OR_RELEASE_CRITICAL_WORK=DO_NOT_DELAY_SOLELY_FOR_PRICE
PRICE_WINDOW_SOURCE=LIVE_DEEPSEEK_OFFICIAL_STATE
HARDCODE_STALE_PRICE_WINDOWS=NO
```

As of 2026-08-18, public reporting confirms that DeepSeek introduced peak/off-peak V4 API pricing effective 2026-08-17 and that peak rates can be roughly twice off-peak rates for the same billing category. DeepSeek's indexed public API pricing documentation may lag the newly effective schedule. Therefore no automated scheduler may freeze exact peak/off-peak clock windows from a third-party article or stale documentation.

Before Hermes or any local scheduler defers work by price window, it must resolve the then-current official DeepSeek pricing/window information. If that information cannot be verified, cost scheduling is advisory/manual rather than an execution gate.

Cache-hit optimization remains valuable in either window and should not be traded away merely to move work in time.

---

## 9. Qualification acceptance matrix

DeepSeek Harness is eligible for normal Writer routing only after a bounded qualification demonstrates:

```text
IDENTITY_AND_VERSION=PASS
OFFICIAL_PROVIDER_ROUTE=PASS
WORKSPACE_SANDBOX=PASS
AGENTS_GOVERNANCE_LOAD=PASS
READ_ONLY_REPO_UNDERSTANDING=PASS
CODE_MODE_BOUNDED_EDIT=PASS
ALLOWED_PATH_ENFORCEMENT=PASS
FOCUSED_TEST_EXECUTION=PASS
RELEVANT_REGRESSION=PASS
DIFF_SCOPE_EVIDENCE=PASS
NO_UNAUTHORIZED_GIT_OR_GITHUB_MUTATION=PASS
TOKEN_USAGE_CAPTURE=PASS
CACHE_HIT_MISS_CAPTURE=PASS
SESSION_RESUME_BEHAVIOR=PASS
RAW_EVIDENCE_PRESERVATION=PASS
INDEPENDENT_REVIEW=PASS
```

Also record comparative evidence against at least one existing Writer route where practical:

- wall-clock completion time;
- model/token cost;
- cache-hit ratio after warm context;
- number/severity of Writer errors;
- repair/rework count;
- test pass rate;
- operator burden.

Qualification is evidence collection, not a permanent ranking. Future task routing remains capability-matched.

---

## 10. Future Hermes integration seam

If DeepSeek Harness passes qualification, the preferred automation seam is its native non-interactive/headless CLI rather than GUI Computer Use when the exact required behavior is supported.

A later bounded governance/schema task may add a machine-readable executor such as:

```text
executor.kind=DEEPSEEK_HARNESS
```

That later task must define at minimum:

- exact DSH version/profile;
- exact provider/model/reasoning;
- exact session NEW/resume semantics;
- exact worktree/branch/expected HEAD;
- allowed paths and permission preset;
- Task Packet acknowledgement fields;
- raw Result Packet/evidence capture;
- timeout/failure semantics;
- no autonomous repair/retry;
- compatibility-break handling for Developer Preview upgrades.

Until that later schema/profile is accepted, Hermes must return `HUMAN_OR_L1_DECISION_REQUIRED` rather than improvising a DeepSeek Harness launch.

---

## 11. Upgrade policy while DSH is Developer Preview

Do not silently float Harness versions on an authority-bearing coding task.

For qualification and later automation, record the exact installed/resolved DSH version. An upstream version change that alters command grammar, profile composition, permission behavior, tool visibility, session semantics or output contract requires bounded requalification of the affected seam before Hermes automation resumes.

Interactive exploratory use may run the latest official package, but accepted automation must pin or otherwise verify the exact expected version at launch.

---

## 12. Mandatory preflight record for this route

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
TASK_CLASS=MATERIAL
LIVE_REPO=woshixiong/trader-assist-v0
LIVE_MAIN_SHA=4b8719ca44f9ff9d459910690183ca9b790b726d
EXACT_START_HEAD=4b8719ca44f9ff9d459910690183ca9b790b726d
INDEPENDENT_ANALYSIS_DONE=YES
EXTERNAL_RESEARCH_DONE=YES
SYNTHESIS_DONE=YES
ROOT_CAUSE_LEVEL=ARCHITECTURAL
AFFECTED_AUTHORITIES=engineering executor routing; Hermes operator boundary
FROZEN_INVARIANTS=three-peer coding pool; Hermes separate non-decision operator; one primary Writer per shared authority; independent review; user-retained gates
CURRENT_ROUTE=specialized executor profile + manual DSH qualification before Hermes integration
MATURE_ALTERNATIVES_CONSIDERED=Trae-only; Codex-only; Claude Code plus DeepSeek; raw API/custom harness; custom DSH plugins
CURRENT_NEED=freeze role architecture and DSH efficiency/cost profile
NEXT_EXPECTED_STAGE=manual DSH qualification, then separately reviewed Hermes schema/profile update if accepted
STABLE_INTERFACES=Task Packet; executor assignment; worktree; tests; Result Packet; independent review
REPLACEABLE_IMPLEMENTATION_SEAMS=executor kind/profile
KNOWN_REWRITE_OR_LOCKIN_RISK=DSH Developer Preview/breaking changes, bounded by narrow executor seam and version qualification
OVERENGINEERING_CHECK=PASS
PROVIDER_SCALE_BUDGET=NOT_APPLICABLE
REALISTIC_SCALE_TEST_PLAN=bounded qualification corpus plus token/cache/cost/rework metrics
FRESHNESS_OR_LATENCY_GATE=off-peak preferred; live official price-window resolution before automated scheduling
ATTACK_MATRIX_FROZEN=YES
REPAIR_STAGE=INITIAL
STOP_CONDITION=qualification failure, incompatible upstream break, or unresolved authority/price-window condition blocks automation promotion
WRITER_SCOPE=governance/docs only
PROHIBITED_SCOPE=runtime/product/strategy/schema/production/credentials/merge
ROLLBACK_OR_SAFE_STOP=discard this branch/PR; main remains unchanged
```

---

## 13. External authority basis used for this profile

Primary technical sources reviewed on 2026-08-18:

- DeepSeek AI `deepseek-ai/deepseek-harness` root README and CLI documentation;
- shipped Code Mode preset;
- DSH agent-instructions, skills, token-meter, compaction, permissions, workflow/Ralph and DeepSeek LLM adapter documentation;
- DeepSeek API context-caching, V4 model and API pricing documentation.

The external findings **confirm** the independent route of using first-party DSH as a replaceable coding executor, stable-prefix/canonical-repository prompting, on-demand skills, token/cache observability, bounded permissions and headless automation later. They **modify** the preliminary route by making Code Mode and project-local skills first-class efficiency mechanisms and by retaining shipped compaction/pruning rather than custom context management. They also identify one unresolved external fact: the indexed official pricing page may lag the newly active peak/off-peak schedule, so exact automated time windows remain verification-gated.

---

## 14. Frozen concise rulings

```text
CODING_EXECUTOR_POOL=CODEX+TRAE+DEEPSEEK_HARNESS
TRAE_RETAINED=YES
HERMES_IS_CODING_EXECUTOR=NO
HERMES_LAYER=ROUTINE_OPERATOR_AUTOMATION
L1_FREEZES_EXECUTOR_AND_MODEL=YES
ONE_PRIMARY_WRITER_PER_SHARED_AUTHORITY_STAGE=YES
DEEPSEEK_HARNESS_FIRST_PARTY=YES
DEEPSEEK_HARNESS_DEVELOPER_PREVIEW=YES
DEEPSEEK_HARNESS_QUALIFICATION_REQUIRED=YES
DEEPSEEK_CODE_MODE_PREFERRED_FOR_CODING=YES_AFTER_QUALIFICATION
DSH_PERMISSION_DEFAULT=WORKSPACE_WRITE_PLUS_ASK
DSH_DANGER_FULL_ACCESS_DEFAULT=NO
DSH_STABLE_PREFIX_CACHE_OPTIMIZATION=YES
DSH_PROJECT_SKILLS_ON_DEMAND=YES_AFTER_QUALIFICATION
DSH_CUSTOM_PLUGIN_FIRST=NO
DSH_TOKEN_CACHE_METRICS_REQUIRED_FOR_QUALIFICATION=YES
DEEPSEEK_OFF_PEAK_PREFERRED=YES
DEEPSEEK_EXACT_PRICE_WINDOW_DYNAMIC_VERIFICATION=REQUIRED_BEFORE_AUTOMATION
HERMES_TO_DSH_H2_ALLOWED_NOW=NO
HERMES_TO_DSH_FUTURE_SEAM=HEADLESS_CLI_PREFERRED_WHEN_ACCEPTED
MARK_READY_MERGE_DEPLOY_RUNTIME_ACCOUNT_EXCHANGE=SEPARATE_USER_AUTHORITY
```
