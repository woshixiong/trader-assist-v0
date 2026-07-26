# First Launch Host Qualification Automation Abandonment Ruling V1

## 1. Binding decision

The repository-backed automated supported-host qualification feature attempted by PR #48 is
abandoned as a planned product or engineering feature.

Decision:

`ABANDONED_LOW_FREQUENCY_AUTOMATION`

This is not an active First Launch task, a post-First-Launch backlog item, or a deferred
implementation commitment.

PR #48 must receive no fourth commit. No V2 replacement implementation is authorized or
planned.

The historical PR, failed reviews, proposed two-script architecture, and research record are
preserved only as an archive. Preservation does not imply future implementation.

## 2. Why the feature is abandoned

The capability is primarily useful during:

- initial deployment;
- migration to another host;
- a major release requiring full redeployment;
- disaster recovery or complete host replacement.

These are expected to be infrequent events for this personal trading-assistance system.
Ordinary operation relies on `ta-status`, bounded diagnosis, and one operator-controlled
restart; it does not repeatedly require a full host qualification framework.

A guided human session can establish the minimum launch facts with limited operator effort:

- confirm one fixed Ubuntu/systemd host;
- confirm one fixed system Python 3.12+ path;
- deploy one exact approved SHA;
- confirm a clean tree and valid systemd unit;
- confirm `ta-status` reaches and maintains `READY`;
- perform one controlled restart;
- complete the 3+3 readiness observations;
- confirm inactive, disabled, and no remaining runtime process at closeout.

Developing and reviewing a reusable automated verifier, evidence model, Python trust chain,
journal transformation pipeline, and extensive negative-case tests costs substantially more
than performing this low-frequency guided work.

## 3. Practical replacement

At each real deployment event, use a temporary host-specific execution bundle rather than a
repository feature.

The bundle may contain a small number of visible copy-ready command blocks for:

1. read-only host confirmation;
2. exact-SHA deployment;
3. runtime start and `ta-status` checks;
4. one controlled restart;
5. final inactive / disabled / no-process closeout.

The bundle must be generated for the exact approved host and SHA, used under step-by-step
human supervision, fail or stop on unresolved output, and be discarded after the session.

It must not become a generalized production verifier or permanent evidence framework.

Journal output is diagnostic only when readiness is abnormal. A retained sanitized and hashed
journal evidence bundle is not a normal First Launch requirement.

Connectivity is verified during separately authorized supervised runtime or smoke rather than
through a new general host-audit subsystem.

## 4. Permanent efficiency rule

Future engineering decisions must apply the following rule before developing automation:

`FREQUENCY × MANUAL_COST × RISK_REDUCTION MUST EXCEED BUILD_AND_MAINTENANCE_COST`

Do not build a product-grade feature when all of the following are true:

- the event is infrequent;
- one operator can complete it with guided copy-and-paste commands;
- the active human effort is small;
- a short temporary script or command bundle can reduce mistakes;
- the feature is not required for ordinary operation;
- the proposed automation creates a large test, security, evidence, or maintenance surface.

Efficiency is the primary optimization target after preserving the minimum real safety
boundary.

Avoid perfect or institution-grade automation for personal, low-frequency operations.
Prefer, in order:

1. an existing command;
2. a short checklist;
3. a temporary visible script;
4. a small permanent script only when repeated use proves its net value;
5. a full framework only when scale, frequency, authority, or compliance objectively requires
   it.

Two failed repair rounds are a mandatory stop signal. After the normal repair and one
exceptional repair fail, do not continue patching the same design. Reduce scope, replace the
route, or abandon the feature.

## 5. Historical archive

The detailed history remains available in:

- PR #48 and branch `docs/first-launch-supported-host-qualification-v1`;
- final reviewed Head `0451afee4285d41b7e95f0b3a2bc458c6ec16c6c`;
- exact-head CI Run 288 / Run ID `30204735266` / SUCCESS;
- `governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md`;
- the Operations, Security and Final Acceptance failure reports;
- the proposed but unimplemented script names:
  - `scripts/p4a/first_launch_supported_host_preflight.sh`;
  - `scripts/p4a/capture_first_launch_journal_evidence.sh`.

The unresolved RR-01 through RR-08 findings remain research material. They are not open bugs
in the accepted trading runtime and are not active implementation tasks.

No historical code needs to be copied into main. PR #48 already preserves the exact failed
implementation and complete commit history.

## 6. Reopening policy

This feature must not be reopened automatically because of a second deployment, new major
release, or ordinary host maintenance.

A new implementation may be considered only after a fresh cost-benefit review and explicit
user authorization. Material evidence would need to show that at least one of the following is
true:

- deployments have become frequent enough that repeated manual work costs more than the
  automation;
- multiple operators or multiple hosts make guided execution unreliable;
- manual deployment has produced actual safety incidents or repeated errors;
- account, signing, nonce, or exchange-write authority materially raises the deployment risk;
- a real external compliance or retained-evidence requirement exists;
- a proven maintained external tool can provide the capability with much less custom code.

Even then, first evaluate existing open-source or standard operating tools. Do not immediately
resume the PR #48 architecture.

## 7. Authority

This ruling authorizes documentation and planning synchronization only.

It does not authorize:

- closing PR #48;
- host access or SSH;
- deployment;
- service mutation;
- credentials;
- runtime or smoke;
- account access;
- signing, nonce, or exchange write;
- Mark Ready;
- merge.

Every later operational action requires separate current authorization.
