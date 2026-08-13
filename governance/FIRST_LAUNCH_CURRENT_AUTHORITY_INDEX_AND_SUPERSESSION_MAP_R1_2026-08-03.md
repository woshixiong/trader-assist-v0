# First Launch 当前权威索引与取代关系 R1

**记录 ID：** `TA-FIRST-LAUNCH-CURRENT-AUTHORITY-INDEX-R1-2026-08-03`  
**更新日期：** `2026-08-13`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `CURRENT AUTHORITY ENTRY / NON-EXECUTABLE / NON-AUTHORIZING`

---

## 1. 当前唯一权威顺序

发生冲突时按以下顺序解释：

1. `FIRST_LAUNCH_CURRENT_RELEASE_MACHINE_EXECUTABLE_STRATEGY_PACKAGE_R1_1_FINAL_PRECISION_CLOSURE_2026-08-03.md`
   - 当前发布候选机器策略精度闭环。

2. `FIRST_LAUNCH_CURRENT_RELEASE_MACHINE_EXECUTABLE_STRATEGY_PACKAGE_R1_2026-08-03.md`
   - 当前三 Setup 主体机器合同；冲突时服从 R1.1。

3. `FIRST_LAUNCH_MANUAL_40_MARKET_REGISTRY_FAST_ROUTE_AND_TIMEFRAME_PROFILE_BACKLOG_R1_2026-08-12.md`
   - 当前 Universe/API/时间周期/1m/手续费最小边界和 Post-Launch V0.2 Timeframe Profile Backlog 的最高路线权威。固定 40 市场人工热插拔 Registry 已取代本发布中的自动全市场发现与扩张容量路线。

4. `FIRST_LAUNCH_CORRELATED_SIGNAL_CLUSTERING_BACKTEST_AND_EXECUTION_EXPOSURE_GOVERNANCE_R1_2026-08-04.md`
   - 高相关信号归组、研究独立样本解释、回撤和未来真实暴露治理最高权威。

5. `FIRST_LAUNCH_POST_LAUNCH_STRATEGY_RESEARCH_AND_SHADOW_EVIDENCE_BACKLOG_R1_2026-08-12.md`
   - 当前上线后 Strategy Research / Shadow Evidence 的父级 Backlog 权威。其 Evidence、可重建性和“不扩大当前发布”边界继续有效。
   - 当前研究/未来开发排序由 `FIRST_LAUNCH_POST_LAUNCH_STRATEGY_RESEARCH_AND_DEVELOPMENT_PRIORITY_ROADMAP_R2_2026-08-13.md` 进一步收敛；该 R2 只更新 Post-Launch Research/Development Priority，不修改当前 Machine Strategy R1/R1.1。
   - `R4 = SCHEDULED MACRO EVENT + EVENT ASSET ROUTER` 的当前子研究合同为：`FIRST_LAUNCH_SCHEDULED_US_MACRO_EVENT_STRATEGY_RESEARCH_AND_FUTURE_AUTOMATION_BACKLOG_R1_2026-08-12.md`。该子合同初始聚焦 CPI / NFP / PCE，可并行历史/离线研究，但不扩大当前发布范围，也不授权自动交易。

6. `FIRST_LAUNCH_MULTI_ASSET_PARALLEL_REPLACEMENT_ARCHITECTURE_DECISION_R1_2026-08-03.md`
   - 旧 ETH fallback 与新多资产并行替代架构权威。

7. `FIRST_LAUNCH_INTRADAY_ENTRY_STRATEGY_PRE_BACKTEST_FREEZE_R5_2026-08-02.md`
   - 三 Setup 研究父合同；与机器包冲突时服从第 1/2 项。

8. `FIRST_LAUNCH_SESSION_MOMENTUM_BREAKOUT_SCANNER_LITE_R3_FINAL_PARAMETER_AND_DELIVERY_FREEZE_2026-08-01.md`
   - Scanner 参数和 WATCH/SETUP_READY 边界；Universe/数据路线冲突时服从第 3 项。

9. `STRATEGY_RESEARCH_DISCOVERY_AND_CONVERGENCE_PLAYBOOK_V5_2026-08-03.md`
   - 小批量、快速前向验证方法权威。

10. `FIRST_LAUNCH_SHADOW_FORWARD_VALIDATION_AND_RAPID_ITERATION_PLAN_R1_2026-08-03.md`
   - T/S/R、Outcome、Evidence、快速迭代流程权威；样本独立性服从第 4 项；上线后研究排序服从第 5 项及其 R2 Roadmap。

11. `FIRST_LAUNCH_CURRENT_MASTER_TASK_REGISTER_AND_EXECUTION_ORDER_R2_2026-08-03.md`
    - 当前执行顺序与 Backlog 入口。

