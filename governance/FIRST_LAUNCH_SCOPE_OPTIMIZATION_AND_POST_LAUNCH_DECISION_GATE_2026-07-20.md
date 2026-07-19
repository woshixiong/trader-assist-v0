# Trader Assist — First Launch 范围优化与上线后产品决策记录

**记录 ID：** `TA-FIRST-LAUNCH-SCOPE-OPTIMIZATION-AND-POST-LAUNCH-DECISION-GATE-2026-07-20-R1`  
**日期：** 2026-07-20  
**仓库：** `woshixiong/trader-assist-v0`  
**状态：** `USER APPROVED / GITHUB DRAFT SYNCHRONIZATION`  
**适用范围：** First Launch 当前收尾、上线门禁、上线后证据采集与下一阶段产品重规划输入  
**不包含：** V0 详细方案冻结、自动下单授权、多策略开发授权、账户/签名/交易所写入授权

---

## 1. 本记录的目的

本记录统一以下已经由用户确认的产品与工程原则：

1. 当前集中全部力量完成 First Launch 并尽快上线；
2. First Launch 是验证性交易辅助系统，不是机构级审计平台；
3. 已经完成且对后续有用的能力应保留，不通过删除代码来“简化”；
4. 未完成能力不得继续扩大 First Launch 的关键路径；
5. 与 First Launch 正确信号、资金风险、运行可靠性和权限安全无直接关系的工作统一延期；
6. First Launch 上线后，再根据真实数据决定优先开发更多策略还是用户确认执行/自动下单链；
7. 当前不冻结 V0 详细顺序，也不提前判定“多策略”或“自动执行”谁优先；
8. 所有延期能力必须保留记录，不得因本次范围压缩被静默删除；
9. GitHub 中的产品、工程和项目状态必须保持一致，冲突时以最新用户裁决和 exact GitHub object 为准。

本记录补充现有 First Launch Signal-First Baseline、Deferred Capability Registry 和 First Launch Verification Protocol。任何旧文档中与本记录冲突的固定开发顺序、过度审计要求或上线前范围，应以本记录为准重新审查。

---

## 2. 当前产品目标

### 2.1 First Launch 唯一当前目标

尽快交付一个可以真实辅助人类交易员的最小系统：

```text
Hyperliquid 公共 ETH 数据
→ 数据质量与因果性验证
→ 单一产品策略核心
→ 波动率与 OI/Funding/basis 上下文
→ 完整 TradePlan
→ 即时通知
→ 人类判断
→ 人工下单
→ 影子与结果记录
```

First Launch 需要验证：

- 系统能否稳定识别并通知交易机会；
- 信号是否及时、清楚且具有实际可执行性；
- 入场、追价、止损、止盈和数量是否可靠；
- 系统是否减少人工盯盘和临场计算负担；
- 当前策略是否具备足够的信号质量和机会覆盖；
- 人工复制信号并下单是否造成显著的机会损失。

First Launch 不需要在上线前证明：

- 策略长期盈利；
- 统计显著性；
- 所有市场 regime 均被覆盖；
- 多策略选择已经完成；
- 自动下单已经完成；
- 完整历史重建与机构级防篡改；
- 完整 Dashboard、HA、分布式存储或通用数据平台。

### 2.2 “一个策略”的解释

First Launch 保持一个产品策略核心或策略族。

现有代码内部可能包含：

- LONG / SHORT；
- FAST / STANDARD；
- 不同 setup family；
- WAIT / WATCH / PREPARE / EXPIRED / INVALIDATED；
- LOW / NORMAL / HIGH / EXTREME；
- 5m / 15m / 30m / 60m 决策与上下文；
- OI、Funding、basis 证据。

这些属于同一产品策略核心的方向、速度、状态、形态或安全覆盖，不自动等同于已经进入“多策略产品”。

用户所说的“增加策略”是指增加能够应对不同市场 regime、具有独立产品逻辑的互补策略，而不是简单增加参数变体。

---

## 3. 不删除代码的范围优化原则

### 3.1 保留

已经开发完成、通过现有测试、对 First Launch 或 V0 有复用价值的能力应保留，包括但不限于：

