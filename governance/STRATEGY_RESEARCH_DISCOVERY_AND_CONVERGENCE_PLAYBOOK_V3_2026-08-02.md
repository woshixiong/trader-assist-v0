# Strategy Research Discovery and Convergence Playbook V3

**记录 ID：** `TA-STRATEGY-RESEARCH-DISCOVERY-CONVERGENCE-PLAYBOOK-2026-08-02-V3`  
**日期：** `2026-08-02`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `MANDATORY FUTURE RESEARCH METHOD / NON-EXECUTABLE / NON-AUTHORIZING`  
**优先级：** 本文件取代与其冲突的 V1/V2。  
**适用范围：** 所有 Setup、Scanner、市场状态、入场、止损、止盈、持仓管理和参数研究。  
**权限边界：** 不授权代码修改、回测执行、工程派发、部署、账户访问、交易所写入或自动交易。

---

## 1. 默认研究目标

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

项目默认研究的是 15 分钟主导的日内交易，不得静默改成波段、长线或固定持有期策略。

日内研究必须平衡：

- 信号数量；
- 胜率；
- 平均盈利 R；
- 平均亏损 R；
- 成本；
- 回撤；
- 结构止损；
- 实际可获得的日内空间。

约 1R 的成本后机会可以接受；固定 R 只是基线和影子检查点，不是唯一退出权威。

---

## 2. 最高优先级原则：只根据已发生事实决策

```text
OBSERVED_FACTS_ONLY = YES
CLOSED_AND_RECEIVED_DATA_ONLY = YES
FUTURE_PATH_ASSUMPTION = PROHIBITED
TIME_TO_COMPLETION_FORECAST = PROHIBITED
```

策略不得假定：

- 行情应该在多少分钟内完成突破、回踩或趋势；
- 低波动一定会在更长时间后完成；
- 高波动一定会迅速达到目标；
- 某形态未来必然继续；
- 固定数量 K 线之后机会天然失效。

波动率的合法用途是：

- 归一化距离、实体、止损、价格带宽度和 Chase Limit；
- 选择更合适的观察尺度；
- 判断当前已经发生的运动相对正常波动是快、慢、强或弱；
- 进行分层归因和敏感性比较。

波动率不得被用来预言行情将在何时、以何种路径完成。

固定时间或 bar count 仅可用于：

- 指标统计窗口；
- 数据启动历史；
- 工程资源清理和证据归档；
- 明确标记的 comparator。

固定时间不得单独成为经济意义上的确认或失效条件。

---

## 3. 状态驱动而非时钟驱动

每个 PREPARE / WATCH / SETUP_READY 状态必须由已经发生的价格事实推进：

```text
STATE_CONTINUES_WHILE:
original structure remains valid
AND no opposite confirmed event
AND no accepted re-entry invalidates the hypothesis
AND entry has not exceeded Chase Limit
AND target feasibility has not failed
AND data remains causally valid
```

确认由形态与路径触发，例如：

- 收回带内后形成更高低点或更低高点；
- 带外接受后回踩保持原结构；
- 回踩结束后重新形成同方向推进；
- 新的因果结构确认支持原方向。

失效由事实触发，例如：

- 价格重新接受旧结构；
- 对侧 Setup 得到确认；
- 原关键价格带被新的结构取代；
- 价格已超过可接受追价范围；
- 前方结构空间不足；
- 数据质量或因果对齐失败。

仅因经过了 N 根 K 线或 N 分钟，不得自动宣告策略失效。

---

## 4. 多周期职责

```text
1h = 已经形成的上层方向背景
15m = 关键价格带与交易机会
5m = 可执行确认与入场时机
1m/3m = 路径还原和可选微观证据
```

1h 方向是现有事实分类，不是未来预测。

每个候选必须标记：

```text
ALIGNED
NEUTRAL_CONTEXT
COUNTERTREND
UNCERTAIN
```

第一轮必须同时比较：

- 无 1h 过滤；
- 顺势/中性可操作、逆势仅影子；
- 各 Setup 与方向的独立结果。

