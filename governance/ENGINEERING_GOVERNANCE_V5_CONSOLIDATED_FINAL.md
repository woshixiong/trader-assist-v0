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

This constitution grants no unrestricted production deployment, live service
control, credential/private-API, wallet/signing, exchange-write/order,
autonomous-trading, or real-capital authority. Once separately activated,
ordinary GitHub Ready, Merge and closed-scope shadow/test deployment are
deterministic automatic outcomes of verified acceptance and security gates,
not repetitive human approval steps. No automatic GitHub merge grants live
runtime or real-capital authority.

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

Material technical direction is a human choice, not routine executor selection.
Before freezing a new or materially changed architecture, framework/provider,
deployment/recovery method, commodity infrastructure, strategy/research/backtest
execution route, or major scope/cost direction, Engineering Control must first
explain in concise, plain language the root problem (or what remains unknown),
the simplest credible existing/official route, and the meaningful alternative
and cost/trade-off; then obtain the user's current direction decision. An accepted direction may be reused while its
material predicates remain unchanged; do not repeatedly ask for the same choice.
That direction decision never grants protected-action authority.

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

## 5. Risk-proportional engineering and phase verification

**V5 streamlined amendment (candidate until separately reviewed and activated).** Engineering Control binds a change risk tier from actual changed paths, semantic blast radius, intended runtime exposure and evidence, not from the Writer's claim. Unknown classification, mixed-risk packages, governance/control-plane edits, or a discrepancy fail to HIGH. Record the tier and exact classification evidence in the canonical task packet; the controller represents its verified routing decision as `RISK_TIER=LOW|MEDIUM|HIGH` and `RISK_PACKET_VERIFIED` in retained gates. The marker is an adapter to the canonical packet, not authorization to self-declare lower risk.

**LOW**: documentation, non-operational UI presentation and bounded non-critical maintenance with no trading, secrets, permission, deployment, data-integrity or execution effect. Direct small implementation -> focused tests -> exact-head CI -> closeout. No mandatory Plan-only, Pre-code or independent Final Review for each small change.

**MEDIUM**: strategy research and shadow-only code, isolated scanner/market-data features, dashboard functionality and bounded refactors that cannot send orders, mutate production, bypass risk or change exchange credentials. Make coherent, optionally larger development bundles with cheap local tests and a single CI candidate publication instead of CI after every local commit. Skip routine Pre-code and per-slice independent Final Review; run scripted end-to-end phase verification on the integrated user-visible feature before promotion. Failing scenarios become one deduplicated, severity-ranked defect batch; fix in small commits with immediate CI, then rerun only affected and boundary regressions. Medium does not authorize live trading, production exposure or actual deployment.

**HIGH**: OMS/order path, Risk Kernel, sizing, wallet/signing, execution guards, permissions, service/deployment control, persistent-data correctness with trading consequences, external provider/security architecture, governance, or any ambiguity about exposure. Retain one short design/Pre-code Review only when architecture or safety design changes, then one fresh independent Final Review of the exact candidate, required deterministic negative and failure-mode tests, stage-level end-to-end evidence, and current human protected-action authority. Governance amendments require fresh independent review even if documentation-only.

For a HIGH implementation without a new architecture, an existing accepted design plus tests replaces repeated Pre-code Reviews. Engineering Control records this determination. The single independent Final Review remains required.

### OFFICIAL_NATIVE_REUSE fast lane — integration origin, not a financial-risk exemption

Where the goal is solely assembling capabilities **already provided by the pinned NautilusTrader version**, organize one **large, coherent, end-to-end development package** by functional area (native data capture/health, native order lifecycle/risk, native shadow/backtest, native operations). Prove each claimed capability against actual installed pinned-version API/examples and explicitly list unsupported gaps. Do not rewrite framework internals, add a parallel OMS/risk/controller, or infer support from newer upstream versions.

One task brief and one Codex execution plan at package start. Codex may work through many local commits without repeated handoffs, routine Pre-code reviews or full CI per local commit. Perform cheap developer-side syntax/unit/smoke checks while building; run the complete required GitHub CI once on the final published candidate head (and rerun only after real corrections). Then perform **one consolidated strict independent review plus integrated real-behavior and negative/failure-path testing** on the exact package. Consolidate noncritical defects into one reproducible batch; block on critical ones immediately.

