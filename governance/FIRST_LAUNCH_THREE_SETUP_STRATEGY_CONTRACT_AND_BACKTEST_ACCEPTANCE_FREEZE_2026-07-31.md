# First Launch 三 Setup 策略量化合同与回测验收冻结

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-STRATEGY-CONTRACT-FREEZE-2026-07-31-R1`  
**日期：** `2026-07-31`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**生产基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**状态：** `STRATEGY CONTRACT AND BACKTEST ACCEPTANCE FREEZE / NON-EXECUTABLE / NON-DEPLOYMENT`

本文是 Strategy Optimization Window 对 `SWEEP_RECLAIM`、`BREAKOUT_RETEST`、`RANGE_EDGE_REJECTION` 的上层策略研究冻结输出。

本文只冻结：

- 外部证据与经济机制；
- Environment State；
- 三 Setup 因果量化合同；
- FAST / STANDARD；
- 边界、反例与交互；
- 有限候选预注册；
- 数据、成本、raw candidate、market event 和结果报告合同；
- GO / REVISE / INCONCLUSIVE / REJECT Gate；
- 向 Product Function Planning、Engineering Optimization 和 Project Control 提供的策略输入。

本文不授权：

- 修改生产代码；
- 回测执行；
- 安装研究工具；
- 向 Codex CLI、Reviewer、CI 或部署窗口派发任务；
- 生产部署、重启、Mark Ready 或 merge；
- 账户访问、签名、交易所写入或自动下单。

---

## 1. READ_ONLY_REVIEW_STATUS

```text
PR_52_REVIEWED_HEAD_BEFORE_THIS_RECORD = 82aa1c71b36a0ab23a6bf695b6aba144f96d72f8
PR_52_STATE = OPEN_DRAFT
PR_52_BASE_SHA = ac6496596ebdb0b8c2b0a40753dbed1771a0c85d
MAIN_AND_PRODUCTION_BASELINE = ac6496596ebdb0b8c2b0a40753dbed1771a0c85d
PRODUCTION_STRATEGY = ETH-LDAR-v0.1
PRODUCTION_SETUPS = SWEEP_RECLAIM | BREAKOUT_RETEST
PRODUCTION_RANGE_SETUP = ABSENT
BACKTEST_EXECUTED = NO
PRODUCTION_MUTATION = NO
STRATEGY_CONTRACT_STATUS = FROZEN_R1
```

### 1.1 已核验的生产策略事实

当前 `strategy.py`：

- 以 64 根闭合 5m K 线计算 Wilder ATR14；
- 以触发 K 线之前最近 12 根 5m K 线定义当前 Sweep / Breakout 边界；
- 以触发 K 线之前 20 根 5m 成交量中位数作为 volume baseline；
- 以 20 根闭合 15m K 线计算 long / short bias；
- 按固定 first-match 顺序检查 Sweep Long、Sweep Short、Breakout Long、Breakout Short；
- FAST 返回 `StrategyOutput`；
- 非 FAST 返回 `PreparedSetup`；
- 当前 `SetupFamily` 不含 `RANGE_EDGE_REJECTION`。

### 1.2 阻断性 STANDARD 事实

```text
STANDARD_PROGRESSION_FINDING = FAIL_CURRENT_RUNTIME_PATH
STRATEGY_RULE_FUNCTION = PRESENT
LIFECYCLE_ADVANCE_FUNCTION = PRESENT
LATER_CLOSED_5M_RUNTIME_INVOCATION = ABSENT
```

当前 runtime 在每根新闭合 5m 上调用一次 `evaluate_signal(snapshot)`。只有本次返回一个新 `PreparedSetup` 时，才立即使用同一 snapshot 调用一次 lifecycle `advance()`；没有可见路径在后续闭合 5m 上遍历并推进此前保留的 PREPARE。

因此必须区分：

```text
V0_1_EXACT_BASELINE
= 复现 ac649 当前实际行为，包括当前 STANDARD runtime 缺陷

