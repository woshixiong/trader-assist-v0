# First Launch 三 Setup 策略合同 R1.1 精度审查与修正

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-STRATEGY-CONTRACT-R1-1-2026-07-31`  
**日期：** `2026-07-31`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**生产基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**前序合同：** `TA-FIRST-LAUNCH-THREE-SETUP-STRATEGY-CONTRACT-FREEZE-2026-07-31-R1`  
**状态：** `STRATEGY CONTRACT R1.1 PRECISION FREEZE / NON-EXECUTABLE / NON-DEPLOYMENT`

本文是对 R1 策略合同的第二次严格静态审查。审查目标不是继续增加指标、参数或 Setup，而是关闭会导致产品解释分叉、工程实现分叉、回测结果不可复现或错误归因的精确定义缺口。

本文与 R1 合并构成完整策略权威输入。发生冲突时，以本文为准；本文未修改的内容继续沿用 R1。

本文不授权回测执行、代码修改、依赖安装、任务派发、部署、重启、Mark Ready、merge、账户访问、签名、交易所写入或自动下单。

---

## 1. SECOND_REVIEW_STATUS

```text
R1_ECONOMIC_MODEL = PASS
R1_THREE_SETUP_SCOPE = PASS
R1_PRIMARY_THRESHOLDS = PRESERVED
R1_SENSITIVITY_COUNT = PRESERVED
R1_CAUSAL_INTENT = PASS
R1_IMPLEMENTATION_PRECISION = INCOMPLETE_BEFORE_THIS_RECORD
R1_1_PRECISION_GAPS_CLOSED = YES

STRATEGY_DESIGN_OPTIMIZATION = COMPLETE_R1_1
BACKTEST_EXECUTED = NO
PERFORMANCE_IMPROVEMENT_PROVEN = NO
PRODUCTION_PATCH_AUTHORIZED = NO
```

第二次审查确认三个经济机制没有必要重做：

- `SWEEP_RECLAIM`：边界外流动性被触发后未被市场接受，价格收回；
- `BREAKOUT_RETEST`：边界外收盘获得接受，回踩不重新进入旧结构；
- `RANGE_EDGE_REJECTION`：稳定双边区间的边缘发生浅度拒绝并向内部回归。

本次修正不改变 R1 已预注册的六个 candidate ID 和核心阈值。修正对象仅为计算时点、状态优先级、窗口范围、执行语义、比较基线和统计裁决单位。

---

## 2. AUTHORITY_AND_BASELINE_HIERARCHY

必须保留三个不同基线，禁止混用：

```text
V0_1_EXACT_RUNTIME_BASELINE
= 精确复现 ac649 当前实际 runtime 行为，包括 STANDARD 后续推进缺陷

V0_1_INTENDED_STANDARD_REFERENCE
= 保留 v0.1 原始 Sweep / Breakout 参数和 FAST 行为，
  但依据现有 advance_prepare 规则在后续闭合 5m 上推进 retained PREPARE

V0_1_INTENDED_REFERENCE
= V0_1 exact FAST + V0_1 intended STANDARD
```

裁决用途：

- `V0_1_EXACT_RUNTIME_BASELINE` 只用于证明生产 parity 和量化现有运行时缺陷的影响；
- Sweep / Breakout 的经济优化必须与 `V0_1_INTENDED_REFERENCE` 比较；
- FAST 子集必须同时与 exact FAST 比较；
- STANDARD 子集必须与 intended STANDARD 比较；
- 不得把修复 STANDARD 缺陷产生的新增交易或收益记为新策略参数的改善。

因此，R1 Gate 3 中“相对 exact v0.1”修正为：

```text
EXISTING_SETUP_ECONOMIC_COMPARATOR = V0_1_INTENDED_REFERENCE
OPERATIONAL_DEFECT_COMPARATOR = V0_1_EXACT_RUNTIME_BASELINE
```

---

## 3. CAUSAL ATR NAMESPACES

R1 中单一符号 `A` 同时承担 pre-event 环境和 current-event 触发归一化，可能导致实现分叉。现冻结为：

```text
A_EVENT_t
= 当前生产 64 根闭合 5m Wilder 序列的最终 ATR 值，包含触发 K 线 t 的 TR

