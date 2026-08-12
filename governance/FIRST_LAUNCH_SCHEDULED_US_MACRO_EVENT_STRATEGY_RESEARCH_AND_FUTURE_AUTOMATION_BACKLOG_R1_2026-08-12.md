# First Launch Scheduled U.S. Macro Event Strategy Research and Future Automation Backlog R1

**记录 ID：** `TA-FIRST-LAUNCH-SCHEDULED-US-MACRO-EVENT-RESEARCH-R1-2026-08-12`  
**日期：** `2026-08-12`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `POST-LAUNCH STRATEGY RESEARCH CONTRACT / NON-EXECUTABLE / NON-AUTHORIZING`  
**父级 Backlog：** `FIRST_LAUNCH_POST_LAUNCH_STRATEGY_RESEARCH_AND_SHADOW_EVIDENCE_BACKLOG_R1_2026-08-12.md` → `R4 = EVENT REGIME`  
**适用阶段：** `POST_FIRST_LAUNCH / OFFLINE_RESEARCH / SHADOW_RESEARCH / FUTURE_V0.x`  

---

## 1. 决策摘要

本研究方向值得继续，并具有较高产品价值。

核心问题不是“预测 CPI/NFP/PCE 的具体公布值”，而是：

```text
SCHEDULED MACRO RELEASE
→ POINT-IN-TIME SURPRISE
→ MARKET POLICY / RATES INTERPRETATION
→ CROSS-ASSET ACCEPTANCE OR CONFLICT
→ EVENT PRICE STRUCTURE
→ EXECUTION-QUALITY GATE
→ TRADE / NO_TRADE
```

当前固定：

```text
CURRENT_RELEASE_STRATEGY_CHANGE = NO
NEW_FORMAL_SETUP_THIS_RELEASE = NO
EVENT_SPECIFIC_LIVE_LOGIC_THIS_RELEASE = NO
AUTO_TRADE_THIS_RELEASE = NO

R4_EVENT_REGIME_RESEARCH = YES
SCHEDULED_MACRO_SUBTRACK = YES
HIGH_PRODUCT_VALUE = YES
PARALLEL_OFFLINE_RESEARCH_ELIGIBLE = YES
CURRENT_R1_R2_R3_PRIORITY_ORDER_CHANGED = NO
```

