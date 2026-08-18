# Trader Assist / Trade OS — Codex Non-Interactive Execution and Session Policy V1

**Status:** DRAFT SPECIALIZED GOVERNANCE  
**Effective date:** 2026-08-19  
**Repository:** `woshixiong/trader-assist-v0`  
**Scope:** Codex CLI execution mode, session identity/reuse, token/cache telemetry, human-assisted routing, and future Hermes transport.

This specialized rule complements `governance/UNIFIED_ENGINEERING_GOVERNANCE_AND_EXECUTION_STANDARD_V1_2026-08-17.md`, especially sections 19–21. It does not replace normal project preflight, Task Packet, Writer/Reviewer separation, tests, CI, repair budget, or explicit user-retained authority gates.

It grants no Mark Ready, merge, deployment, runtime/cloud mutation, credentials/private API, wallet/signing, exchange write, order submission/cancellation, or trading authority.

---

## 1. Decision

The default Trader Assist / Trade OS Codex route is provider-native non-interactive Codex CLI execution:

```text
CODEX_DEFAULT_EXECUTION_MODE=codex exec
CODEX_INTERACTIVE_TUI_POLICY=OPT_IN_HUMAN_PAIRING_OR_EXPLORATION_ONLY
CODEX_NEW_SESSION_POLICY=DEFAULT_FOR_NEW_TASK_ROLE_WORKTREE_AUTHORITY_OR_MATERIAL_STAGE
CODEX_RESUME_POLICY=EXACT_SESSION_ID_ONLY_FOR_SAME_WRITER_TASK_COHERENT_STAGE_WORKTREE_AUTHORITY
CODEX_RESUME_LAST_POLICY=NOT_AN_AUTOMATION_DEFAULT
CODEX_SESSION_ID_CAPTURE=REQUIRED_FOR_RESUMABLE_ROUTED_RUNS
CODEX_JSONL_POLICY=DEFAULT_FOR_ENGINEERING_ROUTED_OR_HERMES_MANAGED_RUNS_WHEN_MACHINE_PARSING_IS_AVAILABLE
CODEX_TOKEN_TELEMETRY_POLICY=CAPTURE_WHEN_AVAILABLE_WITHOUT_EXTRA_MODEL_TURNS
CODEX_PERMISSION_POLICY=EXPLICIT_PER_TASK_AND_SEPARATE_FROM_PERMANENT_PROJECT_AUTHORITY_GATES
HERMES_CODEX_TRANSPORT_POLICY=NATIVE_CODEX_EXEC_FIRST
HERMES_DEEPSEEK_TRANSPORT_POLICY=NATIVE_DSH_HEADLESS_FIRST_WHEN_SEPARATELY_AUTHORIZED
```

The default one-paste macOS workflow therefore ends with the Codex process exiting and control returning to the ordinary shell.

---

## 2. Why `codex exec` is the default

OpenAI's first-party Codex documentation defines `codex exec` as the non-interactive mode for scripts, pipelines, CI and CLI workflows. It does not open the interactive TUI, supports explicit sandbox/permission settings, and exits when the task is complete.

This matches the project execution split:

```text
L1 Engineering Control
→ frozen Writer Task Packet
→ L2 Codex Writer
→ deterministic shell/local gates
→ exact artifact / CI
→ independent Reviewer
```

A persistent foreground TUI adds user-routing ambiguity when the next step is a shell gate, CI poll, evidence command, or another role. Keeping a TUI open is therefore not a token optimization by itself and is not the default automation seam.

Interactive Codex remains valid when the user intentionally wants human pair-programming, exploratory dialogue, or live steering in one conversation.

---

## 3. Session identity and reuse

### New session

Start a new Codex session/thread when any material identity dimension changes:

- new task;
- new Writer role;
- new worktree;
- new authority context;
- independent Reviewer or security/authority review;
- material stage change;
- route reset / clean adjudication;
- prior context is stale, ambiguous, untrusted, or contaminated by a different objective.

### Resume exact

Resume an existing Codex session only when all are true:

```text
SAME_WRITER=YES
SAME_TASK=YES
SAME_COHERENT_STAGE=YES
SAME_WORKTREE=YES
SAME_AUTHORITY_CONTEXT=YES
PRIOR_CONTEXT_TRUSTWORTHY=YES
INDEPENDENCE_REQUIRED=NO
```

Use the exact recorded session/thread identifier:

```text
codex exec resume <EXACT_SESSION_ID> "<next bounded instruction>"
```

Do not use process/window continuity as session identity.

### `resume --last`

