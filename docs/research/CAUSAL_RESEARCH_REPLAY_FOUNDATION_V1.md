# Causal research replay foundation V1

Package B implements the frozen [Plan v1](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-5977844499)
in `research_replay`. It is an offline engineering library. Every executable run
is S0 / PIPELINE_CORRECTNESS_ONLY. It does not certify an edge, select parameters,
promote a Strategy, or acquire data. Package A and Hyperliquid E4 remain the raw
evidence, rights, mapping, storage and exact-venue truth owners.

## Composition and identities

`evidence.read_external` delegates opening/checksums/admission/PIT to the accepted
ReferenceReplayReader. `read_e4` consumes the existing manifest, snapshot and
AdmittedEvent ledger. Both check the accepted DatasetManifest access gate first.
Only SACRIFICIAL/CONTAMINATED and allowed pipeline rights can be opened; even
DEV_EXPOSED is refused by this access contract. No raw manifest is rewritten.
`bind_domain_records` retains lawful MarketEvent, ScannerEvidence, Candidate,
StrategyEvaluation, FormalizationDisposition and FormalSignal IDs and hashes.
Missing upstream opportunities are not synthesized. Suppressed opportunities can
have an explicitly absent FormalSignal.

All contracts are immutable, extra-field-forbidding, domain-separated BoundRecords
using the accepted canonical JSON/SHA256 implementation. Consumers revalidate
serialized identities rather than trust a caller's Pydantic container.

| Contract | Binding |
|---|---|
| EvidenceRef / Observation | Original source/admission hash, dataset/mapping/interval/Registry, owner, native instrument/expression, units, source mode/tier/exposure, rights, validity/coverage, original clocks, ordinal, quality/epoch |
| FeatureSpec | Semantic algorithm/release, family, sorted parameters, raw kinds, clock/window/warmup/stale/skew, units, rounding and availability/mapping claim |
| FeatureObservation | Spec and consumed source/mapping hashes, source modes, event/knowledge cutoffs, values/unit/coverage, ancestor features, availability reasons, original versus retrospective claim |
| Opportunity / DecisionSnapshot | Fixed roster identity, original MarketEvent/Thesis/funnel IDs, Three Setup/mode/side, Registry/Strategy/parameter, barriers/expiry/invalidation, immutable prefix, participation/reason, cost/horizon |
| CandidatePlan | Exact authority-qualified participation/L/R/E/A policies, frozen parameters, attempt/add/cost/winner bounds and comparison role |
| ResearchRunSpec | Package/base/release/runtime, Strategy, datasets/features/candidates/roster, cost/fill/delay/size/seed, trial/block/visibility/correlation, horizon and resource bounds |
| Attempt / CandidateResult | Trigger and native entry/exit fills, scratch/winner state, fresh-condition receipt, actions, signed cash flows, paths, outstanding exposure and limitations |
| ReplayBundle | Ordered semantic input/frame/output/pair/counterfactual hashes and noncircular fingerprint bound to the RunSpec |

The documentation example is an R0 shape example with synthetic hash references,
not a provider-enabled or production configuration. No new schemas are exported
into the production schema registry.

## Causal alignment and clocks

An eligible source has event time <= t and retained knowledge time <= K. Its PIT
interval must contain the event (half-open), and mapping known/recorded times must
be <= K. Finalized bars also require bar end <= t. Joins choose only the greatest
eligible backward timestamp. Future nearest-neighbor joins and later revisions
cannot change an earlier immutable decision. Equal-time conflicts, gaps, epoch
breaks, stale quotes and unknown continuity remain explicit.

EVENT, RECEIVE, OBSERVED and INIT are distinct variants. RECEIVE requires a true
receive timestamp and provenance; neither admission nor replay time substitutes
for it. Negative/inconsistent clocks are excluded. An explicitly retrospective
FeatureSpec can diagnose historical event-time alignment at a declared K; its
output is tagged RETROSPECTIVE_EVENT_TIME and cannot support operational
availability. HISTORY/LIVE/FREE_REFERENCE_IMPORT are retained source identities;
REPLAY is a separate consumption mode.

`cross_venue` reports HL/Binance and HL/OKX basis
`10000 * (external_mid / HL_mid - 1)`, reference ages, disagreement and expected /
eligible / agreeing / disagreeing / stale / missing breadth. The expected
denominator is two references. Units must already be comparable through accepted
mapping; there is no invented USDT/USDC conversion. Native E4 units without an
accepted comparable binding remain unavailable for cross-unit comparisons.
External references never repair a missing HL quote, structural bar, path,
funding settlement, fill or continuity proof.

