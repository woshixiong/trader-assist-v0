# Brooks / Louie 公开证据与量化验证方案

**任务包**：`PA_BROOKS_LOUIE_LIBRARY_20261016` · **状态**：`DOCUMENTED_NOT_BACKTESTED`  
**证据分层**：`SOURCE_OBSERVED` 公开资料/字幕已核实概念；`AUTHOR_HEURISTIC` 主讲者经验或概率；`PROJECT_HYPOTHESIS` 按我们的交易目标导出的新实验；`MEASURED_PROJECT_EDGE` **暂无**。

## 1. 研究源和读取边界

**来源 A：Louie（方方土 PriceAction）公开视频**  
频道：[https://www.youtube.com/@louiepriceaction](https://www.youtube.com/@louiepriceaction)  
频道描述：自称 Al Brooks 课程中文翻译者，按主题课/边做边讲展示 ES、GC、CL、股票及选定加密相关案例。频道的“公开视频总数”会变化；**本包未完整逐条读取全部公开视频**，无权访问付费课程全文。链接和公开字幕只支持对具体主题的说明。

已参考的公开视频与研究焦点（链接指向作者原视频，**不复制字幕**）：

| 视频 | 研究焦点 | 证据可证明的范围 |
|---|---|---|
| [杜绝大亏的入场规则](https://www.youtube.com/watch?v=nFKiwGHqpsA) | 防止亏损加仓、首次逆势反转、第二次信号、保护性止损与重新入场 | 作者讲解/举例，不是已证实的策略胜率 |
| [突破专题 1：假突破](https://www.youtube.com/watch?v=152osf_ULas) | 趋势/区间惯性、真突破跟随、反转亦属突破、目标位 | 作者教学启发，不是 Hyperliquid 统计 |
| [早盘：突破失败后的反转](https://www.youtube.com/watch?v=QwnAatdZvWQ) | 开盘相对前日极值/区间、反转与突破模式 | ES 开盘的经验，不得照搬 RWA |
| [沪锡期货：波段转剥头皮](https://www.youtube.com/watch?v=5rDTfseBNMU) | 首段大阴线、糟糕跟随、动态保护、actual risk 与波段/剥头皮切换 | 单笔叙述，选择性展示风险 |
| [加速突破失败后的反转波段](https://www.youtube.com/watch?v=Cn6yAnTlke4) | 宽通道/楔形、反向二次运动、因果周期选择 | 作者单笔判断，不代表所有市场 |
| [如何建立优势 / 提前止损](https://www.youtube.com/watch?v=65vMspZElCg) | 费用/胜率/盈亏比关系，提前止损和交易理由失效 | 数学例子和案例，不是统一阈值 |
| [顺势交易：回调与数 K 线](https://www.youtube.com/watch?v=OBcf89c67GM) | 方向上下文、高一高二与低一低二 | 策略词汇和机制 |
| [震荡行情边做边讲](https://www.youtube.com/watch?v=1Im5C_y-LVo) | 区间双向、假突破、剥头皮 | 课堂交易案例 |

上述视频的中文/自动字幕存在语言变体和转写错误；精确 tick 规则、百分比与语义需对照原图和官方定义，不能把误识别词当权威公式。

**来源 B：Al Brooks 官方公开教育材料（非付费视频）**

- [价格行为官方教学手册](https://www.brookstradingcourse.com/how-to-trade-price-action-manual/)：先分趋势/通道/突破和区间，再依环境选择 stop/target。
- [官方术语词典](https://www.brookstradingcourse.com/price-action-trading-terms-glossary/)：breakout pullback、breakout test、bull flag、entry 等词汇。
- [官方公开 10 种 Price Action Pattern](https://www.brookstradingcourse.com/price-action/10-best-price-action-trading-patterns/)：opening reversal、wedge、双顶/双底等。
- [公开视频课程目录](https://www.brookstradingcourse.com/trade-forex-price-action/)：market cycle、breakouts、follow-through、second-leg traps 等课目。

**归因**：本包的手动清单和 Q0~Q8 分类是 Trade OS **重新组织和提出的假设**，不是 Brooks 或 Louie 发布的现成策略代码，也不暗示他们推荐我们的执行方式。视频中出现的“80/20”“40%/60%”“75%”“两段十根”等，是教学经验/背景限定的参考说法，**不得**作为 Universal Probability、未来收益保证、固定停止线或 Promotion 结果。

## 2. 项目独立判断和反证

- **问题**：目前人类影线 A/B/C 对 1m 反向力度敏感，但强趋势的第一次逆势影线容易误判；赢家持仓和提前退出缺乏统一、可检验的环境条件。
- **最简单可行路径**：保留 Three Setup；按 `STATE -> LEVEL -> TRIGGER -> INVALIDATION -> AFTER-COST ROOM` 加入**少量**可测因子，再检验同机会同成本的增量。
- **支持机制**：区间中边缘突破失败可能带来回归，强突破的跟随具有延续性；早期无进展可提供失败信息；二次入场可能改变胜率/空间折中。
- **主要反证**：动态 regime 误分类、强趋势少量第一次反转确实能抓大行情、等待第二信号损失最佳价格、1m 成交摩擦放大、确认型指标导致后验看似强、只在高波动单品种有效。
- **处置**：`INDEPENDENTLY_DERIVED_EXTERNALLY_MODIFIED`，但 **经济有效性=UNRESOLVED_REQUIRES_EXPERIMENT**。不采纳课程声称概率，不改基础设施。
- **成本/复杂度**：首选复用现有行情回放与日志；不可重建的微观数据一律标 `NOT_EVALUABLE`。优先 `PROCEED_WITH_CURRENT_BEST_AND_DEFER`，非必要 L2/新供应商 `PARK_OR_REJECT`；只有若缺项构成被允许的正式结论的硬门槛，才单独 `ACQUIRE_BEFORE_NEXT_GATE`。
- **中止进一步搜索**：简单基线若在可信 OOS/Forward 无改善，不增加更多信号/阈值；保留档案，等待新的独立证据。

## 3. 实验前的冻结 / 因果护栏

1. **声明** exact `data_manifest / PIT universe / market / venue / instrument spec / session timezone / fee state / feature code & timestamp / execution model / trial ledger`。
2. **Baseline** 当前 Three Setup 和已存在的 A/B/C、EA、AP、X 控制。变化的单一分量明确记录。不得用同一结果选择 Entry + Stop + Exit 的最佳组合。
3. **数据**：先优先使用合法免费、可核实的公开 OHLCV 做 **MECHANISM_ONLY**；1m/5m 可用于局部形态统计，但 **不足以** 声称 10~60 秒止损/先后触价、maker 填单或真实日内可执行净 PnL。需要后者时才使用已保存且符合授权的 BBO/trade 数据或保持结论未定。
4. **时间**：以当时已确认 bar、因果接纳事件、已知 session 作为唯一决策输入；跨市场前/后盘的财报/交易时段/合约定价状态分别版本化。
5. **执行**：买 ask / 卖 bid、真实有效费率（RWA maker/taker 随账号/市场/政策而变）、滑点/冲击、延迟、部分成交/未成交、重复尝试成本、持仓跨 funding 的费用。maker 只触价≠填单。
6. **样本**：保留所有 Opportunity，包括 WAIT、PASS、BLOCKED 和 `NOT_EVALUABLE`。集群按同事件/时段/主题、存储股相关性分组，不把 SKHX/MU/SNDK 的同一冲击当 3 个独立市场事件。
7. **分段**：先 dev -> 验证 -> untouched chronological OOS；训练标签重叠时 purge/embargo；后续仅在 exact frozen candidate 上收集 Forward。封存的数据 Reserve 不得拿来做优化筛选。
8. **止损/右尾**：所有提前止损实验同时计算 false scratch、re-entry cost、missed winner，不许事后删亏单；权益曲线和大赢家贡献必须成组报告。
9. **门槛**：沿用当前 [TA_VNEXT 验证标准](../TA_VNEXT_VALIDATION_BACKTEST_SHADOW_AND_PROMOTION_STANDARD_V1_2026-09-11.md) 与后续优先 addendum 的 G0–G5 正式闸口，包括 Forward 最小样本、置信界、集群与成本压力。这里不凭公开教育资料批准任何资金使用。

## 4. 关键输出表结构（建议字段）

```text
research_package_id
source_confidence: SOURCE_OBSERVED | AUTHOR_HEURISTIC | PROJECT_HYPOTHESIS | PROJECT_VALIDATED
candidate_id / variant_id
strategy_version / policy_version / parameter_version / derivation_version
market / venue / instrument / session / native_open_definition
raw_data_manifest / pit_universe / fee_profile / execution_model / latency_profile
source_event_time / admitted_at / signal_completed_at / decision_at / order_active_at
opportunity_id / thesis_id / setup_type / side / attempt_id
regime_predecision / known_level / location_quality / followthrough_evidence
eligibility: ELIGIBLE | BLOCKED
decision: TAKE | WAIT | PASS
not_evaluable_reason / opportunity_expiry / fresh_trigger_id
simulated_entry_exit / fill_state / all_in_friction / net_r / mae / mfe
false_scratch / missed_winner_cost / right_tail_capture / giveback
source_period / dev_or_oos_or_forward / cluster_id / trial_id / freeze_hash
```

## 5. 假设登记与首轮试验顺序

| 研究项 | Primary question | 直接对照 | 测量期望 | 停止/下一步 |
|---|---|---|---|---|
| Q1 | Regime 是否改善参与质量？ | 当前 Three Setup vs State gate | delta net R、coverage、错失赢家 | 无稳定增量→停止加复杂度 |
| Q2 | 回收+反向力度是否提高质量？ | A/B/C vs 加回收/跟随 | first-passage、MAE、成本 | 信号过晚→保留纯形态 |
| Q4 | 跟随 / 回测确认净效应？ | EA0/EA1/EA2 等既有控制 | 延迟、追价、missed winners | 无用→保持现有 |
| Q3 | H2/L2 对比首试及再入？ | first vs fresh second | thesis R、attempt 费用 | second 无净值→PARK |
| Q6 | 无跟随提前退出减少左尾？ | AP0/AP3/AP4 | tail loss、false scratch、费用 | 割掉右尾→PARK |
| Q7 | 状态化出场保右尾？ | X0/X1/X2/X3 | winner capture、giveback | 增益不稳→较简单 X |
| Q8 | 开盘反向可转移？ | 原 setup vs opening context | pre/post opening event+fees | 交易制度不等价→拒绝迁移 |
| Q5 | 高潮楔形可提供独立信息？ | Q1 simple vs +wedge | OOS lift vs complexity | 无增量→PARK |

**No completed run / no authoritative strategy result in this package.** `TRIALS_COMPLETED=0` 指本研究包新产生的运行次数，不暗示仓库旧研究历史完整或为零。

## 6. 下一次研究运行的前置与交接

只有在相关数据、精确版本、执行模型和策略研究任务另行冻结后才可启动。Strategy author 提交小网格与确认/否证条件；Engineering 使用成熟 NautilusTrader 能力实现因果对照；Independent Validation 进行后验检查与独立宣告。任何必要策略代码修改另立新的冻结包、审核、CI 与授权。当前文件**只是待用候选库**。

```text
NEXT_TRIGGER=QUALIFIED_CAUSAL_HISTORICAL_PATH_OR_APPROVED_SHADOW_RESEARCH_PACKAGE
RESEARCH_EXECUTION_AUTOSTART=NO
ORDER_WRITE=NO
MAINNET=NO
```