`codex exec resume --last` is an official convenience command, but it is **not** the project automation default. In multi-window, parallel-worktree, or future Hermes workflows, `--last` can select the wrong thread or collide with an active Writer.

For routed work:

```text
EXACT_SESSION_ID_KNOWN=YES → resume exact id when reuse conditions pass
EXACT_SESSION_ID_KNOWN=NO  → start new session or SAFE_STOP; do not guess with --last
THREAD_ALREADY_ACTIVE      → do not force a second Writer into the thread; wait/stop and reconcile ownership
```

---

## 4. Token and cache efficiency

OpenAI's Codex agent-loop documentation confirms that prompt caching depends on exact reusable prefixes, not on whether a TUI process stays foregrounded. Cache misses can be caused by changing model, tool set, sandbox/approval configuration, or working directory.

Therefore keep the stable portion of one coherent Writer stage stable:

```text
MODEL
TOOLS / MCP SET
SANDBOX / APPROVAL MODE
CWD / WORKTREE
STABLE AGENTS / PROJECT INSTRUCTIONS
STABLE ROLE + AUTHORITY + OUTPUT CONTRACT
→ mutable task delta late
```

Rules:

1. Reuse the exact session only when the reuse gate in section 3 passes.
2. Do not repaste long project history when canonical `AGENTS.md`, repository authority, Skills, or a frozen Task Packet already carry it.
3. Put volatile SHA/CI/blocker/delta facts late in the task input.
4. Use deterministic shell commands for mechanical validation instead of additional Codex turns.
5. Do not change model/tool/sandbox/CWD mid-stage merely for convenience.
6. Do not keep a stale session alive solely to chase cache hits; growing conversation history also consumes context and may require compaction.
7. Cache is an optimization, not an authority or correctness gate.

There is no project assumption that `resume exact` is always cheaper than a new session. Measure on real tasks where useful.

---

## 5. JSONL, Result Packet and telemetry

For Engineering-routed automation where a wrapper can parse machine output, prefer:

```text
codex exec --json ...
```

OpenAI's current non-interactive mode emits JSONL events including `thread.started` with `thread_id`, turn lifecycle events, and `turn.completed.usage` with fields such as:

```text
input_tokens
cached_input_tokens
output_tokens
reasoning_output_tokens
```

This is the preferred source for exact session identity and token/cache telemetry because it does not require an extra model turn merely to ask Codex what session it used.

Capture, when naturally available:

```text
thread_id / session_id
input_tokens
cached_input_tokens
output_tokens
reasoning_output_tokens
elapsed_time
repair/rework_count
model
reasoning level
worktree
```

Do not generate synthetic paid turns solely to improve cache metrics.

### Final-message transport

`--output-last-message <path>` is appropriate when the operator wants a separate final human-readable result artifact.

`--output-schema` is appropriate when a downstream machine step truly benefits from a stable structured Result Packet. Do not require structured output for every human-assisted run when plain final output is sufficient.

When `--json` is enabled, treat stdout as JSONL; the wrapper/Hermes should parse the event stream rather than assuming stdout is plain final prose.

---

## 6. Current human-assisted workflow

Default user experience:

```text
ONE ORDINARY TERMINAL PASTE
→ deterministic repo/worktree/preflight
→ codex exec [explicit task settings]
→ capture exact session id / useful telemetry when available
→ Codex completes and exits
→ deterministic tests/evidence/commit/push only if authorized
→ Terminal returns to ordinary shell
```

If Engineering Control later determines that the same Writer/task/stage should continue, the next one-paste block may use:

```text
codex exec resume <EXACT_SESSION_ID> ...
```

If the next action is deterministic shell validation, no Codex continuation is required.

The user should not have to decide whether a block belongs in zsh or inside a persistent Codex composer during routine project work.

---

## 7. Future Hermes-managed workflow

Initial Hermes-to-Codex automation should use the smallest provider-native seam:

```text
L1 frozen Task Packet
→ Hermes validates/transports exact packet
→ native codex exec
→ JSONL event capture
→ exact thread id + token/evidence extraction
→ optional exact-session resume only when the packet authorizes it
→ Result Packet / raw evidence
→ independent downstream review
```

Do **not** build a custom Codex SDK/App Server orchestration layer as the default merely to reproduce behavior already provided by `codex exec`.

OpenAI also provides the Codex SDK and Codex App Server with programmatic thread start/resume and richer JSON-RPC control. These are mature provider-native alternatives for a future need such as bidirectional steering, richer approval handling, long-lived multi-turn client control, or a custom internal application. They remain a **replaceable future seam**, not the current default, until measured operator requirements justify their added implementation/maintenance burden.

