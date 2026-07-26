# First Launch Host Qualification Failure and Deferred Work V1

## 1. Purpose

This document preserves the complete engineering record for the failed PR #48 supported-host
qualification route, the immediate minimum First Launch alternative, and the more complete
scripted design that may be researched or implemented later.

It is a planning and research record only. It does not authorize host access, SSH, AWS,
deployment, service mutation, credentials, runtime, smoke, account access, signing, nonce,
exchange write, Mark Ready, or merge.

## 2. Current decision summary

- PR #48 must not receive a fourth commit.
- PR #48 remains a frozen failed-design and review reference until a replacement route is
  technically accepted.
- The immediate First Launch path should not build a generalized host-verifier or evidence
  framework.
- The preferred immediate option is one human-controlled, guided deployment and qualification
  session on one fixed supported host.
- A future scripted V2 is retained in the backlog for repeated deployments, additional hosts,
  or when manual execution is no longer sufficiently reliable.

## 3. Exact failed-route state

Task:
`FIRST_LAUNCH_SUPPORTED_HOST_DEPLOYMENT_AND_QUALIFICATION_PACKET_V1`

PR:
#48

State:
`OPEN / DRAFT / NOT_MERGED`

Base:
`90f8cee145f07e135f8ba306832032ba917e2356`

Final reviewed Head:
`0451afee4285d41b7e95f0b3a2bc458c6ec16c6c`

Commits after base:
3

Changed files:
4

Exact-head CI:
`V0 contracts CI / Run 288 / Run ID 30204735266 / SUCCESS`

Final review result:

- Operations: FAIL
- Security and Authority: FAIL
- Final Acceptance: FAIL
- Technical Acceptance: FAIL
- Merge eligibility: none

CI success did not establish technical acceptance because the tests did not execute all of
the exact operational procedures documented for the future host.

## 4. What PR #48 attempted

PR #48 attempted to provide one complete repository-backed package for:

- supported-host preflight;
- deployment guidance;
- Python interpreter continuity;
- qualification evidence;
- two 30-minute READY observation windows;
- one controlled restart;
- journal evidence capture and sanitization;
- final inactive / disabled / no-process proof;
- offline tests for the packet and evidence contract.

The route began as a documentation and evidence package. During repair, it increasingly
became an executable verification design without placing the authoritative executable logic
in repository scripts.

## 5. Repair history

### Initial implementation

The initial packet documented the authority phases, host profile, P4A deployment reuse,
`ta-status`, 30+30-minute observation, one controlled restart, and qualification evidence.

### Repair 1

Repair 1 attempted to close command correctness and alignment issues inside the same four
files. It retained the main design: long shell procedures in documentation plus mostly static
or semantic tests.

### Exceptional Repair 2

A one-time exceptional third commit was authorized after the normal repair budget was
consumed. It attempted to add fail-closed behavior, complete evidence fields, secure journal
handling, Python identity continuity, and offline behavioral testing.

The final reviews still failed. A fourth commit is prohibited because continuing repairs
would reproduce the previously observed pattern of expanding scope and increasingly fine
edge-case development.

## 6. Core design failure in simple terms

The route created more than one version of the same operational truth:

1. the documentation contained shell commands intended for the real host;
2. the tests executed a separately rewritten harness rather than those exact commands;
3. the P4A runbook contained overlapping procedures;
4. the evidence example described results that were not always produced by one tested
   authoritative implementation.

Therefore, CI could pass even when the real commands remained different, incomplete, or
fail-open.

The security review then correctly required stronger interpreter trust, journal cleanup,
sanitization, exit-code handling, service-manager proof, connectivity handling, and bounded
resource evidence. Each new requirement created additional implementation and test edges.

The problem is not a discovered defect in the trading runtime. It is a mismatch between a
manual First Launch objective and an increasingly software-like host qualification system.

## 7. Consolidated unresolved technical issues

### 7.1 Documented shell was not the tested implementation

The tests executed a separate behavioral model. The exact commands intended for the host
were not fully executed by the test suite.

### 7.2 Python trust was incomplete

An absolute executable path alone does not prove that a Python binary is safe for privileged
use. The failed design did not completely verify canonical path, regular-file status,
ownership, write permissions, symlink state, digest, version, and substitution resistance.

### 7.3 Journal evidence could fail open

Extraction, scanning, transformation, hashing, and cleanup did not form one exact,
fail-closed executable transaction.

### 7.4 Raw logs were not truly sanitized

Copying raw journal output under a new name is not sanitization. A safe retained artifact
would require an allowlisted transformation that removes raw message text and identifying
metadata.

### 7.5 Packet and runbook competed

The packet and P4A runbook described overlapping journal and qualification procedures,
creating ambiguity over which one was authoritative.

### 7.6 Closeout commands masked errors

Shell patterns that map all nonzero results to `inactive` or `no process` cannot distinguish
an expected negative state from a command or service-manager failure.

