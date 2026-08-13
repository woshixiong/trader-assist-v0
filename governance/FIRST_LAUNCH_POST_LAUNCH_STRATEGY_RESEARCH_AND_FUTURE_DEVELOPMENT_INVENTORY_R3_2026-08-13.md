# First Launch 上线后策略研究与未来开发完整清单 R3

**记录 ID：** `TA-FIRST-LAUNCH-POST-LAUNCH-STRATEGY-RESEARCH-FUTURE-DEV-INVENTORY-R3-2026-08-13`  
**日期：** `2026-08-13`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `CURRENT COMPLETE RESEARCH / FUTURE DEVELOPMENT INVENTORY / NON-EXECUTABLE / NON-AUTHORIZING`  
**父级：** `FIRST_LAUNCH_POST_LAUNCH_STRATEGY_RESEARCH_AND_SHADOW_EVIDENCE_BACKLOG_R1_2026-08-12.md`  
**取代关系：** 本文件取代 `FIRST_LAUNCH_POST_LAUNCH_STRATEGY_RESEARCH_AND_DEVELOPMENT_PRIORITY_ROADMAP_R2_2026-08-13.md` 中“未来优先级已经冻结”的解释。R2 保留审计与研究内容价值，但未来项目顺序必须在 First Launch 上线并取得真实 Shadow / Forward Evidence 后重新评估。

---

## 1. 当前发布决策

当前发布继续固定：

```text
CURRENT_RELEASE_NEW_STRATEGY_FEATURES = 0
CURRENT_MACHINE_PARAMETER_CHANGE = 0
NEW_FORMAL_SETUP_COMMITTED = 0
AUTO_TRADE_THIS_RELEASE = NO
```

