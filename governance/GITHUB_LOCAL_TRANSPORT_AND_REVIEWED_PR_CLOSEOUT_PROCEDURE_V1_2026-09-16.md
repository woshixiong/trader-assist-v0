# Trader Assist / Trade OS — GitHub Local Transport and Reviewed-PR Closeout Procedure V1

**Status:** TASK-CONDITIONAL PROCEDURE CANDIDATE  
**Effective date:** 2026-09-16  
**Normative owner:** `ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md`

This procedure operationalizes two already-established project-wide invariants for GitHub publication work.

**Applicability boundary:** local GitHub transport health is a publication/source-acquisition concern, not a universal semantic-Writer-start prerequisite. `SEMANTIC_READINESS` and `PUBLICATION_READINESS` are separate derived states.

1. project-generated local Git commands must use the simplest mature/provider-native reliable transport compatible with the current environment; and
2. independently reviewed Pull Requests must reach an explicit terminal disposition rather than remain indefinitely open or draft.

It is subordinate to V4. It does not create Mark Ready, merge, deployment/runtime/cloud, credential/private-API outside the bounded GitHub authentication route, wallet/signing, exchange-write, Testnet/Mainnet, real-capital or autonomous-trading authority.

---

## 1. Local Git transport for this project

The accepted default for user-local Git operations against `woshixiong/trader-assist-v0` is:

```text
LOCAL_PROJECT_GIT_TRANSPORT=https
AUTH_SURFACE=GitHub CLI browser OAuth
CREDENTIAL_HELPER=gh auth setup-git --hostname github.com
SYSTEM_CREDENTIAL_STORE_REQUIRED=YES
PLAINTEXT_FALLBACK_ALLOWED=NO
MANUAL_PAT_IN_SCRIPTS=NO
GLOBAL_URL_REWRITE_REQUIRED=NO
PROJECT_REMOTE=https://github.com/woshixiong/trader-assist-v0.git
FUTURE_GENERATED_PROJECT_LOCAL_GIT_COMMANDS_USE_HTTPS=YES
SSH_OVER_443_FOR_USER_LOCAL_GIT=DEPRECATED
```

Rationale: repeated project-local SSH-over-443 commands were disrupted by the user's proxy/TUN path, while provider-native HTTPS + GitHub CLI browser OAuth + macOS secure credential storage was independently reviewed and successfully activated. Do not reintroduce SSH-over-443 as the default merely because an older launcher used it.

The default route is a preferred route, not proof that the current local network path is healthy. A prior successful `git ls-remote`, authentication check, or publication on another day does not prove the later mutation path is currently reliable.

### 1.1 Credential handling

Generated project commands must not embed GitHub passwords, PATs, OAuth tokens or other credentials in scripts, logs, Issue comments or committed files.

```text
--insecure-storage = PROHIBITED
PLAINTEXT_GITHUB_TOKEN_FALLBACK = FAIL_CLOSED
GH_TOKEN / GITHUB_TOKEN ENVIRONMENT OVERRIDE = EXPLICITLY CLASSIFY BEFORE USE
```

When `gh auth login --git-protocol https --web` is required, normal browser OAuth is the preferred route. `gh auth setup-git --hostname github.com` is the preferred Git credential-helper integration.

A material expansion of GitHub credential scopes remains a separate authority/change decision. Do not silently add `workflow`, repo-wide administration or other scopes merely to bypass a rejected operation; first determine whether the existing GitHub connector/provider-native path already has the required bounded permission.

### 1.2 Generated-command routing

For this repository, future user-local `git fetch`, `git pull`, `git push`, `git ls-remote` and equivalent generated commands should use the HTTPS project remote by default.

Before a command mutates a branch/ref, still apply the normal exact-state safeguards:

```text
FRESH_REMOTE_IDENTITY=REQUIRED
EXPECTED_HEAD_OR_LEASE=REQUIRED_WHEN_HISTORY_OR_REF_SAFETY_DEPENDS_ON_IT
FORCE_WITH_LEASE_ONLY_WHEN_SEPARATELY_AUTHORIZED_AND_NARROWLY_REQUIRED
NO_FORCE_AS_NORMAL_PUBLICATION_ROUTE
```

Transport reliability never weakens branch/ref/merge authority rules.

### 1.3 Mandatory applicability and transport-health gate

Any bounded task that will generate or execute user-local Git publication for this repository must load this procedure before the **publication command** is delivered.

Do not move this gate in front of semantic work merely because one wrapper combines semantic execution and publication. Before semantic start classify:

```text
SEMANTIC_SOURCE_ACQUISITION_REQUIRES_LOCAL_GITHUB_TRANSPORT=YES|NO
PUBLICATION_REQUIRES_LOCAL_GITHUB_TRANSPORT=YES|NO
```

If the semantic source is already exact/available and the first value is `NO`, local GitHub auth/API/push health must not block the semantic Writer. Publication may remain `NOT_READY` until after the semantic checkpoint.

