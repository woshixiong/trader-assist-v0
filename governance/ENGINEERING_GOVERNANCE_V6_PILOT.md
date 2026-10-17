# Trade OS — V6 PILOT Sole Engineering Constitution

**Effective only when the checked-out/current GitHub ref's**
`governance/ACTIVE_GOVERNANCE_MANIFEST.json` selects
`governance_version=V6`, `status=PILOT_ACTIVE` and this sole constitution.
V5 is retained as a historical archive, not concurrent policy. In the candidate
PR, this constitution is **NOT effective on main** until an explicitly authorized
exact-head reviewed merge. V6 is a named time-boxed operating PILOT; Cloud
capabilities are not qualified merely by governance activation.

## 1. Authority and context (hard gate)

GitHub is sole engineering truth. Every material engineering actor (ordinary
ChatGPT control, Codex Writer, Reviewer, Muse / other executor) first reads:
`AGENTS.md -> ACTIVE_GOVERNANCE_MANIFEST.json -> sole constitution ->
exact current Issue/PR/package checkpoint -> triggered narrow skill`.
`EXACT_COMMENT_LOCATOR_PRESENT=>READ_EXACT_COMMENT_ONLY`
`FETCH_ALL_ISSUE_COMMENTS_WHEN_EXACT_COMMENT_KNOWN=PROHIBITED`
`BROAD_ISSUE_OR_PR_HISTORY=>CONTROL_ESCALATION_ONLY`
`RAW_SUCCESS_LOG_INGESTION=PROHIBITED`
`MODEL_MEDIATED_CI_POLLING=PROHIBITED`

Load only current task files, not archived governance, prior chats, long backlog
or unrelated histories. Exact main/base/head/tree, actual executor and model,
scope, acceptance, current permissions, review evidence, checkpoint and CI
result must be recorded. A new window uses the exact checkpoint rather than
entire previous chat. Missing/contradictory authority => PAUSED_CAPABILITY.

## 2. Four hard engineering rules

**MATURE_FRAMEWORK_FIRST=HARD_GATE.** Commodity data acquisition, reconnect/
resubscribe, catalog/storage, health/recovery, generic Shadow/order lifecycle,
OMS, account/position/risk/execution and service management use pinned
supported NautilusTrader or proven existing/provider-native mature solutions
first. Only strategy semantics and edge are independent research. No new generic
controller, OMS, WebSocket client, scheduler or persistence engine while a
suitable mature capability exists.

**OFFICIAL_SOURCE_BEFORE_CUSTOM_ADAPTER=HARD_GATE.** On integration failure,
first inspect *installed pinned version*, official docs/source, reproducible
examples and relevant maintained community issues. Prove a concrete missing
contract before a **thin, bounded** custom adapter; a convincing claim without
evidence is not approval to reinvent native functionality.

**ROOT_CAUSE_BEFORE_PATCH=HARD_GATE.** Reproduce and classify shared failure,
identify system-layer owner, test falsifying hypotheses, then patch one root
cause. Do not defend a failing architecture with cascading small changes.
After **two failed targeted semantic fixes of one root cause**:
`TWO_FAILED_SEMANTIC_REMEDIES=>STOP_USER_PLUS_ORDINARY_CHATGPT`.
Codex and other executors stop editing. User + ordinary ChatGPT jointly
choose new technical direction before any third attempt. Stop earlier on
invalid premise, security concern, cross-module breakage or scope expansion.
Network/transport retries do not count as semantic fixes.

**END_TO_END_FUNCTIONAL_ACCEPTANCE=HARD_GATE.** Test full applicable flow:
data provenance -> persistence -> strategy -> shadow or native execution ->
immutable ledger -> host freshness/health, with negative/failure tests and
cost/safety checks. A systemd "active" flag is not data qualification; CI green
alone is not end-to-end functional proof. No false PASS or history rewrite.

Each implementation package records one short root-owner/native-capability
decision and exact positive/negative test evidence. CI enforces checkable
contracts; static prompts alone cannot guarantee every model obeys a rule.

## 3. Lean lifecycle and same-session writer

