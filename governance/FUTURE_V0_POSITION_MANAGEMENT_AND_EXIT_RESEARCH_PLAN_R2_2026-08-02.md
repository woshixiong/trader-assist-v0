# Future V0 Position Management and Exit Research Plan R2

**记录 ID：** `TA-FUTURE-V0-POSITION-MANAGEMENT-EXIT-RESEARCH-R2-2026-08-02`  
**日期：** `2026-08-02`  
**状态：** `FUTURE RESEARCH / PRODUCT PLANNING / NON-EXECUTABLE / NON-DEPLOYMENT`  
**关联：** PR #52、First Launch 三 Setup、Scanner Lite R3、Strategy Research and Backtest Operating Standard V1、R1 Position Management Plan  
**优先级：** 与 R1 冲突时，以本文件 R2 为准。  
**权限边界：** 本文不授权实现、回测执行、部署、账户访问、交易所写入、自动下单、自动止盈或自动止损。

---

## 1. 最终目标

本项目的退出原则固定为：

```text
PROTECT_OPEN_PROFIT
+ STAY_WITH_VALID_TREND
+ EXIT_DECISIVELY_ON_CONFIRMED_END_OR_REVERSAL
+ REENTER_ONLY_ON_A_NEW_VALID_ENTRY_SIGNAL
```

固定 R 目标仅作为研究基线和参考检查点，不作为所有订单的强制退出逻辑。

一段大趋势可以拆成多个独立交易段：

```text
TREND_LEG_A
→ EXIT_OR_PROTECT_WHEN_PULLBACK/REVERSAL_BEGINS
→ FLAT_AND_OBSERVE
→ NEW_VALID_ENTRY_SIGNAL
→ TREND_LEG_B
```

不得把“上一笔订单继续持有”和“下一段趋势重新建仓”混为同一交易生命周期。

---

## 2. 当前 First Launch 范围

本轮策略优化继续以入场为核心：

- 关键价格带；
- Sweep / FAST / STANDARD / Range 入场；
- 初始结构止损；
- 入场时最大计划亏损；
- 候选、Signal、TradePlan、T/S/R 和 Outcome 证据。

当前不建设实时动态退出引擎。

但每个正式 Signal / TradePlan 必须尽量提供完整参考信息：

```text
ENTRY_ZONE
INITIAL_STRUCTURAL_STOP
PLANNED_RISK
REFERENCE_1R_PRICE
REFERENCE_1_5R_PRICE
REFERENCE_2R_PRICE
NEXT_STRUCTURAL_ZONE_IF_KNOWN
REFERENCE_EXIT_MODE
DO_NOT_CHASE
```

其中：

- Entry 与 Initial Stop 属于正式交易方案；
- Reference R 与 Structural Zone 属于退出参考；
- First Launch 中人工仍拥有最终止盈和止损调整权威；
- 系统参考止盈不自动执行，也不要求人工服从。

---

## 3. 当前影子退出评估

所有被记录的 Scanner Candidate、正式 Signal 或 TradePlan，应尽可能离线计算：

```text
1R_hit
1_5R_hit
2R_hit
next_structural_zone_hit
MFE_30m_60m_120m
MAE_30m_60m_120m
maximum_MFE_before_initial_stop
time_to_1R
return_to_entry_after_MFE
maximum_profit_given_back
```

本轮优先保存价格路径和可复现事实，而不是实时运行复杂退出策略。

若现有数据和 evaluator 可低成本复用，可额外计算少量研究参考：

```text
REFERENCE_BREAK_EVEN_OUTCOME
REFERENCE_STRUCTURE_TRAIL_OUTCOME
REFERENCE_NO_PROGRESS_OUTCOME
REFERENCE_REVERSAL_EXIT_OUTCOME
```

这些额外参考不得因为实现复杂而阻塞当前发布。

---

## 4. 退出状态研究模型

未来系统不只输出固定 TP，而应输出以下持仓建议状态：

```text
HOLD
TIGHTEN_STOP
MOVE_TO_BREAK_EVEN_OR_PROFIT_LOCK
PARTIAL_EXIT
FULL_EXIT
```

### 4.1 HOLD

趋势结构仍然有效，价格行为仍支持原方向，且没有明显趋势衰减或反向确认。

### 4.2 TIGHTEN_STOP

出现新的有利结构，可以将止损向盈利方向移动，例如：

- 做多形成新的 higher low；
- 做空形成新的 lower high；
- 突破后的新支撑/阻力转换得到确认；
- 价格已脱离原风险区域。

止损在持仓后只能保持或收紧，不得向扩大亏损方向移动。

### 4.3 MOVE_TO_BREAK_EVEN_OR_PROFIT_LOCK