Official reuse reduces design uncertainty, **not** the impact of incorrect venue configuration, event routing, lost-data handling, order outcomes, recovery or permissions. Real-capital execution boundaries remain HIGH at final verification even when the upstream component is mature. A test/shadow package contains no order-authorized credentials and cannot promote itself to live. User may personally perform the final acceptance trial after automated verification. Keep experimental proprietary strategy/edge work separate from native framework assembly.

**Routine state paths (new packages only):**
- LOW/MEDIUM: CONTROL_FREEZE -> IMPLEMENT -> LOCAL_VALIDATE -> PUBLISH -> CI_WAIT -> HUMAN_CLOSEOUT_GATE. PLAN is optional; routine PRECODE_REVIEW and FINAL_INDEPENDENT_REVIEW are not required.
- HIGH: CONTROL_FREEZE -> PLAN -> PRECODE_REVIEW (only when design-risk triggers) -> IMPLEMENT -> LOCAL_VALIDATE -> PUBLISH -> CI_WAIT -> OPTIONAL_INTERNAL_REVIEW -> FINAL_REVIEW_READY -> FINAL_INDEPENDENT_REVIEW -> HUMAN_CLOSEOUT_GATE. Where the Pre-code gate is not triggered, PLAN -> IMPLEMENT is allowed only with a separately verified HIGH design-reuse predicate; the current controller does not yet enable this shortcut.
- Untagged/legacy packages continue the strict HIGH path; no automatic migration or reclassification.

Independent validation is **behavioral**, not another blanket code-reading round. A project-local Verification Skill or equivalent harness must specify Launch, Doctor, Drive, Evidence and Cleanup, plus small feature maps. Use the existing test runner, HTTP/CLI, browser and replay tools first. Verification agents act as a real user and an adversarial outsider, using *disposable/offline/shadow* environments without production credentials or exchange write access. Hark Pro and Muse may supply independent **test observations only**, not authoritative code or production changes. The Writer and testing agents must not share a mutable production host. All outcomes are PASS / FAIL / BLOCKED with reproducible evidence; missing evidence is never PASS.

Every slice keeps fast CI and exact-head binding. Every meaningful feature/milestone gets one phase-level E2E/exploratory pass; a release or trading-risk promotion always re-enters HIGH. Do not defer all tests to the end of a large branch. The completed phase report must include tested features, real versus simulated data, negative paths, CI head, evidence artifacts, defects and retained blockers.

Codex thread/worktree continuity is preferred for a coherent task, not a reason to freeze LOW/MEDIUM delivery when a checkpoint survives. If an executor loses its session, resume from exact canonical GitHub evidence and record the new session explicitly; no semantic work may silently be replayed. HIGH frozen work keeps the existing fail-closed exact-resume rule when applicable.

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
qualified. This applies only while the human-selected material direction
remains valid and no unexpected failure requires the §13 stop-and-escalate
rule. A repair budget is a ceiling, not permission to preserve a failed route.

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

Every failed exact-head CI result is classified before retry or mutation.
Classification does not itself authorize an unexpected-failure repair; §13
requires immediate route pause and user direction unless the exact deterministic
mechanical correction or bounded transient recovery was already authorized:

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

## 9. Risk-scoped review and phase evidence

LOW: focused test and exact-head CI status are sufficient for routine code acceptance; no Pre-code or Final Independent Review packet is required. MEDIUM: local focused checks during development, full CI on the final published candidate, and one integrated phase-level independent behavioral verification packet for each meaningful feature milestone or before promotion. OFFICIAL_NATIVE_REUSE: one consolidated strict independent final review and integrated test of the finished large package, never a per-file or per-subfeature review. HIGH and governance: preserve fresh independent Final Review and canonical GitHub result egress. Pre-code Review for HIGH is triggered only by new/changed safety-critical architecture or an explicitly identified design-risk.

Any required independent review reads every materially changed file and records exact PR/head/tree, CI locator, observed behavior, negative tests, unresolved risk, PASS/FAIL/BLOCKED, and its canonical result. A changed head invalidates old PASS and requires targeted revalidation of the changed scope and dependent invariants, not necessarily a full new review of unrelated files. A green CI result without behavioral evidence never qualifies a claim requiring live behavior. Never misrepresent the PR author's own approval as an independent identity.

