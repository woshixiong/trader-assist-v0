# First Launch 三 Setup 同日最小上线与信号证据计划

**记录 ID：** `TA-FIRST-LAUNCH-THREE-SETUP-SAME-DAY-MINIMUM-RELEASE-2026-07-31`  
**日期：** `2026-07-31`  
**仓库：** `woshixiong/trader-assist-v0`  
**生产基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**关联 Draft PR：** `#52`  
**状态：** `BINDING SCOPE CORRECTION / PLANNING ONLY / NON-EXECUTABLE`

## 1. 本轮唯一目标

在人工最终判断、人工下单的 First Launch 模式下，以最低投入完成三个 Setup 的基本可用版本：

- `SWEEP_RECLAIM`
- `BREAKOUT_RETEST`
- `RANGE_EDGE_REJECTION`

本轮目标不是证明策略长期盈利，也不是建设长期回测或交易基础设施，而是：

```text
最小策略实现
→ 最低必要历史筛查
→ 人工抽查
→ 复用现有信号和通知流程
→ 受限 First Launch 上线
```

## 2. 质量与时间目标

```text
STRATEGY_QUALITY_TARGET = 5_OF_10
BACKTEST_RIGOR_TARGET = 5_OF_10
TARGET_ELAPSED = SAME_DAY
NORMAL_EXPECTED = 6_TO_9_HOURS
HARD_MAXIMUM = 1_WORKING_DAY
```

若默认路线超过一个工作日，必须先删除非必要范围，不得通过扩展平台、框架或研究流程抬高工期。

## 3. 当前固定范围

### 3.1 Sweep / Breakout

- 不再做深度优化；
- 不改参数，除非发现明显实现错误；
- 只做基本回归，确保新增 Range 不破坏现有 FAST 行为；
- 不为本轮追求更好回测结果持续调参。

### 3.2 Range

第一版固定为：

```text
RANGE_EDGE_REJECTION_V0_1
RANGE_MODE = FAST_ONLY
```

最低能力：

1. 识别基本震荡区间；
2. 价格接近上沿或下沿；
3. 出现简单拒绝证据；
4. 生成 Long 或 Short；
5. 输出 Entry / Chase / Stop / TP；
6. 极端波动时不产生 actionable 信号。

本轮不做：

- Range STANDARD；
- Range → Breakout takeover；
- failed Breakout → Sweep；
- 复杂跨 Setup arbitration；
- 多候选评分系统；
- 大量 sensitivity；
- UI 重构。

### 3.3 STANDARD

当前生产 STANDARD progression 缺陷继续记录，但不进入本轮关键路径。

```text
STANDARD_PRODUCTION_FIX = DEFERRED
```

只有未来确定需要上线某个 STANDARD 单元时，才单独安排最小修复。

## 4. 最低必要回测

只使用：

- 一个 ETH perpetual 代理市场；
- 一个容易获得的历史区间；
- 1m / 5m / 15m；
- 一个现有或最薄的回放实现；
- 一个小修复轮次上限。

最低输出：

- signal count；
- win rate；
- average net R；
- total net R；
- rough maximum drawdown；
- longest losing streak；
- Setup 分组；
- Long / Short；
- fee、slippage 和保守人工延迟后的结果；
- 约 10–20 个 Range 信号人工抽查。

第一轮不做：

- 新回测框架接入；
- 第二数据源；
- 第二回测引擎；
- Hyperliquid 完整历史验证；
- 10,000 次 bootstrap；
- PBO / Deflated Sharpe；
- 完整消融；
- 完整 funding 管线；
- 长期研究平台。

最低准入：

```text
NO_OBVIOUS_LOOKAHEAD
NO_OBVIOUS_IMPLEMENTATION_ERROR
SIGNALS_NOT_EXTREMELY_SPARSE
NOT_CLEARLY_NEGATIVE_AFTER_BASIC_COSTS
DRAWDOWN_AND_LOSING_STREAK_NOT_OBVIOUSLY_UNCONTROLLED
MANUAL_SIGNAL_REVIEW_BASICALLY_MATCHES_TRADING_LOGIC
```

裁决仅为：

```text
ACCEPT_FOR_LIMITED_FIRST_LAUNCH
REVISE_ONCE
REJECT
```

## 5. 不可删除的底线

即使追求同日完成，也必须保留：

1. 只使用闭合 K 线，无未来数据；
2. Range Long / Short 的基本确定性测试；
3. 最低手续费、滑点和人工延迟；
4. 现有 Sweep / Breakout 回归；
5. 人工抽查一批真实信号；
6. 当前生产 SHA、配置和数据库一致性备份；
7. 部署后只读状态检查和非交易 smoke；
8. 人工最终判断、人工下单、无交易所写权限。

## 6. 同日工作包

```text
A. Strategy freeze and minimum Range implementation: 1.0–1.5h
B. Minimal historical screen and manual review: 2.0–3.0h
C. Existing-flow integration, focused tests and deployment: 3.0–4.0h
```