不能只因为价格短暂达到某个固定 R 就机械移动止损。建议条件至少结合：

- 已形成新的有利结构；
- 当前浮盈能够覆盖手续费和滑点；
- 新止损不会落在正常回踩噪音内部；
- 原 Setup 仍然有效。

可选位置：

```text
BREAK_EVEN
BREAK_EVEN_PLUS_COST
SMALL_LOCKED_PROFIT
NEW_STRUCTURE_PROTECTIVE_LEVEL
```

### 4.4 PARTIAL_EXIT

适用于：

- 到达下一关键价格带；
- 趋势仍有效，但前方阻力明显；
- 波动率或方向效率开始衰减；
- 需要保护一部分浮盈，同时保留右尾趋势收益。

### 4.5 FULL_EXIT

退出候选证据：

- 原有趋势高低点结构被破坏；
- 价格重新进入已突破价格带；
- 下一关键区域出现明确反向拒绝；
- 方向效率持续下降；
- 趋势斜率显著变平并进入稳定震荡；
- 相反方向 Sweep / Breakout 得到确认；
- 长时间无进展且原市场状态已失效。

---

## 5. 大趋势分段交易

系统应允许并研究：

```text
POSITION_A_OPEN
→ EXIT_A_ON_PULLBACK_OR_REVERSAL_EVIDENCE
→ NO_POSITION
→ WAIT_FOR_NEW_SETUP
→ POSITION_B_OPEN
```

核心原则：

- 不因为担心错过未来趋势而忽略当前反转/回调证据；
- 退出后若原方向恢复，必须由新的有效入场 Setup 重新授权；
- 新入场拥有新的 Entry、Stop、Risk、TradePlan 与 Outcome；
- 不允许把重新入场伪装成旧仓位的延续或无审计加仓。

未来统计应比较：

- 一直持有整个趋势；
- 分段退出和重新进入；
- 分批止盈并保留剩余仓位；
- 实际净 R、回撤、成本和右尾收益。

---

## 6. V0 人工确认执行模型

### 6.1 第一次确认：建仓与保护性止损

```text
ENTRY_PROPOSAL
+ INITIAL_STOP_PROPOSAL
+ POSITION_SIZE
+ MAX_PLANNED_RISK
→ ONE HUMAN CONFIRMATION
→ SYSTEM SUBMITS ENTRY
→ SYSTEM SUBMITS/VERIFIES PROTECTIVE STOP
```

建仓与初始止损必须作为同一个确认包。不得出现已建仓但保护性止损长期缺失的状态。

### 6.2 第二次及后续确认：持仓管理

系统持续监控并提出：

```text
STOP_ADJUSTMENT_PROPOSAL
PARTIAL_EXIT_PROPOSAL
FULL_EXIT_PROPOSAL
```

人工确认后，系统才提交 reduce-only、close 或 stop modification。

### 6.3 系统状态建议

```text
ENTRY_PROPOSED
ENTRY_CONFIRMED
ENTRY_SUBMITTED
POSITION_OPEN
PROTECTIVE_STOP_ACTIVE
STOP_ADJUSTMENT_PROPOSED
PARTIAL_EXIT_PROPOSED
FULL_EXIT_PROPOSED
ACTION_CONFIRMED
ACTION_SUBMITTED
ACTION_FILLED
POSITION_CLOSED
```

所有建议、人工决定、订单请求、交易所响应和最终成交必须可审计。

---

## 7. 人工在 Hyperliquid 界面修改订单的权利

V0 必须保留用户直接在 Hyperliquid 官方界面进行人工修改的能力，包括：

- 修改或取消系统提交的止损；
- 修改或取消系统提交的止盈或 reduce-only 订单；
- 手工部分平仓；
- 手工全部平仓；
- 手工调整仓位。

系统不得锁定账户或阻止人工操作。

但人工修改会造成系统本地计划与交易所真实状态发生差异，因此 V0 必须具备：

```text
EXCHANGE_IS_FINAL_POSITION_TRUTH
MANUAL_OVERRIDE_DETECTION
ORDER_AND_POSITION_RECONCILIATION
LOCAL_PLAN_MARKED_SUPERSEDED_OR_MODIFIED
NO_DUPLICATE_EXIT_ORDER
NO_STOP_WIDENING_WITHOUT_NEW_CONFIRMATION
```

检测到外部人工修改后，系统至少应：

1. 重新读取真实仓位和开放订单；
2. 标记原 TradePlan / PositionPlan 已被人工覆盖；
3. 取消或修正可能重复、过量或方向错误的退出建议；
4. 在重新确认前，不自动恢复旧订单；
5. 保存 override 时间、前后状态和用户动作证据。

