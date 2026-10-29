# FinalShell Target-Host Deployment Workflow V1

**Status:** SPECIALIZED CANONICAL OPERATIONS WORKFLOW  
**Effective date:** 2026-08-26  
**Repository:** `woshixiong/trader-assist-v0`  
**Authority:** subordinate to explicit current user authority, current Product/Strategy/Security/Operations authority, the active manifest, and `governance/ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md`.

## 1. Purpose

This document freezes the default user-operated target-host deployment transport for Trader Assist / Trade OS so future Engineering and Operations windows do not repeatedly redesign, re-ask, or silently substitute the deployment workflow.

The current normal operator path is:

```text
GITHUB_ACTIONS_LINUX_X86_64
  -> DOWNLOAD ONE EXACT-RELEASE TRANSPORT ARCHIVE
  -> FINALSHELL FILE MANAGER / SFTP UPLOAD
  -> ALREADY-CONNECTED FINALSHELL SERVER TERMINAL
  -> ONE CONTIGUOUS REMOTE EXECUTION BLOCK
  -> EVIDENCE / RESULT RETURN
```

FinalShell is the operator surface. It is not a new deployment authority, source of truth, runtime, orchestration framework, or replacement for GitHub/systemd/Registry/security controls.

## 2. Permanent workflow invariants

```text
DEFAULT_TARGET_HOST_OPERATOR_SURFACE=FINALSHELL
RELEASE_BUNDLE_BUILD_SURFACE=GITHUB_ACTIONS_LINUX_X86_64
OLD_INTEL_MAC_BUILD_DEPENDENCY=NO
TRANSFER_SURFACE=FINALSHELL_SFTP_OR_FILE_MANAGER
REMOTE_EXECUTION_SURFACE=ALREADY_CONNECTED_FINALSHELL_TERMINAL
MAC_DIRECT_SSH_REQUIRED=NO
ONE_EXACT_ARTIFACT_DOWNLOAD=DEFAULT
ONE_TRANSFER_ARCHIVE=DEFAULT
ONE_REMOTE_EXECUTION_BLOCK=DEFAULT
SILENT_DEPLOYMENT_TRANSPORT_SUBSTITUTION=NO
EXACT_40_CHAR_RELEASE_SHA_REQUIRED=YES
DEPLOYMENT_ARTIFACT_HASH_MANIFEST_REQUIRED=YES
SECRET_IN_DEPLOYMENT_BUNDLE=NO
USER_RETAINED_DEPLOY_RUNTIME_AUTHORITY=PRESERVED
```

These invariants apply whenever the user is operating the current Linux target host through FinalShell unless the user explicitly selects another operator surface or a real capability/safety constraint requires a visible route change.

## 3. Canonical authority and precedence

Before preparing any deployment package, the controlling Engineering/Operations role must fresh-check live GitHub and current narrow-domain authority.

This workflow is an active subordinate V4 procedure. In any conflict, the active V4 authority graph and current narrow-domain authority govern. Current deployment/runtime authorization remains a separate explicit user gate and is never inferred from this workflow.

At minimum verify:

1. live repository and exact `main` SHA;
2. exact release artifact/commit intended for deployment;
3. exact-head and/or post-merge CI required by the active release contract;
4. current Issue/Operations authority;
5. current deployment/runtime/cloud authorization;
6. any host-specific safety dependency such as required service preservation;
7. current rollback/default-off boundary.

No artifact, FinalShell session, old deployment folder, stale prompt, prior authorization, or server checkout overrides live GitHub authority.

FinalShell workflow selection never grants deployment, runtime, service start/restart/enable, reboot, credential/private API, wallet/signing, exchange-write, order-submission or trading authority. Those remain explicit current user-retained gates.

## 4. Phase A — GitHub exact-release artifact generation and download

Engineering/Operations should bind the reviewed full release SHA and tree, then
use the manual GitHub Actions Linux x86_64 / CPython 3.12 release-bundle builder.
The old Intel Mac is a download/transfer surface; native local generation is not
required. Release-specific inputs and download commands are in the accepted
Operations runbook. The workflow/control HEAD and historical product release
SHA are separate identities; a later control HEAD must not move the release.

