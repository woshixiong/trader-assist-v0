# V5 Fast-Safe Engineering: Evidence Review and Target Contract (2026-10-15)

**Status:** RESEARCH / CANDIDATE ONLY. Not currently operative policy. Main's ACTIVE V5 constitution wins until reviewed and explicitly activated. This document includes unresolved blocking gaps in Draft PR #339. No Codex Cloud migration or AWS host change is authorized by this document.

## 1. Intent and constraints

Reduce excessive task-by-task Plan-only, Pre-code Review, Final Independent Review, handoffs and repeated human relay while retaining stringent controls for financial consequences. Default to ChatGPT for analysis/review and Codex for substantial production coding. Hark Pro/Muse are optional **untrusted test observers** on synthetic/shadow environments only; neither may author authoritative production changes or hold live keys. Reuse official tool capabilities, GitHub CI and systemd rather than building a new controller or Agent framework. Do not require extra model/API subscriptions, extra AWS instances or permanent expensive services.

**Goal:** Small bounded work can ship after deterministic evidence; meaningful feature changes receive real-product and negative-path verification at phase checkpoints; high-risk trading changes retain independent design/security judgment and explicit real-capital authority. A green CI check alone does not prove trading system safety.

## 2. Practices studied and confidence

| Practice | What it contributes | What we should not copy |
|---|---|---|
| DORA continuous integration / working in small batches | Short-lived changes, fast feedback, integration in hours not giant branches; tested independently before phase closure | Do not save **all** testing for the end of a huge change |
| DORA deployment automation and Fowler's deployment pipeline | Build once and progressively validate artifact through smoke, test and promotion stages; machine-readable release evidence | Do not equate auto-deploy-to-staging with permission to send live orders |
| Cursor pstack / verification skill | Define a feature map with Launch, Doctor, Drive, Evidence, Cleanup; drive actual product; inspect artifact, do not trust agent self-report | The pstack model ensemble is expensive and optional; never install whole ecosystem just for process |
| Playwright Test Agents | Planner, generator, healer can create and execute browser-level usage tests using existing tools; headless CI reports and traces | It is a UI test layer, not a financial risk, deterministic engine or exchange execution oracle |
| OpenHands Agent Server / automation | Shows feasibility of event-driven agent orchestration and sandboxed long tasks | Self-hosting the stack creates maintenance/resource burden and is not required for the current no-extra-cost target |
| GitHub Actions / AWS OIDC / AWS SSM Run Command | Provider-native repeatable deploys; short-lived cloud credentials, target restriction and auditable command history | Direct privileged SSH sessions from an LLM to live trading host are not an acceptable normal deploy route |
| AWS CodeDeploy rollback | Known-good immutable revision and rollback by redeploying prior release | Full CodeDeploy setup unnecessary for a small single-host shadow service if an existing systemd release script suffices |

Primary sources:
- https://dora.dev/capabilities/streamlining-change-approval/ (heavy external approvals harm delivery; targeted peer review and automation are preferred, not "never review")
- https://dora.dev/capabilities/continuous-integration/
- https://dora.dev/capabilities/working-in-small-batches/
- https://dora.dev/capabilities/deployment-automation/
- https://www.martinfowler.com/bliki/DeploymentPipeline.html
- https://github.com/cursor/plugins/blob/main/pstack/docs/guide/06-verify-and-ship.md
- https://github.com/cursor/plugins/blob/main/pstack/skills/figure-it-out/SKILL.md
- https://playwright.dev/docs/test-agents
- https://github.com/OpenHands/OpenHands
- https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws
- https://docs.aws.amazon.com/systems-manager/latest/userguide/run-command.html
- https://docs.aws.amazon.com/codedeploy/latest/userguide/deployments-rollback-and-redeploy.html

## 3. Diagnosis of ACTIVE V5 (read on main, 2026-10-15)

