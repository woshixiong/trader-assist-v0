# First Launch 当前总任务登记表与执行顺序 R2

**记录 ID：** `TA-FIRST-LAUNCH-CURRENT-MASTER-TASK-REGISTER-R2-2026-08-03`  
**日期：** `2026-08-03`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `PLANNING_ONLY / NON_EXECUTABLE / MASTER_BACKLOG_INDEX`  
**任务派发权威：** `PROJECT_CONTROL_ONLY`  
**当前文档入口：** `FIRST_LAUNCH_CURRENT_AUTHORITY_INDEX_AND_SUPERSESSION_MAP_R1_2026-08-03.md`  
**策略机器权威：** `FIRST_LAUNCH_CURRENT_RELEASE_MACHINE_EXECUTABLE_STRATEGY_PACKAGE_R1_2026-08-03.md`  
**架构权威：** `FIRST_LAUNCH_MULTI_ASSET_PARALLEL_REPLACEMENT_ARCHITECTURE_DECISION_R1_2026-08-03.md`  
**优先级：** 本文件只管理任务和顺序，不得覆盖上述策略、架构和权威索引。

---

## 1. 当前核心决策

取消：

```text
COMPLETE_THREE_ROUND_HISTORICAL_BACKTEST
AS_CURRENT_RELEASE_PREDEPLOYMENT_HARD_GATE
```

采用：

```text
STRATEGY RESEARCH OPTIMIZATION
→ MINIMUM CORRECTNESS VALIDATION
→ UNIFIED MULTI_ASSET SHADOW SIGNAL SYSTEM
→ SCANNER + COMPLETE EVIDENCE PIPELINE
→ CLOSE PREDEPLOYMENT OPERATIONS BLOCKERS
→ HUMAN_CONTROLLED DEPLOYMENT
→ SHADOW FORWARD VALIDATION
→ EVIDENCE_TRIGGERED LIMITED STRATEGY REVISION
→ RAPID REDEPLOYMENT
→ REPEAT AS JUSTIFIED
```

固定原则：

```text
RAPID_ITERATION = CORE_PROJECT_METHOD
SMALL_BATCH_CHANGE = REQUIRED
HUMAN_FINAL_DECISION = REQUIRED
AUTO_TRADE = NO
ALL_ELIGIBLE_MARKETS_CAN_RECEIVE_FULL_SIGNAL = YES
```

---

## 2. 当前发布关键路径

1. Strategy Optimization 完成当前机器策略包与权威清理；
2. Engineering Optimization 核验真实代码、复用点和最小实现路线；
3. Project Control 派发：
   - 新统一多资产 Shadow Signal System；
   - Scanner Stage A/B/C；
   - Candidate / Signal / Plan / ShadowOrder / T-S-R / Outcome / Export；
   - 最小正确性门禁；
   - reconnect-budget；
   - 主机外备份和恢复；
4. CI、独立 Review、回滚、部署和 Smoke；
5. 上线后根据实际 Scanner 和证据质量决定何时复核，不预设固定天数或样本数；
6. 只在证据支持时进行有限、版本化调整。

---

## 3. 新旧系统关系

```text
LEGACY_ETH_RUNTIME
= FROZEN FALLBACK / ROLLBACK / COMPARATOR

NEW_MULTI_ASSET_SYSTEM
= ETH + ALL ELIGIBLE HYPERLIQUID PERPS
= SAME FULL SIGNAL FIELDS
= NOT_SUBMITTED SHADOW AUTHORITY
= HUMAN FINAL DECISION
```

当前不对旧 ETH Runtime、TradePlan Hash 或 runtime.db 做侵入式多资产迁移。

---

## 4. 当前必须完成

- 新资产无关 MarketIdentity、ClosedBar、Strategy State、PlanDraft；
- 当前机器策略包的 Sweep、Breakout Micro FAST、state-driven STANDARD、Range Edge Rejection；
- Scanner R3 全市场发现与候选分层；
- 所有 WATCH/Candidate 自动留存；
- Scanner SETUP_READY 进入完整三 Setup evaluator；
- Formal Setup 生成完整 Shadow TradePlan / ShadowOrder；
- 所有资产输出 Entry、Chase、Stop、TP、1%/2% 参考金额；
- T/S/R；
- 30/60/120m Outcome；
- 一键导出和完整性报告；
- failure isolation；
- reconnect-budget；
- off-host backup and recovery；
- CI、Review、Rollback、Deploy、Smoke。

---

## 5. 当前不做

- 完整历史回测；
- 长期回测平台；
- Nautilus/Freqtrade/vectorbt/Backtrader 接入；
- 自动交易；
- 账户或签名接入；
- 多资产组合资金仲裁；
- 动态退出引擎；
- Discord Bot；
- 第四 Setup；
- OI/funding/L2 硬触发；
- 旧 ETH Schema 多资产迁移；
- 旧 ETH 下线。

---

## 6. 部署前阻断

```text
OPS-1 = FIRST_LAUNCH_RECONNECT_BUDGET_RESET
OPS-2 = TRADER_ASSIST_OFF_HOST_BACKUP_AND_LIGHTSAIL_SNAPSHOT_RETIREMENT
```

部署前必须完成修复、测试和恢复门禁。Lightsail 快照不得在恢复门禁通过前删除。

---

## 7. 上线后条件性 Backlog

`LONG_TERM_BACKTEST_ARCHITECTURE_REEVALUATION` 仅在以下条件出现时重新讨论：

- 前向样本过慢；
- 需要同时比较大量参数；
- 需要研究罕见历史行情；
- 准备自动交易或提高资金规模；
- 需要组合级风险验证；
- 每次修改等待真实样本的时间不可接受。

旧 ETH 运行时下线同样需要另行授权和完整门禁。

---

## 8. 权限边界

本文件不授权代码修改、工程派发、依赖安装、部署、重启、permit 修改、快照删除、账户访问、签名、交易所写入、自动下单、PR Mark Ready 或 Merge。