The builder must fail closed on release/tree, locked dependency, launch identity,
manifest/hash or secret mismatch. It emits one non-secret tar.gz with the exact
bundle, manifest and five handoff anchors. Record the exact run ID/attempt,
artifact name, control HEAD and independently reviewed anchors. Public metadata
observation times can change between builds; each run has its own hash binding.
Artifact PASS grants no deployment/runtime/service authority.

Download that exact run's artifact once, without rebuilding or editing it.
GitHub's outer artifact does not preserve filesystem executable modes; the inner
tar payload preserves `remote-qualification.sh` mode `0750`. Keep the archive
intact through transfer. Handoff metadata stays outside the manifest-bound bundle
and does not become independent authority by travelling in the same archive.

The user should not have to assemble payloads, edit generated scripts, install a
native build environment, configure a new macOS SSH route or reconstruct the
release from chat text.

### Package safety

The deployment folder must not contain:

- passwords;
- private SSH keys;
- notification webhook secrets;
- API keys/tokens;
- wallet/signing material;
- production database contents unless a separately authorized recovery workflow explicitly requires them;
- unbounded logs/caches;
- unrelated local configuration.

Existing secure server-side credentials remain server-side unless a separately authorized credential operation explicitly requires another route.

## 5. Phase B — FinalShell transfer

After exact GitHub artifact download, the normal irreducible human transfer step is:

1. open the already configured target host in FinalShell;
2. use FinalShell file manager/SFTP transfer;
3. upload the single unchanged transport archive to the exact temporary destination specified by Engineering/Operations;
4. do not rename, edit, partially copy, unzip/rebuild, or mix files with an older deployment folder unless the generated instructions explicitly require it.

The preferred remote staging location is a unique temporary path such as:

```text
/tmp/trade-os-deploy-<task-or-release-id>-<sha-prefix>/
```

The exact generated package controls the real path for each run.

The transfer step is transport only. Upload success is not deployment acceptance.

## 6. Phase C — already-connected FinalShell server execution

After upload, Engineering/Operations should provide one contiguous block for the **already-connected FinalShell server Terminal**.

Do not ask the user to establish another SSH connection from macOS when the FinalShell server session already provides the required shell access.

The remote block should perform, where applicable:

- remote staging-path preflight;
- safe archive path/type verification and extraction into a new staging directory;
- executable mode `0750` and independent manifest/script hash verification before running uploaded code;
- package/manifest/hash verification before mutation;
- exact release SHA verification;
- host identity/state verification;
- disk/resource prerequisite checks;
- required protected-service checks;
- current source/config/Registry/durable-state capture before mutation;
- deployment only within the currently authorized mutation boundary;
- validate-only/config/import/systemd checks before any runtime activation;
- bounded qualification when separately authorized;
- fail-closed cleanup/restore behavior;
- default-off restoration where required;
- final source/config/service/Registry identity checks;
- evidence packaging and concise terminal result.

For multi-step remote scripts, contain failures so a script exit does not unnecessarily terminate the parent FinalShell session.

## 7. Exact-release and anti-drift requirements

Production deployment must use an explicitly authorized full 40-character commit SHA or another exact artifact identity permitted by the active release contract.

Prohibited deployment identities include:

- floating `main` without resolving/fixing the exact SHA;
- mutable branch names as the only release identity;
- abbreviated commit SHA;
- unverified local folder state;
- a prior deployment folder assumed to still match current GitHub;
- a manually reconstructed payload with no hash proof.

Where a deployment package is transferred instead of cloning directly on the host, the remote execution must independently verify the transferred artifact hashes before installation.

## 8. FinalShell is a replaceable operator surface

This project does not depend architecturally on FinalShell-specific proprietary semantics.

The stable contract is:

```text
VERIFIED LOCAL ARTIFACT
-> SECURE FILE TRANSFER OVER THE EXISTING SSH/SFTP HOST ACCESS
-> VERIFIED REMOTE SHELL EXECUTION
```

FinalShell is the user's current default client implementing that contract.

If FinalShell becomes unavailable or objectively unsuitable, Engineering/Operations may propose an equivalent mature SSH/SFTP client or provider-native transfer path. The change must be visible and must preserve the same exact-artifact, hash, authority, secret-handling, remote-execution and evidence boundaries.

No silent substitution is allowed. Do not introduce Terraform, Ansible, a custom deployment service, a persistent agent, or another deployment framework merely because an individual deployment is inconvenient.

## 9. User interaction budget

The normal workflow should require only these operator interactions:

```text
1. GENERATE / DOWNLOAD ONE EXACT GITHUB ARTIFACT
2. UPLOAD ONE UNCHANGED ARCHIVE THROUGH FINALSHELL
3. PASTE ONE REMOTE BLOCK INTO THE ALREADY-CONNECTED FINALSHELL TERMINAL
4. RETURN THE RESULT/EVIDENCE WHEN THE CONTROL WINDOW CANNOT ACCESS IT DIRECTLY
```

Do not split the workflow into many small copy/paste fragments when one bounded block can safely perform the same work.

If an unavoidable password/MFA/GUI confirmation/secret-manager step exists, surface only that irreducible action and continue task ownership afterward.

## 10. Operations handoff and evidence

Engineering owns release correctness through the release/merge/post-merge gates defined by the active task. Operations owns the target-host deployment/qualification stage after an explicit acknowledged handoff and current authority.

The handoff must include, as applicable:

- exact release SHA;
- CI identity/result;
- release-specific deployment constraints;
- expected host/default-off state;
- protected dependencies/services;
- exact qualification scope;
- retained authority gates;
- rollback/safe-stop conditions.

The remote run must return enough evidence for Operations Control to adjudicate the host result without making the user manually interpret raw logs.

Writer/operator self-reported PASS is not independent acceptance when the active task requires a separate Reviewer.

## 11. Safety and stop conditions

Immediately stop the specific deployment/qualification action on any material mismatch including:

- live release drift;
- package/hash mismatch;
- wrong host or unexpected host state;
- unexpected meaningful production durable data;
- protected service state/PID drift where preservation is required;
- missing rollback/default-off prerequisite;
- credential exposure;
- new runtime/architecture/provider blocker;
- cleanup/restore failure;
- authority needed beyond the current user grant.

Stopping a blocked action does not release active task ownership. Complete all safe evidence/restore work and return the minimum irreducible blocker to the responsible control role.

## 12. Relationship to existing runbooks

This file fixes the **operator transport/workflow contract**. It does not duplicate release-specific server commands.

Release-specific deployment mechanics remain in the current accepted Operations runbook, including where applicable:

- `docs/operations/V0_FL_R3_P4A_LOCAL_DEPLOYMENT.md`;
- current Issue #93 Operations authority;
- current release/task packet.

If a release-specific runbook shows direct host Git clone/fetch commands while the active workflow uses a transferred exact artifact folder, Engineering/Operations must preserve the runbook's exact-SHA/import/config/systemd/security invariants while adapting only the transport seam. Do not treat the historical clone example as a requirement to expose persistent GitHub credentials on the target host.

## 13. External mature-solution confirmation

This workflow uses mature standard capabilities rather than custom deployment infrastructure.

AWS Lightsail official documentation confirms that Linux/Unix instances support secure file transfer using SFTP and that documented SFTP-client steps can apply to other clients. AWS also documents administration through a user's own SSH client.

Primary references:

- `https://docs.aws.amazon.com/lightsail/latest/userguide/amazon-lightsail-connecting-to-linux-unix-instance-using-sftp.html`
- `https://docs.aws.amazon.com/lightsail/latest/userguide/lightsail-how-to-connect-to-your-instance-virtual-private-server.html`

The evidence confirms the project's selected route: use standard SSH/SFTP transport through the user's existing FinalShell client, with project-specific exact-release validation and safety logic remaining in thin scripts/runbooks.


## 14. Mac RDC + FinalShell: user-keyboard focus isolation (2026-10-29 field addendum)