- `AGENTS.md`: fixed Route C Codex CLI; cross-window handoff records required at every stop.
- `governance/ENGINEERING_GOVERNANCE_V5_CONSOLIDATED_FINAL.md`: mandatory Plan-only -> fresh Pre-code -> same thread -> CI -> fresh Final Review -> control closeout; first unexpected failure may force human architecture decision even when ordinary in-scope; separate Mark Ready / Merge.
- `governance/ACTIVE_GOVERNANCE_MANIFEST.json`: review protocol and CLI are pinned as universal defaults.
- `scripts/control/v5_controller.py`: exact stages are hard-coded and tests assert this lifecycle. Editing docs only will **not** simplify routing.
- `scripts/check_v5_governance.py`, `tests/control/*`, Skills, Bridge and `docs/engineering/CODEX_V5_OPERATING_GUIDE.md` also encode or narrate old gates.
- `.github/workflows/ci.yml` already has integrity, ruff, mypy, pytest, secrets and locked dependency checks. Reuse these instead of writing another test controller.

**Diagnosis:** Repeated read-only semantic review and human cross-window relay cause latency; preserve CI and safety, but turn review into an explicit risk-triggered exception.

## 4. Target risk classification (NOT based on a Writer's self-report)

- LOW: docs, wording/presentation, non-operational isolated maintenance; cannot alter exchange, execution, risk, identity, persisted market/account data, privileges or deployment surfaces. One branch/PR, focused check, exact-head CI, no AI pre-review/final review.
- MEDIUM: offline backtest, strategy research, shadow-only experiments, isolated scanner/dashboard/non-execution features. Small CI-checked changes; real launch-and-drive milestone verification, one deduplicated defect batch; no live deploy/order privileges. A promotion to a live-use artifact always reclassifies HIGH.
- HIGH: execution, OMS, Risk Kernel, wallet/signing, private API, order guard, production service/deploy/credential control, trading-relevant data integrity, architectural security migration or governance. Independent Final Review of exact state; design Pre-code Review only where a new safety design exists; deterministic negative-path tests; stage proof; separate production and real-capital permission.
- UNKNOWN, multi-tier, missing provenance, changes in governance or the risk-classifier itself => HIGH.

**Security invariant:** A `retained_gates` string (e.g. `RISK_PACKET_VERIFIED`) is insufficient as proof: if a Writer can modify it, LOW/MEDIUM shortcuts are forgeable. Risk classification needs non-self-attested evidence recorded by Engineering Control (or a verified policy authority), derivation from changed paths, and exact-head integrity. HIGH-protected paths must override all LOW claims.

## 5. Suggested user-facing lifecycle

~~~text
USER GOAL
 -> ordinary ChatGPT clarifies risk/acceptance, only material architecture decisions
 -> Codex implements a bounded feature slice; existing CI checks every PR commit
 -> for meaningful feature milestones: launch disposable sandbox/shadow
 -> independent agent drives product as user + adversarial tester
 -> capture actual traces, logs, outputs and negative outcomes; triage/dedupe findings
 -> Codex fixes reproducible defects in focused PR commits; affected CI/regression reruns
 -> LOW/MEDIUM non-live closeout; HIGH exact-head independent Final Review
 -> release is a distinct target-specific act (shadow automatic only when safely authorized)
 -> real-capital/credentials/risk-authority deployment remains human-gated
~~~

The loop is bounded by **objective regression evidence** and scope, not by an arbitrary two-repair budget or mandatory fresh reviewer on every commit. For persistent repeated or cross-domain failure, pause and investigate root cause. Never let an agent alter its acceptance predicates to pass.

## 6. Project-local Verification Skill proposal (reuse current runners first)

Write a small `.agents/skills/trade-os-verify/SKILL.md` (not a new orchestration platform) with:
1. **Launch:** disposable workdir or GitHub hosted CI; explicit fake account/testnet/shadow; order writer disabled.
2. **Doctor:** correct commit/artifact identity, dependency lock, health/readiness, effective risk config and lack of exchange write credentials.
3. **Drive:** CLI/API/dashboard routes, scanner decisions, trigger/backtest on a known dataset, corrupted/disconnected feeds, reset after restart.
4. **Evidence:** input bundle hash, stdout/trace/screenshot (where relevant), assertions, expected and actual output, CI locator, run timestamp; PASS/FAIL/BLOCKED not model judgment.
5. **Cleanup:** only terminate own test session and test files; never stop a shared production process.

