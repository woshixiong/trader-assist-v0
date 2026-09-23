# Trader Assist / Trade OS — Trading Behavior and Edge Review Procedure V1

**Status:** TASK-CONDITIONAL PROCEDURE CANDIDATE  
**Effective date:** 2026-09-06  
**Normative owner:** `ENGINEERING_GOVERNANCE_V4_CONSOLIDATED_FINAL.md`
**Scope:** recurring review of the user's discretionary/manual trading behavior and edge from official trade records plus approved market-path evidence.

This is a narrow research/review procedure. It does **not** create trading authority, strategy authority, exchange-write authority, sizing authority, or autonomous-trading authority. It does not replace current Product / Strategy / Risk decisions. When this procedure conflicts with a newer explicit user instruction or a current accepted domain authority, the newer/higher authority governs.

The purpose is continuity: a future review window should be able to read this file and reproduce the same analytical framework instead of relying on chat memory.

---

## 1. Core objective

The recurring review must answer four questions separately:

1. **Is the underlying trading method showing a positive or improving edge?**
2. **Which execution/behavior errors are contaminating that edge?**
3. **Which market regimes increase the probability of those errors?**
4. **Which changes improve after-fee expectancy without destroying the right-tail winners?**

Do not reduce the review to weekly PnL alone.

Primary optimization target:

```text
AFTER_FEE_EXPECTANCY
= WIN_RATE × AVG_WIN
- LOSS_RATE × ABS(AVG_LOSS)
```

Win rate, payoff ratio, frequency, fees, tail losses, and behavior violations must be analyzed together.

---

## 2. Evidence hierarchy

Use the strongest available evidence in this order:

1. official Hyperliquid fills / official account trade export;
2. official Hyperliquid market-path data captured by the project;
3. official macro/event release calendars for exact event timestamps;
4. user-provided screenshots/notes for contextual annotation;
5. third-party visualization only as supplementary evidence.

Never treat screenshots or third-party calendars as accounting authority when official fills are available.

Do not commit raw private/account data, real account identifiers, trade CSVs, production DBs/logs, wallet material, or credentials to GitHub.

---

## 3. Time normalization and trading-day boundary

Canonical analytical timezone:

```text
UTC+08:00
```

All source timestamps must be explicitly converted before session analysis. Do not silently interpret UTC exports as local time.

Canonical discretionary trading day for weekly behavior grouping:

```text
08:00 UTC+08:00
through
07:59:59 UTC+08:00 on the following calendar day
```

This groups the Korea session, Europe/US preparation, US session, and late-night continuation into one behavioral trading day.

US market-open timestamps must be resolved from the actual US exchange calendar for the date and then converted to UTC+08:00. Do **not** hardcode 21:30 for the entire year because US daylight-saving transitions change the UTC+08:00 open time.

Korea open should likewise be resolved from the actual exchange calendar when holiday/exception handling matters; the normal KRX open maps to 08:00 UTC+08:00.

Macro release timestamps must come from official release calendars and be converted to UTC+08:00. Do not assume every important release occurs at 20:30.

---

## 4. Trade reconstruction

Primary research unit:

```text
FLAT_TO_FLAT_POSITION_EPISODE
```

Reconstruct chronologically per market/coin.

Must support:

- single-fill entry and exit;
- multiple entry fills;
- partial exits;
- multiple exit fills;
- long and short;
- scratch and re-entry;
- pyramiding;
- adverse-direction adding.

For each episode calculate at minimum:

```text
entry_time
exit_time
market
side
entry_vwap
exit_vwap
entry_notional
peak_position_notional_if_available
duration
fees
net_pnl
net_pnl_bps
```

Do not assume one open row plus one close row equals one complete trade.

Official export semantics must be checked before fee arithmetic. Never double-subtract fees when the provider's `closedPnl` field already includes them.

### 4.1 Canonical accounting basis

All recurring canonical edge and behavior metrics in this procedure **always use episode-level after-fee PnL**. Provider-specific source semantics may change only how that after-fee episode PnL is reconstructed from source fields; they may not change the canonical accounting basis within an individual review.

If verified source semantics are insufficient to reconstruct after-fee `EPISODE_NET_PNL` without fee omission or double counting, the affected canonical accounting metrics must be reported as `UNKNOWN` or `NOT_APPLICABLE` as appropriate. A different recurring accounting basis requires a versioned procedure change; it cannot be introduced by a one-off review note or provider-specific exception.

Canonical definitions:

```text
EPISODE_NET_PNL
= realized flat-to-flat episode PnL after fees,
  with fees deducted exactly once according to verified provider semantics

EPISODE_FEES
= fees attributable to the complete flat-to-flat episode

GROSS_PRICE_PNL
= EPISODE_NET_PNL + EPISODE_FEES
  only when both components are verified and this arithmetic exactly reverses
  the fee deduction used to produce EPISODE_NET_PNL;
  otherwise UNKNOWN or NOT_APPLICABLE

REALIZED_LOSS
= max(-EPISODE_NET_PNL, 0)

WIN
= EPISODE_NET_PNL > 0

LOSS
= EPISODE_NET_PNL < 0

SCRATCH
= EPISODE_NET_PNL == 0
```

Do not silently introduce a PnL zero-tolerance or rounding band. If the source export requires a non-zero scratch tolerance because of documented quantization/rounding behavior, that tolerance must be stated explicitly in the review and requires a versioned procedure change before it becomes a recurring canonical definition.

`net_pnl_bps` is calculated from `EPISODE_NET_PNL / entry_notional × 10,000` when `entry_notional > 0`; otherwise it is `NOT_APPLICABLE` rather than guessed.

All dollar loss thresholds in this procedure, including `>$0.25`, `>$0.50`, and `>$1.00`, always refer to `REALIZED_LOSS` on this canonical after-fee episode basis.

---

## 5. Mandatory weekly scorecard

Every complete weekly review must report, for the full week and relevant subgroups:

### Accounting / friction

- net PnL;
- gross/pre-fee price PnL where derivable;
- fees;
- fee / gross-profit ratio;
- turnover;
- daily PnL.

### Edge

- trade count;
- win rate;
- Profit Factor;
- expectancy per episode;
- average winner;
- average loser;
- payoff ratio;
- break-even win rate implied by current payoff.

Canonical metric formulas use the after-fee episode basis from §4.1:

```text
WIN_RATE
= count(WIN) / count(complete episodes)

AVG_WIN
= mean(EPISODE_NET_PNL for WIN episodes)

AVG_LOSS
= mean(EPISODE_NET_PNL for LOSS episodes)

PROFIT_FACTOR
= sum(positive EPISODE_NET_PNL)
  / abs(sum(negative EPISODE_NET_PNL))

PAYOFF_RATIO
= AVG_WIN / abs(AVG_LOSS)

EXPECTANCY_PER_EPISODE
= mean(EPISODE_NET_PNL)

BREAK_EVEN_WIN_RATE
= abs(AVG_LOSS) / (AVG_WIN + abs(AVG_LOSS))
```

Profit Factor edge cases use this deterministic precedence:

```text
IF count(WIN) == 0 AND count(LOSS) == 0:
    PROFIT_FACTOR = NOT_APPLICABLE/NO_WIN_OR_LOSS_POPULATION
ELSE IF count(WIN) >= 1 AND count(LOSS) == 0:
    PROFIT_FACTOR = INF/NO_LOSSES
ELSE IF count(WIN) == 0 AND count(LOSS) >= 1:
    PROFIT_FACTOR = 0/NO_WINS
ELSE:
    PROFIT_FACTOR = canonical formula above
```

For `WIN_RATE`, zero complete episodes yields `NOT_APPLICABLE/NO_EPISODES`; an all-scratch non-empty subgroup has `WIN_RATE=0`. `AVG_WIN` and `AVG_LOSS` are `NOT_APPLICABLE` when their respective populations do not exist. `EXPECTANCY_PER_EPISODE` is `NOT_APPLICABLE` for zero complete episodes and equals `0` for an all-scratch non-empty subgroup. `PAYOFF_RATIO` and `BREAK_EVEN_WIN_RATE` are `NOT_APPLICABLE` when their required winner/loss populations do not exist. Scratch episodes remain in the denominator of `WIN_RATE` and complete-episode expectancy; they are not silently reclassified as wins or losses.

Gross/pre-fee metrics may be reported as secondary friction diagnostics, but must not replace the after-fee canonical edge metrics.

### Distribution / tail risk

- median winner and loser;
- largest winner and loser;
- max consecutive losses;
- max trade-sequence drawdown;
- top-1 / top-3 / top-5 / top-10 winner concentration;
- loss contribution from `>$0.25`, `>$0.50`, and `>$1.00` losers.

### Holding behavior

- winner median duration;
- loser median duration;
- duration by loss-size bucket;
- duration by winner-size bucket.

---

## 6. Session and regime analysis

Do not compare SKHYNIX and MU in isolation without controlling for session. The minimum useful segmentation is:

```text
MARKET × SESSION × SIDE × EVENT_REGIME
```

The user's current behavior is session-dependent: SKHYNIX is primarily traded during the Asia/Korea daytime session; MU is more heavily traded during US hours. Raw market-level PnL therefore contains session confounding.