STANDARD_INTENDED_REFERENCE
= 依据现有 advance_prepare 规则，在后续闭合 5m 上推进 retained PREPARE
```

`STANDARD_INTENDED_REFERENCE` 不得被称为 `V0_1_EXACT_BASELINE`。

策略研究合同可以冻结；任何 production strategy patch 必须等待该既有缺陷被独立闭合。

---

## 2. EVIDENCE_SOURCE_MATRIX

外部资料用于证明经济机制、适用环境、失败机制、成本和偏差控制，不用于直接复制具体参数。

| 来源 | 成熟结论 | 本轮合同用途 |
|---|---|---|
| Chung & Bellotti, *Evidence and Behaviour of Support and Resistance Levels in Financial Time Series* — https://arxiv.org/abs/2101.07410 | 支撑阻力可产生显著临时反应；历史反应次数增加时再次反应概率更高；效力随时间衰减 | Level Quality 必须包括独立反应次数和新鲜度；任意 rolling high/low 不能自动成为高质量边界 |
| Henderson, Jacka & Liu, *The Support and Resistance Line Method: An Analysis via Optimal Stopping* — https://arxiv.org/abs/2103.02331 | 支撑阻力交易具有路径依赖；进入和退出是相互关联的问题 | 每个 Setup 必须同时冻结 trigger、entry、stop、target feasibility、expiry 和 invalidation |
| Osler, *Currency Orders and Exchange-Rate Dynamics* — https://www.newyorkfed.org/research/staff_reports/sr125.html | 止损、止盈订单会在可观察技术位置附近聚集 | 同一边界需要区分 shallow rejection、sweep reclaim 和 accepted breakout |
| Osler, *Stop-Loss Orders and Price Cascades in Currency Markets* — https://www.newyorkfed.org/research/staff_reports/sr150.html | 止损订单可能形成正反馈级联并加速越界趋势 | Sweep 必须限制 excursion；Range 必须禁止真实 breakout transition；Breakout 需要 acceptance |
| Leung & Li, *Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit* — https://arxiv.org/abs/1411.5062 | 均值回归的 entry、exit、成本和 stop-loss 必须联合设计 | Range 必须有完整 target-feasibility gate；ETH 绝对价格不得默认视为稳定 OU 过程 |
| Bailey et al., *The Probability of Backtest Overfitting* — https://papers.ssrn.com/sol3/papers.cfm?abstract_id=2326253 | 尝试配置越多，选择偏差与 false discovery 风险越高 | 每个 Setup 第一轮仅一个主候选和一个经济解释明确的敏感性对照；所有尝试必须留痕 |
| Freqtrade official lookahead-analysis — https://www.freqtrade.io/en/stable/lookahead-analysis/ | 全 dataframe 回测可能访问未来数据；未触发分支可能形成假阴性 | runner 必须逐根闭合 K 线推进；每个 Setup、方向和模式必须在验证集或 deterministic fixture 中触发 |
| Freqtrade official recursive-analysis — https://docs.freqtrade.io/en/stable/recursive-analysis/ | startup history 长度会导致 recursive 指标和 live/backtest 结果差异 | 必须复现 live 的 64x5m 与 20x15m startup contract，并报告 startup variance |
| Hyperliquid official Info endpoint — https://hyperliquid.gitbook.io/hyperliquid-docs/for-developers/api/info-endpoint | Candle Snapshot 仅提供最近 5000 根 K 线 | Hyperliquid exact recent evidence 与 Binance/Bybit long-history proxy evidence 必须分开 |
| Hyperliquid official fees / funding — https://hyperliquid.gitbook.io/hyperliquid-docs/trading/fees and https://hyperliquid.gitbook.io/hyperliquid-docs/trading/funding | Perp fee 随 rolling volume tier 变化；funding 每小时支付 | 无账户级 tier 证据时采用生产 parity 成本；只有跨 funding 时点的持仓才计 funding |

```text
EXTERNAL_EVIDENCE_SUPPORTS_ECONOMIC_MECHANISMS = YES
EXTERNAL_EVIDENCE_PROVES_ETH_5M_15M_PARAMETERS = NO
COPY_PARAMETERS_FROM_OTHER_MARKETS = PROHIBITED
```

---

## 3. THREE_SETUP_ECONOMIC_MODEL

### 3.1 两层模型

Layer A — Environment State：

```text
RANGE
DIRECTIONAL_UP
DIRECTIONAL_DOWN
TRANSITION
UNCERTAIN
```

Layer B — Event Outcome：

```text
SWEEP_RECLAIM
BREAKOUT_RETEST
RANGE_EDGE_REJECTION
NO_ACTION
```

Environment 只决定哪些 Setup 有资格参与判断；Event Outcome 决定实际发生的市场事件。

不得定义：

```text
one regime = one Setup
```

同一边界可以先后出现：

- shallow rejection；
- liquidity sweep and reclaim；
- accepted breakout and retest；
- failed breakout turning into sweep；
- range-to-trend transition。

### 3.2 三种经济机制

#### SWEEP_RECLAIM

经过验证的边界被穿越，可能触发止损、强平或外侧流动性。若价格未被市场接受在边界外并重新收回，流动性冲击可能暂时耗尽，价格向边界内侧回归。

#### BREAKOUT_RETEST

经过验证的边界被闭合 K 线突破并获得接受，随后回踩不重新进入旧结构；止损级联、追随订单和重新定价可能推动方向延续。

#### RANGE_EDGE_REJECTION

在非方向性环境中，上下两侧均经重复反应验证的稳定区间，其边缘发生浅度越界或触碰并收回；当区间内仍有足够成本后目标空间时，价格可能向内部回归。

---

## 4. SHARED_CAUSAL_DEFINITIONS

当前触发 K 线为 `t`。所有历史窗口均排除 `t`，只使用在决策截止时已经闭合并到达的数据。

```text
A       = 截止 t 的生产同语义 Wilder ATR14
M20     = t 之前 20 根 5m 成交量中位数
CL      = (C_t - L_t) / (H_t - L_t)
SCL     = 1 - CL
BODY_A  = abs(C_t - O_t) / A

U12     = max(high) over t-12 ... t-1
L12     = min(low)  over t-12 ... t-1

U24     = max(high) over t-24 ... t-1
L24     = min(low)  over t-24 ... t-1
W24     = (U24 - L24) / A

ER12 =
abs(C_{t-1} - C_{t-13})
/
sum(abs(C_i - C_{i-1}), i=t-12...t-1)

D12 = (C_{t-1} - C_{t-13}) / A
```

若 `ER12` 分母为零，令 `ER12 = 0`；Range width 和 target feasibility 仍须独立通过。

### 4.1 Level Reaction

支撑位 `L` 的历史 K 线构成一次反应：

```text
low_i ∈ [L - 0.15A, L + 0.15A]
AND
close_i >= L + 0.05A
```

阻力位完全镜像。

两个反应只有相隔至少三根 5m K 线，才计为两个独立事件。

### 4.2 LEVEL_QUALITY

```text
Q0 = 无合格历史反应
Q1 = 1 次独立反应
Q2 = 至少 2 次独立反应，且最近一次距当前 <= 12 根 5m
Q3 = 至少 3 次独立反应，且最近一次距当前 <= 12 根 5m
```

Sweep 与 Breakout 主候选要求 `Q2+`。

Range 主候选要求上下边界均为 `Q2+`。

---

## 5. ENVIRONMENT_STATE_CONTRACT

```text
ENV_PRE_t
= 只使用 t 之前可见结构计算

