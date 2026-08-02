# First Launch 当前总任务登记表与执行顺序

**记录 ID：** `TA-FIRST-LAUNCH-CURRENT-MASTER-TASK-REGISTER-2026-08-03`  
**日期：** `2026-08-03`  
**仓库：** `woshixiong/trader-assist-v0`  
**生产比较基线：** `ac6496596ebdb0b8c2b0a40753dbed1771a0c85d` / `ETH-LDAR-v0.1`  
**关联 Draft PR：** `#52`  
**状态：** `PLANNING ONLY / NON-EXECUTABLE / MASTER BACKLOG INDEX`  
**任务派发权威：** `PROJECT_CONTROL_ONLY`

本文统一登记当前已经冻结、但尚未执行或尚未完成的工作，并明确阶段顺序。本文不取代各专项策略合同、研究合同、产品合同或运维合同；专项细节仍以被引用的权威文件为准。

本文不授权代码修改、回测执行、依赖安装、分支创建、PR、merge、部署、重启、permit 修改、账户访问、签名、交易所写入或自动下单。

---

## 1. 当前唯一工作主线

当前必须先完成策略优化与回测，其他全部工作保留但暂停派发。

```text
CURRENT_EXCLUSIVE_FOCUS = INTRADAY_STRATEGY_OPTIMIZATION_AND_BACKTEST

SCANNER_IMPLEMENTATION = DEFERRED_UNTIL_BACKTEST_COMPLETE
PRODUCT_RELEASE_WORK = DEFERRED_UNTIL_BACKTEST_COMPLETE
RECONNECT_FIX_IMPLEMENTATION = DEFERRED_UNTIL_BACKTEST_COMPLETE
BACKUP_DR_IMPLEMENTATION = DEFERRED_UNTIL_BACKTEST_COMPLETE
PRODUCTION_DEPLOYMENT = PROHIBITED_UNTIL_ALL_PREDEPLOYMENT_GATES_CLOSE
```

当前唯一顺序：

```text
R5 STRATEGY FREEZE
→ ENGINEERING ROUTE DESIGN
→ PROJECT CONTROL DISPATCH
→ ROUND 1 CAUSAL BACKTEST
→ STRATEGY OPTIMIZATION REVIEW
→ LIMITED ROUND 2 REVISION IF EVIDENCE JUSTIFIES
→ PARAMETER FREEZE
→ FINAL HOLDOUT
→ BACKTEST COMPLETION GATE
→ REOPEN DEFERRED RELEASE AND OPERATIONS WORK
```

不得在当前策略回测工作中混入：

- Scanner 开发；
- 产品 UI 或 Discord 体验改造；
- WebSocket reconnect-budget 修复；
- 服务器备份或灾难恢复实施；
- Lightsail 快照删除；
- 生产部署、重启或 permit；
- Hyperliquid 账户访问、私钥、签名或交易所写入；
- 半自动或自动交易；
- 实时动态退出系统。

---

## 2. 当前策略与回测权威

优先级：

```text
FIRST_LAUNCH_INTRADAY_ENTRY_STRATEGY_PRE_BACKTEST_FREEZE_R5
> R4 > R3 > R2

STRATEGY_RESEARCH_DISCOVERY_AND_CONVERGENCE_PLAYBOOK_V4
> V3 > V2 > V1

旧三 Setup 语义：
R1.2 > R1.1 > R1
```

当前必须读取：

1. `governance/FIRST_LAUNCH_INTRADAY_ENTRY_STRATEGY_PRE_BACKTEST_FREEZE_R5_2026-08-02.md`
2. `governance/STRATEGY_RESEARCH_DISCOVERY_AND_CONVERGENCE_PLAYBOOK_V4_2026-08-02.md`
3. `governance/FIRST_LAUNCH_INTRADAY_BACKTEST_ENGINEERING_HANDOFF_R1_2026-08-02.md`
4. `governance/STRATEGY_RESEARCH_AND_BACKTEST_OPERATING_STANDARD_V1_2026-08-01.md`
5. `governance/FUTURE_V0_POSITION_MANAGEMENT_AND_EXIT_RESEARCH_PLAN_R2_2026-08-02.md`
6. 三 Setup R1 / R1.1 / R1.2
7. 当前生产 `src/trader_assist_v0/first_launch/strategy.py`，只读 Comparator

当前策略工程任务标识：

```text
FIRST_LAUNCH_INTRADAY_STRATEGY_BACKTEST_ENGINEERING_ROUTE_R1
```

