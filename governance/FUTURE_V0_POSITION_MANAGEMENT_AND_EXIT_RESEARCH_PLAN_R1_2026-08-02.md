# Future V0 Position Management and Exit Research Plan R1

**记录 ID：** `TA-FUTURE-V0-POSITION-MANAGEMENT-EXIT-RESEARCH-R1-2026-08-02`  
**日期：** `2026-08-02`  
**状态：** `FUTURE RESEARCH / PRODUCT PLANNING / NON-EXECUTABLE / NON-DEPLOYMENT`  
**关联：** PR #52、First Launch 三 Setup、Scanner Lite R3、Strategy Research and Backtest Operating Standard V1  
**权限边界：** 本文不授权实现、回测执行、部署、账户访问、交易所写入、自动下单、自动止盈或自动止损。

---

## 1. 最终方向

当前 First Launch 的核心任务仍然是：

```text
ENTRY_FIRST
+ INITIAL_STRUCTURAL_STOP_REQUIRED
+ HUMAN_EXIT_AUTHORITY
+ SHADOW_EXIT_REFERENCE
```

本轮策略优化优先解决：

- 哪些价格带值得交易；
- Sweep / Breakout / Range 的入场条件；
- FAST / STANDARD 的真假突破和入场位置；
- 入场时结构止损；
- 入场后的最大计划风险。

当前不把完整动态止盈系统放入关键路径。

未来 V0 的目标工作流：

```text
SYSTEM_ENTRY_PROPOSAL
→ HUMAN_CONFIRM
→ SYSTEM_SUBMITS_ENTRY
→ SYSTEM_MONITORS_POSITION
→ SYSTEM_PROPOSES_STOP_OR_EXIT_ACTION
→ HUMAN_CONFIRM
→ SYSTEM_SUBMITS_REDUCE_ONLY_OR_CLOSE
```

未来自动交易前，建仓、减仓、止盈、移动止损和最终平仓均需要经历可审计的系统建议和人工确认阶段。

---

## 2. 核心原则

### 2.1 入场决定最大计划亏损

每一笔候选在入场前必须确定：

```text
ENTRY_ZONE
INITIAL_STRUCTURAL_STOP
PLANNED_RISK
POSITION_SIZE
```

初始止损基于策略失效结构，不基于任意固定美元或百分比。

止损在持仓后只能：

```text
KEEP
OR TIGHTEN
```

不得因为行情不利而向扩大亏损方向移动。

### 2.2 盈利是路径依赖的

盈利不能只由一个固定 TP 决定。系统需要研究并组合：

- 固定 R 检查点；
- 下一关键价格带；
- 支撑/阻力转换；
- 新形成的高低点结构；
- 趋势斜率和方向效率衰减；
- 震荡或反转；
- 长时间无进展；
- 移动止损；
- 分批减仓。

### 2.3 当前人工拥有最终退出权威

First Launch 阶段：

```text
SYSTEM_EXIT_OUTPUT = REFERENCE_ONLY
HUMAN_EXIT_DECISION = AUTHORITATIVE
```

系统可以给出参考止盈、移动止损和退出原因，但不自动执行，也不要求交易员服从。

---

## 3. 退出方式研究分类

### 3.1 Fixed-R checkpoint

用途：建立最简单、可比较的基线。

候选：

```text
1.0R
1.5R
2.0R
```

这些是研究检查点，不代表所有订单必须在该位置全部退出。

### 3.2 Structural target

目标由下一处价格结构决定：

- 下一支撑/阻力带；
- 下一高成交接受区；
- 区间中点或对侧边缘；
- 最近 swing high / swing low；
- 低接受区域之后的下一接受区。

系统至少输出：

```text
NEXT_STRUCTURAL_ZONE
DISTANCE_TO_ZONE
EXPECTED_R_TO_ZONE
```

### 3.3 Structure-trailing stop