本文件不改变当前正式三 Setup：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST  # Micro FAST + Standard
RANGE_EDGE_REJECTION
```

也不改变当前 40-market / 5m-only release route。

---

## 2. 为什么值得研究

重大美国宏观数据发布具有几个适合机器辅助 / 自动化的特征：

1. 发布时间预先已知；
2. Actual / Consensus / Previous 可结构化；
3. 多个关键变量需要同时解释；
4. 2Y、美元、指数、Crypto 等跨资产会在极短时间内共同重新定价；
5. 人工操作容易受到第一根 spike、假突破、快速反转、价差扩大和信息过载影响；
6. 系统能够同时处理数据一致性、跨资产确认、执行质量和明确 `NO_TRADE`。

公开高频研究长期表明，宏观公告会造成资产价格跳跃、波动率和成交活动快速变化，且影响强度随经济/政策状态变化。因此不应使用静态规则：

```text
CPI hot → always short risk assets
```

而应研究：

```text
SURPRISE
× POLICY REGIME
× MARKET INTERPRETATION
× CROSS-ASSET CONFIRMATION
× EVENT MICROSTRUCTURE
× EXECUTION COST
```

---

## 3. 与当前 Strategy Authority 的关系

当前父级 Strategy Research Backlog 已冻结：

```text
R1 = FAILED_ACCEPTED_BREAKOUT / FAILED_IMPULSE
R2 = PER_MARKET_STABLE_TIMEFRAME_PROFILE
R3 = SECTOR / PEER RELATIVE STRENGTH
R4 = EVENT REGIME
R5 = CASH OPEN / OPENING REPRICING
R6 = LOGICAL INVALIDATION EXIT
R7 = PROBE → ADD
R8 = CROSS-MARKET CONFIRMATION SOFT SCORE
```

本文件将 `R4 EVENT REGIME` 细化为一个可研究、可回测、可进入未来工程评估的 Scheduled Macro 子合同。

研究顺序不改变，但本子项目允许：

```text
PARALLEL HISTORICAL / OFFLINE RESEARCH
```

原因是它主要依赖外部历史 Point-in-Time 宏观数据与事件窗口市场数据，不必等待当前全部 Shadow Forward 样本成熟。

它不得阻塞当前 First Launch。

---

## 4. 当前最合理的策略归类

目前不应把它定义成第四个正式 Setup。

第一研究假设：

```text
MACRO_EVENT_REGIME
+
EVENT INTERPRETATION STATE MACHINE
+
ENTRY ROUTER
```

其中 Entry Router 可输出：

```text
EXISTING_BREAKOUT_MICRO_FAST_CONTEXT
EXISTING_BREAKOUT_STANDARD_CONTEXT
EXISTING_SWEEP_RECLAIM_CONTEXT
MACRO_SHOCK_MOMENTUM_RESEARCH_ONLY
MACRO_MICRO_PAUSE_RESEARCH_ONLY
MACRO_SHALLOW_PULLBACK_RESEARCH_ONLY
FAILED_FIRST_MOVE_RESEARCH_ONLY
NO_TRADE
```

未来只有 Evidence 证明某个 Macro-only entry pattern 无法合理映射到现有 Setup、且具有稳定独立正期望，才重新讨论新 Setup。

---

## 5. Event Family 分离

第一阶段：

```text
P1 = CPI
P2 = NFP / EMPLOYMENT SITUATION
P3 = PCE / CORE PCE
```

后续：

```text
PPI
RETAIL_SALES
ISM
JOLTS
GDP
JOBLESS_CLAIMS
```

FOMC 必须单独建模，不与 CPI/NFP/PCE 直接共享一个 release state machine，因为 FOMC 是多阶段信息释放：

```text
RATE DECISION
→ STATEMENT
→ SEP / DOTS WHEN APPLICABLE
→ PRESS CONFERENCE
→ Q&A
```

---

## 6. Causal Event State Machine — 研究目标

未来研究/Shadow 原型优先采用状态机，而不是简单指标加权总分：

```text
PRE_EVENT_ARMED
→ RELEASE_RECEIVED
→ RELEASE_VALIDATED
→ SURPRISE_CLASSIFIED
→ MARKET_INTERPRETATION_PENDING
→ CONFIRMED_DIRECTIONAL | MIXED | CONFLICT
→ LIQUIDITY_GATE
→ ENTRY_PATTERN_CLASSIFIED
→ SHADOW_ORDER | NO_TRADE
→ OUTCOME
```

因果层次：

```text
LAYER 1 — MACRO DATA
What happened?

LAYER 2 — RATES / USD
How did the market interpret policy/economic implications?

LAYER 3 — TRADABLE ASSET
Did price accept that interpretation?