For HIGH Pre-code decisions use PASS, PLAN_REVISE or CONTROL_REPLAN. If required review evidence cannot be written to canonical GitHub, the review is incomplete; LOW/MEDIUM skip paths do not fabricate review results. Test agents may discover and report defects, but may neither replace HIGH independent review nor authorize protected actions.

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

Priority is (1) human decision before a material technical direction is frozen,
then (2) first-unexpected-failure reset if that direction fails, then (3)
ordinary V5 execution. These are checks inside existing stages, not additional
Review rounds or a new workflow.

On an **unexpected LOW/MEDIUM failure**, first reproduce and classify it, retain
the failing command/evidence in GitHub, and fix within the accepted feature scope
using small CI-checked changes. At a phase checkpoint, aggregate reproducible
defects into one prioritized batch before focused correction and phase re-test.
No new human decision is needed for ordinary in-scope semantic or test failure.
Escalate on a new architecture/provider/security decision, unexpected live-risk
effect, cross-layer authority break, loss of reliable evidence, uncontrolled
repair loop, or expansion beyond the accepted direction.

On an **unexpected HIGH failure**, pause affected source changes, preserve the
exact checkpoint, identify root cause and the mature/official alternative,
then route new architecture, authority, security or funds-impacting decisions
to Engineering Control and the current human. Do not weaken validators or
override risk limits to make CI pass.

A previously human-authorized, narrowly bounded deterministic mechanical
correction, planned red/green local test, or transient transport retry may
continue within its exact existing limits when no new material uncertainty or
route change appears. Do not label a new environmental, architecture, semantic,
cross-layer or long-running-no-progress failure as routine to evade the stop.
No uncontrolled termination of live services/processes: existing safety and
protected-action gates remain in force.

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

### 14.1 Explicit executor input and relay boundary

~~~text
MODEL_EXECUTOR_STDIN_SOURCE=EXPLICIT
SHARED_OUTER_LAUNCHER_STDIN=PROHIBITED
ONE_PASTE_AGENT_WORKFLOW=>FILE_BACKED_PHASE_SEPARATION
PROMPT_IN_ARGV=>STDIN_CLOSED_OR_/dev/null
PROMPT_VIA_STDIN=>DEDICATED_PROMPT_FILE_WITH_EXPLICIT_EOF
REMOTE_DESKTOP_COMMANDER_STATUS=FORMAL_V5_EXECUTION_RELAY
AUTHORITY_TYPE=EXECUTION_TRANSPORT_ONLY
HARD_DEPENDENCY=NO
~~~

Remote Desktop Commander is a quota-limited local execution relay and is
preferred only when the required action genuinely needs local desktop/process
execution and no canonical/native lower-cost surface can perform the equivalent
action. It has no engineering or protected-action authority.

Before every RDC call, all of the following must hold:

~~~text
LOCAL_ONLY_ACTION_OR_EVIDENCE_REQUIRED=YES
NO_CANONICAL_OR_NATIVE_LOWER_COST_EQUIVALENT=YES
CALL_ADVANCES_STATE_OR_RETURNS_DECISIVE_EVIDENCE=YES
RELATED_LOCAL_OPERATIONS_BUNDLED=YES
~~~

Routine GitHub reads/writes, CI/status polling, repeated progress reads,
redundant unchanged identity readback, rereading canonically available files,
and blind connectivity retry loops through RDC are prohibited. The normal local
stage target is at most one RDC start/resume call and zero routine progress
reads; one bounded result read is allowed only for a concrete abnormal or
interactive need. Additional calls require concrete technical necessity.

Automation continuity remains higher priority than RDC quota minimization:
never introduce routine human relay solely to save RDC calls when RDC is
genuinely required for a local-only automated action.

If RDC is unavailable or quota-exhausted, preserve the exact canonical
checkpoint and generate one exact human Terminal command or block; do not rerun
semantic work, consume repair budget, or change package, thread, worktree,
authority, or executor. On transport/network failure, use the existing bounded
retry/fallback contract and never create an RDC retry storm.

Before a real local push containing `.github/workflows/**`, require:

~~~text
GH_WORKFLOW_SCOPE_REQUIRED=YES
GH_WORKFLOW_SCOPE_VERIFIED=YES
~~~

`gh auth status`, API reads, fetch, ls-remote, and dry-run do not prove this
scope. Missing proof pauses at current human credential/scope authority; never
silently refresh OAuth scopes and never count this as semantic failure.

Normal engineering work:

- never commits directly to main;
- never force-pushes or rewrites reviewed shared history;
- uses one bounded branch/worktree scope;
- never commits secrets, credentials, wallets, raw private/account data,
  production DB/log/cache, or real account identifiers;
- never presents simulated/default account or market data as real evidence.

Publication sequence is:

~~~text
EXACT CANDIDATE -> FOCUSED VALIDATION -> DRAFT PR -> EXACT-HEAD CI
-> LOW: BOUNDED CLOSEOUT / MEDIUM: BOUNDED CLOSEOUT + MILESTONE VERIFICATION
-> HIGH OR GOVERNANCE: REQUIRED FRESH INDEPENDENT FINAL REVIEW
-> RETAINED HUMAN PROTECTED-ACTION AUTHORITY
-> RELEVANT POST-MERGE CHECK; LIVE PROMOTION REQUIRES SEPARATE AUTHORITY
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

## 17. Human-exclusive secrets and automated protected boundaries

**Human-only, with no model delegation:** create, obtain, enter, reveal, rotate, revoke or grant access to passwords, API keys, tokens, wallet private keys, seed phrases, SSH keys, signing material, GitHub/AWS credentials and IAM/secret-manager grants. The human performs these directly in the vendor/provider interface. Agents may describe minimal required scopes and safely test whether a *capability* is present, but must never request secret values, print/redact-after-reading secrets, fetch private credentials, or modify secret/identity grants. Preserve secrets outside repository and all AI/test-agent inputs, prompts, logs and screenshots.

The following remain individually human-authority-bound and can **never** be inferred from a passing CI, merge, prior test or shadow deployment:

~~~text
PRODUCTION_RUNTIME_OR_CLOUD_MUTATION_OUTSIDE_PREAUTHORIZED_SCOPE
LIVE_SERVICE_START_RESTART_ENABLE_REBOOT
CREDENTIAL_OR_PRIVATE_API
WALLET_OR_SIGNING
EXCHANGE_WRITE_OR_ORDER_ACTION
AUTONOMOUS_OR_REAL_CAPITAL_TRADING
~~~

**GitHub code acceptance is automated after safeguards, not a human click.**
After the governance change is properly reviewed and activated, the verified
exact-head pipeline may automatically Mark Ready, enable native GitHub auto-merge
and delete the merged temporary branch when all applicable mandatory status
checks, required independent HIGH/governance or native-reuse review, change-scope
integrity, CODEOWNERS/branch-protection requirements and negative-path claims
PASS. Block immediately on any failed/missing/stale check, unresolved security
issue, untrusted evidence, drifted head or required review absence. Do not
weaken branch protection to force auto-merge. GitHub native auto-merge is
preferred to a home-grown merging controller. The actor that wrote code
cannot forge review/CI attestation.

**Scoped test-only deployments** may automatically install, start, health-check
and roll back an immutable GitHub-hashed build in an isolated Shadow/test
directory or service after a one-time, explicitly configured allowlisted
deployment scope and OS-level credential separation. This never permits
production service restart, real order placement, wallet reads or credential
changes. Limit rollout to CPU/memory constraints of the existing AWS host,
default OFF, and deploy only artifacts passing current CI. GitHub keeps the
commit, build hash, deployment/health evidence and last-known-good rollback
reference. No direct root shell from AI agents. Human final exploratory
acceptance is the last check before separately authorized live promotion,
not a mandatory approval for every GitHub Merge.

**Current governance transition:** This candidate does not change active main
permissions. PR #339 itself remains subject to the current main V5 gates and
independent governance review until separately accepted and activated. Native
GitHub auto-merge/branch-protection and restricted AWS deployment are not
configured by merely editing this constitution. Controller and CI must
provide non-forgeable verified evidence before any shortcut is enabled.

---

## 18. Governance maintenance

Keep one manually authored generic project-wide engineering constitution.
AGENTS, manifest, Rules Index, Project Instruction bridge, skills, and model
profiles are thin routing/configuration/progressive-disclosure surfaces and may
not become competing constitutions.

Model IDs and execution defaults belong in refreshable manifest/profile
configuration. Durable lessons that are truly project-wide belong here.
Task-specific details remain in their narrow lifecycle.

Material governance changes require a fresh independent review, matching
controller/validator/test updates, and current authorization before activation.
A proposal branch or Draft PR is never itself an active rule.
