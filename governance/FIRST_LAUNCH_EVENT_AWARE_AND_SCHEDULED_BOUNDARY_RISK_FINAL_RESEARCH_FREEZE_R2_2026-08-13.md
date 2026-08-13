# First Launch Event-Aware 与 Scheduled Boundary Risk 最终研究冻结 R2

**记录 ID：** `TA-FIRST-LAUNCH-EVENT-AWARE-BOUNDARY-RISK-FINAL-R2-2026-08-13`  
**日期：** `2026-08-13`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `POST-FIRST-LAUNCH STRATEGY / RISK RESEARCH FINAL FREEZE / NON-EXECUTABLE / NON-AUTHORIZING`

---

## 0. Authority / Supersession

本文件是以下两个方向的当前最终研究权威：

```text
A. EVENT_AWARE_PRICE_ACTION_OVERLAY
B. SCHEDULED_BOUNDARY_RISK_GUARD
```

它在发生冲突时取代：

```text
FIRST_LAUNCH_EVENT_AWARE_OVERLAY_AND_SCHEDULED_BOUNDARY_RISK_CONVERGENCE_R1_2026-08-13.md
```

并对更早的 Macro / Earnings / Extended-Hours 文档作进一步语义收敛。

旧文档的数据源、PIT、宏观 surprise、财报 KPI、FOMC / Earnings Call 多阶段、execution / venue tracking 等研究内容继续保留参考价值；但若与本文件的最终架构、authority、风险边界或研究方法冲突，以本文件为准。

当前 First Launch / V0 不因此增加任何生产策略功能：

```text
CURRENT_RELEASE_CODE_CHANGE = NO
CURRENT_MACHINE_STRATEGY_CHANGE = NO
NEW_FORMAL_SETUP = NO
AUTO_TRADE = NO
ACCOUNT_ACCESS = NO
SIGNING = NO
EXCHANGE_WRITE = NO
```

---

# 1. 最终架构

整个未来交易策略继续只有一个价格行为 Alpha / Entry Core：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST
  ├─ MICRO_FAST
  └─ STANDARD
RANGE_EDGE_REJECTION
```

外层只保留两个非平行 Alpha 模块：

```text
CORE THREE-SETUP PRICE ACTION
        │
        ├── EVENT_AWARE_CONTEXT / ATTRIBUTION
        │
        └── SCHEDULED_BOUNDARY_RISK / PERMISSION
```

固定：

```text
PRICE-ACTION SETUPS = PRIMARY DIRECTION / ENTRY AUTHORITY
EVENT OVERLAY = INFORMATION / CONTEXT / ATTRIBUTION
BOUNDARY GUARD = RISK / PERMISSION / DE-RISK AUTHORITY
SESSION = CONTEXT, NOT A NEW SETUP FAMILY
```

Event Overlay 不因为 CPI / Earnings 等数据自动产生 Long / Short。

Boundary Guard 不决定 Long / Short，但未来自动交易时可以：

```text
ALLOW_NEW_ENTRY
BLOCK_NEW_ENTRY
DE_RISK_EXISTING
REQUIRE_FLATTEN
WAIT_FOR_RECOVERY
```

---

# 2. 外部成熟研究与市场机制依据

本研究方向与以下成熟文献 / 官方市场机制一致。

## 2.1 开盘 / Pre-open / Auction

成熟市场微观结构研究长期发现：

- 交易日开盘附近通常具有异常高的 volatility / volume / price discovery；
- opening auction / pre-open order accumulation 具有独立的信息聚合过程；
- 开盘价格形成机制与正常 continuous trading 不完全相同；
- 开盘后的最初一段时间容易同时包含真实方向发现与短期 inventory / liquidity / order-imbalance 噪声。

主要参考：

```text
Wood, McInish & Ord (1985)
An Investigation of Transactions Data for NYSE Stocks
Journal of Finance

Biais, Hillion & Spatt (1999)
Price Discovery and Learning during the Preopening Period in the Paris Bourse
Journal of Political Economy

Madhavan & Panchapagesan (2000)
Price Discovery in Auction Markets: A Look Inside the Black Box
Review of Financial Studies

