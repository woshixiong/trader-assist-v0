# Trader Assist / Trade OS — Agent Router

This is the repository bootstrap/router. It is not the engineering constitution.

## Resolve authority

GitHub is the canonical engineering control plane. Chat history, copied prompts,
remembered SHAs, old PR descriptions, and stale local state are not authority.

For material engineering work, resolve the exact checked-out/ref state in this order:

~~~text
AGENTS.md
-> governance/ACTIVE_GOVERNANCE_MANIFEST.json
-> manifest-selected sole project-wide constitution
-> exact current package-state / Issue / PR
-> governance/PROJECT_RULES_INDEX.md when navigation is needed
-> only the narrow subordinate procedure triggered by the task
~~~

The manifest on the exact ref decides which constitution and skills apply.
This router cannot activate a candidate governance version by itself.

## Bootstrap invariants

Before mutation, fresh-resolve repository, main/base/head/tree, task identity,
role, route, scope, authority boundary, acceptance criteria, execution surface,
and retained gates. Never silently change role, executor, model, reasoning,
surface, scope, acceptance, or authority.

Use progressive disclosure. Do not load broad governance history, old chats, or
unrelated backlog by default.

### Remote Desktop Commander quota discipline

Remote Desktop Commander (RDC) is a quota-limited local execution transport,
not a default observation or GitHub-control surface. Preserve automation first,
then minimize RDC calls. Never force routine human relay merely to save RDC
quota when a local-only automated action genuinely requires RDC.

Before every RDC call, all of the following must be true:

~~~text
RDC_NECESSITY_TEST:
LOCAL_ONLY_ACTION_OR_EVIDENCE_REQUIRED=YES
NO_CANONICAL_OR_NATIVE_LOWER_COST_EQUIVALENT=YES
CALL_ADVANCES_STATE_OR_RETURNS_DECISIVE_EVIDENCE=YES
RELATED_LOCAL_OPERATIONS_BUNDLED=YES
~~~

Use GitHub/native connectors, canonical GitHub state, deterministic
controller/waiter output, and direct project tools instead of RDC whenever they
can provide equivalent authority/evidence/action.

The following are prohibited as routine RDC use:

- GitHub Issue/PR/file/status/CI reads or writes that a GitHub-native surface can perform;
- CI/status polling or repeated "is it done" progress reads;
- redundant identity/status readback when the exact canonical binding has not changed;
- rereading files already available from GitHub or another native file surface;
- blind network/connectivity retry loops;
- repeated process-output reads merely because a process is still running.

Normal local stage target:

~~~text
RDC_START_OR_RESUME_CALLS_PER_LOCAL_STAGE<=1
RDC_ROUTINE_PROGRESS_READS=0
ONE_BOUNDED_RESULT_READ=ALLOWED_ONLY_FOR_CONCRETE_ABNORMAL_OR_INTERACTIVE_NEED
AUTOMATION_CONTINUITY_TAKES_PRIORITY_OVER_RDC_MINIMIZATION=YES
~~~

Additional RDC calls require a concrete technical necessity. On transport/network failure, preserve exact canonical checkpoint. For genuine
transient network outages, automatically retry 10 seconds apart, at most 20
times in one burst; a durable native GitHub/service timer may then retry every
5-15 minutes with jitter until restored/cancelled. No RDC polling storm, no
human relay, no semantic replay. Before any write retry, reconcile GitHub
ref/run or host operation identity; ambiguous side effects stop for readback.
Never retry secrets/auth/permission, semantic failures or exchange writes as
if they were transport interruptions. Continued operation needs an actual
persistent executor; chat sessions are not an always-on worker.

### Execution defaults — operational clarification only

These defaults clarify how to apply the existing V5 route and transport rules.
They do not add stages, change lifecycle/authority, or modify controller, CI,
review, repair, or protected-action behavior.

- Resolve the active constitution's LOW/MEDIUM/HIGH tier first. Route B uses an
  ordinary ChatGPT Writer; Route C uses the selected Codex execution surface.
  HIGH/governance requires independent review; LOW/MEDIUM use small CI-checked
  changes and milestone behavioral verification rather than blanket reviews.
  Until this amendment is activated on main, existing V5 gates remain binding.
- When Route C genuinely requires local execution, use RDC only to start or
  resume one visible foreground Terminal/Codex session. Do not use RDC for
  routine progress polling.
- On a clearly transient local Codex network interruption, wait 10 seconds and
  retry/resume the same task/session when available. This is a local Codex
  transport rule; it does not change CI polling or CI waiter behavior.
- When the local Mac cannot authoritatively represent the required test
  environment, do not repeatedly rebuild or repair the local environment for
  parity. Use the already-qualified GitHub CI or other existing authoritative
  environment.

Every actor works to its safe authorized ability boundary. Routine continuation,
SHA/CI/log relay, and long review-result relay through the user are prohibited.

At every human-required stop emit (machine-to-machine continuation uses canonical GitHub state):

~~~text
DECISION=
CANONICAL_GITHUB_REF=
NEXT_DESTINATION=
NEXT_ACTION=
COPY_PASTE_COMMAND_OR_PROMPT=
~~~

## Protected actions

On activation of this reviewed amendment only: routine Mark Ready, native
auto-Merge and safe merged-branch cleanup are machine-authorized **only** after
trusted exact-head CI, required independent review, provenance and branch
protection gates are verified. Missing evidence blocks. Isolated Shadow/test
deployment may use a previously human-configured *bounded* allowlist; it never
grants live deployment or trading authority.

Human only: all passwords, keys, tokens, SSH credentials, wallet material,
IAM/access grants, secret provisioning/rotation/revocation. Agents never read
or change these. Human authorization remains mandatory for real-capital/order
enabling and production changes outside the preauthorized test scope.
The active-main V5 rules still apply until this candidate is accepted and
activated; no proposal document grants current action authority.

Load the manifest-selected phase skill only when that phase actually applies.