最大允许一次 30–60 分钟的小修复。不得进入第二轮持续优化。

## 7. ShadowOrder 与真实信号证据现状

仓库当前已经具备以下基础：

- `OperatorReviewCard`；
- `ShadowOrder`，固定 `submission_status = NOT_SUBMITTED`、`manual_execution_required = true`；
- `TAKEN / SKIPPED / REJECTED` 人工决策；
- append-only hash-chained decision journal；
- offline Outcome，可把决策包与人工实际成交及后续市场证据匹配。

但当前公共运行时明确不拥有 persistence；本记录未证明生产运行已经自动为每个新信号持久化 ShadowOrder、人工决策和完整后续结果。

因此状态冻结为：

```text
SHADOW_ORDER_DATA_MODEL = EXISTS
MANUAL_DECISION_JOURNAL = EXISTS
OFFLINE_OUTCOME_MATCHING = EXISTS
AUTOMATIC_LIVE_SHADOW_CAPTURE = NOT_PROVEN_ACTIVE
AUTOMATED_SHADOW_CANARY = DEFERRED_BACKLOG_ISSUE_62
```

ShadowOrder、影子评估或自动 canary 不进入本次三 Setup 同日上线范围。

## 8. 下一阶段的最小信号验证方向

在三 Setup 上线后，先评估是否只需复用现有日志和行情数据，而无需新增完整影子订单系统。

最小流程：

```text
signal / TradePlan persisted with immutable ID
→ operator marks TAKEN / SKIPPED / REJECTED
→ future closed candles retained
→ offline evaluator computes planned outcome, MFE/MAE and TP/stop path
→ TAKEN trades optionally import actual fills
→ compare system signal, human judgment and actual/planned outcome
```

产品窗口先冻结最小人工工作流和字段；工程窗口随后审查当前生产持久化缺口，只补最小缺失能力。不得默认开发完整 paper-trading、shadow-canary 或自动执行系统。

## 9. 简化人工验证规则

交易节奏下只要求一次快速输入：

```text
T = TAKEN
S = SKIPPED
R = REJECTED
```

可选增加一个单字符原因码，不要求交易过程中继续填写：

```text
1 = market context
2 = entry/chase timing
3 = structure conflict
4 = risk/reward
5 = signal logic appears wrong
```

交易结束或信号过期后，由离线记录自动完成结果匹配；不要求交易员实时填写复盘表。

## 10. 权威关系与边界

R1 / R1.1 / R1.2 继续作为完整策略语义参考，但不得被自动解释为本轮全部工程实施范围。本记录对当前 First Launch 执行范围和优先级具有更高的阶段性约束。

```text
CURRENT_FIRST_LAUNCH_EXECUTION_SCOPE = THIS_RECORD
LONG_TERM_FRAMEWORK_DISCUSSION = OUT_OF_SCOPE
PRODUCT_CODE_CHANGE = MINIMUM_RANGE_COMPATIBILITY_ONLY
DATABASE_MIGRATION = NO
NEW_PRODUCTION_SERVICE = NO
NEW_PRODUCTION_DEPENDENCY = NO
EXCHANGE_WRITE_AUTHORITY = NO
TASK_DISPATCH_AUTHORITY = PROJECT_CONTROL_ONLY
```

## 11. 下一次部署强制可靠性阻断项

当前生产已经确认存在 WebSocket 重连预算按进程生命周期错误累计的问题。服务已通过人工受控重启恢复，因此不安排当前生产服务器直改或单独 hotfix；但该缺陷必须在本次功能发布的最终生产部署前完成源码修复、事故回归测试、完整 CI、独立 Review 和合并。

权威任务记录：

```text
governance/FIRST_LAUNCH_RECONNECT_BUDGET_RESET_NEXT_DEPLOYMENT_BLOCKER_2026-08-02.md
```

固定身份：

```text
TASK_ID = FIRST_LAUNCH_RECONNECT_BUDGET_RESET
PRIORITY = P1_PRODUCTION_RELIABILITY
RELEASE_GATE = NEXT_DEPLOYMENT_BLOCKER
```

最小范围：

```text
1 个 runtime 源码文件
1 个主要测试文件
可选 1 个简短 runbook 更新
```

必须保持：

```text
连续恢复失败达到预算后仍 fail closed
成功完整恢复 READY 后重连计数归零
历史成功重连不消耗下一次独立事故的预算
```

最终 release candidate 必须包含：

```text
RECONNECT_BUDGET_RESET_TEST=PASS
CONSECUTIVE_FAILURE_BUDGET=PASS
SUCCESSFUL_READY_RESET=PASS
FULL_CI=PASS
```

该任务可与 Three Setup / Scanner 功能开发并行，但必须在最终 integration 和部署 Gate 前闭合。预计新增工作量为 2–4 person-hours，不得扩大为新的连接管理框架。

本文只固定计划，不授权代码修改、回测执行、依赖安装、部署、重启、permit 修改、Mark Ready、merge、账户访问、签名或下单。