LAYER 4 — EXECUTION
Is the trade actually executable at acceptable spread/slippage?
```

禁止把上述四层直接混成一个难以解释的总分后自动下单。

---

## 7. Event Metadata / Point-in-Time Contract

每个事件必须有唯一：

```text
macro_event_id
```

至少保存：

```text
event_name
event_family
reference_period
scheduled_release_timestamp
actual_observed_release_timestamp_if_available
timezone
source
source_version
release_status
revision_status
market_session
dst_status
relevant_fomc_meeting
```

历史研究禁止使用后来修订后的最终数据覆盖事件当时真实可见值。

---

## 8. Surprise Contract

### 8.1 MVP 必须有

```text
ACTUAL
CONSENSUS
PREVIOUS_AS_KNOWN_BEFORE_RELEASE
REVISION_IF_RELEASED_SIMULTANEOUSLY
```

### 8.2 第一版至少比较

```text
RAW_SURPRISE = ACTUAL - CONSENSUS
HISTORICAL_STANDARDIZED_SURPRISE
```

### 8.3 Forecast dispersion

以下具有潜在价值：

```text
FORECAST_COUNT
FORECAST_MIN
FORECAST_MAX
FORECAST_STD
IQR
```

但不是 MVP Hard Dependency。

若获得成本明显较高：

```text
DEFER_TO_RESEARCH_R2
```

不得为了 forecast distribution 建设复杂数据平台。

---

## 9. CPI 研究字段

第一轮必须：

```text
HEADLINE_CPI_MOM
CORE_CPI_MOM
HEADLINE_CPI_YOY
CORE_CPI_YOY
```

优先研究权重：

```text
MOM > YOY for immediate release shock hypothesis
CORE vs HEADLINE weighting = EMPIRICAL, NOT HARDCODED BY OPINION
```

组件类数据如 shelter、energy、used vehicles、services 等先归为：

```text
HIGH_VALUE_RESEARCH / NOT_MVP_HARD_DEPENDENCY
```

只有历史增量预测价值明确时才进入实时策略。

---

## 10. NFP 研究字段

NFP 不得只看 headline payroll。

第一阶段至少：

```text
NONFARM_PAYROLLS
UNEMPLOYMENT_RATE
AVERAGE_HOURLY_EARNINGS
PRIOR_PAYROLL_REVISIONS
```

未来可增加：

```text
LABOR_FORCE_PARTICIPATION
AVERAGE_WEEKLY_HOURS
TEMP_HELP / DIFFUSION / OTHER COMPONENTS
```

但必须通过增量价值检验，禁止 indicator stacking。

---

## 11. PCE 研究字段

第一阶段至少：

```text
PCE_PRICE_MOM
CORE_PCE_MOM
PCE_PRICE_YOY
CORE_PCE_YOY
```

同时记录同一 release package 内可能影响解释的收入/支出数据，但第一版不强制进入 signal logic。

---

## 12. Internal Conflict Classification

每个 Event Family 必须允许：

```text
CLEAR_HAWKISH
CLEAR_DOVISH
INLINE
MIXED
DATA_CONFLICT
INSUFFICIENT_DATA
```

`MIXED` 必须是一等状态。

系统不得被迫在每次事件中输出 long/short。

---

## 13. Rates / Policy Repricing

### 13.1 第一核心确认层

优先研究：

```text
US 2Y / 2Y TREASURY FUTURES PROXY
```

目的：观察近端利率/政策重新定价。

生产实现时应评估“2Y cash yield”与可实时订阅的 2Y Treasury futures proxy 哪个在成本、延迟和授权上更适合。

### 13.2 Secondary

```text
US 10Y
2s10s
```

用于区分：

```text
FRONT-END POLICY SHOCK
BROAD RATE SHOCK
STEEPENING
FLATTENING
```

第一版不要求将 2s10s 作为 Hard Gate。

---

## 14. FedWatch 定位

CME FedWatch 未来值得接入，但定位固定为：

```text
POLICY_REPRICING CONFIRMATION
NOT FIRST-SUBSECOND ENTRY TRIGGER
```

研究保存：

```text
PRE_EVENT FOMC PROBABILITY DISTRIBUTION
POST_EVENT PROBABILITY DISTRIBUTION
EXPECTED_POLICY_RATE_DELTA
PROBABILITY_DELTA_BY_TARGET_RANGE
```

建议时间点：

```text
T-1D
T-60m
T-30m
T-5m
T+1m
T+2m
T+5m
T+15m
T+30m
T+60m
```

CME 当前官方产品提供 FedWatch REST API、60-second intraday stream，并提供 2015 起历史数据；具体 license/cost/usage 需工程阶段重新核验。

---

## 15. USD Confirmation

DXY 具有较高研究价值，但不是第一版绝对 Hard Dependency。

研究：

```text
DXY_DELTA
DXY_CONFIRM
DXY_DIVERGENCE
```

如果实时 DXY 数据授权/成本不合适，可在产品/工程阶段比较成熟的美元期货/FX 代理；不得自行构造复杂美元指数基础设施。

---

## 16. Tradable / Reference Assets

### 16.1 研究基准优先

```text
NQ
ES
```

原因：重大美国宏观事件通常发生在美国现金市场开盘前，NQ/ES futures 是更直接的连续事件反应基准。

### 16.2 当前 Trader Assist 可低成本观察

```text
XYZ100
SP500
BTC
ETH
```

但必须分别研究：

```text
TRACKING_LAG
BASIS
SPREAD
SLIPPAGE
EVENT_REACTION_BETA
REVERSAL_RATE
```

不得假设 Hyperliquid proxy 与 CME NQ/ES 在事件窗口完全等价。

### 16.3 当前初步研究定位

```text
NQ = PRIMARY MACRO SENSITIVITY RESEARCH BENCHMARK
ES = PRIMARY BROAD-RISK BENCHMARK
BTC/ETH = SECONDARY 24/7 TRADABLE / CONFIRMATION RESEARCH
XYZ100/SP500 = CURRENT SYSTEM SHADOW CANDIDATES SUBJECT TO EXECUTION QUALITY
```

最终交易标的必须由 execution-adjusted evidence 决定。

---

## 17. Critical Data-Resolution Decision

当前 First Launch：

```text
RAW_STRATEGY_CANDLE = 5m ONLY
FORMAL_OUTCOME = 1m ON DEMAND
```

该架构对当前三 Setup 保持不变。

但未来若要研究：

```text
T+1s
T+5s
T+10s
10–60s MICRO_PAUSE
IMMEDIATE MOMENTUM
EVENT SPREAD EXPANSION
```

仅 5m / 1m 数据不足。

因此未来 Macro Research 的低成本路线应是：

```text
EVENT-WINDOW HIGH-RES DATA ONLY
NOT FULL-DAY / FULL-UNIVERSE CONTINUOUS TICK INFRASTRUCTURE
```

目标分辨率按可得性优先：

```text
BBO / TRADE TICK
or
1s BAR + BBO SNAPSHOTS
or
5s BAR + SPREAD/DEPTH EVIDENCE
```

事件窗口示例：

```text
T-5m → T+15m high-resolution
T+15m → T+120m lower-resolution outcome
```

具体窗口必须后续通过数据成本与研究价值冻结。

---

## 18. Entry Model Research

必须分开比较，不把所有事件强制为 Full Retest。

### A. SHOCK_MOMENTUM

```text
LARGE SURPRISE
+ INTERNAL CONSISTENCY
+ FAST RATES CONFIRMATION
+ TRADABLE-ASSET ACCEPTANCE
+ EXECUTION HEALTHY
```

允许研究无 full retest 的 continuation。

### B. MICRO_PAUSE_CONTINUATION

```text
IMPULSE
→ 10–60s PAUSE / COMPRESSION
→ SECOND BREAK
```

### C. SHALLOW_PULLBACK_CONTINUATION

按：

```text
RETRACE / INITIAL_IMPULSE
```

分桶研究：

```text
0–10%
10–20%
20–33%
33–50%
>50%
```

### D. FULL_BREAKOUT_RETEST

用于较弱或较慢解释的 Event Regime，可与当前 `BREAKOUT_RETEST` 进行映射研究。

### E. FAILED_FIRST_MOVE

第一波与数据方向一致或看似一致，但价格/利率/美元确认失败并迅速回收。

当前：

```text
RESEARCH_ONLY
```

它与 `FAILED_ACCEPTED_BREAKOUT / FAILED_IMPULSE` 研究存在天然交叉，应共享证据定义但不得提前生成反向 Live Signal。

---

## 19. No-Retest 研究是核心问题

必须统计 strong event 后 initial impulse 的：

```text
NO_RETRACE
<10%
10–20%
20–33%
33–50%
FULL_RETEST
FULL_REVERSAL
```

核心比较：

```text
CONSERVATIVE = FULL RETEST ONLY
BALANCED = MOMENTUM + SHALLOW + FULL RETEST
AGGRESSIVE = IMMEDIATE MOMENTUM
```

必须回答：

```text
How much trend recall is lost by waiting for a full retest?
How much false continuation / MAE is added by earlier entry?
```

---

## 20. NO_TRADE 是核心策略能力

至少研究以下 Hard/Soft Gates：

```text
ACTUAL_NEAR_CONSENSUS
SEVERE_INTERNAL_DATA_CONFLICT
RATES_DO_NOT_CONFIRM
TRADABLE_ASSET_DOES_NOT_ACCEPT
SEVERE_CROSS_ASSET_DIVERGENCE
SPREAD_ABNORMAL
SLIPPAGE_ABNORMAL
ORDERBOOK_THINNING
INITIAL_MOVE_OVEREXTENDED
DATA_FEED_DELAYED
DATA_FEED_CONFLICT
RELEASE_TIMESTAMP_UNCERTAIN
VENUE_UNHEALTHY
```

Macro Event Strategy 的目标不是每次发布都交易。

```text
NO_TRADE = VALID SUCCESSFUL OUTPUT
```

---

## 21. Execution / Liquidity Contract

事件策略禁止只用 OHLC mid-price 回测。

至少研究：

```text
SPREAD_MULTIPLIER
BBO
DEPTH_IF_AVAILABLE
SLIPPAGE
ORDER_REJECTION
PARTIAL_FILL
PRICE_GAP
LATENCY
```

所有策略结果必须区分：

```text
THEORETICAL_PRICE_PATH
vs
EXECUTABLE_PATH
```

若历史执行数据缺失，必须输出：

```text
BACKTEST_EXECUTION_LIMITATION = YES
```

不得把理论成交结果当成生产可实现结果。

---

## 22. Pre-Event Position Boundary

第一研究版默认：

```text
NO DIRECTIONAL EVENT BET BEFORE RELEASE
```

除非未来有独立证据证明 pre-release positioning strategy 有稳定 edge，否则 Macro Strategy 的默认工作是：

```text
RELEASE → INTERPRET → CONFIRM → EXECUTE / NO_TRADE
```

---

## 23. Risk / Stop Research

第一阶段只离线比较，不提前冻结：

```text
EVENT_IMPULSE_INVALIDATION
MICROSTRUCTURE_INVALIDATION
ATR_STOP
FIXED_MAX_LOSS
TIME_STOP
```

禁止：

```text
AVERAGING_DOWN
WIDEN_STOP_BECAUSE_THE_DATA_IS_THEORETICALLY_RIGHT
IGNORE_PRICE_REVERSAL_BECAUSE_MACRO_VIEW_IS_RIGHT
```

Probe→Add 属于现有 R7 Backlog；Macro 研究可以离线比较，但不得借本项目提前建设多腿仓位引擎。

---

## 24. Historical Research Design

事件样本天然低频，必须避免过拟合。

优先：

```text
CPI: as much Point-in-Time history as reliable data allows
NFP: same
PCE: same
```

至少分层：

```text
HIKING
CUTTING
PAUSE
HIGH_INFLATION
LOW_INFLATION
HIGH_VOL
LOW_VOL
HIGH_ATTENTION
LOW_ATTENTION_IF_PROXY_AVAILABLE
```

必须保留：

```text
trial_id
hypothesis
changed_variable
dataset_cut
point_in_time_source
cost_model
delay_model
result
decision
trial_count
```

统计优先：

```text
SAMPLE_COUNT
EVENT_FAMILY_COUNT
DIRECTIONAL_ACCURACY
CONTINUATION_RATE
REVERSAL_RATE
NO_RETEST_RATE
SHALLOW_RETRACE_RATE
FULL_RETEST_RATE
MFE
MAE
TIME_TO_MFE
TIME_TO_MAE
EXPECTANCY
PAYOFF_RATIO
DRAWDOWN
EXECUTION_ADJUSTED_RETURN
```

样本允许时使用：

```text
WALK_FORWARD
OUT_OF_SAMPLE
BOOTSTRAP CI
PBO / DEFLATED SHARPE
```

---

## 25. Data Priority — MVP Complexity Control

### MUST HAVE

```text
SCHEDULED EVENT TIMESTAMP
ACTUAL
CONSENSUS
PREVIOUS / REVISION AS KNOWN AT RELEASE
POINT-IN-TIME EVENT SNAPSHOT
EVENT FAMILY
HIGH-RES EVENT PRICE PATH FOR PRIMARY RESEARCH ASSET
TRADABLE-ASSET BBO / SPREAD OR EXECUTION PROXY
US2Y OR PRACTICAL FRONT-END RATE PROXY
PRE-EVENT PRICE CONTEXT
```

### HIGH VALUE

```text
CORE/HEADLINE MULTI-FIELD EVENT LOGIC
DXY
FEDWATCH INTRADAY
US10Y
NQ + ES JOINT RESPONSE
BTC + ETH RESPONSE
PRE-EVENT IMPLIED MOVE / VIX/VXN
FORECAST DISPERSION
```

### NICE TO HAVE

```text
2s10s
MOVE
DETAILED CPI COMPONENTS
OPTIONS STRADDLE IMPLIED MOVE
ORDERBOOK DEPTH BEYOND BBO
ECONOMIST DISTRIBUTION / WHISPER
```

### NOT WORTH MVP COMPLEXITY

```text
FULL GENERAL-PURPOSE MACRO DATA PLATFORM
FULL-TIME SUBSECOND DATA FOR ALL 40 MARKETS
REAL-TIME EVENT-SPECIFIC PARAMETER OPTIMIZATION
DOZENS OF MACRO COMPONENTS AS HARD GATES
COMPLEX ECONOMIC-CALENDAR UI
CROSS-ASSET HARD-GATE DEPENDENCY GRAPH
```

---

## 26. Mature External Data Route

工程原则仍是成熟外部方案优先。

### Official authoritative release sources

```text
BLS — CPI / Employment Situation
BEA — PCE / Personal Income and Outlays
```

它们适合做 authoritative published values / archives / revision audit。

### Consensus / Point-in-Time calendar candidate

Trading Economics 当前官方 API 文档声明其 Calendar API 提供：

```text
actual
previous
consensus
forecast
historical calendar
Point-In-Time data
```

它可作为低开发成本候选，但未来工程前必须重新评估：

```text
price
latency
historical PIT coverage
license
production SLA
release-time reliability
```

### Fed repricing

```text
CME FedWatch REST API
```

当前官方说明包含 60-second intraday updates 与 2015 起历史。

### Futures market data

CME 官方 Market Data API 可作为未来 NQ / ES / Treasury futures 高质量数据候选；工程阶段必须单独评估授权、成本、non-display/automated use。

---

## 27. Important Source-Latency Rule

官方 BLS/BEA 是事实权威，不等于适合未来自动交易的最低延迟执行 feed。

未来必须把：

```text
AUTHORITATIVE SOURCE
```

与：

```text
TRADING-LATENCY DELIVERY SOURCE
```

分开评估。

不得因为某 API 能查询已发布数据，就假设它足够快、足够稳定地支持 event-time automated entry。

---

## 28. Current First Launch Engineering Boundary

当前 Engineering 正在实现的系统不得因本文件增加范围。

固定：

```text
NO CURRENT RELEASE MACRO CALENDAR ENGINE
NO CURRENT RELEASE FEDWATCH INTEGRATION
NO CURRENT RELEASE SUBSECOND DATA FEED
NO CURRENT RELEASE MACRO ENTRY STATE MACHINE
NO CURRENT RELEASE AUTO TRADE
```

当前最多允许未来通过已有时间戳离线 join Event Tag。

若当前 Evidence Pipeline 已保存足够 market timestamp / path：

```text
ADDITIONAL_CURRENT_ENGINEERING = 0
```

本 Macro 研究所需的额外高频事件数据应作为独立未来 Research Data Spike，而不是侵入当前 Runtime。

---

## 29. Future Development Path

只有历史与 Shadow 研究通过后，才按小步路线推进：

```text
PHASE M0
OFFLINE EVENT DATASET

