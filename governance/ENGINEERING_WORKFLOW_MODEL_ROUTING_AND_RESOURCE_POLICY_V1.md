# Engineering Workflow, Model Routing, and Resource Policy V1

**Status:** DRAFT CONSOLIDATION  
**Applies to:** Engineering Optimization, Project Control, Writer, Reviewer, auxiliary Agents  
**Builds on:** `TRADER_ASSIST_ENGINEERING_WORKFLOW_V3_2026-07-22`

## 1. Objective

Deliver the smallest adequate and safely coherent engineering objective with one primary Writer, exact scope, exact-head verification, independent Review, and bounded repair while minimizing user handoffs, elapsed time, and paid/limited model quota.

Speed is obtained through correct granularity, legitimate human-machine allocation, parallel read-only work, reuse, and elimination of duplicate work. Safety or quality gates are not removed for speed, but work with no current operational value must not be built merely because it may matter in a later automation phase.

## 2. Authority windows

### Product Function and Priority

Decides what and why:

- product scope and value;
- feature selection and priority;
- product acceptance;
- deferral, rejection, restoration, and post-launch direction.

### Engineering Optimization

Decides how:

- architecture and stage boundaries;
- largest safe coherent task granularity;
- Agent/model/harness routing;
- allowlists and commit budgets;
- tests, Review, Repair, evidence, and escalation;
- token and cycle-time optimization.

### Project Control

Executes accepted decisions:

- live-state verification;
- exact task, base, branch, worktree, and packet control;
- Writer and Reviewer routing;
- PR, CI, finalization, merge, and refreeze;
- authority and state consistency.

No window may infer another window's decision.

## 3. Default execution architecture

```text
ONE COHERENT STAGE OBJECTIVE
→ ONE PRIMARY WRITER
→ ONE EXACT FILE/SOURCE ALLOWLIST
→ ONE COMMIT BUDGET
→ ONE EXACT HEAD
→ PARALLEL READ-ONLY VERIFICATION
→ ONE CONSOLIDATED FINDING SET
→ AT MOST ONE NORMAL CONSOLIDATED REPAIR
→ MATERIAL USER AUTHORITY GATE
```

The user must not be used as a routine message bus.

## 4. Granularity and root-cause compression

Default prohibitions:

- one finding → one Writer;
- one finding → one task;
- one finding → one commit;
- one file → one Agent;
- one test → one repair prompt;
- Reviewer-specific serial repairs.

Required design:

1. group findings by underlying root cause;
2. remove an erroneous mechanism before adding compensating layers;
3. shrink unnecessary contracts before preserving placeholders;
4. align accepted authoritative contracts;
5. implement the minimum acceptance closure;
6. introduce shared abstractions only after repeated accepted use.

Test granularity may be finer than implementation granularity.

Split a stage only when it crosses:

- product rulings;
- runtime or cloud authority;
- public-read versus account/write authority;
- incompatible Writer ownership;
- dependency/workflow changes;
- an unreviewable allowlist or diff boundary.

## 4.1 Practical auxiliary-system and human-machine allocation

Trader Assist is a practical decision-support system for an experienced operator. Planning must optimize the complete human-machine system, not software in isolation.

The governing product objective is:

```text
SIMPLEST ADEQUATE METHOD
→ FASTEST RELIABLE USER VALUE
→ STABLE SUPPORTED WORKFLOW
→ EVIDENCE-DRIVEN LATER AUTOMATION
```

Before assigning a difficult implementation task, Engineering Optimization must answer:

1. **Necessity:** What concrete current failure does the work prevent, and is it required in the current product phase?
2. **Blocking detail:** Which exact detail creates the obstacle?
3. **Direct solution:** What is the smallest direct correction?
4. **Alternative:** Can a different interface, boundary, or existing platform function solve it more simply?
5. **Human-assisted control:** Can an experienced operator perform a simple, explicit, low-friction check or decision safely?
6. **Bypass:** Can the obstacle leave the current critical path without weakening a concrete supported-path safety invariant?

A safe human-assisted control is preferred over disproportionate automation when all of the following are true:

- no exchange order is submitted automatically;
- no account, wallet, private-key, signing, or nonce authority exists;
- the operator-facing result and required action are simple and unambiguous;
- the action is low-frequency or naturally aligned with normal trading supervision;
- omission or delay cannot automatically create or enlarge a position;
- the system clearly states when its output must not be relied upon;
- a normal recovery or escalation path exists.

Human participation may provide current-phase value through:

- discretionary acceptance or rejection of every signal;
- rapid comparison of signal time, reference price, current market price, entry zone, chase limit, stop, targets, and risk;
- ignoring all system output while status is not READY or is unknown;
- continuing independent discretionary trading while the assistant is unavailable;
- periodic status refresh during active trading;
- normal systemd restart after persistent failure;
- bounded log capture for targeted engineering diagnosis;
- market-context judgment that the encoded strategy does not yet model.

Human participation must not be used to excuse:

- hidden or ambiguous system state;
- repeated interpretation of shell, procfs, cgroup, or systemd races;
- timing-critical low-level recovery steps;
- frequent manual work that materially interferes with trading;
- automatic exchange-write risk;
- missing hard risk controls after automatic or one-click execution is introduced.

For the current First Launch boundary, ordinary NOT_READY means the operator ignores system signals and rechecks later. It does not by itself require a new stop feature. Existing systemd restart and bounded journal commands are the preferred low-cost recovery path before any new self-healing product is considered.

Before automatic execution is introduced, planning must re-evaluate every human-assisted control. Automatic order safety may not depend solely on the operator noticing a fault in time.

Every launch runbook must include:

- a concise human-machine responsibility matrix;
- exact daily commands;
- exact status meanings;
- the shortest supported recovery sequence;
- the escalation threshold;
- no placeholder hostnames, paths, users, or service names in the final operator copy.

## 5. Model and harness routing

### 5.1 Codex

Preferred use:

- primary code Writer when quota and task complexity justify it;
- bounded repair of a proven code defect;
- repository-local implementation requiring strong code context.

Do not use Codex for:

- status transcription;
- governance document drafting;
- packet formatting;
- duplicate validation reports;
- ordinary product planning;
- tasks that a read-only ChatGPT or TRAE lane can complete independently.

Interfaces:

- desktop application may be used immediately;
- CLI and SDK are later automation layers, not prerequisites;
- no global auto-commit, auto-push, auto-merge, or unrestricted network authority.

### 5.2 TRAE IDE SOLO with DeepSeek V4 Pro

Preferred use:

- Project Control at an explicitly activated safe stage boundary;
- primary Writer in `IDE_SOLO_PRIMARY` mode;
- large coherent design or documentation packages;
- fallback implementation when Codex quota or availability requires it.

Activation requirements:

- project Skills and Commands installed;
- direct read-only activation preflight passed;
- exact project context and model selection confirmed;
- worktree and role isolation confirmed;
- blocked authorities confirmed;
- user explicitly selects the mode.

### 5.3 GLM-5.2

Preferred use:

- strict read-only Operations Review;
- bounded auxiliary analysis;
- documentation and transition-package work;
- independent verification that does not require high-risk final adjudication.

### 5.4 Ordinary ChatGPT high-reasoning windows

Preferred use:

- Engineering Optimization authority;
- independent Security Review;
- independent Final Review;
- product-planning authority;
- exact-head read-only adjudication;
- cross-source consolidation and governance Review.

Use different independent windows for Security and Final Review on credential, runtime, cloud, authority, or trading-boundary stages.

### 5.5 OpenCode with DeepSeek V4 Pro API

Fallback route only after bounded configuration and authority intake:

- user-owned API credentials must not enter the repository or prompts;
- exact model identity and endpoint must be confirmed;
- logging and secret handling must be bounded;
- repository write authority must be stage-specific;
- no automatic mode switch by quota alone.

## 6. Execution-mode control

Only the user may switch modes, effective at the next safe stage boundary.

```text
CODEX_PRIMARY
```

- Codex primary Writer;
- DeepSeek V4 Pro fallback;
- GLM-5.2 auxiliary/Operations Review;
- ordinary ChatGPT independent high-reasoning Review.

```text
IDE_SOLO_PRIMARY
```

- TRAE IDE SOLO Project Control;
- DeepSeek V4 Pro primary Writer;
- GLM-5.2 strict read-only Operations Review;
- Codex reserved or explicitly assigned fallback;
- ordinary ChatGPT independent high-reasoning Review.

A model or harness change is not authority to alter scope, history, branch, commit budget, or Review requirements.

## 7. Codex quota policy

User-reported quota is a planning signal, not an exact billing API.

### Above 40 percent

- Codex may remain primary for critical code stages;
- still route non-code work elsewhere;
- preserve one repair reserve.

### Around 40 percent

- enter critical-path-only mode;
- no speculative hardening;
- no duplicate Review or report generation;
- one Writer only;
- prepare DeepSeek/OpenCode continuity without switching mid-stage.

### At or below 30 percent

- perform continuity intake;
- start no new noncritical Codex work;
- preserve quota for proven blockers and launch-critical closure;
- prefer DeepSeek V4 Pro for new safe-boundary implementation stages after user approval.

