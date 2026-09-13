# Trader Assist / Trade OS — Trading Behavior Active Experiment Baseline — Week Beginning 2026-09-14

**Status:** ACTIVE USER-DIRECTED PROVISIONAL BEHAVIOR BASELINE  
**Effective week:** 2026-09-14 through the next weekly review  
**Normative review owner:** `governance/TRADING_BEHAVIOR_AND_EDGE_REVIEW_PROCEDURE_V1_2026-09-06.md`  
**Scope:** prospective behavior-control and evaluation baseline for the user's manual/discretionary trading practice.

This file is a dated experiment baseline, not a new project-wide authority. It is subordinate to Unified Engineering Governance V2 and the Trading Behavior and Edge Review Procedure. It grants no strategy authority, sizing authority, exchange-write authority, order-submission authority, or autonomous-trading authority.

All rules and thresholds below are:

```text
PROVISIONAL_RULE
```

They are selected for **simple, fast, repeatable human execution** during live discretionary trading. They are not claimed to be mathematically optimal trading parameters.

For the week beginning 2026-09-14, this dated baseline supersedes the earlier week-beginning-2026-09-07 behavioral experiment baseline only for current-week compliance evaluation. The earlier baseline remains historical evidence for week-over-week comparison.

---

## 1. Primary operating objective

The current practice objective is:

```text
SMALL PRACTICE SIZE
-> SELECTIVE ENTRY
-> FAST SMALL LOSS WHEN WRONG
-> FLAT
-> FRESH-TRIGGER RE-ENTRY IF THE THESIS REVALIDATES
-> HOLD GENUINE WINNERS
```

The user explicitly prioritizes a rule set that can be executed quickly and consistently over a slower per-trade workflow that requires detailed structure-stop, volatility, position-size, and leverage calculation before every entry.

This simplification is an execution choice for the current practice phase, not evidence that structure/volatility-based sizing is inferior in theory.

---

## 2. Loss-control rule — `PROVISIONAL_RULE`

Maintain the prior week's reduced practice-size regime; no private account size or exact live position-sizing data is stored in GitHub.

Current target:

```text
TARGET_NORMAL_REALIZED_LOSS <= approximately $0.20
```

Operational behavior:

```text
IF A NEW POSITION MOVES ADVERSELY:
    EXIT QUICKLY
    DO NOT DELIBERATELY HOLD LONGER MERELY TO AVOID BEING STOPPED OUT

IF THE ORIGINAL THESIS LATER REVALIDATES:
    REMAIN FLAT UNTIL A NEW QUALIFIED ENTRY TRIGGER EXISTS
    THEN A NEW SAME-DIRECTION ATTEMPT IS ALLOWED
```

Hard prohibitions:

```text
HOLDING / FIGHTING A LOSER = PROHIBITED
ADVERSE-DIRECTION ADD = PROHIBITED
AVERAGING DOWN = PROHIBITED
ADDING TO A LOSING POSITION TO IMPROVE ENTRY PRICE = PROHIBITED
```

The approximately `$0.20` target is a behavioral experiment threshold, not a proven optimal market stop. Normal fee/slippage noise may move an otherwise compliant exit slightly around the threshold; the weekly review should evaluate intended process and exact after-fee result separately where evidence permits.

---

## 3. Entry meta-gate — `PROVISIONAL_RULE`

Before every new entry, require six simple checks:

```text
STATE
LEVEL
SETUP
TRIGGER
INVALIDATION
ROOM
```

Definitions:

- `STATE` — attention and reaction quality are acceptable, and the market is not inside a prohibited opening/macro/no-consensus regime below.
- `LEVEL` — the relevant trading area/level was identified before entry; do not invent the level after price has already moved.
- `SETUP` — the trader can state in one short sentence why this location/direction is worth attempting.
- `TRIGGER` — the required confirmation has actually occurred; "almost there" is not a trigger.
- `INVALIDATION` — the trader knows what development would make the current attempt wrong. This may be qualitative for speed; no detailed volatility/position-size calculation is required by this experiment.
- `ROOM` — there is still enough plausible room before the next major opposing level/obstacle to justify the attempt after expected friction; no fixed reward/risk number is imposed by this experiment.

Decision rule:

```text
ALL SIX = YES -> TAKE MAY BE CONSIDERED
ANY ONE != YES -> WAIT OR PASS
```

Explicitly prohibited entry logic:

```text
"PRICE IS CLOSE ENOUGH; ENTER FIRST AND SEE"
"THE STOP IS CHEAP, SO TRY IT ANYWAY"
```

The weekly review should use user annotation and/or market-path evidence before classifying an entry as low quality; fills alone do not prove setup quality.

---

## 4. Market-regime protection — `PROVISIONAL_RULE`

Hard no-new-entry windows for the current week:

```text
KOREA CASH OPEN FIRST 15 MINUTES = NO TRADE
US CASH OPEN FIRST 15 MINUTES = NO TRADE
TIER-1 MACRO RELEASE FIRST 15 MINUTES = NO TRADE
```

