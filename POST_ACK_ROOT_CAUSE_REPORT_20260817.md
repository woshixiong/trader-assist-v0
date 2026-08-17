# POST_ACK_LIVE_FINALITY_AND_LIFECYCLE_COHORT_FAILURE — Root Cause Report

Date: 2026-08-17 · Base: 0ac48b0264f0195242a952e96d8d974c7e0ed179 (verified == origin/main)
Reproducer: `repro_post_ack_cohort.py` (deterministic, real production control flow, no network)

## REAL_PROVIDER_CONTRACT_FINDING

Public read-only probe against live Hyperliquid (no account/private/write API):

REST `candleSnapshot` (interval 5m):
- Native (BTC, ETH) AND xyz/HIP-3 (xyz:NVDA, xyz:TSLA, xyz:XYZ100, xyz:SP500, xyz:CL,
  xyz:GOLD) all returned **strictly contiguous** slot grids.
- 6h window: 73 bars vs 72 expected full-grid slots + current partial, `gap_count=0`
  for every coin.
- 3d window: 865 bars vs 864 expected, `gap_count=0` (BTC, xyz:NVDA, xyz:XYZ100, xyz:GOLD).
- No-trade slots are **not omitted**: they appear as zero-volume flat bars
  (`v=0`, `n=0`, o=h=l=c=prev close; e.g. xyz:TSLA had 2 in 6h).
- `n` (trade count) supplied and consistent with `v`.

WS `candle` channel (130s + 300s observations, BTC + xyz:TSLA/XYZ100/SMSN/EWY/SPCX/DRAM/SILVER):
- Updates are **trade-driven only**; `n`/`v` monotone non-decreasing within a slot.
- **No boundary/heartbeat event**: BTC's first event for a newly opened slot arrived
  ~52s after slot open already carrying `n=418`; sparse coins' first event of a slot
  lagged slot open by up to minutes. A slot with zero trades emits **zero** WS events,
  hence zero finality candidates, for that boundary.

Conclusion: the provider guarantees/returns contiguous 5m slots in REST. The current
Data continuity authority (`new_open > prior_open + 5m` → gap) is CORRECT against the
provider series and must not be weakened. The false gaps observed on the host originate
from the **WS candidate path structurally omitting zero-trade boundaries**, not from
missing provider evidence.

## ROOT_CAUSE (three interacting defects, all deterministically reproduced)

### CAUSE-1 — WS-silent boundary → false "closed 5m gap" (the 15/20 mechanism)
`MultiAssetPublicRuntime._confirm_generation` only confirms boundaries that a WS
candidate nominated. A zero-trade 5m slot emits no WS event → no candidate → that
boundary is never confirmed. The market's next WS candidate then confirms with
`new_open > prior_open + 5m` → `_admit` raises `DataRouteError("closed 5m gap detected")`
→ finality FAILED → `RuntimeHealth.failed_markets.add`. The provider's REST series for
the same window IS contiguous (zero-volume flat bars), so this is
LEGITIMATE_PROVIDER_NO_BAR misclassified as REAL_MISSING_EXPECTED_EVIDENCE.
Reproduced: exactly the 15 sparse-trading xyz/HIP-3 markets fail this way; the 5
native crypto (trade every slot) never do. Explains failed=15/20 being exactly the
xyz count (Finding B) without any asset-class-specific logic, and the ~40-minute
ClosedBarStore spread (each market freezes at its last admitted boundary at its own
first skip).

### CAUSE-2 — Sticky runtime failure, no evidence-derived recovery (Finding A, verified)
`RuntimeHealth.failed_markets` is marked by finality failure but the live success path
never clears it (only warmup/reconnect paths do). `_maybe_stage_lifecycle` skips failed
markets, so one transient confirmation failure permanently blocks that market's
lifecycle. Reproduced: BTC with one transient transport error on its first live
confirmation remains HISTORY_READY through three later genuinely successful
provider-authoritative finalities (short-seed regime).

