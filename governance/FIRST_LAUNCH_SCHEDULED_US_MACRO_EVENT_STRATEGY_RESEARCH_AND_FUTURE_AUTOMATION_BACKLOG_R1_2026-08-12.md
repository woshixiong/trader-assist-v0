# First Launch Scheduled U.S. Macro Event Strategy Research and Future Automation Backlog R1

**记录 ID：** `TA-FIRST-LAUNCH-SCHEDULED-US-MACRO-EVENT-RESEARCH-R1-2026-08-12`  
**更新日期：** `2026-08-13`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `POST-LAUNCH STRATEGY RESEARCH CONTRACT / NON-EXECUTABLE / NON-AUTHORIZING`  
**父级 Backlog：** `FIRST_LAUNCH_POST_LAUNCH_STRATEGY_RESEARCH_AND_SHADOW_EVIDENCE_BACKLOG_R1_2026-08-12.md`；完整候选登记服从 `FIRST_LAUNCH_POST_LAUNCH_STRATEGY_RESEARCH_AND_FUTURE_DEVELOPMENT_INVENTORY_R3_2026-08-13.md`。  
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
→ EVENT ASSET SELECTION
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

SCHEDULED_MACRO_EVENT_RESEARCH = YES
EVENT_ASSET_ROUTER_RESEARCH = YES
HIGH_PRODUCT_VALUE = YES
PARALLEL_OFFLINE_RESEARCH_ELIGIBLE = YES
CURRENT_RELEASE_SCOPE_CHANGED = NO
FUTURE_PRIORITY = NOT_YET_FROZEN
```

本文件不改变当前正式三 Setup：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST  # Micro FAST + Standard
RANGE_EDGE_REJECTION
```

也不改变当前 40-market / 5m-only release route。

---

## 2. 核心因果架构

未来研究不应把全部信息压成一个无解释的总分。

优先保留因果顺序：

```text
L0 PRE-EVENT EXPECTATION
Consensus / prior / revisions / policy prior / implied move / expectation distribution

L1 RELEASE INTERPRETATION
standardized surprise vector / internal conflict

L2 POLICY / MACRO INTERPRETATION
US2Y / front-end rates / DXY / FedWatch lagged confirmation

L3 TRADEABLE MARKET ACCEPTANCE
NQ / ES / BTC / ETH / Hyperliquid index & selected high-beta markets

L4 EXECUTION QUALITY
spread / depth / slippage / price acceptance

L5 ENTRY ROUTER
continuation / pullback / retest / failed first move / NO_TRADE
```

---

## 3. Event Family

第一阶段：

```text
CPI
NFP
PCE
```

FOMC 作为多阶段政策事件必须独立研究，不与 CPI/NFP/PCE 使用同一个简单模型。

---

## 4. Point-in-Time Event Metadata

至少保存：

```text
event_id
event_name
event_family
scheduled_timestamp
timezone
data_source
data_version
revision_status
market_session
relevant_policy_meeting if applicable
```

禁止用最终修订数据替代当时真实可见值做历史回测。

---

## 5. Expectation / Surprise

MVP 必须：

```text
actual
consensus
previous
revised_previous if known at that time
```

研究：

```text
RAW_SURPRISE
HISTORICALLY_STANDARDIZED_SURPRISE
FORECAST_DISPERSION_ADJUSTED_SURPRISE
MULTI_VARIABLE_SURPRISE_VECTOR
```

Forecast distribution / major-bank forecasts / whisper / prediction-market distribution 属于 High Value，但不得成为第一版阻塞依赖。

NFP 与 CPI 必须视为多变量 release，而不是单一 headline：

```text
CPI: headline/core MoM/YoY + revisions/components if incremental value exists
NFP: payroll/unemployment/AHE/revisions
```

---

## 6. Forecast Disagreement / Distribution

研究：

```text
forecast range
std / IQR where available
forecaster disagreement
full probability distribution where available
```

目标：判断同样大小的 `Actual - Consensus` 在 forecast 高度集中与高度分歧时，信息冲击是否不同。