Initial feature map: `scanner/signal`, `capture/gaps`, `risk/order-denial`, `dashboard/manual-operator-controls`, `release/rollback`. Only existing/executable surfaces can be marked VERIFIED; no invented smoke checks.

Testing roles:
- End-user agent: does the feature work with real commands/UI? Is the operator informed?
- Adversarial agent: stale prices, delayed/out-of-order events, duplicates, missing bars, exchange reject, network loss, restart, risk threshold, duplicate order, stale deploy.
- Deterministic oracle: assertions for invariants and accounting (agent cannot override), exchange writes remain impossible in shadow.
- Hark Pro/Muse: optional isolated outsider evidence (report only), never final trust anchor for money-bearing code.

## 7. Fast reversible AWS verification (FUTURE, separate deployment work)

Stage 0: check instance model (EC2 vs Lightsail), existing live process services, free RAM/storage and possible staging namespace. Never assume a spare 2GB box can run a full duplicate trading stack without interference.
Stage 1: CI builds an exact SHA/hash release and records manifest; compile/tests on GitHub-hosted runner to avoid live-host CPU load.
Stage 2: scoped standing operator authorization for a **distinct test/shadow directory and non-order-enabled service**. Target install is an allowlisted root-owned deployment script callable by a least-privileged identity.
Stage 3: GitHub Actions deploys to test/shadow via AWS-native SSM Run Command where the instance is managed and cost-free for EC2, otherwise a restricted SSH deployment key; OIDC for AWS auth where supported. Remote Desktop Commander on AWS is for diagnosis and exceptional manual commands, not default CI transport.
Stage 4: health, specific feature assertions, no-write check, process/resource envelope and run ID all must PASS. On failure, stop candidate and restore last known-good symlink/artifact; record result to GitHub.
Stage 5: independent HIGH-gated production promotion only after exact artifact review; deployment and order enablement are separate gates.

Constraints: no live keys in verification sessions, no agent/root login, no webhook secrets in PR artifacts, no arbitrary shell from untrusted inputs, no automatic service restart on actual money-bearing target. **Never register this production/public-repository AWS server as an unrestricted self-hosted GitHub Actions runner**: GitHub explicitly warns that public-repository pull requests can execute untrusted code on it. Build/test on GitHub-hosted runners; use a restricted deploy command to the isolated test target. Reference: https://docs.github.com/en/actions/how-tos/manage-runners/self-hosted-runners/add-runners No extra AWS instance or paid API dependency. SSM for **non-EC2 (e.g., Lightsail)** needs separate capability and pricing verification; do not assume the free EC2 statement applies.

## 8. Defect consolidation versus risk of delayed testing

Use a bug-bash **after every integrated feature milestone**, not only at the end of many days of feature work. Each bug record: risk severity, user path, exact SHA, input, reproducible failing assertion or trace, affected path, expected outcome and evidence locator. Dedupe by root cause; fix P0/P1 safety cases immediately. Batch ordinary visual/ergonomic issues only after baseline fast CI remains green.

Outcomes:
- VERIFIED: relevant observed behavior and negative-path assertions PASS at current head.
- NOT_VERIFIED: behavior failed or evidence disproves expected result.
- INCONCLUSIVE/BLOCKED: unavailable test environment, missing samples/keys, stale evidence. These cannot justify deployment.

## 9. Blocking issues before activation of Draft PR #339

