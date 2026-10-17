# 可量化研究候选：Brooks / Louie Price Action × Three Setup

**包**：`PA_BROOKS_LOUIE_LIBRARY_20261016` · **版本**：`PA_QUANT_CANDIDATES_V0_20261016` · **级别**：`RESEARCH_ONLY / UNVALIDATED / NO_EXECUTION`。  
**目的**：在不改变已批准的 Three Setup 方向权威下，将价格行为学转换为可复验的上下文、入场、停损及退出假设；判断能否提高税费前后尤其**扣全部摩擦后**的 Thesis 期望值。

## 0. 继承边界：增量验证而非再建体系

```text
EXISTING_THREE_SETUP = SWEEP_RECLAIM | BREAKOUT_RETEST(MICRO_FAST,STANDARD) | RANGE_EDGE_REJECTION
THREE_SETUP = WHAT / WHERE / SIDE
BROOKS_CONTEXT = STATE + LOCATION + QUALITY + FOLLOW_THROUGH
BROOKS_CHALLENGER = ENTRY_TIMING | WAIT/PASS | ATTEMPT_STOP | WINNER_EXIT
ORDER_SIDE_FROM_BROOKS_ALONE=PROHIBITED_ON_ACTIVE_STRATEGY_LANE
UNAUTHORISED_FOURTH_SETUP=NO
LIVE/EXCHANGE_WRITE=NO
```

各项属于独立候选模块，不是把 Q1~Q8 同时接上一个历史盈利最好的“超级策略”。同一 Opportunity 在可因果重建情况下做**成对对照**，每个实验只改一个维度。映射参照 #161、#150、#85、现有 [TA_VNEXT_E4_C1](../TA_VNEXT_E4_C1_STRATEGY_SPEC_2026-09-11.md)。静态价格行为概念可做离线纯机制研究，但不直接获取下单方向。

## 1. 共同定义（所有候选先冻结再跑）

### 1.1 时间与输入

- 基础：**完成并因果接纳后的** 5m bar（结构）、1m bar（时机），有执行级结论时需 BBO、TradeTick、instrument specification、时段/事件、费率、可用量与质量状态。
- 任何 K 线的 `close/high/low` 在完成/接纳前不可提前用作最终值；未收 5m 的形态另标 `EARLY_PARTIAL_5M`。1m pivot 的左右确认须延后至右侧 bar 完成，沿用既有研究合同，不以事后确认点提前触发。
- `t_event, t_received/t_init, t_bar_closed, t_admitted, t_decision, t_order_active, t_fill` 必须区分；触发时间早于行情可获知时间算 LOOKAHEAD。
- 界面可视状态仅是观察，不是 Order Fill。市价买按 ask、卖按 bid（平多 bid、平空 ask）；maker 需要队列/未成交/部分成交假设。日内冻结 session/calendar/timezone。
- 数据缺失、报价过期、冲突、极端跳点、无历史开盘定义时为 `NOT_EVALUABLE / BLOCKED` 或 `UNKNOWN`，不能自动归入亏损或经济 PASS。

### 1.2 可量化原子特征（**参数都是未冻结候选，不是已验证阈值**）

| 因子 | 因果定义（多头示例，空头镜像） | 需要冻结的边界 |
|---|---|---|
| `body_ratio` | `abs(close-open)/(high-low)`，零区间标 missing | “强实体”的下界 |
| `close_location` | `(close-low)/(high-low)` | “收近最高”的下界 |
| `lower_wick_ratio` | `(min(open,close)-low)/(high-low)` | 长影线界值 |
| `bar_overlap` | 当前完成 K 与前一 K 交集长度 / 价格区间并集长度 | 震荡/强趋势阈值 |
| `dir_efficiency_N` | `abs(close_t-close_t-N)/sum(abs(close_i-close_i-1))` | 回看 N、强弱分位 |
| `level_break` | 行情实际跨越 **事前冻结** 的上沿/前高等 | level 来源、tick buffer |
| `reclaim` | 跨出 level 后完成 K 收盘重新回到 level 内侧 | 事件最大等待时间 |
| `followthrough` | 信号后的下一 **已完成** K 收在突破方向、继续建立方向极值等 | K 数、最小推进；用于 **后续决策**，不可回填到先前入场 |
| `retest` | 突破后回到之前冻结的 level 容差区，随后新激活 | tick/ATR 容差、过期 |
| `two_entry_state` | 在同一有效 Thesis/回调内，第一次明确触发失败或不足；再次出现**新**合法信号和价位；每次尝试标独立 ID | “first/second”的切分与重置 |
| `climax/wedge` | 事前可见的三推、加速度变化、过度延伸 + 失败跟随的组合 | 推的因果确认、趋势线画法 |
| `no_followthrough` | 入场后指定秒/根数未达到因果有利进展或出现反向结构 | 期望进度和等待期 |