NYSE official Opening Auction materials
Nasdaq official Opening Cross materials
JPX official cash-equity trading-hours / auction materials
London Stock Exchange official trading-hours materials
```

这些研究支持把开盘视为 `SCHEDULED MARKET BOUNDARY`，但并不支持把所有市场统一硬编码为固定“15 分钟禁止交易”。

## 2.2 宏观公开信息冲击

高频宏观研究一致支持：

```text
PUBLIC INFORMATION RELEASE
→ fast conditional-mean repricing
→ volatility / volume / liquidity regime disturbance
→ later price discovery / acceptance
```

主要参考：

```text
Andersen, Bollerslev, Diebold & Vega (2003)
Micro Effects of Macro Announcements: Real-Time Price Discovery in Foreign Exchange
American Economic Review

Andersen, Bollerslev, Diebold & Vega (2007)
Real-Time Price Discovery in Global Stock, Bond and Foreign Exchange Markets
Journal of International Economics

Fleming & Remolona (1999)
Price Formation and Liquidity in the U.S. Treasury Market: The Response to Public Information
Journal of Finance
```

成熟结果更支持“信息冲击改变交易环境”，而不是证明某一种新的 K 线几何只在 Event 中存在。

## 2.3 Pre-announcement pricing

事件公布前存在价格变化是成熟研究对象，但不能等同于“市场提前知道公布值”。

主要参考：

```text
Lucca & Moench
The Pre-FOMC Announcement Drift

Hu / Pan / Wang / Zhu pre-announcement return research

Federal Reserve research on informed positioning around macro announcements
```

可能机制包括：

```text
risk / uncertainty premium
expectation positioning
forecast information
hedging
attention
liquidity
informed positioning in some samples
```

因此本系统不建立：

```text
PRE_EVENT_DATA_PREDICTION_ENGINE
```

只允许现有三个 Setup 交易已经真实出现在盘面的趋势 / Sweep / Breakout / Range 结构。

## 2.4 Investor attention / event sensitivity

Federal Reserve 对宏观新闻处理的研究表明，同样的 surprise 在不同 investor-attention / policy-sensitivity 环境下可能产生不同反应强度，并存在过度反应与后续修正问题。

因此：

```text
ACTUAL - CONSENSUS
```

不能单独被视为完整 Event Strategy。

## 2.5 Earnings / Conference Call

财报不是单一 headline 信息事件。成熟研究显示 earnings conference call / management tone / guidance 等内容可提供 headline EPS / Revenue 之外的增量信息，市场可能进行多阶段重新定价。

因此：

```text
EARNINGS RELEASE
→ GUIDANCE / SUPPLEMENT
→ CALL
→ Q&A
```

应被视为 linked information boundaries，而不是一个单一时间点。

## 2.6 TradeXYZ / Hyperliquid venue-specific caution

TradeXYZ 股票类市场具有 extended-hours / overnight external pricing 机制；Hyperliquid / XYZ 的 external / oracle / mark / perp mid 并非语义完全相同。

重大财报或宏观跳跃期间，应避免把 venue tracking lag / basis / quote adjustment 错归因为策略 alpha。

---

# PART A — SCHEDULED BOUNDARY RISK GUARD

# 3. Boundary Risk 是所有策略共享的风险层

Boundary 不仅包括 Scheduled Information Release，还包括已知的全球主要参与者 / 流动性切换时点。

最低 Boundary Universe：

```text
SESSION / LIQUIDITY:
- ASIA_OPEN
- EUROPE_OPEN
- US_CASH_OPEN