工程优化窗口当前只需要输出 A～J 完整路线包，不直接实现：

```text
A. LIVE_GITHUB_IDENTITY
B. EXISTING_CAPABILITY_MAP
C. MINIMUM_IMPLEMENTATION_ROUTE
D. EXACT_FILE_ALLOWLIST
E. DATA_PLAN
F. TEST_PLAN
G. REPORT_SCHEMA
H. WORK_BREAKDOWN
I. ACCEPTANCE_GATES
J. FINAL_EXECUTION_PROMPT
```

任何无法唯一实现的策略参数或语义必须返回 Strategy Optimization 裁决；Engineering Optimization 和 Project Control 均不得自行选择或改写参数。

---

## 3. 阶段 S：策略优化和回测

### S0 — GitHub 身份、祖先与已有能力核验

必须核验：

- 实时 `main` HEAD；
- 生产 SHA 与 `main` 的关系；
- PR #52 最新 HEAD；
- 历史 Bronze replay、three-setup research、causal replay、Outcome、Trial Registry、fixtures 和 tests/research；
- 各历史分支祖先和可移植提交；
- 重复开发风险；
- 推荐实现基线和专用回测分支。

文档分支不得直接被假定为代码实现基线。

### S1 — 第一轮回测工程路线

原则：

- 不修改生产 `strategy.py` 作为 R5 研究入口；
- 生产策略只作为 `V0_1_EXACT_BASELINE` Comparator；
- R5 在独立 `research` 包实现；
- 优先复用仓库已有 Candle、validation、aggregation、replay、Outcome、JSONL/SQLite 和 tests/research；
- 只建设最小事件驱动 causal replay；
- 不建设通用回测平台或生产 daemon；
- Trial Registry 只做当前回测所需的最小版本。

### S2 — Round 1

固定范围：

```text
P0 COMPARATORS
+ P1 PRIMARY CANDIDATES
+ COMPLETE CAUSAL PATH EVIDENCE
```

包括：

- 1h dual labels，仅归因、不提前过滤；
- 15m Zone；
- Sweep fact-confirmed reclaim；
- Breakout Micro FAST；
- Breakout state-driven STANDARD；
- Range Edge Rejection；
- Trend Segment Re-entry；
- structural stop、Chase、Target Feasibility；
- 1R/1.5R/2R、MFE/MAE、shadow exits；
- exact recent 与单一 long-history proxy 分开报告；
- Development / Validation / Final Holdout 按时间切分；
- closed-and-received-only、no-lookahead。

### S3 — Strategy Review / Round 2

Round 1 结果必须返回 Strategy Optimization。

每个独立单元最多修改 1～2 个变量；必要 P2 按冻结优先级进入。不得因为结果不好而无限调参。

### S4 — Parameter Freeze / Final Holdout

参数冻结前不得查看或使用 Final Holdout 调参。

最终 Holdout 通过后，输出：

```text
STRATEGY_BACKTEST_COMPLETE = PASS
PARAMETER_FREEZE = PASS
FINAL_HOLDOUT = PASS
```

最多允许 Round 4，且只能因实现错误、重大数据矛盾、exact/proxy 结构性冲突或单一决定性变量。

### S5 — Backtest Exit Gate

只有完成下列门禁后，才能重新启动后续发布工作：

```text
LIVE_IDENTITY_VERIFIED = PASS
NO_PRODUCTION_MUTATION = PASS
DATA_MANIFEST = PASS
DETERMINISTIC_FIXTURES = PASS
NO_LOOKAHEAD = PASS
MULTITIMEFRAME_ALIGNMENT = PASS
STATE_LIFECYCLE = PASS
DEDUP_AND_SUPERSESSION = PASS
SHADOW_OUTCOME = PASS
P0_COMPLETE = PASS
P1_COMPLETE = PASS
REPRODUCIBLE_RERUN = PASS
REPORT_COMPLETE = PASS
STRATEGY_OPTIMIZATION_DECISION = RECORDED
PARAMETER_FREEZE_OR_EXPLICIT_REJECTION = RECORDED
```

---

## 4. 回测完成后重新打开的发布任务

以下任务全部保留，没有取消；但当前不得派发实现。

### R1 — 三 Setup 最终生产范围

状态：

```text
DEFERRED_UNTIL_STRATEGY_BACKTEST_COMPLETE
```

历史阶段计划包括 Sweep、Breakout 和 Range，但最终生产实现不得机械沿用早期缩减方案。应由 R5 回测结果和 Strategy Optimization 最终参数冻结重新生成生产变更范围。