- 严格公共市场数据解析；
- 因果 snapshot；
- rolling composites；
- volatility overlay；
- ContextSeries；
- 外部风险配置；
- TradePlan V2/V3 兼容；
- operator card；
- shadow journal；
- decision/outcome/MFE/MAE；
- pilot review；
- existing contracts、schemas、fixtures、CI 和治理测试。

### 3.2 停止扩张

以下情形不应继续扩大 First Launch：

- 为了对抗拥有本地文件写权限并可一致重算所有无密钥 hash 的攻击者，继续扩展完整历史对象重建；
- 为非资金写入的公共只读试点建立机构级审计系统；
- 为未来多策略、自动下单或 Dashboard 提前建立通用平台；
- 因低风险显示字段或历史对象格式不统一而重构全部旧模块；
- 因“更加完美”而增加与当前真实交易辅助无直接关系的合同或测试矩阵。

### 3.3 延期而非删除

凡是未进入当前上线关键路径的能力，统一标记：

```text
DEFERRED
PRESERVED
UNSCHEDULED
POST-FIRST-LAUNCH REPLANNING INPUT
```

---

## 4. First Launch Gate A：技术上线门禁

Gate A 判断系统是否可以进入 restricted public `LIVE_SHADOW`。它不判断策略长期收益。

### 4.1 数据与因果性

必须满足：

- ETH only；
- Hyperliquid public endpoints only；
- 仅已闭合 K 线具有策略权威；
- 5m 至少 64 根连续闭合 K 线；
- 15m 至少 20 根连续闭合 K 线；
- rolling 15m/30m/60m 仅由连续闭合 5m 数据确定性生成；
- future close、future receipt、future context 和 future metadata 不得影响更早决策；
- GAP、STALE、CONFLICT、malformed、disconnect 时 fail closed；
- warm-up、重连或重启后，READY 之前不得发出 actionable signal。

### 4.2 策略与生命周期

必须满足：

- base strategy 的 WAIT/WATCH 不得被 overlay 升级为交易；
- LOW 没有 longer-window support 时，FAST 和后续 STANDARD 均不得错误变为 actionable；
- NORMAL/HIGH 使用产品规定的权威决策跨度；
- EXTREME 不产生正常 actionable trigger；
- FAST、STANDARD、PREPARE、EXPIRED、INVALIDATED 转换确定；
- 已过期 signal 不得创建新 TradePlan；
- 同一 authority 不重复发出可执行信号；
- restart/reconnect 不得重复通知或恢复失效计划。

### 4.3 TradePlan 与资金风险字段

以下字段属于 First Launch 不可延期的核心字段：

- strategy/version；
- setup identity；
- side；
- trigger；
- reference；
- entry range；
- planned entry；
- chase limit；
- stop；
- TP1；
- TP2；
- quantity；
- notional；
- account equity；
- risk percentage/risk budget；
- max notional；
- expiry；
- Signal ID；
- Plan ID；
- `manual_execution_required = true`；
- `submission_status = NOT_SUBMITTED`。

必须满足：

- LONG/SHORT 几何方向正确；
- entry、stop、TP 和 chase 的方向性 rounding 不增加风险；
- HIGH regime 的 chase 和 risk reduction 规则确定且可重算；
- 数量、名义仓位和 planned risk 可重复、不过限；
- 配置错误 fail closed；
- 配置更新只影响后续计划；
- 已生成 TradePlan 保持不可变。

### 4.4 运行与通知

必须满足：

- real public HTTP/WS composition 可运行；
- snapshot warm-up 与 subscription acknowledgement 正确；
- bounded reconnect/recovery；
- signal de-duplication；
- restart-safe duplicate prevention；
- 单实例保护；
- 最小 signal/notification log；
- 一个可靠即时通知渠道；
- start/stop/error/restart runbook；
- health 和 failure notification；
- 单 AWS 实例部署；
- supervised public-read-only smoke run；
- 无账户、凭据、签名、nonce、订单或交易所写入。

### 4.5 最小记录闭环

至少记录：