A_PRE_t
= 同一 64 根 authority candle 序列中，在纳入触发 K 线 t 的 TR 之前的倒数第二个 Wilder ATR 值
```

用途：

```text
A_PRE_t:
- ENV_PRE 的 D12 与 W24
- Level Reaction proximity
- Level Quality
- pre-event structure normalization

A_EVENT_t:
- 当前 K 线 excursion
- BODY_A / wick ratio threshold distances
- close extension
- Setup geometry
- Chase Limit
- Structural Stop
- signal-time target feasibility
- current volatility overlay
```

这一区分不增加历史窗口，也不要求未来数据。`A_PRE_t` 和 `A_EVENT_t` 必须由同一 64-candle exact authority sequence 导出。

Volatility regime 仍按生产 `wilder_atr14` 的 current event snapshot 计算，是 event-time safety overlay，不属于 `ENV_PRE` 的结构输入。

---

## 4. EXACT EXISTING BIAS AUTHORITY

新合同中的 `long_bias` / `short_bias` 固定复用 ac649 当前语义：

```text
C15 = 因果可见的闭合 15m close 序列

long_bias =
C15[-1] > mean(C15[-8:]) > mean(C15[-11:-3])

short_bias =
C15[-1] < mean(C15[-8:]) < mean(C15[-11:-3])
```

必须至少有 20 根因果对齐的闭合 15m。不得在 research candidate 中替换为 EMA、斜率、未闭合 15m 或其他趋势指标。

---

## 5. LEVEL_QUALITY EXACT WINDOW

R1 没有明确 Level Reaction 的完整搜索窗口。现冻结：

```text
LEVEL_REACTION_LOOKBACK = t-48 ... t-1
LEVEL_REACTION_ATR = A_PRE_t
TRIGGER_BAR_INCLUDED = NO
```

对当前候选边界 `L` 或 `U`，在上述 48 根闭合 5m 内判断 reaction。

支撑 reaction：

```text
low_i ∈ [L - 0.15*A_PRE_t, L + 0.15*A_PRE_t]
AND close_i >= L + 0.05*A_PRE_t
```

阻力 reaction 完全镜像。

### 5.1 Reaction clustering

连续或相邻的多根 K 线不得重复计数：

```text
QUALIFYING_BARS_GAP < 3 bars
=> 同一 reaction cluster

QUALIFYING_BARS_GAP >= 3 bars
=> 新 reaction cluster
```

每个 cluster 只计一次；cluster timestamp 使用该 cluster 最后一根 qualifying bar。`latest_reaction_age` 以当前触发 bar `t` 与最新 cluster timestamp 的 5m bar 距离计算。

候选 rolling high/low 的 defining candle 可以计为一次 reaction，但不能因为连续数根 K 线围绕同一极值而形成多个 reaction。

### 5.2 Quality

```text
Q0 = 0 clusters
Q1 = 1 cluster
Q2 = >=2 clusters AND latest_reaction_age <= 12
Q3 = >=3 clusters AND latest_reaction_age <= 12
```

Range 主候选继续要求：

```text
candidate edge >= Q2 AND age <= 12
opposite edge >= Q2 AND age <= 18
```

---

## 6. DETERMINISTIC ENVIRONMENT CLASSIFICATION

环境计算必须输出以下字段：

```text
environment_pre
environment_decision
transition_origin = RANGE | OTHER | NONE
transition_direction = UP | DOWN | NEUTRAL | NONE
environment_reason_code
```

### 6.1 ENV_PRE

先执行 DataQuality、历史长度、ATR、zero-range、volume 和 5m/15m alignment gate。失败即 `UNCERTAIN`。

结构指标全部只使用 `t` 之前的数据，并使用 `A_PRE_t`。

优先级：

```text
1. RANGE predicate true
   => ENV_PRE = RANGE

2. else exactly one of DIRECTIONAL_UP / DIRECTIONAL_DOWN true
   => corresponding DIRECTIONAL state

3. else transition-core true
   => ENV_PRE = TRANSITION

4. else
   => ENV_PRE = UNCERTAIN