PHASE M1
OFFLINE EVENT CLASSIFIER + ENTRY SIMULATION

PHASE M2
LIVE SHADOW EVENT OBSERVER
NO ORDERS

PHASE M3
HUMAN-CONFIRMED ASSISTED EXECUTION
IF SEPARATELY AUTHORIZED

PHASE M4
BOUNDED AUTOMATED EXECUTION
ONLY AFTER NEW STRATEGY/RISK/EXECUTION AUTHORITY
```

任何自动交易阶段都需要新的：

```text
STRATEGY CONTRACT
RISK CONTRACT
EXECUTION CONTRACT
DATA-LATENCY CONTRACT
FAIL-CLOSED / KILL-SWITCH CONTRACT
EXCHANGE WRITE AUTHORITY
```

本文件不授权这些能力。

---

## 30. Research Promotion Gates

进入未来工程开发前至少回答：

```text
1. Does standardized surprise predict subsequent executable returns?
2. Does US2Y/front-end confirmation add incremental value?
3. Does DXY add value after rates are known?
4. Does FedWatch add value beyond rates and price, despite its 60s cadence?
5. How often do strong events have no/full/shallow retest?
6. Which early-entry mode has best execution-adjusted expectancy?
7. Can FAILED_FIRST_MOVE be recognized causally before hindsight?
8. What is the false-continuation cost of Momentum Entry?
9. Which assets retain edge after real spread/slippage?
10. Does the edge survive policy/inflation regime splits?
11. Can the system output NO_TRADE often enough to avoid low-information events?
12. Is incremental strategy value greater than engineering + data cost?
```

---

## 31. Initial Strategy Recommendation

当前最值得验证的 MVP 不是“自动抢 CPI 第一秒”，而是：

```text
POINT-IN-TIME RELEASE
→ SURPRISE / MIXED CLASSIFICATION
→ FRONT-END RATE CONFIRMATION
→ TRADABLE-ASSET ACCEPTANCE
→ EXECUTION HEALTH CHECK
→
   SHOCK_MOMENTUM
   | MICRO_PAUSE
   | SHALLOW_PULLBACK
   | FULL_RETEST
   | FAILED_FIRST_MOVE_RESEARCH
   | NO_TRADE