- Signal；
- TradePlan；
- Shadow Order；
- TAKEN / SKIPPED / EXPIRED；
- 用户跳过理由；
- 人工实际入场、出场、手续费和滑点；
- MFE / MAE；
- stop/TP 路径；
- signal-to-view、view-to-order、signal-to-order 延迟。

---

## 5. PR #36 与后续 Review 的优化标准

### 5.1 当前 Review 目标

PR #36 的 Review 应判断当前 exact head 是否满足 Gate A，而不是判断它是否已成为机构级审计平台。

旧 repaired-head 报告仍可作为攻击清单，但每次必须对当前 GitHub exact head 重新核验，不得把旧 SHA 的结论自动带到新 head。

### 5.2 上线阻塞项

以下任何问题仍是 blocker：

1. 未来数据或错误 source authority 影响信号；
2. LOW/EXTREME/expiry/lifecycle 产生错误 actionable signal；
3. entry、stop、TP、chase、quantity 或 risk 错误；
4. 配置失败后静默使用旧值或硬编码值；
5. stale/restart/reconnect 导致重复、复活或漏通知；
6. public runtime 无法稳定组合；
7. 记录失败破坏核心运行或计划关联；
8. 出现账户、私钥、签名、nonce、交易所写入或自动 SL/TP；
9. exact-head tests/CI 失败；
10. 真实核心字段无法在 Outcome/DecisionBundle 中对应回原 Signal/TradePlan。

### 5.3 可修复但必须控制范围

以下问题只在影响核心交易字段或真实运行时阻塞：

- Signal ID / Plan ID 的核心字段对应；
- serialized plan 的入场、止损、止盈、数量和风险重算；
- Decision/Outcome 与 TradePlan 的关联；
- V2/V3 真实兼容回归；
- 关键 negative/boundary tests 缺失。

Repair 只允许修复已接受的 Gate A blocker。不得在 Repair 中启动新的审计平台或新产品能力。

### 5.4 延期到 V0 或后续

不再阻塞 First Launch：

- 对全部 provenance 非交易字段进行完整独立重建；
- 对所有 context/overlay 历史 payload 进行攻击者级取证；
- 抵抗本地恶意写入者一致重写全部记录与 hash；
- 完整历史 replay 平台；
- 全量场景和 incident library；
- 统计显著性、PBO/DSR、完整消融；
- 完整 Dashboard 和审计级持久化；
- 多策略选择；
- 自动执行；
- BTC/ETHBTC；
- L2/trades/OFI/CVD；
- 在线 AI 权威决策。

---

## 6. First Launch Gate B：上线后产品证据

Gate B 在真实 `LIVE_SHADOW + HUMAN MANUAL EXECUTION` 中判断产品价值。

`SYSTEM_VALIDATED != STRATEGY_PROFITABILITY_VALIDATED`

允许上线时：

- `STRATEGY_CORRECTNESS = PASS`
- `STRATEGY_EVIDENCE = INSUFFICIENT`
- `STRATEGY_PRODUCT_FIT = UNKNOWN`
- `PRODUCTION_AUTHORITY = NOT_GRANTED`

### 6.1 信号质量

记录：

- actionable signals；
- human accepted/rejected/skipped；
- reject/skip reason；
- win rate；
- average win / average loss；
- fee- and slippage-adjusted expectancy；
- MFE / MAE；
- max consecutive losses；
- FAST / STANDARD 分层；
- LOW/NORMAL/HIGH 分层；
- session 和 regime 分层；
- 信号是否及时、清楚、可执行。

### 6.2 人工执行损失

每个 actionable signal 记录：

- signal time；
- notification received/viewed time；
- order preparation time；
- actual order submission time；
- planned entry；
- actual entry；
- chase limit；
- 是否完全错过；
- 是否因人工延迟获得更差价格；
- 延迟造成的 R 值损失；
- 手工输入错误；
- 是否本可通过确认执行链捕获。

定义：

```text
MANUAL_EXECUTION_GAP
= 因人工延迟、操作或犹豫而错过/显著恶化的有效信号
÷ 全部 actionable signals
```

### 6.3 策略覆盖缺口

用户人工发现、但系统未发出信号的机会，记录：