不要以画在完整历史图上的“漂亮趋势线”作为当时可知的输入；价位计算只允许回看已完成 bar 和已确认枢轴，不允许使用右侧未来结果。

### 1.3 统一结果单位

`MarketEvent -> Opportunity -> Thesis -> Attempt(1|2) -> OrderIntent -> Simulated Fill -> Outcome`。一级评估为 **Thesis**；同时保留 `TAKE/WAIT/PASS/BLOCKED` 及 `NOT_EVALUABLE`，对同一机会的错过赢家/省掉摩擦进行追踪。基线的开仓侧、时间戳和原始规则须锁定。

## 2. 候选清单

| ID | 名称 | 唯一改动 | 现有 Setup / 层次 | 优先 |
|---|---|---|---|---|
| **Q0** | Champion 原始对照 | 当前已冻结 5m Three Setup + 原入场/出场，及已存在的用户 A/B/C 影线研究对照 | Base | P0 |
| **Q1** | 市场状态过滤 | 用趋势/宽通道/区间标签调整 `TAKE/WAIT/PASS` | 三者共享 / Context | P0 |
| **Q2** | 假突破回收+1m力度 | 只比较回收到关键位内后的信号/确认是否更可靠 | `SWEEP_RECLAIM`, `RANGE_EDGE_REJECTION` / Entry | P0 |
| **Q3** | H2/L2 与二次反转 | 比较 first-entry 与 **fresh** second-entry 的收益和追价损失 | 三者适用时 / Entry、Re-entry | P1 |
| **Q4** | 突破跟随与回测 | 直接突破 vs 先看跟随 vs 回测再加速 | `BREAKOUT_RETEST` / WAIT、Entry | P0 |
| **Q5** | 楔形/加速失败/高潮 | 在宽通道极端处，检验延续或反转风险标签 | 三者的 context 或 isolated offline only | P2 |
| **Q6** | 无跟随提前退出 | 相同入场，仅在 Attempt 中新增 **causal no-progress** 退出 | Machine Position AP3/AP4 | P1 |
| **Q7** | 波段 vs 剥头皮动态管理 | 相同入场和确认，按后续趋势/重叠证据选择 X0~X3 子策略对照 | Winner Exit | P1 |
| **Q8** | 开盘反转上下文 | 开盘首波/假突破/反向 1m，作为已有 Setup 的参与过滤 | 开盘 Context（非新 Setup） | P2 |

### Q0：唯一可信对照

- 对比目标必须绑定已批准的 Champion 版本和执行费率/填单假设。不能将 Louie 实盘交易结果冒充我们的基线。
- 同一事件上保留 A/B/C 原有分层，且 early pre-close 与 close-confirmed 作为不同 Variant。
- 原始 A/B/C 定义不得为了匹配 Brooks 结果而更改；若改变定义必须重新版本化。

### Q1：`PA_REGIME_SELECTIVITY`

- **假设**：趋势阶段顺势信号的有效性、区间边缘假突破反向信号的有效性，优于各阶段无差别参与。
- **特征**：已完成 5m 的重叠比例、方向效率、EMA20 倾斜/位置（可选）、高低点序列、通道宽度；预先冻结 `TREND_STRONG / CHANNEL_BROAD / RANGE / UNKNOWN` 判定，允许 UNKNOWN 阻断或等待。
- **变动**：不改变方向或触发；只比较原本可交易的同一 Three Setup 在可评估的不同 state 下的参与/放弃。
- **对照**：Q0 无环境过滤 vs Q1 regime filter；分别评估被过滤的赢家机会成本与虚假信号减少量。
- **否证**：经过配对成本/OOS 测试，环境过滤带来的 missed-winner 或低覆盖使净期望下降。

### Q2：`PA_FAILED_BREAKOUT_WICK_CONFIRMATION`