```

FedWatch 作为较慢的 policy repricing confirmation / outcome feature，而不是首触发器。

这条路线最符合：

```text
MINIMUM DEVELOPMENT COST
EXTERNAL MATURE DATA FIRST
SMALL BATCH
RAPID VALIDATION
REAL EVIDENCE FIRST
NO PREMATURE PLATFORM
```

---

## 32. External Research Basis

本文件的方向与以下公开一手/学术来源一致：

1. CME Group — FedWatch API  
   `https://www.cmegroup.com/market-data/market-data-api/fedwatch-api.html`
   - REST API；
   - 60-second intraday stream；
   - history back to 2015；
   - CME explicitly lists CPI/NFP high-volatility algorithmic use cases.

2. CME Group — Market Data APIs  
   `https://www.cmegroup.com/market-data/market-data-api.html`
   - real-time futures/options market data API candidates.

3. U.S. BLS — CPI release schedule / CPI / Employment Situation archives  
   `https://www.bls.gov/schedule/news_release/cpi.htm`  
   `https://www.bls.gov/cpi/`  
   `https://www.bls.gov/bls/news-release/empsit.htm`

4. U.S. BEA — Release Schedule / PCE  
   `https://www.bea.gov/news/schedule`  
   `https://www.bea.gov/data/personal-consumption-expenditures-price-index`