INFORMATION:
- CPI
- PPI
- NFP
- PCE
- FOMC_STATEMENT
- FOMC_PRESS_CONFERENCE
- EARNINGS_RELEASE
- GUIDANCE_RELEASE
- EARNINGS_CALL
- OTHER_SCHEDULED_HIGH_IMPACT_INFORMATION
```

当前人工 / V0 阶段原则：

```text
DEFAULT = DO NOT CARRY ORDINARY POSITION THROUGH MAJOR BOUNDARY
DEFAULT = FLATTEN / DE-RISK BEFORE BOUNDARY
EXCEPTION = HUMAN-APPROVED SPECIAL CASE
```

适用于三个 Setup。

---

# 4. 四个关键问题的最终研究裁决

## 4.1 Default Flatten 是否应该冻结？

### Ruling

```text
DEFAULT_FLATTEN_OR_DE_RISK = YES
```

原因：

- Boundary 附近的 tail MAE / slippage / false-break risk 与普通连续交易不同；
- 已知 Boundary 可提前规避，而非未知随机风险；
- 当前交易目标不是赚取“持仓穿越边界本身”的 jump premium；
- 用户资金规模不要求为了流动性抢在 Boundary 瞬间成交；
- 未来自动化更应先采用可解释、可审计的 conservative baseline，再用 evidence 打开例外。

未来研究顺序必须是：

```text
DEFAULT FLATTEN / DE-RISK
→ collect counterfactual carry evidence
→ prove bounded exception
→ only then permit exception
```

不得反向采用：

```text
DEFAULT CARRY
→ 找条件禁止
```

### Important distinction

Default Flatten 是风险政策 baseline，不意味着：

```text
LONG PRE-BOUNDARY BLACKOUT WINDOW
```

在 Boundary 前较早阶段，只要三个 Setup 合格，人工仍可交易；真正的问题是仓位能否在 Boundary 前安全结束 / 去风险。

---

## 4.2 Asia / Europe / U.S. 是否都必须是 Mandatory Guard？

### Ruling

```text
ALL_THREE_BOUNDARY_FAMILIES = MANDATORY IN REGISTRY / GUARD
SAME_SEVERITY_FOR_ALL_ASSETS = NO
```

未来采用 `BOUNDARY_RELEVANCE`：

```text
DIRECT
SYSTEMIC
SECONDARY
```

示例：

```text
U.S. equity / XYZ100 / SP500
  US_CASH_OPEN = DIRECT
  EUROPE_OPEN = SYSTEMIC or SECONDARY by evidence
  ASIA_OPEN = SYSTEMIC or SECONDARY by evidence

Korean / Japanese equity-linked RWA
  relevant local Asia cash open = DIRECT
  U.S. open = SYSTEMIC where sector/global linkage is material

BTC / ETH
  no direct cash-market opening auction
  Asia / Europe / U.S. boundaries = participant-flow / cross-asset SYSTEMIC candidates
```

重要：

`SECONDARY` 不代表从 calendar 删除，只代表自动 Guard 的观察窗口 / required evidence / de-risk severity 可更弱。

### Calendar rules

必须：

```text
local-time aware
DST-aware
holiday-aware
underlying-market aware
```

初始参考：

```text
Asia:
  primary relevant local cash open
  e.g. TSE 09:00 JST / Korean cash open 09:00 KST

Europe:
  primary major European / London opening transition
  initial research anchor ~08:00 Europe/London

U.S.:
  NYSE / Nasdaq cash open 09:30 America/New_York
```

不得硬编码固定 UTC。

---

## 4.3 Event Overlay 是否必须始终服从三个 Setup？

### Ruling

```text
YES FOR CURRENT / FIRST FUTURE IMPLEMENTATION
```

Event information 第一阶段：

```text
DOES NOT CREATE LONG / SHORT
DOES NOT CREATE FOURTH SETUP
DOES NOT OVERRIDE PRICE-ACTION DIRECTION
```

它只能：

```text
TAG
EXPLAIN
ATTRIBUTION
SUPPLY NEXT INFORMATION BOUNDARY
SUPPLY RESEARCH FEATURES
```

未来若 Event feature 要升级成 Ranking / Gate，必须独立证明：

```text
BASE SETUP + EVENT FEATURE
>
BASE SETUP
```

且必须通过独立 Strategy Authority 再冻结。

未来如果有人希望：

```text
CPI SURPRISE → DIRECT LONG / SHORT
EPS BEAT → DIRECT LONG / SHORT
```

这属于新策略 authority，不能从本 Overlay 隐式获得权限。

---

## 4.4 Event Release / Call / FOMC 等是否统一进入同一个 Boundary Guard？

### Ruling

```text
YES
```

统一模型：

```text
EVENT OVERLAY
→ emits / knows SCHEDULED INFORMATION BOUNDARY
→ BOUNDARY RISK GUARD
→ permission / de-risk decision
```

每个事件阶段是独立 `boundary_instance`：

```text
FOMC_PARENT
  ├─ STATEMENT_BOUNDARY
  └─ PRESS_CONFERENCE_BOUNDARY