- market regime；
- session；
- price structure；
- candidate strategy family；
- ideal entry；
- invalidation；
- MFE / MAE；
- 当前策略未覆盖原因；
- 是否属于另一个明确 regime；
- 是否值得形成互补策略。

定义：

```text
REGIME_COVERAGE_GAP
= 人工识别但当前产品策略未覆盖的有效机会
÷ 全部人工识别的有效机会
```

### 6.4 系统质量

记录：

- valid runtime hours；
- data gaps；
- reconnects；
- stale periods；
- duplicate prevention；
- notification latency；
- session failures；
- restart recovery；
- zero-signal periods；
- WAIT/WATCH/PREPARE 数量；
- near-miss 和 boundary interactions。

---

## 7. 上线后“更多策略 vs 用户确认执行”的决策规则

当前不提前固定优先级。

### 7.1 自动执行/用户确认执行优先的条件

倾向优先开发执行链，当：

- 当前信号质量高；
- fee/slippage-adjusted expectancy 有价值；
- 人工判断大多数认可信号；
- 信号经常因速度、追价或操作延迟错过；
- `MANUAL_EXECUTION_GAP` 高；
- 流动性清扫、快速回收等信号的有效窗口很短；
- 现有机会覆盖已经足够，主要瓶颈是兑现率。

### 7.2 互补策略优先的条件

倾向优先增加策略，当：

- 当前信号质量或 expectancy 不足；
- 信号频率过低；
- 当前策略只能覆盖少数 regime；
- 人工执行延迟不显著；
- 大量有效机会属于当前策略之外；
- `REGIME_COVERAGE_GAP` 高；
- 当前信号本身需要重新设计或增加互补逻辑。

### 7.3 并行两个 Lane 的条件

倾向并行，当：

- 当前策略已经证明部分有效；
- `MANUAL_EXECUTION_GAP` 和 `REGIME_COVERAGE_GAP` 同时显著；
- 工程上可保持文件、权限和 Writer lane 隔离；
- 具备一个 Integration Lane；
- 不降低资金安全和 Review 独立性。

### 7.4 暂不扩展的条件

当信号质量、机会覆盖和人工执行损失均未形成足够证据时：

- 继续运行 First Launch；
- 改善记录质量；
- 不因少量个案仓促启动自动下单或新策略；
- 不以工程开发时间单独决定产品优先级。

最终优先级由用户在 Post-First-Launch Product Replanning Gate 决定。

---

## 8. 当前工作顺序

```text
1. 当前 PR #36 exact-head 独立 Review
2. 仅修复 Gate A blocker
3. 完成 restricted public runtime composition
4. 完成通知、最小持久化和去重
5. AWS restricted pilot acceptance
6. supervised LIVE_SHADOW smoke
7. First Launch 上线
8. Gate B 真实数据采集
9. Post-First-Launch Product Replanning Gate
10. 用户决定更多策略、用户确认执行、并行或其他方案
```

不得因为以下工作推迟 First Launch：

- V0 详细设计；
- 第三个策略；
- 自动下单架构；
- Dashboard；
- L2/OFI/CVD；
- 完整回测平台；
- 完整审计平台；
- 大型工程自动化或多 Agent 平台。

---

## 9. 延期能力登记

以下全部保留但不激活：

- 第二及更多互补策略；
- 多策略冲突与选择；
- BBO、Order Preview；
- account read；
- user-confirmed Testnet/Mainnet submission；
- automatic protective SL/TP；
- cancellation/recovery；
- signal/decision/order/fill closure；
- shadow-to-real matching；
- 完整 Outcome/Pilot automation；
- continuous historical replay；
- complete backtesting；
- reports/dashboard；
- audit-grade persistence；
- BTC/ETHBTC；
- L2/trades/OFI/CVD；
- broader liquidation/session/macro/news/flow context；
- non-authoritative AI explanation/research/review；
- advanced automation、HA、disaster recovery；
- V0/mainline broader foundation。

延期不代表取消，也不代表已经获得下一阶段优先级。

---

## 10. 角色与同步边界

### 10.1 策略研究窗口

