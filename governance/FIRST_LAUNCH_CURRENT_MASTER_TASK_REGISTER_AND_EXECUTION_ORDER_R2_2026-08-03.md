# First Launch 当前总任务登记表与执行顺序 R2

**记录 ID：** `TA-FIRST-LAUNCH-CURRENT-MASTER-TASK-REGISTER-R2-2026-08-03`  
**更新日期：** `2026-08-12`  
**仓库：** `woshixiong/trader-assist-v0`  
**关联 Draft PR：** `#52`  
**状态：** `PLANNING_ONLY / NON_EXECUTABLE / MASTER_BACKLOG_INDEX`  
**任务派发权威：** `PROJECT_CONTROL_ONLY`  
**当前文档入口：** `FIRST_LAUNCH_CURRENT_AUTHORITY_INDEX_AND_SUPERSESSION_MAP_R1_2026-08-03.md`  
**当前快速路线：** `FIRST_LAUNCH_MANUAL_40_MARKET_REGISTRY_FAST_ROUTE_AND_TIMEFRAME_PROFILE_BACKLOG_R1_2026-08-12.md`  
**策略精度最高权威：** `FIRST_LAUNCH_CURRENT_RELEASE_MACHINE_EXECUTABLE_STRATEGY_PACKAGE_R1_1_FINAL_PRECISION_CLOSURE_2026-08-03.md`  
**策略主体权威：** `FIRST_LAUNCH_CURRENT_RELEASE_MACHINE_EXECUTABLE_STRATEGY_PACKAGE_R1_2026-08-03.md`  
**相关信号与未来暴露权威：** `FIRST_LAUNCH_CORRELATED_SIGNAL_CLUSTERING_BACKTEST_AND_EXECUTION_EXPOSURE_GOVERNANCE_R1_2026-08-04.md`

---

## 1. 当前核心决策

当前发布不再采用高成本的全市场自动 Universe / 扩张容量路线。

固定：

```text
MANUALLY_MAINTAINED_VERSIONED_MARKET_REGISTRY = YES
INITIAL_MARKET_COUNT = 40
HOT_ADD_REMOVE_TIER_CHANGE = REQUIRED
FULL_EXCHANGE_DYNAMIC_DISCOVERY = NO
EXPANDING_CAPACITY_HARNESS = CANCELLED_FOR_CURRENT_RELEASE
AUTOMATIC_UNIVERSE_SCORING = NO
```

当前方法：

```text
FIXED 40-MARKET REGISTRY
→ 5m PUBLIC DATA
→ LOCAL 15m / 1h CAUSAL AGGREGATION
→ ASSET-NEUTRAL THREE-SETUP KERNEL
→ FORMAL SIGNAL
→ NOT_SUBMITTED SHADOW ORDER
→ ON-DEMAND 1m OUTCOME
→ T/S/R + EVIDENCE + EXPORT
→ CORRELATION CLUSTERS
→ FAST SHADOW FORWARD VALIDATION
```

固定原则：

```text
RAPID_ITERATION = CORE_PROJECT_METHOD
SMALL_BATCH_CHANGE = REQUIRED
HUMAN_FINAL_DECISION = REQUIRED
AUTO_TRADE = NO
ALL_TIERS_FULL_STRATEGY = YES
ALL_TIERS_FORMAL_SIGNAL_NOTIFICATION = YES
ALL_TIERS_SHADOW_ORDER = YES
ALL_TIERS_OUTCOME = YES
RAW_CORRELATED_SIGNALS_ARE_INDEPENDENT_SAMPLES = NO
CLUSTER_NORMALIZED_PRIMARY_RESEARCH_METRICS = YES
```

---

## 2. 当前时间周期语义

```text
RAW_STRATEGY_CANDLE_FEED = 5m ONLY
SIGNAL_BASE_TIMEFRAME = 5m
STRUCTURE_TIMEFRAME = 15m LOCAL_FROM_5m
CONTEXT_TIMEFRAME = 1h LOCAL_FROM_5m
OUTCOME_PATH_TIMEFRAME = 1m ON DEMAND
```

当前所有市场只使用一个有效 Profile：

```text
FAST_5M_PROFILE
Execution = 5m
Structure = 15m
Context = 1h
```

本轮明确不开发实时动态周期切换。

---

## 3. 当前发布关键路径

1. Engineering Optimization 核验当前代码、Git 状态和最小复用点；
2. Project Control 派发人工热插拔 Market Registry；
3. 实现资产无关 5m 数据路径与 MarketIdentity；
4. 实现 5m → 15m / 1h 严格因果聚合；
5. 复用当前机器策略包，实现资产无关三 Setup Kernel；
6. P0/P1/P2 全部运行完整策略、Formal Signal、ShadowOrder、Outcome；
7. BBO/L2 采用按需获取；
8. 正式 ShadowOrder 才开启/回补 1m Outcome Path；
9. 实现 T/S/R、Evidence、Export；
10. 实现 Setup Research Cluster / Exposure Cluster 证据与统计；
11. 统一 Discord Signal Notification，带 Tier / Execution Eligibility；
12. 手续费 Micro Guard 仅在包含测试总增量 `<=90 minutes` 时加入，否则延期；
13. 做固定 40 市场 30–60 分钟轻量 Load Smoke，不再建设 Expansion Capacity Harness；
14. 完成 reconnect-budget、off-host backup/recovery 等运维阻断；
15. CI、独立 Review、Rollback、Deploy、Smoke、Cutover；
16. 开始 Shadow Forward Validation 和证据驱动快速迭代。

