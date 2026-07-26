# Historical First Launch Host Qualification Automation Abandonment Ruling V1

## 1. Status

This document records the earlier permanent-abandonment decision for the automated
supported-host qualification capability.

Status:

`SUPERSEDED_BY_LOWEST_PRIORITY_BACKLOG_RULING_V1`

The current binding decision is:

`governance/FIRST_LAUNCH_HOST_QUALIFICATION_LOWEST_PRIORITY_BACKLOG_RULING_V1.md`

The capability is no longer permanently abandoned. It remains inactive, unauthorized and last
in priority, but may be reconsidered after higher-priority work or when a real migration, major
redeployment, disaster-recovery, multi-host, multi-operator or higher-authority need exists.

## 2. Historical decision preserved

The earlier ruling concluded that permanent development was not justified for the immediate
First Launch because the capability is mainly useful during:

- initial deployment;
- migration to another host;
- major release redeployment;
- disaster recovery or complete host replacement.

These events are infrequent for the current personal trading-assistance system. A guided human
session can establish the minimum facts with much less development effort:

- confirm one fixed Ubuntu/systemd host;
- confirm one fixed system Python 3.12+ path;
- deploy one exact approved SHA;
- confirm a clean tree and valid systemd unit;
- confirm `ta-status` reaches and maintains `READY`;
- perform one controlled restart;
- complete the 3+3 readiness observations;
- confirm inactive, disabled and no remaining runtime process at closeout.

The cost of a reusable verifier, evidence model, Python trust chain, journal transformation
pipeline and extensive negative-case tests was disproportionate to immediate First Launch
value.

That cost assessment remains valid. What changed is the backlog disposition: the feature is
now preserved at the lowest priority rather than removed permanently.

## 3. Practical replacement until activation

At each real low-frequency event, prefer a temporary host-specific execution bundle covering:

1. read-only host confirmation;
2. exact-SHA deployment or restoration;
3. service verification and `ta-status` checks;
4. one controlled restart;
5. final inactive / disabled / no-process closeout.

For disaster recovery, also evaluate provider snapshots or images, repository-based recreation,
secure credential restoration and the existing database backup or restore procedure before
writing custom automation.

The temporary bundle must be specific to the approved host and SHA, visible to the operator,
fail or stop on unresolved output and not become an unreviewed permanent framework.

## 4. Efficiency and repair-stop rules remain binding

Before developing automation, compare event frequency, active manual cost, real risk reduction,
build cost, review cost and maintenance cost.

Prefer, in order:

1. existing command;
2. short checklist;
3. temporary visible script;
4. provider-native or maintained external tool;
5. small permanent script after repeated use proves value;
6. a framework only when scale, authority or compliance objectively requires it.

A normal repair plus one exceptional repair is the maximum for one bounded design route. After
both fail, do not continue patching the same design. Reduce scope or start a clean replacement.

PR #48 has exhausted that budget and must receive no fourth commit.

## 5. Historical archive

The detailed record remains available in:

- PR #48 and branch `docs/first-launch-supported-host-qualification-v1`;
- final reviewed Head `0451afee4285d41b7e95f0b3a2bc458c6ec16c6c`;
- exact-head CI Run 288 / Run ID `30204735266` / SUCCESS;
- `governance/FIRST_LAUNCH_HOST_QUALIFICATION_FAILURE_AND_DEFERRED_WORK_V1.md`;
- the Operations, Security and Final Acceptance failure reports;
- RR-01 through RR-08;
- the proposed but unimplemented two-script architecture.

## 6. Authority

This supersession note authorizes documentation synchronization only. It does not authorize PR
#48 repair, V2 implementation, host access, deployment, recovery execution, snapshot creation,
runtime, smoke, account authority, exchange write, Mark Ready or merge.
