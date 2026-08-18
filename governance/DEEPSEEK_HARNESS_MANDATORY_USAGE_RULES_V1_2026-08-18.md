# Trader Assist / Trade OS — DeepSeek Harness Mandatory Usage Rules V1

**Status:** DRAFT SPECIALIZED GOVERNANCE  
**Effective date:** 2026-08-18  
**Repository:** `woshixiong/trader-assist-v0`  
**Parent profile:** `governance/ENGINEERING_EXECUTOR_POOL_AND_DEEPSEEK_HARNESS_PROFILE_V1_2026-08-18.md`  
**Scope:** mandatory execution, prompt, context, cache, skill, session, model, permission, cost and setup-verification rules whenever DeepSeek Harness is used as a Trader Assist / Trade OS coding executor.

This file is a specialized L2 execution contract. It does not replace the canonical Unified Engineering Governance, Mandatory Engineering Preflight, Research/Evidence/Decision Method, Hermes contract, product/strategy/security authorities, or explicit user gates.

It grants no Mark Ready, merge, deployment, production/runtime/cloud mutation, credentials/private API beyond the DeepSeek model credential, signing/wallet, exchange write, order submission or trading authority.

---

## 1. Frozen provider/harness route

The DeepSeek coding route for this project is fixed as:

```text
DEEPSEEK_HARNESS=@deepseek-ai/dsh
DEEPSEEK_PROVIDER=deepseek-official
DEEPSEEK_API=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash | deepseek-v4-pro
```

Do not route the DeepSeek API through Codex, Trae, Claude Code, OpenCode or another harness for normal project work. Codex and Trae remain independent peer coding executors with their own task assignments; they are not alternate wrappers for the DeepSeek route.

Current setup baseline:

```text
DSH_VERSION=0.1.0-rc.7
DSH_UPSTREAM_RELEASE_SHA=99f6f02fecdb7dff40c3fbc9470f5907c29f74ca
```

Because DSH is Developer Preview, authority-bearing automated use MUST pin or verify the expected DSH version. A version change that alters command grammar, agent preset composition, permission behavior, tool visibility, session semantics, skill semantics or output/evidence behavior requires bounded seam re-verification before automation resumes.

---

## 2. Authority split: L1 decides; L2 executes

The full material governance/preflight burden belongs to L1 Engineering Control before Writer dispatch:

```text
L1
→ load canonical governance + live GitHub
→ independent analysis
→ external mature/provider-native research when material
→ synthesis
→ PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
→ ENGINEERING_PREFLIGHT_GATE=PASS
→ freeze route / executor / model / reasoning / scope / tests / stop conditions
→ issue one frozen Writer Task Packet
```

DeepSeek Harness is an L2 bounded Writer. It MUST NOT independently redo a material route choice that L1 already froze.

### 2.1 Token-efficient L2 fast path

A DeepSeek Writer session does **not** automatically reread every large governance document when all of these are true:

```text
FROZEN_TASK_PACKET=VALID
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS            # material tasks
LIVE_REPO_AND_EXPECTED_HEAD_MATCH=YES
EXECUTOR=DEEPSEEK_HARNESS
MODEL_AND_REASONING=EXPLICIT
WORKTREE_AND_ALLOWED_PATHS=EXPLICIT
STOP_CONDITIONS=EXPLICIT
USER_GATES=EXPLICIT
```

In that case the Writer loads:

1. root `AGENTS.md` automatically through the shipped DSH instruction mechanism;
2. the frozen Task Packet;
3. `trade-os-writer-preflight` at task start;
4. other project-local skills only when required by the current step;
5. any narrow authority/source file explicitly referenced by the Task Packet.

The Writer MUST safe-stop and request L1 resolution before continuing if it encounters a new material design choice, an authority ambiguity, missing/stale preflight attestation, governance/version mismatch, HEAD drift, required allowlist expansion, new dependency/service, repair-route change, or a conflict between the Task Packet and repository authority. At that point L1 re-enters the full canonical governance path.

This fast path reduces duplicate model context; it does not delegate L1 authority to the Writer and does not weaken any safety or release gate.

---

## 3. Ten mandatory DeepSeek operating rules

### Rule 1 — PTC / Code Mode first for coding

For coding, use the shipped `code` agent preset, displayed as **PTC 模式** in the current Chinese UI. It keeps the standard coding capabilities but presents tools through the Code Mode SDK so a deterministic sequence can be composed in one TypeScript `run_code` instead of many model/tool round trips.

Use Standard/Plan behavior only when the task explicitly calls for exploration/planning. A session's agent preset is fixed at session creation; do not churn presets mid-stage for convenience.

### Rule 2 — Keep always-loaded instructions small, stable and canonical

