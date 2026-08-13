# First Launch Event-Aware Overlay 与 Scheduled Boundary Risk 收敛合同 R1

**记录 ID：** `TA-FIRST-LAUNCH-EVENT-AWARE-BOUNDARY-RISK-CONVERGENCE-R1-2026-08-13`  
**日期：** `2026-08-13`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `POST-FIRST-LAUNCH STRATEGY / RISK RESEARCH AUTHORITY / NON-EXECUTABLE / NON-AUTHORIZING`

---

## 1. 收敛结论

未来策略研究只保留两个明确方向：

```text
A. EVENT-AWARE PRICE-ACTION OVERLAY
B. SCHEDULED MARKET BOUNDARY RISK
```

当前正式 Alpha / Entry Authority 仍只有三个 Setup：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST  # MICRO_FAST + STANDARD
RANGE_EDGE_REJECTION
```

本文件不增加第四 Setup，不修改当前 Machine Strategy，不进入当前 First Launch 实现。

核心原则：

```text
PRICE-ACTION SETUPS = PRIMARY TRADE AUTHORITY
EVENT / SESSION = CONTEXT + RISK + ATTRIBUTION
```

---

# A. EVENT-AWARE PRICE-ACTION OVERLAY

## 2. Event 不建立平行的形态策略体系

宏观数据、公司财报、FOMC、Guidance、Earnings Call 等事件会改变信息环境，但大部分可交易价格几何仍可由现有三个 Setup 覆盖。

因此以下不再作为独立 Event Setup：

```text
PRE_EVENT_TREND_ENTRY
POST_EVENT_CONTINUATION
SELL_THE_FACT_SETUP
EARNINGS_CONTINUATION_SETUP
PREMARKET / AFTER_HOURS / OVERNIGHT SETUP
TREND_HOLD / EXIT / REENTRY
MICRO_PULLBACK / TIME_ACCEPTANCE as Event-only logic
```

事件前市场已经出现的预期定价，如形成有效 Sweep / Breakout / Range 信号，原则上继续使用普通三 Setup 交易；不得因为未来有 Scheduled Event 就粗暴长期屏蔽所有此前信号。

`BUY EXPECTATION / SELL FACT` 只作为研究 Attribution，不是直接交易口诀。

## 3. Event Overlay 真正保留的差异

### 3.1 Scheduled Information Identity

保存：

```text
event_id
event_family
issuer / macro family
scheduled_time
actual_release_time where known
stage
source
```

### 3.2 Information Context / Attribution

Macro 可记录：

```text
actual / consensus / revisions
surprise vector
rates / DXY / benchmark response
```

Earnings 可记录：

```text
EPS / revenue / guidance / company-specific KPI
release / call / Q&A stage
```

这些第一阶段用于解释和研究，不直接替代三个 Setup 产生 Long / Short。

### 3.3 Multi-stage Event Awareness

FOMC、Earnings 等事件可能具有：

```text
RELEASE
→ GUIDANCE / SEP
→ CALL / PRESS CONFERENCE
→ Q&A
```

系统未来应知道下一次已知信息节点仍在前方；但是否持仓跨越该节点统一服从 `SCHEDULED MARKET BOUNDARY RISK`。

### 3.4 Event-specific feature promotion rule

任何 Event feature 只有在 Forward / Historical / Shadow Evidence 证明其对现有 Setup 有稳定的增量价值后，才允许从 Attribution/Context 升级为 Signal/Ranking/Gate。

必须比较：

```text
BASE SETUP
vs
BASE SETUP + EVENT FEATURE
```

并至少评估：

```text
Net Expectancy
MFE / MAE
Failure Rate
Drawdown
Execution Cost
Out-of-sample stability
```

## 4. Asset Selection 收敛

Macro 的最佳 Trade Expression 可能跨资产，但第一阶段优先使用现有 Scanner / Relative Strength / Liquidity / Correlation 机制。

Earnings 的信息主体由 issuer 固定，peer / sector / index 仅作为 bounded comparison。

因此：

```text
NEW LIVE EVENT ASSET ROUTER = NOT REQUIRED NOW
```

只有数据证明普通 Scanner 在 Event Window 系统性选错表达，才重新升级 Event-specific ranking。

---

# B. SCHEDULED MARKET BOUNDARY RISK

## 5. 这是所有策略共用的 Risk Overlay，不是 Event 专属

已知高风险边界不仅包括 CPI / NFP / Earnings 等信息发布，也包括全球主要交易时段参与者和流动性重新集中时点。

当前人工交易原则冻结为：

```text
ASIA OPEN BOUNDARY
EUROPE OPEN BOUNDARY
US OPEN BOUNDARY

