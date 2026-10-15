---
name: trade-os-v5-development
description: Implement small risk-classified Trade OS changes with fast CI and phase-level verification; retain strict HIGH safety gates.
---

# Trade OS V5 Development

This is an adapter to the manifest-selected constitution, not a second policy.

~~~text
MODEL_EXECUTOR_STDIN_SOURCE=EXPLICIT
SHARED_OUTER_LAUNCHER_STDIN=PROHIBITED
~~~

1. Bind exact repo/issue/base/head, frozen feature and acceptance predicates. Engineering Control records verified LOW/MEDIUM/HIGH risk classification in the canonical packet; ambiguity defaults HIGH. Legacy untagged packages retain old strict V5 stages.
2. LOW: direct bounded implementation -> focused validation -> short Draft PR -> exact-head CI -> human protected closeout. No routine plan-only, Pre-code or Final Independent Review.
3. MEDIUM: ship several isolated short CI-checked changes; hold new trading/production behavior OFF. No per-slice Pre-code/Final Review. On an actual feature/milestone, run a real user scenario and independent adversarial scenario on disposable/offline/shadow hosts. Capture traces and deduplicate faults into a ranked defect batch, fix in small CI-checked commits, rerun focused and boundary regression.
4. HIGH or governance: fresh independent Final Review always; add one Pre-code Review only for changed/unknown safety-critical design. Preserve exact-head identity, negative-path tests, and current human gates. No real exchange writes or service mutations via test agents.
5. For Codex, preserve the primary thread/worktree whenever available. Only HIGH required Pre-code resumption fails closed on exact resume loss; LOW/MEDIUM can start an explicitly recorded replacement executor at the last canonical checkpoint without repeating completed work.
6. On failure, classify/reproduce first. LOW/MEDIUM within frozen scope can repair without user relay. New architecture/security/authority or real-capital risk returns to Control. Do not weaken guards to green CI.
7. If publishing `.github/workflows/**` through a local git transport, enforce current human-backed `GH_WORKFLOW_SCOPE_VERIFIED=YES` without silent OAuth refresh.
8. CI status waiting is deterministic, not a model or RDC polling loop.