`lead_lag` uses registered backward-ending intervals. `propagation` is a separate
matured outcome contract for quote-mid or signed known-aggressor trade impulses.
It records the first observed follower response, elapsed time, clock, censoring
and ambiguity. Simultaneous/unordered responses cannot establish a leader.
Positive-horizon labels are never FeatureObservations or policy inputs.

## Features and profiles

Arithmetic uses Decimal precision 80 with half-even rounding; finite feature wire
values use 12 decimal places. Formula, parameters, clock, units and family are
part of identity. Available zero differs from an unavailable feature with empty
values and typed reasons.

* BBO imbalance: `(bid_size - ask_size) / (bid_size + ask_size)`.
* L1 microprice: `(ask * bid_size + bid * ask_size) / total_size`.
* OFI increment: `1[b>=pb]*qb - 1[b<=pb]*pqb - 1[a<=pa]*qa + 1[a>=pa]*pqa`.
  Sum over the registered healthy window; normalized OFI divides by latest size.
* Spread/friction: absolute spread, spread/mid in bps, quote age and microprice
  displacement. Spread is explanatory when already included in bid/ask fills.
* Trades: retained native identity deduplication, signed aggressor flow, flow
  imbalance and price response. Unknown aggressor and zero volume are missing.
* Volume Profile: floor bins from registered origin and tick-aligned width;
  POC ties choose lower bin. Value area expands contiguously toward greater
  adjacent observed volume, with lower-bin ties, until the configured fraction.
  It cannot invent volume across an unobserved hole. VAL/VAH are bin edges.
  Strict local maxima are HVNs; LVNs require the full registered neighborhood.
  Width, sum-of-squared volume-share concentration, outside-area volume and
  earlier same-version POC migration retain definitions and ancestor identity.
* Failed Auction: frozen balance -> edge test -> failed candidate on causal
  return/opposing-flow/response conditions, or accepted break after registered
  dwell -> new balance. Confirmation occurs at the observation that establishes
  it. This is a research candidate state, not a fourth Setup.

BBO_TRADES and DEPTH10_OR_L2 have different identities. Optional depth accepts
only healthy retained native snapshots for bounded top-N imbalance/capacity
VWAP. Delta-only, gapped or insufficient depth remains unavailable; no capture,
reconnect or orderbook reconstruction platform is introduced. Optional depth
does not change a non-depth feature calculation.

## Policies, paths and native simulation

B EA0..EA6 use the Issue #161 requirement authority, qualified by
ISSUE_FAMILIES_B_V1 and config hash. Legacy VNEXT_G4_V1 EA meanings remain
unchanged and cannot be cast into these IDs. The registry includes current
Three Setup Champion, four #85 simple baselines, #150 L0..L6 / R0..R4 / A0..A3,
and #85 E0..E9. `replay_champion` delegates to the unchanged
PilotStrategyEvaluator/StrategyPackageManifest and continuation/kernel.

| Family | Finite causal mechanics |
|---|---|
| EA | Champion; price core; failed auction; profile; Binance; OKX; explicit composition |
| L | Original structural stop; fixed adverse; volatility multiple; timeout/no progress; structure failure; microstructure failure; registered hybrid |
| R | None; blind negative control; cooldown; fresh Setup; fresh microstructure, with valid Thesis and budgets |
| E | Fixed R; structural full; scale-out; trailing; subsequent-observation ratchet; giveback; reversal; protected reversal/retest; regime adaptation; finite continuation/state controller |
| A | None; favorable progress; pullback/retest; continuation, with winner/add/cost bounds |

Every required threshold/fraction/horizon is supplied explicitly. EA6/L6/E9/A3
require named simple-component evidence receipts; R0 receipts test wiring only.
There is no automatic full Cartesian search, ranking or promoted default.

One frozen opportunity roster precedes candidate evaluation. WAIT, PASS,
NOT_EVALUABLE, BLOCKED, nonfill and no-submit opportunities remain in the
denominator. Each candidate owns a fresh engine/state. ContextFrames bind
retained source/feature prefixes; forward calculators receive separate matured
windows. A CounterfactualPathRef preserves a suppressed snapshot and a separate
native TAKE scenario at the registered reference time using the same model,
rather than entering at a hindsight-optimal price.

The optional native boundary uses exact Nautilus 2.0.0rc5 public BacktestEngine,
the existing admitted-event catalog projection and native fill/state utilities.
A small simulation-only Strategy callback bridge executes B policy actions;
no legacy CandidateManifest is forged. The replay consumption clock is retained
admission time, while raw event/init/receive clocks remain unchanged. The
derived native copy is explicitly consumption metadata, not a raw clock repair.