EARNINGS_PARENT
  ├─ RELEASE_BOUNDARY
  ├─ GUIDANCE_BOUNDARY where separate
  └─ CALL_BOUNDARY
```

这样无需：

```text
CPI risk engine
Earnings risk engine
FOMC risk engine
Session-open risk engine
```

四套重复机制。

它们共享 state machine，但 boundary subtype / relevance / timing precision 可不同。

---

# 5. Boundary Identity / Data Contract — Future Research Target

未来研究 / 自动化候选至少包含：

```text
boundary_id
boundary_family
boundary_subtype
parent_event_id optional
anchor_market / region
relevance = DIRECT | SYSTEMIC | SECONDARY
scheduled_time
scheduled_window_start optional
scheduled_window_end optional
actual_time optional
timezone
calendar_source
calendar_version
holiday_state
DST_state
market_id / affected_group
```

### Why scheduled window is required

宏观数据通常有精确发布时间。

公司财报常只有：

```text
BEFORE MARKET
AFTER MARKET
approximate call time
```

或实际发布时间存在分钟级不确定性。

未来自动化不能把 Earnings 一律假定为精确秒级 boundary，应支持：

```text
BOUNDARY_WINDOW
```

默认在 release window 尚未结束 / actual release 尚未确认时保持 fail-closed carry exception。

---

# 6. Boundary stacking / compound risk

新增最终要求：

```text
BOUNDARY_STACKING = REQUIRED RESEARCH CONCEPT
```

例如：

```text
08:30 ET CPI
09:30 ET U.S. cash open
```

或：

```text
16:00 ET cash close / session transition
16:05 ET earnings release
16:30 ET earnings call
```

多个 Boundary 很近时，不应该把前一个 Boundary 视为完全恢复后再独立处理后一个。

未来候选：

```text
COMPOUND_BOUNDARY
```

规则方向：

```text
recovery cannot be considered durable if another higher/equal-risk boundary is imminent
later boundary may reset RECOVERY_OBSERVATION
```

具体 lookahead window 待数据校准。

---

# 7. Future Automated Boundary State Machine

最终候选：

```text
NORMAL
→ BOUNDARY_WATCH
→ PRE_BOUNDARY_DE_RISK
→ BOUNDARY_NO_NEW_ENTRY
→ BOUNDARY_DISCOVERY
→ RECOVERY_OBSERVATION
→ RECOVERY_CONFIRMED
→ NORMAL
```

异常：

```text
CALENDAR_UNKNOWN
BOUNDARY_TIME_UNCERTAIN
MARKET_DATA_STALE
EXECUTION_DATA_STALE
COMPOUND_BOUNDARY
```

未来 Auto Entry 默认：

```text
UNKNOWN / STALE BOUNDARY STATE
→ FAIL CLOSED FOR NEW AUTO ENTRY
→ NO AUTOMATIC CARRY EXCEPTION
```

是否自动强制平仓已有仓位属于单独的 Risk Authority，不能只因 calendar provider 暂时失败而无条件市价清仓。

---

# 8. Pre-boundary position management research

默认 benchmark：

```text
POLICY A = FULL FLATTEN
```

对照：

```text
POLICY B = PARTIAL DE-RISK
POLICY C = CARRY EXISTING RISK
POLICY D = BOUNDED EVIDENCE-BACKED EXCEPTION
```

未来研究必须比较：

```text
Net R
Tail MAE
Worst Event Loss
Stop-out Rate
False-break Rate
Worst Slippage
Opportunity Cost of Flatten
Re-entry Quality
```

不以 Win Rate 单独决定。

### Future carry exception eligibility — hypothesis only

只有以下方向可研究，不授权实施：

```text
boundary is not DIRECT information shock for the held asset
AND no compound higher-risk boundary
AND position has material profit cushion
AND execution / tracking is healthy
AND structure remains strongly accepted
AND retained risk is explicitly capped
```

任何阈值必须由 OOS evidence 冻结。

---

# 9. Exit deadline / decision clock

不应在 Boundary 精确瞬间才尝试去风险。

未来概念：

```text
EXIT_DEADLINE
=
boundary_window_start
- execution_safety_buffer
```

`execution_safety_buffer` 由：

```text
market
boundary type
venue latency
spread
slippage
order policy
```

校准。

对于当前 5m Strategy Core，未来自动化研究应优先在**最后一个能够因果完成的安全闭合 5m decision boundary**作出预边界决策；不得用尚未闭合 candle 做 hindsight decision。

这不授权当前 First Launch 自动平仓。

---

# 10. Boundary Recovery — 核心研究

“约 09:45 恢复”保留为人工 benchmark，但不冻结为机器规则。

研究：

```text
TIME_ONLY
vs
MARKET_STATE_RECOVERY
vs
COMPOSITE_RECOVERY
```

## 10.1 Execution Recovery — hard prerequisite candidate

```text
BBO_FRESH
spread acceptable
book depth usable
estimated slippage acceptable
provider / oracle / mark / external tracking healthy where relevant
```

只要 execution 明显异常：

```text
NO_NEW_AUTO_ENTRY
```

## 10.2 Volatility / path stability

研究：

```text
realized_vol_ratio_to_baseline
range_ATR_ratio
opening_displacement_ATR
sign_flip_count
boundary_cross_count
reclaim_count
```

## 10.3 Directional Efficiency

研究核心指标：

```text
DIRECTIONAL_EFFICIENCY
= abs(P_end - P_start)
  / sum(abs(P_i - P_i-1))
