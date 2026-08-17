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
| lifecycle | frozen `SNAPSHOT_READY:19 / HISTORY_READY:1` (never ACTIVE) | `ACTIVE: 20` |
| health failed | 20/20 | 1/20 (xyz:SP500 only) |
| Data authority failed | 16/20 (15 false gaps + 1 genuine) | 1/20 (genuine only) |
| ready markets | 0/20 | 19/20 (SP500 correctly excluded) |
| ClosedBarStore spread | 4 slots | 0 slots among the 19 healthy |
| finalized boundaries | 10 | 62 |

BTC's transient failure recovers at its next provider-authoritative success; the 15
WS-silent xyz boundaries are admitted from the provider's own REST flat bars; SP500's
genuine omission stays fail-closed; every lifecycle activation still flows through
Closed5mAdmission. Durable acceptance lives in
`tests/test_post_ack_finality_lifecycle_repair.py` (7 tests).
