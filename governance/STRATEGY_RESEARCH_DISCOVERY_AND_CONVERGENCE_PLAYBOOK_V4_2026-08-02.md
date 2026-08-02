# Strategy Research Discovery and Convergence Playbook V4

**记录 ID：** `TA-STRATEGY-RESEARCH-DISCOVERY-CONVERGENCE-PLAYBOOK-2026-08-02-V4`  
**日期：** `2026-08-02`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `MANDATORY FUTURE RESEARCH METHOD / NON-EXECUTABLE / NON-AUTHORIZING`  
**优先级：** 本文件取代与其冲突的 V1/V2/V3；V3 中不冲突内容继续有效。  
**适用范围：** 所有 Setup、Scanner、市场状态、入场、止损、止盈、持仓管理和参数研究。  
**权限边界：** 不授权代码修改、回测执行、工程派发、部署、账户访问、交易所写入或自动交易。

---

## 1. 默认交易研究目标

```text
CONTEXT_TIMEFRAME = 1h
PRIMARY_STRUCTURE_TIMEFRAME = 15m
EXECUTION_TIMEFRAME = 5m
MICRO_TIMEFRAME = 1m/3m OPTIONAL_PATH_EVIDENCE_ONLY
TRADING_HORIZON = INTRADAY
HOLDING_TIME = PATH_DEPENDENT_NOT_FIXED
ENTRY_AND_EXIT = MAY_SCALE
HUMAN_FINAL_AUTHORITY = CURRENTLY_YES
```

默认研究的是 15 分钟主导的日内交易，不得静默改成波段、长线或固定持有期策略。

---

## 2. 最高优先级：只根据已发生事实决策

```text
OBSERVED_FACTS_ONLY = YES
CLOSED_AND_RECEIVED_DATA_ONLY = YES
LOOKAHEAD = PROHIBITED
FUTURE_PATH_ASSUMPTION = PROHIBITED
TIME_TO_COMPLETION_FORECAST = PROHIBITED
```

波动率只可用于归一化、观察尺度、已发生速度和幅度分类、结果分层；不得预测行情将在多少分钟或多少根 K 线后完成。

固定时间或 bar count 只可用于指标统计窗口、数据启动历史、工程归档或明确 comparator，不得单独成为经济意义上的确认或失效条件。

---

## 3. Signal Authority 与高周期背景严格分离

```text
SIGNAL_AUTHORITY = SETUP_OBSERVED_FACTS
HTF_ROLE = CONTEXT_LABEL + ATTRIBUTION + POST_BACKTEST_POLICY_RESEARCH
AUTOMATIC_HTF_FILTER_IN_FIRST_BACKTEST = DISABLED
```

满足 Setup 自身因果规则、5m/15m 数据有效且具有可执行 Entry/Stop/Chase/Target Feasibility 的候选，应进入第一轮回测。不得在回测前因为其与 1h 趋势逆向、1h 中性、1h 转换或 1h 背景暂时不可用而提前删除。

1h 背景用于回答：

- 顺势与逆势是否存在统计差异；
- 差异是否依赖 Setup、方向、波动状态和入场模式；
- 未来应当只提示、排序、调整仓位、增加确认，还是成为特定 Setup 的过滤器。

这些结论必须来自回测与影子证据，而不是预先假定。

---

## 4. 1h 趋势采用双标签，不提前合并

每个候选同时记录：

```text
HTF_MOMENTUM_STATE
HTF_STRUCTURE_STATE
```

### 4.1 动量标签

可使用方向效率、ATR 归一化净位移等因果指标，例如：

```text
HTF_MOMENTUM_UP
HTF_MOMENTUM_DOWN
HTF_MOMENTUM_NEUTRAL
HTF_MOMENTUM_UNAVAILABLE
```

具体窗口和阈值属于回测候选，不是永久市场真理。

### 4.2 价格结构标签

使用已因果确认的 1h Swing：

```text
HTF_STRUCTURE_UP
HTF_STRUCTURE_DOWN
HTF_STRUCTURE_RANGE
HTF_STRUCTURE_TRANSITION
HTF_STRUCTURE_INSUFFICIENT
HTF_STRUCTURE_UNAVAILABLE
```

