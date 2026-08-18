# Trader Assist / Trade OS — Engineering Executor Pool and DeepSeek Harness Profile V1

**Status:** DRAFT GOVERNANCE  
**Effective date:** 2026-08-18  
**Repository:** `woshixiong/trader-assist-v0`  
**Base main when drafted:** `4b8719ca44f9ff9d459910690183ca9b790b726d`  
**Scope:** project execution-layer separation and the bounded DeepSeek Harness coding-executor profile.

This specialized profile complements the canonical Unified Engineering Governance and merged Hermes operator contract. It grants no Mark Ready, merge, deployment, runtime/cloud mutation, credential/private-API, signing/wallet, exchange-write, order-submission or trading authority.

---

## 1. Frozen engineering-layer architecture

```text
L1 — DECISION / CONTROL
Human + high-capability Engineering / Strategy / Product / Operations ChatGPT
        ↓ freezes task, route, executor, model, permissions, acceptance and stop conditions

L2 — CODING EXECUTOR POOL
Codex CLI | Trae | DeepSeek Harness
        ↓ code / tests / Git / authorized PR + CI work

L3 — ROUTINE AUTOMATION / OPERATOR
Hermes + approved low-cost/free model
        ↓ exact packet transport, launch, wait/poll and mechanical evidence work

L4 — FOUNDATIONAL TOOLS
Terminal | Git | GitHub | CI | browser | local applications
```

### 1.1 Three peer coding executors

The project retains all three coding tools:

- `CODEX_CLI`;
- `TRAE_COMPUTER_USE` / Trae interactive coding;
- `DEEPSEEK_HARNESS` after lightweight setup verification.

No tool is the universal Writer. L1 assigns the exact executor/model for each bounded task by capability, quality, cost, speed and availability.

For one coherent shared-authority stage there is exactly one primary Writer. Parallel execution is allowed only for read-only/disjoint work whose contracts, worktrees and integration ownership are frozen. Competing Writers must not mutate the same shared authority or release branch.

### 1.2 Hermes is not a fourth coding executor

Hermes plus a free/approved low-cost model is a separate L3 operator. It does not decide technical routes, select or substitute coding executors, invent repairs, review engineering acceptance or become a trading authority.

The merged `HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md` remains binding when Hermes is active.

---

## 2. DeepSeek route is fixed to first-party Harness

For DeepSeek API coding work the selected route is:

```text
DEEPSEEK_PRIMARY_HARNESS=DEEPSEEK_HARNESS
DEEPSEEK_PRIMARY_PROVIDER=deepseek-official
```

Do not spend project effort benchmarking DeepSeek through Codex or another harness as a prerequisite. Codex and Trae remain independent peer coding executors, not alternate DeepSeek wrappers.

Current setup baseline:

```text
DSH_VERSION=0.1.0-rc.7
UPSTREAM_RELEASE_SHA=99f6f02fecdb7dff40c3fbc9470f5907c29f74ca
```

DeepSeek Harness is Developer Preview. Keep its integration behind the replaceable executor seam and verify/pin the expected DSH version for authority-bearing automated runs.

---

## 3. Provider-native DSH operating profile

The binding detailed rule is:

`governance/DEEPSEEK_HARNESS_MANDATORY_USAGE_RULES_V1_2026-08-18.md`

Normal coding profile after lightweight setup verification:

```text
PROVIDER=deepseek-official
AGENT_PRESET=code / PTC
PERMISSION_PRESET=workspace-write
APPROVAL_POLICY=ask
PROVIDER_RETRY_POLICY=normal
DANGER_FULL_ACCESS=NO
PROJECT_MAIN_WORKTREE_MUTATION=NO
ISOLATED_WORKTREE=YES_FOR_WRITER_MUTATION
MODEL_AND_REASONING=L1_FROZEN_PER_TASK
```

The shipped DeepSeek adapter's bounded normal provider retry policy may retry transient model-request failures, but that is transport recovery only. Unbounded `always` provider retry is not part of the project profile, and no provider retry grants engineering repair/replan authority.

### 3.1 Reasoning tiers use actual DeepSeek semantics

The official provider's effective thinking controls are ON/OFF plus `high` / `max`; compatibility `low`/`medium` map to `high`, and `xhigh` maps to `max`.

Project defaults:

```text
Flash + OFF  = deterministic/narrow mechanical work where reasoning is unnecessary
Flash + HIGH = ordinary bounded coding
Pro   + HIGH = material implementation / difficult debugging
Pro   + MAX  = exceptional difficult quality-first coding
```

A UI `Low` label is not treated as a cost-saving tier for DeepSeek while it maps to provider `high`.

### 3.2 Keep provider-native defaults unless evidence says otherwise

The current first-party adapter already supplies the official endpoint, model catalog, context-window metadata, reasoning serialization, required tool-call reasoning passback, cache-usage accounting, bounded request timeout and normal finite retry behavior.