DEFAULT = DO NOT CARRY ORDINARY POSITION THROUGH THE BOUNDARY
DEFAULT = FLATTEN / DE-RISK BEFORE BOUNDARY
EXCEPTION = HUMAN-APPROVED SPECIAL CASE ONLY
```

这条纪律适用于所有三个 Setup 和未来所有人工确认交易。

当前 V0 / 人工确认阶段由人类执行，不要求本次 First Launch 增加自动化 Guard。

未来全面自动交易前，必须建立独立、量化、可审计的：

```text
SCHEDULED_BOUNDARY_RISK_GUARD
```

自动化系统不得只靠固定“9:45以后恢复”或主观描述。

## 6. Boundary 类型

至少区分：

```text
SESSION / LIQUIDITY BOUNDARY
- Asia regional open
- Europe regional open
- U.S. cash open

INFORMATION BOUNDARY
- CPI / PPI / NFP / PCE
- FOMC / press conference
- Earnings / Guidance / Call
- other scheduled high-impact releases
```

两者原因不同，但共享同一风险问题：

```text
SHOULD EXISTING POSITION CROSS THIS KNOWN HIGH-RISK BOUNDARY?
WHEN IS MARKET QUALITY SUFFICIENTLY RECOVERED FOR NEW ENTRY?
```

## 7. Calendar-aware reference anchors

未来自动化不得把“亚洲 / 欧洲 / 美国”粗暴写成固定 UTC。

研究初始参考锚点：

```text
ASIA_REFERENCE = major relevant Asian cash-session open
  e.g. TSE 09:00 JST; market-specific Asian underlying may use its own primary cash open

EUROPE_REFERENCE = major relevant European cash-session open
  e.g. London 08:00 Europe/London

US_REFERENCE = U.S. cash equity open
  NYSE/Nasdaq 09:30 America/New_York
```

必须：

```text
calendar-aware
holiday-aware
DST-aware
underlying-market-aware where applicable
```

对于 24/7 crypto / 24/5 TradeXYZ，Boundary 的意义是 participant-flow / liquidity regime change，而不是交易 venue 自己停止/恢复交易。

## 8. Future Automated Boundary State Machine

未来候选：

```text
NORMAL
→ BOUNDARY_WATCH
→ PRE_BOUNDARY_DE_RISK
→ BOUNDARY_NO_NEW_ENTRY
→ RECOVERY_OBSERVATION
→ RECOVERY_CONFIRMED
→ NORMAL
```

当前不冻结具体分钟数。

人工经验中的“开盘前平仓、约 9:45 再找机会”作为重要 prior / benchmark 保存，但机器规则必须由数据校准。

## 9. 量化研究变量

至少研究：

### 9.1 Price / Volatility

```text
realized_vol_ratio_to_baseline
range_ATR_ratio
opening_displacement
max_adverse_excursion
max_favorable_excursion
jump / gap magnitude
```

### 9.2 Whipsaw / False Break

```text
false_breakout_rate
reclaim_rate
boundary_cross_count
sign_flip_count
directional_efficiency
```

### 9.3 Execution / Liquidity

```text
spread_bps / spread_ratio_to_baseline
book_depth_ratio
estimated_slippage
BBO freshness
mark / oracle / external / perp basis where relevant
```

### 9.4 Cross-market / Breadth

```text
index / peer breadth
correlation spike
leader-laggard dispersion
cross-asset disagreement
```

### 9.5 Time since boundary

研究 bucket 而不是立即冻结阈值：

```text
PRE: T-30 / T-15 / T-5
POST: 0-5 / 5-15 / 15-30 / 30-60m
```

这些窗口是实验 buckets，不是自动交易硬规则。

## 10. 核心研究问题

### BOUNDARY-1 — Carry vs Flatten

比较：

```text
FLATTEN BEFORE BOUNDARY
vs
CARRY THROUGH BOUNDARY
```

按 Setup / market / boundary type 分层，至少比较：

```text
Net R
Tail MAE
Stop-out Rate
False-break Rate
Worst Slippage
Recovery Opportunity Cost
```

未来自动交易默认继续 `FLATTEN / DE-RISK`，除非数据支持特定 bounded exception。

### BOUNDARY-2 — Recovery Timing

研究何时恢复允许新仓，不用固定 15 分钟：

```text
TIME-ONLY RULE
vs
VOLATILITY NORMALIZATION
vs
SPREAD/DEPTH RECOVERY
vs
STRUCTURE / DIRECTIONAL EFFICIENCY RECOVERY
vs
COMPOSITE RECOVERY GATE
```

### BOUNDARY-3 — Three Setup performance around opens

分别统计：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST
RANGE_EDGE_REJECTION
```

