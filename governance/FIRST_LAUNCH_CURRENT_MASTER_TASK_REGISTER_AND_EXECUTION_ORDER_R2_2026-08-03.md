# First Launch 当前总任务登记表与执行顺序 R2

**记录 ID：** `TA-FIRST-LAUNCH-CURRENT-MASTER-TASK-REGISTER-R2-2026-08-03`  
**日期：** `2026-08-03`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `PLANNING_ONLY / NON_EXECUTABLE / MASTER_BACKLOG_INDEX`  
**任务派发权威：** `PROJECT_CONTROL_ONLY`  
**当前文档入口：** `FIRST_LAUNCH_CURRENT_AUTHORITY_INDEX_AND_SUPERSESSION_MAP_R1_2026-08-03.md`  
**策略精度最高权威：** `FIRST_LAUNCH_CURRENT_RELEASE_MACHINE_EXECUTABLE_STRATEGY_PACKAGE_R1_1_FINAL_PRECISION_CLOSURE_2026-08-03.md`  
**策略主体权威：** `FIRST_LAUNCH_CURRENT_RELEASE_MACHINE_EXECUTABLE_STRATEGY_PACKAGE_R1_2026-08-03.md`  
**Universe/容量权威：** `FIRST_LAUNCH_UNIVERSE_REFRESH_AND_EXPANDING_CAPACITY_SPIKE_DECISION_R1_2026-08-03.md`  
**架构权威：** `FIRST_LAUNCH_MULTI_ASSET_PARALLEL_REPLACEMENT_ARCHITECTURE_DECISION_R1_2026-08-03.md`  
**优先级：** 本文件只管理任务和顺序，不得覆盖上述策略、Universe、架构和权威索引。

---

## 1. 当前核心决策

取消：

```text
COMPLETE_THREE_ROUND_HISTORICAL_BACKTEST
AS_CURRENT_RELEASE_PREDEPLOYMENT_HARD_GATE
```

采用：

```text
STRATEGY MACHINE SEMANTICS FREEZE
→ READ-ONLY UNIVERSE + CAPACITY SPIKE
→ EXACT UNIVERSE ELIGIBILITY FREEZE
→ ENGINEERING FINAL ROUTE
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
FUTURE_AUTOMATED_TRADING_GRADE_MARKET_ELIGIBILITY = REQUIRED
ALL_APPROVED_MARKETS_CAN_RECEIVE_FULL_SIGNAL = YES
```

---

## 2. 当前第一阻塞任务：Universe 与容量实测

当前不得继续冻结或估算：

```text
FINAL_APPROVED_UNIVERSE_COUNT
FINAL_VOLUME/OI/DEPTH/SPREAD/REGULARITY_THRESHOLDS
MAX_ACTIVE_FORMAL_EVENTS
```

必须先完成：

```text
GLOBAL MARKET SNAPSHOT
→ ORDERED CAPACITY CANDIDATE POOL
→ 8/16/32/64/128/... EXPANDING TEST
→ FIRST FAILURE
→ BOUNDARY CONVERGENCE
→ QUALITY DISTRIBUTION
→ SAFE CAPACITY
```

固定 Top-100 测试法和预设 30/50/100 Universe 均已取消。

容量实测必须：

- 在目标 AWS 或严格等价环境；
- 与生产服务隔离；
- 只使用公共只读数据；
- 不安装依赖；
- 不修改生产代码、数据库、服务或 permit；
- 区分 Global Snapshot、Cold Bootstrap、Steady State、Candidate/Event/Outcome/Recovery Stress；
- 输出真实 API、WebSocket、CPU、内存、延迟和数据库结果。

只有完成该实测，Strategy Optimization 才冻结 `MULTI_ASSET_UNIVERSE_ELIGIBILITY_R1`，Engineering Optimization 才重新形成最终工程工作包和工期。

---

## 3. 当前发布关键路径

1. Strategy Optimization 已完成机器策略包和文档权威清理；
2. Engineering Optimization 执行或安排只读 Universe/Capacity Spike；
3. Strategy Optimization 根据真实质量分布与安全容量冻结精确 Universe Eligibility；
4. Engineering Optimization 核验真实代码、复用点和最小实现路线；
5. Project Control 派发：
   - 新统一多资产 Shadow Signal System；
   - 周期性 versioned Universe Refresh；
   - Scanner Stage A/B/C；
   - Candidate / Signal / Plan / ShadowOrder / T-S-R / Outcome / Export；
   - 最小正确性门禁；
   - reconnect-budget；
   - 主机外备份和恢复；