负责：

- 策略定义；
- regime 与市场行为；
- 信号频率；
- near-miss；
- coverage gap；
- expectancy；
- 新策略候选；
- 参数、假设和失效条件研究。

不得：

- 自行修改生产代码；
- 自行改变产品 scope；
- 自行激活新策略；
- 自行授予账户或交易权限。

策略研究结论作为 Product Function and Priority Control 的输入。

### 10.2 Product Function and Priority Control

唯一决定：

- 为什么开发；
- 开发什么；
- 当前、延期、取消、恢复或替代哪些能力；
- 策略和数据的产品价值；
- 产品优先级；
- First Launch acceptance；
- Post-First-Launch 下一产品配置。

### 10.3 Engineering Optimization

唯一决定：

- 如何实现已接受产品决定；
- Package 边界；
- Writer/Reviewer/Agent/Harness 路由；
- 测试、Review、Repair、Evidence 和 preflight；
- 并行、自动化、速度与质量平衡。

不得重定义产品 scope 或替用户选择下一产品能力。

### 10.4 Project Control

负责：

- exact GitHub state；
- Task Contract；
- branch/worktree/allowlist；
- Write Lease；
- Writer/Reviewer/Finalizer 调度；
- PR、CI、Repair、merge、refreeze；
- 权限和项目状态一致性。

不得推断产品或工程未决事项。

### 10.5 冲突解决

优先级：

```text
最新明确用户裁决
→ Product Function and Priority Control 对产品的裁决
→ Engineering Optimization 对工程实现的裁决
→ Project Control 对执行对象的冻结
→ Writer / Reviewer 的任务内证据
```

GitHub exact object 优先于过时的 PR body、旧提示词和旧窗口状态。

---

## 11. 当前 GitHub 同步快照

同步前只读核验：

- `main = 8be9922e7e70fa1b2738994c2f31c2c87e866cb2`
- PR #33：Open / Draft / Not merged  
  head `5db8074b2303bdc45b9071ec31b929385fa9b9f4`
- PR #35：Open / Draft / Not merged  
  同步前 head `c37ef84cfbe7a45a1eb28298b55fbb73aab5a9c0`
- PR #36：Open / Draft / Not merged  
  核验时 head `66039a347ca54565a9f9e2f26dc8895939313a32`

PR #36 head 可能继续变化。任何 Review 或 Repair 必须重新查询当前 exact head。

本记录同步到 PR #35 文档分支，不修改：

- `main`；
- PR #33；
- PR #36；
- 产品代码；
- tests；
- CI；
- runtime authority；
- trading authority。

---

# Appendix A — 工程优化窗口提示词

