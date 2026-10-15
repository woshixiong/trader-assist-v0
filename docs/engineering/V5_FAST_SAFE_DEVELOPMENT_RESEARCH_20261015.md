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
