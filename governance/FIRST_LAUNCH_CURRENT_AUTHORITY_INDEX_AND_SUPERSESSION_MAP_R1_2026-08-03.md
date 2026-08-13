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
   - `FIRST_LAUNCH_POST_LAUNCH_STRATEGY_RESEARCH_AND_FUTURE_DEVELOPMENT_INVENTORY_R4_2026-08-13.md` 是当前完整 Post-Launch Research / Future Development Inventory；未来全局优先级不因旧 R1→R9 编号冻结。
   - **当前 Event / Boundary 最终研究权威：** `FIRST_LAUNCH_EVENT_AWARE_AND_SCHEDULED_BOUNDARY_RISK_FINAL_RESEARCH_FREEZE_R2_2026-08-13.md`。它把最终架构冻结为：`ONE CORE THREE-SETUP PRICE-ACTION SYSTEM + EVENT-AWARE CONTEXT / ATTRIBUTION + GENERAL SCHEDULED BOUNDARY RISK / PERMISSION LAYER`；Event 不直接产生 Long/Short，Boundary Guard 不改变方向但未来可 veto / de-risk；Asia / Europe / U.S. 三类主要开盘边界全部纳入 Guard，但采用 asset-specific relevance；Default Flatten / De-Risk 为未来自动化研究 baseline；所有宏观/财报/FOMC/Call 信息节点统一进入同一个 Boundary Guard。
   - `FIRST_LAUNCH_EVENT_AWARE_OVERLAY_AND_SCHEDULED_BOUNDARY_RISK_CONVERGENCE_R1_2026-08-13.md` 保留审计价值，但发生冲突时服从上述 R2 Final Research Freeze。
   - `FIRST_LAUNCH_SCHEDULED_US_MACRO_EVENT_STRATEGY_RESEARCH_AND_FUTURE_AUTOMATION_BACKLOG_R1_2026-08-12.md`、`FIRST_LAUNCH_SCHEDULED_CORPORATE_EARNINGS_EVENT_STRATEGY_RESEARCH_BACKLOG_R1_2026-08-13.md`、`FIRST_LAUNCH_INTRADAY_INFORMATION_EVENT_AND_US_EXTENDED_HOURS_STRATEGY_RESEARCH_ADDENDUM_R1_2026-08-13.md` 保留数据源、PIT、财报/FOMC 多阶段、执行研究等历史价值；与 R2 Final Research Freeze 冲突时服从 R2。
   - 旧 `...PRIORITY_ROADMAP_R2...` / `...INVENTORY_R3...` 保留审计价值，不再冻结未来开发顺序。

6. `FIRST_LAUNCH_MULTI_ASSET_PARALLEL_REPLACEMENT_ARCHITECTURE_DECISION_R1_2026-08-03.md`
   - 旧 ETH fallback 与新多资产并行替代架构权威。

7. `FIRST_LAUNCH_INTRADAY_ENTRY_STRATEGY_PRE_BACKTEST_FREEZE_R5_2026-08-02.md`
   - 三 Setup 研究父合同；与机器包冲突时服从第 1/2 项。

8. `FIRST_LAUNCH_SESSION_MOMENTUM_BREAKOUT_SCANNER_LITE_R3_FINAL_PARAMETER_AND_DELIVERY_FREEZE_2026-08-01.md`
   - Scanner 参数和 WATCH/SETUP_READY 边界；Universe/数据路线冲突时服从第 3 项。

9. `STRATEGY_RESEARCH_DISCOVERY_AND_CONVERGENCE_PLAYBOOK_V5_2026-08-03.md`
   - 小批量、快速前向验证方法权威。

10. `FIRST_LAUNCH_SHADOW_FORWARD_VALIDATION_AND_RAPID_ITERATION_PLAN_R1_2026-08-03.md`
   - T/S/R、Outcome、Evidence、快速迭代流程权威；样本独立性服从第 4 项；上线后候选方向服从第 5 项及其 Inventory / Final Research Freeze。

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

Event / Earnings / Boundary 未来如需秒级或分钟级 price-discovery / execution 研究，优先采用：

```text
BOUNDED EVENT / BOUNDARY WINDOW HIGH-RES EVIDENCE
```

不得因此修改当前 5m-only Strategy Route，也不得恢复全市场持续 tick/sub-second 平台。