Human communicates through ordinary ChatGPT Engineering Control, which sets
one bounded package, exact scope, one Writer surface and acceptance. One chosen
Codex **Cloud or CLI** semantic session/worktree/task and one GitHub PR handle
implement -> cheap decisive local tests -> exact-head full GitHub CI ->
bounded *same-session* fix/CI until accepted or stopped. Do not silently
switch Cloud/CLI/Legacy, create a replacement Cloud task/PR, model-poll CI,
or load broad history to recover old context. Preserve exact PR/head, task
identifier, failure hypothesis, attempt counter and artifact links at
checkpoint. Use deterministic CI wait and official context compaction.
Unverifiable original session continuity => PAUSED_CAPABILITY/Engineering
Control + user decision, not silent re-run.

New Codex Cloud's complete same-session CI repair/ChatGPT trigger ability is
`UNVERIFIED_UNTIL_USER_SELECTED_REAL_TASK`; do not imply activation proves it.
Codex CLI local transient network retries: 10 seconds apart, at most 20, same
task/session and bounded safe transport (not semantic reruns). Never charge
model tokens to repetitive status checks. Cloud vs CLI is selected only per
user-authorized real task. No Legacy Cloud fallback.

Routine low-risk work has no mandatory iterative Pre-code/Final-review
ping-pong. Quality gates are exact-head CI, full changed-scope safety tests,
bounded functional acceptance and evidence. Material architecture, governance,
security/permission, wallet/order/real-capital changes require targeted fresh
independent scrutiny. No self-certification of reviewer identity.

## 4. Human authority / user override

`USER_ROUTINE_OVERRIDE=EXPLICIT_SCOPED_GITHUB_RECORD`.
The user has highest project decision authority over priorities, route,
models, ordinary review/approval steps, acceptance scope and exceptional
workflow paths. Express exceptions as a **current explicit** user decision
recorded in exact Issue/PR scope; never silently waive controls or grant
permanent blanket authority.

**PROTECTED_ACTIONS_REQUIRE_EXPLICIT_CURRENT_HUMAN_AUTHORITY=YES**:
Mark Ready, Merge, branch deletion, deployment, production/runtime/cloud
mutation, service start/restart/enable/reboot, credentials/private APIs/IAM/
SSH access, wallet/signing, exchange/order writes, autonomous trading and
real-capital actions. One current message may *conditionally* authorize both
Mark Ready and Merge after exact-head final evidence, but they remain distinct
actions; verify head/CI/no drift before either. No model, agent, package,
CI or prior broad grant silently bypasses these human gates.

## 5. GitHub/AWS/remote transport and failure handling

Use GitHub native issue/PR/check APIs for canonical state; CI and notifications
run without language-model polling. Exact protected mutation ambiguity =>
read back or fail closed; no blind retry. RDC has limited quota; require a
genuinely local-only action and bundle it, never query GitHub through RDC.

AWS Remote Desktop Commander is already installed as restricted, systemd
auto-start `rdc-aws.service`, `rdc-ops` no sudo with
`systemd-journal` read access and service memory cap 350MiB. Use direct AWS
RDC for necessary read-only health/log queries within filesystem rights.
Mac Remote Desktop Commander -> FinalShell SSH to AWS is the *backup* when
Mac online, with explicit current authorization for privileged operations.
Neither transport is a source of account, merge, service-control or exchange
authority. Do not access private strategy secrets via the AWS agent.

## 6. Pilot, cross-repo and rollback

Root AGENTS and manifest are dynamic, not version-stamped Project Instructions.
ChatGPT Project Settings require one-time user update; GitHub cannot mutate
existing UI instructions. Separate repositories (Muse private experiment) need
their own small AGENTS bridge and CI; they do NOT inherit main repo files
automatically. Unknown cross-repo visibility => fail closed. Existing frozen
packages do not silently inherit new routes; rebind when chosen.

V5 constitutional/controller/skill history remains immutable. V6 candidate
is tested on an isolated branch with exact-head CI, negative governance tests
and independent V5 Final Review. Only separately human-authorized single merge
can switch active main. A rollback is a new controlled reviewed and authorized
change; no silent force reset or mass cleanup.
