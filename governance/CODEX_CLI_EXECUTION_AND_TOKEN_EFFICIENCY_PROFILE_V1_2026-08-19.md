# Trader Assist / Trade OS — Codex CLI Execution and Token Efficiency Profile V1

**Status:** DRAFT SPECIALIZED GOVERNANCE  
**Effective date:** 2026-08-19  
**Scope:** Codex CLI Writer execution mode, session identity, continuation, machine evidence, token/cache telemetry, and future Hermes transport.

This profile specializes the canonical engineering governance. It does not grant Mark Ready, merge, deployment, runtime/cloud mutation, credentials/private API, wallet/signing, exchange-write, order-submission/cancellation, or trading authority.

## 1. Decision

For the project’s normal layered workflow:

```text
L1 Engineering Control
→ L2 Codex Writer
→ deterministic local/CI gates
→ Independent Reviewer
```

use the provider-native non-interactive CLI path by default:

```text
CODEX_DEFAULT_EXECUTION_MODE=codex exec
CODEX_INTERACTIVE_TUI_POLICY=OPT_IN_HUMAN_PAIR_PROGRAMMING_OR_EXPLORATION_ONLY
CODEX_NEW_SESSION_POLICY=NEW_TASK_OR_ROLE_OR_WORKTREE_OR_AUTHORITY_OR_MATERIAL_STAGE_CHANGE_OR_INDEPENDENT_REVIEW
CODEX_RESUME_POLICY=RESUME_EXACT_SESSION_ID_ONLY_WHEN_SAME_WRITER_TASK_COHERENT_STAGE_WORKTREE_AUTHORITY_AND_TRUSTED_CONTEXT
CODEX_RESUME_LAST_POLICY=PROHIBITED_AS_PROJECT_AUTOMATION_DEFAULT
CODEX_SESSION_ID_CAPTURE=REQUIRED_FOR_RESUMABLE_WRITER_RUNS
CODEX_JSONL_POLICY=DEFAULT_FOR_MATERIAL_OR_RESUMABLE_WRITER_RUNS
CODEX_TOKEN_TELEMETRY_POLICY=PASSIVE_CAPTURE_FROM_REAL_RUNS_NO_SYNTHETIC_TOKEN_TESTS
CODEX_PERMISSION_POLICY=NONINTERACTIVE_APPROVAL_NEVER_BY_DEFAULT; SANDBOX_SEPARATELY_FROZEN_PER_TASK
HERMES_CODEX_TRANSPORT_POLICY=HEADLESS_CODEX_EXEC_JSONL_WITH_EXACT_SESSION_ID
HERMES_DEEPSEEK_TRANSPORT_POLICY=NATIVE_DSH_HEADLESS_WHEN_SEPARATELY_SCHEMA_AUTHORIZED
```

## 2. Why `codex exec` is the default

`codex exec` is the first-party non-interactive mode intended for scripts, pipelines, CI and CLI workflows. It exits when the turn completes, so a user-operated one-paste Terminal workflow returns to the ordinary shell instead of remaining inside the Codex TUI.

This preserves the project UX:

```text
one ordinary Terminal paste
→ deterministic preflight/routing
→ Codex Writer if assigned
→ tests/evidence
→ Codex process exits
→ ordinary shell returns
```

Interactive TUI is not prohibited. It is reserved for work whose value genuinely comes from live human pair-programming, exploratory back-and-forth, or interactive inspection. It is not the default transport for bounded Engineering-Control-issued Writer packets.

## 3. Session identity and continuation

A process ending is not the same as a model session ending. Continuation uses the persisted Codex thread/session identity.

### Resume exact

Use:

```text
codex exec resume <EXACT_SESSION_ID> <follow-up-prompt>
```

only when all are true:

- same Writer role;
- same task;
- same coherent authorized stage;
- same worktree;
- same authority context;
- prior context remains trustworthy;
- no independent-review boundary has been crossed;
- no active Writer collision exists for that thread.

A deterministic shell/CI check between two Writer turns does not by itself require a new Codex session if all conditions above remain true.

### New session

Start a new Codex session for:

- a new task;
- a different Writer/Reviewer role;
- a different worktree;
- a materially changed authority context;
- a material route/stage change;
- clean-route adjudication after a failed architecture;
- security/authority review;
- independent final review.

### `resume --last`

`codex exec resume --last` is a valid first-party convenience command, but it is not a safe project automation default because “last” is contextual rather than an authority-bearing identity. The project must carry the exact session/thread ID when continuation matters.

Human ad-hoc use of `--last` is not globally forbidden, but Engineering/Hermes task routing must not depend on it.

## 4. JSONL and Result Packet transport

For material or resumable Writer runs, prefer:

```text
codex exec --json ...
```

and mechanically capture the JSONL stream outside the repository or in ephemeral local evidence storage. Do not commit raw Codex logs.

From provider-native events capture, when present:

```text
thread.started.thread_id
turn completion/failure status
input_tokens
cached_input_tokens
output_tokens
reasoning_output_tokens
final agent result
command/file-change status needed by the frozen task
```

The exact `thread_id` is the continuation identity.

`--output-last-message` is an optional convenience for separating the final human/result text from event telemetry. `--output-schema` is preferred when a future automated Result Packet needs stable machine-readable final fields. Neither is mandatory for every small human-assisted task.