### 6.0 Deterministic episode assignment and boundaries

For recurring subgroup statistics, each flat-to-flat episode has one primary timestamp:

```text
PRIMARY_ASSIGNMENT_TIME = entry_time
```

`entry_time` is the timestamp at which the position first departs from flat; `exit_time` is the timestamp at which that episode finally returns to flat.

All recurring session/event windows use **half-open intervals**:

```text
[start_time, end_time)
```

The exact start belongs to the window; the exact end belongs to the following window. This rule prevents boundary double counting.

An episode that begins in one window and exits in another remains assigned to the window containing `entry_time` for the primary scorecard. If exposure across a later boundary is analytically material, it may also receive a separate `SPAN_EVENT_EXPOSURE=YES` or `SPAN_SESSION_BOUNDARY=YES` annotation, but that exposure flag must not duplicate the episode in primary subgroup totals.

Intersections and unions must operate on stable episode IDs under these same predicates. A deduplicated union counts each episode once.

### 6.1 Korea Opening Regime

Define relative to the actual KRX cash-equity open for that date:

```text
KOREA_OPEN_0_15M
= [KRX_OPEN, KRX_OPEN + 15m)

KOREA_OPEN_15_60M
= [KRX_OPEN + 15m, KRX_OPEN + 60m)

KOREA_POST_OPEN
= [KRX_OPEN + 60m, ACTUAL_KRX_CASH_CLOSE)
```

Entries outside the actual KRX cash session are not silently assigned to `KOREA_POST_OPEN`.

At minimum report:

- trades;
- win rate;
- net PnL;
- PF;
- average winner/loss;
- `>$0.50` loss rate;
- process-violation rate;
- rapid re-entry rate.

The current working hypothesis is that the Korea open has fast two-way volatility, frequent wicks/liquidity sweeps, and an initial direction that may not represent the later Korea-session direction. This remains a **hypothesis** until market-path data can measure it directly.

### 6.2 US Opening Regime

Define relative to the actual US cash-equity open and close for that date:

```text
US_OPEN_0_15M
= [US_CASH_OPEN, US_CASH_OPEN + 15m)

US_OPEN_15_60M
= [US_CASH_OPEN + 15m, US_CASH_OPEN + 60m)

US_POST_OPEN
= [US_CASH_OPEN + 60m, ACTUAL_US_CASH_CLOSE)
```

Entries outside the actual US cash session are not silently assigned to `US_POST_OPEN`.

The first 15 minutes must always be reported separately from the rest of the first hour.

### 6.3 Macro Event Regime

Macro events are regimes, not directional signals.

For each Tier-1 event, resolve the exact official release timestamp `T0` in UTC+08:00 and use these canonical analytical windows unless a future version explicitly changes them:

```text
EVENT_RELEASE
= [T0, T0 + 15m)

POST_RELEASE_PRE_OPEN
= [T0 + 15m, US_CASH_OPEN)
  only when T0 < US_CASH_OPEN and the interval is non-empty

MACRO_US_OPEN
= [US_CASH_OPEN, US_CASH_OPEN + 60m)
  on a trading day classified as a material macro-event day

INTRASESSION_RELEASE
= descriptive event flag when T0 occurs inside the active US cash session;
  the release-local entry window remains EVENT_RELEASE
```

The 15-minute `EVENT_RELEASE` interval is a reproducible analytical bucket, not a claim that the market effect ends after 15 minutes. `MACRO_US_OPEN` is intentionally separate because the user's behavior often shifts at the later cash open even when the release itself occurred earlier.

Examples include employment/NFP, CPI, PCE, FOMC, GDP, JOLTS, ISM, and other events the current strategy/review authority classifies as material.

Do not infer direction from the economic surprise alone. The review must compare the user's actual entries with actual price action.

The key interaction term is:

```text
MACRO_DAY × US_OPEN
```

because the user's current behavior is usually to avoid the exact release moment but attempt to trade the larger move after the US open.

### 6.4 Overlap handling

Session and event regimes overlap. Never add their standalone losses as if they were independent.

Every counterfactual removing multiple error classes must use the **deduplicated union** of affected episode IDs under the canonical `entry_time` assignment rules in §6.0.

Always report:

```text
standalone subgroup result
intersection result
union result
```

when material overlap exists.

If an episode was entered before a release/open and merely remained open across it, report that separately as span exposure rather than silently reclassifying its entry into the later event/session subgroup.

---

## 7. Behavioral-risk analysis

### 7.1 Hold-loss / stop-discipline proxy

Until exact market-path/manual annotation is available, use the following **conservative diagnostic proxy**, not psychological ground truth:

```text
HOLD_LOSS_PROXY =
realized_loss > $0.50
AND episode_duration >= 5 minutes
```

`realized_loss` means the after-fee `REALIZED_LOSS` defined in §4.1.

Track:

- count;
- total loss;
- percentage of gross losses;
- rate by session/regime;
- overlap with Korea Open, US Open, and Macro × US Open.

If user annotation identifies a stop-discipline violation that the proxy misses, preserve the manual annotation separately rather than silently changing the historical proxy.

### 7.2 Process violation

Current review classification:

```text
REALIZED_LOSS > $0.50
= PROCESS_VIOLATION_CANDIDATE
```

This threshold is a behavior-control diagnostic, not a claim that $0.50 is an optimal market stop.

Track the performance of the next trade after a process violation and the time until that next entry.

### 7.3 Rapid re-entry

Define:

```text
RAPID_REENTRY = next entry <= 5 minutes after prior episode exit
```

Break down by:

- prior result win/loss;
- same market vs different market;
- same side vs opposite side;
- session/regime;
- fresh trigger YES/NO/UNKNOWN when annotation or market-path evidence exists.

Do not automatically call every rapid re-entry emotional. Fills alone cannot prove motive. The review should identify statistically weak rapid-reentry groups and then use market-path/user annotation to distinguish valid fresh-trigger re-entry from emotional retry.

### 7.4 Adverse-direction add vs winner pyramiding

Classify adds conservatively using fill/position evidence.

Current behavioral rule to evaluate:

```text
ADVERSE_DIRECTION_ADD / AVERAGING_DOWN = PROHIBITED
WINNER_PYRAMID = ALLOWED ONLY WITH CONTROLLED TOTAL POSITION RISK
```

Do not use a few winning adverse-add examples to justify the behavior; evaluate distribution and tail-risk impact.

### 7.5 Low-quality probe

Fills alone cannot prove an entry lacked a valid setup. Therefore:

```text
LOW_QUALITY_ENTRY
```

requires user annotation and/or market-path/setup evidence.

However, the weekly review must quantify the cost of small losers (for example `<= $0.25`) and their fees because repeated low-cost probes can become a material loss source even when each individual loss appears trivial.

---

## 8. Winner quality / MAE-MFE

Do not infer from fills alone that a profitable exit was too early. Without post-entry market-path evidence, any material conclusion that a winner was exited too early must be labelled:

```text
NEEDS_MARKET_PATH_DATA
```

Once market-path capture is available, calculate at minimum:

```text
MAE
MFE
time_to_MAE
time_to_MFE
MFE_capture_ratio
max_profit_giveback
```

Where BBO evidence is available, maintain both:

```text
MARKET_MAE_MFE
EXECUTABLE_MAE_MFE
```

For long executable exit use best bid; for short executable exit use best ask.

Canonical evidence boundary:

```text
CANDLE_HIGH_LOW != EXECUTABLE_MAE_MFE
```

Candle high/low may support only approximate market-path excursion estimates. They must never be labelled executable MAE/MFE. If BBO/quote evidence is absent, `EXECUTABLE_MAE_MFE=UNKNOWN` rather than inferred from candle prices or interpolated.

One-minute fallback must be labelled `ONE_MINUTE_APPROX`; where entry or exit occurs inside a minute, the affected boundary minute must additionally be labelled `BOUNDARY_MINUTE_UNCERTAIN`. Do not interpolate missing tick/BBO observations and call the result exact.

The strategy should preserve right-tail winners. Do not recommend a small fixed take-profit merely to raise win rate without testing the impact on expectancy and winner concentration.

---

## 9. Opening-reversal research

When market-path data is available, every Korea and US open should calculate:

- pre-open 30-minute trend direction;
- first 5-minute direction;
- first 15-minute direction;
- first 30-minute direction;
- max upward excursion;
- max downward excursion;
- first sweep direction and magnitude;
- first reclaim/reversal timestamp;
- whether the first move is reversed;
- whether the later 60/120-minute move restores the pre-open/day trend;
- probability of continuation conditional on sweep/reclaim structure.

The current hypothesis that opens often make an initial liquidity sweep in one direction before developing the later session trend must remain labelled **HYPOTHESIS** until the above evidence is available.

---

## 10. Counterfactual analysis rules

The review should answer questions such as:

- what if hold-loss/process-violation episodes were absent;
- what if Korea/US opening regimes were avoided;
- what if Macro × US Open were avoided;
- what if multiple error classes were jointly removed.

But every such result must be labelled:

```text
POST_HOC_DIAGNOSTIC
NOT_FORECAST
```