不得只因交易数量下降就宣称方向过滤有效；必须比较成本后期望、回撤、漏失机会和样本量。

Range 必须按交易方向与 1h 趋势判断，不得粗暴要求 1h 必须中性：

- HTF_UP：Range Long 为 aligned，Range Short 为 countertrend；
- HTF_DOWN：Range Short 为 aligned，Range Long 为 countertrend；
- HTF_NEUTRAL：两侧均为 neutral context。

---

## 5. 研究流程

```text
REAL TRADING OBJECTIVE
→ CURRENT SYSTEM IN PLAIN LANGUAGE
→ HUMAN OBSERVATION AS HYPOTHESIS
→ OBSERVABLE MARKET OBJECTS AND STATES
→ EXTERNAL EVIDENCE ACROSS MATURE MARKETS
→ COMMON EVENT MODEL
→ RESEARCH QUESTION SET
→ CANDIDATE PRIORITY QUEUE
→ FIRST-ROUND PARAMETER PACKET
→ FORMAL BACKTEST OPERATING STANDARD
→ PRODUCT / ENGINEERING HANDOFF
```

研究问题数量不设固定值；每个问题必须是当前决策所必需、输入可观察、输出可测试，并经过收敛门禁分类为当前、影子、后续或拒绝。

---

## 6. 候选优先级

```text
P0_COMPARATOR
P1_PRIMARY
P2_SECONDARY_OR_SENSITIVITY
P3_DEFERRED_EVIDENCE_CANDIDATE
REJECTED_WITH_REASON
```

未入选候选不得消失。每个候选必须记录：

```text
candidate_id
priority
mechanism
why_now_or_later
required_data
implementation_cost
promotion_condition
rejection_or_defer_reason
```

---

## 7. 人工经验和截图

```text
SCREENSHOT_OR_OBSERVATION
→ VISIBLE_FACTS
→ TRADER_INTERPRETATION
→ TESTABLE_SYSTEM_HYPOTHESIS
→ REQUIRED_DATA
→ COMPARATOR_OR_QUALITY_LABEL
```

截图可以发现反例和结构，但单张截图不能证明统计优势、实时订单簿状态或未来路径。

人工经验是高价值研究输入，但必须被翻译为因果、可观察、可复现和可证伪的规则。

---

## 8. 外部研究

默认跨市场检索：高流动性加密永续、黄金、原油、股指期货、外汇、高流动性股票和其他成熟订单簿市场。

```text
OFFICIAL_EXCHANGE_OR_API_DOCS
→ PEER_REVIEWED_MICROSTRUCTURE_OR_MARKET_RESEARCH
→ HIGH_QUALITY_WORKING_PAPERS
→ MATURE_OPEN_SOURCE_IMPLEMENTATIONS
→ REPRODUCIBLE_STRATEGY_CODE
→ COMMUNITY_AND_TRADER_RULES
```

```text
CROSS_MARKET_MECHANISM_REUSE = YES
DIRECT_PARAMETER_COPY = NO
PUBLIC_BACKTEST_RESULT_AS_PRODUCTION_AUTHORITY = NO
```

---

## 9. 工程和策略边界

策略研究负责：经济机制、事实状态、参数候选、对照、失败条件和结果裁决。

工程负责：因果回放、数据、测试、报告、可复现性和最低实现成本。

工程不得自行改变参数或用技术方便性替代策略含义。研究未收敛时不得进入生产开发。

---

## 10. 强制输出

进入回测前至少形成：

1. 普通语言策略地图；
2. 当前研究问题集；
3. 外部证据矩阵；
4. 可观察字段字典；
5. 共同事件和状态模型；
6. 完整候选优先级；
7. 第一轮参数包；
8. 无未来数据与事实驱动生命周期合同；
9. 研究、产品、工程和延期范围。

```text
DISCOVER_AND_CONVERGE
→ REGISTER_AND_BACKTEST
→ SHADOW_AND_HUMAN_REVIEW
→ VERSIONED_PROMOTION
```