For a public repository, unauthenticated exact source acquisition or an already-verified exact local/artifact source should be preferred over introducing authenticated `gh` as a semantic-start dependency when they provide equal identity fidelity. This is independent of the general Generated Command gate.

Record at minimum:

```text
LOCAL_GIT_TRANSPORT_APPLICABLE=YES|NO
LOCAL_GIT_TRANSPORT_PROCEDURE_LOADED=YES|NO|NOT_APPLICABLE
LOCAL_GIT_TRANSPORT_GATE=PASS|FAIL|NOT_APPLICABLE
LOCAL_TRANSPORT_HEALTH_PREFLIGHT=PASS|FAIL|NOT_APPLICABLE
KNOWN_TRANSPORT_INCIDENT_NONREGRESSION=PASS|FAIL|NOT_APPLICABLE
AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED=YES|NO|NOT_APPLICABLE
```

For an applicable user-local publication command, `LOCAL_GIT_TRANSPORT_GATE=PASS` is a derived state, not an independently asserted label:

```text
USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_GIT_TRANSPORT_PROCEDURE_LOADED = YES
AND LOCAL_TRANSPORT_HEALTH_PREFLIGHT = PASS
AND KNOWN_TRANSPORT_INCIDENT_NONREGRESSION = PASS
AND AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED = YES
=> LOCAL_GIT_TRANSPORT_GATE=PASS

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_TRANSPORT_HEALTH_PREFLIGHT != PASS
=> LOCAL_GIT_TRANSPORT_GATE=FAIL

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED != YES
=> LOCAL_GIT_TRANSPORT_GATE=FAIL

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND KNOWN_TRANSPORT_INCIDENT_NONREGRESSION != PASS
=> LOCAL_GIT_TRANSPORT_GATE=FAIL

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_GIT_TRANSPORT_PROCEDURE_LOADED != YES
=> LOCAL_GIT_TRANSPORT_GATE=FAIL
```

`AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED=YES` means the routing check has been resolved; it does not mean an authoritative remote write surface necessarily exists. If an equal-or-higher-fidelity authoritative remote publication surface is available, apply V4's remote-execution preference before selecting another user-local publication attempt. If the local path is already proven unhealthy, the local gate cannot PASS merely because HTTPS remains the project default.

Hard enforcement:

```text
USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_GIT_TRANSPORT_PROCEDURE_LOADED != YES
=> COMMAND_DELIVERY=PROHIBITED

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_GIT_TRANSPORT_GATE != PASS
=> COMMAND_DELIVERY=PROHIBITED

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND LOCAL_TRANSPORT_HEALTH_PREFLIGHT != PASS
=> COMMAND_DELIVERY=PROHIBITED

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND AUTHORITATIVE_REMOTE_PUBLICATION_SURFACE_CHECKED != YES
=> COMMAND_DELIVERY=PROHIBITED

USER_LOCAL_GIT_PUBLICATION_COMMAND
AND KNOWN_TRANSPORT_INCIDENT_NONREGRESSION != PASS
=> COMMAND_DELIVERY=PROHIBITED
```

A local transport-health check must protect a real publication invariant. Do not create repeated speculative network probes merely to earn `PASS`; fresh provider/control-plane identity and an already-proven unhealthy local path are routing evidence. A provider-native connector identity check must not be redundantly re-proved through lower-reliability local `gh api` before semantic start unless the local result protects a distinct source invariant. When an authoritative connected GitHub surface can perform the same bounded mutation at equal or higher fidelity with less human relay, apply the V4 remote-execution preference before requiring another local publication attempt.

### 1.4 Checkpoint-aware fallback ladder

After a semantic Writer/action has completed, publication transport failure is an evidence/publication-tail failure unless evidence proves the semantic checkpoint itself is corrupt. Never consume another semantic Writer attempt merely to recover transport.

Use this ladder:

```text
SEMANTIC_CHECKPOINT_NOT_YET_COMPLETE
-> use accepted HTTPS + GitHub CLI route when LOCAL_GIT_TRANSPORT_GATE=PASS
-> otherwise select an authoritative safe publication surface before semantic mutation when practical

SEMANTIC_CHECKPOINT_ALREADY_COMPLETE
AND LOCAL_GITHUB_TLS_OR_API_PATH_PROVEN_UNRELIABLE
AND AUTHORITATIVE_GITHUB_CONNECTOR_WRITE_SURFACE_AVAILABLE
-> RERUN_SEMANTIC_ACTION=NO
-> LOOP_LOCAL_TRANSPORT_RETRIES=NO
-> PRESERVE_EXACT_HEAD_TREE_SCOPE_AND_HASH_EVIDENCE=YES
-> OFFLINE_EXACT_ARTIFACT_EGRESS_WHEN_SOURCE_BYTES_ARE_LOCAL_ONLY
-> CONNECTOR_PROVIDER_NATIVE_PUBLICATION
-> VERIFY_TERMINAL_REMOTE_TREE_OR_EXACT_ARTIFACT

AUTHORITATIVE_REMOTE_WRITE_SURFACE_UNAVAILABLE
-> preserve checkpoint
-> SAFE_STOP_AT_TRANSPORT_CAPABILITY_BOUNDARY
-> do not weaken credentials, force semantics, or semantic identity merely to publish
```

