# Trader Assist / Trade OS — Codex Profile Research Evidence Snapshot V1

**Status:** RESEARCH / EVIDENCE SNAPSHOT FOR PR #117  
**Original research date:** 2026-08-20  
**Latest re-verification:** 2026-08-23  
**Repository:** `woshixiong/trader-assist-v0`

This file records the evidence used to design the Codex CLI profile and GPT-control-first execution-class routing. It is not an independent acceptance and grants no publication/runtime/trading authority.

## 1. Independent analysis before external research

The project should not pay coding-Agent token/credit/context cost for work that an Engineering/Review GPT window can complete directly with GitHub/connectors or with a deterministic one-paste Terminal block. Once a task genuinely requires local semantic code inspection/mutation/debug/repair, Codex should use the narrowest provider-native execution seam with explicit task-local model/reasoning/permission configuration, exact session identity, small stable project instructions, local repository context discovery, and passive usage evidence.

The main optimization target is accepted useful work per total cost:

```text
MODEL INPUT/OUTPUT/REASONING
+ CACHED/UNCACHED INPUT ECONOMICS
+ RETRIES/REWORK
+ REVIEW
+ HUMAN RELAY
+ TOOL/CONTEXT BOOTSTRAP
```

Candidate routes considered before external research:

1. use Codex for every engineering stage including publication/review;
2. route noncoding stages to GPT Control / deterministic Terminal and reserve Codex for code-semantic work;
3. persistent interactive TUI versus non-interactive `codex exec`;
4. new session every turn versus exact trusted-stage resume;
5. one large permanent Codex context versus small stable project instructions + exact task packet + local inspection;
6. hidden global model defaults versus explicit task-local model/reasoning/sandbox choices;
7. general-purpose model default versus task-tiered Sol/Terra/Luna routing;
8. speculative SDK/App Server/MCP/Skills versus provider-native CLI first.

Pre-research preference: route noncoding mechanics away from Codex, use `codex exec` for bounded code work, keep project instructions small, make model/version facts refreshable, use exact-session continuation only inside one coherent trusted stage, and measure cache/token evidence passively rather than creating benchmark calls.

## 2. External first-party evidence checked

OpenAI/Codex first-party material checked includes current documentation for:

- Codex non-interactive mode and `codex exec`;
- Codex CLI/reference and configuration reference;
- Codex `AGENTS.md` instruction discovery;
- Codex Skills/progressive disclosure;
- GPT-5.6 model guidance and Sol/Terra/Luna model pages;
- GPT-5.6 availability in Codex;
- Codex rate card / cached-input accounting;
- prompt caching principles;
- current Codex distribution/package surface.

Key current first-party findings:

- `codex exec` is the native non-interactive route for scripting/pipeline/CLI work and can return control to the ordinary shell after the turn.
- `codex exec --json` exposes structured JSONL events including session/thread identity and usage; current examples include input, cached-input, output and reasoning-output token fields.
- `codex exec resume <SESSION_ID>` can continue an exact persisted session. `--last` exists as convenience but does not carry authority-grade identity.
- Codex supports task-local model, working-directory, sandbox, approval and config overrides. Explicit launch choices can override ordinary defaults.
- Current public Codex configuration documents `model_reasoning_effort` through `xhigh`; product-level GPT-5.6 materials additionally advertise `max` in Codex and `ultra` for eligible plans. Therefore a one-paste CLI workflow must verify the installed task-local seam before encoding Max/Ultra rather than assuming a product/UI control is a documented CLI config value.
- GPT-5.6 Sol is the frontier choice for complex reasoning/coding; Terra balances intelligence/cost; Luna is optimized for cost-sensitive/high-volume work.
- Current Codex availability includes Sol/Terra/Luna for eligible paid plans and Terra for Free/Go.
- Current GPT-5.6 model pages expose very large context, but this is capacity rather than a reason to provide unnecessary context.
- Prompt-cache reuse benefits stable exact prefixes with dynamic content later; Codex JSONL can passively reveal cached input without an extra model turn.
- Current Codex rate material shows cached input much cheaper than uncached input; rate/plan facts are refreshable and must not be confused with direct API billing semantics.
- `AGENTS.md` is loaded before Codex works. Global `$CODEX_HOME/AGENTS.md` is inherited by every repository, while project instructions are layered from repository root toward the working directory. The default combined project-instruction ceiling is 32 KiB.
- `$CODEX_HOME/AGENTS.override.md` overrides the global base file and is designed for override behavior, not as a permanent project-specific rule store.
- Skills support progressive disclosure; this supports adding a focused Skill only after repeated real tasks prove the workflow is worth encoding, rather than turning all governance into always-loaded Skills.

## 3. Synthesis and selected route

External evidence confirms the independent route with two important refinements.

First, context/cache efficiency is not only about shorter prompts. A stable prefix, small `AGENTS.md`, exact local code discovery, coherent session reuse and deterministic shell/Git mechanics outside model tokens all reduce total cost without weakening authority.

Second, model/reasoning/provider facts move faster than the durable CLI workflow. Therefore:

```text
Layer A = stable execution-class + executor routing
Layer B = stable Codex CLI workflow core
Layer C = refreshable current model/reasoning/rate/service snapshot
```