随着有利方向产生新的结构，保护止损向盈利方向移动。

做多示例：

```text
形成新的 higher low
→ stop 提高到该结构下方
→ 后续只提高，不降低
```

做空完全镜像。

### 3.4 Break-even / profit-lock transition

当订单已经产生足够浮盈，并形成新的有利结构时，可以将止损移动到：

```text
BREAK_EVEN
OR
BREAK_EVEN_PLUS_COST
OR
SMALL_LOCKED_PROFIT
```

不能只因为价格短暂达到某个 R 就机械移动；需要同时记录：

- 有利结构是否形成；
- 当前波动率；
- 回踩正常噪音范围；
- 成本和滑点；
- 是否容易被普通回踩扫出。

### 3.5 Trend deterioration / reversal exit

退出证据候选：

- 原有更高高点/更高低点或更低高点/更低低点被破坏；
- 价格重新进入已突破价格带；
- 在下一关键区域出现明确拒绝；
- 方向效率显著下降；
- 趋势斜率持续变平；
- 进入新的稳定震荡；
- 相反方向 Sweep 或 Breakout 获得确认；
- 订单流和市场深度证据显著反向。

该类信号未来可输出：

```text
HOLD
TIGHTEN_STOP
PARTIAL_EXIT
FULL_EXIT
```

### 3.6 No-progress / time-aware exit

持仓时间不固定，但系统必须识别“长时间没有按预期发展”。

候选证据：

- 若干根 5m/15m K 线没有形成新的有利结构；
- MFE 长时间不再扩展；
- 价格持续围绕入场位或局部中点震荡；
- 方向效率下降；
- 交易时段状态发生变化；
- 信号最初的市场环境已经失效。

Time exit 不能只用固定分钟数，应该与 Setup、状态和进展共同研究。

### 3.7 Partial exit / scale-out

允许：

- 分批建仓；
- 1R 或结构位部分止盈；
- 剩余仓位由结构移动止损管理；
- 分批最终退出。

但部分止盈可能：

- 提高表面胜率；
- 降低回撤；
- 同时截断大趋势的右尾收益。

因此必须以完整 trade-level PnL、净 R、回撤和右尾贡献评估，不能只看胜率。

---

## 4. 当前 First Launch 最小要求

### 4.1 Signal / TradePlan

每个正式信号至少给出：

```text
ENTRY_ZONE
INITIAL_STRUCTURAL_STOP
PLANNED_RISK
REFERENCE_1R_PRICE
NEXT_STRUCTURAL_ZONE_IF_KNOWN
DO_NOT_CHASE
```

`REFERENCE_1R_PRICE` 是研究与人工参考，不强制作为固定 TP。

### 4.2 Shadow exit reference

对每个被记录的候选或正式 Signal，离线保存/计算：

```text
1R hit or not
1.5R hit or not
2R hit or not
next structural zone hit or not
MFE / MAE at 30m, 60m, 120m
maximum MFE before initial stop
time to 1R
return-to-entry after MFE
```

若能够低成本完成，可额外生成：

```text
REFERENCE_STRUCTURE_TRAIL_OUTCOME
REFERENCE_NO_PROGRESS_OUTCOME
```

这些不阻断当前发布。

### 4.3 人工实际退出记录

真实订单允许记录：

- 实际分批入场；
- 实际分批退出；
- 实际移动止损；
- 实际退出原因；
- 实际手续费、滑点和净 R。

交易过程中不增加复杂实时填写。实际成交可以在后续导入或匹配。

---

## 5. 未来 V0 产品能力

### 5.1 Position lifecycle

未来 V0 需要明确状态：

```text
ENTRY_PROPOSED
ENTRY_CONFIRMED
POSITION_OPEN
STOP_ADJUSTMENT_PROPOSED
PARTIAL_EXIT_PROPOSED
FULL_EXIT_PROPOSED
ACTION_CONFIRMED
ACTION_SUBMITTED
ACTION_FILLED
POSITION_CLOSED
```