ENV_DECISION_t
= ENV_PRE_t + 当前闭合 K 线的有限 transition override
```

### 5.1 RANGE

全部满足：

```text
long_bias = false
short_bias = false
ER12 <= 0.35
abs(D12) <= 0.75
1.50 <= W24 <= 4.00
upper_level_quality >= Q2
lower_level_quality >= Q2
volatility_regime = NORMAL
```

### 5.2 DIRECTIONAL_UP

```text
long_bias = true
short_bias = false
ER12 >= 0.45
D12 >= 0.75
```

### 5.3 DIRECTIONAL_DOWN

```text
short_bias = true
long_bias = false
ER12 >= 0.45
D12 <= -0.75
```

### 5.4 TRANSITION

以下任一成立，且数据完整：

```text
0.35 < ER12 < 0.45

OR

方向 bias 与 D12 符号冲突

OR

ENV_PRE = RANGE
AND 当前 close 在 U24 或 L24 外至少 0.10A

OR

价格正在破坏原环境的已验证边界，
但尚未满足完整 DIRECTIONAL 条件
```

Transition override：

- 可以取消 Range eligibility；
- 可以允许 Breakout 参加判断；
- 不得单独创造候选；
- 不得把 UNCERTAIN 提升为可交易状态；
- 不得绕过 Setup 自身确认合同。

### 5.5 UNCERTAIN

以下任一成立：

```text
DataQuality != READY
历史长度不足
5m / 15m 因果对齐失败
ATR 无效
long_bias 与 short_bias 同时为 true
dual-edge candle
不能唯一归入其他四类环境
```

### 5.6 Volatility policy

第一轮保持当前 v0.1 overlay 作为独立 safety layer，不做参数搜索：

- `EXTREME`：全部不可操作；
- `HIGH`：Sweep / Breakout 可参与，但应用现有更严格 Chase Limit；
- `LOW`：FAST 不直接生产化，沿用现有 longer-window support 语义；
- `NORMAL`：正常评估；
- Range 主候选只允许 `NORMAL`。

---

## 6. SWEEP_RECLAIM_FULL_CONTRACT

### ECONOMIC_HYPOTHESIS

价格穿越高质量边界后触发外侧流动性，但未被市场接受在外侧并重新收回。

### TARGET_ENVIRONMENT

Long：

```text
RANGE
TRANSITION
DIRECTIONAL_UP
```

Short 镜像。

### PROHIBITED_ENVIRONMENT

```text
UNCERTAIN
EXTREME
Long 禁止 DIRECTIONAL_DOWN
Short 禁止 DIRECTIONAL_UP
```

### LEVEL_DEFINITION / LEVEL_QUALITY

```text
Long boundary  = L12
Short boundary = U12
LEVEL_QUALITY >= Q2
```

### EVENT_TRIGGER — Long

```text
X = (L12 - low_t) / A

0.10 <= X <= 0.60
close_t >= L12
CL >= 0.55
short_bias = false
dual_edge = false
```

Short 镜像。

`X == 0.10` 唯一归属于 Sweep，不属于 Range。

### FAST_CONFIRMATION — Long

```text
EVENT_TRIGGER = true
close_t >= L12 + 0.10A
CL >= 0.70
volume_t >= 1.50 * M20
TARGET_FEASIBILITY = PASS
```

### STANDARD_PREPARE — Long

```text
EVENT_TRIGGER = true
FAST_CONFIRMATION = false
close_t >= L12
CL >= 0.55
volume_t >= 0.80 * M20
TARGET_FEASIBILITY_AT_PREPARE != FAIL
```

### STANDARD_CONFIRMATION — Long

后续第 1–3 根闭合 5m 中：

```text
close_k >= L12 + 0.05A
low_k > initial_low
不存在中间 close < L12 - 0.20A
不存在 low < initial_low - 0.10A
最终 target feasibility = PASS
```

Short 镜像。

### INVALIDATION

```text
DataQuality != READY
超过 3 根闭合 5m
Long close < boundary - 0.20A
Long new_low < initial_low - 0.10A
Short 完全镜像
同一 market event 已被有效 Breakout outcome 接管
目标空间不再满足
```

### EXPIRY

```text
PREPARE_EXPIRY = 15 minutes / 3 closed 5m bars
FAST_OUTPUT_EXPIRY = 180 seconds
STANDARD_OUTPUT_EXPIRY = 900 seconds
```

### ENTRY_ZONE / CHASE_LIMIT / STRUCTURAL_STOP — Long

```text
FAST_ENTRY_ZONE     = [L12, L12 + 0.15A]
FAST_CHASE_LIMIT    = L12 + 0.25A
FAST_STOP           = initial_low - 0.10A

STANDARD_ENTRY_ZONE = [L12 - 0.05A, L12 + 0.10A]
STANDARD_CHASE      = L12 + 0.20A
STANDARD_STOP       = initial_low - 0.10A
```

Short 镜像。

### TARGET_FEASIBILITY

```text
R = abs(planned_entry - structural_stop)

reserve = max(
    0.10A,
    planned_entry * round_trip_all_in_cost_rate
)

Long available_space  = U12 - planned_entry
Short available_space = planned_entry - L12