在各 boundary bucket 的：

```text
signal count
expectancy
MFE / MAE
stop rate
false-break rate
spread / slippage
```

用于判断是否需要：

```text
NO-ENTRY WINDOW
RANKING PENALTY
EXCEPTION POLICY
```

## 11. Future automation mandatory rule

在未来具备真实自动交易 authority 之前，必须有一份独立冻结的 Boundary Risk Contract，至少包含：

```text
boundary calendar / identity
pre-boundary position policy
new-entry suppression policy
exception authority
recovery gate
DST / holiday handling
missing calendar / stale data failure mode
execution-quality dependency
evidence / audit record
```

默认安全方向：

```text
UNKNOWN BOUNDARY STATE = FAIL CLOSED FOR NEW AUTO ENTRY
```

是否强制自动平掉既有仓位、提前多久、哪些特殊情况允许 carry，必须由研究结果和新的风险 authority 单独冻结。

---

## 12. Session 本身不是独立 Alpha Strategy

Premarket / Regular / Postmarket / Overnight / Asia / Europe / U.S. 只作为：

```text
SESSION / BOUNDARY CONTEXT
```

而不是新的 Setup Family。

正常市场只要现有三个 Setup 成立、执行质量足够，就可以交易。

真正需要特殊处理的是：

```text
KNOWN HIGH-RISK BOUNDARY
```

而不是“盘前/盘后”标签本身。

---

## 13. 与旧 Event 文档的取代关系

本文件对以下旧研究文档做语义收敛：

- `FIRST_LAUNCH_SCHEDULED_US_MACRO_EVENT_STRATEGY_RESEARCH_AND_FUTURE_AUTOMATION_BACKLOG_R1_2026-08-12.md`
- `FIRST_LAUNCH_SCHEDULED_CORPORATE_EARNINGS_EVENT_STRATEGY_RESEARCH_BACKLOG_R1_2026-08-13.md`
- `FIRST_LAUNCH_INTRADAY_INFORMATION_EVENT_AND_US_EXTENDED_HOURS_STRATEGY_RESEARCH_ADDENDUM_R1_2026-08-13.md`

旧文档中的数据源、PIT、财报多维 surprise、FOMC/Call 多阶段、执行研究等内容继续保留参考价值；但发生冲突时，以本文件以下收敛结论为准：

```text
NO FIXED 10-120m HOLDING LIMIT
NO SEPARATE PREMARKET / AFTER_HOURS STRATEGY FAMILY
NO PRE_EVENT STRATEGY FAMILY
NO SELL_THE_FACT STRATEGY FAMILY
EVENT = THIN CONTEXT / ATTRIBUTION OVERLAY
BOUNDARY RISK = GENERAL ALL-STRATEGY RISK LAYER
```

---

## 14. 当前发布边界

```text
CURRENT FIRST LAUNCH CODE CHANGE = NO
CURRENT MACHINE STRATEGY CHANGE = NO
NEW FORMAL SETUP = NO
CURRENT AUTOMATED BOUNDARY GUARD = NO
AUTO_TRADE = NO
```

当前人工/V0 阶段：Boundary discipline 由人类最终交易者执行。

未来自动化阶段：Boundary Risk Guard 是 mandatory prerequisite，不得遗漏。

---

## 15. 研究方法原则

```text
SAVE / USE RAW RECONSTRUCTABLE EVIDENCE
→ OFFLINE STUDY
→ FORWARD / SHADOW VALIDATION
→ QUANTIFY MARGINAL VALUE
→ FREEZE ONLY THE MINIMUM NECESSARY RULE
```

不得把人工经验直接硬编码成未验证参数；也不得因为需要量化就忽略已经被人工实践识别的高风险边界。

---

## 16. Authority Boundary

本文只固定策略/风险研究方向，不授权代码修改、工程实施、依赖安装、部署、重启、生产 DB 变更、账户/private API、签名、交易所写入、自动下单、Mark Ready 或 Merge。