# FinalShell Target-Host Deployment Workflow V1

**Status:** SPECIALIZED CANONICAL OPERATIONS WORKFLOW  
**Effective date:** 2026-08-26  
**Repository:** `woshixiong/trader-assist-v0`  
**Authority:** subordinate to explicit current user authority, current Product/Strategy/Security/Operations authority, the active manifest, and `governance/ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md`.

## 1. Purpose

This document freezes the default user-operated target-host deployment transport for Trader Assist / Trade OS so future Engineering and Operations windows do not repeatedly redesign, re-ask, or silently substitute the deployment workflow.

The current normal operator path is:

```text
MACOS LOCAL TERMINAL
  -> GENERATE ONE EXACT-RELEASE DEPLOYMENT FOLDER / BUNDLE
  -> FINALSHELL FILE MANAGER / SFTP UPLOAD
  -> ALREADY-CONNECTED FINALSHELL SERVER TERMINAL
  -> ONE CONTIGUOUS REMOTE EXECUTION BLOCK
  -> EVIDENCE / RESULT RETURN
```

FinalShell is the operator surface. It is not a new deployment authority, source of truth, runtime, orchestration framework, or replacement for GitHub/systemd/Registry/security controls.

## 2. Permanent workflow invariants

```text
DEFAULT_TARGET_HOST_OPERATOR_SURFACE=FINALSHELL
LOCAL_ARTIFACT_BUILD_SURFACE=MACOS_TERMINAL
TRANSFER_SURFACE=FINALSHELL_SFTP_OR_FILE_MANAGER
REMOTE_EXECUTION_SURFACE=ALREADY_CONNECTED_FINALSHELL_TERMINAL
MAC_DIRECT_SSH_REQUIRED=NO
ONE_LOCAL_GENERATION_BLOCK=DEFAULT
ONE_TRANSFER_FOLDER=DEFAULT
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

## 4. Phase A — local exact-release package generation

Engineering/Operations should provide one contiguous ordinary macOS Terminal block that performs the complete local packaging step.

The block should, where applicable:

- resolve or use the explicitly authorized full 40-character release SHA;
- fresh-check that the expected release remains valid before packaging;
- obtain source from the approved local repository/worktree or another exact verified source;
- fail closed on repository/release identity mismatch;
- create one uniquely named deployment folder;
- place only required non-secret deployment payload inside that folder;
- include server-side execution script(s) needed for the bounded deployment/qualification;
- create a manifest identifying the exact release SHA and included paths;
- calculate cryptographic hashes for the package/payload or manifest-bound files;
- record the expected upload destination;
- emit a concise operator summary naming the single folder that must be uploaded.

The user should not have to manually assemble files, edit generated scripts, copy multiple unrelated payloads, configure a new macOS SSH route, or reconstruct the release from chat text.

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

After local package generation, the normal irreducible human transfer step is:

1. open the already configured target host in FinalShell;
2. use FinalShell file manager/SFTP transfer;
3. upload the single generated deployment folder to the exact temporary destination specified by Engineering/Operations;
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
1. PASTE ONE LOCAL MACOS TERMINAL BLOCK
2. UPLOAD ONE GENERATED FOLDER THROUGH FINALSHELL
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