12. 部署前运维阻断：
    - `FIRST_LAUNCH_RECONNECT_BUDGET_RESET_NEXT_DEPLOYMENT_BLOCKER_2026-08-02.md`
    - `TRADER_ASSIST_OFF_HOST_BACKUP_AND_LIGHTSAIL_SNAPSHOT_RETIREMENT_NEXT_DEPLOYMENT_SCOPE_2026-08-02.md`

---

## 2. 当前被取代的 Universe / Capacity 路线

以下文件继续保留审计价值，但其自动扩张容量与自动 Universe 路线**不再是当前发布执行权威**：

```text
FIRST_LAUNCH_UNIVERSE_REFRESH_AND_EXPANDING_CAPACITY_SPIKE_DECISION_R1_2026-08-03.md
```

其被取代部分包括：

- 8→16→32→64→... Expansion Capacity Harness；
- 自动全市场质量筛选；
- 自动寻找最终 Universe 数量；
- 周期性全市场自动 Universe Refresh；
- 复杂自动 Apply 路线。

当前改为：

```text
MANUAL VERSIONED 40-MARKET REGISTRY
+ HOT ADD/REMOVE/TIER CHANGE
+ LIGHT 40-MARKET LOAD SMOKE
```

旧文件中与当前仍不冲突的只读安全思想可作历史参考，但不得恢复被明确取消的开发范围。

---

## 3. 当前时间周期权威

```text
RAW_STRATEGY_CANDLE = 5m ONLY
SIGNAL = 5m
STRUCTURE = 15m LOCAL_FROM_5m
CONTEXT = 1h LOCAL_FROM_5m
FORMAL_OUTCOME_PATH = 1m ON DEMAND
```

当前全部市场：

```text
FAST_5M_PROFILE ONLY
```

本发布：

```text
REALTIME_DYNAMIC_TIMEFRAME_SWITCH = NO
```

未来：

```text
PER_MARKET_STABLE_TIMEFRAME_PROFILE
= POST_FIRST_LAUNCH / V0.2 STRATEGY OPTIMIZATION
= CONDITIONAL BACKLOG
= REQUIRES FORWARD EVIDENCE AND NEW MACHINE SEMANTICS FREEZE
```

Engineering 不得自行实现第二 Profile 或动态切换。

Scheduled U.S. Macro Event 子研究未来如需研究 `T+1s / T+5s / T+10s / 10–60s Micro-Pause`，允许在独立未来研究阶段评估：

```text
EVENT-WINDOW HIGH-RES DATA ONLY
```

该研究需求不得修改当前发布的 5m-only Strategy Route，也不得恢复全市场持续 tick/sub-second 平台。

Strong / No-Retest Breakout 未来研究如需 `MICRO_PULLBACK / TIME_ACCEPTANCE`，优先使用 bounded 1m event path；不得因此把当前正式 Signal timeframe 改为 1m。

---

## 4. 当前产品与发布方向

```text
MANUAL 40-MARKET REGISTRY
→ MULTI-ASSET 5m DATA CORE
→ LOCAL 15m/1h
→ THREE-SETUP STRATEGY KERNEL
→ P0/P1/P2 FULL FORMAL SIGNALS
→ SHADOW ORDERS
→ ON-DEMAND 1m OUTCOME
→ T/S/R + EVIDENCE
→ CORRELATION CLUSTERS
→ LIGHT 40-MARKET LOAD SMOKE
→ OPS BLOCKERS
→ HUMAN-CONTROLLED DEPLOYMENT
→ SHADOW FORWARD VALIDATION
→ POST-LAUNCH STRATEGY EVIDENCE REVIEW
→ CLUSTER-NORMALIZED REVIEW
→ RAPID LIMITED ITERATION
```

固定：

```text
AUTO_TRADE = NO
EXCHANGE_WRITE_AUTHORITY = ABSENT
HUMAN_FINAL_DECISION = YES
ALL_TIERS_FULL_STRATEGY = YES
ALL_TIERS_FORMAL_SIGNAL_NOTIFICATION = YES
ALL_TIERS_SHADOW_ORDER = YES
ALL_TIERS_OUTCOME = YES
RAW_CORRELATED_SIGNALS_ARE_INDEPENDENT_SAMPLES = NO
CLUSTER_NORMALIZED_PRIMARY_RESEARCH_METRICS = YES
FUTURE_CORRELATED_EXPOSURE_GATE = REQUIRED
```

---

## 5. 手续费当前边界

当前发布只允许一个可选 Micro Fee Guard：

```text
TOTAL_INCREMENTAL_ENGINEERING_TIME_INCLUDING_TESTS <= 90 MINUTES
```