```

范围：

```text
0 → highly noisy / oscillating
1 → nearly one-directional path
```

只用 closed causal bars。

## 10.4 Robust normalization

不同资产 / 不同 session 天生 spread / vol 不同，因此优先研究：

```text
same-market / same-boundary baseline
median / percentile / MAD robust normalization
```

而不是全市场一个绝对阈值。

候选：

```text
RV_RATIO_TO_BASELINE
SPREAD_RATIO_TO_BASELINE
DEPTH_RATIO_TO_BASELINE
ROBUST_Z_BY_MARKET_BOUNDARY
```

## 10.5 Earliest possible recovery under current Setup Core

当前 Formal signal 使用 closed 5m。

因此基于现有三个 Setup 的未来 Auto Guard，第一阶段原则上不应在第一根 post-boundary 5m candle 闭合前宣称三个 Setup 的正常 closed-5m structure 已恢复。

研究比较：

```text
first closed post-boundary 5m
second closed post-boundary 5m
third closed post-boundary 5m
state-based recovery regardless of elapsed bucket
```

若未来另有经过独立授权的更高频策略，本条需重新研究，不自动继承。

---

# 11. Boundary Research Buckets

只作为实验 bucket：

```text
PRE:
T-60 to T-30
T-30 to T-15
T-15 to T-5
T-5 to T

POST:
0-5m
5-15m
15-30m
30-60m
60m+
```

不冻结任何 bucket 为机器 blackout。

对每个：

```text
market
asset class
setup
direction
boundary family
boundary relevance
vol regime
liquidity regime
```

统计：

```text
signal count
net expectancy
MFE
MAE
tail MAE
stop rate
false-break rate
reclaim rate
directional efficiency
spread / depth / slippage
re-entry quality
```

---

# 12. Boundary Policy Experiment Matrix

```text
B0 = NO BOUNDARY GUARD

B1 = FIXED-TIME DEFAULT FLATTEN
     + FIXED-TIME RECOVERY

B2 = DEFAULT FLATTEN
     + DYNAMIC MARKET-STATE RECOVERY

B3 = DEFAULT FLATTEN
     + DYNAMIC RECOVERY
     + BOUNDED CARRY EXCEPTION
```

Primary comparison：

```text
TAIL-RISK-ADJUSTED NET EXPECTANCY
```

不是单纯 win rate / gross return。

---

# PART B — EVENT-AWARE PRICE-ACTION OVERLAY

# 13. Event Overlay 的最终职责

只回答：

```text
WHAT INFORMATION EVENT IS RELEVANT?
WHEN IS / WAS THE INFORMATION RELEASED?
WHAT STAGE IS THE EVENT IN?
WHAT WAS PUBLICLY KNOWN AT THAT TIME?
WHAT DID THE MARKET APPEAR TO PRICE BEFORE RELEASE?
WHAT HAPPENED AFTER RELEASE?
WHEN IS THE NEXT KNOWN INFORMATION BOUNDARY?
```

不回答：

```text
LONG OR SHORT DIRECTLY
```

---

# 14. Event Registry / PIT contract

最低未来研究字段：

```text
event_id
parent_event_id optional
event_family
stage
issuer / macro_family
scheduled_time
scheduled_window
actual_release_time
observed_at / ingested_at
source
source_version
revision_status
```

必须区分：

```text
scheduled_time
actual_release_time
system_observed_at
```

避免未来回测假定系统在官方数据真正可见之前就知道结果。

---

# 15. Macro Context — minimum research vector

第一阶段优先保存：

```text
actual
consensus
previous
revision