6. CI、独立 Review、回滚、部署和 Smoke；
7. 上线后根据实际 Scanner 和证据质量决定何时复核，不预设固定天数或样本数；
8. 只在证据支持时进行有限、版本化调整。

---

## 4. 新旧系统关系

```text
LEGACY_ETH_RUNTIME
= FROZEN FALLBACK / ROLLBACK / COMPARATOR

NEW_MULTI_ASSET_SYSTEM
= ETH + ALL APPROVED HYPERLIQUID PERPS
= SAME FULL SIGNAL FIELDS
= NOT_SUBMITTED SHADOW AUTHORITY
= HUMAN FINAL DECISION
```

当前不对旧 ETH Runtime、TradePlan Hash 或 runtime.db 做侵入式多资产迁移。

通知采用：

```text
PARALLEL_INSTALLED
SINGLE_ACTIVE_NOTIFICATION_AUTHORITY
```

正式切换后，新系统是唯一活动通知来源，旧 ETH 服务停止/禁用并保留回滚材料。

---

## 5. Universe Refresh 固定要求

Universe 不得硬编码在源码中。

目标流程：

```text
AUTO REFRESH
→ VALIDATE
→ DIFF
→ VERSIONED CANDIDATE
→ ATOMIC APPLY
→ HOT RELOAD ON NEXT CLOSED 5M
```

不得要求修改代码、Git commit、完整 CI、重新部署或重启整个系统。

前两次：

```text
AUTO_REFRESH = YES
AUTO_APPLY = NO
USER_REVIEW_TARGET = 5–10 MINUTES
```

稳定并授权后可自动 Apply；异常时保留上一有效版本。

初始周期候选为 7 天，但须依据至少四次 Turnover 数据再决定维持 7 天或调整至 14 天。该周期目前不是永久参数。

---

## 6. 当前必须完成

容量实测完成后，本轮必须实施：

- 新资产无关 MarketIdentity、ClosedBar、Strategy State、PlanDraft；
- 当前机器策略包的 Sweep、Breakout Micro FAST、state-driven STANDARD、Range Edge Rejection；
- versioned Universe Refresh 和原子切换；
- Scanner 只处理 Approved Universe；
- 所有 Approved WATCH/Candidate 自动留存；
- Scanner SETUP_READY 进入完整三 Setup evaluator；
- Formal Setup 生成完整 Shadow TradePlan / ShadowOrder；
- 所有 Approved Market 输出 Entry、Chase、Stop、TP、1%/2% 参考金额；
- T/S/R；
- 30/60/120m Outcome；
- 一键导出和完整性报告；
- failure isolation；
- reconnect-budget；
- off-host backup and recovery；
- CI、Review、Rollback、Deploy、Smoke。

---

## 7. 当前不做

- 完整历史回测；
- 长期回测平台；
- Nautilus/Freqtrade/vectorbt/Backtrader 接入；
- 自动交易；
- 账户或签名接入；
- 多资产组合资金仲裁；
- 动态退出引擎；
- Discord Bot；
- 第四 Setup；
- OI/funding 作为 Setup 硬触发；
- 旧 ETH Schema 多资产迁移；
- 旧 ETH 下线；
- 日常持续触碰全交易所所有市场；
- 固定 Top-100 或固定 30/50 Universe；
- 未经实测的 Active Event 上限。

---

## 8. 部署前阻断

```text
OPS-1 = FIRST_LAUNCH_RECONNECT_BUDGET_RESET
OPS-2 = TRADER_ASSIST_OFF_HOST_BACKUP_AND_LIGHTSAIL_SNAPSHOT_RETIREMENT
```

部署前必须完成修复、测试和恢复门禁。Lightsail 快照不得在恢复门禁通过前删除。

---

## 9. 上线后条件性 Backlog

`LONG_TERM_BACKTEST_ARCHITECTURE_REEVALUATION` 仅在以下条件出现时重新讨论：

- 前向样本过慢；
- 需要同时比较大量参数；
- 需要研究罕见历史行情；
- 准备自动交易或提高资金规模；
- 需要组合级风险验证；
- 每次修改等待真实样本的时间不可接受。

旧 ETH 运行时下线同样需要另行授权和完整门禁。

周期性 Universe Refresh、Universe Turnover、自动 Apply 安全性和质量变化本身属于上线后的持续验证对象。

---

## 10. 权限边界

本文件不授权代码修改、工程派发、依赖安装、部署、重启、permit 修改、快照删除、账户访问、签名、交易所写入、自动下单、PR Mark Ready 或 Merge。
