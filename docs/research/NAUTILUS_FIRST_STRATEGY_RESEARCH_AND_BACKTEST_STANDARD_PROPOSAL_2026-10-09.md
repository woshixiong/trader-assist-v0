# Trade OS — Nautilus-first 统一策略研究、优化、回测标准方案（讨论稿）

**记录日期：** 2026-10-09  
**文件性质：** 跨策略可复用的完整方案与历史研究衔接说明，**不是已批准架构、不是新宪法、不是实施授权**。  
**状态：** PROPOSAL_ONLY / AWAIT_HUMAN_ARCHITECTURE_DECISION。  
**适用范围：** 新策略设计、已有策略优化、回撤根因分析、重复历史回测、样本外/Forward/Shadow 晋级；RWA、加密和其他被扫描器纳入的合格标的。  
**治理入口：** AGENTS.md → governance/ACTIVE_GOVERNANCE_MANIFEST.json → manifest 选定的唯一宪法 → 当期精确 Issue/package-state → 触发的最窄程序。GitHub 的最新权威决定优先于本文。

## 0. 用户真正要的结果

不是增加回测引擎、PR、审核轮次、控制器或新数据平台；而是**尽快、以最低整体工作量判断策略在真实可执行成本和风险限制下是否有正期望**。目标是：

1. 框架和基础设施**尽量直接使用成熟官方方案**。已采用 NautilusTrader 时，默认优先复用其现有回测、数据、事件、缓存、订单、组合和运行能力；不得为某个策略另写通用回测引擎。
2. 我们拥有的知识产权是策略：人类决策逻辑、Setup、扫描、入场/退出/再入场、策略专属风险及实证研究判定。**只有这些差异化部分才需要独立研究。**
3. 先看完整系统设计，再看局部性能问题；先用最便宜的决定性验证，再消耗完整样本和计算资源；不以审查繁复替代结果。
4. 未来新策略、策略优化、回撤归因和不同市场回测使用**同一成熟运行能力 + 不同策略/数据/配置**，不重复建设通用功能。
5. 严格保持真实数据、无前视、时间与可知性、封存 Holdout、成本和执行假设的真实性。更快不能牺牲这些硬门槛。

## 1. 本次失误产生的架构事实与未解决问题

**已确认的证据：**

- GitHub Issue #161 当前状态（记录时 Revision 22）是 R4 经用户授权中止；原后台 Python 收到 SIGTERM，退出码 143，**没有完整 R4 aggregate、没有有效 G0 策略优势结论**。这不是策略失败证据：[中止记录](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6064702223)、[package-state](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6038693551)。
- 已有 R3D **240/240 合规 DEV Sidecars**，4 个交易对、60 天、每对每天 288 根 5 分钟 K 线，共 69,120 条名义 observations。原始数据保留，不必仅因迁移重新下载。**16/16 Reserve 仍封存**；不向 GitHub 发布原始市场行或数据包。
- 当前 G0 的自建研究路径涉及逐时刻多次重扫原始 K 线、重新构建前缀、跨周期重新聚合、重复回调扫描器和候选结果索引。实测中止前运行接近 10 小时，未产生回测结果；已有[性能证据](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6063927940)。
- 仓库**已经**锁定 NautilusTrader 2.0.0rc5，并有 research_data/nautilus.py、nautilus_g4/runner.py、nautilus_g4/catalog_bridge.py 等原生能力集成。过去只是 G0 没有把成熟通用回测作为统一责任方。
- 原 [Nautilus-first 架构纠偏](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6066539312)仍然是待讨论建议。不能把它写成已迁移或已复核 PASS 的事实。
- **关键不兼容待证**：Nautilus v2.0.0rc5 官方 [bar-execution](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/docs/concepts/backtesting/bar-execution.md)明确不提供默认 native next-bar-open fill mode。原 G0 冻结的 BAR_NEXT_OPEN_STOP_FIRST_V1 与官方默认 OHLC 模拟**不能直接宣布等价**；这只是一个明确的领域研究假设兼容点，**不能据此另造时钟、历史回放、交易账户、通用撮合引擎**。

## 2. 全局唯一责任分工