require available_space >= 2R + reserve
```

### FAILURE_MODE

- 真正止损级联正在形成；
- 边界陈旧或偶然；
- excursion 过深后的暂时收回；
- 逆明确方向接飞刀；
- 人工延迟后超过 Chase Limit。

### PRE_REGISTERED_SENSITIVITY

仅修改一个变量：

```text
PRIMARY_MAX_EXCURSION = 0.60A
SENSITIVITY_MAX_EXCURSION = 0.80A
```

---

## 7. BREAKOUT_RETEST_FULL_CONTRACT

### ECONOMIC_HYPOTHESIS

高质量边界被收盘突破并获得接受；回踩不重新进入旧结构，止损级联、追随订单和重新定价推动延续。

### TARGET_ENVIRONMENT

Long：

```text
DIRECTIONAL_UP
TRANSITION_FROM_RANGE_UP
```

Short 镜像。

### PROHIBITED_ENVIRONMENT

```text
RANGE 且没有 transition override
Long 禁止 DIRECTIONAL_DOWN
Short 禁止 DIRECTIONAL_UP
UNCERTAIN
EXTREME
```

### LEVEL_DEFINITION / LEVEL_QUALITY

```text
Long boundary  = U12
Short boundary = L12
LEVEL_QUALITY >= Q2
```

### EVENT_TRIGGER — Long

```text
close_t >= U12 + 0.10A
BODY_A >= 0.35
CL >= 0.70
volume_t >= 1.20 * M20

direction_support =
long_bias
OR
(
    ENV_PRE = RANGE
    AND BODY_A >= 0.50
    AND volume_t >= 1.50 * M20
)
```

### FAST_CONFIRMATION — Long

```text
EVENT_TRIGGER = true
close_t >= U12 + 0.15A
BODY_A >= 0.50
CL >= 0.75
volume_t >= 1.50 * M20
TARGET_FEASIBILITY = PASS
```

### STANDARD_PREPARE

```text
EVENT_TRIGGER = true
FAST_CONFIRMATION = false
initial close remains >= boundary + 0.10A
```

### STANDARD_CONFIRMATION — Long

后续第 1–3 根闭合 5m：

```text
retest_low ∈ [U12 - 0.05A, U12 + 0.15A]
confirmation_close >= U12 + 0.05A
所有中间 close >= U12 - 0.20A
TARGET_FEASIBILITY = PASS
```

Short 镜像。

### INVALIDATION

Long：

```text
close <= U12 - 0.20A
PREPARE 超过 3 根闭合 5m
出现对侧已确认 Breakout
DataQuality != READY
目标空间不再满足
```

Breakout PREPARE 失效后若形成完整 Sweep：

```text
EVENT_TRANSITION = FAILED_BREAKOUT_TO_SWEEP
```

旧 Breakout PREPARE 必须先终止，才允许 Sweep outcome。

### EXPIRY

```text
PREPARE_EXPIRY = 15 minutes
FAST_OUTPUT_EXPIRY = 180 seconds
STANDARD_OUTPUT_EXPIRY = 900 seconds
```

### ENTRY_ZONE / CHASE_LIMIT / STRUCTURAL_STOP — Long

```text
FAST_ENTRY_ZONE     = [U12 + 0.10A, U12 + 0.20A]
FAST_CHASE_LIMIT    = U12 + 0.30A
FAST_STOP           = U12 - 0.25A

STANDARD_ENTRY_ZONE = [U12 - 0.05A, U12 + 0.10A]
STANDARD_CHASE      = U12 + 0.20A
STANDARD_STOP       = min(U12 - 0.25A, retest_low - 0.05A)
```

Short 镜像。

### TARGET_FEASIBILITY

在 `t-64 ... t-13` 中识别已完整闭合的三 K 线 local swing：

```text
swing_high_i = high_i > high_{i-1} AND high_i >= high_{i+1}
swing_low_i  = low_i < low_{i-1} AND low_i <= low_{i+1}
```

Long obstacle 为高于 planned entry 的最近合格 swing high；Short 镜像。

若存在 obstacle：

```text
distance_to_obstacle >= 2R + reserve
```

若不存在：

```text
TARGET_SPACE_STATUS = NO_KNOWN_STRUCTURAL_OBSTACLE
```

允许通过，但必须单独统计。

### FAILURE_MODE

- 假突破后立即收回；
- Range 外侧试探但未获得接受；
- 高波动反转；
- 入场已超过 Chase Limit；
- 历史障碍使 2R 不可实现；
- STANDARD 回踩过深并重新进入旧区间。

### PRE_REGISTERED_SENSITIVITY

仅修改 FAST acceptance：

```text
PRIMARY_FAST_CLOSE_EXTENSION = 0.15A
SENSITIVITY_FAST_EXTENSION = 0.10A
```

---

## 8. RANGE_EDGE_REJECTION_FULL_CONTRACT

### ECONOMIC_HYPOTHESIS

在稳定非方向区间中，高质量边缘发生触碰或浅度越界后收回；当区间内仍有足够成本后目标空间时，价格向内部回归。

### TARGET_ENVIRONMENT

```text
ENV_DECISION = RANGE
VOLATILITY = NORMAL
```

### PROHIBITED_ENVIRONMENT

```text
DIRECTIONAL_UP
DIRECTIONAL_DOWN
TRANSITION
UNCERTAIN
LOW / HIGH / EXTREME volatility
```

### LEVEL_DEFINITION

```text
upper = U24
lower = L24
width = upper - lower

