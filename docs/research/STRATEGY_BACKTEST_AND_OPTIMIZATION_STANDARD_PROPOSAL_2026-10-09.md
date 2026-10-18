# Trade OS — 统一策略构建、回测与优化标准流程（Nautilus-first）

**状态：提案 / 待人类讨论与批准；非生效治理、非开发冻结、非回测执行许可**  
**记录日期：2026-10-09**  
**应用对象：Three Setup、开盘反转、未来任何新策略、既有策略优化、重复历史回测、Shadow / Forward 评估**  
**主要目标：以最小的工程和研究成本，尽快形成真实、可复现的扣费后交易优势证据。**

> 本文记录已讨论的目标架构、复盘结论和建议的长期工作法，不自行覆盖当前 GitHub ACTIVE manifest 选择的宪法、不改写任何已冻结 G0 数字/研究合同。所有真实实施均需重新检查当前 package-state、权限及必要 V5 生命周期；禁止把本提案解释为已经批准迁移、编码、CI 改造、云运行、Reserve 解封或实盘交易。

## 0. 当前案例状态与事实边界

- GitHub：woshixiong/trader-assist-v0，权威入口始终为 AGENTS.md → ACTIVE_GOVERNANCE_MANIFEST.json → manifest 所选唯一宪法 → 精确 package-state / Issue / PR → 触发的窄程序。
- G0 的当前权威状态见 [Issue #161 package-state Revision 22](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6038693551)。R3D 已完成 240/240 份原生 5m Sidecar；16 份 Reserve 仍封存。R4 曾用冻结源码 660e00dcf05bc8962649891b6c232f3451bc037c 启动一轮历史运行，耗时约 10 小时仍未完成，获用户明确授权后以 SIGTERM 停止，记录 exit 143；**没有生成合格 R4 aggregate，不能宣称策略成功、失败或有正期望**。确切停止证据：[Issue #161 人类授权中止](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6064702223)。
- [性能诊断](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6063927940) 指向 G0 自建代码重复扫描历史、重复转换及聚合；这是一条有源码证据的主嫌疑路径，并非完整函数级性能归因。**不能把“优化旧自建回放函数”当作已选架构。**
- 更新后的 [Nautilus-first 讨论](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6066539312) 明确优先让成熟框架拥有通用数据、时间、缓存、回放与执行。当前仅是架构提案，**没有获得实施许可**。
- G0 本轮原始数字与策略研究权限以 [预数据冻结](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6017065560) 和其后精确 Run Plan/Issue 记录为准；本文不替代它们，也不允许看过结果后改冻结指标。

## 1. 战略目标、边界和成功定义

交易研究的目标不是把历史收益调到最高，而是：

> 在因果有效、可执行且成本真实的前提下，使“已验证扣费后交易效用 / 策略复杂度 + 研究工程负担”最大。若候选之间的验证效用实质相当，保留最简单者。

- **我们必须自己研究的领域**：人的交易假设量化、Setup、结构/状态识别、扫描器与信号逻辑、策略型入出场、再入场、赢家持有、策略风险及研究问题。
- **我们不应该自己重复开发的领域**：历史数据目录、事件时钟/调度、一般缓存、普通 K 线聚合、市场事件回放、通用成交/OMS/账户/仓位/组合、运行编排、部署/日志/CI/基础设施。
- 技术正确性、数据权属、PIT、时间因果、独立证据和交易权限是硬约束，不能为追求速度省略。
- 正确的速度优化是**尽早拒绝错误路线、早停技术不合格任务、复用框架和数据**，不是简化研究真伪门槛或大量新增治理设施。

## 2. 唯一回测基础设施与责任矩阵

| 责任 | 默认唯一 owner | 对 Trade OS 自研的界限 |
| --- | --- | --- |
| 事件驱动历史回放、时钟、Bar/Trade/Quote、数据缓存、订阅/回调 | 经版本核实的 NautilusTrader BacktestNode/BacktestEngine、Catalog、DataEngine、Cache 等 | 禁止第二套通用回放循环、历史数据存储、调度器、事件总线 |
| 支持的多周期 K 线聚合、通用技术指标 | Nautilus 官方已验证 API/框架现有成熟组件 | 仅在确定官方能力不符合**特定策略语义**时考虑窄扩展，不复制通用基础设施 |
| 标准模拟撮合、订单、成交、仓位、账户、风险通用执行、安全边界 | Nautilus 正式扩展接口/原生提供的 execution/portfolio/account/OMS | 禁止新造 execution engine/OMS/通用 Fill model；任何偏离默认成交的假设明确登记 |
| 交易所公共数据和离线 240 Sidecar、权利/时间/映射身份 | 已验收 R3D 数据合同 + 兼容性证实的官方 Nautilus 数据格式/薄适配 | 不重下载，不重复发明解析器、下载器、数据库；数据仍按权利限制存储 |
| Three Setup、开盘反转等策略状态、信号、触发与策略风险 | Trade OS Strategy Kernel、Scanner、Frozen Strategy Package | 保留策略差异化；以 Nautilus Strategy/on_bar/官方扩展接口承载 |
| 人工逻辑复盘、研究问题、对照组、统计充分性/成本/因果结论 | Trade OS research policy 与既有预注册/试验账本 | 只保留“研究判定规则”；不能变成第二个通用回测引擎 |
| CI / Linux 性能运行 / 日志证据 | 现成 GitHub Actions、标准 Runner 或已批准现有服务器 | 不开发调度平台、控制器、轮询器或性能基础设施 |

已有可用项目代码：research_data/nautilus.py、nautilus_g4/runner.py、nautilus_g4/catalog_bridge.py、E4/Strategy Kernel，以及现有 research replay 领域合同；**“项目已有”不等于“直接与 G0 完全等价”**，必须先验证对应职责和冻结语义，再切换。

### 2.1 唯一明确的当前交易语义兼容性问题

冻结 G0 使用 BAR_NEXT_OPEN_STOP_FIRST_V1，属于研究性 next-bar-open/stop-first 成交假设。锁定的 NautilusTrader 2.0.0rc5 官方文档明确指出：默认 OHLC bar simulation **没有直接提供 native next-bar-open fill mode**；使用 on_bar 当前 K 线开盘价可能产生前视，bar-only latency 通常也不能保证下一根开盘价成交。

因此：

1. 不得把 Nautilus 默认成交等同原 G0 结果；
2. 首先验证官方已支持的事件、订单模型或正式扩展口是否可以保持语义；
3. 如不能等价，**保留小而明确、仅供该研究主张使用的结果计算规则**，并标记与原生执行结果不同；它不能拥有第二套事件时钟、缓存、回放或 OMS；
4. 如果一个窄研究规则也不能与原生回放干净分离，立即返回 Engineering Control 作架构决策；不得自行开发私有 Nautilus fork 或全新引擎；
5. 未通过精确事件/成本/填单语义对照前，不宣称迁移 PASS。

精确上游证据：
- https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/docs/concepts/backtesting/bar-execution.md
- https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/docs/concepts/cache.md
- https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/docs/concepts/strategies.md

## 3. 所有新策略、原策略优化和重复回测共用的六阶段 SOP

### Stage 1 — 先定义人类交易假设 / 因果问题（Strategy，不写回测框架）

- 对已有真实/模拟交易重建时间线：交易前情境、观察信息、触发、入场、止损、主动退出、持有、再进场、延迟及人类可执行约束；不凭事后 K 线美化决策。
- 如开盘反转：将“美股前一日/盘后方向、韩股集合竞价、开盘 1 分钟不延续/插针回收、几十秒平仓”拆成可量化的**前视可用**条件；明确观察粒度与 5m 数据不匹配时必须有更高频、具有权利的真实数据，不能用 5m 伪造秒级结果。
- 冻结 Universe/时间分区/日历/交易时段/时区/PIT、机会单位和独立 cluster、策略版本、最简单对照组、成本与执行模型、最大亏损和终止条件。
- 人类确认交易与策略影子、真实成交的证据身份必须分开；不从“理想价格”直接推断人类可成交收益。
- 判断问题是否具有现实决策价值；没有实际交易决策影响的特征/数据提案直接 PARK，不做“可能有用”的研究堆积。
- 产物：**单页研究登记**（目标、策略、基线、候选、数据分区、成本、成功标准与不变量）；复用既有 Issue/Trial Ledger，不另建数据库。

### Stage 2 — 复用框架、组件和已批准的数据（Infrastructure，只做能力匹配）

- 默认同一个 Nautilus 版本/统一入口，仅改 Strategy 参数、数据目录与受控运行配置。
- 在开发前查现有项目能力 → 精确官方接口 → 官方配置/插件 → 薄适配；任何通用能力“不支持”必须附真实版本、公开文档/代码和最窄缺失语义的证据。
- 已有 DEV/Sidecar 先做权利、Checksum、时间、PIT/corporate action/delistings/bad ticks 和缺口校验；原始私有或受限行不传 GitHub；输出仅允许已授权汇总。
- 不将股票/RWA 与加密混成同一费用、时段、可交易性和数据语义；当前 Binance G0 只支持其已冻结的“外部加密机制验证”，不能代替 Hyperliquid RWA 的成交验证。
- 改不了的成交假设或数据契约在此 STOP/REPLAN，而不是构建新 engine。
- 产物：一张 owner/compatibility 结论：REUSE、THIN_ADAPTER、STRATEGY_ONLY_GAP 或 BLOCKED（附理由）。

### Stage 3 — 先技术验收，再完整回测（small deterministic smoke）

- 对已经批准的固定小样本和合成边缘情形一次性检查：Bar close/finality 和 callback 顺序、无未来数据、session 日界、缺口/warmup、状态重置、相同 timestamp 的稳定排序、成交与止损优先模型、成本、结果 provenance、合法可见性。
- 复用已有框架的 per-candidate isolated engine/cache；不共享候选运行状态。
- **只针对新能力**做最小测试；已验收的框架责任不用每次重审。新的迁移/新引擎配置需精确版本/完整事件、决策、经济汇总的差异矩阵。
- 用一个预登记的代表性小样本/规模扩展性测试建立 CPU/内存/时间基线，测试后估算完整运行的时间预算；无进度或超预算时 fail-closed，而非让用户等 9 小时后再诊断。
- 不把简单单次样本的快当作全体数据性能保证；必要时使用标准 cProfile/框架现成指标，**不用自建 profiler/daemon**。
- 产物：TECH_PASS 或 FIRST_BLOCKER。TECH_FAIL 不消耗策略研究试验、不能擅自开启完整 R4。

### Stage 4 — 一次预注册正式回测，和简单基线作对照

- 只使用 frozen 候选和 DEVELOPMENT 样本，不按 PnL 自选窗口、添加新交易条件或提前看 Reserve/OOS。
- 执行框架官方标准 backtest 运行入口，优先 GitHub 官方执行/受控服务器（需要相应执行表面权限），避免对 Mac 持续多小时计算；不因更换运行机器就认为解决算法复杂度。
- 每个候选在相同有效机会集合、时间状态和成本合同下做配对比较，防止机会数不同造成虚假收益。
- 记录：完整费用/滑点/资金费用/冲击及不利成交、净 R/净 cash、交易次数与独立 MarketEvent/cluster、最大 DD、尾部、收益集中度、持仓周期、MFE/MAE、交易时间/状态、延迟/可成交敏感性、机会覆盖、容量、资料完整性。
- 默认采用 chronological holdout / paired 或 block bootstrap / 预声明成本情景；DSR、PBO、CPCV 等只有自适应搜索规模和问题触发时条件升级，不为了流程好看机械全做。
- 记录 RunSpec/Strategy/Code/Dependencies/Data/Execution/CandidateRoster/TrialLedger 和允许发布的汇总指纹，禁止部分结果冒充完成。

### Stage 5 — 只作一个可证据化的研究决策

- KEEP_CURRENT：现有策略已是可证实更优或没有可靠增量改善；
- RESEARCH_LEADER / ONE_BOUNDED_REPAIR：仅在预注册允许、确切机制失败且已证明新的改变值得试验时，执行有限策略改良；绝非修回测引擎；
- MORE_INDEPENDENT_EVIDENCE：若事件/簇/状态覆盖不足，只寻找能改变当前决策的最少新独立证据；不得自动开 Reserve；
- STOP_OR_PARK：无扣费后机制、后续信息成本高于价值，停止广泛调参。
- 相近验证效果选更简策略；**不能因胜率较低否定正期望，也不能以高胜率替代收益尾部和亏损分布审查**。
- 任何材料参数/规则/特征变更先记 trial ledger 和新不可变版本；被看过的 OOS 不恢复为独立样本；长期优化循序前进，不允许相同 DEV 无限寻优。
- 本阶段调用现有研究治理的真实判定，不另建“研究决策引擎”。

### Stage 6 — 后续冻结 Forward / Shadow，实盘单独授权

- Shadow 首先验证流程、实时时间、数据质量和人工可执行性；短 Shadow **不能代替跨市场状态的独立历史证据**。
- 三类证据始终分开：策略理想价 Shadow、人类确认价+延迟 Shadow、真实成交结果。
- 所有实盘/部署/权限动作按现有 V5 Human Gate，先执行与研究隔离的 Shadow/模拟验证，再另行决定人类确认和真实资金。
- 若 Forward 表现失效，先判断数据/执行/策略哪一层失败，再决定 HOLD、RESEARCH 或 STOP；不直接循环修改模型参数。

## 4. 三种日常任务的最低成本执行路径

| 任务 | 默认改什么 | 原则上不改什么 | 是否触发框架选型 |
| --- | --- | --- | --- |
| 新建策略 | 策略说明、冻结策略实现/配置、试验登记、最小新验证 | 通用引擎、数据目录、历史回放、CI 工作流 | 否；仅出现真实缺失的通用能力时 |
| 优化原策略 | 已冻结机制缺口对应的策略变量、版本/Trial Ledger、配对分析 | 市场数据权利、交易执行假设、引擎及宏观基础设施 | 否；如果问题是基础设施直接进入 Control |
| 重复回测或增加已批准新样本 | 数据和合法范围、运行配置、哈希、结果与比较 | 策略/引擎源码、下载器/数据库/新脚本 | 否 |

同一基础设施一次经合格测试、长期复用。不同策略可使用同一引擎但不能共享未声明的策略状态、未冻结结果或测试/样本污染。

## 5. 针对 G0 的一次性迁移决策（目前不得执行）

建议只在单独批准后按以下最窄顺序做，不把它分裂为一连串临时修补：

1. **Ownership/fit matrix**：逐项映射研究数据 → Nautilus Catalog → event/bar callback/cache → 策略 kernel → native execution/result → Trade OS 研究决策，列出现有代码中所有重复通用 owner（包括机制造环、重新做历史前缀、重复周期聚合、全量 candidate 重建）；每项给出“框架现成、薄适配、策略专属、不可兼容”之一。
2. **唯一关键语义核验**：精准验证 rc5 bar timestamp、on_bar/下单、模拟撮合、next-open stop-first、成本/资金/价差与完整候选匹配。不满足原 G0 合同的差异不能隐瞒，不另建通用 engine。
3. **一条可长期使用的官方原生运行入口**：复用现有 Nautilus G4/E4 与 R3D 240 Sidecar，限定一个薄输入接口和策略执行接口；避免重抓历史；**渐进淘汰**重复自建回放责任而不破坏数据证明合同。
4. **有界等价性+真实性测试**：先用既有合成、困难边界、代表性样本做事件/成本/状态逐项比较与性能测试。新实现的代码 fingerprint 必然变化，必须重绑定，不能假称旧代码头相同；不允许把旧中断 run 当 PASS。
5. **正式新 R4 是另一次受控研究动作**：仅在架构、review/CI 和单次执行权限都满足后，使用相同冻结 DEV 资料/Trial Ledger 运行；不自动释放 Reserve，不自动推进交易。

若经官方接口检验无法在保留 G0 研究语义下建立薄适配：**停下来做一次 Architecture Decision**，考虑把原经济模型保持为独立研究主张，或在新的预注册中明确区分 Nautilus 经济主张；不重复发明引擎。

## 6. 现有 G0/V1.2 研究纪律必须保留

- Pre-data 先冻结 A/B/C（或当期真实 frozen 字段）顺序与停止规则；C 为证据不足时不得因为想要结论而跳到新数据/多 trial。
- Sample gate：独立事件数量、事件簇、状态/交易时段/市场覆盖和分母完整性。G0 当前具体 10 个必填 cell、每 cell 12 个独立 MarketEvent 与 4 个 clusters、5 个候选等数字仅可引用原始 [Issue #161 numeric freeze](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6017065560)，本通用 SOP 不把它们写成所有策略的常数。
- 数据 PIT：corporate actions、delistings、timezone、异常 ticks、上市前/退市后、bars finalized、权利、时钟、missingness、映射被知时间，缺一不能“推定修复”。
- Purge/Embargo 对齐标签/持仓/outcome 真正事件窗口；Holdout/Lockbox 按 claim 保留。不得把反复使用或被看过的 Holdout 称为 untouched。
- 默认经济评估：按 chronology/配对/重抽样/已冻结成本和净期望，对不利止损及执行可实现性敏感性做测试；高级检验条件触发。
- DEV 预算要给后续修订和测试保留余地。当前 16 Reserve 不自动开封、未授权不改变权限。
- 区分研究适用性：加密 DEV 对现有 Three Setup 的机制验证不能直接证实 Hyperliquid RWA 的成交、订单簿与实盘正期望。
- 连续研究修订的成本与复杂度必须受 Value of Information 约束：新增资料/参数仅当可改变真实决策时投入；单次错误信号不自动引发新开发。

## 7. 原始策略精神与后续重点

- 先把真实成熟的人类交易行为拆解为可观察事件，再用数量化研究核验；不为了方便编码而改变人的决策时序。
- 快进快出、小止损、可保留大趋势赢家；市场出现结构性失败时退出；允许失败重试但禁止盲目追单/亏损加码；不以胜率最大化为目标。
- 开盘反转（韩国/美国及 Hyperliquid RWA 可迁移性）属于**新研究假设**，要按上述 6 Stage 做 PIT、秒级执行数据与样本独立性核验；不能以粗粒度 5m Bar 推定几十秒的稳定回报。
- 优先以最终是否形成**扣除真实成本且执行可实现的正期望**作为策略研究晋级依据。历史研究只是阶段性证据，不能替代前瞻与真实成交证据。

## 8. 统一入口建议：配置驱动，不新造框架

每个策略 RunSpec/元数据应复用现有研究合同，逻辑字段包括：
StrategyVersion + Setup/Parameters + DataSource/Checksum/Rights/PIT + Window/Purge/Embargo + Venue/Calendar/Costs/FillSemantics + CandidateAndBaseline + TrialLedger + Code/Dependencies/EngineVersion + RequiredGates + ExecutionSurface + ResultArtifactIdentity。

这是**对既有合同的字段映射建议，不是授权创建新的 RunSpec 格式或自研控制器**。若当前已有对应字段直接使用，不要复制第二份源头。执行/输出优先 Nautilus/官方 GitHub Actions runner、受权限约束的数据存储，以及现有 aggregate evidence egress。

## 9. 全局管理员模拟（仅桌面分析，非已执行测试）

| 情形 | 必须表现 | 否则 |
| --- | --- | --- |
| A. 新建策略 | 框架/数据已有 → 只变策略与配置 | 拒绝新回测程序 |
| B. 策略优化 | 只改预注册机制变量；原对照/样本/成本保留 | 返回研究冻结 |
| C. 回测性能异常 | 全链路责任和复杂度审计 → 先查 Nautilus owner | 禁止单函数无限修补 |
| D. Nautilus 默认 fills 与 G0 不同 | 对照官方接口、策略专属 overlay 明确声明 | 禁止假称同等经济主张 |
| E. 数据不足 / 未来信息 | 停止或只寻最少独立证据 | 禁止窥探 Reserve |
| F. 多次修复或相关模块反复坏 | 报告 first failure / repair count，返回 Control 全局 replan | 禁止越预算改代码 |
| G. 无部署/云/真实资金授权 | 只输出方案、不会开始运行 | fail-closed |
| H. 技术通过、统计不足 | 正确分类“更多证据”而非“策略通过” | 禁止伪成功 |
| I. 原 G0 中止 | Exit143=人工中止，新的 run 需新授权并保留 fingerprints | 禁止自动重跑 |
| J. 下一项新策略 | 直接用统一框架，沿用已有已通过证据 | 禁止第二套执行平台 |

每次关键复盘至少报告“业务目标、已有成熟 owner、真正的缺口、最小路径、失败/退出、运行预算、保留权限、证据强度”。不重复完整治理论文。

## 10. 最小硬门槛与角色

- Engineering Control **开发前**区分 Strategy / Commodity / Thin adapter，给出版本正确的成熟方案证据、全球根因和边界；任何 UNKNOWN 不能变 PASS。
- Writer 严格执行 frozen scope，不能因为本地失败自行扩大 scope/架构。独立 Reviewer 审查复用能力、官方扩展与适配真实性；“文件叫 adapter”不是薄适配证明。
- 重用 V5 既有 package-state、GitHub Issue、PR、CLI hooks、CI；不创建独立治理服务、轮询器或新的审批平台。必要机械拦截加入已有 GitHub CI，语义判别仍需独立人工/AI Reviewer。
- 内部普通文档、研究、方案分析不要无必要调用 Codex；真正实现代码才使用已冻结 Route/Writer。Pre-code 和 Final Review 不自行增加轮次。
- 发现首个根因/语义失败时先**清晰公布失败和 impact**，再根据当前修复预算、角色、权限决定是否继续。跨层新根因或第三次语义失败应 Control Replan，不得假装是原计划修补。
- GitHub Mark Ready / Merge / branch deletion / deployment / production/cloud/service / credentials / exchange/order / real-capital 均受当前明确人类权限限制。

## 11. 阶段交付与下一动作

**本文件自身的通过标准**：清楚标注提案、可复用责任、6 Stage 策略研究、原 G0 语义边界、V1.2 研究纪律、10 种失败演练、最小后续路线和全部需用户授权的动作。完成本文不等于实施通过。

**暂不执行**：Nautilus 迁移、废弃旧回测代码、性能修复、数据解封、Runner/CI 改造、R4 再启动、部署、订单或真钱动作。

建议未来如果用户单独批准：
1. 一次只读的 Nautilus rc5 precise fit/ownership + 实际差异验证计划；
2. 一次最小、受 V5 控制的原生迁移/薄适配包（只在 fit PASS 后）；
3. 一次代表样本技术验收 + 经授权正式回测；
4. 使用相同 SOP 长期开展策略研究。

阶段是逻辑工作单元，**不是强制增加四个 PR 或四轮 Reviewer**。已经正确完成的证据复用，最少必要验证，避免造“治理轮子”。

## 12. 证据与规范出处

- 当前权威 V5：https://github.com/woshixiong/trader-assist-v0/blob/main/AGENTS.md ，manifest 根据 live ref 选择宪法；
- 项目成熟方案准入：https://github.com/woshixiong/trader-assist-v0/blob/main/governance/EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md
- 研究投资/复杂度/自适应搜索：https://github.com/woshixiong/trader-assist-v0/blob/main/governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md
- 行为和 edge 证据：https://github.com/woshixiong/trader-assist-v0/blob/main/governance/TRADING_BEHAVIOR_AND_EDGE_REVIEW_PROCEDURE_V1_2026-09-06.md
- 策略实验生命周期：https://github.com/woshixiong/trader-assist-v0/blob/main/governance/TRADING_BEHAVIOR_REVIEW_AND_EXPERIMENT_LIFECYCLE_V1_2026-09-13.md
- 当前 G0：Issue #161 原始 prereg、R3D/R4 运行与人工中止、Nautilus-first 提案，均以精确 Issue refs 为准。
- NautilusTrader 官方：v2.0.0rc5 tag 的 Strategy/Cache/Bar Execution docs，以上链接。

~~~text
DECISION=STRATEGY_BACKTEST_STANDARD_PROPOSAL_ONLY
CANONICAL_GITHUB_REF=THIS_DOC_ON_DOCS_BRANCH_PENDING_REVIEW
NEXT_DESTINATION=HUMAN_ARCHITECTURE_DISCUSSION_AND_V5_ENGINEERING_CONTROL
NEXT_ACTION=NO_EXECUTION;AWAIT_SEPARATE_ARCHITECTURE_OR_STRATEGY_RUN_APPROVAL
COPY_PASTE_COMMAND_OR_PROMPT=NONE
~~~