JSONL collection is local observability/transport; it must not cause extra model turns merely to obtain telemetry.

## 5. Token and cache policy

Prompt caching is automatic. The project optimizes reusable prefix shape rather than asking Codex to “use cache.”

Keep stable content first:

```text
role/mode
→ safety and permanent authority boundary
→ canonical repository rule pointers
→ stable Writer/output contract
→ mutable task facts last
```

Put volatile facts late:

```text
branch/base/head
current blocker
allowlist delta
CI run
one-off evidence
```

Do not repeatedly paste full project history or already accepted governance when repository `AGENTS.md`, canonical pointers, exact accepted artifacts and delta evidence are sufficient.

Use deterministic shell/Git/CI work outside the model whenever judgment is not required.

Exact-session resume is permitted because it preserves coherent context, but **the project does not assume that resume is always cheaper than a new session**. Real-task evidence must decide that empirically.

For useful real tasks, passively record when available:

```text
input_tokens
cached_input_tokens
output_tokens
reasoning_output_tokens
elapsed_time
repair_or_rework_count
new_session_vs_resume_exact
```

Do not create synthetic paid requests solely to improve or benchmark cache-hit metrics.

## 6. Permissions are separate from execution mode

Interactive versus `exec` does not decide authority.

For normal non-interactive local Writer work:

```text
APPROVAL_POLICY=never
SANDBOX=explicitly frozen per task; normally workspace-write when sufficient
```

`approval_policy=never` means Codex does not stop for routine per-command approval prompts. It does **not** grant release/runtime/trading authority.

If a required action exceeds the frozen sandbox or Task Packet authority, fail closed or return to L1 rather than silently escalating. Do not make `danger-full-access` a universal project default; use a broader sandbox only for a bounded task when Engineering has explicitly determined it is technically required and the permanent user gates remain unchanged.

The following remain separate current-user gates regardless of approval policy:

```text
Mark Ready
merge
deployment
runtime/cloud mutation
credentials/private API
wallet/signing
exchange write
order submission/cancellation
trading authority
```

## 7. Current human-assisted workflow

Engineering Control should continue producing one ordinary-Terminal block. Inside that block it may:

1. resolve repo/worktree/exact authority;
2. run deterministic preflight;
3. invoke `codex exec --json` for a new Writer turn or `codex exec resume <EXACT_SESSION_ID>` for a valid continuation;
4. redirect/parse JSONL mechanically so the user does not have to inspect it;
5. run authorized deterministic tests/Git/CI steps;
6. print a concise Result Packet/evidence summary;
7. return control to the ordinary shell.

The user should not have to decide whether the next paste belongs to zsh or the Codex TUI.

## 8. Future Hermes workflow

When Hermes transports `CODEX_CLI`, the preferred seam is:

```text
verified frozen Task Packet
→ exact NEW or RESUME_EXACT session mode
→ codex exec --json
→ mechanical thread_id/status/token/result extraction
→ raw evidence preservation
→ downstream independent review
```

Hermes must never choose NEW versus RESUME_EXACT, infer a session ID, use `--last` as a substitute, switch model/sandbox/authority, or review the result.

For DeepSeek Harness, keep the separate provider-native route:

```text
verified frozen Task Packet
→ dsh native headless execution
→ raw Result Packet/evidence
```

Hermes-to-DeepSeek dispatch remains prohibited until the project Lossless Task Packet schema/profile separately enumerates and accepts `DEEPSEEK_HARNESS`.

## 9. Routes not selected as the default

### Persistent interactive Codex TUI

Useful for human pair-programming; rejected as the normal bounded Writer transport because it leaves the foreground Terminal in Codex, mixes execution environments, and adds user routing work.

### New `codex exec` session for every turn

Simple but unnecessarily discards a valid continuation option. Use NEW when the task/role/worktree/authority/stage boundary requires it, not after every process exit.

### Codex SDK

Official and mature enough to programmatically start/resume threads. Keep it as a replaceable future seam if repeated automation needs exceed what `codex exec --json` can cleanly provide. Do not add SDK code/dependencies merely to reproduce behavior already provided by the CLI.

### Codex app-server / MCP multi-agent orchestration

Not selected for the current project operator route. App Server is intended for deep rich-client integration, while MCP/Agents SDK orchestration adds another orchestration layer that would overlap Hermes. Revisit only if a measured requirement cannot be met by the narrower CLI/SDK seam.

## 10. First-party evidence basis

Decision checked against current OpenAI first-party documentation on 2026-08-19:

- `https://developers.openai.com/codex/noninteractive`
- `https://developers.openai.com/codex/cli/reference`
- `https://developers.openai.com/codex/config-reference`
- `https://developers.openai.com/codex/sdk`
- `https://developers.openai.com/codex/app-server`
- `https://developers.openai.com/codex/mcp-server`

The first-party docs explicitly support non-interactive `codex exec`, exact session resume, JSONL event output with `thread_id` and token usage, `--output-last-message`, structured final output schemas, sandbox/approval separation, SDK thread control, and richer App Server/MCP routes. This project selects the smallest provider-native route that satisfies the current and future Hermes-managed workflow.