| 责任 | 唯一优先责任方 | 禁止事项 |
| --- | --- | --- |
| 通用历史数据目录、读取、转换、时间推进、历史事件回放、通用数据缓存 | Nautilus 官方 Data/Backtest/Catalog/Cache，优先复用项目既有 RC5 桥接 | 不得再自建第二套历史引擎、时间循环或数据存储平台 |
| Bar 驱动、通用聚合、框架可提供的指标、订阅、消息调度 | Nautilus 官方 Strategy/Actor 和受支持组件 | 不以 G0 专有代码长期承接通用职责 |
| 通用订单生命周期、持仓、账户、执行/撮合、标准费用、状态恢复与隔离 | Nautilus 官方受支持版本及模型 | 不自行维护通用 OMS、Portfolio、Fill Engine 或私有框架 fork |
| Three Setup / 其他策略的可交易信号、区间结构、候选选择、入场/止损/离场/再入场、策略特有风控 | Trade OS Strategy 逻辑，通过官方接口接入 | 不把成熟框架的基础设施复制进 Strategy |
| 数据权限、PIT 可知性、冻结研究假设、样本/Reserve/Trial Ledger、保密、统计置信、研究晋级 | 现有 Trade OS 研究合同与治理规则 | 不为每个策略重写研究证据平台 |
| 原 G0 特殊成交假设与锁定成本规则 | 由 Engineering Control 先检查 Nautilus 官方 seam；仅无法原生覆盖的**策略研究特定**差异允许最薄的、可替换的研究评价逻辑 | 不以局部 next-open 不兼容作为重建整个回测引擎的理由 |
| CI、Runner、定时、结果工件、进程监督 | GitHub Actions / 已采用标准 Runner / 必要时已有服务器成熟管理工具 | 不自建调度器、轮询器、控制器、日志数据库 |

最终必须形成：**通用基础设施只有一个主责任方，研究规则与框架可单独替换，新增策略默认仅需策略/配置改变。** 同一个适配层不得形成第二份权威状态。

## 3. 成熟能力的真实兼容门槛

必须针对**当前锁定版本**确认，而不是因为“某个新版本的官方文档可能支持”就认定已经符合：

1. Nautilus rc5 的 BacktestNode、BacktestEngine、ParquetDataCatalog、Strategy.on_bar、Cache、DataConfig/Bar 结构、时间戳、单次/跨标的 bar finality；既有适配已提供哪些能力。
2. Frozen R3D Sidecar → 官方支持数据格式的**一次性可追溯薄转换**；保留原源 SHA、交易所、品种、时区、原始 5m 信息、权利和时间可知性。转换必须可校验，不重新采集同一 DEV 样本。
3. 既有 Strategy Kernel、Scanner、状态/事件 ID、不同周期、warmup、成交时点、滑点和手续费映射。官方支持即可复用；只有策略领域特有逻辑由 Trade OS 保留。
4. 对 G0 的 BAR_NEXT_OPEN_STOP_FIRST_V1 不能用官方默认 Bar 撮合偷换。先做**一项精确官方 seam/等价性验证**。若无法等价，明确区分**Nautilus 原生成交回测**与**G0 策略研究合成成交假设**；限定后者为研究特有 outcome 评估，不能伪装成已真实执行或把它膨胀为新通用引擎。
5. 任何必要的显著版本升级、框架改选或通用自研，都是**新的架构决策/权限边界**；不能因性能焦虑随意变更 Nautilus 版本。

只有兼容性关卡通过，才能主张“完全统一、可替换的架构”已经可实施；目前是目标架构，而非已完成状态。

## 4. 统一、可复用的六阶段策略工作流

### Stage 1 — 先定义有价值的研究问题（Human → Quant）

新策略优先从成熟人类交易逻辑入手：记录完整交易序列——行情背景、候选区、观察、进场时刻、确认、失败判据、止损、减仓/平仓及行情后果——再逐项转化为无未来数据的可观察条件。避免凭一张事后走势图发明一组阈值。

对于**回撤与表现恶化**，先分类真实原因（信号质量、成交、交易成本、市场状态、止损/持仓、数据质量、样本结构或执行违规），定位哪一层证据能区分原因；不要直接大范围搜参数。