1.50A <= width <= 4.00A
```

### LEVEL_QUALITY

主候选：

```text
candidate_edge >= Q2
opposite_edge >= Q2
candidate_edge_latest_reaction_age <= 12 bars
opposite_edge_latest_reaction_age <= 18 bars
```

### EVENT_TRIGGER — Long

```text
low_t <= lower + 0.15A
outside_excursion = max(0, lower - low_t)
outside_excursion < 0.10A
close_t >= lower + 0.05A
high_t < upper - 0.15A
dual_edge = false
Sweep Long raw predicate = false
all Breakout raw predicates = false
```

Short 镜像。

### FAST_CONFIRMATION — Long

```text
EVENT_TRIGGER = true
close_t >= lower + 0.10A
CL >= 0.70
lower_wick / candle_range >= 0.35
volume_t >= 1.20 * M20
TARGET_FEASIBILITY = PASS
```

### STANDARD_PREPARE

```text
EVENT_TRIGGER = true
FAST_CONFIRMATION = false
CL >= 0.55
volume_t >= 0.80 * M20
```

### STANDARD_CONFIRMATION — Long

后续第 1–3 根闭合 5m：

```text
所有 close >= lower - 0.10A
所有 low >= initial_low - 0.05A
confirmation_close >= lower + 0.05A

AND

(
    confirmation_close > setup_close
    OR confirmation_low > setup_low
)

TARGET_FEASIBILITY = PASS
```

Short 镜像。

### INVALIDATION

```text
Long close < lower - 0.10A
Long new_low < initial_low - 0.05A
Short 完全镜像
触及 opposite-edge zone
环境变为 TRANSITION / DIRECTIONAL
有效 Breakout 接管同一 market event
超过 3 根闭合 5m
目标空间失败
```

### EXPIRY

```text
PREPARE_EXPIRY = 15 minutes
FAST_OUTPUT_EXPIRY = 180 seconds
STANDARD_OUTPUT_EXPIRY = 900 seconds
```

### ENTRY_ZONE / CHASE_LIMIT / STRUCTURAL_STOP — Long

```text
FAST_ENTRY_ZONE = [lower, lower + 0.10A]
FAST_CHASE = lower + 0.20A
FAST_STOP = min(initial_low - 0.10A, lower - 0.20A)

STANDARD_ENTRY = [lower - 0.05A, lower + 0.10A]
STANDARD_CHASE = lower + 0.20A
STANDARD_STOP = min(material_low - 0.05A, lower - 0.20A)
```

Short 镜像。

### TARGET_FEASIBILITY

Long：

```text
available_space = upper - planned_entry
R = planned_entry - stop
require available_space >= 2R + reserve
```

Short 镜像。

### FAILURE_MODE

- 区间正在转换为真实趋势；
- 边界没有重复验证；
- 区间过窄，成本吞噬收益；
- 区间过宽，并非同一稳定结构；
- dual-edge 大 K 线产生错误双向解释；
- 人工响应后已接近区间中部。

### PRE_REGISTERED_SENSITIVITY

仅放松对侧边界质量：

```text
PRIMARY:
candidate_edge Q2
opposite_edge Q2

SENSITIVITY:
candidate_edge Q2
opposite_edge Q1
```

其他参数不得改变。

---

## 9. FAST_STANDARD_PER_SETUP_CONTRACT

| 场景 | 冻结归属 |
|---|---|
| 初始 K 线满足 FAST | 直接产生 FAST；不得同时建立 STANDARD PREPARE |
| 初始 K 线只满足 PREPARE | 建立唯一 STANDARD PREPARE |
| PREPARE 期间后续 K 线满足同 Setup 的 FAST 形态 | 仍归为 STANDARD confirmation，不新建 FAST |
| FAST 已确认，同一 level/event 后续满足 STANDARD | 记录 raw candidate，标记 `DUPLICATE_AFTER_FAST`，不得重复发布 |
| PREPARE 失效后出现不同 outcome | 先终止旧 PREPARE，再允许事件 outcome 转换 |
| PREPARE 到期后价格离开并重新返回 | 必须满足新 market-event separation 后才建立新事件 |

必须分别报告：

```text
FAST_ONLY_EVENTS
STANDARD_ONLY_EVENTS
FAST_AND_STANDARD_SAME_EVENT
STANDARD_FILTERED_FAILURES
STANDARD_DELAYED_MISSES
FAST_NET_R
STANDARD_NET_R
FAST_MAE / MFE
STANDARD_MAE / MFE
```

FAST 主要风险：单根 K 线噪声、假突破和异常成交量。

STANDARD 主要风险：延迟、滑点、Chase Limit 超限和错过快速移动。

---

## 10. THREE_SETUP_BOUNDARY_AND_INTERACTION_MATRIX

| 市场事实 | 唯一域或政策 |
|---|---|
| 外侧 excursion `< 0.10A`、收盘在边界内、环境为 RANGE | Range candidate domain |
| excursion `== 0.10A`、收盘重新在边界内 | Sweep domain |
| excursion `> 0.10A`、收盘重新在边界内 | Sweep domain，受 maximum excursion 限制 |
| 收盘在边界外 `< 0.10A` | 不属于 Breakout；NO_ACTION / WATCH |
| 收盘在边界外 `>= 0.10A` | Breakout domain |
| Sweep vs Breakout | close-inside / close-outside 数学互斥 |
| Sweep vs Range | excursion `>= 0.10A` / `< 0.10A` 数学互斥 |
| Breakout vs Range | close-outside / close-inside 数学互斥 |
| 同一 Range K 线触及上下边缘 | `RANGE_DUAL_EDGE_AMBIGUOUS`，NO_ACTION |
| Range PREPARE 后出现 accepted Breakout | Range invalidated，Breakout 接管 |
| Breakout PREPARE 后深度收回 | Breakout invalidated；完整满足时转 Sweep |
| FAST / STANDARD 指向同一 level/event | 一个 market event，只允许一个最终候选 |
| 同方向多个 level candidate | 归并后保留证据等级最高者，其余记录 suppression |
| active expiry 内出现反方向候选 | 全部记录；生产默认不发布第二个反向信号 |
| Environment 无法唯一分类 | UNCERTAIN / NO_ACTION |

最终路径：

```text
ENUMERATE_ALL_RAW
→ CLASSIFY_ENVIRONMENT
→ CLASSIFY_EVENT_DOMAIN
→ GROUP_MARKET_EVENT
→ DEDUPLICATE
→ APPLY_ACTIVE_STATE_POLICY
→ FINAL_OUTPUT
```

固定 first-match 顺序只能作为 exact v0.1 baseline 事实，不得作为三 Setup 最终归属的主要逻辑。

---

## 11. FAILURE_AND_COUNTEREXAMPLE_MATRIX

| 反例 | 必须结果 |
|---|---|
| 只有一次历史触碰的 rolling high/low | Level Quality 不通过 |
| 触碰次数多但最近一次过旧 | Level 衰减，不通过 Q2 |
| Sweep excursion 达 1.2A 后勉强收回 | 主候选拒绝 |
| Range 浅刺穿恰好 0.10A | 不属于 Range，进入 Sweep domain |
| Breakout 只有影线越界、close 在内 | 不属于 Breakout |
| Breakout close 越界后下一根深度回区间 | STANDARD invalidated |
| Range rejection 后下一根 accepted breakout | Range PREPARE invalidated |
| 同一 K 线触及 Range 两侧 | Dual-edge veto |
| FAST 发布后同事件出现 STANDARD | Duplicate event，不发布 |
| 反方向候选出现在 active expiry 内 | 记录 conflict，默认不发布 |
| Stop 与 TP 在同一 1m K 线内触发 | `AMBIGUOUS_PATH`，Stop-first |
| Hyperliquid exact 与 proxy 方向相反 | INCONCLUSIVE |
| 组合盈利但单 Setup 为负 | 不得用组合结果掩盖单 Setup |
| 收益主要来自极少数异常交易 | Concentration Gate 失败或 INCONCLUSIVE |

---

## 12. PRE_REGISTERED_PRIMARY_CANDIDATES

```text
V0_1_EXACT_BASELINE
V0_1_INSTRUMENTED_PARITY