---

## 4. 当前必须完成

- versioned/manual Market Registry；
- Hot Add/Remove/Tier Change；
- 新市场 metadata validate + 5m warmup + safe closed-5m activation；
- 删除市场停止新 Candidate/Event，但历史 Shadow Outcome drain；
- 资产无关 MarketIdentity / ClosedBar / Strategy State / PlanDraft；
- 5m 唯一原始策略 Candle；
- 本地 15m/1h 聚合；
- Sweep Reclaim；
- Breakout Micro FAST；
- Breakout STANDARD；
- Range Edge Rejection；
- P0/P1/P2 完整 Signal；
- NOT_SUBMITTED ShadowOrder；
- On-demand BBO/L2；
- On-demand 1m Outcome；
- T/S/R；
- 30/60/120m Outcome；
- Correlation Cluster Evidence；
- Raw / Cluster-normalized / Leader-only 统计；
- Evidence Export；
- Unified Notification；
- 40-market Load Smoke；
- reconnect-budget；
- off-host backup/recovery；
- CI、Review、Rollback、Deploy、Smoke。

---

## 5. 手续费当前边界

本轮只允许可选的极小 Fee Guard：

```text
OPTIONAL_MICRO_FEE_GUARD
TOTAL_INCREMENTAL_ENGINEERING_TIME_INCLUDING_TESTS <= 90 MINUTES
```

允许：

- 读取现有 HIP-3 metadata `growthMode`；
- 保存 growth mode / fee class / observed-at；
- P0 HIP-3 非 Growth Mode 时 `FEE_EXECUTION_BLOCKED`；
- Shadow Research 继续。

如果 Engineering 核验超过 90 分钟：

```text
DEFER_TO_POST_FIRST_LAUNCH_COST_MODEL_R2
```

当前不做：`userFees`、账户级费率、TT/MT/MM 完整模型、自动 maker/taker routing、自动 fee-based market switching。

---

## 6. 当前明确不做

- 全交易所自动发现；
- 自动 Universe Scoring；
- Expansion Capacity Harness；
- 自动全市场 Universe Refresh；
- 实时 Dynamic Timeframe Switching；
- 第二个有效 Timeframe Profile；
- 全市场持续 1m；
- 全市场永久 BBO/L2；
- 独立持续 15m API Feed；
- 独立持续 1h API Feed；
- 自动交易；
- 账户或签名接入；
- 多资产组合资金仲裁；
- 第四 Setup；
- 动态退出引擎；
- 大型外部交易框架接入；
- 把高度相关 ShadowOrder 全部解释成独立策略证据。

---

## 7. 部署前阻断

```text
OPS-1 = FIRST_LAUNCH_RECONNECT_BUDGET_RESET
OPS-2 = TRADER_ASSIST_OFF_HOST_BACKUP_AND_LIGHTSAIL_SNAPSHOT_RETIREMENT
```

正式部署前必须完成恢复和回滚门禁。

---

## 8. Post-Launch / V0.2 条件性 Backlog：Per-Market Stable Timeframe Profile

该项必须保留，防止后续遗漏：

```text
BACKLOG_ID = PER_MARKET_STABLE_TIMEFRAME_PROFILE
STAGE = POST_FIRST_LAUNCH / V0.2 STRATEGY OPTIMIZATION
STATUS = CONDITIONAL
CURRENT_IMPLEMENTATION = NO
```

目标不是实时动态切换，而是在真实证据支持后，为某些市场选择一个稳定、版本化的 Timeframe Profile。

当前 Profile：

```text
FAST_INTRADAY_PROFILE
Execution = 5m
Structure = 15m
Context = 1h
```

未来候选（仅研究示例，不授权参数）：

```text
SLOW_INTRADAY_PROFILE
Execution = 15m
Structure = 1h
Context = 4h
```

只有前向证据出现以下任一情况才重新打开：

- 某些市场长期 5m 噪声过高；
- 5m 成本后 Net Edge 持续显著差；
- 当前结构周期造成长期 Entry/Stop/Target 经济性恶化；
- Shadow/Offline 对照持续证明稳定较慢 Profile 改善 Net Expectancy、回撤或执行可靠性；
- 某类资产长期产生大量低价值/重复 Formal Signal。

启动时必须先由 Strategy Optimization 做版本化研究，不能由 Engineering 自行切换周期。

Registry 可以现在低成本预留：

```text
timeframe_profile = FAST_5M
```

但当前只允许这一个有效值，不得因此提前实现多 Profile 行为分支。

---

## 9. 其他未来条件性 Backlog

### Cost Model R2

可研究：

- `userFees`；
- actual account fee tier；
- TT/MT/MM；
- Gross/Net Expectancy；
- Cost / Opportunity Ratio。

### Correlated Execution Risk

自动交易前必须实现：

```text
ONE_NEW_POSITION_PER_EXPOSURE_CLUSTER
```

或另行冻结：

```text
SHARED_RISK_BUDGET_PER_EXPOSURE_CLUSTER
```

### Long-term Backtest Architecture

仅在前向样本过慢、需要大量参数比较、罕见历史行情、自动交易/资金规模提升或组合级风险验证时重新评估。

---

## 10. 权限边界

本文件不授权代码修改、工程派发、依赖安装、部署、重启、permit 修改、快照删除、账户访问、签名、交易所写入、自动下单、PR Mark Ready 或 Merge。