每项研究预冻结：
- 简短可证伪的因果假设、目标市场/时段/分辨率；
- Champion/最简单合适 baseline、候选数量和 Trial Ledger；
- entry/exit/holding、订单与价格可得性、完整摩擦、真实成本/资金风险；
- 数据来源、时间可知性、训练/选择/holdout/Forward 边界、Purge/Embargo（若结果跨窗口重叠）；
- 样本数、独立事件/簇、状态覆盖和可宣称的证据等级；
- 成功、失败、证据不足和退出规则；明确本轮研究能改变的决策。

**简单优先但不是盲目限制参数**：在扣费后的可验证效果相当时选择简单方案；新复杂规则须有可证伪机制及明确增量价值检验，不能靠历史最优分数晋级。

### Stage 2 — 复用框架与合格数据

先查已有 Nautilus/Trade OS 责任方，**不为新策略开发数据平台或回测程序**。复用现有合法数据目录和预冻结的 market/universe、time-window、license、rights、timestamp/provenance/PIT 验证。真实股票/RWA、Hyperliquid 永续、加密、韩国/美国开盘研究需要分开维护时区、会话、市场结构、手续费/滑点和开盘/集合竞价假设；不能将加密合成成交证明冒充 RWA 的可执行优势。

用户认可的 RWA 优先级不等于可以忽略扫描器覆盖的其他品种；所有品种都须通过相同的正期望/成本/实际可执行性门槛。

### Stage 3 — 最便宜的技术验证（先于全量）

对明确的**预定代表样本**验证：
- 原生回测数据/时间/顺序/PIT 与无前视；
- 5m/15m/60m 的逐级聚合、事件/状态 ID、原始 Strategy 决策一致性；
- 成交价、下一根开盘与 stop-first 等特殊假设的明确分层；费用、maker/taker、资金费、滑点和不可成交路径；
- 结果完整性、失败信号、机器资源消耗、执行时间和扩展性。

使用现有 unittest/pytest/CI 及 Nautilus 官方 Runner 能力，不做本机重负载验证。不需要为每轮研究重新审查已经合格的通用框架。时间预算与 timeout 由已采用的 Runner 原生能力负责；**若代表样本失败，禁止直接运行 240 数据规模碰运气。**

### Stage 4 — 一次冻结的正式比较

正式运行按研究预注册锁定的源、代码、成本、候选和次序；不在运行后根据盈亏更改过滤条件，不改试验数，不提前打开 Holdout/Reserve，不因亏损提前修改停止规则。

评价除收益外，至少覆盖：**实际摩擦后的净 R/净现金、简单基准的 paired 增量价值、事件/簇/状态覆盖、最大回撤、尾部、MFE/MAE、成本敏感性、交易集中度与实际执行可能性**。优先合适的 paired / chronological / bootstrap 分析；DSR/PBO/CPCV 按事先触发的多重搜索风险决定是否必要，非形式性标配。

对本次 G0：原始[数值冻结](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6017065560)已预注册 5 个候选、10 个必需策略分格、至少 12 个独立 MarketEvents/格及至少 4 簇/格等阈值，应尊重精确冻结，不得在数据暴露后重写指标。G0 的结论类别仍然是 **机制验证（MECHANISM_VALIDATION），合成成交覆盖（SYNTHETIC_VENUE_OVERLAY），不得自动晋级真实交易（PROMOTION_PROHIBITED）**。

### Stage 5 — 有限、可验证的策略优化决策

每轮从且只从以下四种**研究结论**选择，并在现有 GitHub Issue/Trial Ledger 记录：

- KEEP_CURRENT：现有 Champion 足够，或更简单模型在可比证据下同样有效；
- BOUNDED_MECHANISM_REPAIR：存在**明确且预先允许**的因果失败机制，最多执行允许的有限修订并变更版本，禁止连环修补；
- MORE_INDEPENDENT_EVIDENCE：样本/独立覆盖不足；只获取能改变关键决策的最小独立证据，而不是扩大搜索；
- STOP_OR_PARK：没有证明扣费后可用的增量价值，或复杂度/研究成本不合理。