Do not customize `maxTokens`, context-window values, retry budgets, compaction thresholds, instruction-byte budget, plugin topology or wire semantics merely for optimization. Change a shipped default only after measured project evidence identifies a concrete problem.

---

## 4. Token-efficient context architecture

The first read-only qualification proved DSH/provider/governance discovery but deliberately loaded the full governance corpus. That was a qualification test, not the normal Writer design.

Normal DSH Writer context is:

```text
DSH / PTC stable composition
→ small stable repository AGENTS.md
→ small stable project skill catalog
→ mandatory writer-preflight skill when execution starts
→ additional skills only on demand
→ frozen Task Packet as the mutable tail
→ narrow authority/source files only when the packet or discovered problem requires them
```

### 4.1 L1 full preflight; L2 bounded execution

L1 remains responsible for full live-GitHub and material-governance preflight before dispatch. A DeepSeek L2 Writer with a valid frozen packet and PASS attestations does not automatically reread every large governance document merely to repeat L1's route decision.

If the packet is stale/ambiguous, HEAD drifts, scope must expand, a new material decision appears, a dependency/service changes, or repository authority conflicts with the packet, the Writer fails closed and returns to L1. It does not improvise.

### 4.2 Keep global DSH instructions minimal

Do not copy project governance into `$DSH_HOME/AGENTS.md`. The project repository remains canonical. Root project `AGENTS.md` is the stable instruction baseline; detailed repeatable mechanics belong in project-local skills.

Do not increase DSH's shipped agent-instruction byte budget merely to inject more prose.

### 4.3 Progressive project skills

Initial project-local DSH skills:

```text
.dsh/skills/trade-os-writer-preflight/SKILL.md
.dsh/skills/trade-os-local-gates/SKILL.md
.dsh/skills/trade-os-evidence/SKILL.md
.dsh/skills/trade-os-result-packet/SKILL.md
```

The skill catalog exposes routing metadata initially; full bodies load when used. Skills contain mechanical procedures only and never acquire L1/review/release/trading authority.

### 4.4 Stable-prefix cache discipline

Keep stable instructions/preset/tool/skill catalog ahead of volatile task facts. Put branch, SHA, current blocker, CI run, timestamp and one-off evidence late in the Task Packet.

Design tasks to remain reasonably efficient at zero cache. Cache hits reduce provider cost/latency but are not permission to send unnecessarily large repeated context.

DeepSeek cache verification is intentionally minimal: a tiny read-only repeated/stable-prefix request in the same session only needs to show observable nonzero provider cache use; there is no arbitrary required hit percentage.

---

## 5. Use shipped DSH capabilities before custom integration

Use this order:

```text
SHIPPED DSH PROFILE/CAPABILITY
→ DSH SETTINGS / PERMISSION / AGENT PRESET
→ PROJECT AGENTS.md
→ PROJECT-LOCAL ON-DEMAND SKILL
→ THIN CUSTOM PLUGIN ONLY AFTER REPEATED MEASURED NEED
```

No custom DSH plugin is authorized for the initial integration.

PTC/Code Mode is preferred for coding because it can compose multiple tool operations into one `run_code`. Keep the shipped tool-result pruning and compaction behavior initially. Prune deterministic tool noise before model-backed compaction; compact only at genuine pressure/coherent substage boundaries.

Subagents/workflows/Ralph are opt-in only. They may not become hidden repair loops, competing shared-authority Writers or independent acceptance substitutes.

---

## 6. Cost scheduling

Current official DeepSeek schedule confirmed 2026-08-18:

```text
TIMEZONE=Asia/Shanghai
PEAK=09:00-12:00,14:00-18:00
OFF_PEAK=00:00-09:00,12:00-14:00,18:00-24:00
OFF_PEAK_PRICE=0.5 × PEAK
```

Delay-tolerant DeepSeek work should use off-peak windows where practical. Urgent/release-critical work is not delayed solely for cost. Provider state supersedes this snapshot if DeepSeek changes the schedule.

---

## 7. Lightweight setup verification only

Read-only qualification has already passed at PR #108 historical head `e8891d0fb8270e83fd34e9790d341932a02846f0`, proving the provider route, PTC mode, workspace-write/ask safety baseline, isolated worktree, governance discovery, no mutation, token/cache telemetry and raw evidence capture.

No separate synthetic development qualification and no Harness-only independent review are required.

The remaining mechanical setup check is limited to:

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

After that, DeepSeek Harness is ready for a **first real small bounded task**. That real task is the capability validation and must follow the normal task-specific Task Packet, isolated worktree, tests/evidence and review rules already required by project governance. Do not create an extra coding exercise or extra review solely to validate the Harness.

---

## 8. Future Hermes integration

When DSH automation is later authorized, native DSH headless execution is the preferred Hermes seam when supported:

```text
L1 frozen packet
→ Hermes validates/transports exact packet
→ exact DSH version/worktree/model verification
→ dsh --profile headless <job>
→ raw Result Packet/evidence
→ normal downstream task review
```

Current merged Hermes schema does not enumerate `DEEPSEEK_HARNESS`; Hermes H2 dispatch to DSH remains prohibited until a later bounded schema/profile change receives independent acceptance.

Trae remains the GUI/Computer-Use executor path. Codex remains a native CLI coding executor. DeepSeek Harness uses its native headless seam.

---

## 9. Current tooling priority, in order

The user has reprioritized tooling work because Codex is needed immediately for active development:

```text
NEXT_1=CODEX_CONFIGURATION_AND_EFFICIENCY_PROFILE
- inspect current local Codex version/config/model surface;
- configure safe user/project settings;
- optimize AGENTS/project-doc byte budgets and progressive skills;
- define stable-prefix Task Packet prompting and same-stage session resume;
- define current model/reasoning tiers from live official capability;
- prefer deterministic mechanics before model tokens;
- measure token/cache/time/rework where useful.

NEXT_2=DEEPSEEK_HARNESS_LIGHTWEIGHT_SETUP_VERIFICATION
- verify only the preset/skills/cache behaviors in section 7;
- defer real coding validation to the first actual small DeepSeek task.

NEXT_3=HERMES_CONFIGURATION
- install/configure an approved free or low-cost model;
- minimum toolsets/permissions;
- H0/H1 lossless transport and evidence qualification;
- later add DEEPSEEK_HARNESS to the machine schema/profile through a separately accepted change.
```

These are committed tooling priorities, not execution authority for retained user gates.

---

## 10. Permanent boundaries

No tool profile or setup verification implicitly authorizes:

- Mark Ready;
- merge;
- deployment;
- production/runtime/cloud mutation;
- service start/restart/enable/reboot;
- credentials/private APIs outside the specifically authorized model credential;
- wallet/signing/nonce;
- real notifications when separately gated;
- exchange writes/order submission/cancellation;
- autonomous trading/financial action.

All remain separate current user authority gates.

---

## 11. Mandatory preflight record for this route

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
TASK_CLASS=MATERIAL
LIVE_REPO=woshixiong/trader-assist-v0
LIVE_MAIN_SHA=4b8719ca44f9ff9d459910690183ca9b790b726d
ACTIVE_ISSUE_OR_PR=PR #108
INDEPENDENT_ANALYSIS_DONE=YES
EXTERNAL_RESEARCH_DONE=YES
SYNTHESIS_DONE=YES
ROOT_CAUSE_LEVEL=ARCHITECTURAL
AFFECTED_AUTHORITIES=L1/L2 execution boundary; DSH context; future Hermes transport seam
FROZEN_INVARIANTS=GitHub canonical; three peer coding executors; Hermes separate L3 operator; one primary Writer; normal task review; user-retained gates
CURRENT_ROUTE=DeepSeek API via first-party DSH; lean stable AGENTS + progressive skills + frozen Task Packet; provider-native capabilities first
MATURE_ALTERNATIVES_CONSIDERED=full governance reread every task; duplicated global DSH instructions; giant always-loaded capsule; custom DSH plugin; alternate DeepSeek harness wrappers; synthetic Harness coding benchmark
CURRENT_NEED=low-token reliable DeepSeek coding executor without unnecessary qualification overhead
NEXT_EXPECTED_STAGE=Codex configuration first → DSH lightweight preset/skills/cache verification → Hermes configuration; first real small DSH task supplies coding capability evidence
STABLE_INTERFACES=Task Packet; executor assignment; worktree; tests; evidence; Result Packet; normal independent review when the actual engineering task requires it
REPLACEABLE_IMPLEMENTATION_SEAMS=executor profile; project skills; future Hermes launch adapter
KNOWN_REWRITE_OR_LOCKIN_RISK=DSH Developer Preview, bounded by exact-version verification and narrow executor seam
OVERENGINEERING_CHECK=PASS
PROVIDER_SCALE_BUDGET=PASS_BY_TOKEN/CACHE_TELEMETRY_SETUP_VERIFICATION
FRESHNESS_OR_LATENCY_GATE=off-peak preferred; current official schedule recorded; urgent work not delayed solely for cost
ATTACK_MATRIX_FROZEN=YES
REPAIR_STAGE=INITIAL
STOP_CONDITION=incompatible upstream change, stale/invalid packet, authority ambiguity, scope expansion or new material design choice
WRITER_SCOPE=governance/docs/project DSH skills only
PROHIBITED_SCOPE=runtime/product/strategy/Hermes schema/production/credentials/merge
ROLLBACK_OR_SAFE_STOP=discard PR #108 branch; main remains unchanged
```