### CAUSE-3 — Lifecycle version-name chain overflow crashes the confirmer
`_maybe_stage_lifecycle` builds `f"{active.version}-lifecycle-{suffix}"` and stages it
via `lifecycle_successor` → `RegistryVersion.create` (`version` max_length=80). With the
realistic First-Launch seed name (31 chars, matching `release/first-launch-manual-20-20260817`),
the ACTIVE-stage name is 97 chars → pydantic `ValidationError` (a `ValueError`, NOT
`RegistryError`) escapes the `except RegistryError` guard, propagates into
`GenerationFinalityAuthority._run_market`'s `except Exception` → the innocent
confirming market is marked FAILED. Every later confirmer repeats this.
Baseline reproducer (verified 2026-08-17, 31-char seed, one batch per stage):
lifecycle froze at `{'HISTORY_READY': 1, 'SNAPSHOT_READY': 19}`, `failed_markets=20/20`,
`ready=0/20`, ClosedBarStore spread 4 slots. A seed ≥32 chars — or one extra chain hop
from split batching — overflows one stage earlier (SNAPSHOT_READY staging) and freezes
the cohort at HISTORY_READY 20/20 with `pending=NONE`: exactly the host-observed
stage. The exact host seed/batching is not recoverable from here; both regimes are the
same defect and no repair decision depends on the distinction.

## WHY_15_OF_20_FAILURE_OCCURRED
15 = the xyz/HIP-3 cohort size. Sparse Sunday-session trading ⇒ zero-trade 5m slots ⇒
CAUSE-1 false gaps at each such market's next confirmation ⇒ sticky CAUSE-2 failures.
Native crypto trade continuously ⇒ never skipped ⇒ never falsely gapped.

## WHY_LIFECYCLE_STOPPED_AT_HISTORY_READY
The batched lifecycle ladder requires: no pending version, eligible (non-failed)
markets, a valid successor version name, and an admitted bar to flip the pointer.
CAUSE-1/2 progressively remove markets; CAUSE-3 makes the batched staging itself
crash and additionally fails the confirming market. No staging beyond the first
survives ⇒ cohort never reaches SNAPSHOT_READY/ACTIVE ⇒ readiness ready=0 ⇒
Scanner/Strategy whole-cohort gate correctly stayed closed.

## EXACT_REPAIR_SCOPE (bounded)

1. `runtime.py` — `_confirm_generation`: before confirming a live candidate whose
   open time jumps past `last_open + 5m`, admit the provider's own REST series for
   the intervening boundaries (`admit_rest_history`, bounded by the warmup window).
   Zero-trade slots arrive as provider zero-volume flat bars (legitimate provider
   evidence); a genuine provider omission still fails closed in the unchanged gap
   check. Continuity authority semantics unchanged.
2. `runtime.py` — evidence-derived, market-scoped recovery: a successful
   provider-authoritative confirmation clears a runtime finality failure for that
   market ONLY IF the Data authority holds no failure for it and its durable 5m
   series is exactly contiguous. No broad `failed_markets.clear()`. Data gaps,
   conflicts, Registry/metadata/callback failures are never cleared by this path.
3. `runtime.py` — bounded non-durable operator diagnostics: per-market latest
   failure record (market/coin, boundary, stage, category, recoverable
   classification) in `RuntimeHealth`; no DB/table/queue/platform.
