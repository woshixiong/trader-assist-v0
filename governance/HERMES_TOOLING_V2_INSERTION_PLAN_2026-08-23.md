# Hermes Insertion Plan after Tooling Router / Codex V2

**Status:** PRE-CONFIGURATION PLAN — NO HERMES ACTIVATION AUTHORITY

Hermes configuration is the next tooling stage after the Router/Codex V2 candidate receives independent acceptance. Existing `HERMES_EXECUTION_OPERATOR_CONTRACT_V1_2026-08-16.md` remains the authority boundary. `ENGINEERING_TOOL_ONBOARDING_AND_CHANGE_ACCEPTANCE_RULE_V1_2026-08-23.md` additionally requires independent acceptance of the actual Hermes project configuration/automation surface before first project use.

## 1. Intended insertion

```text
L1 ChatGPT Engineering Control / Router
-> live preflight + exact route/model/reasoning/tool freeze
-> canonical lossless Task Packet
-> Hermes transport/operator
   -> selected semantic Writer when needed
      (Codex | OpenCode | Trae | DeepSeek Harness)
   -> authorized deterministic terminal/browser/file mechanics
   -> exact evidence/result collection
   -> authorized commit/push/CI observation where included
-> independent strongest-appropriate ChatGPT Reviewer
-> separate user release/merge/runtime gates
```

Hermes is not an extra semantic reasoning layer. It transports and executes already-decided work.

## 2. Efficiency rule — Hermes replaces relay, not reasoning

Use a low-cost/free Hermes model for:

- packet integrity/field verification;
- launching an already-selected executor/model/reasoning/tool shape;
- deterministic terminal/files/browser steps;
- waiting/polling bounded processes;
- collecting exact Result Packets/evidence;
- deterministic commit/push/status/CI mechanics when explicitly authorized;
- preparing and transporting an independent-review evidence bundle.

Hermes must not:

- choose the engineering route, Writer model, Reviewer model or reasoning level;
- paraphrase/reconstruct authority-bearing Task Packets or review prompts;
- ask another model to re-reason over code before every Codex step;
- independently expand scope or semantically retry a failed Writer;
- declare independent engineering acceptance;
- infer Mark Ready/merge/deploy/runtime/trading authority.

The target is fewer handoffs and less Codex quota spent on mechanics, not a longer agent chain.

## 3. Codex handoff optimization with Hermes

Without Hermes, Codex may finish a small already-authorized mechanical tail when that is cheaper than another handoff.

After Hermes is qualified, the preferred boundary for a material Codex stage is:

```text
CODEX
  inspect -> reason -> implement -> focused/relevant validation -> self-check
  -> freeze exact semantic result/evidence

HERMES
  verify frozen result identity
  -> remaining deterministic status/diff/evidence mechanics
  -> commit/push if the Task Packet explicitly authorizes them
  -> observe CI / collect artifacts if authorized
  -> return exact Result Packet
```

This can save Codex tokens because Hermes performs mechanics without another Codex reasoning turn. Do not force the handoff when the remaining tail is trivial enough that handoff metadata/latency would exceed the saved burden.

## 4. Independent review — local evidence bundle first

T4 independent acceptance defaults to a separate ordinary ChatGPT window using the strongest appropriate available model and highest appropriate reasoning.

When local execution/inspection is required, prefer:

```text
DETERMINISTIC TERMINAL / TOOLING
-> generate exact independent-review bundle
-> hash/manifest bundle
-> HERMES transports bundle + frozen review prompt
-> NEW independent ChatGPT conversation/window
-> exact reviewer model/reasoning selection already frozen by L1
-> upload bundle
-> strongest ChatGPT performs review/adjudication
```

This is preferred to assigning final independent acceptance to a materially weaker local coding model merely because that model can execute locally.

The bundle may contain, as applicable:

```text
MANIFEST
BASE / HEAD / WORKTREE IDENTITY
PATCH / DIFF
CHANGED-FILE LIST
EXACT RELEVANT SOURCE/CONFIG FILES
LOCAL TEST / STATIC-CHECK RESULTS
BOUNDED FAILURE LOGS
ARTIFACT HASHES
CI / GITHUB REFERENCES
FROZEN ACCEPTANCE CRITERIA / REVIEW PROMPT
```

Secrets, credentials, private account material, production databases and unnecessary large logs are prohibited.

## 5. Hermes -> ChatGPT review transport is technically feasible but separately gated

Current Hermes upstream exposes:

- terminal/process tooling suitable for deterministic bundle generation;
- computer-use/browser automation;
- browser file-input support (`cua_browser_set_input_files`) for explicit local file paths;
- exact browser-state/capture-before-mutation patterns.

Therefore the intended automation is technically feasible after Hermes installation/qualification:

```text
R0 FREEZE_REVIEW_TRANSPORT
R1 BUILD_BUNDLE
R2 VERIFY_BUNDLE_HASHES
R3 BIND_FRESH_CHATGPT_REVIEW_SURFACE
R4 VERIFY_EXACT_REVIEWER_MODEL_REASONING_UI_STATE
R5 UPLOAD_EXACT_BUNDLE
R6 PASTE_FROZEN_REVIEW_PROMPT_WITHOUT_PARAPHRASE
R7 VERIFY_ATTACHMENTS_AND_PROMPT_BEFORE_SUBMIT
R8 SUBMIT_AND_WAIT
R9 CAPTURE_REVIEW_RESULT_AND_EVIDENCE
R10 RETURN_REVIEW_TRANSPORT_RESULT
```

No phase may infer that the next phase succeeded merely because the UI changed.

Important current limitation: the existing Hermes V1 Lossless Task Packet/H2 executor contract was not designed around ChatGPT review-browser transport or direct OpenCode/DSH H2 dispatch. Those schema/contract surfaces must be updated and independently accepted during the Hermes configuration stage before this automation is activated. This plan does not pretend the current V1 schema already authorizes it.

## 6. Mandatory checkpoint ledger — no black-box automation

Every Hermes multi-step run must be interruptible, diagnosable and resumable from exact state.

Record after each phase:

```text
RUN_ID=
PHASE=
PHASE_STATUS=PASS|FAIL|NOT_RUN
LAST_COMPLETED_PHASE=
TASK_PACKET_ID=
TASK_PACKET_HASH=
INPUT_ARTIFACTS_AND_HASHES=
OUTPUT_ARTIFACTS_AND_HASHES=
DESTINATION=
EXECUTOR=
MODEL=
REASONING=
WORKTREE=
HEAD_BEFORE=
HEAD_AFTER=
ACTION_RESULT_OR_EXIT_STATUS=
RETRY_COUNT=
STOP_REASON=
RESUME_FROM=
TIMESTAMP=
```

For browser/ChatGPT review transport also record safe non-secret identity fields needed to locate the exact run, such as the browser/session/tab capability or conversation locator when available. Never store OAuth/access/refresh tokens or cookies.

If an action fails, Hermes returns the ledger immediately. It must not hide the failure inside a later successful step.

## 7. Retry and recovery policy

```text
SEMANTIC_WRITER_FAILURE -> NO AUTONOMOUS SEMANTIC RETRY
ROUTE/MODEL/REASONING MISMATCH -> STOP
UI MODEL/REASONING STATE CANNOT BE VERIFIED -> STOP
UPLOAD/PROMPT ATTACHMENT MISMATCH -> STOP
WORKTREE/HEAD/PACKET HASH DRIFT -> STOP
UNEXPECTED LOGIN/UPDATE/PERMISSION DIALOG -> STOP
```

A narrowly deterministic idempotent action may have an explicitly frozen bounded retry count. Every retry is recorded. There is no hidden unlimited retry loop.

Resume only from an exact checkpoint whose prerequisite hashes/state still verify. If they do not verify, restart from the last earlier verified checkpoint or return to L1.

## 8. OpenCode relationship

Before Hermes is qualified, OpenCode Opus can perform the free deterministic operator tail.

After Hermes is qualified:

- Hermes becomes the preferred orchestration/transport layer when it can safely execute the mechanics itself;
- OpenCode remains a free semantic Writer and may still be an executor under Hermes when useful;
- do not force Hermes -> OpenCode -> Codex chains when Hermes can directly dispatch Codex or perform the deterministic action;
- do not use OpenCode as a ceremonial second reasoning layer between Codex and Hermes.

## 9. Tool-specific Web/model/reasoning state remains L1-frozen

Hermes does not decide whether Codex gets Web Search, which Codex model is used, or which reasoning level is used. Engineering Control/Router freezes those task-local fields before dispatch. Hermes verifies and transports them exactly.

For Codex, the Task Packet must explicitly state:

```text
CODEX_MODEL=
CODEX_REASONING_EFFORT=
CODEX_WEB_SEARCH_REQUIRED=YES|NO
```

If Web Search is required, the launch contract must enable the verified current Codex web-search surface for that stage. If it is not required, keep it disabled. Hermes may not silently flip the setting.

## 10. Qualification focus

Hermes setup/qualification must prove:

1. lossless Task Packet integrity and exact field/hash preservation;
2. current macOS repo/worktree identity;
3. explicit destination/executor/model/reasoning/permissions/tool shape;
4. fail-closed behavior on missing/ambiguous authority;
5. safe terminal/browser/file execution boundaries;
6. exact evidence/result transport without paraphrase;
7. checkpoint ledger completeness and human takeover from a failed phase;
8. no silent model/route/reasoning/Web-Search substitution;
9. no hidden semantic retry loop;
10. deterministic review-bundle generation and hash verification;
11. ChatGPT upload/prompt transport only after exact reviewer-surface verification;
12. materially lower human relay than the current one-paste/manual-upload workflow.

The actual installed Hermes version/configuration plus any required H2/review-transport schema extension must receive separate independent acceptance before first project use.

No deployment/runtime/account/exchange action is part of this tooling qualification.
