# First Launch Host Qualification Lowest-Priority Backlog Ruling V1

## 1. Binding decision

The automated supported-host qualification capability attempted by PR #48 is retained as a
lowest-priority future backlog item.

Decision:

`DEFERRED_LOWEST_PRIORITY__NO_CURRENT_IMPLEMENTATION_AUTHORITY`

This means:

- do not continue PR #48;
- do not create a fourth commit;
- do not start the proposed V2 now;
- do not treat this capability as First Launch work;
- preserve the complete failed implementation and review history;
- reconsider a clean replacement only when development capacity or real operating need justifies it.

The prior permanent-abandonment wording is superseded by this ruling. The efficiency-first and
repair-stop rules remain binding.

## 2. Why the item remains in the backlog

The capability may become useful for:

- migration to a new server;
- major-version full redeployment;
- disaster recovery or complete host replacement;
- repeated deployments;
- multiple hosts or multiple operators;
- materially higher authority, including account or exchange-write integration;
- retained evidence or compliance requirements.

These events are currently infrequent, so the feature has low near-term return. Its future value
is not zero because repeatability, operator-error reduction and recovery speed become more
important as the system grows.

## 3. Priority

Backlog priority:

`LAST / LOWEST PRIORITY`

The item must not displace:

- First Launch completion;
- real-operation stability;
- strategy and signal quality;
- risk control;
- required account or execution safety work;
- defects observed in actual operation.

It may be scheduled only after higher-value work is complete or when an activation condition is
met.

## 4. Low-cost alternatives before permanent development

Until the backlog item is activated, use the least expensive adequate method for each event.

### 4.1 Migration or major redeployment

Use one temporary host-specific command bundle generated for the exact host and exact release
SHA. It should cover read-only host checks, exact-SHA deployment, service verification,
`ta-status`, one controlled restart and final closeout.

### 4.2 Disaster recovery

Use a small recovery card based on existing assets:

- repository and exact approved commit;
- current P4A deployment runbook;
- systemd unit and wrapper already in the repository;
- secure credential-ingress procedure;
- SQLite backup or restore procedure where applicable;
- cloud-provider instance or volume snapshot when separately configured and authorized;
- fixed-host command bundle generated for the recovery event.

Provider snapshots or images can reduce restoration time without requiring a custom host-audit
framework. Their retention, encryption, testing and cost must be evaluated separately.

### 4.3 Repeated but still infrequent events

Prefer, in order:

1. existing runbook and commands;
2. short checklist;
3. temporary visible script;
4. a maintained external tool or standard provider feature;
5. a small permanent repository script;
6. a custom framework only when objectively required.

The temporary solution must remain host-specific, visible to the operator and discarded or
archived as non-product material after use.

## 5. Activation conditions

A new implementation may be proposed when at least one of the following becomes true:

- development capacity exists after higher-priority roadmap work;
- a real migration, major redeployment or disaster-recovery project is scheduled;
- deployment frequency makes repeated manual work materially expensive;
- multiple hosts or operators create repeated inconsistency;
- manual execution causes actual errors or near misses;
- account, signing, nonce or exchange-write authority materially increases deployment risk;
- a real audit or retained-evidence requirement exists;
- a maintained external or open-source solution can close the need with low custom-code cost.

An activation condition permits research and cost-benefit analysis only. Implementation still
requires a new explicit user authorization, bounded file scope and commit budget.

## 6. Required route when activated

Do not resume or patch PR #48.

Use a clean task from the then-current live main. Before writing code:

1. review the actual deployment frequency and incidents;
2. evaluate provider-native, open-source and standard configuration tools;
3. define the minimum required capability;
4. reuse PR #48 only as historical failure input;
5. prefer one or two small tested scripts over a generalized framework;
6. ensure tests execute the exact operational scripts;
7. preserve a strict anti-expansion boundary.

The historical two-script proposal remains a candidate, not a predetermined solution:

- `scripts/p4a/first_launch_supported_host_preflight.sh`;
- `scripts/p4a/capture_first_launch_journal_evidence.sh`.

## 7. Preserved research archive

The complete research package consists of:

- PR #48 and branch `docs/first-launch-supported-host-qualification-v1`;
- final reviewed Head `0451afee4285d41b7e95f0b3a2bc458c6ec16c6c`;
- exact-head CI Run 288 / Run ID `30204735266` / SUCCESS;
- Operations, Security and Final Acceptance failure reports;
- RR-01 through RR-08;
- `governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md`;
- `governance/FIRST_LAUNCH_HOST_QUALIFICATION_AUTOMATION_ABANDONMENT_RULING_V1.md` as a superseded historical ruling;
- this lowest-priority backlog ruling.

No historical code needs to be copied into main to preserve it; Git and PR #48 already retain
the exact commits and review state.

## 8. Rules that remain unchanged

- Efficiency comes before perfection after the minimum real safety boundary is preserved.
- Low-frequency work should use existing commands, checklists or temporary scripts first.
- A normal repair plus one exceptional repair is the maximum for one bounded design route.
- After both fail, stop patching and replace the route.
- No host, deployment, runtime, smoke, account or exchange-write authority is implied.

## 9. Authority

This ruling authorizes backlog and documentation synchronization only.

It does not authorize:

- continued PR #48 development;
- a V2 implementation;
- closing PR #48;
- host access or SSH;
- deployment or recovery execution;
- snapshot creation;
- service mutation;
- credentials;
- runtime or smoke;
- Mark Ready;
- merge.

Every later action requires separate current authorization.