Removing historical losers is not proof that the remaining subset can be selected perfectly in real time.

When simulating capped stops, do not claim the result is valid without MAE/path evidence because a tighter stop may also remove future winners.

---

## 11. Evidence labels

Every material conclusion should be classified as one of:

```text
OBSERVED_FACT
DATA_SUPPORTED_ASSOCIATION
POST_HOC_DIAGNOSTIC
HYPOTHESIS
PROVISIONAL_RULE
NEEDS_MARKET_PATH_DATA
```

Do not silently upgrade association to causality.

---

## 12. Week-over-week comparison

Every new week must compare against the prior accepted baseline using the same definitions.

Minimum change table:

```text
net_pnl
profit_factor
expectancy
win_rate
payoff_ratio
trades_per_day
fees
avg_loss
losses_gt_0_50
losses_gt_1_00
hold_loss_proxy_count
rapid_reentry_count
Korea_open_PF
US_open_PF
Macro_US_open_PF
winner_median_hold
loser_median_hold
```

Do not change definitions mid-series without versioning the procedure and restating historical comparability.

---

## 13. Current active behavioral experiment baseline — week beginning 2026-09-07

Evidence label for every rule/threshold in this section:

```text
PROVISIONAL_RULE
```

These are user-directed behavioral targets for the next validation week. They are **not** permanent mathematical strategy parameters and may be revised by explicit user authority after review. Numeric values in this section, including approximately `$0.20`, `$0.50`, `10 minutes`, and `15 minutes`, are prospective behavioral experiment parameters rather than proven optimal trading parameters.

### Target A — stop discipline — `PROVISIONAL_RULE`

```text
NO_HOLDING_LOSERS=TARGET
TARGET_NORMAL_REALIZED_LOSS <= approximately $0.20
ADVERSE_DIRECTION_ADD = ZERO
```

A normal manual exit can contain execution/fee noise; the weekly review must distinguish intended behavior from exact after-fee cents where possible.

### Target B — entry selectivity / lower frequency — `PROVISIONAL_RULE`

```text
REDUCE_LOW_INFORMATION_ENTRIES=YES
REDUCE_TRADES_PER_DAY=YES
EACH_ENTRY_REQUIRES_EXPLICIT_SETUP_REASON=YES
```

Do not treat a cheap stop as permission to enter casually.

### Target C — macro neutrality — `PROVISIONAL_RULE`

```text
MACRO_RELEASE_OR_SURPRISE_IS_NOT_A_DIRECTIONAL_SIGNAL
PRICE_ACTION_HAS_PRIORITY
```

Do not enter merely because a release is theoretically bullish/bearish.

### Target D — post-violation cooling period — `PROVISIONAL_RULE`

```text
IF realized_loss > $0.50:
    STOP_NEW_ENTRIES_FOR_AT_LEAST_10_MINUTES
    NEXT_ENTRY_REQUIRES_REASSESSMENT_AND_CLEAR_TRIGGER
```

The review must measure compliance and subsequent-trade performance.

### Target E — opening protection — `PROVISIONAL_RULE`

For both Korea and US cash-market opens:

```text
FIRST_15_MINUTES:
    DEFAULT = NO_TRADE
    EXCEPTION = CLEAR / HIGH-CONVICTION CONFIRMED SIGNAL
```

After 15 minutes, trading does not resume automatically. A sufficiently clear market structure/trigger must exist.

The review must evaluate whether compliance improves after-fee expectancy and reduces process violations, rather than assuming the rule is optimal in advance.

---

## 14. Required weekly final output

A complete review should end with five compact sections:

1. **What worked and should continue**;
2. **What failed and must stop**;
3. **Which errors were regime-dependent**;
4. **What remains unproven / needs MAE-MFE or more samples**;
5. **No more than 3–5 behavioral priorities for the next week**.

The final recommendation must distinguish:

```text
KEEP
STRENGTHEN
MODIFY
PROHIBIT
TEST_MORE
```

Do not respond to one weak week by replacing the whole strategy if the evidence shows that a small number of behavior violations dominate losses. Conversely, do not declare a strategy proven profitable merely because a post-hoc cleaned subset is positive.

---

## 15. Privacy and GitHub boundary

This procedure may store methodology, public market/session definitions, and versioned analytical schemas in GitHub.

It must **not** store:

- raw personal trade exports;
- account addresses or identifiers;
- wallet/private-key material;
- production account DB/log data;
- screenshots containing private account information unless sanitized and explicitly authorized.

Weekly raw data remains outside Git history. Only derived methodology or deliberately sanitized aggregate research artifacts may be proposed for GitHub under normal project review.