The 2026-09-17 R3 incident is a permanent nonregression case: local Git HTTPS failed with LibreSSL `SSL_ERROR_SYSCALL`, and authenticated `gh api` later failed with EOF after earlier read success. That pattern is classified as `LOCAL_GIT_HTTPS_LIBRESSL_OR_API_EOF_AFTER_PRIOR_SUCCESS`; it proves that earlier connectivity/authentication success alone is not a later mutation-path health proof.

---

## 2. Reviewed Pull Request terminal-disposition discipline

V4 already requires explicit bounded-task disposition and separate user Mark Ready / merge authority. For GitHub Pull Requests, operationalize that invariant as:

```text
INDEPENDENT_REVIEW_COMPLETED
=> PR_TERMINAL_DISPOSITION_REQUIRED
```

An independently reviewed PR must not remain indefinitely `OPEN` or `DRAFT` with no explicit next disposition.

### 2.1 PASS / accepted candidate

If final independent review returns PASS and the candidate remains accepted:

```text
FINAL_REVIEW=PASS
AND CANDIDATE_ACCEPTED=YES
-> obtain current explicit user Mark Ready authority
-> Mark Ready if still draft
-> obtain current explicit user merge authority
-> merge using exact-head / drift protection
-> verify live main contains the accepted candidate
-> record merged SHA / terminal status in the controlling Issue or PR
-> close or advance the linked task
```

Mark Ready and merge remain distinct retained user gates unless the user's current instruction explicitly authorizes both together.

A technical PASS alone is not merge authority.

### 2.2 REPLAN / REJECT / SUPERSEDED candidate

If the reviewed candidate is not accepted:

```text
FINAL_REVIEW=REPLAN|REJECT|SUPERSEDED
-> DO_NOT_MERGE
-> explicitly close the PR or mark/document it as superseded
-> record reason and replacement authority/PR when applicable
```

The clean-closeout invariant does **not** mean every reviewed PR must be merged. It means every reviewed PR receives an explicit terminal disposition.

### 2.3 Prohibited dangling state

```text
DANGLING_REVIEWED_PR_WITHOUT_TERMINAL_DISPOSITION=PROHIBITED
REVIEW_PASS_BUT_MERGE_AUTHORITY_PENDING=EXPLICIT_WAITING_ON_USER_AUTHORITY
REVIEW_REPLAN_WITH_REPLACEMENT_IN_PROGRESS=EXPLICIT_SUPERSEDED_OR_REPLAN_STATE
```

If a user-retained authority gate is the only blocker, record that exact blocker; do not silently treat the task as finished.

---

## 3. Post-merge verification

After an authorized merge, verify at minimum:

```text
PR_STATE=CLOSED
PR_MERGED=YES
MERGE_COMMIT_SHA=
LIVE_MAIN_SHA=
LIVE_MAIN_CONTAINS_ACCEPTED_HEAD_OR_TREE=YES
POST_MERGE_REQUIRED_CI_OR_STATUS=PASS|NOT_APPLICABLE
LINKED_TASK_TERMINAL_STATE=
```

If the merge races with another actor, fresh-check before taking any duplicate mutation. Never repeat Mark Ready/merge merely because the control window did not perform the first mutation itself.

---

## 4. Scope and precedence

This procedure applies to:

- user-local Git transport for this repository;
- generated local Git commands;
- GitHub PR publication/closeout after independent review;
- post-merge verification and linked-task closure.

It does not replace:

- V4 project-wide engineering governance;
- Generated Command reliability requirements;
- Tool onboarding/change acceptance for material auth/tool changes;
- task-specific Product / Strategy / Operations / Security authority;
- any retained user authority gate.

When this procedure conflicts with V4 or a stricter current authority, the stricter/higher-precedence authority governs.

---

## 5. Canonical provenance

This procedure canonizes the accepted records from Issue #163 and the post-E4 closeout request in Issue #178:

```text
HTTPS_ROUTE_CANDIDATE=#163 comment 5690751841
HTTPS_PRE_ACTIVATION_HANDOFF=#163 comment 5690754272
HTTPS_INDEPENDENT_REVIEW=PASS
HTTPS_ACTIVATION_RECEIPT=#163 comment 5690829185
POST_E4_CLOSEOUT_TRACKER=Issue #178
R3_TRANSPORT_ENFORCEMENT_ROOT_CAUSE=#163 comment 5712157994
R3_TRANSPORT_AMENDMENT_RECOMMENDATION=#163 comment 5712215961
```

Historical incident details remain in the relevant Issue comments; this file keeps only the durable operational rule.
