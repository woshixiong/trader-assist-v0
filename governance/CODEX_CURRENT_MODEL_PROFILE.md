# Trader Assist / Trade OS — Codex Current Model Profile

**Status:** V5 ACTIVE
**Runtime qualification:** V5 BASELINE PASSED; GPT-6.1 Sol direct model-ID switch; no standalone requalification requested
**Execution target:** Codex CLI only

This profile records refreshable model/config intent and the current active V5
state. The activation merge, baseline CLI/permission/tooling qualification, and
first real non-production end-to-end V5 canary remain accepted historical V5
evidence. The primary Sol model ID was directly switched from GPT-6 Sol to
GPT-6.1 Sol by current human direction without a standalone requalification
exercise; ordinary per-launch requested/actual identity drift remains fail-closed.

## Current V5 routing

~~~text
PRIMARY PLAN + IMPLEMENT    gpt-6.1-sol / medium
REPAIR 1                    gpt-6.1-sol / medium
REPAIR 2 / HARD ROOT CAUSE  gpt-6.1-sol / high
OPTIONAL EXPLORER           gpt-6-luna / low
OPTIONAL INTERNAL REVIEW    gpt-6-luna / high
EXCEPTIONAL CONTROL ANALYSIS
                            gpt-6-astra / medium
                            explicit Engineering Control escalation only
PRE-CODE REVIEW             fresh ordinary ChatGPT / High
FINAL INDEPENDENT REVIEW    fresh ordinary ChatGPT / High
MECHANICAL / CI / STATUS    zero model
~~~

Default subagent count is zero. At most one optional child may run concurrently.
Recursive delegation is prohibited by default. An optional child is skipped
when actual spawned model/reasoning identity cannot be verified; there is no
silent parent/default fallback.

## Static official-contract verification

The repo config continues to reference the official Codex schema at:

https://developers.openai.com/codex/config-schema.json

Current official Codex configuration documentation confirms the fields used by
V5, including:

- model and model_reasoning_effort;
- sandbox_mode = workspace-write;
- approval_policy = on-request;
- approvals_reviewer = user | auto_review;
- agents.max_concurrent_threads_per_session, excluding the primary thread;
- sandbox_workspace_write.network_access.

Current OpenAI model documentation exposes the frozen model IDs gpt-6.1-sol,
gpt-6-luna, and gpt-6-astra and the required reasoning levels.

Static syntax/contracts are only one input. Baseline local runtime identity,
permission/auto-review/network behavior, protected-action nonregression, and the
first real non-production end-to-end package canary have all been qualified.

## CLI-only target and permission posture

The default V5 execution surface is Codex CLI, not Codex Desktop.

Current V5 repo defaults are:

~~~text
sandbox_mode=workspace-write
approval_policy=on-request
approvals_reviewer=auto_review
web_search=disabled
workspace sandbox network_access=false
~~~

The network setting preserves a restrictive default sandbox. Baseline V5
qualification proved the CLI/permission/network/hook/protected-action posture.
The earlier GPT-6 Sol route qualification is historical evidence; the current
GPT-6.1 Sol route was selected by direct human model-ID switch without a separate
qualification package. Normal launches still require requested/actual model and
reasoning identity to match or fail closed.

Normal engineering must not require danger-full-access.

## Active governance boundary

The manifest-selected post-merge route is fail-closed:

- PLAN and IMPLEMENT use gpt-6.1-sol / medium;
- Repair 1 uses gpt-6.1-sol / medium;
- Repair 2 / hard root cause uses gpt-6.1-sol / high;
- GPT-5.6 is not a V5 fallback;
- optional child routes remain optional and require verifiable actual identity;
- exceptional gpt-6-astra remains Engineering-Control-only.

The first real non-production V5 Development Package canary remains the accepted
lifecycle proof point, so the manifest remains `ACTIVE`. The Sol model ID is now
GPT-6.1 Sol; fail-closed identity/permission rules and protected-action boundaries
are unchanged.

## Accepted first real canary telemetry

The accepted first real non-production V5 package is the lifecycle proof point.
Retain observable telemetry, when exposed, for:

- primary model and reasoning identity;
- optional child identity or explicit skip reason;
- input/output/cached-token metrics when exposed;
- stable-prefix/cache reuse behavior;
- thread resume success;
- semantic Repair 1/Repair 2 usage;
- transport retries/readbacks;
- CI waiting model-token use, expected zero;
- human relay count, target zero for routine SHA/log/CI/review state;
- permission/auto-review interruptions;
- context compaction events where exposed.

Use these measurements to update this refreshable profile/backlog without
turning telemetry into a second constitution.