- **假设**：在**事前已知**的区间边缘/前高低附近，刺破→收回→可信反向 1m 跟随，能改善假突破反转的入场质量。
- **事件链**：`KNOWN_LEVEL -> TOUCH/CROSS -> RECLAIM_BAR_CLOSE -> REVERSAL_SIGNAL -> ACTIVATION`。可选择“5m已收线确认”和“未收5m/1m预触发”，**必须分版本**。
- **与原 A/B/C**：A/B/C 不动；添加 `LEVEL_RECLAIM` 和 `FOLLOWTHROUGH` 标注，以配对分析是否真正增加边际价值。
- **无效/误判**：价位基于未来高低点、返回前区间后又被强势二次突破、没有执行可得价。
- **对照**：原 A/B/C、已批准 Three Setup vs 加“已回收”或“后续跟随”过滤。
- **否证**：确认导致追价/迟到，失去主要赢家或 after-cost 价值为零。

### Q3：`PA_SECOND_ENTRY_H2_L2`

- **两个不同模式不得混淆**：① 顺势回调 H1→H2（上涨市场第二次买入信号；下跌镜像 L2）；② 大反转里的第一次/第二次独立反向尝试。分别登记子型 `TREND_SECOND_PULLBACK` 与 `REVERSAL_SECOND_ATTEMPT`。
- **因果状态**：`THESIS_ACTIVE -> FIRST_SIGNAL_KNOWN -> FIRST_TRIGGERED_OR_EXPIRED -> NEW_PULLBACK_OR_FAILED_ATTEMPT -> FRESH_SECOND_SIGNAL_KNOWN -> SECOND_TRIGGER`。
- 每个 `SECOND` 必须具备新的完成 K、区分开的价位触发和有效失效点，不能只是旧价二次跳动；同一 Thesis 不因为第一次出场就自动失效。
- **对照**：第一次入场、第二次入场、只等待第二次（漏掉强趋势赢家风险）及无 re-entry；同时看净 R 与信号频率。
- **否证**：样本不足，或第二次确认提高胜率却降低总净盈利、增加追价/费用。
- **当前 C1 限制**：只研究 initial + 一次 fresh re-entry；Attempt 3+ 和无证据的逆向加仓都不进入优先实验。

### Q4：`PA_BREAKOUT_FOLLOWTHROUGH_RETEST`

- **前提**：三大 Setup 的 `BREAKOUT_RETEST` 已提供方向与结构；突破发生前固定上下界。
- **Variant**：B0=既有 Entry；B1=突破立即激活（对应已有 EA1）；B2=WAIT 确认后再参与（若跟随确认被用作触发，则入场时间必须是其完成之后）；B3=回测再加速（对应 EA2），必要时在已有 EA3 上研究增量 flow×price response。
- **强弱**：突破实体位置 + 随后已完成 K 的方向延伸与重叠 / 返回区间；不以“视频说会有第二段”作为必然。
- **否证**：B2/B3 因延迟与成本反而低于基线或漏掉最赚钱的 runaway winner。

### Q5：`PA_WEDGE_CLIMAX_ACCEL_FAIL`（机制研究先行）

- **假设**：宽通道里的第三推/加速突破后未跟随，可以给出 trend deterioration / 反向风险提示。
- **数据**：已确认的三个局部推点、走势方向、幅度/间隔、相对通道边缘和接下来可见的失效信号；通道线必须因果绘制，避免主观补线。
- **用途**：原 Three Setup 的上下文或已有 Winner exit 风险提示；独立做空/做多只是隔离研究，不构成第四 Setup。
- **否证**：在真实强趋势的高潮阶段频繁错误预警，牺牲右尾大赢家。
- **门槛**：只有 Q1/Q2/Q4 的简单增量价值不足、并且有充足可评估的点位/路径时才打开。

### Q6：`PA_ATTEMPT_NO_FOLLOWTHROUGH`

- **进入条件**：与 Champion 完全相同的 Attempt 入场；硬保护性止损不变，新增“当时可观察的不利证据”提前退出竞争方案。
- **比较**：AP0/结构、AP3/时间无跟随（沿用已存在的 30/60/90/120/180 秒研究网格，300 秒诊断）、AP4 价格+时间；不另外造一个停止器。
- **后验陷阱**：不能“任意浮亏就卖”或只删除历史亏单。没有首次有利进展时也可能随后成为赢家，须计入 `FALSE_SCRATCH`、恢复成本、Re-entry 限额、被错过的右尾。
- **否证**：提前退出带来更多总成本或把高 R 得主切掉，Thesis 净值变差。