不预设 `surprise / dispersion` 一定是最优公式；分别保存 surprise magnitude 与 disagreement，避免过早压缩成单一分数。

---

## 7. Policy Interpretation / Policy Sensitivity / Uncertainty

优先研究：

```text
US2Y / front-end rate response
DXY
FedWatch probability delta as lagged policy-repricing confirmation
```

FedWatch 不作为 sub-second entry trigger。

需要研究 Event-specific / regime-dependent：

```text
POLICY_SENSITIVITY
MONETARY_POLICY_UNCERTAINTY
```

例如滚动估计 standardized CPI / NFP surprise 对 US2Y 的响应，并研究 FedWatch probability distribution / expected policy rate / entropy 等是否提供增量信息。

禁止假定同样 surprise 在所有年份具有相同影响，或 CPI / NFP 的相对重要性恒定。

---

## 8. Investor Attention / Overreaction

独立研究候选：

```text
ATTENTION HIGH
→ larger first reaction?
→ greater continuation?
→ greater overreaction / FAILED_FIRST_MOVE?
```

具体 attention proxy 以后再选择，可研究 mature external measures、event options/volume/news attention 等；当前不因此新增数据平台。

该方向可与 `FAILED_FIRST_MOVE` / `FAILED_ACCEPTED_BREAKOUT` 共享研究方法，但不能因为理论关联直接产生反向交易规则。

---

## 9. Interpretation Asset 与 Trade Asset 必须分离

当前正式研究原则：

```text
MACRO_INTERPRETATION_ASSET != TRADE_ASSET
```

Interpretation Assets 用于回答“市场如何解释数据”：

```text
US2Y / front-end rates
DXY
NQ
ES
```

Trade Assets 用于回答“当前哪个资产以最好风险调整后的方式表达该方向”：

```text
INDEX:
NQ / ES benchmarks
Hyperliquid XYZ100 / SP500 where eligible

HIGH-BETA / SECTOR:
selected registry markets such as MU / SNDK / SKHX / NVDA / AMD

CRYPTO:
BTC / ETH
```

禁止固定：

```text
CPI → always trade ETH
CPI → always trade NQ
```

---

## 10. EVENT ASSET ROUTER Research

未来研究：

```text
EVENT_RELATIVE_STRENGTH
NORMALIZED_EVENT_MOVE
IMPULSE_RETENTION
OUTSIDE / DIRECTIONAL ACCEPTANCE
FOLLOW_THROUGH
SPREAD
SLIPPAGE
DEPTH
FEE
IDIOSYNCRATIC_CATALYST_RISK
```

目标：在 Macro Direction 已经形成后，对候选资产进行 tradeability ranking。

需要明确：

```text
STRONGEST_PRICE_MOVE != BEST_TRADE
```

高 beta 个股/HIP-3 市场可能拥有更大 gross move，但也可能拥有更高 fee、spread、slippage 和个体事件污染。

---

## 11. Macro Pure vs Sector Amplifier / Leader-Laggard

研究两类表达：

```text
MACRO_PURE:
index / broad market expression

SECTOR_AMPLIFIER:
high-beta sector / single-name expression
```

比较：

```text
Net Expectancy
MFE / MAE
False Move Rate
Execution Cost
Slippage
Event-specific catalyst contamination
```

个股/行业当天存在 earnings、M&A、analyst、sector-specific catalyst 时必须记录或排除，避免把 idiosyncratic move 错归因于 CPI/NFP/PCE。

同时研究：

```text
leader confirms → laggard catches up?
laggard weakness → avoid?
sector leader vs index leader
crypto divergence vs equity acceptance
```

不得直接升级为 Cross-Market Hard Gate。

---

## 12. Prediction-Market Macro Distribution

未来研究 Kalshi 或其他成熟、合规 prediction market 是否能提供：

```text
continuous expectation
high-frequency probability distribution
market-implied tail probability
```

其价值可能高于仅增加多个银行点预测，但进入工程前必须独立评估：

```text
historical PIT availability
license / terms
cost
latency
rate limits
API stability
commercial / non-display use
```