Strong / No-Retest Breakout 未来研究如需 `MICRO_PULLBACK / TIME_ACCEPTANCE / IMPACT_RETENTION / RETEST-CONTINUATION-FAILURE`，优先使用 bounded 1m raw event path 并离线重建；不得因此把当前正式 Signal timeframe 改为 1m。

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

当前治理：

```text
REGISTER_ALL_VALUABLE_DIRECTIONS = YES
FUTURE_GLOBAL_PRIORITY = NOT_GLOBALLY_FROZEN
POST_LAUNCH_EVIDENCE_BEFORE_BROAD_PRIORITY_FREEZE = YES
```

但以下工程顺序已单独确认：

```text
P1 BOUNDED INITIAL BREAKOUT 1m RESEARCH EVIDENCE
= HIGH POST-LAUNCH PRIORITY
= FIRST RESEARCH-EVIDENCE ENGINEERING ITEM AFTER RELEASE/OPERABILITY CRITICAL WORK
= MAY BE BUNDLED INTO THE EARLIEST COHERENT POST-LAUNCH STAGE

P2 1m VOLUME / TRADE_COUNT
= PIGGYBACK P1 ONLY IF TRIVIAL

P3 CAUSAL PAIRED OI
= SEPARATE POST-LAUNCH DESIGN
```

P1 的 +120m 只是高分辨率 Breakout research horizon，不是任何交易持仓上限。

当前 Event / Boundary 最终研究冻结为：

```text
CORE ALPHA / ENTRY = THREE EXISTING SETUPS
SESSION = CONTEXT, NOT NEW STRATEGY
EVENT = INFORMATION / ATTRIBUTION OVERLAY
SCHEDULED HIGH-RISK BOUNDARY = GENERAL ALL-STRATEGY RISK / PERMISSION LAYER
EVENT BOUNDARIES USE THE SAME BOUNDARY GUARD
```

### 当前人工 / V0 Boundary Discipline

亚洲、欧洲、美国主要开盘/参与者切换边界都必须格外注意。人工交易阶段原则上：

```text
DEFAULT = DO NOT CARRY ORDINARY POSITION THROUGH MAJOR OPEN BOUNDARY
DEFAULT = FLATTEN / DE-RISK BEFORE BOUNDARY
EXCEPTION = HUMAN-APPROVED SPECIAL CASE
```

具体时间、提前多久、何时恢复交易目前不进入当前 Machine Strategy；由人类最终执行。

### Future Auto-Trading Mandatory Research

全面自动交易前必须建立、验证并冻结：

```text
SCHEDULED_BOUNDARY_RISK_GUARD
```

至少处理：

```text
Asia / Europe / U.S. regional open boundaries
asset-specific boundary relevance
scheduled macro releases
scheduled corporate information releases
multi-stage FOMC / Earnings Call boundaries
uncertain release windows
compound / stacked boundaries
pre-boundary de-risk
new-entry suppression
market-state recovery gate
calendar / DST / holiday handling
execution-quality dependency
exception authority
complete audit evidence
```

不能把人工“约 9:45 恢复”直接硬编码为固定规则；必须用 Historical/Forward/Shadow evidence 量化 false-break、whipsaw、MFE/MAE、spread/slippage、directional efficiency 和 recovery conditions。

Event Overlay 第一阶段不产生 Long/Short；任何 Event feature 想升级为 ranking/gate 必须证明相对 Base Setup 的稳定 OOS marginal value，并重新冻结 Strategy Authority。

当前 Micro FAST 已覆盖无 Pullback Start 后的 5m outside acceptance/continuation，因此：

```text
NEW_MOMENTUM_SETUP_THIS_RELEASE = NO
MICRO_PULLBACK = RESEARCH_ONLY
TIME_ACCEPTANCE = RESEARCH_ONLY
BREAKOUT_PROBE = RESEARCH_ONLY_CONDITIONAL
```

`AUCTION_REGIME` 当前仅为 Research / Attribution Taxonomy，不是 Hard Gate；`RANGE_EDGE_REJECTION` 不在本发布中降级。

当前 P1/P2/P3 已明确移至上线后顺序，不再是 First Launch release blocker：

```text
CURRENT_RELEASE_P1_BLOCKER = NO
CURRENT_RELEASE_P2_BLOCKER = NO
CURRENT_RELEASE_P3_BLOCKER = NO
```

当前策略开发数量：

```text
CURRENT_RELEASE_NEW_STRATEGY_FEATURES = 0
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