### 5.2 操作卡

持仓后的系统提示至少包括：

- 当前持仓、方向、平均价格；
- 当前初始/有效止损；
- 当前浮盈 R；
- 下一关键价格带；
- 最新 5m/15m 结构；
- 建议动作；
- 建议动作原因；
- 建议数量；
- 预计手续费和滑点；
- `HUMAN CONFIRMATION REQUIRED`。

### 5.3 系统操作范围

未来 V0 可以在人工确认后提交：

```text
ENTRY
ADD
REDUCE_ONLY_PARTIAL_EXIT
FULL_CLOSE
STOP_CREATE
STOP_REPLACE_TIGHTER
TAKE_PROFIT_CREATE_OR_REPLACE
```

是否允许取消保护性止损、是否初始止损必须随建仓同时预置，需要在 V0 风险合同中单独裁决。

---

## 6. 研究顺序

### Stage A — Entry first

当前先研究：

- 价格带；
- Sweep / FAST / STANDARD / Range 入场；
- 初始结构止损；
- 入场后的 MFE/MAE 和标准化结果。

为了避免入场和退出相互混淆，第一轮使用统一的简单退出评价基线。

### Stage B — Exit replay

入场候选冻结后，在完全相同的 entry events 上比较：

1. 1R full exit；
2. structural target；
3. 1R partial + structure trail；
4. break-even/profit-lock + structure trail；
5. trend deterioration exit；
6. no-progress/time-aware exit。

### Stage C — Shadow exit advice

系统实时生成退出建议，但：

```text
NO_EXCHANGE_WRITE
HUMAN_ACTUAL_EXIT
```

比较：

- 系统退出建议；
- 人类实际退出；
- 固定 R 基线；
- 事后最佳可实现路径（仅用于诊断，不作为可交易结果）。

### Stage D — V0 human-confirmed execution

完成产品、风险、权限和执行合同后：

```text
SYSTEM_PROPOSES
→ HUMAN_CONFIRMS
→ SYSTEM_EXECUTES
```

### Stage E — Future automation

只有在 entry、exit、risk、execution 和 live shadow evidence 均通过后，才研究有限自动化。

---

## 7. 最低评估指标

每种退出方案至少报告：

```text
trade_count
win_rate
average_net_R
median_net_R
total_net_R
maximum_drawdown
longest_losing_streak
profit_factor
right_tail_contribution
MFE_capture_ratio
MAE
holding_time
fees_and_slippage
partial_exit_contribution
stop_out_after_profit_rate
exit_reason_distribution
```

同时按：

- Setup；
- FAST / STANDARD；
- Long / Short；
- 资产类别；
- 流动性；
- 波动率；
- orderly / displacement / reclaim state；
- session；

进行归因。

---

## 8. 外部研究采用结论

### 8.1 Dynamic/trailing exit

成熟的 optimal-stopping 研究表明，移动止损是路径依赖的动态退出问题，其合理设置依赖价格过程、波动、成本和持仓状态；不能假定存在跨市场通用的最佳 trailing distance。

采用：

```text
TRAILING_STOP = RESEARCH CANDIDATE
UNIVERSAL_TRAILING_PARAMETER = REJECT
```

### 8.2 Risk reduction versus return truncation

实证研究表明，移动止损可以降低总风险和下行风险，但可能牺牲平均收益；过紧规则在成本后尤其容易失效。

采用：

```text
TRAILING_EXIT_EVALUATION = EXPECTANCY + DOWNSIDE + RIGHT_TAIL
```

### 8.3 Structure-based exits

支撑阻力研究支持：多次反应和较新鲜的结构区域更可能产生短期反应。下一结构带适合作为参考退出/障碍，但不能保证反转。

采用：

```text
NEXT_ZONE = TARGET_OR_REVIEW_POINT
NOT GUARANTEED EXIT
```