raw_surprise
historically_standardized_surprise
forecast_dispersion / disagreement where available

pre_event_market_positioning
US2Y / front-end rate response
DXY response
NQ / ES benchmark response
selected-market response
```

### Standardized surprise

候选：

```text
z_surprise_t
=
(actual_t - consensus_t)
/
rolling historical std of prior PIT surprises
```

只能使用 event t 之前可获得的历史 surprise。

对于 CPI / NFP 等多变量 release，保留 vector，不急于压成一个黑盒 score。

---

# 16. Earnings Context — minimum research vector

至少：

```text
issuer
scheduled / actual release time
EPS actual / consensus
Revenue actual / consensus
Guidance
company-specific KPI where material
release stage
call start / end
Q&A stage
peer / sector / index response
```

禁止：

```text
EPS_BEAT → LONG
EPS_MISS → SHORT
```

第一阶段只用于 attribution / incremental-value study。

---

# 17. Pre-event pricing — final treatment

事件前的预期定价不创建新的 Entry Strategy。

三个 Setup 始终正常运行。

研究只保存 / 派生：

```text
pre_event_return
pre_event_ATR_normalized_move
pre_event_relative_strength
pre_event_breadth
pre_event_directional_efficiency
rates / DXY path for macro
implied_move consumption where available
```

初始研究 bucket 可包含：

```text
T-6h
T-3h
T-90m
T-30m
T-5m
```

只是 attribution / event-study windows，不是 entry schedule。

---

# 18. Priced expectation / Sell-the-fact — final treatment

只作为研究 taxonomy。

候选标签：

```text
EXPECTATION_UNDERPRICED
EXPECTATION_CONFIRMED
EXPECTATION_SATURATED
EXPECTATION_CONTRADICTED
AMBIGUOUS
```

由：

```text
pre-event positioning
+
public consensus / distribution
+
actual release vector
+
initial market response
```

共同研究。

不得把：

```text
PRE_EVENT_UP + IN_LINE_DATA
```

直接翻译成自动 Short。

---

# 19. Multi-stage Event Boundary model

FOMC：

```text
FOMC_EVENT
  ├─ STATEMENT
  ├─ SEP if applicable
  ├─ PRESS_CONFERENCE
  └─ Q&A / subsequent stage
```

Earnings：

```text
EARNINGS_EVENT
  ├─ RELEASE
  ├─ GUIDANCE / SUPPLEMENT
  ├─ CALL
  └─ Q&A
```

每个阶段：

```text
= Event Context Stage
+
= Scheduled / Actual Information Boundary
```

所以 Overlay 必须能提供：

```text
NEXT_INFORMATION_BOUNDARY
```

给统一 Boundary Guard。

---

# 20. Event and Boundary Authority Separation

最终未来概念架构：

```text
Strategy Kernel
  → Formal Setup Direction / Plan

Event Overlay
  → EventContext
  → next_information_boundary
  → attribution only

Boundary Risk Guard
  → EntryPermission / PositionRiskDecision

Execution Quality Guard
  → Can execute safely?

Human / future Automation Authority
  → final execution action
```

Boundary Guard 可以 veto 一个正确的 Long/Short Setup 的“现在是否可以执行”，但不能把 Long 变 Short。

Event Overlay 第一阶段甚至没有 veto 权；它只通过 Boundary identity / stage 影响 Boundary Guard。

---

# 21. Asset Selection — no new router until evidence

Macro 信息广泛，Earnings 信息主体较窄。

第一阶段统一使用：

```text
existing Scanner
Relative Strength
Liquidity / Execution
Correlation context
```

研究：

```text
BASE SCANNER
vs
EVENT-CONDITIONED RANKING
```

只有普通 Scanner 在 Event Window 中出现稳定的系统性缺陷时，才允许研究新的 Event-specific ranker。

```text
NEW LIVE EVENT ASSET ROUTER = NOT AUTHORIZED BY THIS CONTRACT
```

---

# 22. Event-specific hypotheses worth testing

只作为 hypothesis：

```text
H1:
Setup direction aligned with macro/earnings information context
→ continuation quality may improve