SWEEP_PRIMARY = SWEEP_Q2_X_010_060_FAST_STD_R1
SWEEP_SENSITIVITY = SWEEP_Q2_X_010_080_FAST_STD_R1

BREAKOUT_PRIMARY = BREAKOUT_Q2_FAST_ACCEPT_015_STD_R1
BREAKOUT_SENSITIVITY = BREAKOUT_Q2_FAST_ACCEPT_010_STD_R1

RANGE_PRIMARY = RANGE_24_Q2_Q2_FAST_STD_R1
RANGE_SENSITIVITY = RANGE_24_Q2_Q1_FAST_STD_R1
```

合同冻结后禁止：

- 改变 lookback；
- 同时改变 volume、close location、stop 和 width；
- 根据首次结果增加第三个候选；
- 删除失败候选；
- 将敏感性对照重新命名为主候选。

---

## 13. DATA_AND_TIME_CONTRACT

### 13.1 决策截止

```text
decision_cutoff = trigger_5m.close_time
```

只允许使用：

```text
5m candle.close_time <= decision_cutoff
5m candle.received_at <= decision_cutoff
15m candle.close_time <= decision_cutoff
15m candle.received_at <= decision_cutoff
active context.received_at <= evaluated_at
```

历史 runner 必须通过现有 parser、`EthMarketData.accept_*` 和 `strategy_snapshot()` 签发策略输入；禁止直接构造普通 `StrategySnapshot`。

### 13.2 OHLCV_ONLY_RESEARCH_BRIDGE

Proxy 数据缺少真实历史 activeAssetCtx 时允许：

```text
CONTEXT_MODE = OHLCV_ONLY_RESEARCH_BRIDGE
mark/mid = cutoff 时点的因果价格
OI/funding = manifest 中声明的 neutral placeholder
metadata = manifest 中冻结的 symbol precision
source_id = research-only
```

必须执行 metamorphic test：在多个合法但不同的 placeholder context 下，当前 v0.1 最终 strategy output 完全相同。若未来 evaluator 开始读取这些字段，该 bridge 自动失效。

### 13.3 数据双轨

```text
HYPERLIQUID_EXACT_RECENT_EVIDENCE
LONG_HISTORY_PROXY_EVIDENCE
```

两者必须分开报告，不得混合后声称 Hyperliquid 精确历史收益。

### 13.4 1m 路径

优先用 1m 数据判断：

- 人工延迟后的可成交价格；
- Chase Limit；
- Stop / TP 先后；
- MAE / MFE。

没有 1m 或同一 1m 内 Stop / TP 均触发：

```text
PATH_STATUS = AMBIGUOUS_PATH
RESOLUTION = STOP_FIRST
```

---

## 14. COST_AND_MANUAL_EXECUTION_CONTRACT

当前 production parity 风险模型使用：

```text
adverse execution offset = 0.0005 per fill
fee = 0.00045 per fill
```

Hyperliquid实际 fee 取决于 rolling volume tier。没有账户级 tier 证据时，主回测采用上述 production parity 数值。

### 主场景

```text
ENTRY_FEE = 4.5 bps
EXIT_FEE = 4.5 bps
ENTRY_EXECUTION_OFFSET = 5 bps adverse
EXIT_EXECUTION_OFFSET = 5 bps adverse
MANUAL_RESPONSE_DELAY = 30 seconds
ORDER_ASSUMPTION = TAKER
```

### 延迟敏感性

```text
FAST_RESPONSE = 15 seconds
PRIMARY = 30 seconds
STRESS = 60 seconds
```

### 执行压力场景

```text
STRESS_EXECUTION_OFFSET = 10 bps per fill
FEE = unchanged
DELAY = 60 seconds
```

### 人工延迟映射

```text
eligible_ts = signal_created_at + manual_delay
```

若 `eligible_ts` 位于某根 1m 内部且没有秒级路径：

```text
Long eligible price = 该 1m high
Short eligible price = 该 1m low
PATH_STATUS = DELAY_FILL_AMBIGUOUS
```

然后再应用 adverse execution offset。

若价格已越过 Chase Limit 或 signal expiry：

```text
TRADE_STATUS = MISSED_NO_FILL
```

### Funding

只在持仓跨越 Hyperliquid 小时 funding 时点时，使用相应历史 funding；否则 funding 为零。

---

## 15. RAW_CANDIDATE_SCHEMA

每个 raw candidate 至少包含：

```text
run_id
dataset_manifest_id
venue_evidence_class
strategy_contract_id
baseline_sha
strategy_version