当前不购买、不开发。

---

## 13. Entry Regimes

第一阶段研究：

```text
A. SECOND-STAGE CONTINUATION
B. MICRO-PAUSE / SHALLOW PULLBACK CONTINUATION
C. FULL RETEST using existing Breakout concepts
D. FAILED FIRST MOVE
```

以及始终允许：

```text
NO_TRADE
```

Immediate first-second news race 不作为第一版主要竞争区域。

---

## 14. Event Window Data

当前 First Launch 仍为 5m strategy route。

未来 Macro Research 如需研究：

```text
T+1s / T+5s / T+10s
10–60s micro pause
spread expansion
```

只允许优先考虑：

```text
EVENT-WINDOW HIGH-RES DATA ONLY
```

例如仅对 CPI/NFP/PCE 的有限事件窗口采集 trades/BBO/high-resolution path，而不是建设全市场持续 sub-second 平台。

---

## 15. NO_TRADE Gate

至少研究：

```text
actual approximately consensus
internal release conflict
rates non-confirmation
cross-asset severe conflict
spread abnormal
slippage abnormal
feed delay/corruption
execution venue unhealthy
first move excessively extended
```

系统不承担“每次宏观发布都必须交易”的目标。

---

## 16. Execution / Risk

Event backtest 不允许只用 OHLC mid-price 假设成交。

至少研究：

```text
spread expansion
slippage
depth
latency
partial / failed fills where relevant
```

预发布默认不做方向性数据赌博。

Probe / scale-in 仍属于未来 Execution Rule，不能因为 Macro Strategy 研究提前建设多腿 Position Engine。

---

## 17. NQ / ES vs Hyperliquid Index Tracking

如果 interpretation 使用 CME NQ / ES，而实际 trade expression 使用 Hyperliquid XYZ100 / SP500，必须研究事件窗口：

```text
tracking lag
basis
spread
slippage
reaction speed
price acceptance consistency
```

不得假设 CME benchmark 与 Hyperliquid perpetual 完全同步。

---

## 18. Pre-Announcement Drift

可以作为 expectation-state / attribution 研究，但当前固定：

```text
PRE_EVENT_DIRECTIONAL_BET = NO
```

不把潜在 proprietary forecast / information leakage 当作可复制 edge。

---

## 19. Event Volatility / Options Independent Branch

长期独立研究候选：

```text
REALIZED EVENT MOVE
vs
PRE-EVENT IMPLIED MOVE
```

可能涉及 straddle / strangle / defined-risk options structures。

该方向需要 options data、IV surface、expiry/gamma/theta/vega 和独立 execution 研究，复杂度显著高于当前 directional Event Strategy，因此只登记，不进入当前开发。

---

## 20. Research Maturity Path

不是冻结的全局开发优先级，只是本模块内部从证据到自动化的成熟度顺序：

```text
M0 = PIT historical event dataset
M1 = surprise + rates + cross-asset event study
M2 = event asset selection / leader-laggard study
M3 = continuation / failure entry simulation
M4 = live shadow event observer
M5 = human-confirmed assisted execution
M6 = bounded automation only after independent evidence and new authority
```

---

## 21. 当前禁止

```text
NO CURRENT RELEASE CODE
NO NEW FOURTH SETUP
NO EVENT-SPECIFIC MACHINE PARAMETERS
NO FEDWATCH PURCHASE REQUIRED NOW
NO PREDICTION-MARKET PURCHASE REQUIRED NOW
NO FULL MACRO DATA PLATFORM
NO FULL-UNIVERSE TICK INFRASTRUCTURE
NO LIVE EVENT ASSET ROUTER
NO PRE-EVENT DIRECTIONAL BET
NO EVENT-VOLATILITY OPTIONS ENGINE NOW
NO AUTO TRADE
```

---

## 22. Authority Boundary

本文件不授权代码修改、工程派发、依赖安装、数据订阅购买、部署、重启、账户访问、签名、交易所写入、自动交易、PR Mark Ready 或 Merge.