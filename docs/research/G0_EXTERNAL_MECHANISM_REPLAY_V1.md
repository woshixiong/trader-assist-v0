# G0 external mechanism replay V1

Package `C_G0_EXTERNAL_MECHANISM_REPLAY_1` adds an offline external-bar research
route. [Plan V2](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-5987160672)
inherits [Plan V1](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-5985506847)
semantics unchanged, with [fresh V2 Pre-code PASS](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-5987332321).
[Issue #280 V1.2](https://github.com/woshixiong/trader-assist-v0/issues/280) controls
rights, staged disclosure, preregistration and the permitted evidence claim.

The route claims `MECHANISM_VALIDATION`; every economic result/fill is labeled
`SYNTHETIC_VENUE_OVERLAY`. Generated engineering fixtures cannot establish an
empirical Strategy edge or select a research leader. There is no certification,
native Hyperliquid execution, production promotion, parameter optimization,
S2–S5, ML, provider, dependency, workflow, service or order interface.

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
The sole existing-file change binds the historical R2B scope test to its reviewed
HEAD; inventory/access behavior is unchanged. External rows always retain
`EXTERNAL_REFERENCE` ownership.

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
package. Required existing CI and fresh Final Independent Review remain gates;
Mark Ready, merge and protected operations require separate human authority.