未来全自动交易阶段是否限制人工修改，必须另行决策；V0 阶段默认保留人工最高控制权。

---

## 8. 研究与回测顺序

### 阶段 A：当前入场研究

统一简单退出基线，优先完成：

- Zone；
- Sweep；
- FAST；
- STANDARD；
- Range；
- 初始结构止损。

### 阶段 B：冻结入场后研究退出

在完全相同的入场事件上比较：

1. 1R 全部退出；
2. 下一结构带退出；
3. 1R 或结构位部分退出，剩余仓位结构跟踪；
4. Break-even / profit-lock 后结构跟踪；
5. 趋势衰减/反转退出；
6. No-progress / time-aware exit；
7. 分段退出和重新入场。

### 阶段 C：First Launch 影子退出建议

系统实时或离线生成退出参考，但不执行。比较：

- 系统建议；
- 人工实际退出；
- 固定 R；
- 结构退出；
- 动态退出；
- 一直持有；
- 分段交易。

### 阶段 D：V0 人工确认执行

系统建议，人工确认，系统提交并对账。

### 阶段 E：自动交易前资格

只有在退出建议、人工 override、订单对账、重复订单保护、异常恢复和长期实盘证据全部通过后，才讨论自动持仓管理。

---

## 9. 当前范围与开发工作量控制

### 9.1 当前发布必要

```text
ENTRY_ZONE
INITIAL_STRUCTURAL_STOP
PLANNED_RISK
REFERENCE_R_LEVELS
NEXT_STRUCTURAL_ZONE_IF_AVAILABLE
BASIC_SHADOW_EXIT_PATH_METRICS
```

### 9.2 当前发布仅在低成本时加入

```text
REFERENCE_BREAK_EVEN_OUTCOME
REFERENCE_STRUCTURE_TRAIL_OUTCOME
REFERENCE_NO_PROGRESS_OUTCOME
REFERENCE_REVERSAL_EXIT_OUTCOME
```

### 9.3 明确延期到 V0

```text
REAL_TIME_POSITION_MONITOR
LIVE_STOP_ADJUSTMENT_SIGNAL
LIVE_PARTIAL_EXIT_SIGNAL
LIVE_FULL_EXIT_SIGNAL
HUMAN_CONFIRMED_EXCHANGE_WRITE
ORDER_RECONCILIATION
MANUAL_OVERRIDE_DETECTION
```

因此，本轮若不建设实时动态退出引擎，可以有效控制开发时间。止盈研究应限于参考字段、路径数据和少量离线 comparator；完整实时持仓管理属于独立 V0 工作包。

工程时间必须在 exact scope 核对后估算，不预设固定小时。

---

## 10. 研究纪律

退出策略不能仅按胜率选择。最低比较：

```text
average_net_R
total_net_R
maximum_drawdown
profit_factor
MFE_capture_ratio
maximum_profit_given_back
right_tail_contribution
cost_and_slippage
average_holding_time
manual_override_rate
reentry_frequency
```

固定 R、结构退出、移动止损、部分退出和趋势反转退出都必须在相同入场、数据、成本和延迟模型上比较。

外部研究只提供机制、候选和反例，不直接授予生产参数。

---

## 11. 最终冻结

```text
CURRENT_RELEASE_PRIORITY = ENTRY_FIRST
INITIAL_STOP_WITH_ENTRY_CONFIRMATION = REQUIRED
CURRENT_EXIT_AUTHORITY = HUMAN
CURRENT_EXIT_OUTPUT = REFERENCE_AND_SHADOW_EVIDENCE
FIXED_R = RESEARCH_BASELINE_NOT_MANDATORY_EXIT
PROFIT_PROTECTION = REQUIRED_RESEARCH_PRINCIPLE
STAY_WITH_VALID_TREND = REQUIRED_RESEARCH_PRINCIPLE
CONFIRMED_TREND_END_OR_REVERSAL = EXIT_CANDIDATE
SEGMENTED_TREND_TRADING = SUPPORTED_RESEARCH_MODEL
V0_ENTRY_AND_STOP = ONE_CONFIRMATION_PACKAGE
V0_EXIT_AND_STOP_ADJUSTMENT = HUMAN_CONFIRM_THEN_SYSTEM_EXECUTES
V0_MANUAL_HYPERLIQUID_OVERRIDE = MUST_REMAIN_AVAILABLE
EXCHANGE_POSITION_AND_ORDER_STATE = FINAL_RUNTIME_TRUTH
FULL_DYNAMIC_EXIT_ENGINE = DEFERRED_TO_V0
AUTO_POSITION_MANAGEMENT = NOT_AUTHORIZED
```