```

`transition-core` 只包括确定表达式：

```text
0.35 < ER12 < 0.45
OR long_bias and D12 < 0
OR short_bias and D12 > 0
```

R1 中“价格正在破坏原环境的已验证边界”这一自然语言条件删除，不作为独立可编码 predicate。

### 6.2 Current-bar transition override

```text
if ENV_PRE = RANGE
and close_t >= U24 + 0.10*A_EVENT_t:
    ENV_DECISION = TRANSITION
    transition_origin = RANGE
    transition_direction = UP

elif ENV_PRE = RANGE
and close_t <= L24 - 0.10*A_EVENT_t:
    ENV_DECISION = TRANSITION
    transition_origin = RANGE
    transition_direction = DOWN

else:
    ENV_DECISION = ENV_PRE
```

没有方向的 transition-core：

```text
transition_direction = NEUTRAL
```

Breakout 的 `TRANSITION_FROM_RANGE_UP/DOWN` 现在精确定义为：

```text
ENV_DECISION = TRANSITION
AND transition_origin = RANGE
AND transition_direction matches candidate side
```

Neutral transition 不得支持 Breakout。

---

## 7. NUMERIC_EDGE_CASES_AND_DUAL_EDGE

以下任一成立，当前 bar 不产生 actionable candidate：

```text
H_t == L_t
A_PRE_t <= 0
A_EVENT_t <= 0
M20 <= 0
non-finite Decimal
price or volume <= 0
5m / 15m alignment invalid
```

所有策略 predicate 使用 exact `Decimal` 比较，先判断策略条件，后做交易所价格精度 rounding。不得在 predicate 之前转 float 或提前 quantize。

### 7.1 Wick ratio

Long lower wick：

```text
(min(O_t, C_t) - L_t) / (H_t - L_t)
```

Short upper wick：

```text
(H_t - max(O_t, C_t)) / (H_t - L_t)
```

### 7.2 Range dual-edge

```text
low_t <= lower + 0.15*A_EVENT_t
AND
high_t >= upper - 0.15*A_EVENT_t
```

成立时：

```text
RANGE_DUAL_EDGE_AMBIGUOUS
ENV_DECISION = UNCERTAIN for actionable arbitration
NO_ACTION
```

raw evidence 仍必须输出。

---

## 8. PREPARE FREEZE_AND_REEVALUATION_RULE

建立 PREPARE 时冻结：

```text
setup boundary
setup A_EVENT
setup initial extreme
setup entry geometry
setup chase limit
setup structural stop
setup level quality and reaction evidence
setup environment_pre / transition metadata
setup trigger candle identity and hash
```

后续第 1–3 根闭合 5m 使用冻结 boundary 与 setup ATR 做 confirmation / invalidation 比较，禁止随着 rolling high/low 或 ATR 变化漂移已有 Setup。

每根后续闭合 5m 必须重新检查：

```text
DataQuality
current prohibited environment
current target feasibility
opposite accepted outcome
duplicate / active policy
expiry
```

环境动态失效：

- Range PREPARE：`ENV_DECISION != RANGE` 即 invalidated；
- Sweep Long：变为 `DIRECTIONAL_DOWN`、`UNCERTAIN` 或 `EXTREME` 即 invalidated；Short 镜像；
- Breakout Long：变为 `DIRECTIONAL_DOWN`、`UNCERTAIN`、`EXTREME`，或 Range 且无 matching transition，即 invalidated；Short 镜像。

后续 bar 处理顺序：

```text
1. advance / invalidate all retained PREPARE
2. finalize terminal state transitions
3. enumerate new raw candidates
4. group market events
5. arbitrate publication
```

旧 PREPARE 在当前 bar 确认时，当前 bar 的新 raw candidates 仍记录，但 publication 服从 active-state policy。

---

## 9. TARGET_FEASIBILITY_AND_ENTRY_REFERENCE

R1 的 `planned_entry` 现精确定义为 signal-time authority：

```text
decision_reference_price
= current ContextSummary.reference_price at the causal decision cutoff

OHLCV_ONLY_RESEARCH_BRIDGE:
decision_reference_price = trigger 5m close