必须保留：

- 人工最终判断；
- 人工下单；
- no exchange write authority；
- closed candle / no-lookahead；
- existing TradePlan / Card / notification compatibility；
- production comparator regression；
-最小回滚。

不得在回测完成前修改生产策略。

### R2 — Scanner Lite R3

权威：

`governance/FIRST_LAUNCH_SESSION_MOMENTUM_BREAKOUT_SCANNER_LITE_R3_FINAL_PARAMETER_AND_DELIVERY_FREEZE_2026-08-01.md`

保留要求：

```text
SCANNER_BIAS = HIGH_RECALL
UNIVERSE = ALL_ELIGIBLE_HYPERLIQUID_PERPS
AUTO_TRADE = NO
AUTO_ASSET_SWITCH = NO
SCANNER_CANDIDATE != FORMAL_SIGNAL
SCANNER_FAILURE_MUST_NOT_AFFECT_ETH_RUNTIME
```

推荐路线仍为独立 Scanner Sidecar / 独立运行单元；最终路线需在回测完成后结合最新代码重新核验。

### R3 — Scanner 与信号证据最低合同

当前发布必须保留：

- 可恢复的 point-in-time Universe；
- 所有 WATCH 和 SETUP_READY 候选先留存，Top-N 只限制通知；
- Scanner Candidate 与正式 Setup/Signal/TradePlan 权威分离；
- strategy/scanner/parameter/release 版本身份；
- 当前数据低成本可生成的最小事件路径；
- T/S/R 关联；
- basic Outcome / 30m、60m、120m MFE/MAE；
- Scanner no-signal 运行证明；
- append-only evidence；
- failure isolation。

不默认建设：

- 完整 recall/precision 平台；
- 完整 Trial Registry 平台；
- 完整 Level Attribution；
- 跨资产聚类；
- PBO、Deflated Sharpe、walk-forward 平台；
- 新研究平台；
- 第四 Setup。

### R4 — Operator / Product 最小体验

保留要求：

- WATCH 与 SETUP_READY 明确不是正式 Signal；
- Formal Signal、TradePlan、Candidate 语义明确区分；
- T/S/R 为一次快速操作；
- `DO NOT CHASE` 和 liquidity warning 清晰显示；
- 所有候选后台留存；
- 不重构完整 UI；
- 不开发 Discord Bot 或复杂 Dashboard，除非产品窗口后来明确授权。

### R5 — ShadowOrder / Outcome 缺口审查

当前仓库已有：

- OperatorReviewCard；
- NOT_SUBMITTED ShadowOrder；
- T/S/R；
- offline Outcome foundations。

待办：

- 只读确认生产是否持久化每个 actionable Signal / TradePlan；
- immutable Signal / Setup / Plan ID 是否完整；
- 是否保留足够未来行情；
- 是否可离线计算未执行计划 Outcome；
- 只补最小缺口。

不建设完整 paper-trading、Shadow Canary、账户模拟或自动撮合系统。

---

## 5. 部署前运维与可靠性任务

统一索引：

`governance/FIRST_LAUNCH_CURRENT_RELEASE_OPERATIONS_BLOCKERS_2026-08-02.md`

这些任务当前暂停实现，但在下一次生产部署前必须重新列出并完成。

### OPS-1 — WebSocket 重连预算错误累计修复

```text
TASK_ID = FIRST_LAUNCH_RECONNECT_BUDGET_RESET
GATE = PRE_DEPLOYMENT_BLOCKER
```

权威：

`governance/FIRST_LAUNCH_RECONNECT_BUDGET_RESET_NEXT_DEPLOYMENT_BLOCKER_2026-08-02.md`

必须：

- 完整恢复 READY 后重置连续重连尝试计数；
- 历史成功重连不消耗下一次独立事故预算；
- 连续失败达到预算仍 fail closed；
- 事故复现、连续失败、不完整恢复、status publication failure 等测试；
- full CI、独立 Review；
- 不以人工重启、增加次数或 systemd 自动重启代替源码修复。

### OPS-2 — 主机外备份、灾难恢复与 Lightsail 快照退役

```text
TASK_ID = TRADER_ASSIST_OFF_HOST_BACKUP_AND_LIGHTSAIL_SNAPSHOT_RETIREMENT
GATE = DEPLOYMENT_WORKFLOW_REQUIRED
```

权威：

