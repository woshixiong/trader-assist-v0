# Trader Assist / Trade OS — Codex Current Model Profile

**Status:** FROZEN V5 INTENDED ROUTING CANDIDATE  
**Runtime qualification:** NOT YET PROVEN  
**Execution target:** Codex CLI only

This profile records refreshable model/config intent for the V5 candidate. It
does not prove that the user's installed CLI exposes or correctly enforces any
model, reasoning, child-identity, approval, network, hook, or resume capability.

## Intended V5 routing

~~~text
PRIMARY PLAN + WRITER       gpt-6-sol / medium
REPAIR 1                    gpt-6-sol / medium
REPAIR 2 / HARD ROOT CAUSE  gpt-6-sol / high
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

## Static official-contract verification for V5-A

The repo config continues to reference the official Codex schema at:

https://developers.openai.com/codex/config-schema.json

Current official Codex configuration documentation confirms the fields used by
V5-A, including:

- model and model_reasoning_effort;
- sandbox_mode = workspace-write;
- approval_policy = on-request;
- approvals_reviewer = user | auto_review;
- agents.max_concurrent_threads_per_session, excluding the primary thread;
- sandbox_workspace_write.network_access.

Current OpenAI model documentation exposes the frozen model IDs gpt-6-sol,
gpt-6-luna, and gpt-6-astra and the required reasoning levels.

This verifies static syntax/contracts only. It is not local runtime
qualification.

## CLI-only target and permission posture

Future default V5 execution surface is Codex CLI, not Codex Desktop.

Candidate repo defaults are:

~~~text
sandbox_mode=workspace-write
approval_policy=on-request
approvals_reviewer=auto_review
web_search=disabled
workspace sandbox network_access=false
~~~

The network setting preserves a restrictive default sandbox. The approved
on-request path is expected to handle eligible GitHub lifecycle operations.
Before activation, the actual installed CLI must prove that this combination
can perform the frozen authorized lifecycle without human relay or protected
authority expansion.

Normal engineering must not require danger-full-access.

## Activation qualification still required

Before V5 activation, observe and record:

- installed Codex CLI version and exact supported config surface;
- gpt-6-sol availability and requested/actual reasoning identity;
- gpt-6-luna availability and optional child identity verification;
- gpt-6-astra availability only if an explicit Control escalation actually
  depends on it;
- thread/session resume capability;
- workspace-write behavior;
- on-request + auto_review behavior;
- authorized GitHub network lifecycle behavior;
- hook loading and protected-action nonregression;
- no silent fallback to GPT-5.6 or another unbound model.

If the primary GPT-6 route is unavailable or unverifiable, V5 activation fails
closed. Static config is never enough to claim PASS.

## First real canary telemetry

On the first accepted non-production V5 package, collect observable:

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