1. **P0 Provenance:** Current controller admits LOW/MEDIUM when state has two strings; no verified independent risk attestation. Implement verifier and deny forged/unknown state before any skip is enabled.
2. **P0 CI correctness:** Current controller checks CI head and presence of a locator, but not PASS conclusion/proof at transition time. Route must consume trusted exact-head successful CI result, not an arbitrary locator.
3. **P0 MEDIUM phase gate:** Draft prose describes milestone user/adversarial verification but controller permits closeout without phase evidence. Represent milestone boundaries and immutable result binding, including a final promotion gate.
4. **P0 Legacy compatibility:** Preserve untagged V5 package paths and known material deployments; never auto-migrate active PRs.
5. **P1 Consistency:** `CODEX_V5_OPERATING_GUIDE.md`, other bootstrap procedures, validators and tests still describe universal Pre-code/Final cycles. Update or explicitly mark old snapshots legacy.
6. **P1 Recovery:** Stage semantics and old code label HIGH Pre-code as optional, while current transition requires it. Align manifest docs and controller state and prove with tests.
7. **P1 Environment:** A test/shadow deploy permission must be separated from live service/order authority by OS user, secrets, path, API and immutable artifact identity.
8. **P1 Test suites:** Add mutation/negative tests for tier spoofing, stale head, forged CI locator, wrong gate, missing phase evidence and repeated failure before granting streamlined routing.

## 10. Acceptance evidence and rollout

- Baseline (current V5): measure Lead time from task to green PR, number of review rounds, human relay prompts, unplanned failures, CI time, test regression count; do not claim speedups until observed.
- Canary 1: low-risk docs/UI task on a clean branch, no Pre-code/final review, exact-head CI and no protected-action bypass.
- Canary 2: medium shadow-only scanner feature with independent black-box check, injected failure, collected bug batch and successful retest; no exchange access.
- Canary 3: high-risk dummy order-denial rule including pre-review when needed, independent final, fail-closed negative-path tests, no live auth.
- Canary 4: scoped, non-order test deployment, health proof, forced rollback, GitHub evidence, no production service change.
- Activation: independent governance review, completed policy regression suite, human merge authorization, explicit manifest/bridge migration to fresh ref. Do not change the active main manifest to a shortcut without the matching tested controller enforcement.
- Target metrics after 5-10 comparable changes: fewer manual relays/reviews for LOW/MEDIUM with stable or improved deterministic CI correctness, no P0/P1 escaped risk faults and bounded recovery time. Metrics are goals, not unearned results.

## 11. Economic constraints

Use existing Plus, optional free-tier Hark Pro/Muse **test-only**, public GitHub Actions hosted runner, and the existing AWS server. No self-hosted new agent server, new cloud VM, paid model router, CodeDeploy cost assumptions, or polling daemon. GitHub Actions uses existing runner quota and pricing rules; do not launch workflows on a schedule merely to drive an AI loop. Never upload private client or exchange data into public issue artifacts.

**Review verdict for this document:** research is sufficient to choose a risk-tier and verification design; **implementation in Draft PR #339 is incomplete** until blockers are resolved. No statement in this document should be treated as a PASS for the candidate.

## 12. 2026-10-15 final user feedback: fast native reuse, human-only secrets, automatic closeout

**Decision update (design pending implementation):** The bulk of near-term work
is reproducing/building existing features from the **pinned NautilusTrader**
release, NOT inventing competing trading infrastructure. The trader's unique
innovation belongs in strategies, research, Shadow outcomes and tuning.

### Large-package native reuse fast lane
- Favor **one coherent large package** per official capability family, not many tiny
  PRs. Group by executable integration seam (data capture, data health,
  shadow/backtest, order lifecycle/risk and system operations), not by arbitrary
  file count. The goal is fast, high-quality official reuse, no new controller.
- One acceptance brief -> Codex continuous development with local fast tests
  (syntax, focused unit, smoke) -> **single full CI on the final published
  candidate SHA** -> **one strict independent end-to-end review and adverse-case
  validation** -> auto closeout if all gates prove PASS. Failed final CI requires
  a corrected candidate and rerun; never suppress a failed required check.
