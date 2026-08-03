# First Launch 当前权威索引与取代关系 R1

**记录 ID：** `TA-FIRST-LAUNCH-CURRENT-AUTHORITY-INDEX-R1-2026-08-03`  
**日期：** `2026-08-03`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `CURRENT AUTHORITY ENTRY / NON-EXECUTABLE / NON-AUTHORIZING`  
**用途：** 本文件是当前策略、Scanner、前向验证、工程顺序和运维阻断的唯一文档入口。旧文件继续保留审计价值，但不得通过旧结论覆盖本索引列出的当前权威。

---

## 1. 当前唯一权威顺序

发生冲突时，按以下顺序解释：

1. `FIRST_LAUNCH_CURRENT_RELEASE_MACHINE_EXECUTABLE_STRATEGY_PACKAGE_R1_2026-08-03.md`
   - 当前发布候选的机器执行语义、参数、状态、计划和拒绝原因最高权威。

2. `FIRST_LAUNCH_MULTI_ASSET_PARALLEL_REPLACEMENT_ARCHITECTURE_DECISION_R1_2026-08-03.md`
   - 当前多资产迁移、旧 ETH 保底、新系统边界和长期替代路线最高架构权威。

3. `FIRST_LAUNCH_INTRADAY_ENTRY_STRATEGY_PRE_BACKTEST_FREEZE_R5_2026-08-02.md`
   - 当前三 Setup 的策略机制、因果原则和研究父合同；其中仍为描述性或与第 1 项冲突的内容，以第 1 项为准。

4. `FIRST_LAUNCH_SESSION_MOMENTUM_BREAKOUT_SCANNER_LITE_R3_FINAL_PARAMETER_AND_DELIVERY_FREEZE_2026-08-01.md`
   - Scanner 的 Universe、Stage A/B、WATCH/SETUP_READY、流动性、排名和产品边界权威；Scanner 状态不得替代正式三 Setup 权威。

5. `STRATEGY_RESEARCH_DISCOVERY_AND_CONVERGENCE_PLAYBOOK_V5_2026-08-03.md`
   - 小批量、快速前向验证、证据驱动和防止无限开发循环的方法权威。

6. `FIRST_LAUNCH_SHADOW_FORWARD_VALIDATION_AND_RAPID_ITERATION_PLAN_R1_2026-08-03.md`
   - 上线前最小正确性门禁、上线后前向验证、T/S/R、Outcome、导出和多轮迭代流程权威。

7. `FIRST_LAUNCH_CURRENT_MASTER_TASK_REGISTER_AND_EXECUTION_ORDER_R2_2026-08-03.md`
   - 当前执行顺序和 Backlog 入口；不得改写上层策略或架构语义。

8. 部署前运维阻断文件：
   - `FIRST_LAUNCH_RECONNECT_BUDGET_RESET_NEXT_DEPLOYMENT_BLOCKER_2026-08-02.md`
   - `TRADER_ASSIST_OFF_HOST_BACKUP_AND_LIGHTSAIL_SNAPSHOT_RETIREMENT_NEXT_DEPLOYMENT_SCOPE_2026-08-02.md`

9. 三 Setup R1/R1.1/R1.2、旧最小上线记录、Pre-Backtest R2/R3/R4、Scanner R1/R2、旧产品与工程计划：
   - `HISTORICAL_REFERENCE_ONLY`；仅在上述当前权威没有覆盖且不冲突时提供背景。

---

## 2. 当前产品与发布方向

```text
STRATEGY RESEARCH OPTIMIZATION
→ MINIMUM CORRECTNESS VALIDATION
→ UNIFIED MULTI_ASSET SHADOW SIGNAL SYSTEM
→ SCANNER + COMPLETE EVIDENCE
→ PREDEPLOYMENT OPERATIONS BLOCKERS
→ HUMAN_CONTROLLED DEPLOYMENT
→ SHADOW FORWARD VALIDATION
→ EVIDENCE_TRIGGERED LIMITED REVISION
→ RAPID REDEPLOYMENT
```

固定：

```text
AUTO_TRADE = NO
EXCHANGE_WRITE_AUTHORITY = ABSENT
HUMAN_FINAL_DECISION = YES
ALL_ELIGIBLE_MARKETS_CAN_RECEIVE_FULL_SIGNAL = YES
ALL_FULLY_QUALIFIED_SETUPS_CAN_RECEIVE_SHADOW_PLAN = YES
```

---

## 3. 已明确失效的旧结论

以下结论不再是当前权威：

- 完整三轮历史回测是本次上线硬门禁；
- 长期回测平台在本次上线后自动立项；
- 固定 1～6 根 5m K 线是正式 STANDARD 的经济失效条件；
- 1h 方向预先过滤有效 Setup；
- Scanner WATCH 或 Scanner SETUP_READY 本身等于正式三 Setup Signal；
- 非 ETH 永远只停留在提示层，不能生成完整 Shadow TradePlan / ShadowOrder；
- 当前发布需要把旧 ETH 生产运行时整体侵入式改造成多资产运行时；
- Range 依据 1h 方向只交易单侧；
- 所有 WATCH 都应伪装成 ShadowOrder；
- 当前需要 NautilusTrader、Freqtrade、vectorbt、Backtrader 或新的通用事件平台。

---

## 4. 仍然有效但被重新定位的旧内容

- 当前生产 SHA `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` 和 `ETH-LDAR-v0.1`：保留为稳定保底、回滚目标和比较基线，不再作为新多资产策略核心。
- Range：当前仍只有 `RANGE_EDGE_REJECTION`，不新增 Range STANDARD；但价格带、双边交易、HTF 仅归因和事实失效采用当前机器包。
- Scanner `RETEST_WINDOW_BARS=1..12`：只属于 Scanner 候选路径；不得让正式 R5 STANDARD 因 Scanner 窗口结束而经济失效。
- 旧 Outcome、ShadowOrder、RuntimeStore、通知和哈希实现：可作为实现模式与保底路径；不得把 ETH Literal 和旧 Authority 约束复制为新多资产合同。
- 长期回测架构：状态为 `CONDITIONAL_FUTURE_REEVALUATION`，不是当前固定任务。

---

## 5. 新旧系统关系

```text
LEGACY_ETH_RUNTIME
= FROZEN FALLBACK + ROLLBACK + COMPARATOR

NEW_MULTI_ASSET_SYSTEM
= ETH + ALL ELIGIBLE MARKETS
= SAME STRATEGY SEMANTICS
= SAME FULL SIGNAL FIELDS
= NOT_SUBMITTED SHADOW AUTHORITY
= HUMAN FINAL DECISION
```

新系统稳定后，旧 ETH 运行时可以另行下线或归档；在获得明确切换授权前，两者并行但不得共享交易所写权限。

---

## 6. PR #52 的解释规则

PR #52 继续保持：

```text
OPEN
DRAFT
UNMERGED
DOCUMENTATION_ONLY
```

PR 正文或旧评论如与本索引冲突，以本索引和第 1 节列出的当前权威为准。后续窗口必须从本文件开始读取，不得按 PR 中旧时间顺序自行推断当前结论。

本文件不授权代码修改、依赖安装、服务启动、部署、重启、permit 修改、账户访问、签名、交易所写入、自动下单、Mark Ready 或 Merge。