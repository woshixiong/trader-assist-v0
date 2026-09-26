# Trader Assist / Trade OS — Engineering Governance V5 Consolidated Final

**Status:** CANDIDATE — NOT ACTIVE ON MAIN UNTIL ACCEPTED V5 ACTIVATION MERGE  
**Repository:** woshixiong/trader-assist-v0  
**Frozen V5-A base:** f17d436b222061ab2229d83f09f743182353fe11

This file is the candidate sole manually authored project-wide engineering
constitution for V5. Until activation is independently accepted and merged,
main remains governed by V4. This file cannot activate itself.

Task-specific Product, Strategy, Operations, Security, deployment, executor, and
operator procedures may be stricter in their narrow domains but may not weaken
or compete with this constitution.

This constitution grants no Mark Ready, merge, deployment, runtime/cloud
mutation, service-control, credential/private-API, wallet/signing,
exchange-write/order, autonomous-trading, or real-capital authority.

---

## 1. Authority architecture

### 1.1 Canonical engineering truth

GitHub is the sole durable engineering source of truth. Before material work,
freshly resolve the repository, current main, exact base/head/tree, current
Issue/PR/package-state, changed paths, CI evidence, artifacts, domain authority,
and retained human gates.

Exact canonical objects override chat history, copied prompts, user summaries,
remembered SHAs, stale branches, old PR descriptions, previous assistant
conclusions, and local cache.

The bootstrap path is:

~~~text
AGENTS.md
-> governance/ACTIVE_GOVERNANCE_MANIFEST.json
-> manifest-selected sole constitution
-> exact current package-state / Issue / PR
-> PROJECT_RULES_INDEX when navigation is needed
-> triggered narrow procedure only
~~~

The manifest is a machine map/configuration surface. The Rules Index and Project
Instruction bridge are navigation/adapters. They do not create a second
constitution.

### 1.2 Precedence

When authorities conflict:

1. explicit current human authority and safety boundaries;
2. current accepted Product / Strategy / Security / Operations authority in its
   real domain;
3. this constitution;
4. current frozen Development Package / Control Capsule / package-state;
5. triggered subordinate procedures and execution profiles;
6. historical governance and incident material as evidence/rationale only.

A less strict source never weakens a stricter safety or authority requirement.

### 1.3 Durable state and compact control capsule

Chat is a reasoning surface, not durable task state. Material workflow state
belongs in GitHub using one compact machine-readable package-state record plus
exact evidence locators.

A material package state must be able to identify at least:

~~~text
PACKAGE_OR_TASK_ID
GOVERNANCE_EPOCH
EXACT_MAIN
EXACT_BASE
EXACT_HEAD_OR_TREE
TASK_PACKET_HASH
ROLE
ROUTE
CURRENT_STAGE
RESUME_STAGE
CURRENT_BLOCKER
NEXT_ALLOWED_TRANSITION
CODEX_THREAD_OR_SESSION_ID_WHEN_AVAILABLE
CURRENT_PR
CI_HEAD_AND_RUN_LOCATOR
SEMANTIC_REPAIR_COUNT
TRANSPORT_OR_CAPABILITY_PAUSE
COMPLETED_WORK_LEDGER
RETAINED_USER_GATES
LAST_CANONICAL_EVIDENCE
~~~

Full history remains behind canonical locators. Do not duplicate long evidence
inside every handoff.

---

## 2. Roles and authority separation

### Engineering Control

Owns requirement interpretation, architecture, decomposition, authority,
execution-route selection, Development Package/Control Capsule freeze, external
contract freeze, acceptance/adversarial matrix, material exceptions, repair
replanning, and retained-gate closeout.

### Writer

Implements only the frozen package and performs bounded in-scope validation and
authorized publication. A Writer does not redesign scope or self-approve.

### Independent Reviewer

A fresh ordinary ChatGPT context that did not control or implement the
candidate. Review is read-only with respect to repository code/config/candidate
state, except for one bounded canonical review-result egress to GitHub.

### Human Gate

Owns protected actions. No governance result, Writer result, CI status, review,
or previous approval implies a current protected-action authorization.

Implementers do not become reviewers. Reviewers do not implement. Engineering
Control or Writer PASS is never independent acceptance.

---

## 3. Execution routing

Engineering Control freezes exactly one route from current evidence:

~~~text
A  DETERMINISTIC / MECHANICAL
   -> zero-model provider-native or deterministic tooling

B  SMALL / FROZEN / BOUNDED SEMANTIC
   -> fresh ordinary ChatGPT Writer

C  LARGE / COHERENT / MULTI-STEP CODING
   -> manifest-selected Codex CLI route
   -> single primary Codex thread by default

D  UNRESOLVED ARCHITECTURE / SECURITY / AUTHORITY /
   HIGH-CONSEQUENCE AMBIGUITY
   -> Engineering Control resolves and refreezes first
~~~

The user is not asked to choose executor, Plan versus implementation, or routine
failure routing when the evidence already determines it.

Before every model-backed launch freeze:

~~~text
ROLE
EXECUTOR_SURFACE
PROVIDER
MODEL
REASONING_OR_EQUIVALENT
WEB_SEARCH_OR_TOOL_STATE
SESSION_POLICY
RESOURCE_STATE
SELECTION_REASON
~~~

Concrete model IDs and refreshable model choices live in the active manifest,
current model profile, or bound package rather than permanent capability rules.

Required requested/actual identity drift fails closed. No silent executor,
model, reasoning, surface, or authority fallback is permitted.

---

## 4. Single-primary execution topology

The default Codex topology is one primary thread/session for one coherent
package. Default subagent count is zero.

At most one optional child may run concurrently, and only for genuinely
separable bounded work such as read-only repository discovery or an optional
internal read-only implementation review.

Rules:

- child runtime model/reasoning identity must be verifiable before use;
- if identity is not verifiable, skip the child;
- never silently inherit or fall back to the parent/default profile;
- children receive fresh/minimal bounded context, not the full parent history;
- recursive subagent delegation is prohibited by default;
- CI/status polling is never an agent role;
- final authority-bearing review is never delegated to an internal Codex child.

Parallel implementation is allowed only when tasks are independent, writes are
disjoint, authority is not shared, and reconciliation is deterministic.
Final integration, exact-head review, and merge-front movement are serialized.

---

## 5. Route C lifecycle and Pre-code Review

A large coherent Codex package uses one primary thread/session and one bounded
worktree/checkpoint chain where the execution surface supports it.

~~~text
ENGINEERING_CONTROL_FREEZE
-> DETERMINISTIC EXACT-BASE BOOTSTRAP
-> CODEX PLAN-ONLY
-> FRESH PRE-CODE REVIEW
-> SAME CODEX THREAD RESUME ON PASS
-> IMPLEMENT / FOCUSED VALIDATE
-> DETERMINISTIC PUBLISH
-> EXACT-HEAD CI
-> BOUNDED REPAIR LOOP IF NEEDED
-> OPTIONAL INTERNAL READ-ONLY REVIEW WHEN JUSTIFIED AND VERIFIABLE
-> FINAL REVIEW MANIFEST
-> FRESH FINAL INDEPENDENT REVIEW
-> ENGINEERING CONTROL CLOSEOUT
~~~

Plan-only may choose implementation order and mechanics but may not change
frozen scope, product behavior, architecture authority, external contracts,
protected actions, or acceptance criteria.

Pre-code Review happens after Plan-only and before product-source mutation.
It is a fresh ordinary ChatGPT / High review of the exact package, plan, base,
architecture/contracts, acceptance criteria, adversarial matrix, and minimal
governance needed for the decision.

Pre-code decisions route deterministically:

~~~text
PASS
-> resume the same Codex thread/session and implement

FAIL + PLAN_REVISE
-> resume the same Codex thread/session for bounded plan revision
-> run a fresh Pre-code Review on the revised plan

FAIL + CONTROL_REPLAN
-> return directly to Engineering Control for refreeze
~~~

Same-thread resume is a fail-closed continuity invariant:

~~~text
PRE_CODE_PASS_SAME_THREAD_RESUME_REQUIRED=YES
PLAN_REVISE_SAME_THREAD_RESUME_REQUIRED=YES
EXACT_RESUME_UNAVAILABLE_OR_UNVERIFIABLE=>PAUSED_CAPABILITY/ENGINEERING_CONTROL
SILENT_NEW_SEMANTIC_THREAD_SUBSTITUTION=PROHIBITED
~~~