After these windows expire, trading does not resume automatically. A valid `LEVEL + SETUP + TRIGGER + INVALIDATION + ROOM` still must exist.

Additional regime filter:

```text
HIGH VOLATILITY + TWO-WAY CHAOS + NO CLEAR CONSENSUS = PASS
```

Do **not** interpret this as a ban on high volatility itself. High volatility with a clear directional structure/trend may be valuable; the prohibited condition is high volatility combined with unresolved two-way price discovery and weak directional consensus.

The exact Korea/US cash open and Tier-1 release timestamps remain governed by the canonical timezone/calendar rules in the Trading Behavior and Edge Review Procedure.

---

## 5. Mental-state gate — `PROVISIONAL_RULE`

No new discretionary entries when any of the following is materially present:

```text
FATIGUE
ATTENTION / CONCENTRATION LOSS
SLOWER REACTION SPEED
EMOTIONAL AGITATION OR IMPULSIVITY
```

Late-night Beijing-time trading is a heightened-risk context because fatigue/attention degradation has already produced user-identified process failures. This experiment does not create a blanket clock-time ban independent of state; it creates a hard **state-quality gate**.

If state quality is poor, the correct action is:

```text
STOP LOOKING FOR A NEW TRADE IN THAT SESSION
```

A seemingly attractive opportunity is not an exception.

---

## 6. Re-entry rule — `PROVISIONAL_RULE`

A fast stop does not automatically invalidate the broader directional thesis.

However:

```text
STOPPED OUT
!=
IMMEDIATE RETRY AUTHORITY
```

A same-direction re-entry requires a **fresh qualified trigger** and a new pass through the entry meta-gate. Re-entry based only on "the previous trade was probably just shaken out" is prohibited.

The fixed `10-minute` post-`>$0.50` cooldown from the week-beginning-2026-09-07 experiment remains a historical experimental parameter and may still be reported for comparability. It is **not the primary current-week re-entry gate** unless explicitly reactivated by later user authority. The active gate for this week is fresh-trigger revalidation plus the state/regime controls above.

---

## 7. Winner management — `PROVISIONAL_RULE / TEST_MORE`

Do not introduce a new fixed small take-profit merely to increase win rate.

Current behavior remains:

```text
IF A POSITION BECOMES A GENUINE WINNER:
    ATTEMPT TO HOLD THE TREND
    EXIT WHEN THE TRADER OBSERVES MATERIAL TREND EXHAUSTION / REVERSAL
```

Winner-exit quality remains an observation target. Without sufficient market-path evidence, do not conclude that a winner was exited too early or too late.

The weekly review must preserve the project objective of protecting right-tail winners while reducing left-tail losses.

---

## 8. Current-week success criteria

The next weekly review should evaluate this baseline using the canonical episode-level after-fee accounting and evidence labels in the Trading Behavior and Edge Review Procedure.

Primary behavioral checks:

```text
ADVERSE_DIRECTION_ADD_COUNT -> TARGET 0
USER_ANNOTATED_HOLD_LOSS / FIGHTING_LOSER_EVENTS -> TARGET 0
OPENING_FIRST_15M_NEW_ENTRY_VIOLATIONS -> TARGET 0
TIER1_RELEASE_FIRST_15M_NEW_ENTRY_VIOLATIONS -> TARGET 0
STATE_IMPAIRED_TRADING_EVENTS -> TARGET 0
```

Primary improvement checks:

```text
NORMAL_LOSS_SIZE MOVES TOWARD APPROXIMATELY $0.20 OR BELOW
TRADES_PER_DAY DECREASES
FEES DECREASE OR DO NOT RISE THROUGH OVERTRADING
LOW-INFORMATION / UNCONFIRMED ENTRIES DECREASE
BLIND RAPID SAME-DIRECTION RETRIES DECREASE
RIGHT-TAIL WINNER CAPTURE IS NOT INTENTIONALLY COMPRESSED
```

Canonical weekly metrics from the parent procedure remain required, including net PnL, PF, expectancy, win rate, payoff, fees, average loss, `>$0.50` and `>$1.00` losses, rapid re-entry, opening-regime PF, winner duration, and loser duration.

Do not declare this baseline successful or failed from weekly PnL alone. Distinguish:

```text
BEHAVIOR IMPROVEMENT
STRATEGY / ENTRY-EDGE IMPROVEMENT
MARKET-REGIME EFFECT
RANDOM VARIANCE
INSUFFICIENT EVIDENCE
```

---

## 9. Privacy and authority boundary

Do not commit to GitHub:

- raw fills or order-history exports;
- public account/wallet addresses tied to the user's trading history;
- private keys, API credentials, signing material, or account secrets;
- screenshots containing private account information;
- exact private account equity/position records unless independently sanitized and explicitly authorized.

This file stores only the prospective behavioral rules and evaluation criteria needed for reproducible future review.