H2:
Setup direction conflicts with interpretation assets / event vector
→ failure / reclaim probability may increase

H3:
high pre-event pricing + weak incremental actual information
→ saturation / failed-first-move may increase

H4:
high attention / high disagreement regimes
→ first-move magnitude / overreaction / failure behavior may differ

H5:
multi-stage pending information boundary
→ carry tail risk may differ from otherwise identical setup
```

不得因经济直觉直接升级成 live rules。

---

# 23. Venue / execution research for TradeXYZ events

重大公司 / 宏观 Event 研究应保存或有界采样：

```text
external price
oracle
mark
perp mid / BBO
spread
estimated slippage
```

研究：

```text
tracking lag
basis
quote adjustment
execution-quality recovery
```

目的：

```text
DO NOT CONFUSE VENUE MECHANICS WITH STRATEGY ALPHA
```

不要求当前建设 continuous tick/L2 platform。

---

# 24. Event Incremental-Value Study Design

每个 Setup 都要做：

```text
BASE SETUP
vs
BASE SETUP + EVENT CONTEXT FEATURE
```

控制：

```text
market
setup
side
session
volatility regime
liquidity regime
correlation / cluster
```

Primary metrics：

```text
Net Expectancy
MFE
MAE
Tail MAE
Failure Rate
Drawdown
Execution Cost
Time to MFE / failure
```

任何 promotion 必须：

```text
OOS / walk-forward evidence
no severe tail-risk deterioration
increment > incremental complexity + execution cost
stable across more than one event cycle / market regime
```

不冻结任意固定样本数量；采用 event-cluster power / uncertainty analysis。

---

# 25. Sample Independence / Cluster rule

一个 CPI event 产生 20 个相关市场 Signal：

```text
!= 20 independent macro experiments
```

一个 US Open 同时产生 20 个科技股 Signal：

```text
!= 20 independent boundary experiments
```

必须同时保留：

```text
RAW SIGNAL LEVEL
MARKET / EXPOSURE CLUSTER LEVEL
EVENT / BOUNDARY INSTANCE LEVEL
```

统计推断优先按：

```text
EVENT_ID / BOUNDARY_ID
```

cluster / block bootstrap 或等价方法。

不得因为相关 Signal 数量大而虚增显著性。

---

# 26. Position Management 与这两个模块的边界

以下问题属于通用 Position Management Research，不属于 Event-specific Alpha：

```text
trend hold
profit giveback exit
trailing structural exit
exit then re-enter
micro-swing harvest
```

Event / Boundary 只增加：

```text
KNOWN BOUNDARY RISK
```

不能把通用仓位管理复制进 Event Strategy。

---

# 27. Future Machine-Ready Permission Model — research target

未来建议统一输出，而不是多个 boolean：

```text
ALLOW_NEW
MANAGE_EXISTING_ONLY
DE_RISK_REQUIRED
FLATTEN_REQUIRED
BLOCK_NEW
RECOVERY_WAIT
MANUAL_EXCEPTION_REQUIRED
```

附 evidence：

```text
boundary_id
boundary_state
relevance
reason_codes
market_quality_evidence
event_context_id optional
next_boundary
calendar_version
```

当前不授权实现。

---

# 28. Minimum research program before future auto-trading

## Program A — Boundary Risk

至少完成：

```text
A1 Asia / Europe / U.S. carry-vs-flatten study
A2 three-Setup performance by boundary bucket
A3 fixed-time vs dynamic-recovery comparison
A4 asset-specific boundary relevance study
A5 compound-boundary study
A6 carry-exception counterfactual study
A7 TradeXYZ execution / tracking around direct boundaries
```

## Program B — Event-Aware Context

至少完成：

```text
B1 Event vs non-event matched Setup comparison
B2 pre-event pricing attribution
B3 surprise / rates / DXY / benchmark incremental-value study
B4 Earnings release / guidance / call stage study
B5 Event-context aligned vs conflicting Setup study
B6 existing Scanner vs event-conditioned ranking study
B7 event-level sample-independence / clustered inference
```

---

# 29. Promotion / deletion rule

未来每个 feature 只有三个结果：

```text
PROMOTE
KEEP RESEARCH-ONLY
DELETE / DO NOT BUILD
```

### Promote

只有：

```text
stable OOS marginal value
+
reasonable engineering cost
+
no unacceptable tail-risk increase
+
clear causal / operational semantics
```

### Keep research-only

解释力有价值，但不改善交易或风险决策。

### Delete

如果普通三个 Setup + Scanner + generic execution / boundary rules 已经达到同等效果：

```text
DO NOT BUILD DUPLICATE EVENT FEATURE
```

---

# 30. Final frozen decisions

```text
ONE CORE PRICE-ACTION SYSTEM = YES