DeepSeek remains separate and provider-native:

```text
Hermes → dsh --profile headless ...
```

only after the separately required Hermes/DSH schema/profile authority is accepted. Do not force Codex and DSH into one custom orchestration implementation merely for symmetry.

---

## 8. Permission policy is independent from execution mode

`interactive` versus `exec` is not the same decision as sandbox/approval policy.

L1 freezes the exact sandbox/approval behavior per bounded task. For authorized isolated local Writer work, the project may choose a configuration that does not request user approval for every ordinary in-scope command. That does not grant any retained release/runtime/account/trading authority.

The following remain separate explicit current user gates regardless of Codex approval mode:

```text
MARK_READY
MERGE
DEPLOYMENT
RUNTIME_OR_CLOUD_MUTATION
CREDENTIALS_OR_PRIVATE_API
WALLET_OR_SIGNING
EXCHANGE_WRITE
ORDER_SUBMISSION_OR_CANCELLATION
TRADING_AUTHORITY
```

---

## 9. What is permanent policy vs measured implementation detail

### Permanent policy

- `codex exec` is the default routed Writer mode;
- interactive TUI is opt-in for intentional human interaction;
- exact session identity controls continuation;
- `resume --last` is not an automation default;
- new-session versus exact-resume gates in section 3;
- Writer and independent Reviewer never share a session for acceptance;
- stable-prefix discipline and deterministic mechanics before model turns;
- token/cache telemetry should be collected when naturally available;
- permissions remain separate from permanent user-retained gates;
- Hermes uses provider-native executor seams before custom orchestration.

### Measured implementation detail

Do not freeze arbitrary thresholds until real evidence exists for:

- a minimum cache-hit ratio;
- a maximum session length;
- a fixed token threshold for forcing new session versus resume;
- a claim that resume is always cheaper than a new session;
- a requirement that every run use `--output-schema`;
- migration from `codex exec` to Codex SDK/App Server.

Evaluate those from real task telemetry and operator burden.

---

## 10. First-party evidence basis

Decision basis checked 2026-08-19:

- OpenAI Codex Non-interactive mode: `codex exec`, `--json`, `thread.started`, token usage, exact `resume <SESSION_ID>`, `--output-last-message`, and `--output-schema`;
- OpenAI Codex SDK: programmatic start/continue/resume of local Codex threads;
- OpenAI Codex App Server: provider-native JSON-RPC thread start/resume and richer client control;
- OpenAI engineering article *Unrolling the Codex agent loop*: cache efficiency requires exact stable prefixes and is affected by model/tool/sandbox/approval/CWD changes; conversation history grows with continued threads and Codex performs automatic compaction.

The project route is independently derived and externally confirmed: use the smallest provider-native automation seam now, preserve exact session identity, and keep richer SDK/App Server control as a replaceable future option.

---

## 11. Preflight record for this route

```text
PROJECT_ENGINEERING_RULESET_PREFLIGHT=PASS
ENGINEERING_PREFLIGHT_GATE=PASS
TASK_CLASS=MATERIAL
LIVE_REPO=woshixiong/trader-assist-v0
LIVE_MAIN_SHA=4b8719ca44f9ff9d459910690183ca9b790b726d
ACTIVE_GOVERNANCE_PR=PR #108 OPEN/DRAFT at e69b594c3007cd687e7772d3078e17c4f8566438 during route research
ROOT_CAUSE_LEVEL=WORKFLOW / EXECUTOR-SEAM
AFFECTED_AUTHORITIES=L1/L2 routing; Codex session identity; user-attention; future Hermes transport
CURRENT_ROUTE=provider-native codex exec + exact-session resume when eligible
MATURE_ALTERNATIVES_CONSIDERED=persistent TUI; always-new exec; exact-session exec resume; Codex SDK; Codex App Server
CURRENT_NEED=one-paste execution that returns to shell while preserving optional exact continuation and measurable token/cache evidence
STABLE_INTERFACES=Task Packet; worktree; exact session id; JSONL evidence; Result Packet
REPLACEABLE_IMPLEMENTATION_SEAMS=codex exec now; SDK/App Server later only if justified
OVERENGINEERING_CHECK=PASS
REPAIR_STAGE=INITIAL
STOP_CONDITION=official Codex session/exec semantics materially change or real telemetry disproves the selected operating policy
PROHIBITED_SCOPE=runtime/product/strategy semantics; merge/deploy/runtime/account/exchange authority
```