```text
ROLE:
ENGINEERING_OPTIMIZATION_AUTHORITY

MODE:
FIRST_LAUNCH_SCOPE_OPTIMIZATION_AND_FINAL_CRITICAL_PATH_ALIGNMENT

REPOSITORY:
woshixiong/trader-assist-v0

PERMISSION:
STRICT_READ_ONLY

SOURCE_AUTHORITY:
Latest explicit user ruling and:
governance/FIRST_LAUNCH_SCOPE_OPTIMIZATION_AND_POST_LAUNCH_DECISION_GATE_2026-07-20.md
on the current PR #35 documentation branch.

PURPOSE:
Align the remaining First Launch engineering path with the newly approved
minimum-usable, proportionate-reliability scope.

Do not modify GitHub.
Do not create a branch.
Do not issue a Write Lease.
Do not activate P3B/P4.
Do not Mark Ready or merge.
Do not redefine product scope.
Do not select post-launch strategy expansion or user-confirmed execution.
Do not authorize account, signing, Testnet/Mainnet, orders, cancellation or SL/TP.

FIRST ACTION:
Verify current exact GitHub state rather than trusting embedded SHAs:

- main;
- PR #33;
- PR #35;
- PR #36 current exact head, commits, files, CI and Review status.

PRODUCT DECISIONS TO ABSORB:

1. Concentrate all current effort on completing and launching First Launch.
2. Preserve completed/reusable code; do not simplify by deletion.
3. Stop expanding unfinished capabilities that do not affect First Launch.
4. Defer non-blocking work and register it for post-launch replanning.
5. Gate A is technical launch readiness.
6. Gate B is post-launch product evidence.
7. First Launch may launch with STRATEGY_EVIDENCE=INSUFFICIENT and
   STRATEGY_PRODUCT_FIT=UNKNOWN if correctness and technical gates pass.
8. Current PR #36 Review must judge Gate A, not institutional-grade audit completeness.
9. Core signal, entry, chase, stop, TP, quantity, risk, expiry and identity
   correspondence remain mandatory.
10. Complete attacker-grade reconstruction of all historical provenance,
    context and overlay objects is deferred unless it directly affects core
    trading fields or real runtime correctness.
11. More strategies versus user-confirmed execution remains undecided until
    real First Launch evidence exists.
12. The post-launch decision must use signal quality/expectancy,
    MANUAL_EXECUTION_GAP and REGIME_COVERAGE_GAP.

REQUIRED ENGINEERING ANALYSIS:

A. VERIFIED_CURRENT_STATE
- exact main;
- PR #33/#35/#36 state;
- current PR #36 exact head;
- drift classification.

B. CURRENT_P3A_DISPOSITION
- map prior and current findings to Gate A;
- identify only true launch blockers;
- identify non-blocking hardening;
- identify deferred audit enhancements;
- determine whether current PR #36 requires another repair, exact-head Review,
  or safe stop;
- do not rely on old repaired-head conclusions.

C. PROPORTIONATE_REVIEW_POLICY
Freeze:
- blocker definitions;
- core financial/strategy fields;
- negative/boundary tests;
- accepted one-pass attack matrix;
- maximum repair boundary;
- stop condition preventing further scope expansion.

D. REMAINING_FIRST_LAUNCH_CRITICAL_PATH
Recommend the shortest reliable sequence from current state to:
- P3A closure;
- restricted public runtime composition;
- notification/de-duplication/minimal persistence;
- AWS pilot acceptance;
- supervised LIVE_SHADOW smoke;
- launch.

E. PACKAGE IMPACT
State whether the accepted top-level P3A/P3B/P4 structure remains efficient.
Do not create a competing product plan.
Only recommend a change if current exact code evidence proves the structure
would delay launch or mix incompatible authority.

F. WRITER/REVIEW ROUTING
- one product Writer;
- one final exact-head Reviewer;
- 0–2 read-only auxiliary lanes;
- one consolidated findings set;
- 0–1 bounded repair commit where feasible;
- no overlapping Writers.

G. DEFERRED_LEDGER
Return a concrete list marked:
DEFERRED / PRESERVED / UNSCHEDULED / POST-FIRST-LAUNCH REPLANNING INPUT.

H. PROJECT_CONTROL_HANDOFF
Produce one concise, copy-ready handoff containing:
- actual current state;
- next exact authorized action;
- required Task Contract adjustment;
- Gate A acceptance;
- engineering blockers;
- non-blocking recommendations;
- prohibitions.

OUTPUT TITLE:
ENGINEERING_OPTIMIZATION_FIRST_LAUNCH_SCOPE_OPTIMIZATION_RULING

The ruling is advisory and read-only.
It must not modify or activate anything.
```

---

# Appendix B — 产品功能规划窗口提示词