### At or near 20 percent

- emergency reserve;
- no new Codex stage without explicit user decision;
- use only for a narrowly proven critical blocker when no accepted fallback is available.

Quota pressure never authorizes weaker tests, skipped Review, or silent scope removal.

## 8. Commit and repair policy

A stage must define:

- target initial commit count;
- maximum pre-Review commits;
- reserved repair capacity;
- hard stop when exhausted.

Normal target:

- one implementation commit;
- zero or one consolidated repair commit.

Before consuming a reserved repair commit:

- consolidate all findings;
- classify real blocker versus non-blocking follow-up;
- validate an uncommitted patch when practical;
- prohibit optional refactor and formatting-only consumption.

No automatic fourth commit, V3 redesign, amend, rebase, or force-push after the accepted budget is exhausted.

A local amend exception is allowed only when:

- the branch is unpublished;
- no PR or exact-head CI is bound to the old head;
- no external accepted evidence depends on the old head;
- no force-push is required;
- the exception is explicitly authorized and audited.

## 9. Validation efficiency

Do not repeat expensive tests without a distinct evidence purpose.

Preferred sequence:

1. targeted tests while editing;
2. one focused pre-commit or pre-amend gate;
3. final candidate focused stability repetitions when boundedness matters;
4. one complete local suite on the final candidate;
5. exact-head CI in the locked environment;
6. independent Review.

Validation must remain truthful:

- never claim an unexecuted check passed;
- never replace a command failure with idealized fixture output;
- no assertion rewriting;
- no command-status bypass;
- no mock-proves-mock tests;
- subprocess harnesses must be bounded and deterministic;
- static fixtures are not real host proof.

## 10. Parallelism

Allowed parallel work:

- exact-head CI;
- independent read-only Reviews;
- packet preparation;
- non-overlapping design/documentation work;
- future-stage late-binding preparation that does not mutate the active branch.

Prohibited parallelism:

- two Writers on the same branch or files;
- competing architecture plans after one engineering ruling is accepted;
- multiple repair lanes for the same findings;
- auxiliary Agents mutating GitHub or active worktrees without authority.

Future two-Writer stages require disjoint paths and an explicit Integration Lane.

## 11. Worktree and environment policy

Reuse a valid, clean, authorized worktree and Python environment.

Recreate only when the current object is:

- missing;
- wrong;
- dirty;
- in use by another Writer;
- invalid;
- insufficiently isolated.

Use `git worktree add`; never emulate a worktree with a normal directory.

Changing window, model, or harness does not require rebuilding a valid environment.

## 12. Prompt and transport policy

TRAE and Codex desktop applications must not be described as terminal-launched CLIs unless an actual CLI is separately installed.

```text
TRAE_MAXIMUM_DIRECT_INPUT: 18,000 characters
TRAE_PROMPT_FILE_MODE: mandatory above 18,000 characters
```

Use one complete task or Review packet, not repeated partial prompts. Delta-only updates are preferred after the initial full contract.

## 13. Persistent rule policy

When the user requests a durable rule, cross-window alignment, fixed policy, or future inheritance, the accepted result must be persisted through the GitHub governance workflow defined in `GITHUB_CANONICAL_RULE_PERSISTENCE_POLICY_V1.md`.

A chat-only statement is not a complete synchronization.

## 14. Absolute authority boundary

Without separate current authorization, no Agent may:

- Mark Ready or merge;
- start services or runtime;
- execute deployment or smoke;
- access AWS or paid resources;
- access credentials, wallets, private keys, signing, or nonce state;
- mutate exchange orders;
- enable Testnet/Mainnet writes;
- enable autonomous trading;
- alter production strategy automatically.

## 15. Escalation

Return to Engineering Optimization when:

- scope or allowlist expands;
- dependency, lockfile, schema, or workflow changes become necessary;
- commit authority is exhausted;
- Writer substitution is required;
- product scope changes;
- a Blocker/High cannot be repaired in scope;
- runtime, cloud, account, or trading authority is requested;
- repeated repair demonstrates route failure.

Return to Product Authority when:

- user value or feature priority changes;
- an item moves between First Launch, V0, and mainline;
- evidence changes the recommended next product configuration.

## 16. Source reconciliation

This policy consolidates and must remain consistent with:

- merged Workflow V3;
- merged Engineering Optimization Successor Handoff V2;
- merged TRAE IDE SOLO direct activation preflight;
- accepted portions of PR #33;
- accepted token and repair-efficiency lessons from prior implementation cycles;
- the current user-approved critical-path and deferred-work rulings.

PR #33 remains a historical Draft input until explicitly superseded or closed after this consolidation is accepted.