对于 G0，**保持其已冻结的 A/B/C/D 结果处置原文语义**，不要把这里的通用分类当成新的 G0 宪法或擅自增加修复预算。

修改参数、增加规则或变换训练/结果可见性，都更新 trial/adaptivity ledger；反复窥探的 Holdout 不再声称独立。减少失败时重复下载、重复回放、重复审查和扩大基础设施的冲动。决策优先级是正期望证据、可执行性、尾部风险，而非孤立的胜率或某一轮 PnL。

### Stage 6 — 独立 Forward / Shadow / Human L2

只将已冻结的候选带入 Shadow 或 Forward，并且区分：
- 以理想信号价格为依据的策略影子；
- 以人为确认时间及延迟为依据的人类确认影子；
- 实际订单成交的真实执行证据。

不同证据不得混合成同一收益。任何策略或数据/特征语义重大变更，都必须生成新的不可变版本，从新版本激活后计算 Forward 证据。是否进入 L2、人类确认、Testnet 或真实订单，是独立权限和风险决策，不从一轮好看的 DEV 回测自动授权。

## 5. 让“新策略 / 优化 / 重跑”真正低成本

| 用户任务 | 默认动作 | 非默认升级条件 |
| --- | --- | --- |
| 新建策略 | 编写/调用 Strategy + 配置 + 预冻结试验，复用同一 Nautilus BacktestNode/Engine 与研究合同 | 发现确实不存在的框架级能力，并经过成熟方案门槛 |
| 既有策略小修改 | 对相同冻结 baseline 作有界候选差异测试，记 ledger | 改动触及数据、成交、时间/状态等框架责任或难以证实等价 |
| 重跑、换合法市场/时段、延长 Forward | 更改批准的数据/配置；使用已有 CI/Runner，不写新的 replay 脚本 | 新来源许可、时区/PIT/模型语义、算力权限发生变化 |
| 回撤/少信号/性能异常 | 首先整体链路归因，区分策略 edge、执行 friction 和架构低效 | 多处相邻错误、第二套 owner、跨层语义冲突 → 工程 Control 全局重新选路 |
| 无优势或数据不足 | KEEP / 独立证据 / STOP，优先结束低价值研究 | 真正会改变重大决策的增量信息 |

不自动为每个策略创建 PR、Controller、持久数据库或监控器；**策略研究记录不是每次都修改框架代码**。已有有效审核证据按 V5 复用，不让用户反复递送 SHA、CI 或长评论。

## 6. 一次性迁移建议，不是另一套新项目

按全局可复用价值排序，尽可能以一个有界工程包而非无休止补丁处理：

1. **只读全链路 ownership audit**：识别当前 G0 哪些职责为 Strategy 差异，哪些是重复的通用历史 replay/时间/缓存/模拟，并映射到**实际已安装 Nautilus rc5** 官方接口。交付一个清晰的不兼容列表，不创建新基础设施。
2. **只检验关键 seam**：以小型预冻结样本验证时间语义、Strategy callback、订单/费用/出场假设；严格比较既有 G0 策略事件、决策和成本。Bar-next-open 若不匹配，只保留研究专属差异，不改默认官方引擎或偷换冻结结论。
3. **统一并切换单一通用 owner**：重用 R3D 240 的合法 DEV Sidecars → 必要的官方数据格式薄适配 → Nautilus BacktestNode/Engine → 现有策略/研究规则。通过独立前审、适当的 exact-head CI 和终审后，**去除或退役重复的通用职责**，不能旧自建 replay 与新框架永久并行。
4. **性能和结果准入**：小样本因果正确 + 规模扩展合格，才允许按准确新代码/配置身份进行正式研究。新 run 与被中止的原 G0 不能伪称同一代码运行结论；仍不开放 Reserve。
5. **只在明确授权后实施**：当前文档和 PR 均是讨论，不得自动启动 Writer、运行大型回测、云/服务器动作、部署、Mark Ready、Merge 或真实下单。

不能在官方原生语义未确认时预先承诺“完全无自定义规则”：**自有策略逻辑可以存在；第二个通用回测引擎不可以。**