Marketable arrival is after configured delay at healthy HL BBO with quote-age
and size/lot feasibility. Long buys ask/exits bid; short sells bid/exits ask.
Native fills, fees and Cache/Portfolio positions are checked and retained.
Instrument maker/taker rates must match the configured cost identity. Native
fill-model/seed assumptions match all candidates; slippage belongs to that
native model. Extra configured modeled bps are separate signed cash costs.
Passive touch is never fill. L1 queue/impact and unfinished/partial/nonfill
limitations remain explicit. No native bar execution chooses an OHLC ordering.

Path metrics separately bind trigger/fill basis, market and executable-BBO
MFE/MAE, first favorable/adverse/stop/target touch, extrema times, recovery,
censoring, bounds and ambiguity. Missing/gapped paths have null metrics.
Partial trigger bars cannot contribute pre-entry extremes. Same-time stop plus
target takes conservative stop-first and remains ambiguous; bar extrema provide
bounds, not sub-minute timing. A new trailing/structural ratchet affects only
subsequent observations. Scratch terminates an Attempt; explicit structural
invalidation/expiry terminates the Thesis. Fresh conditions and attempt/cost
budgets govern re-entry; adds cannot average into a losing state.

Net cash sums all native fill cash flows minus native fees plus signed retained
funding and explicitly additional modeled costs. Spread is not deducted twice.
Funding uses native position size at settlement, exact-venue retained rate and
mark/BBO evidence, configured profile and units. Flat exposure yields zero;
missing applicable funding yields unavailable net attribution. Net R uses the
registered initial risk denominator. Outstanding positions yield no realized
net result. No actual-user-fill/private-account import exists.

Pairs require the same opportunity/Thesis/cluster and cost identity. Incomplete
coverage remains unmatched with reasons. Summaries describe one candidate,
count Theses/clusters and retain ambiguity, cost and tail information. Attempts,
fills and candles are not independent inferential samples. No sufficiency claim
is emitted from an R0 engineering run.

## Lifecycle and validation

The order remains S0 -> S1 original edge -> S2 activation -> S3 fast loss/re-entry
-> S4 winner/exit -> S5 context/selection. S6 ML Meta-Gate is not executable.
Only S0 fixtures execute here; later-stage prerequisites are metadata.

Preregistration binds hypotheses, allowed/prohibited changes, metrics, taxonomy,
models, stopping/failure/selection rules, budgets and reserves. Material variants
must appear in the adaptivity ledger with result-informed ancestry; identical
reproductions do not consume another trial. Unknown legacy history is explicit
and cannot run a complete-claim harness. Research and engineering repair budgets
are separate.

BlockPlan uses chronological half-open DEV/OOS intervals. Purge includes actual
forward/counterfactual endpoints, whole clusters and registered residual embargo;
held-out instruments cannot enter DEV. ReserveScenario is a synthetic metadata
exercise only. Its summary-used/contaminated configurations cannot certify an
adapted version. It grants no raw access. Real sealed opening, diagnostic unlock,
pristine relabel and lockbox consumption have no implementation in B.

Summary-only output is a strict typed aggregate allowlist; raw IDs/timestamps,
extreme-event examples and diagnostics cannot be attached. Native result rows
and summaries are distinct channels. Actual future performance-data access or
certification needs a separate accepted authority/access contract.

The seven `test_research_replay_*` files cover contracts, future joins/PIT/skew,
gaps/staleness/disagreement, explicit missing/depth states, hand-computed feature
oracles and accepted raw-reader rebuild, suppressed paths, ambiguity, signed
funding, every policy family, chronology/adaptivity/firewalls and fresh-process
prefix fingerprints. The existing `test_nautilus_vnext_g4_runner.py` adds a real
R0 rc5 replay proof for delayed bid/ask fills, position isolation, paired WAIT
and matched counterfactuals. Its existing required-runtime mechanism prevents
an absent native runtime from silently passing authoritative CI.

Run the frozen Plan's focused tests, Package A and Strategy/Outcome/G4 authority
regressions, Ruff/mypy, compile, governance/schema/secret and lock checks. Local
Python/platform/environment limitations must remain explicit. Authoritative
Linux x86_64/Python3.12/rc5 CI follows Draft publication through the deterministic
exact-head waiter, without model polling. No dependency or workflow change.

Architecture/provider/dependency/security/authority questions, needed sealed
opening, indispensable Package C evidence, or inability to honor accepted A raw
contracts require CONTROL_REPLAN. This library never authorizes production
promotion, Mark Ready, merge, deletion, deployment, service/cloud changes,
credentials/private APIs, signing, exchange writes, autonomous trading or capital.