5. Federal Reserve / Federal Reserve Bank research on high-frequency macro announcement effects, including:
   - `The High-Frequency Effects of U.S. Macroeconomic Data Releases on Prices and Trading Activity in the Global Interdealer Foreign Exchange Market`;
   - `Real-Time Price Discovery in Global Stock, Bond and Foreign Exchange Markets`;
   - `Time Variation in Asset Price Responses to Macro Announcements`;
   - `How Markets Process Macro News: The Importance of Investor Attention`.

6. Trading Economics — Calendar API  
   `https://tradingeconomics.com/api/calendar.aspx`
   - current official documentation advertises actual/previous/consensus and Point-In-Time calendar data; production suitability remains subject to later engineering verification.

---

## 33. Final Frozen Status

```text
MACRO_EVENT_STRATEGY_RESEARCH = YES
MACRO_EVENT_PRODUCT_VALUE = HIGH
PARENT_BACKLOG = R4_EVENT_REGIME
R1_R2_R3_ORDER_CHANGED = NO
PARALLEL_OFFLINE_RESEARCH = ALLOWED

CURRENT_RELEASE_IMPLEMENTATION = NO
CURRENT_RELEASE_STRATEGY_DELTA = ZERO
CURRENT_FOURTH_SETUP = NO
CURRENT_MACRO_LIVE_SIGNAL = NO
CURRENT_MACRO_AUTO_TRADE = NO

PRIMARY_FUTURE_RESEARCH_FAMILIES = CPI_NFP_PCE
FOMC_SEPARATE_FAMILY = YES
POINT_IN_TIME_DATA_REQUIRED = YES
NO_TRADE_FIRST_CLASS_OUTPUT = YES
EVENT_WINDOW_HIGH_RES_DATA_REQUIRED_FOR_SUBMINUTE_RESEARCH = YES
FULL_UNIVERSE_CONTINUOUS_TICK_PLATFORM = NO
FEDWATCH_FIRST_TRIGGER = NO
FEDWATCH_POLICY_REPRICING_CONFIRMATION = YES

FUTURE_PROMOTION_REQUIRES_EVIDENCE = YES
FUTURE_AUTO_TRADE_REQUIRES_NEW_EXPLICIT_AUTHORITY = YES
```

本文件不授权代码修改、依赖安装、数据订阅购买、生产配置修改、部署、重启、账户访问、签名、交易所写入、自动下单、PR Mark Ready 或 Merge。