`governance/TRADER_ASSIST_OFF_HOST_BACKUP_AND_LIGHTSAIL_SNAPSHOT_RETIREMENT_NEXT_DEPLOYMENT_SCOPE_2026-08-02.md`

必须：

- GitHub exact SHA 重建；
- `runtime.db` SQLite 一致性备份；
- 必要生产配置加密备份；
- 凭据独立恢复来源；
- 主机外对象存储；
- 上传后重新下载、checksum、解密、只读打开和 integrity check；
- 最小离线恢复演练；
- 第二本地副本；
-恢复 runbook；
-部署前和部署后备份；
-备份失败不影响交易主运行时。

当前 Lightsail 快照：

```text
0619-predeploy-20260726T195309Z
```

不得立即删除。只有全部恢复门禁通过，并获得单独授权后才具备删除资格。

---

## 6. 最终集成、部署和验收任务

状态：

```text
DEFERRED_UNTIL_STRATEGY_BACKTEST_COMPLETE
AND ALL PREDEPLOYMENT BLOCKERS PASS
```

未来统一安排：

1. 根据最终策略回测和参数冻结生成生产功能范围；
2. 完成三 Setup / Scanner / evidence 的实现和独立 Review；
3. 完成 reconnect-budget 修复；
4. 完成备份实现、测试和部署前备份；
5. exact-head CI；
6. 独立完整 Review；
7. 冻结 exact release SHA 与 rollback SHA；
8. 用户分别授权 Mark Ready、merge 和 deployment；
9. 一次统一部署或经产品明确允许的分阶段启用；
10. 先验证 ETH 主服务，再验证 Scanner；
11. 非交易 smoke；
12. 确认无交易所写权限；
13. 部署后备份、下载验证和恢复演练；
14. 单独授权后删除 Lightsail 快照；
15. 自然观察 reconnect 行为和运行稳定性。

部署前统一必须重新列出：

```text
STRATEGY_BACKTEST_AND_FREEZE
THREE_SETUP_PRODUCTION_SCOPE
SCANNER_R3
SIGNAL_EVIDENCE_AND_TSR
SHADOW_OUTCOME_MINIMUM_GAP
RECONNECT_BUDGET_RESET
OFF_HOST_BACKUP_AND_DR
ROLLBACK
CI_AND_REVIEW
DEPLOYMENT_AND_SMOKE
POST_DEPLOYMENT_BACKUP_AND_SNAPSHOT_RETIREMENT
```

---

## 7. 后续研究待办，不进入下一次部署关键路径

以下任务保留为 Post-First-Launch / Future V0 Research：

- P2 Secondary/Sensitivity 未在第一轮晋级的候选；
- 30m confirmation scale；
- pin-bar quality、shallow/deep retest 等有限研究；
- Volume Profile / HVN / LVN / POC；
- OI/funding context；
- L2 depth / order flow；
- realtime dynamic exit；
-完整 position management engine；
-更严格 walk-forward、PBO、Deflated Sharpe；
-完整 Scanner recall/precision/missed-candidate research；
-跨资产相关性和事件聚类；
-第四 Setup；
-自动执行或半自动执行。

这些工作只有在 First Launch 数据证明价值、并由产品和策略窗口重新授权后才可进入。

---

## 8. 当前停止规则

在策略回测完成之前，以下请求默认停止并返回本登记表：

- 开始 Scanner Writer；
- 开始 reconnect 修复；
- 开始备份脚本；
- 修改生产策略；
- 修改 runtime/systemd/permit；
- 创建部署候选；
- 生产重启或部署；
- 删除 Lightsail 快照。

例外仅限生产事故的受控临时恢复，并且不能被视为正式修复。

---

## 9. 当前权威状态

```text
CURRENT_ACTIVE_TRACK = STRATEGY_OPTIMIZATION_AND_BACKTEST
CURRENT_IMPLEMENTATION_AUTHORITY = NONE UNTIL PROJECT CONTROL DISPATCH
CURRENT_PRODUCTION_MUTATION_AUTHORITY = NONE
CURRENT_DEPLOYMENT_AUTHORITY = NONE
CURRENT_SCANNER_AUTHORITY = DEFERRED
CURRENT_OPERATIONS_IMPLEMENTATION = DEFERRED
ALL_PRIOR_TODOS_RETAINED = YES
```

当策略优化窗口完成最终回测裁决后，Engineering Optimization 必须重新读取本文和所有专项文件，生成下一阶段的统一工程路线；Project Control 随后才可以派发实现。