decision_cutoff
trigger_5m_identity
trigger_5m_hash
visible_15m_cutoff
snapshot_hash

environment_pre
environment_decision
er12
d12
w24
long_bias
short_bias
volatility_regime

setup_family
side
confirmation_mode
candidate_state

level_id
level_type
level_price
level_quality
touch_count
latest_touch_age
opposite_level_quality

excursion_atr
close_extension_atr
body_atr
close_location
wick_ratio
volume_ratio

prepare_created_at
prepare_expires_at
confirmation_candle_identity
invalidation_reason

raw_entry_low
raw_entry_high
raw_chase_limit
raw_stop
target_feasibility
available_space
planned_r

raw_predicate_result
overlay_result
arbitration_result
suppression_reason
market_event_id
```

未来结果字段必须位于独立的 `outcome_*` 区域，禁止成为 strategy input。

---

## 16. MARKET_EVENT_SCHEMA

```text
level_instance_id = hash(
    symbol,
    level_type,
    canonical_level_price,
    first_seen_cutoff
)
```

若新边界与当前 active level 相差不超过 `0.05 * event_start_ATR`，沿用原 level instance；否则建立新 instance。

```text
market_event_id = hash(
    symbol,
    level_instance_id,
    event_start_5m_identity
)
```

事件开始：

```text
首次 boundary contact
OR 首次 raw candidate
OR 首次 PREPARE
```

事件终止：

```text
所有 PREPARE / output 已 terminal

AND

以下任一：
1. 连续 3 根 5m close 距 level > 0.25 * event_start_ATR
2. 距最后 raw candidate 已经过 6 根 5m
```

研究报告可以使用后续数据确定事件最终结束时间，但事件结束信息不得回流到历史 candidate decision。

---

## 17. MANDATORY_REPLAY_MODES

```text
A. V0_1_EXACT_BASELINE

B. V0_1_INSTRUMENTED_PARITY
   final output 必须逐事件、逐字段与 A 完全一致

C. SWEEP_CANDIDATE
   primary + one sensitivity

D. BREAKOUT_CANDIDATE
   primary + one sensitivity

E. RANGE_FAST_STANDARD
   primary + one sensitivity

F. ALL_RAW_CANDIDATES_NO_ARBITRATION
   不使用 first-match，不压制任何 raw candidate

G. COMBINED_EXACT_POLICY
   environment → event → grouping → dedupe → active policy
```

Interaction counterfactual：

```text
PRIORITY_AND_SINGLE_ACTIVE
ALLOW_SAME_DIRECTION_DEDUPLICATED
PUBLISH_ALL_WITH_CONFLICT_LABEL  # research-only
```

---

## 18. RESULT_REPORT_SCHEMA

每次运行至少报告：

- baseline SHA、contract ID、runner version、Freqtrade version、dataset hash；
- venue、时间范围、缺口、重复、异常 candle、1m coverage；
- parity mismatch、lookahead、recursive variance、startup coverage；
- raw candidates、unique market events、signals per event；
- Sweep / Breakout / Range 独立结果；
- FAST / STANDARD / FAST-only / STANDARD-only；
- LONG / SHORT；
- Environment State 分层；
- same-candle overlap、cross-candle overlap、duplicate、opposite、suppressed、baseline displaced；
- filled、missed、chase exceeded、expired；
- gross R、net R、expectancy、win rate、average win/loss；
- maximum drawdown、longest losing streak、MAE、MFE；
- fee、execution offset、delay、funding；
- ambiguous stop/TP、delay ambiguity；
- 时间分块、venue 分层、cost stress；
- top-1 / top-5 profit concentration；
- `GO / REVISE / INCONCLUSIVE / REJECT`。

---

## 19. ACCEPTANCE_GATES

### Gate 0 — Runtime and replay correctness

任一失败即停止：

```text
STANDARD progression deterministic runtime test fails
v0.1 exact replay unavailable
instrumented parity mismatch > 0
lookahead detected
startup history changes final candidate
5m / 15m causal alignment failure
```

### Gate 1 — Minimum evidence sufficiency

最低可估计性参考，不是机械晋级规则：

```text
proxy independent market events >= 30 per primary candidate
至少覆盖两个不重叠时间区段
核心方向和环境结果不得完全由一个事件支撑
Hyperliquid exact recent evidence 单独报告
```

不足时：

```text
PRODUCTION_DISPOSITION = INCONCLUSIVE
```

### Gate 2 — Primary economic viability

GO 必须同时满足：

```text
primary cost model 下 net expectancy > 0
market-event block bootstrap 95% lower confidence bound > 0
结果不只来自一个方向、一个 environment 或一个时间段
top-5 trades 对总正收益贡献 <= 50%
30s 与 60s delay 下不发生结论性符号翻转
exact recent evidence 与 proxy evidence 不发生方向性冲突
```

### Gate 3 — Existing Setup candidate improvement

Sweep / Breakout 修改候选相对其 exact v0.1 必须形成 Pareto improvement：

```text
A. net expectancy 提高，且 drawdown / losing streak 不恶化