```text
ROLE:
PRODUCT_FUNCTION_AND_PRIORITY_CONTROL

MODE:
FIRST_LAUNCH_SCOPE_OPTIMIZATION_PRODUCT_ALIGNMENT

REPOSITORY:
woshixiong/trader-assist-v0

PERMISSION:
STRICT_READ_ONLY

SOURCE:
Latest explicit user decision and:
governance/FIRST_LAUNCH_SCOPE_OPTIMIZATION_AND_POST_LAUNCH_DECISION_GATE_2026-07-20.md
on the current PR #35 documentation branch.

PURPOSE:
Review and align the authoritative First Launch product scope, launch
acceptance and post-launch replanning gate with the user's latest decisions.

Do not modify GitHub.
Do not create or update a PR.
Do not activate a Package.
Do not issue a Write Lease.
Do not Mark Ready or merge.
Do not choose an engineering implementation.
Do not authorize account access, signing, Testnet/Mainnet exchange write,
order submission, cancellation or automatic SL/TP.
Do not freeze a detailed V0 plan.

FIRST ACTION:
Verify through GitHub:

- current main;
- PR #33;
- PR #35 current exact head and files;
- PR #36 current exact head and state.

LATEST USER PRODUCT RULING:

1. Finish and launch First Launch before detailed V0 planning.
2. First Launch is a minimum-usable validation system, not an institutional-grade platform.
3. Preserve completed and reusable capability.
4. Do not expand unfinished non-critical capability.
5. Defer work that does not affect First Launch correctness, risk, runtime or authority.
6. Gate A is technical launch readiness.
7. Gate B is real operation evidence.
8. Entry, chase, stop, TP, quantity, risk and expiry are mandatory.
9. Full attacker-grade historical reconstruction is not a First Launch blocker
   unless it affects core trading fields or runtime correctness.
10. More strategies versus user-confirmed execution must be decided after
    First Launch using real evidence.
11. If signals are accurate and valuable but manual execution loses many
    opportunities, prioritize user-confirmed execution.
12. If signal quality/expectancy or regime coverage is weak and manual delay is
    not material, prioritize complementary strategies.
13. If both gaps are high and engineering isolation is feasible, parallel lanes
    may be considered later.
14. The user will make the final post-launch priority decision.
15. Strategy research remains a product input; product priority remains owned
    by this window.

REQUIRED OUTPUT:

A. VERIFIED_CURRENT_STATE
- exact GitHub objects;
- identify stale document or PR narrative.

B. PRODUCT_ALIGNMENT
Confirm or challenge, with exact reasons:
- First Launch objective;
- one product strategy core;
- Gate A;
- Gate B;
- minimum records;
- proportional reliability;
- deferred capability policy.

C. CONFLICT_MATRIX
Compare the new record with:
- existing Signal-First Baseline;
- Deferred Capability Registry;
- Verification Protocol V1.1;
- any current PR #35 wording.
Classify:
- compatible;
- superseded;
- needs wording correction;
- unresolved product decision.

D. FIRST_LAUNCH_FINAL_SCOPE
Return a concise authoritative product scope:
- included;
- excluded;
- must retain;
- launch blockers;
- post-launch evidence;
- acceptance state.

E. POST_LAUNCH_REPLANNING_GATE
Freeze only the decision method, not the outcome:
- signal quality/expectancy;
- MANUAL_EXECUTION_GAP;
- REGIME_COVERAGE_GAP;
- system reliability;
- sample sufficiency;
- user final decision.

F. DEFERRED_LEDGER
Confirm every removed capability remains:
DEFERRED / PRESERVED / UNSCHEDULED
unless explicitly cancelled by the user.

G. GITHUB_DOCUMENTATION_RULING
State:
- whether the new PR #35 document accurately records the product decision;
- whether existing PR #35 baseline/registry require later textual edits;
- whether PR #35 should remain Draft;
- the correct checkpoint for independent documentation Review and merge.
Do not perform those changes.

H. ENGINEERING_HANDOFF
Provide a concise product-only handoff for Engineering Optimization:
- fixed product scope;
- Gate A blockers;
- Gate B evidence requirements;
- product prohibitions;
- unresolved items, if any.

OUTPUT TITLE:
PRODUCT_FUNCTION_FIRST_LAUNCH_SCOPE_OPTIMIZATION_RULING

This is a product ruling only.
It must not design packages, route Agents or execute GitHub work.
```

---

## 12. Authority boundary

本记录不授权：

- PR #36 Mark Ready 或 merge；
- PR #35 Mark Ready 或 merge；
- runtime activation；
- AWS deployment；
- account read；
- wallet/private key/signing/nonce；
- Testnet/Mainnet exchange write；
- order submission/cancellation；
- automatic SL/TP；
- BTC/ETHBTC；
- new strategy activation；
- V0 activation；
- AI authoritative trading；
- production parameter automatic mutation。

任何上述权限仍需独立、明确的用户授权。