正式三 Setup 不变：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST  # MICRO_FAST + STANDARD
RANGE_EDGE_REJECTION
```

本文件只负责：

```text
REGISTER ALL VALUABLE RESEARCH DIRECTIONS
REGISTER ALL PLAUSIBLE FUTURE DEVELOPMENT DIRECTIONS
REGISTER EVIDENCE / DEPENDENCY CONDITIONS
DO NOT FREEZE FUTURE GLOBAL PRIORITY YET
```

未来统一排序必须基于真实 Forward Evidence、工程成本、交易成本、样本独立性和用户产品目标重新决定。

---

## 2. 未来筛选原则

每个候选功能在进入开发前必须回答：

```text
1. What exact market problem does it solve?
2. Is the problem already covered by the current three Setup / Scanner / Evidence pipeline?
3. Can it be an Existing Setup Extension / Entry Mode / Regime / Ranking Feature / Execution Rule / Asset Router instead of a new Setup?
4. What does Forward / Shadow evidence say?
5. Is the evidence causal and Point-in-Time rather than hindsight?
6. Does the edge survive correlation-cluster normalization?
7. Does it improve Net Expectancy / Drawdown / MFE-MAE / Signal Quality / Execution Reliability?
8. What is incremental engineering cost and operational complexity?
9. What is incremental data cost / fee / slippage cost?
10. Is the next complexity layer justified by the previous layer's evidence?
```

固定原则：

```text
EVIDENCE_FIRST = YES
ONE_COMPLEXITY_LAYER_AT_A_TIME = YES
NEW_SETUP_IS_LAST_RESORT = YES
CURRENT_RELEASE_MUST_NOT_BE_DELAYED_BY_FUTURE_RESEARCH = YES
```

---

# A. BREAKOUT LIFECYCLE / AUCTION / MICROSTRUCTURE

## A1. Unified Breakout Lifecycle Research

把同一个底层 Breakout Event 的全部结果放进同一研究框架：

```text
MICRO_FAST_SUCCESS
STANDARD_SUCCESS
MISSED_RUNAWAY_BREAKOUT
IMMEDIATE_BREAKOUT_FAILURE
DELAYED_FAILED_ACCEPTED_BREAKOUT
AMBIGUOUS / INSUFFICIENT_DATA
```

目的：同时解决 Healthy Breakout、No-Retest、Missed Runaway、False Breakout 与 Failed Accepted Breakout，避免只研究赢家或止损单造成 selection bias。

至少比较：

```text
breakout_body_atr
breakout_volume_ratio
CLV
breakout_distance_atr
displacement_atr
outside_dwell
outside_close_count
reclaim_latency
relative_strength
session
market / asset_class
spread / slippage if available
30m / 60m / 120m MFE / MAE
ATR-normalized MFE / MAE
stop / 1R / 1.5R / 2R outcomes
```

---

## A2. Bounded 1m Breakout Research Path

高价值 Evidence 候选：

```text
QUALIFIED INITIAL BREAKOUT EVENT
→ bounded on-demand 1m research path
```

关键点：必须包含**最终没有产生 Formal Shadow Plan** 的 Initial Breakout Event。

原因：当前 Formal ShadowOrder 已有 on-demand 1m Outcome，但未来最重要的反事实问题恰恰来自未交易事件：

```text
MICRO_FAST missed runaway?
MICRO_PULLBACK existed?
TIME_ACCEPTANCE existed?
EARLIER ENTRY hypothetical MFE / MAE?
EARLIER ENTRY hypothetical drawdown?
FAST FAILURE path?
CHASE_LIMIT opportunity cost?
```

如果只保留 Formal Plans，会产生 selection bias。

实施边界：

```text
IF existing on-demand 1m collector can be directly reused
AND change is bounded
AND no new live decision logic
AND no architecture rewrite
AND no material launch delay
THEN candidate for current-release evidence-only addition
ELSE defer without blocking launch
```

禁止因此建设：

```text
FULL-UNIVERSE CONTINUOUS 1m
FULL-UNIVERSE TICK
FULL-UNIVERSE L2 ARCHIVE
```

未来真正实施前由 Engineering 独立估算：触发范围、窗口长度、API load、storage growth、backfill/restart semantics、failure isolation、tests 和预计工时。

---

## A3. Strong / No-Retest Breakout Coverage Audit

当前 `BREAKOUT_RETEST.MICRO_FAST` 已覆盖主要的无 Pullback Start + outside continuation，因此：

```text
NEW_MOMENTUM_SETUP_REQUIRED = NO
```

未来只研究现有 coverage 是否存在经济上显著的缺口。

---

## A4. MICRO_PULLBACK Entry Mode

研究 5m 内部的 1m / sub-5m shallow retracement 是否能够：

- 比当前 5m Micro FAST 获得更好的 entry；
- 降低 MAE / stop distance；
- 同时不过度增加 false continuation。

当前：`RESEARCH_ONLY`。

---

## A5. TIME_ACCEPTANCE / OUTSIDE MICRO-BALANCE

研究：

```text
OLD BALANCE
→ DISPLACEMENT
→ OUTSIDE MICRO-BALANCE
→ MICRO-BALANCE BREAK
→ CONTINUATION
```

重点字段：

```text
micro_balance_width_atr
micro_balance_duration
outside_dwell_seconds / bars
distance_from_old_edge_atr
micro_support / resistance hold
```

当前：`RESEARCH_ONLY`。

---

## A6. MISSED_VALID_BREAKOUT / Chase Economics

`MISSED_VALID_BREAKOUT` 是合法 Outcome，不以 capture 100% 行情为目标。

研究当前 Chase 区间：

```text
<= 0.75 ATR
0.75-1.50 ATR
> 1.50 ATR
```

仅作为 sensitivity / opportunity-cost research，当前参数不改。

核心比较：

```text
missed-runaway opportunity cost
vs
false-breakout loss
vs
slippage / fee
vs
MAE / drawdown increase
```

---

## A7. BREAKOUT_PROBE

最后才考虑的条件分支。

至少比较：

```text
NAKED BOUNDARY TRIGGER
BUFFERED TRIGGER
BUFFERED SMALL PROBE
BUFFERED PROBE + ACCEPTANCE ADD
```

不得实现：

```text
boundary crossed → full-size blind market entry
```

只有 A1-A6 的真实 evidence 证明 missed-runaway economics 足够大，才值得进入 Shadow / execution research。

---

## A8. FAST_FAILURE_EXIT / Breakout Logical Invalidation

研究 Probe 或更早 Breakout entry 后：

```text
trigger
→ immediate reclaim
→ structural failure before wide hard stop
```

候选研究：

```text
1m close back inside old range
accepted re-entry
penetration depth back inside
reclaim duration
micro-support failure
future OFI reversal if later available
```

与现有 `LOGICAL_INVALIDATION_EXIT` 共享研究框架；当前不改变正式 Stop。

---

## A9. AUCTION_REGIME / EDGE_TEST Taxonomy

研究状态：

```text
BALANCE
EDGE_TEST
FAILED_AUCTION
ACCEPTED_BREAK
REBALANCE
```

用途：统一解释 Range / Sweep / Breakout，并研究同一 Range Edge 上：

```text
REJECTION → range / sweep side
ACCEPTANCE → breakout side
```

当前仅：`RESEARCH / ATTRIBUTION`，不得成为 Hard Gate。

---

## A10. RANGE_EDGE_REJECTION Information Strength

研究假设：Range Edge 在交易时尚未证明 Reject / Accept，因此信息强度可能低于已完成 Failed Auction 或 Accepted Breakout 的 Setup。

未来只通过 Forward Evidence 判断是否影响：

```text
ranking
confidence
reference size
```

当前 Formal 权限与参数不改。

---

## A11. ADVANCED L2 / ORDER FLOW / BOOK RESILIENCY

只有低成本 price / candle / volume / BBO / 1m evidence 已证明明确问题仍无法区分时才考虑：

```text
aggressive buy/sell volume
trade intensity
CVD
OFI
queue imbalance
multi-level OFI
cancellation
replenishment
book resiliency
depth within 5/10/20 bps
```

不得为了理论完整性提前建设常驻 L2 平台。

---

## A12. Breakout Execution / Hyperliquid Order Semantics

未来 Probe / fast entry 进入 execution research 后必须比较：

```text
Stop Market
Stop Limit
marketable limit / IOC where applicable
```

并考虑：

```text
Mark Price trigger semantics
spread expansion
slippage
book thinning
partial / failed fill risk
asset-class liquidity
fee class
```

不能只用 OHLC 假设事件瞬间可成交。

---

# B. MARKET-SPECIFIC TIMEFRAME / PROFILE

## B1. PER_MARKET_STABLE_TIMEFRAME_PROFILE

继续研究：

```text
FAST_5M_PROFILE
vs
future slower stable intraday profile
```

不同市场的第二 Profile 必须重新冻结完整 Machine Semantics，不允许简单把 5m 参数乘倍数。

当前：

```text
REALTIME_DYNAMIC_TIMEFRAME_SWITCH = NO
```

---

# C. RELATIVE STRENGTH / CROSS-MARKET / CORRELATION

## C1. Sector / Peer Relative Strength

当前 Scanner 已有基础 cross-sectional RS；未来研究 Peer / Sector 增量，例如：

```text
MEMORY: SKHX / MU / SNDK / DRAM
SEMICONDUCTOR: NVDA / AMD / MU / ...
CRYPTO_CORE: BTC / ETH / SOL / HYPE / XRP
INDEX_CONTEXT: XYZ100 / SP500
```

优先作为 Ranking / Attribution，非 Hard Gate。

---

## C2. Cross-Market Confirmation Soft Context

研究同方向 peer / index / crypto leader 的支持程度是否改善：

```text
ranking
leader selection
failed-breakout prediction
confidence context
```

不得因为 benchmark/peer 数据缺失让本标的合格 Formal Signal 直接失效。

---

## C3. Correlation / Exposure Governance

继续要求：

```text
RAW MARKET LEVEL
SETUP RESEARCH CLUSTER
EXPOSURE CLUSTER
CLUSTER-NORMALIZED
LEADER-ONLY
```

未来半自动/自动交易才讨论：

```text
ONE_NEW_POSITION_PER_EXPOSURE_CLUSTER
or
SHARED_RISK_BUDGET_PER_EXPOSURE_CLUSTER
```

---

# D. SCHEDULED U.S. MACRO EVENT RESEARCH

父子合同继续使用：

`FIRST_LAUNCH_SCHEDULED_US_MACRO_EVENT_STRATEGY_RESEARCH_AND_FUTURE_AUTOMATION_BACKLOG_R1_2026-08-12.md`

当前只研究，不进入 First Launch。

## D1. Point-in-Time Macro Dataset / Surprise Vector

初始：

```text
CPI
NFP
PCE
```

保存 Point-in-Time：

```text
actual
consensus
previous
revisions
scheduled timestamp
source / version
```

研究：

```text
raw surprise
historically standardized surprise
multi-variable surprise vector
```

CPI 与 NFP 不允许简化成单一 headline。

---

## D2. Forecast Disagreement / Distribution

研究：

```text
forecast dispersion
forecast range
IQR / std where available
full probability distribution where available
```

目的：区分相同 consensus surprise 在“预测高度一致”与“预测高度分歧”时的信息含量。

---

## D3. Monetary Policy Uncertainty / Policy Sensitivity

研究同样 surprise 在不同阶段对 US2Y / Fed path 的敏感度变化：

```text
rolling event-to-US2Y sensitivity
policy-path uncertainty
FedWatch distribution / entropy / expected-rate delta where available
```

不假定 CPI / NFP 的权重跨 regime 恒定。

---

## D4. Investor Attention / Overreaction

研究高关注时期：

```text
stronger initial response?
more overreaction?
higher FAILED_FIRST_MOVE probability?
```

可能代理包括 event volume / options / news-attention or other mature external measures；具体代理需后续研究，不先开发。

---

## D5. FedWatch

定位：

```text
lagged policy repricing confirmation
NOT first-second trigger
```

研究 T-1d / T-60m / T-5m 与 T+1/5/15/30/60m 的政策概率变化及其对后续方向的增量价值。

---

## D6. Prediction-Market Macro Distribution

研究 Kalshi 或其他成熟、合规、Point-in-Time prediction-market distribution 是否比单一 survey median 提供额外信息。

当前仅数据源/研究候选；未来必须单独评估：

```text
historical availability
licensing
cost
latency
API stability
commercial / non-display rights
```

---

## D7. Interpretation Assets vs Trade Assets

固定研究原则：

```text
MACRO_INTERPRETATION_ASSET != TRADE_ASSET
```

Interpretation candidates：

```text
US2Y / front-end rates
DXY
NQ
ES
FedWatch lagged
```

Trade candidates：

```text
NQ / ES benchmarks
Hyperliquid XYZ100 / SP500
high-beta sector / selected single names
BTC / ETH
```

禁止固定 `CPI → ETH` 或 `CPI → NQ`。

---

## D8. EVENT ASSET ROUTER

研究：

```text
normalized event move
event relative-strength rank
impulse retention
price acceptance
follow-through
spread
slippage
depth
fee
idiosyncratic catalyst risk
```

目标：Macro Direction 形成后，选择最佳 risk-adjusted trade expression。

---

## D9. Macro-Pure vs Sector-Amplifier

比较：

```text
INDEX / BROAD MARKET = macro-pure expression
HIGH-BETA SECTOR / SINGLE NAME = sector-amplifier expression
```

必须控制 earnings / M&A / analyst / company / sector-specific catalyst 污染。

---

## D10. Event Leader / Laggard

研究：

```text
leader confirms → laggard later catches up?
laggard weakness = avoid signal?
sector leader vs index leader?
crypto divergence vs equity acceptance?
```

仅作为研究，不直接形成 cross-market Hard Gate。

---

## D11. Macro Entry Models

第一阶段候选：

```text
SECOND-STAGE CONTINUATION
MICRO-PAUSE CONTINUATION
SHALLOW-PULLBACK CONTINUATION
FULL RETEST
FAILED FIRST MOVE
NO_TRADE
```

Immediate first-second news race 不作为第一版主要竞争区域。

---

## D12. Macro NO_TRADE Engine

研究：

```text
actual approximately consensus
headline/core or multi-variable conflict
US2Y / rates non-confirmation
cross-asset conflict
spread/slippage abnormal
feed delay/corruption
venue unhealthy
first move excessively extended
```

目标不是每次宏观事件都产生交易。

---

## D13. Event-Window High-Resolution Data

如需研究 T+1s / T+5s / T+10s / 10-60s Micro-Pause，只允许优先考虑：

```text
EVENT-WINDOW HIGH-RES DATA ONLY
```

不建设全市场持续 sub-second 平台。

---

## D14. Event Execution Quality

必须研究：

```text
spread expansion
slippage
depth
latency
partial / failed fills
realized execution price
```

禁止将 mid-price OHLC 回测视为真实可成交表现。

---

## D15. NQ / ES vs Hyperliquid Index Tracking

如果实际交易使用 Hyperliquid XYZ100 / SP500，而 interpretation 使用 CME NQ / ES，必须研究事件窗口：

```text
tracking lag
basis
spread
slippage
reaction speed
price acceptance consistency
```

不得假设两者完全同步。

---

## D16. FOMC Separate Event Family

FOMC 包含：

```text
rate decision
statement
SEP / dot plot
press conference
Q&A
```

不得与 CPI/NFP/PCE 使用同一个单阶段模型。

---

## D17. Pre-Announcement Drift

可以研究发布前价格 drift 作为 attribution / expectation state，但当前固定：

```text
PRE_EVENT_DIRECTIONAL_BET = NO
```

不把潜在信息优势/泄漏现象当作可复制 edge。

---

## D18. Macro Event Volatility / Options Branch

长期独立研究候选：

```text
realized event move
vs
pre-event implied move
```

可能涉及 straddle / strangle / defined-risk options structures。

这是不同于 directional Event Strategy 的独立产品方向；只有 future product scope、options data、IV surface、execution capacity 足够时再评估，当前不开发。

---

# E. CASH OPEN / SESSION REPRICING

## E1. Cash Open / Opening Repricing

研究：

```text
PREMARKET TREND
→ CASH OPEN CONTINUATION
or
→ CASH OPEN FAILURE / REPRICING
```

优先作为 Session Regime / Attribution，不立即新增 Setup。

---

# F. EXIT / POSITION MANAGEMENT

## F1. Logical Invalidation Exit

离线比较：

```text
CURRENT HARD / STRUCTURAL STOP
vs
HYPOTHETICAL LOGICAL INVALIDATION EXIT
```

研究是否减少 MAE / Drawdown，同时避免过早退出最终成功交易。

---

## F2. Probe → Add / Continuous Confirmation-to-Size

研究：

```text
first confirmation → small probe
further acceptance → add
```

核心思想：Entry Confirmation 与 Position Size 连续化，而不是 only 0% / 100%。

进入真实开发前必须证明收益足以覆盖 multi-leg risk reservation / weighted entry / fill-state / aggregate-stop 复杂度。

---

# G. COST / EXECUTION MODEL

## G1. Post-Launch Cost Model R2

未来研究：

```text
actual account fee
TT / MT / MM
Gross vs Net Expectancy
Cost / Opportunity Ratio
Maker / Taker routing
```

不得在当前发布扩大为复杂账户级 Fee Engine。

---

# H. SHADOW / RESEARCH GOVERNANCE

## H1. Complete Sample Retention

研究必须保留：

```text
Taken
Skipped
Rejected
Unlabeled
Successful
Failed
No-Plan / Missed
```

禁止只研究赢家、止损单或实际人工执行订单。

---

## H2. Counterfactual Shadow Research

对可重建 path 离线模拟：

```text
alternative entry timing
micro-pullback / time-acceptance hypothetical entries
breakout probe hypothetical entries
logical invalidation exit
probe-add
failed-first-move reverse outcome
```

所有结果必须明确标记 `HYPOTHETICAL / RESEARCH_ONLY`，不得与真实 ShadowOrder 混淆。

---

## H3. Research Statistics

主口径包括：

```text
sample size
independent cluster count
market diversity
setup / mode mix
win rate
expectancy
profit factor
MFE / MAE
drawdown
stop rate
time-to-MFE
1R / 1.5R / 2R
fee / slippage adjusted Net R
missed-opportunity rate
data completeness
```

相关市场主统计使用 `CLUSTER-NORMALIZED`。

---

## H4. Experiment Registry / Anti-Overfitting

每个实验记录：

```text
trial_id
hypothesis
changed_variable
dataset_cut
cost_model
delay_model
result
decision
trial_count
```

样本允许时使用：

```text
walk-forward
out-of-sample
bootstrap confidence intervals
PBO
Deflated Sharpe Ratio
```

---

# I. 当前明确不做

```text
NO FOURTH SETUP NOW
NO CURRENT MACHINE PARAMETER CHANGE
NO NEW MOMENTUM SETUP NOW
NO AUCTION HARD GATE NOW
NO LIVE MICRO_PULLBACK / TIME_ACCEPTANCE NOW
NO LIVE BREAKOUT_PROBE NOW
NO CONTINUOUS FULL-UNIVERSE 1m/tick/L2 NOW
NO L2/OFI/CVD/QUEUE ENGINE NOW
NO REALTIME DYNAMIC TIMEFRAME NOW
NO MACRO LIVE STRATEGY NOW
NO EVENT ASSET ROUTER LIVE NOW
NO MACRO AUTO-TRADING NOW
NO PRE-EVENT DIRECTIONAL BET
NO CROSS-MARKET HARD GATE NOW
```

---

# J. 未来优先级状态

用户当前决策：

```text
FUTURE_GLOBAL_PRIORITY = NOT YET FROZEN
```

未来排序依据：

```text
POST-LAUNCH FORWARD EVIDENCE
+ MARGINAL STRATEGY VALUE
+ DRAWNDOWN / MFE-MAE IMPROVEMENT
+ EXECUTION RELIABILITY
+ ENGINEERING COST
+ DATA COST
+ LAUNCH / OPERATIONS RISK
```

允许先并行进行不影响系统的离线历史研究，但任何实时开发必须重新经过 Product / Strategy / Engineering 取舍。

当前唯一特殊候选是 `A2 Bounded 1m Breakout Research Path`：它可能防止不可恢复的研究证据永久丢失，因此允许先向 Engineering 询问复用成本与开发量；是否加入本轮由用户在收到 Engineering 估算后另行决定。

---

# K. Authority Boundary

本文件不授权代码修改、依赖安装、数据订阅购买、部署、重启、账户访问、签名、交易所写入、自动交易、PR Mark Ready 或 Merge。