4. `runtime.py` — `_maybe_stage_lifecycle`: the chained version name is now built by
   `_lifecycle_version_name()`: the readable chain while it fits the
   RegistryVersion 80-char bound, then a bounded deterministic compression
   (stable predecessor head + 8-hex predecessor-hash tag + suffix; uniqueness
   still enforced fail-closed by the registry's exists-check). The staging guard
   now also contains `ValueError` (pydantic schema rejection) so a control-plane
   or schema failure can never again crash a finality confirmation.

Out of scope (unchanged): finality.py semantics (WS=candidate, REST=authority,
TARGET_CONFIRMATIONS=2, hold, gap, supersession, concurrency=4), data.py continuity
authority, registry authority model, readiness/strategy identity, hyperliquid_public.py.

## Verified post-repair cohort behavior (reproducer + acceptance tests)

Baseline (unrepaired runtime) vs repaired runtime, same deterministic 20-market fixture
(15 xyz WS-silent in slot 1, one BTC transient confirmation failure, one genuine
xyz:SP500 provider omission), production-length seed:

| metric | baseline | repaired |
|---|---|---|
| lifecycle | frozen `SNAPSHOT_READY:19 / HISTORY_READY:1` (never ACTIVE) | Initial-Launch convergence holds the whole cohort PRE_ACTIVE while any selected member is failed; ACTIVE_COUNT is only ever 0 or 20 (never 19/20) |
| health failed | 20/20 | 1/20 (xyz:SP500 only) |
| Data authority failed | 16/20 (15 false gaps + 1 genuine) | 1/20 (genuine only) |
| ready markets | 0/20 | 0/20 during First Launch (see FINAL CONVERGENCE DESIGN below) |
| ClosedBarStore spread | 4 slots | 0 slots among the 19 healthy |
| finalized boundaries | 10 | 62 |

BTC's transient failure recovers at its next provider-authoritative success; the 15
WS-silent xyz boundaries are admitted from the provider's own REST flat bars; SP500's
genuine omission stays fail-closed; every lifecycle activation still flows through
Closed5mAdmission. Durable acceptance lives in
`tests/test_post_ack_finality_lifecycle_repair.py`.

## FINAL CONVERGENCE DESIGN (invariant-based; supersedes the Repair-3 approximation)

The final holistic review stopped the example-by-example repair loop and confirmed
the architecture (Registry → Data Authority → Generation Finality → Runtime →
Bootstrap → production composition) is sound. The residual defects were two
cross-layer state-machine contracts implemented as local approximations:

- Repair-3 approximated First-Launch atomicity as "zero ACTIVE ⇒ stage only if
  every cohort member has an update", which (a) defined First Launch as
  `ACTIVE_COUNT == 0` — misclassifying a post-live DRAINING cohort as a new
  launch — and (b) allowed one batch to advance different markets different
  numbers of stages.
- Repair-3 made Bootstrap defer operational non-readiness but left the
  integrity-vs-operational ordering implicit, so operational conditions could be
  evaluated before observable integrity contradictions.

Both are now implemented as explicit invariants. No authority changed: no new
durable state, table, queue, service, or dependency; every activation still flows
exclusively through `Closed5mAdmission → MarketRegistryManager._apply_admitted()`.

### FINAL INVARIANT A — First-Launch cohort atomic ACTIVE authority

`runtime.plan_lifecycle_updates` is a PURE deterministic planner (no durable
state, never a second authority): it maps immutable cohort lifecycles plus
failure/history/snapshot evidence to one batch of one-step legal
`Registry._LIFECYCLE_NEXT` transitions.

- PRE_ACTIVE = exactly {WARMING, HISTORY_READY, SNAPSHOT_READY}, ranked
  WARMING < HISTORY_READY < SNAPSHOT_READY.
- Initial-Launch convergence mode holds iff EVERY selected non-terminal member
  is PRE_ACTIVE (hence no ACTIVE member). It is NOT defined as
  `ACTIVE_COUNT == 0`: a post-live cohort containing DRAINING or any post-ACTIVE
  member uses hot-add semantics and can never re-enter First Launch.
- While in Initial-Launch convergence: ACTIVE_COUNT ∈ {0, N}. No reachable
  successor has 1 ≤ ACTIVE_COUNT ≤ N-1.
- Reconciliation: any failed launch member holds the whole cohort (no update).
  Otherwise only the markets at the MINIMUM PRE_ACTIVE stage advance, each by
  exactly one legal transition; markets already ahead remain unchanged.
  WARMING→HISTORY_READY requires unanimous current authoritative history for the
  advancing group; HISTORY_READY→SNAPSHOT_READY requires snapshot readiness;
  SNAPSHOT_READY→ACTIVE is reachable only when SNAPSHOT_READY is the minimum
  stage — i.e. the exact launch cohort is coherently SNAPSHOT_READY — so the
  final activation is always ALL selected launch markets together. N is cohort
  size, never hard-coded.
  Example: 19 SNAPSHOT_READY + 1 HISTORY_READY becomes 20 SNAPSHOT_READY before
  20 ACTIVE, never 19 ACTIVE + 1 SNAPSHOT_READY. 5/7/8 mixed starts converge
  monotonically 12/8 → 20 SNAPSHOT_READY → 20 ACTIVE.
- Post-launch (any ACTIVE or post-ACTIVE member exists): accepted hot-add
  behavior is preserved — markets progress independently and a failed future
  member never pauses the already-live cohort.

### FINAL INVARIANT B — Bootstrap gate precedence

`bootstrap._boundary_markets` classifies each boundary under an explicit
precedence: INTEGRITY ERROR > OPERATIONAL DEFER > ACTION.

- PHASE 1 (integrity, fail-closed raise): readiness Registry version or content
  hash contradicting the active Registry; requested boundary contradicting the
  runtime's authoritative latest closed boundary; any PRESENT required retained
  5m boundary row bound to the wrong Registry version/content hash. These are
  checked FIRST: a failed peer, `data_ready=False`, incomplete readiness, or a
  zero-ACTIVE cohort must never hide an observable integrity contradiction.
- PHASE 2 (operational defer, only after available integrity evidence is
  coherent): zero actionable ACTIVE cohort (Initial Launch), `data_ready=False`,
  failed required peer, missing required boundary row (a MISSING row is
  operational non-readiness, never an integrity contradiction), incomplete
  `ready_market_ids` — all defer the whole cohort
  (`DEFERRED_WAITING_FOR_PEERS`) without cascading an application failure onto
  healthy markets.
- PHASE 3: only a complete coherent cohort enters Scanner/Strategy.

### Acceptance method (state machine first, then composition)

- LAYER 1 — `tests/test_first_launch_lifecycle_convergence.py`: exhaustive
  finite-state proof of the pure planner. N=3 synthetic cohort, all 27 PRE_ACTIVE
  configurations × failed/healthy × snapshot_ready true/false × WARMING
  history-currency: every transition is one legal `_LIFECYCLE_NEXT` step, only
  the minimum stage moves, no 1..N-1 ACTIVE successor exists, a failed cohort
  never advances, repeated reconciliation converges monotonically to all ACTIVE,
  and a DRAINING (zero-ACTIVE) control never re-enters First-Launch semantics.
- LAYER 2 — `tests/test_post_ack_whole_cohort_composition.py` precedence matrix:
  coherent failed peer → DEFER; failed peer + PRESENT wrong-bound retained row →
  `BootstrapIntegrityError`; coherent zero-ACTIVE launch → DEFER; zero ACTIVE +
  readiness Registry version/hash mismatch → `BootstrapIntegrityError`; zero
  ACTIVE + authoritative boundary contradiction → `BootstrapIntegrityError`;
  missing required boundary → DEFER; incomplete ready set with coherent
  authority (stale beyond the 60s action ceiling) → DEFER. Integrity always
  dominates operational defer.
- LAYER 3 — real production composition (`Runtime → planner →
  Registry.lifecycle_successor → request_apply → real Closed5mAdmission`):
  (A) mixed 5 WARMING / 7 HISTORY_READY / 8 SNAPSHOT_READY start converges
  12/8 → 20 SNAPSHOT_READY → 20 ACTIVE with ACTIVE_COUNT only 0 or N after
  every applied successor; (B) recoverable failure holds at 0 ACTIVE until
  genuine evidence-derived recovery, then converges to N ACTIVE; (C)
  nonrecoverable failure keeps ACTIVE_COUNT 0; (D) failed/healthy hot-adds never
  pause an existing ACTIVE cohort; (E) failed peer → Bootstrap defer → Scanner 0
  → Strategy 0, no callback cascade onto the healthy triggering market; (F)
  failed peer + wrong PRESENT Registry-bound row raises; (G) the exact-cohort
  one-Scanner/whole-Strategy/duplicate-reuses-retained-authority proof.

### Retained from the earlier repairs (verified unchanged)

1. `runtime.py` `_maybe_stage_lifecycle` — the planner above is the only staging
   decision path; it still stages through `lifecycle_successor` +
   `request_apply` and activates only via genuine `Closed5mAdmission`. The
   staging guard still contains `ValueError` so control-plane/schema failures
   can never crash a finality confirmation; lifecycle version names remain
   bounded by `_lifecycle_version_name`.
2. `bootstrap.py` `_boundary_markets` — the phase ordering above replaces the
   defer-not-cascade approximation with the same fail-closed outcome for true
   integrity breaks and `DEFERRED_WAITING_FOR_PEERS` for expected peer
   non-readiness.
3. `runtime.py` `_confirm_generation` — an unexpected exception inside the
   current finality generation is recorded as `stage=finality_unknown`,
   `recoverable=False`, escalating over any stale recoverable record
   (`test_unknown_finality_failure_escalates_over_stale_recoverable_record`).
   `GenerationFinalityAuthority`'s defensive fail-closed catch is unchanged.
