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

### Manifest-selected V6 Pilot — enforceable admission

USER_ROUTINE_OVERRIDE=EXPLICIT_SCOPED_GITHUB_RECORD
NO_SILENT_EXECUTOR_OR_SESSION_SWITCH=YES
TWO_FAILED_SEMANTIC_REMEDIES=>STOP_USER_PLUS_ORDINARY_CHATGPT
MATURE_FRAMEWORK_FIRST=HARD_GATE
OFFICIAL_SOURCE_BEFORE_CUSTOM_ADAPTER=HARD_GATE
ROOT_CAUSE_BEFORE_PATCH=HARD_GATE
END_TO_END_FUNCTIONAL_ACCEPTANCE=HARD_GATE

- Resolve the active constitution from the **current ref's manifest**; this file
  does not activate governance on another ref. Old V5 manuals are archives,
  never an alternate live authority when V6 is manifest-selected.
- Preserve exact GitHub object retrieval and smallest relevant evidence.
  `EXACT_COMMENT_LOCATOR_PRESENT=>READ_EXACT_COMMENT_ONLY`
  `FETCH_ALL_ISSUE_COMMENTS_WHEN_EXACT_COMMENT_KNOWN=PROHIBITED`
- Ordinary ChatGPT controls architecture, risk, acceptance and user dialogue.
  Choose exactly one Codex Cloud **or** CLI Writer route per approved real task;
  preserve its verified semantic session/worktree/PR and GitHub checkpoint.
  Unknown continuity => PAUSED_CAPABILITY, no silent new session/fallback.
- Prefer pinned mature Nautilus/native commodity services, official installed
  API/source and supported community solutions. Reproduce the shared root
  cause before edits. Two failed targeted semantic remedies on the same root
  => stop for **user + ordinary ChatGPT** technical direction.
- Use native GitHub CI, scope checks and whole-path positive/negative tests;
  no model-mediated CI polling or raw successful log dumps. No mandatory
  repetitive Pre-code/Final review on routine low-risk work; targeted fresh
  scrutiny remains for material governance/security/order/architecture.
- AWS access: direct Remote Desktop Commander on dedicated non-sudo
  `rdc-ops` (systemd `rdc-aws.service`, Journal read) for necessary
  bounded read-only observations. If protected files require access, Mac RDC
  -> FinalShell SSH is an optional online, scoped human-authorized fallback.
  Neither channel grants trading, service-control, sudo or merge authority.
- The user may explicitly override ordinary workflow stages, with a narrow
  GitHub decision record. Protected actions ALWAYS need explicit current
  human authorization. Never silently enlarge this exception.

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