- Even mature Nautilus is not a proof of venue/adaptor compatibility. Confirm
  the exact frozen rc5 implementation, official API and version-specific
  integration contract. Risk-engine, order-outcome, idempotency, reconciliation,
  stale-data and unknown-submit tests are compulsory at package final check.
- The human may perform one **final manual real-product acceptance** after the
  automated stage; lack of a real-person intermediate review is not a blocker
  to test/shadow-only package delivery.

### Human-exclusive operations, no exceptions
- Human: creating, entering, provisioning, rotating, revoking or granting
  passwords, passwords managers, exchange API keys, any API tokens, SSH
  identities, AWS/GitHub credentials and IAM grants, wallet private keys or
  signing secrets. AI only supplies minimal scope/setup guidance and checks
  boolean success without receiving or exposing values.
- Agents and externally connected Hark Pro/Muse **must not** receive live
  credentials or gain broad production command authority. They can submit
  untrusted isolated testing observations only.

### GitHub closed loop and AWS fast deployment
- Remove **per-PR human Mark Ready and Merge approval** from the *future*
  accepted V5; ready and native GitHub auto-merge happen upon exact-head
  authenticated CI PASS, current branch rules, independent review where
  actually required, no unexpected scope/credential changes and no blockers.
  Fail-closed default. Auto-delete merged temporary branch when safe.
- One-time human account setup of GitHub branch protection/auto-merge and AWS
  scoped credentials may be needed; never automate credential issuance via AI.
- Development/test deployment: GitHub-native immutable artifact and commit SHA;
  restricted SSH/SSM deploy command under bounded service permissions into
  isolated **order-OFF Shadow**, health check, capture outcome, restore last
  good artifact automatically on failure. Don't SSH-root to an LLM or run CI
  directly on the live trading host.
- Production/runtime changes and exchange writes remain a separate authority
  surface; no agent can convert a code merge or passing CI into live orders.

### Critical outstanding engineering gates
1. Trustworthy non-self-reported package provenance and risk scope.
2. Genuine *successful* exact-head CI attestation, not merely a locator.
3. Independent final package verification including one real operational test
   suite on test/simulated environment; user acceptance before live release.
4. Update controller, validators and all activation rules before flipping auto
   Ready/Merge; prove gates with negative tests, especially forged PASS data.
5. Verify whether current AWS is Lightsail or EC2; design restricted deploy
   without additional server or paid services. Confirm resource headroom.
6. Use original governance's human gates for **this governance PR itself**
   until new auto-merge policy is activated.

Official sources reviewed for native reuse:
- https://nautilustrader.io/docs/latest/concepts/adapters/
- https://nautilustrader.io/docs/latest/concepts/execution/
- https://nautilustrader.io/docs/latest/concepts/live/
- https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/automatically-merging-a-pull-request

## 13. Two concurrent windows' lessons and durable network resilience (2026-10-15)

### A. New strategy/AWS window — `woshixiong/-`

Most successful pattern: direct on-host diagnosis -> focused edit -> reload
specific test/shadow service -> observe real market-data updates and shadow
ledger. The Mac/FinalShell/RDC middle hop slows work and monopolizes the
desktop. Current evidence confirms market-data and shadow `orders.jsonl` /
`exits.jsonl` can be read, but **does not** prove every one of 71 strategy
identities has an independently valid live shadow record. Observed blockers
include GitHub/AWS source drift, version mapping, duplicate/ambiguous paper
order attribution, BBO/L2/timestamp integrity and data persistence.
The user limited AWS to public live capture + study/shadow paper orders and
explicitly rejected premature statistics/export. As of the consulted window
record, its source fixes and AWS redeployment were **not verified done**.

Borrow: fast scoped deployment + real output inspection + one consolidated bug
batch + SHA comparison against GitHub; prove `version_id`, `order_id`,
`entry/exit` causal alignment and data completeness before claiming success.
Avoid taking an external Agent's self-reported deployment/test result as proof.

### B. Nautilus foundation window — `woshixiong/trader-assist-v0`