任何左右窗口 Pivot 只有在右侧 K 线闭合并已收到后才能生效。

### 4.3 关系标签

基于交易方向与两类背景生成：

```text
HTF_ALIGNED_STRONG
HTF_ALIGNED_PARTIAL
HTF_COUNTERTREND_STRONG
HTF_COUNTERTREND_PARTIAL
HTF_CONFLICTED
HTF_NEUTRAL
HTF_CONTEXT_INCOMPLETE
```

所有关系标签都进入第一轮结果分层，不作为候选生成门槛。

---

## 5. 三种“不确定”必须严格区分

### 5.1 市场方向不明确

例如 1h 横盘、结构转换、动量与结构冲突。

```text
HTF_CONTEXT = NEUTRAL | TRANSITION | CONFLICTED
SIGNAL_GENERATION = ALLOWED
DATA_QUALITY = READY
```

这是正常市场事实，不是数据故障。

### 5.2 只有 1h 背景不可用

当 5m/15m 和 Setup 数据有效，但 1h 历史不足、暂缺或无法计算背景：

```text
SIGNAL_GENERATION = ALLOWED_FOR_RESEARCH_AND_CURRENT_HUMAN_REVIEW
HTF_CONTEXT = UNAVAILABLE
DATA_5M = READY
DATA_15M = READY
DATA_1H = UNAVAILABLE
```

不得静默归入中性或逆势，也不得在第一轮自动降低仓位、风险或信号等级。

### 5.3 核心多周期数据损坏

当 5m/15m 关键输入损坏、K 线未闭合、时间轴无法因果对齐、关键价格或 ATR 无效：

```text
MULTITIMEFRAME_DATA_INVALID
ACTIONABLE_SIGNAL = NO
RAW_CANDIDATE_AND_ERROR_EVIDENCE = RETAINED
```

不可执行的原因是输入不可信，而不是趋势方向不明确。

---

## 6. 禁止不可解释的综合信心分数

不得把 Setup、HTF、数据完整性、Target Feasibility、Chase 和波动状态压缩成一个不可解释的总分。

必须分字段记录和展示：

```text
SETUP_QUALITY
HTF_RELATION
HTF_MOMENTUM_STATE
HTF_STRUCTURE_STATE
DATA_QUALITY
TARGET_FEASIBILITY
CHASE_STATUS
VOLATILITY_STATE
```

未来可以基于回测结果形成排序模型，但原始维度和原因必须保留。

---

## 7. 第一轮必须进行的后验政策比较

使用同一批原始事件和结果，至少比较：

```text
POLICY_ALL
POLICY_MOMENTUM_ALIGNED
POLICY_STRUCTURE_ALIGNED
POLICY_CONSENSUS_ALIGNED
POLICY_ALIGNED_OR_NEUTRAL
POLICY_SETUP_SPECIFIC
```

必须同时报告：

- 信号数量变化；
- 成本后平均和总净 R；
- 最大回撤；
- 漏失盈利事件；
- 样本量与结果集中度；
- Setup × 波动状态 × HTF 关系的差异。

不得只因过滤后胜率提高而宣布有效。

---

## 8. Range 的特殊处理

Range 的交易依据是已经形成的上下边界、边缘反应、结构止损和可行空间，不预测区间最终向何方突破。

```text
RANGE_SIGNAL_GENERATION = BOTH_VALID_EDGES
HTF_FILTER = NONE_IN_FIRST_BACKTEST
HTF_CONTEXT = ATTRIBUTION_ONLY
```

仍需记录 1h 背景，以检验强趋势环境下区间两侧交易是否存在不对称，但不得在第一轮预先排除任一侧。

---

## 9. 强制研究输出

进入回测前至少形成：

1. 普通语言策略地图；
2. 当前研究问题集；
3. 外部证据矩阵；
4. 可观察字段字典；
5. 共同事件和状态模型；
6. 完整候选优先级；
7. 第一轮参数包；
8. 无未来数据与事实驱动生命周期合同；
9. HTF 双标签与数据质量合同；
10. 研究、产品、工程和延期范围。

```text
DISCOVER_AND_CONVERGE
→ REGISTER_AND_BACKTEST
→ SHADOW_AND_HUMAN_REVIEW
→ VERSIONED_PROMOTION
```