OR

B. drawdown / losing streak 降低，且 net expectancy 不下降
```

仅增加交易次数不构成 improvement。

### Gate 4 — Combined policy

```text
V0_1_INSTRUMENTED_PARITY_MISMATCH = 0
RANGE_DISPLACED_VALID_BASELINE_SIGNAL = 0
UNEXPLAINED_OPPOSITE_CONFLICT = 0
DUPLICATE_PUBLICATION_PER_MARKET_EVENT = 0
COMBINED_NET_EXPECTANCY > 0
COMBINED_RISK_NOT_DOMINATED_BY_A_SIMPLER_POLICY
```

### GO

- correctness Gate 全部通过；
- 主候选成本后有效；
- event-level 95% CI 下界为正；
- interaction 可解释；
- combined policy 不静默破坏旧信号。

### REVISE

- 经济机制仍被证据支持；
- 失败集中在一个明确、可解释的合同问题；
- 修改生成新 Contract ID 并重新预注册；
- 不允许在同一结果集上连续多轮修补。

### INCONCLUSIVE

- 样本不足；
- exact 与 proxy 冲突；
- FAST / STANDARD 无法区分；
- 置信区间跨零；
- STANDARD runtime 语义尚未闭合。

### REJECT

- 主成本模型下为负，且上置信界不支持正期望；
- 成本消除全部优势；
- 主要在禁止环境触发；
- interaction 无法通过确定规则解决；
- 必须依赖 L2、Volume Profile、未来数据或架构扩张才能成立。

---

## 20. INPUT_FOR_PRODUCT_FUNCTION_PLANNING

用户可见信号至少需要：

```text
SetupFamily
Side
Environment State
FAST / STANDARD
Level price
Level Quality
Trigger evidence
Entry Zone
Chase Limit
Structural Stop
TP1 / TP2
Expiry
Target Feasibility
Volatility warning
Venue evidence classification
```

产品语义：

```text
FAST
= 初始闭合 K 线已达到高证据标准
!= 无条件激进版本

STANDARD
= 初始事件成立但证据不足，等待后续 1–3 根闭合 K 线
!= 低优先级信号
```

以下不得展示为可执行信号：

```text
UNCERTAIN
PROHIBITED_ENVIRONMENT
TARGET_SPACE_INSUFFICIENT
CHASE_LIMIT_EXCEEDED
EXPIRED
AMBIGUOUS_PATH
CONFLICT_SUPPRESSED
```

产品准入不得只看组合收益；必须看到单 Setup、FAST / STANDARD、成本后结果和失败模式。

---

## 21. INPUT_FOR_ENGINEERING_OPTIMIZATION

策略输入冻结为：

```text
64 x closed 5m
20 x causally aligned closed 15m
existing ATR authority
existing bias semantics
24-bar range and level-quality features
all-raw candidate enumerator
retained PREPARE iteration
market-event grouper
Freqtrade signal adapter
structured result exporter
```

强制要求：

- 先证明 v0.1 exact baseline；
- raw instrumentation 不得改变 baseline 最终输出；
- old PREPARE 必须在每根新 5m 被推进；
- 不修改 candle authority、transport 或 reconnect；
- 不做数据库迁移；
- 不增加生产服务或生产依赖；
- 不复制第二套长期策略实现；
- Freqtrade 负责数据管理、fill/fee/SL/TP 和统计，不定义 Trader Assist Setup 语义。

---

## 22. INPUT_FOR_PROJECT_CONTROL

本文件不派发任务。三方冻结完成后，Project Control 可依据以下顺序安排执行：

```text
1. 核验所有三方冻结输出和当前 exact identities
2. 独立闭合 CURRENT_STANDARD_PROGRESSION_DEFECT
3. 准备 dataset manifest
4. 建立 limited causal runner
5. 证明 V0_1_EXACT_BASELINE
6. 证明 V0_1_INSTRUMENTED_PARITY
7. 运行三个 Setup 的 primary + sensitivity
8. 运行 ALL_RAW_CANDIDATES_NO_ARBITRATION
9. 运行 COMBINED_EXACT_POLICY
10. Independent Reviewer
11. Strategy / Product / Engineering 联合裁决
12. 只有 GO 才进入最小 production candidate
```

---

## 23. FINAL_STATUS

```text
WORK_PACKAGE_A = CONTRACT_FROZEN_R1
WORK_PACKAGE_B = INPUT_AND_ACCEPTANCE_FROZEN_R1

STRATEGY_CONTRACT_COMPLETENESS = PASS
CAUSAL_FORMULAS = PASS
PARAMETER_GRID = ABSENT
FUTURE_DATA_REQUIREMENT = ABSENT
L2_REQUIREMENT = ABSENT
VOLUME_PROFILE_REQUIREMENT = ABSENT
ARCHITECTURE_CHANGE_REQUIRED = NO

STANDARD_RUNTIME_PATH = BLOCKING_EXISTING_DEFECT
BACKTEST_EXECUTION_AUTHORIZED_BY_THIS_RECORD = NO
PRODUCTION_PATCH_AUTHORIZED = NO
TASK_DISPATCH_AUTHORITY = PROJECT_CONTROL_ONLY
```