若超过：

```text
DEFER
```

当前不允许为了手续费扩大为账户级 fee engine、TT/MT/MM、自动 maker/taker routing 或自动 fee-based market switching。

---

## 6. 相关信号、研究与未来暴露

所有 Approved Formal Signal / ShadowOrder / Outcome 继续完整保留。

研究同时保留：

```text
RAW MARKET-LEVEL
SETUP RESEARCH CLUSTERS
EXPOSURE CLUSTERS
CLUSTER-NORMALIZED
LEADER-ONLY
```

未来半自动或自动交易必须采用：

```text
ONE_NEW_POSITION_PER_EXPOSURE_CLUSTER
```

或另行冻结的共享 Cluster 风险预算。

---

## 7. 上线后策略研究与未来开发权威

当前发布不因新研究增加第四 Setup 或重新打开 Machine Strategy 参数。

当前统一排序：

```text
R1 = BREAKOUT LIFECYCLE OPTIMIZATION
     R1A FAILED_ACCEPTED_BREAKOUT / FAILED_IMPULSE
     R1B STRONG / NO-RETEST BREAKOUT COVERAGE AUDIT

R2 = PER_MARKET_STABLE_TIMEFRAME_PROFILE
R3 = SECTOR / PEER RELATIVE STRENGTH
R4 = SCHEDULED MACRO EVENT + EVENT ASSET ROUTER
R5 = CASH OPEN / OPENING REPRICING
R6 = LOGICAL INVALIDATION EXIT
R7 = POSITION ENTRY SCALING / PROBE → ADD
R8 = CROSS-MARKET CONFIRMATION SOFT SCORE
R9 = ADVANCED L2 / OFI / BOOK RESILIENCY
```

R1 不改变原 `FAILED_ACCEPTED_BREAKOUT` 的最高优先级；它将成功 Micro FAST、Standard、Missed Runaway、Immediate Failure 与 Delayed Failed Accepted Breakout 放入同一 Breakout Event 生命周期研究，减少重复开发和样本选择偏差。

当前 Micro FAST 已覆盖无 Pullback Start 后的 5m outside acceptance/continuation；因此：

```text
NEW_MOMENTUM_SETUP_THIS_RELEASE = NO
MICRO_PULLBACK = RESEARCH_ONLY
TIME_ACCEPTANCE = RESEARCH_ONLY
BREAKOUT_PROBE = RESEARCH_ONLY_CONDITIONAL
```

`AUCTION_REGIME` 当前仅为 Research / Attribution Taxonomy，不是 Hard Gate；`RANGE_EDGE_REJECTION` 不在本发布中降级，未来只通过 Shadow Evidence 判断其 Ranking / Confidence 是否应低于 Sweep/Accepted Breakout。

当前发布只允许核验一个 Breakout Research Evidence 风险：没有 Formal Plan 的 Initial Breakout Event 是否具有未来可研究的 bounded 1m path。若可直接复用现有 on-demand 1m collector 且不造成实质 launch delay，可保留最小研究证据；否则作为第一项 Post-Launch Evidence Collector 工作，不得阻塞当前发布。

Scheduled Macro Event 继续保持 Research Only，未来明确加入：

```text
MACRO INTERPRETATION ASSET != TRADE ASSET
EVENT ASSET ROUTER
EVENT RELATIVE STRENGTH
IMPULSE RETENTION
PRICE ACCEPTANCE
EXECUTION QUALITY
IDIOSYNCRATIC CATALYST RISK
```

当前策略开发数量：

```text
CURRENT_RELEASE_NEW_STRATEGY_FEATURES = 0
POST_LAUNCH_RESEARCH_DEVELOPMENT_STREAMS = 9
NEW_FORMAL_SETUP_COMMITTED = 0
```

---

## 8. 新旧系统关系

```text
LEGACY_ETH_RUNTIME
= FROZEN FALLBACK + ROLLBACK + COMPARATOR

NEW_MULTI_ASSET_SYSTEM
= ETH + CURRENT REGISTRY MARKETS
= NOT_SUBMITTED SHADOW AUTHORITY
= HUMAN FINAL DECISION
```

通知采用：

```text
PARALLEL_INSTALLED
SINGLE_ACTIVE_NOTIFICATION_AUTHORITY
```

---

## 9. PR #52 解释规则

PR #52 继续保持：

```text
OPEN
DRAFT
UNMERGED
DOCUMENTATION_ONLY
```

旧文档或评论如与本索引冲突，以本索引和第 1 节当前权威为准。

本文件不授权代码修改、依赖安装、数据订阅购买、部署、重启、permit 修改、账户访问、签名、交易所写入、自动下单、Mark Ready 或 Merge。