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

Additional RDC calls require a concrete technical necessity. On transport/network
failure, preserve the exact checkpoint and use the existing bounded retry/fallback
contract; never create an RDC retry storm.

### Frozen route and CI admission

Use the package-state and manifest-selected procedures for the authorized route:
A is deterministic/no-model; B is fresh ordinary ChatGPT High Writer; C is the
frozen primary Codex route with exact same-thread/worktree resume after Pre-code
PASS; D returns to Engineering Control. A matching executor string is not proof
of actual runtime identity. No in-flight cross-route, model or surface fallback:
Engineering Control must refreeze a material change first.

Use native GitHub checks and executed job-step evidence for exact-head CI.
Normal status polls use 60 seconds; classified transient read retries use
10 seconds/20 consecutive failures maximum, never fast-retry quota/auth/429.
Missing/skipped mandatory tests are not PASS. Do not launch a fresh Final
Independent Reviewer until all frozen required checks and genuine test steps
have been verified. The Reviewer's source of truth is canonical GitHub, not
routine Remote Desktop Commander reads.

macOS foreground Terminal/provider-session recovery remains a separate,
unqualified Packet 2; GitHub CI cannot certify local terminal visibility.

Every actor works to its safe authorized ability boundary. Routine continuation,
SHA/CI/log relay, and long review-result relay through the user are prohibited.

At every expected stop emit:

~~~text
DECISION=
CANONICAL_GITHUB_REF=
NEXT_DESTINATION=
NEXT_ACTION=
COPY_PASTE_COMMAND_OR_PROMPT=
~~~

## Protected actions

The manifest/constitution may never imply current authority for Mark Ready,
merge, branch deletion, deployment, production/runtime/cloud mutation, service
control, credential/private-API mutation, wallet/signing, exchange/order writes,
autonomous trading, or real-capital action. Each requires explicit current human
authorization.

Load the manifest-selected phase skill only when that phase actually applies.