### Q7：`PA_REGIME_DEPENDENT_WINNER_EXIT`

- **假设**：有强跟随的赢家宜保留右尾，重叠/无进展的赢家不该强制同一波段目标。
- **对照**：已有 `X0` 固定 R、`X1` 因果结构离场、`X2` MFE giveback、`X3` 结构 ratchet + giveback。仅把当时可知的 regime/followthrough 作为 **退出路由候选**。
- **保护**：与原设计一致，`PROBE_UNCONFIRMED` 和 `WINNER_CONFIRMED` 分离，micro 反转不自动结束已确认的大赢家；硬止损及 Thesis 失效始终有权威。
- **指标**：`MFE_CAPTURE_RATIO`、`PROFIT_GIVEBACK`、`PROFIT_TO_LOSS_FLIP`、top-winner concentration、净 Thesis R。
- **否证**：动态路由复杂度上升但在 OOS/Forward 没有增量、或显著切掉右尾。

### Q8：`PA_OPEN_REVERSAL_CONTEXT`

- **问题**：韩/美开盘的前 2–3 分钟方向与开后首 1m 反向，有无超过基线、可执行且扣费后的优势？
- **观测**：开盘标签定义（NYSE/NASDAQ/KRX/具体 RWA 的真实交易时段/合约映射）、前期极值、首段区间、gap、逆向强实体、是否假突破、宏观事件、执行延迟与开盘价差。
- **对照**：原 setup vs 同一 setup + opening context；独立“首分钟反向”只做 OFFLINE_MECHANISM，不能赋予订单方向。
- **有偏样本警告**：股票现金市场开盘 != Hyperliquid 24/7 合约开盘，RWA 跳价、mark/index/oracle 机制、暂停/展期等都可能改变可执行性；对照样本应按时区/市场制度隔离。
- **目前人工限制**：不违反 Issue #171 最新有效的 NO-ENTRY 窗口，即使研究发现某些开盘窗口潜在盈利。
- **否证**：有概率偏差但跨品种不可交易、或滑点/点差吃掉净 edge、或开盘标签错位。

## 3. 试验结构与暂不做的事情

**推荐首轮小型因子梯**：

```text
Stage A: Q0 baseline, causal input/filled-path capability / cost integrity
Stage B: Q1 / Q2 / Q4 单因素成对消融（优先）
Stage C: Q3 第二次入场（多一次 Attempt 的成本敏感性）
Stage D: Q6 / Q7 出场策略（保持同一 Entry）
Stage E: Q8 / Q5 仅在收益/机制疑问仍显著时
```

- 每个 Challenger 在回测前冻结  `strategy_version / policy_version / parameter_version / derivation_version / data_contract / execution_model / fee_profile`，以及时间窗、否证条件与试验索引。现有 C1/验证规范里的网格优先复用；全新阈值只用**事前小网格**，不是不断网格搜索。
- 不合并多模块寻找历史最大 Sharpe；否则既不能归因，也会污染验证集。
- 每次变动必须单独记入试验/适应性台账；看过 OOS 结果后再修改，不得重复声称它是 untouched OOS。
- 没有实际可执行微观报价/交易路径，只能作 `MECHANISM_ONLY`，**不宣称** 1m/秒级小止损的真实期望。
- 不先建新数据服务、回放引擎、策略控制器或实盘下单链路；复用 NautilusTrader native BacktestNode/Parquet catalog/现有 Three-Setup evidence。
- 只有 G0~G5 的独立验证通过且另有授权，才有资格讨论更高级别的策略变更；本库本身不启动任何 Shadow。

## 4. 需保留的空白项

```text
EXACT_THRESHOLD_SELECTION = NOT_FROZEN_FOR_EXECUTION
OOS_GAIN = NOT_MEASURED
FORWARD_EDGE = UNPROVEN
RWA_TRANSFER_VALIDITY = UNKNOWN
FILL_REALISM_ON_TARGET_VENUE = UNKNOWN
TRIAL_COUNT_FOR_NEW_VARIANTS = 0_COMPLETED_IN_THIS_PACKAGE
RESEARCH_REQUESTS = SPEC_ONLY_NO_RUNTIME_CHANGE
```

证据、指标、场景与冻结规则详见 [EVIDENCE_AND_VALIDATION_PLAN](EVIDENCE_AND_VALIDATION_PLAN_V0_20261016.md)。