planned_entry
= production-equivalent directional rounding of
  clamp(decision_reference_price, entry_zone_low, entry_zone_high)
```

signal-time target feasibility 使用 `planned_entry`、冻结 structural stop 和冻结 structural obstacle。

```text
planned_R = abs(planned_entry - structural_stop)
round_trip_all_in_cost_rate = 2 * (0.00045 + 0.00050) = 0.00190
reserve = max(0.10*A_EVENT, planned_entry*0.00190)
```

`TARGET_FEASIBILITY` 只有三个值：

```text
PASS
FAIL
NO_KNOWN_STRUCTURAL_OBSTACLE
```

- `NO_KNOWN_STRUCTURAL_OBSTACLE` 只适用于 Breakout；
- 它允许进入研究，但不能改写为“无限目标空间”；
- 必须独立报告事件数、净 R、回撤和收益贡献。

STANDARD PREPARE 时若完整计算所需信息已经可用，只能是 `PASS` 或 `FAIL`；不得使用未定义的隐式 UNKNOWN。`FAIL` 不建立 PREPARE。

---

## 10. BREAKOUT_OBSTACLE_OFF_BY_ONE_CORRECTION

R1 写作 `t-64 ... t-13`，但 current authority input 为 64 根闭合 5m（含 `t`），且三 K 线 swing 需要左右邻居。现修正：

```text
available authority bars = t-63 ... t
recent boundary bars = t-12 ... t-1
obstacle source bars = t-63 ... t-13
eligible swing centers = t-62 ... t-14
```

Long swing high：

```text
high_i > high_{i-1}
AND high_i >= high_{i+1}
AND high_i > planned_entry
```

Short 镜像。

“nearest obstacle”定义为价格距离最近：

```text
Long: minimum positive (swing_high - planned_entry)
Short: minimum positive (planned_entry - swing_low)
```

价格距离相同时，选择时间上最近的 swing；再次相同则使用 candle identity 的确定性顺序。

---

## 11. EXECUTION_SIMULATION_POLICY

策略信号、产品 TradePlan 和实际人工成交必须分层报告。

### 11.1 Signal-time plan

- entry zone、planned entry、stop、TP1=1R、TP2=2R 在 signal-time 冻结；
- signal expiry：FAST 180 秒，STANDARD 900 秒；
- Chase Limit 是人工成交的绝对上限，不是建议入场价。

### 11.2 Primary manual execution simulation

```text
ORDER_MODEL = DELAYED_TAKER
TOTAL_RESPONSE_DELAY = 30 seconds primary
SENSITIVITY = 15 seconds / 60 seconds
```

`TOTAL_RESPONSE_DELAY` 包含通知、阅读、判断与手工操作的总延迟，从 `signal_created_at` 开始。

若只有 1m 数据且 eligible timestamp 位于 1m 内：

```text
Long adverse eligible price = whole-minute high
Short adverse eligible price = whole-minute low
PATH_STATUS = DELAY_FILL_AMBIGUOUS
```

这是保守执行假设。若 adverse price 超过 Chase Limit、已越过 structural stop 或 signal 已过期：

```text
MISSED_NO_FILL
```

实际模拟成交价应用 5 bps adverse execution offset。产品计划的 stop、TP1、TP2 保持 signal-time 锁定；不得因看见后续路径而重算。

必须同时报告：

```text
planned_entry
simulated_entry
entry_deviation
planned_R
actual_distance_to_stop
realized_R_on_planned_risk
realized_R_on_actual_entry_risk
```

### 11.3 Scale-out policy

为了让 TP1/TP2 产生唯一经济结果，主回测固定：

```text
50% quantity exits at TP1
50% quantity exits at TP2
remaining stop stays at original structural stop after TP1
NO automatic breakeven move
```

这只是统一回测执行政策，不是对用户的交易指令。任意不同人工减仓方式只进入 forward-learning outcome，不得回填历史策略输入。

### 11.4 Maximum holding horizon

```text
MAX_HOLDING_TIME = 24 hours from simulated entry
```

在 24 小时内未触及 stop 或完成 TP2：

```text
TIME_EXIT_24H
```

按 24 小时截止后的第一根可用 1m close 加 adverse exit offset 平仓。若 `TIME_EXIT_24H` 占某裁决单元交易数超过 10%，该单元不得 GO，状态为 `INCONCLUSIVE_HOLDING_RULE_SENSITIVE`。

### 11.5 Intra-minute priority

- 同一 1m 内 stop 与任一 target 同时可达：`AMBIGUOUS_PATH / STOP_FIRST`；
- 同一 1m 内 TP1 与 TP2 同时可达且 stop 未触发：按 TP1 后 TP2 处理；
- 无 1m 证据：`AMBIGUOUS_PATH / STOP_FIRST`；
- fee 对每个实际 entry / exit fill 计收。

---

## 12. SINGLE_ASSET_CONCURRENCY_POLICY

First Launch 为 ETH-only。最终可执行回测固定：

```text
MAX_CONCURRENT_OPEN_TRADES = 1
PYRAMIDING = NO
SAME_DIRECTION_ADD_ON = NO
AUTOMATIC_REVERSAL = NO
```

存在 open trade 时：

- 所有新 raw candidate 继续记录；
- 不产生第二笔可执行成交；
- 反向信号不自动平仓或反手；
- 标记 `SUPPRESSED_OPEN_TRADE`；
- trade 关闭所在 1m 内不得立即建立新 trade；最早从其后第一个新闭合 5m decision cutoff 重新评估。

信号已确认但尚未成交期间，仍服从 signal expiry 和 single-active publication policy。

---

## 13. DETERMINISTIC_ARBITRATION_AND_TIE_BREAKS

R1 中“证据等级最高者”现冻结为确定性排序。对同方向、同一 decision cutoff、同一 market event 的多个可发布候选，按以下顺序选择：

```text
1. CONFIRMED output > PREPARE > WATCH/raw-only
2. existing active event continuation > new event
3. Q3 > Q2 > Q1 > Q0
4. TARGET_FEASIBILITY PASS > NO_KNOWN_STRUCTURAL_OBSTACLE
5. larger available_space / planned_R
6. smaller distance from decision_reference_price to entry zone
7. newer latest_reaction timestamp
8. earlier candidate creation timestamp
9. lexicographically smaller immutable candidate_id
```

FAST 与 STANDARD 的同事件规则继续按 R1：FAST 已发布后，后续 STANDARD 只能是 duplicate evidence；PREPARE 期间后续强确认仍归类为 STANDARD。

不同方向在 active expiry 或 open trade 内都记录，但默认不发布第二个反向信号。

---

## 14. MARKET_EVENT_CONTACT_AND_LEVEL_IDENTITY

Boundary contact 现精确定义：

```text
abs(relevant extreme - level_price) <= 0.15 * event_start_A
```

- 支撑使用 low；阻力使用 high；
- `event_start_A` 在事件开始时冻结；
- `canonical_level_price` 使用 exact Decimal canonical string，不使用 float；
- 若 manifest 提供交易所 price precision，仅在最终 display / TradePlan rounding 使用，market-event grouping 在 exact strategy Decimal 上完成。

沿用 level instance 的条件继续为：

```text
abs(new_level - active_level) <= 0.05 * event_start_A
```

事件结束规则不得反馈到候选决策。

---

## 15. HISTORICAL_ARRIVAL_SEMANTICS

数据 manifest 必须声明：

```text
ARRIVAL_MODE = OBSERVED_RECEIVED_AT
             | SYNTHETIC_CLOSE_TIME