For both PASS and PLAN_REVISE, the exact primary Codex thread and worktree must
be resumed. If exact resume semantics are unavailable or cannot be verified,
preserve the checkpoint, enter the capability-paused state, and return to
Engineering Control. Never substitute a new semantic Codex thread silently.

The user does not select the failure route.

---

## 6. Deterministic controller contract

The V5 controller is a small deterministic state machine, not an AI agent and
not a second authority.

It may own only deterministic workflow state/transitions, including:

- exact package/base/head/tree;
- task hash and governance epoch;
- current stage and resume stage;
- Codex thread/session locator where available;
- exact-head CI binding;
- semantic repair count;
- quota/transport/capability pause state;
- stale-evidence invalidation;
- integration-front ordering;
- next allowed transition;
- last canonical evidence.

It must not decide architecture, reinterpret requirements, alter acceptance,
perform model-based review, act as a generic orchestrator, or duplicate GitHub
as canonical state.

The initial V5 controller target is the smallest native CLI/process approach
that can parse structured execution events, preserve checkpoint identity, and
drive deterministic Git/GitHub/CI transitions. A generic agent framework,
daemon, database, web service, or separate user-facing launcher is not a V5
requirement.

The controller implementation/bootstrap/validator is a later implementation
surface and must be qualified before V5 activation.

---

## 7. Automated middle lifecycle, repair budget, and interruption

After a passing Pre-code Review, routine implementation, focused validation,
publication, CI wait, bounded repair, and handoff should proceed without
routine human relay when the deterministic controller and permissions are
qualified.

Semantic repair budget:

~~~text
INITIAL IMPLEMENTATION
+ REPAIR 1
+ REPAIR 2 / HARD ROOT-CAUSE ROUTE
THIRD SEMANTIC FAILURE => ENGINEERING CONTROL REPLAN
~~~

Repair 1 stays on the normal frozen Writer route. Repair 2 uses the manifest-
selected hard-root-cause profile. A third semantic failure, a new root cause,
scope expansion, architecture/provider/dependency decision, security issue, or
authority conflict returns to Engineering Control.

Quota exhaustion, UI interruption, transport failure, CI transport loss, or
review-result egress failure is not semantic failure. Resume the exact durable
checkpoint. Never rerun completed semantic work merely because output was
interrupted.

No hidden semantic retry is allowed.

---

## 8. CI and failure classification

After Draft PR publication, CI/status waiting is deterministic:

~~~text
MODEL_MEDIATED_CI_POLLING=PROHIBITED
RAW_SUCCESS_LOG_INGESTION=PROHIBITED_BY_DEFAULT
EXACT_HEAD_BINDING=REQUIRED
~~~

Verify PR head before waiting and at terminal readback. A changed head invalidates
old-head CI and review evidence.

Every failed exact-head CI result is classified before retry or mutation:

~~~text
TRANSIENT_OR_KNOWN_FLAKE
DETERMINISTIC_MECHANICAL
SEMANTIC
INFRASTRUCTURE_OR_TRANSPORT
UNRESOLVED
~~~

A known transient may receive at most one same-head rerun. A deterministic
source defect receives a narrow proven mechanical repair and a new exact-head
run. A semantic failure consumes the frozen semantic repair budget.
Infrastructure/transport recovery preserves the semantic checkpoint.
Unresolved failure gathers only bounded decisive evidence and returns to
Engineering Control.

Success logs are not model input. Failure evidence is limited to the minimum
decisive run/job/step excerpt.

---

## 9. Review result egress is part of review completion

Every Pre-code Review and Final Independent Review must persist its complete
result to canonical GitHub before the review stage is complete.

~~~text
REVIEW_DECISION_COMPLETE
AND CANONICAL_GITHUB_RESULT_EGRESS != PASS
=> REVIEW_STAGE_NOT_COMPLETE
~~~

The user must not carry long review findings between windows.

### 9.1 Pre-code Review result

Canonical destination: the Development Package Issue/package-state record.

Required structured block:

~~~text
REVIEW_TYPE=PRE_CODE
REVIEW_RESULT_KEY=
PACKAGE_ID=
FROZEN_BASE=
PLAN_REF=
DECISION=PASS|FAIL
FAIL_ROUTE=NONE|PLAN_REVISE|CONTROL_REPLAN
BLOCKERS=
NEXT_DESTINATION=
NEXT_ACTION=
NEXT_COMMAND_REF_OR_LITERAL=
REVIEWER_MODE=FRESH_ORDINARY_CHATGPT_READ_ONLY
RESULT_EGRESS=GITHUB_CANONICAL
~~~

