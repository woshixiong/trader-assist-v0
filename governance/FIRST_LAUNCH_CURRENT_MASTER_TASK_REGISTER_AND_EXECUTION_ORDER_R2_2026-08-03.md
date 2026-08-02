# First Launch 当前总任务登记表与执行顺序 R2

**记录 ID：** `TA-FIRST-LAUNCH-CURRENT-MASTER-TASK-REGISTER-R2-2026-08-03`  
**日期：** `2026-08-03`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `PLANNING_ONLY / NON_EXECUTABLE / MASTER_BACKLOG_INDEX`  
**任务派发权威：** `PROJECT_CONTROL_ONLY`  
**优先级：** 本文件取代与其冲突的 `FIRST_LAUNCH_CURRENT_MASTER_TASK_REGISTER_AND_EXECUTION_ORDER_2026-08-03.md`；旧文件中不冲突的待办和部署前阻断继续有效。

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
→ SCANNER + EVIDENCE + SHADOW PIPELINE
→ CLOSE PREDEPLOYMENT OPERATIONS BLOCKERS
→ HUMAN-CONTROLLED DEPLOYMENT
→ SHADOW FORWARD VALIDATION
→ EVIDENCE-TRIGGERED LIMITED STRATEGY REVISION
→ RAPID REDEPLOYMENT
→ REPEAT AS JUSTIFIED
```

固定原则：

```text
RAPID_ITERATION = CORE_PROJECT_METHOD
SMALL_BATCH_CHANGE = REQUIRED
HUMAN_FINAL_DECISION = YES
MANUAL_EXECUTION = YES
AUTO_TRADE = NO
EXCHANGE_WRITE_AUTHORITY = ABSENT
COMPLETE_EVIDENCE = REQUIRED
ROLLBACK = REQUIRED
```

---

## 2. 当前上线前唯一主线

### P0 — 上线前策略研究冻结

由 Strategy Optimization 完成最多 1～2 轮研究优化，输出最合理的上线前研究候选。

状态要求：

```text
MACHINE_EXECUTABLE = YES
NO_OBVIOUS_INTERNAL_CONTRADICTION = YES
OBSERVED_FACTS_ONLY = YES
PROFITABILITY_PROVEN = NO_CLAIM
PARAMETERS_OPTIMAL = NO_CLAIM
```

### P1 — 最小正确性验证

只验证：

- 确定性 Fixture；
- closed-and-received-only；
- no-lookahead；
- 状态确认/失效/取代；
- slow STANDARD；
- dedup；
- re-entry；
- Entry/Stop/Target/ShadowOrder 一致；
- 小段近期数据 Smoke；
- 回滚能力。

不建设长期回测平台，不运行正式三轮历史回测。

权威：

- `STRATEGY_RESEARCH_DISCOVERY_AND_CONVERGENCE_PLAYBOOK_V5_2026-08-03.md`
- `FIRST_LAUNCH_SHADOW_FORWARD_VALIDATION_AND_RAPID_ITERATION_PLAN_R1_2026-08-03.md`

### P2 — Scanner Lite R3

保留：

```text
SCANNER_BIAS = HIGH_RECALL
UNIVERSE = ALL_ELIGIBLE_HYPERLIQUID_PERPS
WATCH_AND_SETUP_READY = REQUIRED
ALL_CANDIDATES_RETAINED = YES
TOP_N_LIMITS_NOTIFICATION_ONLY = YES
AUTO_TRADE = NO
AUTO_ASSET_SWITCH = NO
SCANNER_FAILURE_ISOLATION = REQUIRED
```

### P3 — 候选、影子、标注和 Outcome 闭环

上线前必须补齐：

- Scan/Candidate 稳定身份；
- WATCH、SETUP_READY、正式 Signal 和拒绝原因留存；
- Candidate/Signal/TradePlan 权威分离；
- T/S/R 快速人工标注；
- 30/60/120m 自动 MFE/MAE；
- Plan 级 TP/Stop/1R/1.5R/2R；
- 版本化批量导出；
- 数据完整性报告；
- Candidate→Signal→Plan→Annotation→Outcome 关联。

不建设：

- Dashboard；
- 完整 paper trading；
- 自动撮合；
- 账户模拟；
- 通用 Trial 平台；
- 实时动态退出系统。

### P4 — 部署前可靠性和灾难恢复阻断

下一次生产部署前仍必须完成：

```text
OPS-1 = FIRST_LAUNCH_RECONNECT_BUDGET_RESET
OPS-2 = TRADER_ASSIST_OFF_HOST_BACKUP_AND_LIGHTSAIL_SNAPSHOT_RETIREMENT
```

Lightsail 快照在恢复门禁和单独授权前不得删除。

### P5 — 最终集成、Review、部署和 Smoke

要求：

- exact release SHA；
- full CI；
- 独立 Review；
- deployment backup；
- rollback target；
- Scanner 故障隔离；
- no exchange write authority；
- ShadowOrder 仍为 NOT_SUBMITTED；
- 部署后健康和通知 Smoke；
- 生产旧版本可恢复。

---

## 3. 上线后前向验证

上线后不预设固定优化日期、候选数量或第二轮具体方案。

流程：

```text
RUN
→ USER REPORTS ACTUAL SCANNER THROUGHPUT AND DATA QUALITY
→ EXPORT VERSIONED EVIDENCE PACKAGE
→ STRATEGY OPTIMIZATION REVIEW
→ CONTINUE_COLLECTING | LIMITED_CHANGE | ROLLBACK
```

必须分析：

- 所有被保留候选，不只 TAKEN；
- T/S/R 和可选原因；
- 自动 Outcome；
- WATCH→SETUP_READY；
- Scanner Candidate→Formal Signal；
- Setup、方向、HTF、波动率、流动性和资产类别分层；
- 不同策略/参数/Release 版本严格分离。

---

## 4. 上线后每轮快速迭代

每轮根据问题类型分级：

### 参数/阈值修改

```text
EXPECTED_TOTAL = 4.5～12.5 person-hours
EXPECTED_ELAPSED = approximately 0.5～1.5 workdays
```

### 局部机器语义修改

```text
EXPECTED_TOTAL = 8～21 person-hours
EXPECTED_ELAPSED = approximately 1～3 workdays
```

### 架构或数据链缺陷

必须单独工程立项，不得混入普通策略迭代估算。

完成首版数据闭环以后，不应每轮重复开发导出、标注、Outcome 或基础部署流程。

---

## 5. 长期回测架构

保留为本轮成功部署后的高优先级专项，但当前不继续讨论或实施。

```text
TASK = LONG_TERM_REUSABLE_BACKTEST_ARCHITECTURE
STATUS = DEFERRED_UNTIL_CURRENT_RELEASE_DEPLOYED
```

当前研究方向保留：

```text
MATURE_ENGINE
+ ENGINE_AGNOSTIC_STRATEGY_KERNEL
+ THIN_ADAPTERS
+ PROJECT_SPECIFIC_EVIDENCE
+ MINIMAL_DETERMINISTIC_ORACLE
```

部署后重新评估：

- NautilusTrader compatibility Spike；
- 数据目录和 Manifest；
- Strategy Kernel；
- Backtest/Shadow/Live Adapter；
- 复用当前前向证据作为 Golden Fixtures；
- 长期开发时间和维护成本。

该专项不得重新进入当前上线关键路径。

---

## 6. 仍然保留的后续任务

以下任务没有取消：

- Three Setup 根据前向证据继续版本化优化；
- Scanner Lite R3 后续参数优化；
- Point-in-time Universe 和全候选证据；
- T/S/R、Outcome、No-Signal 证明；
- ShadowOrder 与实际人工成交匹配；
- 长期回测架构；
- 半自动执行研究；
- 动态持仓和退出研究；
- 多标的正式 Setup 运行；
- 运维、备份、恢复和成本优化。

所有任务必须按 Project Control 的单一路径派发。

---

## 7. 当前禁止事项

当前治理记录不授权：

- 代码修改；
- 分支创建；
- 依赖安装；
- Scanner 实施；
- 部署；
- 服务重启；
- permit 修改；
- 账户访问；
- 私钥或签名；
- 交易所写入；
- 自动下单；
- Mark Ready；
- merge。

---

## 8. 当前最终执行顺序

```text
1. Strategy Optimization freezes predeployment candidate
2. Engineering Optimization produces minimum-release route
3. Product Optimization confirms T/S/R and evidence UX only where needed
4. Project Control dispatches implementation
5. Minimum correctness validation passes
6. Scanner and evidence pipeline pass
7. Reconnect and backup/DR blockers pass
8. Full CI and independent review pass
9. Controlled deployment and smoke
10. Shadow forward validation begins
11. User reports actual throughput and qualitative feedback
12. Versioned export and Strategy Optimization review
13. Continue, limited revision, or rollback
14. Long-term reusable backtest architecture discussion reopens after deployment
```
