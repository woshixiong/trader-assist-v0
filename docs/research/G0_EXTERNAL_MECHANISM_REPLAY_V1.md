# G0 external mechanism replay V1

Package `C_G0_EXTERNAL_MECHANISM_REPLAY_1` adds an offline external-bar research
route. [Plan V3](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-5987565251),
[Refreeze 2](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-5987514882)
and [fresh V3 Pre-code PASS](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-5987760911)
retain the V1/V2 research semantics and move full/native validation to qualified
GitHub CI. [Refreeze 3 / Repair 1](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-5988276922),
[Plan V4](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-5988355720)
and [fresh V4 Pre-code PASS](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-5993379947)
repair shared reporting ownership and this document's final topology.
[Issue #280 V1.2](https://github.com/woshixiong/trader-assist-v0/issues/280) controls
rights, staged disclosure, preregistration and the permitted evidence claim.

The route claims `MECHANISM_VALIDATION`; every economic result/fill is labeled
`SYNTHETIC_VENUE_OVERLAY`. Generated engineering fixtures cannot establish an
empirical Strategy edge or select a research leader. There is no certification,
native Hyperliquid execution, production promotion, parameter optimization,
S2–S5, ML, provider, dependency, service or order interface. The sole workflow
addition is the retained native DEV regression on the existing qualified E4
CI surface; it adds no execution or production authority.

## Owners and APIs

`mechanism_contracts.py` defines immutable, concrete, hash-bound run, source,
config, market, candidate, episode, decision, fill, path, result, pair, metrics,
summary and bundle contracts. `mechanism.py` composes the existing scanner and
pure Three Setup kernel, derives simple causal baselines and applies the
registered bar arithmetic model. `mechanism_harness.py` guards source access,
composes existing readers, validates the full matrix, computes diagnostics and
emits bounded aggregates.

The public harness functions are `validate_mechanism_access`,
`read_mechanism_sources`, `replay_mechanism`, `mechanism_trial_identity` and
`mechanism_summary_bytes`. Their immutable positional inputs are run, sources,
inventory, ledger, block plan, visibility, config and candidates, followed by
keyword `s0_preparation_hash`; replay also requires an explicit `as_of_ns`.
The pure functions `derive_mechanism_opportunities` and
`evaluate_mechanism_candidate` accept admitted in-memory observations. Pure
helpers grant no file access; the complete replay authenticates their retained
receipts and output independently at bundle construction and aggregate egress.

Current Strategy identity is unchanged:

```text
THREE_SETUP_CHAMPION_E3_V1
FL-MA-PRICE-ACTION-v0.1
2026-08-03-r1
SESSION-MOMENTUM-R3
KERNEL_SCHEMA_VERSION=1
```

`StrategyPackageManifest`, `scan_cross_section`, scanner continuation and
`evaluate_strategy` retain Strategy ownership. No Setup logic or thresholds are
copied. `replay_dev`, `_native_candidate` and native fills remain unchanged.
The historical R2B inventory scope guard was absorbed upstream by PR #294;
`tests/test_research_inventory_manifest.py` is absent from the PR #295 diff and
is not edited by Repair 1. Its original historical allowlist and inventory/access
protections remain intact. External rows retain `EXTERNAL_REFERENCE` ownership.

`dev_reporting.select_prospective_candidate` is the sole prospective
simpler-on-equivalence selection owner. Retained `summarize_dev` delegates with
unchanged valid-input output bytes. `summarize_mechanism` receives keyword `run`
and `candidates` and requires `pre.candidate_order == run.candidate_hashes ==
tuple(c.record_hash for c in candidates)` with exact complexity alignment.
Eligibility stays caller-owned. The pure helper filters eligible candidates,
forms the inclusive preregistered equivalence band around best after-cost Thesis
R, and selects lowest preregistered complexity then stable preregistered order.
A non-simpler challenger below the strict minimum incremental gate falls back
only to eligible Champion, with no second-challenger fallback. A genuinely
simpler equivalent candidate may win even with a small negative paired delta.

Package C calls that helper independently for each existing
family/mode/side/regime cell: Champion versus sweep; Champion versus both close
and Donchian within each breakout mode; Champion versus range. No unrelated
family/mode participates in another edge. Champion's selector-only self delta
is zero; diagnostic paired metrics remain unchanged. Global disposition
aggregates only edge decisions, after unavailable/incomplete MORE_EVIDENCE and
insufficient/non-performance gates: any selected baseline gives RESEARCH_LEADER,
otherwise any selected Champion gives KEEP_CURRENT, otherwise REJECT. Synthetic
engineering evidence cannot establish empirical selection. Sufficient performance
evidence with no coherent Champion and no edge-selected baseline retains the
hard stop and diagnostic action, with no S2–S5 progression.

## Access before source I/O

Every request passes a whole-batch gate before admission construction, store
construction, path resolution, file/stat access, byte hashing or outcomes.
The public reader repeats the gate. A permitted first source and forbidden
second source still result in zero source reads.

Only rights-authorized R1/R2/R3, `DEV_EXPOSED`, exact `CURRENT_DEV` inventory
allocations are admitted. Sealed/validation/lockbox, R0/R4/R5/R6, forward/native
identity and reserves are rejected. The gate composes existing DEV authority,
R2B inventory, preregistration/S0, append-only trial, block and visibility
contracts; it checks question, Strategy, cut, instruments, rights, mapping,
registry, candidates, config and reserve identities. Equity/RWA requires an
accepted canonical PIT QA receipt. Missing inventory remains unavailable and
is never read or substituted.

`MechanismSource.checksum` binds the exact **replay sidecar** checksum through
the source/run hash. The dataset manifest and DEV authority separately bind
the original **dataset/raw-evidence** checksum. These are distinct existing
storage identities; the sidecar contains the dataset hash, so identifying its
checksum with the original dataset checksum would create a circular binding.
The unchanged reader verifies sidecar checksum, dataset/mapping/capability/
policy bindings and reproduces admission observations before returning rows.

This implementation package opens only generated test sidecars. Real DEV use
requires a separately frozen complete inventory/reserve allocation and numeric
G0 preregistration. It cannot fill in sample sufficiency, cost, risk, funding,
Donchian lookback, delay or QA authority from attractive outcomes.

## Causal episode and candidate composition

V1 supports complete UTC-aligned finalized external 5m bars. The config freezes
`decision_start_ns` before opening data: prior bars initialize causal history,
and unavailable coverage after that boundary remains in the denominator. Conversion from ns
to kernel ms is exact; unsupported or partial intervals are unavailable. Kernel
15m/1h aggregation uses causal prefixes. Event, knowledge, finality and mapping
knowledge all precede a decision. Cross-sectional scanner inputs use the full
frozen universe; missing cohort members do not become survivor-only ranks.
Spread/liquidity inputs are explicitly registered modeled assumptions here.

The episode register is the union of kernel-created MarketEvents, scanner raw
breakout episodes and simple baseline triggers. Formal confirmation or a fill
is not necessary for retention. Kernel-created IDs remain kernel IDs; separate
external episodes have domain-separated IDs. The registered overlap key is
market/family/side/boundary, with a bounded expiry. Correlation clusters use a
prospective theme plus fixed time bucket. Breakout MICRO_FAST, STANDARD and
UNCONFIRMED strata share the underlying event/Thesis IDs; they are never pooled
as independent observations. Missing/warmup slots have unavailable evidence,
not invented independent MarketEvents.

Every retained stratum receives all five frozen candidate results, including
suppressed, nonfill, unavailable and not-applicable rows. Comparisons are only
sweep vs simple sweep, breakout modes vs simple close/Donchian breakout, and
range vs simple range rejection. Unrelated families are not ranked together.

Baselines use prior causal zone boundaries; Donchian extrema exclude the
signal bar. Signal geometry and registered target-R multiple are frozen at
activation. Champion geometry and confirmation come from actual kernel
receipts. The harness rejects caller signal substitution and pruned matrices.

## Modeled economics

- A finalized decision bar cannot fill itself. Modeled entry is the first next
  whole bar open at/after registered delay and before expiry. Champion entry
  zone/chase constraints apply to the adverse modeled price.
- Quantity is original cash risk divided by stop distance, capped by registered
  capital. `CostModel.size` must equal one and is a non-sizing placeholder;
  it never independently sets quantity.
- Spread half-width and slippage are adverse per leg; taker fees and additional
  costs apply to each modeled notional. There is no maker/queue/passive-touch
  fill claim.
- Applicable funding is an explicit fixed modeled rate/anchor/interval. Missing
  applicable funding makes economics incomplete. Nonapplicable funding is
  separately declared; future funding does not inform activation.
- Both stop and target touched in a bar means ambiguity and stop first.
  Gap-through-stop uses the worse open/stop; favorable target gaps do not receive
  an optimistic improvement. Terminal exit uses the last fully covered close.
- Gaps, unknown continuity, missing geometry, missing cost and horizon censorship
  preserve null economics. Suppression or nonfill with complete evidence has
  realized zero policy cash, separately from registered counterfactual R.
- There is one modeled attempt, with no re-entry or winner scaling. Re-entry tax
  is explicitly not applicable. OHLC excursions are bounds, never observed
  native executable excursions.

## Diagnostics, gates and reproducibility

Primary inference is MarketEvent/Thesis/cluster and `THESIS_NET_R_AFTER_COST`.
Risk normalization uses the original cash-risk denominator. Pairs are matched
within family/mode with the same episode, costs, delay, availability and risk;
positive delta means baseline minus Champion.

Reports retain observed and total counts, coverage, unavailable/incomplete and
ambiguity rates, participation, missed opportunity, false positives/registered
counterfactual false negatives, per-leg fees/friction/funding/additional costs,
turnover, MFE/MAE and first-touch/recovery paths, chronological drawdown, tail
loss/MAE, losing streak and winner/cluster concentration. Cluster delta ranges
are descriptive; there is no inferential significance or certification claim.
Undefined metrics remain null. Frozen gates and mandatory cells precede any
research disposition. Met sufficiency with no coherent mechanism stops broad
optimization and routes to scanner/setup/entry/cost diagnosis.

Fingerprinting binds current Strategy, code/runtime/dependency, universe,
source/dataset/mapping/rights/admission/checksum, inventory/reserve/preregistration,
trial ledger, candidates, config/risk/cost/funding/delay, full roster, decisions,
results, pairs, diagnostics, visibility and output artifacts. Identical inputs
produce identical canonical bytes. Rehashed omission or result forgery is
rejected by deterministic recomputation at bundle/report authentication.
Operational reruns do not debit material trials; economic model changes do.

Aggregate egress has an explicit field allowlist, attribution and byte/bucket
limits; source paths, locators and raw/event evidence are withheld. A bundle
retains local diagnostics but does not publish itself. Aggregate-only rights
must not disclose its local rows.

## Validation

Generated tests exercise the actual external admission/sidecar reader and
current scanner/kernel owners, access spies, claims, causal prefixes, matched
risk/model arithmetic, same-bar/gap behavior, omission/tamper/fingerprint and
visibility. Retained native replay, DEV lifecycle/reporting, R2B inventory and
kernel/scanner tests prove unchanged owners. No real data is opened for this
package. The final candidate includes the unchanged E4 step
`Retained native DEV replay exact-rc5 qualification`, executing exactly:

```text
/tmp/trader-assist-e4-venv/bin/python -m pytest -q tests/test_research_replay_dev_harness.py::test_matched_s0_dev_real_native_results_and_fingerprints
```

It runs after existing Linux x86_64 / Python3.12 / Nautilus 2.0.0rc5 identity
proof, using the existing hashed environment, with failure propagated to the
job and no conditionalization or broad test expansion. V0 contracts CI is the
authoritative full Ubuntu/Python3.12 repository pytest+mypy surface; E4 is the
authoritative retained native rc5 surface. The selected test must execute and
pass, not merely skip. Failed-head CI PASS is historical evidence and cannot
accept a repaired head. All required checks must PASS on the repaired exact
HEAD before fresh Final Independent Review. Local Linux rc5 unavailability
moves the gate to that qualified surface; it does not waive it.

Required existing CI and fresh Final Independent Review remain gates;
Mark Ready, merge and protected operations require separate human authority.