```

- Hyperliquid live capture / exact retained evidence 使用真实 `received_at`；
- 只有 OHLCV close-time 的历史数据使用 `SYNTHETIC_CLOSE_TIME`：`received_at = candle.close_time`；
- 同一 5m cutoff 的 15m candle 只有在其 `close_time <= cutoff` 且 synthetic/observed `received_at <= cutoff` 时可见；
- synthetic arrival 结果不得被描述为真实历史网络延迟表现；
- manual response delay 从生成信号的 synthetic/observed `received_at` 开始。

任何 dataset 若无法唯一确定 candle boundary、UTC、close-time convention 或 duplicate/conflict disposition，fail closed。

---

## 16. DECISION_UNITS_AND_NO_POOLING_RULE

不得用一个强子组掩盖一个负子组。

最低报告单元：

```text
setup_family × side × confirmation_mode
```

生产候选准入单元：

```text
setup_family × side
```

FAST 与 STANDARD 必须分别报告；只有当二者 interaction 与总风险通过时，才能作为同一 setup-side policy 联合启用。

规则：

- Long 正、Short 负时不得报告“该 Setup 整体 GO”；
- FAST 正、STANDARD 负时不得用合并收益隐藏 STANDARD；
- 允许最终只保留通过 Gate 的 setup-side/mode 单元；
- Combined policy 只能纳入已经单独满足其准入要求的单元；
- Range 没有旧生产 comparator，必须先独立证明成本后正期望和风险可接受，再评估增量组合价值。

---

## 17. ONE_SHOT_EVALUATION_AND_STATISTICAL_PROTOCOL

### 17.1 Dataset lock

在第一次经济结果运行前必须冻结：

```text
dataset manifests
exact time ranges
proxy time ranges
candidate IDs
execution policy
bootstrap seed rule
result schema
```

Pipeline 开发、fixture 和 parity 调试所用数据不得作为唯一经济裁决证据。经济 evaluation periods 在首次结果生成前必须 hash-lock。

### 17.2 Sensitivity rule

- primary candidate 才能直接进入 GO 裁决；
- sensitivity 只用于判断主候选失败是否集中在预注册单一变量；
- sensitivity 即使盈利，也不能在同一结果集上直接晋级为生产候选；
- 若 sensitivity 支持继续研究，结论只能是 `REVISE`，生成新 Contract ID，并使用未被消费的新 holdout evidence。

### 17.3 Trial ledger

必须保存全部尝试：

```text
contract_id
candidate_id
dataset_hash
code_hash
execution_policy_id
result_hash
disposition
```

禁止删除失败 run、替换数据区间或重新命名 sensitivity。

### 17.4 Event bootstrap

主 Gate 的 confidence interval 固定：

```text
RESAMPLING_UNIT = independent market_event_id
BOOTSTRAP_REPLICATIONS = 10,000
SEED = first 64 bits of SHA256(run_id + dataset_hash + candidate_id)
LOWER_CONFIDENCE_BOUND = one-sided 95% percentile lower bound
```

少于 30 个 independent proxy market events 时不计算 GO，只能 `INCONCLUSIVE`。30 是最低可估计性门槛，不保证统计功效。

Deflated Sharpe Ratio / PBO 可作为补充诊断，但不得替代 event-level net expectancy、confidence bound、concentration 和 cost stress Gate。

---

## 18. AMENDED_ACCEPTANCE_GATES

### Gate 0 — Correctness

继续要求：

```text
STANDARD deterministic defect test PASS
V0_1_EXACT_RUNTIME parity = 100%
V0_1_INTENDED_REFERENCE reproducible
instrumented final-output mismatch = 0
lookahead = 0
5m/15m causal alignment PASS
arrival mode declared
all numeric edge fixtures PASS
```

### Gate 1 — Evidence

每个 primary `setup × side`：

```text
proxy independent events >= 30
at least two non-overlapping time blocks
exact recent evidence reported separately
no unexplained dataset conflict
```

### Gate 2 — Economic viability

每个准入单元必须：

```text
net expectancy after fees/offset/delay > 0
one-sided event-bootstrap 95% lower bound > 0
top-5 positive trades contribution <= 50%
30s and 60s delay do not flip conclusion negative
TIME_EXIT_24H share <= 10%
exact recent and proxy do not show directional contradiction
```

`NO_KNOWN_STRUCTURAL_OBSTACLE` Breakout 子组必须单独报告；若该子组贡献超过 Breakout 总正收益的 50%，Breakout 状态不得直接 GO，至少为 `INCONCLUSIVE_CONCENTRATION`，除非 exact recent evidence 对该子组方向一致。

### Gate 3 — Existing Setup improvement

Sweep / Breakout 相对 `V0_1_INTENDED_REFERENCE` 必须形成 Pareto improvement：

```text
expectancy improves without worse drawdown/losing streak
OR
risk improves without lower expectancy
```

同时：

```text
FAST candidate vs exact FAST
STANDARD candidate vs intended STANDARD
```

均须单独报告。

### Gate 4 — Combined policy

```text
only individually eligible units included
unexplained baseline displacement = 0
unexplained opposite conflict = 0
duplicate publication per market event = 0
max concurrent open trade = 1
combined net expectancy > 0
combined risk not dominated by a simpler eligible subset
```

组合结果不得使单独 `REJECT` 或 `INCONCLUSIVE` 单元获得生产资格。

---

## 19. ENGINEERING_FIXTURES_REQUIRED_BY_STRATEGY

工程实施前至少需要确定性 fixture 覆盖：

1. `A_PRE` 与 `A_EVENT` 不同且分类稳定；
2. 48-bar reaction clustering；
3. candidate defining extreme 只计一个 cluster；
4. environment precedence 与 neutral transition；
5. range-to-transition UP / DOWN；
6. zero-range、zero-volume、invalid ATR；
7. Range dual-edge；
8. frozen boundary/ATR across PREPARE；
9. Sweep / Breakout / Range dynamic invalidation；
10. Breakout obstacle window `t-62...t-14`；
11. obstacle price-nearest tie-break；
12. same-event FAST/Standard dedupe；
13. multiple same-direction candidate ranking；
14. opposite candidate suppression；
15. one-open-trade policy；
16. delayed fill inside/outside Chase Limit；
17. fixed TP1/TP2 scale-out；
18. TP1 then stop with unchanged stop；
19. same-1m stop/TP ambiguity；
20. 24h time exit；
21. synthetic vs observed arrival mode；
22. exact runtime vs intended reference attribution separation。

---

## 20. PRODUCT_INPUT_AFTER_R1_1

产品窗口应以 R1 + 本 R1.1 为共同策略输入。

新增必须理解的产品语义：

- `Environment State` 需要 transition direction / origin 才能解释 Breakout；
- Level Quality 来自 48-bar clustered reactions；
- Signal-time plan 与实际人工 fill 可能不同；
- Chase Limit 是硬上限；
- TP1/TP2 主回测采用 50%/50%，TP1 后不自动移动止损；
- 一个 ETH open trade 期间新候选只记录、不自动加仓或反手；
- `TIME_EXIT_24H`、`SUPPRESSED_OPEN_TRADE`、`DELAY_FILL_AMBIGUOUS` 是研究/结果状态，不默认要求全部进入 First Launch 主卡；
- 当前 STANDARD runtime 缺陷仍必须独立修复，R1.1 不改变该事实。

---

## 21. FINAL_STATUS

```text
WORK_PACKAGE_A_STRATEGY_CONTRACT = COMPLETE_R1_1
WORK_PACKAGE_B_BACKTEST_INPUT = COMPLETE_R1_1

ECONOMIC_MECHANISMS = PASS
CAUSAL_TIME_SEMANTICS = PASS
LEVEL_QUALITY_WINDOW = PASS
ENVIRONMENT_PRECEDENCE = PASS
TRANSITION_DIRECTION = PASS
PREPARE_FREEZE_SEMANTICS = PASS
TARGET_FEASIBILITY_REFERENCE = PASS
BREAKOUT_OBSTACLE_INDEXING = PASS
EXECUTION_POLICY = PASS
CONCURRENCY_POLICY = PASS
ARBITRATION_TIE_BREAK = PASS
STATISTICAL_PROTOCOL = PASS
BASELINE_ATTRIBUTION = PASS

NUMERIC_PRIMARY_CANDIDATES_CHANGED = NO
ADDITIONAL_PARAMETER_GRID = NO
BACKTEST_EXECUTED = NO
PERFORMANCE_IMPROVEMENT_PROVEN = NO
STANDARD_RUNTIME_DEFECT = STILL_BLOCKING_PRODUCTION
PRODUCT_REVIEW_CAN_START = YES
ENGINEERING_FINAL_ROUTE_REQUIRES_PRODUCT_FREEZE = YES
PRODUCTION_PATCH_AUTHORIZED = NO
```