Routine model upgrades update Layer C only. Layer B changes only when durable CLI/session/context/permission/evidence semantics change. Layer A changes only when the execution-class or L1/L2 authority model changes.

The selected route is:

```text
GPT_CONTROL_DIRECT
→ GPT_CONTROL_DETERMINISTIC_TERMINAL
→ L2_CODING_EXECUTOR only if local semantic code work is required
   → when Codex selected: one-paste `codex exec`
      + explicit task-local model/reasoning/sandbox
      + small project instructions
      + complete frozen Task Packet
      + local exact code inspection
      + exact-session resume only inside same trusted stage
      + JSONL passive usage/evidence
```

## 4. Counterexamples / rejected defaults

Rejected as project defaults:

- coding Agent for GitHub-only publication or other connector-sufficient work;
- coding Agent for deterministic commit/push of an already accepted artifact;
- persistent TUI for every bounded Writer stage;
- `resume --last` as automation identity;
- new session after every process exit;
- stale-session resume solely for cache savings;
- global project-specific `~/.codex/AGENTS.md` duplicating repository governance;
- giant always-loaded Codex instruction corpus;
- hidden remembered model/reasoning defaults;
- Fast/Max/Ultra/Pro-like/broad-permission modes as prestige defaults;
- API-only cache controls treated as if they were Codex CLI controls;
- speculative Skills, MCP, App Server or SDK layers without measured need.

## 5. Writer-side normal repair before independent review

The initial route exposed two self-review problems:

1. making downstream Codex reread the full specialized governance profiles on every Writer run would undercut token/context efficiency;
2. freezing universal Fast speed/credit multipliers would make a durable workflow depend on moving commercial facts.

These were repaired before independent review by:

- making full Codex profile reading an **Engineering Control pre-dispatch** responsibility and allowing a downstream Codex Writer with a complete frozen packet to avoid automatic full-profile rereads;
- retaining Standard/Fast policy while moving exact current commercial/speed facts behind current-surface verification.

This is the route's Writer-side `NORMAL_REPAIR`; Writer PASS remains non-independent.

## 6. 2026-08-23 first-party re-verification addendum

Before final independent-review dispatch, the material first-party claims were refreshed again on 2026-08-23. This addendum does not replace the original independent-analysis record above and does not create a new design route.

Current first-party recheck confirms:

- OpenAI's current model guidance still routes `gpt-5.6` to `gpt-5.6-sol`, recommends Sol for complex/uncertain work, Terra for intelligence/cost balance, and Luna for cost-sensitive/high-volume work.
- Current Codex availability exposes Sol, Terra and Luna to eligible paid plans and Terra to Free/Go; exact local/account availability is still verified at dispatch.
- Current GPT-5.6 product material says `max` is available in Codex for users with GPT-5.6 access and `ultra` is available to eligible Plus-and-higher Codex plans, while the public Codex config reference still documents task/config `model_reasoning_effort` only through `xhigh`. The project therefore verifies the installed one-paste CLI seam before encoding Max/Ultra.
- Current Codex non-interactive documentation still defines `codex exec` as the script/pipeline/CLI surface, supports explicit sandbox/approval settings, JSONL output, and exact `codex exec resume <SESSION_ID>` continuation.
- Current JSONL examples expose `input_tokens`, `cached_input_tokens`, `output_tokens`, and `reasoning_output_tokens`, so passive cache/usage measurement does not require an extra model turn.
- Current `AGENTS.md` guidance still uses global plus root-to-working-directory project layering and a 32 KiB default combined project-instruction ceiling. Because global `$CODEX_HOME/AGENTS.md` is inherited across repositories, Trader Assist project rules remain in the repository root; a global file, if present, should remain small and cross-repository only. `AGENTS.override.md` is not a permanent Trader Assist rule location.
- Current Skills guidance explicitly uses progressive disclosure. This supports measured focused Skills rather than always-loaded workflow duplication.
- Current prompt-caching guidance still favors exact stable prefixes with mutable content later. API-specific cache keys/breakpoints/write billing remain API facts and are not treated as Codex CLI controls unless separately exposed there.
- Current Codex rate material still reports cached input at a substantial discount and the current GPT-5.6 Codex credit table used by Layer C. Commercial facts remain refreshable and plan/surface-specific.
- Current GPT-5.6 help material still gives Codex CLI `0.144.0` as the minimum GPT-5.6 access version; this remains a compatibility floor rather than a permanent project pin.
- The current public `@openai/codex` npm distribution observed on 2026-08-23 is `0.149.0`. This is recorded only as a moving evidence point. Real Writer dispatches mechanically run `codex --version` and do not assume this evidence snapshot remains latest.

The re-verification does not change the Layer A/B architecture. The user's additional 2026-08-23 scope clarification is now also explicit in root `AGENTS.md`: when exact GitHub artifacts and exact-head CI are sufficient, a separate ordinary GPT window with the strongest appropriate reasoning is the default independent-review route; coding-Agent review is reserved for cases that actually require local execution or local semantic code-environment access.

Current live repository context at this addendum is `main=a97fff5c45eaffe86157c9ebfa2d01a58188586b`. The proposal branch was created from earlier main `c8946512cc77254b53093ebac29a6fdc51d17721`; intervening PR #118 touched Issue #112 runtime/test paths rather than this proposal's governance/docs paths. Final independent review must verify live drift/non-overlap itself rather than trusting this statement.