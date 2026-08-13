# First Launch Scheduled U.S. Macro Event Strategy Research and Future Automation Backlog R1

**记录 ID：** `TA-FIRST-LAUNCH-SCHEDULED-US-MACRO-EVENT-RESEARCH-R1-2026-08-12`  
**更新日期：** `2026-08-13`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `POST-LAUNCH STRATEGY RESEARCH CONTRACT / NON-EXECUTABLE / NON-AUTHORIZING`  
**父级 Backlog：** `FIRST_LAUNCH_POST_LAUNCH_STRATEGY_RESEARCH_AND_SHADOW_EVIDENCE_BACKLOG_R1_2026-08-12.md` → Current R2 Roadmap `R4 = SCHEDULED MACRO EVENT + EVENT ASSET ROUTER`  
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
Consensus / prior / revisions / policy prior / implied move

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
```

Forecast distribution / major-bank forecasts / whisper / prediction-market distribution 属于 High Value，但不得成为第一版阻塞依赖。

NFP 与 CPI 必须视为多变量 release，而不是单一 headline：

```text
CPI: headline/core MoM/YoY + revisions/components if incremental value exists
NFP: payroll/unemployment/AHE/revisions
```

---

## 6. Policy Interpretation

优先研究：

```text
US2Y / front-end rate response
DXY
FedWatch probability delta as lagged policy-repricing confirmation
```

FedWatch 不作为 sub-second entry trigger。

需要研究 Event-specific / regime-dependent `POLICY_SENSITIVITY`，避免假定同样 surprise 在所有年份具有相同影响。

---

## 7. Interpretation Asset 与 Trade Asset 必须分离

当前新增正式研究原则：

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

## 8. EVENT ASSET ROUTER Research

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

## 9. Macro Pure vs Sector Amplifier

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

---

## 10. Entry Regimes

第一阶段研究四类：

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

## 11. Event Window Data

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

## 12. NO_TRADE Gate

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

## 13. Execution / Risk

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

## 14. 研究优先级与成熟度

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

## 15. 当前禁止

```text
NO CURRENT RELEASE CODE
NO NEW FOURTH SETUP
NO EVENT-SPECIFIC MACHINE PARAMETERS
NO FEDWATCH PURCHASE REQUIRED NOW
NO FULL MACRO DATA PLATFORM
NO FULL-UNIVERSE TICK INFRASTRUCTURE
NO LIVE EVENT ASSET ROUTER
NO PRE-EVENT DIRECTIONAL BET
NO AUTO TRADE
```

---

## 16. 与当前 Strategy Roadmap 的关系

当前统一 Post-Launch Roadmap：

```text
R1 BREAKOUT LIFECYCLE OPTIMIZATION
R2 PER_MARKET_STABLE_TIMEFRAME_PROFILE
R3 SECTOR / PEER RELATIVE STRENGTH
R4 SCHEDULED MACRO EVENT + EVENT ASSET ROUTER
R5 CASH OPEN / OPENING REPRICING
R6 LOGICAL INVALIDATION EXIT
R7 POSITION ENTRY SCALING / PROBE→ADD
R8 CROSS-MARKET CONFIRMATION SOFT SCORE
R9 ADVANCED L2 / OFI / BOOK RESILIENCY
```

本文件只负责 R4，不改变当前发布。

---

## 17. Authority Boundary

本文件不授权代码修改、工程派发、依赖安装、数据订阅购买、部署、重启、账户访问、签名、交易所写入、自动交易、PR Mark Ready 或 Merge。