The root repository `AGENTS.md` is the stable project baseline. Do not duplicate the full project governance in `$DSH_HOME/AGENTS.md`, `CLAUDE.md`, prompt prose or task history.

For project work:

```text
$DSH_HOME/AGENTS.md = empty or minimal generic non-project guidance
repository AGENTS.md = canonical stable project pointers/boundaries
large detailed mechanical procedures = on-demand skills
volatile task facts = frozen Task Packet tail
```

Do not modify DSH's shipped 65,536-byte instruction budget merely to stuff more project prose into the initial prompt. Smaller correct context is preferred over filling the available budget.

### Rule 3 — Use project-local progressive skills for reusable mechanics

Project skills live at:

```text
.dsh/skills/<skill-name>/SKILL.md
```

The initial model catalog carries routing metadata only; the full skill body is loaded on demand. Use this to keep recurring mechanical runbooks out of every prompt.

Initial project skill set:

```text
trade-os-writer-preflight
trade-os-local-gates
trade-os-evidence
trade-os-result-packet
```

Skills may encode deterministic procedures, commands and output formats. Skills MUST NOT decide product/strategy/technical routes, architecture, executor/model, scope expansion, repair/replan/simplification, independent acceptance, Mark Ready, merge, deployment, runtime/cloud, credentials/private API, signing/wallet, exchange write or trading actions.

### Rule 4 — Stable prefix, small mutable tail

DeepSeek context caching is automatic and prefix-based. Optimize both token volume and cache reuse with this shape:

```text
stable DSH/PTC composition
→ stable root AGENTS instructions
→ stable skill catalog
→ stable bounded Writer/output contract
→ mutable frozen Task Packet facts last
```

Keep branch/head SHA, CI run, timestamps, blocker IDs, one-off evidence and task deltas late. Do not unnecessarily change provider/model/preset/tool composition during one coherent stage.

**Zero-cache rule:** a task must remain reasonably efficient even if cache hit is 0%. Cache is an optimization, not a license to send huge repeated governance bodies.

### Rule 5 — Measure provider usage, not just UI estimates

For setup verification and material DeepSeek stages capture when available:

```text
uncached_input_tokens
prompt_cache_hit_tokens / cache_read_tokens
prompt_cache_miss_tokens
output_tokens
cache_hit_ratio
provider/model
reasoning mode/effort
session/task id
elapsed time
price window
repair/rework count
```

Provider-reported usage is billing evidence. DSH token-meter/context-pressure figures are useful observability but include heuristic estimation when provider usage is unavailable; they are not billing or authority gates.

### Rule 6 — Resume only the same Writer/stage/worktree

Resume the exact DSH Writer session only when all are true:

- same Writer role;
- same coherent authorized stage;
- same worktree/authority context;
- prior context remains trustworthy;
- independence is not required.

Use a new session for a new materially different task, changed authority/worktree, clean-route adjudication, different role, or independent Reviewer work. Cache savings never override reviewer independence or clean-context needs.

### Rule 7 — Prune deterministic tool noise before compaction; keep provider retries bounded

Keep the shipped Code/PTC tool-result pruner and compaction behavior initially. The current shipped Code preset prunes large tool results at its normal thresholds before model-backed compaction.

Prefer bounded command output and deterministic pruning. Use compaction only for genuine context pressure or a coherent substage boundary; do not compact every few turns. Preserve raw authority-bearing evidence outside conversational summaries.

For the DeepSeek provider route, retain the shipped **normal finite provider-request retry policy** unless a later measured problem justifies a change. Current normal mode is transport/model-request recovery with a bounded retry budget for transient failures; it is not engineering repair authority. Do **not** use the unbounded `always` retry mode for Trader Assist project work. A provider retry may repeat input billing, so retry events are cost evidence and must never be reinterpreted as permission for autonomous task-level repair/replan/retry.

### Rule 8 — Model/reasoning economy uses real provider semantics

DeepSeek's official API exposes thinking ON/OFF and effective reasoning efforts `high` and `max`. Compatibility values `low` and `medium` map to `high`; `xhigh` maps to `max`.

Therefore the project routing defaults are:

```text
Flash + thinking OFF = deterministic/narrow mechanical work where reasoning is unnecessary
Flash + HIGH         = ordinary bounded coding / repository work
Pro   + HIGH         = material implementation / difficult debugging
Pro   + MAX          = exceptional difficult quality-first agent coding
```

Do **not** use a UI label `Low` as a token-saving policy: with the current DeepSeek API it maps to `high` while thinking is enabled.

L1 freezes model and reasoning per task. DeepSeek/Hermes may not self-upgrade model, reasoning, scope or cost tier.

### Rule 9 — “Everything is a Plugin” means stable seams, not plugin proliferation

Use this order:

```text
SHIPPED DSH CAPABILITY
→ SETTINGS / PERMISSION / AGENT PRESET
→ AGENTS.md
→ PROJECT-LOCAL SKILL
→ THIN CUSTOM PLUGIN ONLY AFTER REPEATED MEASURED NEED
```

No custom DSH plugin is authorized for the initial project integration. Subagents/workflows/Ralph are opt-in only; they must not become hidden repair loops, competing Writers or substitutes for independent acceptance.

### Rule 10 — Prefer official DeepSeek off-peak windows for delay-tolerant work

Current official DeepSeek schedule confirmed on 2026-08-18:

```text
TIMEZONE=Asia/Shanghai
PEAK_1=09:00-12:00
PEAK_2=14:00-18:00
OFF_PEAK=00:00-09:00,12:00-14:00,18:00-24:00
OFF_PEAK_PRICE_MULTIPLIER=0.5_OF_PEAK
```

Delay-tolerant DeepSeek coding/replay/evaluation work should run off-peak where practical. Urgent, incident, release-critical or user-time-sensitive work must not be delayed solely for price. Reverify the provider schedule if DeepSeek changes its pricing page.

---

## 4. Frozen Writer Task Packet shape

L1 should give DSH a compact, complete packet rather than a long chat-history prompt. The packet is the mutable tail; it is not a second engineering constitution.

Minimum shape:

```yaml
task_id: <stable-id>
role: BOUNDED_IMPLEMENTATION_WRITER
mode: READ_ONLY | IMPLEMENT

executor:
  kind: DEEPSEEK_HARNESS
  dsh_version: 0.1.0-rc.7
  provider: deepseek-official
  model: deepseek-v4-flash | deepseek-v4-pro
  thinking: disabled | enabled
  reasoning_effort: high | max | n/a
  agent_preset: code
  permission_preset: workspace-write
  approval_policy: ask
  provider_retry_policy: normal
  session_mode: NEW | RESUME_EXACT
  session_id: <required only for RESUME_EXACT>

authority:
  project_engineering_ruleset_preflight: PASS
  engineering_preflight_gate: PASS | NOT_REQUIRED
  authority_refs: [<narrow canonical refs>]
  repair_stage: INITIAL | NORMAL_REPAIR | EXCEPTIONAL_REPAIR

target:
  repo: woshixiong/trader-assist-v0
  live_main_sha: <sha>
  exact_base_sha: <sha>
  expected_head_sha: <sha>
  branch: <branch>
  worktree: <absolute path>

objective: <one coherent objective>
root_cause: <frozen by L1 when material>
allowed_paths: [<paths>]
prohibited_scope: [<explicit boundaries>]
frozen_invariants: [<invariants>]
required_behavior: [<requirements>]
test_plan: [<commands/gates>]
stop_conditions: [<fail-closed conditions>]
output_contract: RESULT_PACKET

user_gates:
  mark_ready: NOT_AUTHORIZED
  merge: NOT_AUTHORIZED
  deploy: NOT_AUTHORIZED
  runtime_cloud: NOT_AUTHORIZED
  credentials_private_api: NOT_AUTHORIZED
  signing_wallet_exchange: NOT_AUTHORIZED
```

Do not prepend volatile timestamps or long histories. Do not ask the Writer to rediscover an L1-frozen route. If architecture-critical information changes after issuance, void the packet and issue one complete replacement rather than appending patches.

The field model intentionally aligns with the project's existing Lossless Task Packet concepts so later Hermes integration can reuse the same semantics instead of inventing another authority model.

---

## 5. Mandatory DSH session baseline

Normal project Writer session after lightweight setup verification:

```text
PROVIDER=deepseek-official
AGENT_PRESET=code / PTC
PERMISSION_PRESET=workspace-write
APPROVAL_POLICY=ask
PROVIDER_RETRY_POLICY=normal
DANGER_FULL_ACCESS=NO
PRODUCTION_CREDENTIALS=NO
PROJECT_MAIN_WORKTREE_MUTATION=NO
ISOLATED_WORKTREE=YES_FOR_WRITER_MUTATION
MODEL_AND_REASONING=L1_FROZEN_PER_TASK
```

Settings that change defaults apply to new sessions; create a new session after a preset/permission/model-default change when the current session cannot safely adopt it.

Do not customize shipped `maxTokens`, compaction thresholds, instruction-byte budget or plugin composition merely for optimization before measured evidence shows a real need.

---

## 6. Lightweight setup verification; real coding validation is deferred to real work

The first read-only qualification at exact PR #108 historical head `e8891d0fb8270e83fd34e9790d341932a02846f0` already demonstrated:

```text
OFFICIAL_PROVIDER_ROUTE=PASS
CODE_PRESET_SELECTED=PASS          # PTC mode
WORKSPACE_WRITE_PLUS_ASK=PASS
ISOLATED_WORKTREE=PASS
AGENTS_GOVERNANCE_DISCOVERY=PASS
READ_ONLY_REPOSITORY_UNDERSTANDING=PASS
NO_FILE_MUTATION=PASS
NO_GIT_MUTATION=PASS
NO_GITHUB_MUTATION=PASS
TOKEN_USAGE_CAPTURE=PASS
CACHE_USAGE_CAPTURE=PASS
RAW_EVIDENCE_CAPTURE=PASS
```

The original qualification intentionally read the full governance set and observed a large prompt surface; that proved correctness but is **not** the normal Writer context design.

No separate synthetic coding qualification or harness-only independent review is required before the first real bounded task. The remaining setup work is intentionally small and mechanical:

```text
EXPECTED_DSH_VERSION_VISIBLE=PASS
DEEPSEEK_OFFICIAL_PROVIDER_VISIBLE=PASS
FLASH_AND_PRO_CATALOG_VISIBLE=PASS
PTC_CODE_PRESET_VISIBLE=PASS
WORKSPACE_WRITE_PLUS_ASK_VISIBLE=PASS
ROOT_AGENTS_AUTOLOAD=PASS
FOUR_PROJECT_SKILLS_DISCOVERED=PASS
SKILL_BODY_LOADS_ON_DEMAND=PASS
SKILL_BODY_NOT_ALWAYS_INJECTED=PASS
CACHE_TELEMETRY_VISIBLE=PASS
WARM_STABLE_PREFIX_CACHE_HIT_OBSERVED=PASS
NO_FILE_GIT_GITHUB_MUTATION_DURING_SETUP_CHECK=PASS
```

The cache check should use a tiny read-only repeated/stable-prefix request in the same session. It only needs to demonstrate that provider cache usage is observable and nonzero under a reusable prefix; no arbitrary target percentage is required.

After these checks:

```text
DEEPSEEK_HARNESS_SETUP=READY_FOR_BOUNDED_REAL_TASK
```

The first actual small Trader Assist task assigned to DeepSeek Harness becomes the real capability validation. It must use the normal frozen Task Packet, isolated worktree, task-specific tests/evidence and normal project review requirements for that task. Do not create an extra development exercise or extra review solely to validate the Harness.

---

## 7. Future Hermes integration seam

When the project later automates DeepSeek Harness, prefer native non-interactive/headless DSH rather than GUI Computer Use whenever the exact required behavior is supported:

```text
Hermes frozen packet transport
→ verify exact dsh version / packet / worktree / model
→ dsh --profile headless <frozen job>
→ collect raw Result Packet/evidence
→ normal downstream task review
```

Current merged Hermes Task Packet/operator contract does not yet enumerate `DEEPSEEK_HARNESS`; Hermes H2 dispatch to DSH remains prohibited until a later bounded schema/profile change is independently accepted.

Hermes remains an L3 low-cost/free-model operator. It does not become the DeepSeek coding model, choose DeepSeek/Trae/Codex, invent repairs, or evaluate independent acceptance.

---

## 8. Current tooling priority

The current user priority as of 2026-08-18 is:

```text
NEXT_1=CODEX_CONFIGURATION_AND_EFFICIENCY_PROFILE
- configure Codex first because it is immediately needed for development;
- inspect the installed Codex version and current official configuration surface;
- configure safe user/project settings;
- optimize AGENTS/project-doc byte budgets, skills, stable prompts and session resume;
- define model/reasoning tiers from current official model availability;
- use deterministic mechanics before model tokens;
- measure token/cache/time/rework only where the evidence is useful;
- keep Codex as a peer coding executor.

NEXT_2=DEEPSEEK_HARNESS_LIGHTWEIGHT_SETUP_VERIFICATION
- perform only the preset/skills/cache checks in section 6;
- do not create a separate synthetic coding task or harness-only review;
- validate real coding capability on the first actual small assigned task.

NEXT_3=HERMES_CONFIGURATION
- configure an approved free or low-cost operator model and minimum permissions/toolsets;
- H0/H1 lossless transport/evidence qualification;
- later add DEEPSEEK_HARNESS to the Lossless Task Packet only through a separately accepted schema/profile change;
- use native DSH headless seam where supported.
```

These are tooling priorities, not authority for Mark Ready, merge, deployment, runtime or other retained user gates.

---

## 9. Permanent boundaries

This specialized rule does not authorize:

- autonomous executor/model switching;
- autonomous engineering repair/replan/retry beyond a frozen packet;
- unbounded provider retry mode;
- Hermes H2 dispatch to DSH before schema/profile acceptance;
- Mark Ready or merge;
- deployment/runtime/cloud mutation;
- credential/private API/account access outside the explicit DeepSeek provider credential needed for model calls;
- wallet/signing/exchange write/order/trading actions.

Any such boundary requires the existing explicit current user authorization and canonical project governance path.