### 8.4 Time-aware exits

近期 E-mini S&P 500 value-area breakout 样本中，浅回踩优于深回踩，且结合 trailing、break-even 和 no-progress timeout 的 time-aware exit stack 优于其固定价格止损基线。该结果为单市场、单时期独立研究，只作为候选设计依据，不直接复制参数。

采用：

```text
NO_PROGRESS_EXIT = REQUIRED RESEARCH CANDIDATE
PAPER_PARAMETERS = NOT PORTABLE
```

### 8.5 Partial exit

公开研究和初步实证对部分止盈没有统一结论。部分退出会改变收益分布，可能提高胜率和降低波动，也可能截断大赢家。

采用：

```text
PARTIAL_EXIT = EMPIRICAL CANDIDATE
NOT DEFAULT SUPERIOR
```

---

## 9. 当前范围控制

### Current release required

- 入场时结构止损；
- planned risk；
- 1R参考价格；
- 下一结构带（可得时）；
- 未来 Outcome 所需的基本证据；
- 人工最终退出。

### Current release only if near-zero cost

- 简单 reference exit outcome；
- 交易后自动 MFE/MAE；
- 实际分批成交后导入；
- 低成本退出原因记录。

### Post-First-Launch

- 完整退出策略回放；
- structure trailing；
- no-progress detection；
- trend termination/reversal classifier；
- 分批建仓和平仓研究；
- V0 持仓后提示；
- 人工确认后的 reduce-only/stop/close 执行；
- 退出策略样本外验证。

### Explicitly not current scope

- 自动止盈；
- 自动移动止损；
- 自动平仓；
- 完整 Position Management UI；
- 大规模退出参数网格；
- 机器学习退出策略；
- 取消当前入场研究以转做退出系统。

---

## 10. 最终冻结

```text
CURRENT_PRIORITY = ENTRY_QUALITY
INITIAL_STOP = REQUIRED_AT_ENTRY
PLANNED_MAX_LOSS = DETERMINED_AT_ENTRY
FIXED_TP = REFERENCE_NOT_MANDATORY
PROFIT_MANAGEMENT = PATH_DEPENDENT
HUMAN_EXIT_AUTHORITY = YES
CURRENT_EXIT_SIGNAL = REFERENCE_ONLY
SHADOW_EXIT_EVALUATION = REQUIRED_DIRECTION
PARTIAL_ENTRY = SUPPORTED_FUTURE
PARTIAL_EXIT = SUPPORTED_FUTURE
STOP_CAN_ONLY_TIGHTEN = REQUIRED PRINCIPLE
V0_POSITION_MONITORING = REQUIRED FUTURE CAPABILITY
V0_EXIT_PROPOSAL = REQUIRED FUTURE CAPABILITY
V0_HUMAN_CONFIRMATION = REQUIRED
V0_SYSTEM_EXECUTION_AFTER_CONFIRMATION = TARGET
FULL_AUTO_EXIT = DEFERRED
CURRENT_RELEASE_SCOPE_EXPANSION = PROHIBITED
```

---

## 11. Research references

- Leung and Zhang, *Optimal Trading with a Trailing Stop*.
- Dai, Marshall, Nguyen and Visaltanachoti, *Risk Reduction Using Trailing Stop-Loss Rules*.
- Chung and Bellotti, *Evidence and Behaviour of Support and Resistance Levels in Financial Time Series*.
- Osler, *Currency Orders and Exchange-Rate Dynamics*.
- Leung and Li, *Optimal Mean Reversion Trading with Transaction Costs and Stop-Loss Exit*.
- Howard, *Stop Distance, Exit Methodology, and Signal Preservation in Intraday Value Area Breakouts: Evidence from E-mini S&P 500 Futures* — preliminary independent evidence, non-authoritative parameters.
- Ma, Morita and Detko, *Re-Examining the Hidden Costs of the Stop-Loss*.