## 7. 管理员端到端模拟（仅桌面推演，不等于实测 PASS）

| 情境 | 正确决策 / 拦截 |
| --- | --- |
| 新策略只有信号逻辑变化 | 原生 Nautilus 配置和 Strategy 直接复用，不触发新基础设施 |
| Scanner 几乎无信号 | 区分规则过滤、市场状态、输入/权限/时间异常，先量化分母，再决定是否有策略假设可测 |
| DEV 成本后 PnL 不佳 | 不继续无限优化；对照基准、摩擦、预定退出规则，按四类结论关闭 |
| “只需改一个慢循环” | 先检查整个历史访问/Bar 聚合/Scanner/结果链路与成熟 owner，防止单点修复隐瞒第二个引擎 |
| 官方 Bar 成交与冻结 G0 不同 | 明确不等价，只检验最窄的研究规则 seam；严禁偷换盈利结论或另建模拟交易平台 |
| 240 数据不在 GitHub Runner | 核查合法、低成本转运/已有服务器及权限；不把原始行上传公开仓库，不建新分布式任务系统 |
| 代表样本正确但扩展速度异常 | 不启动全量，先用原生 profiling/Runner 观察，再做全局路线决定 |
| Holdout/Reserve 未获授权 | 不打开，不因首轮 DEV 结果不佳而重新采样 |
| 原任务已中止 | 读取 exit143 和中止证据；不能将其当作策略亏损或完整失败回测 |
| 新架构尚未获批准 | 仅保留文档讨论，不能转 Writer/PR 实现、自动重跑或合并 |
| 真实交易或部署需求 | 走现有 Human Gate，不从回测效果推导权限 |

该表为**计划审查检查清单**，不是虚构的自动测试结果。

## 8. 优先级、最小阶段与管理交付

**低频的一次性工程事**：Nautilus 官方能力/薄适配契约确认、历史通用自建责任退役、通用运行环境合格。  
**高频的日常研究事**：新策略/旧策略修改 → 冻结研究 → 已批准原生 Runner → 输出有限证据 → 决策。

建议最少的逻辑决策顺序：先只读能力/兼容判定；获得人类架构批准后才进入一个整合包（须当前 V5 路由、Writer、必要的独立评审和 protected gate）；技术兼容与代表样本达标，再明确授权正式冻结 G0 DEV 回测。**不预先保证实际只需一个 PR 或多少小时。**

管理验收用：从研究问题到有效结论的墙钟时间、正常新策略不需基础设施变更、复用成熟代码责任份额、真实回测覆盖与可信度、用户手动动作次数。不能用“做了多少 PR/Review/治理文件”替代。

## 9. 权限、链接及清晰的下一步

**当前明确未授权**：实施本方案、迁移 Nautilus、重启 G0、切换执行环境、修改治理、Mark Ready、Merge、部署、开封 Reserve、任何真实订单/资本行为。本文是只读方案的文档化产物，不改变 Issue #161 Revision 22。

关联证据：
- [Issue #161 当前 package-state](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6038693551)
- [原始 G0 数值冻结](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6017065560)
- [R4 停止与未完成证据](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6064702223)
- [Nautilus-first 全局纠偏](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6066539312)
- [Nautilus rc5 Cache](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/docs/concepts/cache.md)
- [Nautilus rc5 Strategies](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/docs/concepts/strategies.md)
- [Nautilus rc5 Bar Execution](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/docs/concepts/backtesting/bar-execution.md)

DECISION=NAUTILUS_FIRST_REUSABLE_STRATEGY_RESEARCH_PROPOSAL_DOCUMENTED_NOT_APPROVED  
CANONICAL_GITHUB_REF=THIS_DOCUMENT_ON_DOCUMENTATION_BRANCH  
NEXT_DESTINATION=HUMAN_WITH_ENGINEERING_CONTROL_DISCUSSION  
NEXT_ACTION=REVIEW_ONE_TIME_NATIVE_OWNER_COMPATIBILITY_AND_STANDARD_WORKFLOW_BEFORE_ANY_IMPLEMENTATION  
COPY_PASTE_COMMAND_OR_PROMPT=No execution command. This document alone grants no engineering or protected-action authority.