### 9.2 Final Independent Review result

Final Review uses a fresh ordinary ChatGPT context with High reasoning, reads
the exact current PR/base/head/tree/diff, frozen acceptance/adversarial matrix,
exact-head CI, final review manifest, and minimal authority/safety rules.

Required structured block:

~~~text
REVIEW_TYPE=FINAL_INDEPENDENT
REVIEW_RESULT_KEY=
PR=
BASE=
HEAD=
TREE=
DECISION=PASS|FAIL
BLOCKERS=
CI_EVIDENCE=
REVIEW_SUBMISSION_MODE=NATIVE_REVIEW|COMMENT_ONLY
NEXT_DESTINATION=
NEXT_ACTION=
NEXT_COMMAND_REF_OR_LITERAL=
RESULT_EGRESS=GITHUB_CANONICAL
~~~

If the authenticated PR owner cannot submit a native independent approval, use
COMMENT_ONLY canonical evidence. COMMENT_ONLY is evidence, not a second
identity. Do not misrepresent self-review as independent GitHub identity.

A changed candidate head requires a new fresh Final Reviewer.

---

## 10. Zero-decision handoff contract

Every expected stop emits exactly enough information for the next node to act:

~~~text
DECISION=
CANONICAL_GITHUB_REF=
NEXT_DESTINATION=
NEXT_ACTION=
COPY_PASTE_COMMAND_OR_PROMPT=
~~~

The copy-paste command/prompt must be complete. Do not require the user to
reconstruct SHA, logs, findings, route, or next action.

A fresh Engineering Control window must be able to take over by reading only:

~~~text
AGENTS.md
-> active manifest
-> manifest-selected constitution
-> current package-state / Issue / PR
-> triggered narrow procedure only
~~~

It then returns a compact takeover capsule: current main, active governance,
current package/PR, stage, blocker, route, authority boundary, and exact next
action.

Historical governance and old chat transcripts are not routine startup input.

---

## 11. Context, cache, and progressive disclosure

Use stable instructions/tool definitions as the context prefix and append
dynamic package state afterward. Preserve/resume the same exact primary Codex
thread and worktree for Plan -> implementation -> Repair 1/2. This continuity
is mandatory and fail-closed; inability to verify exact resume pauses at the
capability boundary rather than authorizing a fresh semantic thread.

Load only the minimum active governance, exact package/manifest, affected
code/tests, and triggered procedure needed for the current decision.

Do not feed success logs or broad repository history to models. Store durable
decisions/evidence in GitHub so context rotation is cheap and safe.

Compaction is context management, not durable state.

---

## 12. Research and mature-solution invariants

Material direction-setting follows:

~~~text
INDEPENDENT ANALYSIS
-> CURRENT EXTERNAL / MATURE EVIDENCE
-> SYNTHESIS / DECISION
~~~

Research must converge to a disposition rather than expand indefinitely.
Safety, authority, correctness, data-integrity, or causal blockers cannot be
traded away for speed or token savings.

For commodity infrastructure, prefer provider-native, official/standard, or
mature maintained external ownership before custom rebuild. A fitting mature
capability blocks a second project-owned commodity implementation unless a
current explicit human exception authorizes it.

Project-specific strategy intelligence may remain project-owned. Architecture
ownership must remain single and explicit per durable responsibility.

---

## 13. Architecture, continuity, and verification

Global root cause precedes repeated local patch loops. Mixed state, duplicate
authority, repeated adjacent fixes, or new cross-layer failures trigger
route-level reanalysis rather than validator weakening.

For authoritative adjacent layers, supported domains must close cleanly and
valid admitted input must have a deterministic semantic result.

Prefer stable narrow contracts, one current implementation, and replaceable
policy over speculative generalized platforms.

Verification is claim-based and designed with implementation. Use the cheapest
decisive layer first and expand only as the claim requires. Tests must exercise
the real authority/composition seams relevant to the claim. Platform-sensitive
claims run on their authoritative environment.

Broad PASS/DONE language may not overstate unrun, stale, wrong-head, or
nonrepresentative proof.

---

## 14. Repository, publication, and transport discipline

Normal engineering work:

- never commits directly to main;
- never force-pushes or rewrites reviewed shared history;
- uses one bounded branch/worktree scope;
- never commits secrets, credentials, wallets, raw private/account data,
  production DB/log/cache, or real account identifiers;
- never presents simulated/default account or market data as real evidence.

Publication sequence is:

~~~text
EXACT CANDIDATE
-> FOCUSED VALIDATION
-> DRAFT PR
-> EXACT-HEAD CI
-> FRESH FINAL INDEPENDENT REVIEW
-> CURRENT HUMAN MARK-READY AUTHORITY
-> CURRENT HUMAN MERGE AUTHORITY
-> REQUIRED LIVE-MAIN / POST-MERGE VERIFICATION
~~~

For transient network/TLS/HTTP instability, preserve the semantic checkpoint
and same execution/credential route first. Idempotent reads normally receive a
small bounded retry budget. A write may be retried only after canonical
readback proves no mutation or proves the exact target is unchanged and retry
is safe. Ambiguous mutation without readback fails closed.

Transport recovery never authorizes force push, credential weakening, or
semantic rerun.

Human-executed commands are engineered artifacts and must be safe, bounded,
reproducible, and tailored to the observed OS/shell/tool contract.

---

## 15. Exact release/runtime separation

Keep strict separation between source, exact release artifact, staged proof,
public-provider rehearsal, exact-head CI/review, target-host qualification,
bounded shadow, and separately authorized live action.

Merge does not authorize deployment or runtime mutation. Qualification evidence
does not authorize real-capital or exchange action.

---

## 16. Pre-V5 work and activation boundary

Unfinished packages created under pre-V5 governance do not silently inherit V5
identity. After V5 activation, each such package must be explicitly rebound to:

- V5 governance epoch;
- exact current main/base;
- exact current package/head;
- current V5 route/model/reasoning;
- current acceptance and authority.

V5 is not ACTIVE merely because candidate files exist.

Activation requires all frozen qualification evidence, including V5
single-constitution consistency, CLI/model identity, permission/auto-review,
protected-action nonregression, controller/state-transition testing, success
and failure simulations, exact-head CI, fresh Independent Review, replacement
of the ChatGPT Project Instruction with the version-agnostic bridge, and the
frozen non-production end-to-end canary requirement.

V4/VNext archive/supersession cleanup happens only in the separately authorized
later stage. V5-A does not archive or delete them.

---

## 17. Protected human gates

Each protected action requires explicit current human authority:

~~~text
MARK_READY
MERGE
BRANCH_DELETION
DEPLOYMENT
PRODUCTION_RUNTIME_OR_CLOUD_MUTATION
SERVICE_START_RESTART_ENABLE_REBOOT
CREDENTIAL_OR_PRIVATE_API
WALLET_OR_SIGNING
EXCHANGE_WRITE_OR_ORDER_ACTION
AUTONOMOUS_OR_REAL_CAPITAL_TRADING
~~~

Mark Ready and Merge remain two distinct protected actions. After Final Review
PASS, one current user message may conditionally authorize both actions. Before
acting, Engineering Control must fresh-verify the exact reviewed head, all
required CI, and no drift against the frozen predicates. If every predicate
matches, a second authorization prompt is prohibited. If any predicate changed
or is unknown, fail closed without performing either action and without
consuming that conditional authorization.

~~~text
MARK_READY_AND_MERGE_REMAIN_PROTECTED_ACTIONS=YES
ONE_CURRENT_USER_MESSAGE_MAY_CONDITIONALLY_AUTHORIZE_BOTH=YES
SECOND_AUTHORIZATION_PROMPT_WHEN_FROZEN_PREDICATES_MATCH=PROHIBITED
CHANGED_OR_UNKNOWN_PREDICATE=>FAIL_CLOSED_WITHOUT_CONSUMING_AUTHORIZATION
~~~

No package, controller, Writer, CI, Reviewer, or prior authorization can infer
these gates.

---

## 18. Governance maintenance

Keep one manually authored generic project-wide engineering constitution.
AGENTS, manifest, Rules Index, Project Instruction bridge, skills, and model
profiles are thin routing/configuration/progressive-disclosure surfaces and may
not become competing constitutions.

Model IDs and execution defaults belong in refreshable manifest/profile
configuration. Durable lessons that are truly project-wide belong here.
Task-specific details remain in their narrow lifecycle.

Material governance changes require fresh independent review before activation.