**Authority and precedence.** This section records an operational usability requirement, not permission to operate a server. The **current** \`AGENTS.md\` -> \`ACTIVE_GOVERNANCE_MANIFEST.json\` -> manifest-selected constitution and the exact task's human authorization always supersede this historical workflow's V4 references. For AWS operations, prefer the user-selected ChatGPT Chrome extension controlling **AWS official browser SSH** where that interaction capability is actually available. The already-connected **Mac RDC -> FinalShell SSH** path is the user-approved fallback only; do not silently substitute another host, browser, remote shell or access route.

### 14.1 Required non-interference contract

\`\`\`text
USER_CONTINUES_WORK_IN_OTHER_WINDOWS=SUPPORTED
STEAL_USER_KEYBOARD_FOCUS_WHILE_USER_TYPES_OR_DICTATES=PROHIBITED
INTERACT_WITH_UNRELATED_WINDOWS_OR_READ_THEIR_CONTENTS=PROHIBITED
FULLY_BACKGROUND_FINALSHELL_EXECUTION=NOT_YET_VERIFIED
CLAIM_ZERO_FOCUS_WHEN_ACTIVATE_OR_GLOBAL_KEYSTROKES_USED=PROHIBITED
WRONG_WINDOW_OR_UNVERIFIED_SHELL_INPUT=FAIL_CLOSED
ONE_BOUNDED_REMOTE_BLOCK_WITH_IDENTITY_AND_OUTPUT_EVIDENCE=PREFERRED
\`\`\`

When the user is working in other Mac windows, a purported "background" mechanism must be tested **end to end**, not inferred from successful remote connectivity or the ability to populate an input field. A valid zero-focus path must demonstrably (a) leave the user's active app and keyboard focus unchanged, (b) deliver a harmless sentinel command to the **existing** intended FinalShell session and receive its exact server output, (c) not consume the user's live keyboard, speech input or clipboard, and (d) be scoped to the exact host and operator permissions. **Do not send production edits or service restarts unless that path passes the sentinel test.**

### 14.2 What was actually verified on 2026-10-29

- The Mac RDC agent could address the existing FinalShell application and read FinalShell-only GUI evidence. The safe capture was by its own macOS window ID: \`screencapture -x -l <FinalShell-window-id>\`, rather than a full-desktop capture that might include unrelated work.
- FinalShell's accessibility command input accepted text through its \`AXSelectedText\` attribute **without requiring the app to become frontmost**. But the subsequent attempts to submit the command entirely in the background were **not reliable** (including an attempted accessibility-button press and per-process keyboard events). **Typing into that field is not proof of an executable, zero-focus terminal route.**
- The **successfully verified execution path** was a bounded Mac-side AppleScript operation: save the existing clipboard; set the clipboard to one already-reviewed shell command; activate the existing FinalShell app; click its terminal area; clear any pending line with Ctrl+C; paste with Cmd+V; press Return; restore the original clipboard, including on errors; and read **only the FinalShell window** for a returned sentinel and final result. In the Tokyo Freqtrade canary this path successfully ran preflight, SQLite online backup, an exact one-key configuration modification, one Dry-run restart, and native 14-pair freshness checks. Canonical evidence: \`https://github.com/woshixiong/fraqtrade/issues/3#issuecomment-6490288976\`.
- **Important limitation:** \`activate\` and the terminal click **briefly take the foreground focus**. This method is low-interaction but **not** genuinely "non-focus-stealing." The canary also showed that concurrent voice dictation or typing can leak text into the FinalShell terminal. Therefore it must **not** be called automatically while the user is actively using other Mac windows, even if the focus switch lasts only a moment.

### 14.3 Future default and safe fallback

1. **First choose a genuinely focus-independent FinalShell mechanism** only after an observed positive sentinel and negative focus-interference test, using the same mature FinalShell/macOS facilities and the existing SSH connection. Treat unverified UI automation or guessed background key submission as a blocker, not a successful execution.
2. If the exact FinalShell version cannot execute commands without stealing foreground focus, record \`FOCUS_FREE_BLOCKED\`; do not repeatedly activate the app, hijack the user's input or inspect unrelated windows. A short foreground paste remains a separately visible **user-coordinated exception**, allowed only when the user explicitly permits a brief exclusive focus window and a sentinel test passes.
3. For any authorized remote change, bind the exact host and Dry-run/runtime status before mutation, take safe non-secret backups, check an official native config parser, apply only the scoped difference, preserve a bounded rollback and verify the entire requested data/order/health path. Never assume a running container or one five-minute canary proves 24–72-hour reliability.
4. Keep prompts, remote commands, screenshot evidence and failure reporting minimal; never display access tokens, SSH keys, API passwords or contents of unrelated applications. Never use RDC for routine GitHub reads or repetitive CI/status polling.

**Status as of 2026-10-29:** Desired *fully zero-focus FinalShell execution* = **UNQUALIFIED / NOT YET DEMONSTRATED**. *Bounded foreground FinalShell paste with clipboard restoration* = **VERIFIED, CONDITIONAL, NOT ZERO-FOCUS**. Future windows must not collapse these two statuses into one.
