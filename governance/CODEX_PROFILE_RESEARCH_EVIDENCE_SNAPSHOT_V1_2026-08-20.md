# Codex Profile Research Evidence Snapshot V1 — 2026-08-20

**Status:** REVIEW EVIDENCE / NON-RUNTIME GOVERNANCE  
**Repository base at research start:** `c8946512cc77254b53093ebac29a6fdc51d17721`

This file records the required three-stage research trail for the Codex configuration/profile decision. It grants no implementation/publication/runtime/account/trading authority.

## 1. Independent analysis — before external solution research

The project problem is not simply "configure Codex." It has three coupled cost/correctness questions:

1. which tasks genuinely require a local coding Agent versus ordinary GPT control or deterministic shell/Git mechanics;
2. when Codex is required, which provider-native execution/session/context pattern minimizes duplicate work and user relay;
3. how model/reasoning choice should trade first-pass success against token/credit cost without becoming model-version architecture.

Pre-research position:

```text
A. ROUTE EXECUTION CLASS BEFORE MODEL
   ordinary GPT/connectors for connector-sufficient work
   deterministic Terminal for frozen mechanics
   coding Agent only for semantic local code work

B. CODEX CLI-FIRST
   use the provider-native non-interactive CLI if it supports exact workdir,
   model/reasoning, sandbox, persisted session continuation and usage evidence

C. CONTEXT ECONOMY
   small stable repository instruction surface
   stable control prefix + mutable task tail
   exact local code inspection rather than repasting source/history
   resume only inside one trustworthy coherent stage

D. MODEL VERSION IS A REFRESHABLE POLICY
   stable CLI/session rules must survive model upgrades
   current model/reasoning/cost facts belong in a replaceable Layer C profile

E. PUBLICATION IS NOT CODING
   accepted artifact publication should not consume coding-Agent tokens unless
   a new code judgment/repair is actually required
```

Evidence that could falsify/modify this view included: Codex CLI lacking reliable noninteractive/exact-session controls; first-party guidance requiring persistent TUI; current model surfaces lacking task-local model/reasoning control; provider cache behavior making session/prefix discipline irrelevant; or GitHub/publication steps materially requiring code-agent semantics.

## 2. External first-party evidence

Research then checked current OpenAI first-party Codex/API/help material and current `openai/codex` source. Key findings:

- OpenAI positions Codex for understanding codebases, building/testing features, fixing bugs and reviewing changes, while Chat/Work cover broader conversational/research/knowledge work. This supports capability-based routing rather than using Codex for every engineering-adjacent action.
- Codex provides native noninteractive `codex exec`, task-local working-directory/model/sandbox/config controls, JSONL execution evidence and exact session resume. The narrower CLI route is sufficient for the current one-paste workflow; SDK/App Server/MCP are not required merely to reproduce it.
- Codex project instructions use `AGENTS.md`; current guidance supports layered repository instructions. Keeping the root instruction surface small is compatible with provider-native behavior.
- Codex Skills use progressive disclosure. This supports adding skills only for measured repeated workflows rather than duplicating static governance into always-loaded context.
- GPT-5.6 current model guidance distinguishes Sol for frontier complex reasoning/coding, Terra for intelligence/cost balance, and Luna for cost-sensitive high-volume work. OpenAI recommends Sol when model fit is genuinely uncertain.
- GPT-5.6 guidance recommends intentionally selecting reasoning effort and comparing representative workloads at the same and one-lower effort instead of assuming more reasoning is always better.
- Current Codex rate material prices cached input substantially below uncached input and states Codex cache writes are not charged on the current token-based rate-card path. Current direct API cache/billing controls differ, so API-only cache semantics must not be assumed to be Codex CLI controls.
- Current GPT-5.6 API guidance emphasizes exact-prefix prompt caching and mutable content later; Codex JSONL exposes cached-input usage evidence. This supports stable-prefix/mutable-tail design and passive real-task measurement.
- Current first-party material shows Fast is a latency/service-tier feature with a usage premium rather than an intelligence tier. Exact plan/rate behavior can change, so it belongs in the refreshable current-model profile.
- Current GPT-5.6 access material requires Codex CLI `0.144.0` or later for GPT-5.6 access; this is a current compatibility floor, not a permanent project pin.

Primary sources checked include current pages under:

- `developers.openai.com/codex/...`
- `developers.openai.com/api/docs/models`
- `developers.openai.com/api/docs/guides/latest-model`
- `developers.openai.com/api/docs/guides/prompt-caching`
- `help.openai.com` current GPT-5.6/Codex availability and Codex rate-card material
- `github.com/openai/codex` current source for evolving reasoning-effort support.

## 3. Synthesis and final route

External evidence **confirmed** the independent CLI-first, exact-session, stable-prefix, capability-routing approach. It also refined the route in three ways:

1. current model guidance justifies a three-level practical matrix: Luna only for very low-ambiguity strongly validated coding, Terra for ordinary bounded coding when clearly sufficient, and Sol for difficult/uncertain/high-consequence work;
2. model/reasoning/service-tier facts must be a refreshable Layer C because current surfaces evolve faster than durable project workflow;
3. provider/API capabilities such as explicit cache keys, persisted reasoning, Pro/Max/Ultra-like modes or exact Fast multipliers must not be transferred into Codex CLI without current surface verification.

The selected route is therefore:

```text
EXECUTION CLASS
GPT_CONTROL_DIRECT
→ GPT_CONTROL_DETERMINISTIC_TERMINAL
→ L2_CODING_EXECUTOR only when genuinely required

IF L2=CODEX_CLI
→ LAYER B stable Codex CLI core
→ LAYER C refreshable current model profile
→ one-paste `codex exec`
→ task-local model/reasoning/sandbox
→ exact session resume only within one trusted stage
→ JSONL passive token/cache evidence
→ independent review
→ publication routed back to GPT Control where possible
```

Rejected current defaults:

- coding Agent for GitHub-only publication;
- coding Agent for deterministic commit/push of an already accepted artifact;
- persistent TUI as bounded Writer default;
- new session every turn;
- resume-everything merely for cache hits;
- Fast as default;
- Max/Ultra/Pro-like mode as default;
- speculative Skills/MCP/App Server/SDK orchestration;
- global model defaults as hidden authority;
- API-only cache controls treated as Codex CLI controls.

## 4. Residual validation plan

Do not manufacture paid benchmark tasks. On real Codex tasks, passively retain:

```text
CODEX_VERSION
MODEL / REASONING / SERVICE_TIER
NEW_OR_RESUME_EXACT + SESSION_ID
INPUT / CACHED_INPUT / OUTPUT / REASONING_OUTPUT where exposed
ELAPSED_TIME
MODEL_RETRY_COUNT
ENGINEERING_REPAIR_REWORK_COUNT
FINAL_ACCEPTANCE
```

Use accumulated real evidence to refine the Luna/Terra/Sol and reasoning-effort boundaries. No arbitrary cache-hit percentage is a correctness gate.

## 5. Writer-side repair note

Writer self-review found two issues before independent review:

1. the first draft could cause downstream Codex to reread large specialized profiles on every run, conflicting with the token-efficiency objective;
2. the first draft froze Fast speed/credit multipliers too aggressively despite current first-party surface/plan variation.

These were repaired before independent review by:

- making full Codex profile reading an **Engineering Control pre-dispatch** responsibility and allowing a downstream Codex Writer with a complete frozen packet to avoid automatic full-profile rereads;
- retaining Standard/Fast policy while moving exact current commercial/speed facts behind current-surface verification.

This is the route's Writer-side `NORMAL_REPAIR`; Writer PASS remains non-independent.