Issue #338 groups **A native public capture without mandatory warmup, B
Catalog/data health, C native shadow lifecycle, D execution/risk/account
wiring with no private execution** in one coherent package. This is the right
large-package development style. The current local implementation reportedly
had a Draft PR and local 102 PASS/22 SKIP, while native CI surfaced a
`ParquetDataCatalog` directory-initialization failure. Local PASS was not the
same as exact-head Linux CI PASS, and final merge/deployment was not proved.
The older #329/#331 recorder work was merged on main; continuous production
capture after that merge was *not* verified deployed. Previous failed first
launch stemmed partly from project-added all-strategy historical warmup, queue
overflow and excessive qualification, not an intrinsic Nautilus requirement.

Borrow: native RC5 pinned APIs, one master feature bundle with internal A/B/C/D
integration checks, GitHub-hosted CI as authoritative Linux proof, optional
history only for strategies that need it, one strict final integrated package
review, no separate tiny PR for every minor gate. Keep new base integration
independent of proprietary signal research, private wallets and live orders.

### Combined workflow adjustment

1. Each task has `task_id + immutable base/head + expected service scope +
   acceptance` stored in GitHub; read actual AWS deployed SHA/config and
   reconcile drift before any patch. Do not trust copied output.
2. Codex works continuously on a **large coherent package** with inexpensive
   focused local checks. No repeated pre-code/final reviews per submodule.
   Publish a single bounded candidate and run full exact-head Linux CI;
   batch noncritical corrections, then rerun necessary gates.
3. Only in isolated shadow/test mode, use an existing provider-native
   deploy mechanism with a one-time human-scoped credential setup; drive
   actual subscribed streams, catalog reopen, synthetic orders, versioned
   paper ledger and negative paths. Save immutable evidence and rollback
   identity to GitHub. No AI secrets or live-capital permission.
4. Real user/Hark Pro/Muse adversarial tests are supplemental **read-only
   findings**. Explicit human final use test happens after automatic
   behavioral proof, not every iteration. Release blocker is factual
   capability and data/ledger correctness, not ritual window switching.
5. Network disruptions: **10s x 20 fast recovery attempts** on only transient
   transport. After that use a durable 5-15min jittered GitHub/native
   systemd recovery timer that keeps trying until restored/cancelled, with a
   finite budget per invocation. Prefer provider auto reconnect/resubscribe,
   resume from GitHub run/commit/deploy checkpoint, avoid manual intervention.
   Prevent compounded retries, CI runner cost storms, quota storms and
   duplicated service/Git/exchange writes. Never attempt token or permission
   repairs through AI. If no durable timer exists, call the state
   `PAUSED_TRANSPORT_AUTO_RESUME_NOT_CONFIGURED`, never falsely report
   automatic recovery.

### Expected acceptance
- One disconnected Mac does not break an already-running GitHub-hosted CI.
- A retryable GitHub read recovers; a successfully completed GitHub write is
  not repeated after lost acknowledgment.
- A failed network step does not rerun prior passing expensive native CI.
- A shadow deployment whose SSH acknowledgment was lost reconciles the
  installed SHA before any retry. Unknown outcome cannot restart live services.
- Temporary disconnection produces an observable checkpoint; persistent
  connectivity resumption continues only unfinished steps through the tested
  native timer/scheduler, with no additional paid service.
- Auth denied, resource OOM, code test failures, real-account/order failures
  do not trigger transport retries.
- Final users can distinguish GH code SHA, AWS deployed SHA, collector gaps
  and shadow order identity/causal correctness; none inferred from PR green.
  
Primary retry sources:
- https://docs.aws.amazon.com/wellarchitected/latest/framework/rel_mitigate_interaction_failure_limit_retries.html
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/re-run-workflows-and-jobs?tool=cli
- https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/retry-backoff.html

**Not implemented solely by this governance-document change:** persistent
retry/timer, credentialless native deploy command, verified tier attestation,
exact CI result predicate, medium phase evidence, automatic merge. Keep
candidate Draft until all safety and functionality tests pass.