### 7.7 Host PASS overclaimed capabilities

Finding binaries did not prove systemd was the functioning service manager. Mandatory
outbound connectivity was also not established or explicitly deferred before PASS.

### 7.8 Resource evidence could expose identity

Raw filesystem output may disclose device, mount, NFS, hostname, or infrastructure details.
Only normalized resource values should be retained in a future automated system.

## 8. Continue development versus defer automation

| Area | Continue full scripted development now | Defer automation and use minimum guided launch |
| --- | --- | --- |
| Repository work | Two scripts, packet, manifest, tests, runbook update | One short checklist or command card |
| Expected files | About six | About one or two documentation files |
| Expected development | At least one to two working days, possibly more after review | About three to five hours of preparation |
| Tests | Extensive fake-command and negative-case matrix | Existing repository tests plus direct operator observation |
| Host coverage | Repeatable supported-host procedure | One fixed approved host only |
| Python assurance | Canonical path, owner, mode, symlink, digest, version | Human confirms one fixed system Python path before use |
| Journal evidence | Deterministic transformation, scans, hashes, cleanup | Diagnostic viewing only; no retained qualification artifact |
| Connectivity | Explicit probe design and result model | Verified later in separately authorized supervised smoke |
| Repeatability | High after successful implementation | Moderate; depends on guided operator execution |
| Initial launch speed | Slower | Faster |
| Future multi-host value | High | Low |
| Risk of scope expansion | Material | Low when checklist remains fixed |

### Practical difference at First Launch

Both routes can establish the minimum facts needed for a personal public-data-only First
Launch:

- the exact approved code is deployed;
- the service starts correctly;
- `ta-status` reaches READY;
- READY remains stable before and after one restart;
- the service can finish inactive and disabled;
- no account or exchange-write authority exists.

The full scripted route additionally produces repeatable, machine-checked host and evidence
proof. That additional assurance matters more for repeated deployment, multiple operators,
multiple hosts, institutional audit, or automated rollout than for one supervised personal
launch.

## 9. Minimum guided manual route

### 9.1 Fixed assumptions

Use only one explicitly approved host profile:

- one controlled Ubuntu/systemd host;
- one instance;
- one runtime process;
- ETH public data only;
- SQLite;
- no account credentials;
- no wallet or private key;
- no signing or nonce;
- no exchange write;
- one fixed approved system Python 3.12+ path.

Do not claim support for arbitrary equivalent Linux hosts.

### 9.2 Work the operator must perform

The operator must be able to:

1. open Terminal or FinalShell and connect to the approved host;
2. paste one command block at a time;
3. read a short PASS / FAIL / UNKNOWN result;
4. stop when instructed after any failure or unknown result;
5. provide the displayed non-secret output back to the guiding window;
6. authorize each later phase separately;
7. observe the two readiness windows;
8. perform exactly one instructed service restart;
9. make the final human acceptance decision.

The operator is not expected to write code, edit system files manually, interpret long logs,
or design shell commands.

### 9.3 Work the guiding AI or engineer can provide

For the exact host and authorized SHA, the guiding window can prepare:

- one copy-ready read-only preflight block;
- one copy-ready deployment block derived from the existing P4A runbook;
- one copy-ready status and qualification card;
- exact instructions for what output to return;
- stop conditions after every phase;
- one bounded journal command only if readiness remains abnormal;
- a final closeout block for inactive, disabled, and no-process checks.

The guidance can be performed interactively: the operator pastes one bounded block, returns
the result, and receives the next block. This lowers interpretation risk without creating a
new repository automation framework.

### 9.4 Efficiency tools

The recommended simple tooling is:

- macOS Terminal as the primary interface;
- FinalShell only as an optional SSH interface;
- a local shell alias for the remote `ta-status` command after the host is stable;
- one temporary, host-specific command bundle generated for the approved session;
- `tee` only for non-secret summary output when retention is useful;
- no raw journal upload or persistent evidence bundle by default.

A temporary command bundle is not a reusable production verifier. It must be specific to the
approved host and SHA, visible to the operator, fail at the first unresolved condition, and be
discarded after the session.

### 9.5 Minimum phase sequence

#### Phase A — read-only host confirmation

Confirm only:

- expected Ubuntu release;
- systemd is active;
- fixed Python path exists and reports 3.12+;
- Git is present;
- basic disk and memory are adequate;
- required repository and service paths do not contain an unresolved conflict.

No installation or service mutation occurs.

#### Phase B — deployment

After separate authorization:

- deploy one exact full SHA;
- verify exact Head equality;
- verify clean tree;
- create the venv with the fixed Python path;
- install the existing hashed runtime lock;
- verify the systemd unit;
- preserve secure credential ingress and default-off state;
- verify `ta-status` is installed and executable.

#### Phase C — supervised qualification

After separate authorization:

- start the service;
- obtain READY;
- observe READY at start, midpoint, and end of the first 30-minute window;
- perform exactly one controlled restart;
- obtain READY again;
- observe READY at start, midpoint, and end of the second 30-minute window;
- treat any NOT_READY or STATUS_UNKNOWN result as a failed or incomplete attempt;
- use one bounded journal view only for diagnosis if needed.

#### Phase D — closeout and acceptance

- stop the service;
- confirm inactive;
- confirm disabled;
- confirm no runtime process remains;
- record only a concise non-secret result summary;
- request separate final acceptance before real operation.

## 10. Can the user complete the manual route?

The route is suitable when the user can copy and paste commands, return outputs, and follow
explicit stop instructions. It does not require Linux administration expertise if the guiding
window supplies exact commands and interprets each result.

The guiding window cannot directly operate the user's Mac or host unless an appropriate
connected execution tool is available. It can, however, perform the command design,
step-by-step interpretation, safety gating, troubleshooting, and final checklist review.

The manual route should be rejected or paused if:

- the host differs materially from the fixed supported profile;
- the fixed Python path cannot be confidently established;
- unexpected prior deployments or service files exist;
- credential handling requires improvisation;
- the user cannot reliably return the required outputs;
- readiness is unstable or repeated restart is required.

## 11. Future scripted V2 retained for research

The failed-route reviewers recommended a clean replacement from live main with two short,
single-purpose scripts:

1. `scripts/p4a/first_launch_supported_host_preflight.sh`
2. `scripts/p4a/capture_first_launch_journal_evidence.sh`

The proposed bounded replacement also included:

- a V2 qualification packet;
- a V2 evidence JSON example;
- tests that execute the exact scripts;
- one P4A runbook update.

This design is technically stronger because documentation references the executable scripts
and tests execute the same implementation used operationally.

It should remain deferred unless one or more activation criteria are met:

- a second deployment is planned;
- a second host is introduced;
- another operator must perform deployment;
- the system becomes account-connected or exchange-writing;
- evidence retention becomes a real compliance requirement;
- manual qualification produces errors or inconsistent results;
- deployment becomes frequent enough that automation saves more time than it costs.

## 12. Research questions

A separate research effort should determine:

1. What is the minimum trustworthy interpreter policy for a single Ubuntu host?
2. Can the Ubuntu package-managed Python path be accepted without a custom digest chain?
3. Which read-only checks reliably prove systemd is the active service manager?
4. Should outbound connectivity be verified in host preflight or supervised smoke?
5. What minimum evidence is actually needed for personal First Launch acceptance?
6. Is retained journal evidence necessary at all for a non-account, non-trading-write system?
7. What deterministic allowlisted journal representation provides useful diagnostics without
   retaining sensitive or identifying text?
8. Can existing tools such as `journalctl --output=json`, `systemd-analyze`, or a small
   standard utility reduce custom code?
9. At what deployment frequency does a scripted verifier become economically justified?
10. Which review requirements are safety-critical for this product and which are primarily
    institutional audit requirements?

## 13. Value assessment

### Immediate value

A complete automated host qualification system has limited immediate value for one personal,
public-data-only First Launch. The most important immediate controls are exact code identity,
safe credential ingress, `ta-status`, stable public-data runtime, default-off behavior, and
human acceptance.

### Future value

The work becomes valuable when deployment must be repeated or delegated. At that point it can
reduce operator errors, prevent unsafe interpreter substitution, create consistent evidence,
and make multiple hosts easier to qualify.

### Investment ruling

Do not invest heavily before First Launch unless the minimum guided route proves unreliable.
Preserve the design and research record, complete the first supervised deployment with a
fixed-host checklist, collect real operational evidence, and then decide whether the actual
failure modes justify scripted V2 development.

The preferred order is:

`FIRST LAUNCH WITH MINIMUM GUIDED CONTROL`

then

`REAL OPERATION EVIDENCE`

then, only when justified,

`SCRIPTED HOST QUALIFICATION V2`.

## 14. Backlog registration

### Active First Launch P0

- design the minimum manual checklist;
- identify and approve one fixed host profile;
- create one host-specific command bundle after host authorization;
- complete deployment and 3+3 supervised qualification;
- finalize Mac operator shortcut and command card;
- reach separate real-operation acceptance.

### Deferred post-First-Launch engineering

- research RR-01 through RR-08;
- evaluate the two-script V2 architecture;
- define activation criteria from real operation;
- decide whether journal evidence should be retained;
- decide the minimum interpreter trust policy;
- decide connectivity-probe placement;
- implement V2 only under a new bounded task and commit budget.

## 15. Authority and PR disposition

- PR #48: frozen failed-design reference; no fourth commit.
- PR #48 closure: not authorized by this document.
- Replacement scripted V2 implementation: not authorized by this document.
- Host access: not authorized.
- Deployment: not authorized.
- Runtime or supervised smoke: not authorized.
- Mark Ready: not authorized.
- Merge: not authorized.

Every later action requires its own current user authorization.