EVENT-AWARE OVERLAY = YES
EVENT DIRECT LONG/SHORT AUTHORITY = NO
EVENT-SPECIFIC FOURTH SETUP = NO

SCHEDULED BOUNDARY RISK GUARD = YES / FUTURE AUTO MANDATORY
ASIA BOUNDARY = MANDATORY COVERAGE
EUROPE BOUNDARY = MANDATORY COVERAGE
U.S. BOUNDARY = MANDATORY COVERAGE
SAME SEVERITY ACROSS ALL ASSETS = NO
ASSET-SPECIFIC RELEVANCE = YES

DEFAULT FLATTEN / DE-RISK BEFORE MAJOR BOUNDARY = YES
AUTOMATIC CARRY EXCEPTION NOW = NO
EVIDENCE-BACKED FUTURE EXCEPTION RESEARCH = YES

FIXED 09:45 MACHINE RULE = NO
DYNAMIC RECOVERY RESEARCH = YES

ALL INFORMATION BOUNDARIES USE ONE GUARD = YES
MULTI-STAGE EVENT BOUNDARIES = YES
BOUNDARY STACKING = YES
UNCERTAIN RELEASE WINDOW SUPPORT = YES

PREMARKET / AFTER-HOURS / OVERNIGHT AS SEPARATE SETUP = NO
PRE-EVENT ENTRY STRATEGY FAMILY = NO
SELL-THE-FACT STRATEGY FAMILY = NO

CURRENT FIRST LAUNCH CHANGE = NO
AUTO TRADE AUTHORITY = NO
```

---

# 31. Current human/V0 rule vs future auto rule

## Current human / assisted V0

```text
Three Setup signals continue normally.

Major Asia / Europe / U.S. open boundaries:
  default do not carry ordinary positions through boundary;
  flatten / de-risk before boundary;
  human may approve a special case.

Scheduled information releases:
  same boundary-risk principle.

Exact recovery timing:
  human judgement / current trading discipline.
```

## Future automated execution

Before granting autonomous execution authority, must separately freeze a machine contract covering：

```text
calendar / DST / holiday
boundary relevance
default flatten / de-risk
exit deadline / safety buffer
no-new-entry state
compound boundary
uncertain release window
recovery metrics / thresholds
carry exception authority
missing/stale calendar failure mode
execution-quality integration
audit evidence
```

本 R2 提供研究方向和 authority architecture，但不提前冻结未经数据验证的阈值。

---

# 32. Research Method Rule

最终原则：

```text
MATURE MARKET-MICROSTRUCTURE / EVENT-STUDY THEORY
+
RAW RECONSTRUCTABLE EVIDENCE
+
HISTORICAL / FORWARD / SHADOW STUDY
+
OUT-OF-SAMPLE VALIDATION
+
INCREMENTAL VALUE vs COMPLEXITY
→ FREEZE MINIMUM NECESSARY RULE
```

禁止：

```text
human heuristic → untested hard-coded machine parameter
one event anecdote → production rule
correlated signals → fake independent sample size
fundamental story → direct trade authority without price confirmation
```

---

# 33. Authority Boundary

本文不授权：

```text
current release code changes
Engineering implementation
new dependency
runtime / service mutation
production DB mutation
deployment
account/private API
wallet/key
signing
exchange writes
automatic order submission
PR Mark Ready
Merge
```

未来实现必须由新的 Product / Strategy / Engineering / Project Control authority 重新派发。