# Trader Assist / Trade OS — Codex Token Efficiency and Prompt Rules V1

**Status:** FROZEN PROCESS RULE  
**Effective date:** 2026-08-13  
**Repository:** `woshixiong/trader-assist-v0`

## 1. Objective

Use Codex with the lowest practical token cost and the highest practical first-pass engineering success rate without weakening independence, exact-head review, safety boundaries, or user authority.

Token efficiency is an engineering constraint, not a reason to reduce correctness.

## 2. Prompt-caching principle

Codex/OpenAI prompt caching is automatic. Prompts must not waste tokens telling the model to "use cache".

Optimize for cache reuse by keeping the reusable prompt prefix stable and placing task-specific mutable material near the end.

Where practical, preserve across related Codex calls:

- the same model;
- the same reasoning level unless task complexity materially changes;
- the same sandbox / approval configuration;
- the same authorized clean worktree and current working directory;
- the same tool surface;
- the same stable role, safety, workflow, and output-contract prefix.

Do not change these merely to start a new Terminal window.

## 3. Terminal-window rule

Before every user-facing Codex command, Engineering Optimization or Project Control must state in ordinary prose, outside the prompt/code block:

```text
TERMINAL=REUSE_EXISTING | OPEN_NEW
CODEX_SESSION=RESUME_EXISTING | NEW_INDEPENDENT
WORKTREE=<exact path>
MODEL=<model>
REASONING=<level>
SANDBOX=<mode>
TOKEN_STRATEGY=<short explanation>
```

Do not hide Terminal-window instructions inside the Codex task prompt.

A new Terminal window alone is not an engineering isolation boundary. Worktree, exact HEAD, model role, sandbox, and Codex conversation independence are the relevant controls.

## 4. Session reuse

Use `RESUME_EXISTING` when all are true:

- the same engineering role continues;
- the same coherent stage continues;
- the same worktree remains authorized and clean;
- independence is not required;
- the previous context remains relevant and trustworthy.

Typical examples:

- Writer continuing the same stage after a local test failure;
- Writer performing one authorized consolidated repair;
- the same read-only diagnostic continuing a bounded investigation.

Do not restart a fresh Codex conversation merely because a new shell or Terminal is convenient.

## 5. Mandatory independent sessions

Use `NEW_INDEPENDENT` when independence is part of the control objective, including:

- Writer versus final Reviewer;
- separate Security / Authority review;
- clean-route architecture adjudication after a failed design route;
- reviews where inherited Writer conclusions could bias acceptance.

Do not sacrifice reviewer independence to improve cache reuse.

Independent sessions should still maximize cacheability by reusing the same stable static prefix and moving reviewer-specific facts to the end.

## 6. Prompt construction

Default Codex prompts must be compact.

Preferred structure:

1. role and mode;
2. immutable safety / authority boundary;
3. exact repository / worktree / base / HEAD facts;
4. concise objective;
5. exact allowlist or review scope;
6. stop rules;
7. validation commands or acceptance criteria;
8. compact final-output contract;
9. task-specific delta facts last.

Do not repeatedly paste long project histories that already exist in repository governance.

Instead instruct Codex to read only the relevant local sources such as:

- `AGENTS.md`;
- `governance/PROJECT_RULES_INDEX.md`;
- the named current authority / strategy / product contract;
- exact changed files or exact commit delta.

Use `rg`, targeted file reads, and exact diff ranges instead of blindly reading every governance file.

## 7. Static prefix / dynamic suffix

For repeated task families, preserve a canonical static prefix for:

- role;
- read/write mode;
- user-retained authority;
- one-Writer rule;
- exact-head review rule;
- repair-budget rule;
- no deployment/account/exchange authority;
- output schema.

Append changing facts near the end:

- branch;
- base SHA;
- exact HEAD;
- current blocker IDs;
- changed-file allowlist;
- current CI run;
- current task delta.

Do not reorder stable sections without a reason.

## 8. Model and reasoning economy

Use the lowest reasoning level that is likely to complete the task correctly in one pass.

Default allocation:

- mechanical checks, fixtures, bounded docs, simple tests: normal / medium;
- normal module implementation and frozen-interface wiring: high only when needed;
- cross-persistence, restart, authority, safety, or release blockers: high;
- xhigh/max: exceptional only, never default.

A higher reasoning level is justified when it materially lowers expected rework cost.

Do not use high reasoning merely because quota is available.

## 9. Parallelism

Maximize throughput with role separation, not competing Writers.

```text
ONE COHERENT CODE STAGE
→ ONE PRIMARY WRITER
→ ONE EXACT HEAD
→ PARALLEL READ-ONLY REVIEW / CI
```

Multiple Codex sessions may run in parallel only when they do not write competing versions of the same stage.

Parallel read-only tasks should be deliberately non-overlapping where possible, for example:

- persistence/restart review;
- scanner/frozen-contract review;
- security/authority review;
- release/bootstrap planning.

## 10. Worktree and environment reuse

Follow the existing frozen workflow rule:

```text
REUSE VALID CLEAN AUTHORIZED WORKTREE
REUSE VALID PYTHON ENVIRONMENT
```

Do not rebuild a worktree or Python environment just because:

- a new Terminal opens;
- a new Codex conversation starts;
- a different Reviewer runs.

Create a new worktree only when isolation, branch ownership, dirtiness, incompatibility, or concurrent-write safety requires it.

## 11. Avoid duplicate context work

Codex must not repeatedly re-prove stable facts already accepted at the current exact-head boundary unless the task specifically challenges them.

After a blocker is independently adjudicated:

- Writer fixes the accepted blocker scope;
- Reviewer tests the repair and adjacent bypass risk;
- do not spend another full review proving the original blocker existed.

After a design route consumes one normal consolidated repair plus one exceptional repair and still fails the same root class:

```text
STOP_REPLAN
```

Do not spend tokens on Repair 3/4/5.

## 12. Large prompt fallback

If a task genuinely requires a long packet, prefer a stable prompt file or repository-local packet and give Codex a short instruction to read it rather than repeatedly pasting the entire packet into every invocation.

Do not store secrets in prompt files.

For independent reviews, create a clean immutable review packet tied to the exact HEAD when this materially reduces repeated context.

## 13. Safety and authority remain dominant

Token optimization never grants authority to:

- commit or push unless explicitly authorized;
- Mark Ready or merge;
- deploy or mutate runtime;
- access AWS/paid resources;
- access credentials/account/private API;
- sign, manage nonce, or write to an exchange;
- send real Discord messages.

User-retained gates remain unchanged.

## 14. Required user-facing behavior

Before providing a Codex Terminal command, always state clearly in ordinary prose whether to open a new Terminal or reuse the current one.

Prefer concise operational guidance such as:

```text
这一步：复用原来的 Terminal。
原因：同一个 Writer、同一阶段、同一 worktree；这样上下文和缓存复用最好。
```

or:

```text
这一步：新开一个 Terminal。
原因：这是独立 Reviewer / clean replacement route，需要新的 Codex session；仍复用同一只读 worktree 与固定 prompt prefix。
```

## 15. Frozen ruling

```text
CODEX_TOKEN_EFFICIENCY=DEFAULT_ENGINEERING_CONSTRAINT
PROMPT_CACHE=AUTOMATIC__OPTIMIZE_EXACT_STABLE_PREFIX
LONG_HISTORY_REPASTE=AVOID
STATIC_PREFIX_DYNAMIC_SUFFIX=REQUIRED_WHEN_PRACTICAL
WORKTREE_REUSE=DEFAULT
SESSION_REUSE=SAME_ROLE_SAME_STAGE
INDEPENDENT_REVIEW_SESSION=NEW
ONE_PRIMARY_WRITER=REQUIRED
PARALLEL_READ_ONLY_REVIEW=ENCOURAGED
TERMINAL_GUIDANCE=VISIBLE_OUTSIDE_PROMPT
REPAIR_3_PLUS=PROHIBITED_FOR_SAME_FAILED_ROUTE
SAFETY_AND_USER_AUTHORITY=UNCHANGED
```
