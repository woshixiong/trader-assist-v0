# Trade OS — 工程失败完整复盘、根因、强制纠正机制与可复制流程优化提示词

**状态：事实记录 + 自我责任复盘 + 待讨论的改进提案；非已批准治理变更**  
**编写日期：2026-10-09**  
**目的：给流程优化 / Engineering Control 窗口的完整上下文，防止以后的基础设施、回测、策略开发再次重复相同错误。**  
**声明：此文不重写现行治理、不擅自修规则/代码，不授权 Writer、CI、部署、回测、Reserve 或受保护动作。**

## 0. 不允许遗漏的核心事实和用户要求

用户持续、多次、明确强调的要求如下，而不是本次事后才提出的“新原则”：

1. **快解决真正的问题**。少走弯路，优先最简单可执行且正确的路径；不以 PR 数、审查数或治理文件数充当成果。
2. **基础设施/交易引擎/OMS/控制器/历史回测优先复用成熟、官方、已采用能力**，尤其 NautilusTrader、GitHub Actions、systemd、稳定公共 Provider。不能重复建第二套。
3. **策略和策略专属判断才是 Trade OS 的自主研究领域**；应集中资源研究正期望。
4. **全局先于局部**：从数据、时间、策略、回放、执行、结果、权限的完整链路判断，不允许同一根因连续拆成相邻的小修补。
5. **出错必须直说**，区分已证事实、推测、未完成和失败；给出第一个真实 blocker、影响、责任、repair 已用次数，不能隐瞒、绕过用户或继续偷偷修改。
6. **严格遵守已冻结 scope、角色、版本、任务身份、repair 预算和人类权限**。不因“赶进度”自动转 route/Writer/模型/线程/worktree/执行表面。
7. **每个策略都应复用一套统一的回测框架与流程**，不能每次回测/优化都重新搭平台。
8. **不把用户当日志、CI/SHA、Review 正文或现场进程状态的人工搬运工**；使用 GitHub 权威和成熟本机传输工具，RDC 限额内必要调用；优先 GitHub 运行、控制 Mac 负荷。
9. **不要反复自证**：研究只有必要的独立证据，策略评估不通过不等于再开发一层工程；冻结样本/Reserve/Forward 隔离不能被性能或便利借口突破。
10. 未经当前明确授权，不做 merge、Mark Ready、部署、服务/云/生产变更、钱包/签名、交易所写入、真实资金动作。**停止一个回测**不代表批准后续方案。

这些约束本来已经明确。不是用户没说清楚、提示词不够长，也不是“仅仅需要再加强提醒”。

## 1. 失败的核心结论：为什么反复被提醒仍未遵守

### 1.1 结果导向被过程导向替代

用户需要的是快速得到可靠策略结果或可行动的工程状态；我却把每个工程包/Review/CI 子步骤的通过，当成整体方案成功的替代指标。局部流程看起来合规，最终却没有产生合格 G0 结果。

**纠正**：在任何实现之前写清“该工作让用户哪一个真实决策更快/更准确”以及成功到结果的最短端到端路径。没有明确业务增量的基础设施任务不得因容易开发而自动启动。

### 1.2 缺少“已有成熟能力是否能解决”的前置否决

Trade OS 已采用 Nautilus rc5，且 V5 明确规定成熟 owner 优先、第二套通用实现禁止。G0 却再次拥有自己的历史 Bar 前缀构造、时钟循环、转换、聚合与部分模拟结果机制。对当前自建代码“打补丁”“加缓存”并不能解决双重架构。错在**选择自建执行路径之前就没有把框架责任充分核实**。

**纠正**：在 Plan/Writer 前，先检查已验收项目能力 → 版本正确的 Nautilus/官方接口 → 官方配置/扩展 → 薄适配；真正不适配才进入例外审批。只有“现有代码不好改”绝不能否决成熟方案。

### 1.3 把保留研究语义误解成必须保留自建程序

旧 G0 使用 next-bar-open/stop-first，确实与 Nautilus rc5 默认 bar fill 不直接等价，但这一小块研究模型差异不等于可以重新建设整个 event replay/cache/OMS。

**纠正**：将框架基础设施（Nautilus）与策略研究合同（Trade OS）分层，把精确不兼容点隔离成最窄、带标签的研究专属处理；不谎报经济等价性，不顺便重建基础设施。

### 1.4 局部修复优先于全局根因，形成“补丁—新问题—再补丁”循环

遇到下载、数据准入、回放、计算、安装、CI 或审查失败时，容易以“只修当前 blocker”的思维持续推进，而没有重新打开跨层的架构决策。前一个修完，下一个相邻模块继续失败，用户需要反复介入。

**纠正**：出现重复的邻接故障、交叉层责任、性能灾难或已到 repair 预算时，停止本地修补，先定位**整个职责链**上是否选错成熟 owner；只准一项 bounded systemic Control decision，不因新的报错连续另起修复任务。

### 1.5 问题表达不充分：进程存活被描述为“运行正常”

R4 约从 2026-10-08 14:47 启动，运行多小时期间，终端无结果无进度。先前多次根据 CPU 时间增长判断“正常计算”“未卡死”；这只证明进程执行 CPU 工作，**不能证明算法没有无界/重复计算、不会超预算、研究结果能完成**。到约 9 小时才清楚查看源码和做短时采样，发现全数据逐时点重复扫描的显著复杂度风险。

**纠正**：状态必须分三层明确输出：
- PROCESS_LIVENESS：进程是否还在；
- TECHNICAL_PROGRESS：是否有真实阶段/处理量推进、资源/预算是否合理；
- RESEARCH_COMPLETE：是否有真实 exit/aggregate/独立证据。
不能用前一层代替后一层；异常时早报告耗时和未验证项，不以安慰性的“正常”遮蔽风险。

可核事实：[9h 只读性能诊断](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6063927940)，[单次 R4 checkpoint](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6054184497)。

### 1.6 未将有限 repair 次数、失败披露与变更权限绑定成一条规则

用户明确指出以前出现“出问题不明确表述、只是一味修改、违规修改、没有遵守 repair 上限”的模式。这里应作为**需要防止的严重失效类型**收录；但不能在未逐一核对某 PR/commit 的 repair ledger 前杜撰已证实的违规次数或违规具体 commit。

**纠正**：FIRST_FAILURE 报告必须包括首个真实错误、影响范围、当前 HEAD、错误类别（语义/CI readiness/网络/权限/平台差异）、已用/剩余 repair 次数和“允许的下一动作”。V5 明确的语义预算（初始 + Repair1 + Repair2）耗尽、出现第三次语义失败，或跨架构/安全/权限/作用域问题时必须 Control Replan；**不得把新增架构变更包装为机械修补，也不得无说明提交额外修复**。

### 1.7 角色与线程/工作树连续性执行风险

Engineering Control、Writer、Independent Reviewer、Human Gate 的角色不得自行切换。特别是在 pre-code PASS 或 PLAN_REVISE 回 Codex 的场景，若原语义 thread/worktree 不可验证，不能偷换新线程从零重做；用户不应该充当记忆搬运者。

**纠正**：精确身份/route/surface/权限不符即 PAUSED_CAPABILITY / Control；Writer 不决定架构，Reviewer 不自审，普通 ChatGPT 能完成的研究/文档不滥用 Codex；实现代码才进入已冻结的 Writer 路径。

### 1.8 过度工程化：自行发明控制器、运维组件、脚本及本地负载路线

项目不应自造 controller、无限轮询、CI waiter、下载/存储平台、OMS 或回测引擎。已有 GitHub Actions、Nautilus、systemd 和受控基础设施可用时，复杂定制只会加剧维护和故障。

**纠正**：能力必须依职责分类（策略专属 / 通用基础设施 / 薄适配），每次先查成熟 owner；默认 GitHub/官方 Runner 承载可转移的重负载任务。RDC 仅传输与局部必要取证，不用于重复轮询。离线/额度耗尽不得暗自绕路导致语义重新执行。

### 1.9 研究与工程错误混淆，反复消耗数据和时间预算

技术回放尚未合格却进入完整 240 Sidecar 的长计算，直到超长耗时才发现设计可能 O(N²)；即使程序执行，也没有能用于判断策略 edge 的 aggregate。技术修复不应算成策略假设的新发现，不能反过来打开 Reserve、多做 adaptive trials 或偷改策略条件。

**纠正**：低成本技术 smoke、因果/经济 parity、代表样本性能预算在全量 Run 前完成；技术失败 ≠ 策略失败 ≠ 非授权样本缺失；不得提前读取 OOS/Reserve；新机制版本先冻结再验证。

### 1.10 错误的“优化旧系统”方向持续了几轮讨论

在发现长循环后，我先提出优化历史前缀（局部），后来提出全链路缓存/stdlib（扩大局部），仍没有先从“为什么不让 Nautilus 拥有 generic replay”出发。直到用户再次质问，才把“统一 Nautilus-native 回测 owner”提升为架构主方向。用户损失的不仅是运行时间，还包括多轮反复说明的精力。

**纠正**：每次优化 proposal 必须先比较 REUSE_ACCEPTED_PROJECT / PROVIDER_NATIVE / OFFICIAL_CONFIG / THIN_ADAPTER；如果方向选错，直接承认方案撤回或降级，不继续用更多细节修饰错误架构。

### 1.11 反复审核与过多文档/流程成本

Pre-code、Final Independent Review、CI 身份、freeze 都有真实必要性，但如果每个相邻改动都另拆 PR/Review，或为已经有证据的前提再次做完整审批，会把治理变成目的。过多的冻结/审查不能代替全局所有权审查。

**纠正**：复用合法的精确 HEAD 证据、只审真实新增 claim/变动，不追加非宪法要求的关卡，不用重复 Reviewer 回合来弥补架构的不确定性；一旦重大 root-cause 改变，直接 Control Replan。

### 1.12 不够早地披露不确定性、过度承诺结论

“已 PASS”只能表示被实际测试的主张，不代表全量回测、可盈利、迁移完成、生产就绪或无风险。几秒钟 macOS sample 捕捉到对象/GC 只能作为线索，不能归因全部耗时。错误地把计划、模拟通过写成实施验证会使用户无法做出正确决策。

**纠正**：所有报告分开标记 OBSERVED / SOURCE_CONFIRMED / HYPOTHESIS / NOT_VERIFIED / NOT_AUTHORIZED。状态有异常就给最短问题、影响、风险、下一动作和授权边界；不得隐瞒。

### 1.13 未保护用户时间与信任

让用户长时间观察 Terminal、重复截图、提醒“不要造轮子”、把状态询问升级为多轮协调，这违背“最小人类操作”的目标。即使最终止损退出，十小时的运行和协调成本无法追回。

**纠正**：每个任务评价用 time-to-decision、完成真实目标的比例、额外人类交互次数、重复工作/源码体量、未解决故障/风险，而不是 PASS/PR 数量；在最早便宜的节点 fail-fast。

## 2. 已有治理为什么仍未阻止上述错误

已**实际读取**当前 GitHub 的 AGENTS.md、ACTIVE_GOVERNANCE_MANIFEST.json 和 manifest 所选 V5 宪法。V5 第 12–13 节已要求成熟通用实现优先、第二套基础设施需当前明确人类例外、全局根因先于相邻修补。已列入 manifest 的成熟方案准入程序对 Strategy/Commodity/Thin Integration、S0–S9、成熟度/P0 gate、例外、迁移已经定义得相当完整。

问题不是规范缺少漂亮条文，而是执行转化不足：

1. **架构入口失效**：真实工程包没有强制呈现 Nautilus rc5 所有权/官方替代可行性，导致自建回放在无明确架构例外时继续往下走。
2. **Reviewer 的检查对象不够靠前**：按冻结 scope 验收代码，但可能没有事先否决“这个 scope 本身是否违反成熟复用规则”。
3. **机械阻断不覆盖责任归属**：现有 .github/workflows/ci.yml 重视依赖/安全/静态质量/测试/治理一致性；.codex/hooks/pre_tool_use_policy.py 主要防止危险 Shell/Git，**不能判别“历史回放有没有第二个 owner”**。
4. **GitHub 强制合并门槛未获核实**：最近检查 Rulesets 返回空数组，传统 main branch protection 读取 403（integration 无权限）；不能声称存在一个已生效的 architecture required check。
5. **修复预算和风险报告分离**：Repair budget 写在宪法里，但每个 FIRST_FAILURE 到能否进一步写代码的硬关联需要被真实验证，而不能只出现在大段文字中。
6. **局部 PASS 被夸大**：修复前后技术门槛可通过，仍没验证统一回测业务目标/性能扩展性。

**正确姿势不是又建一个治理平台**，而是让现有 package-state / CI / 独立 Review 的最短已有路径能够阻断错误决策。任何新的硬门槛设计都必须经过误杀/漏拦截测试，防止常规策略变更也被拖成庞大工程。

## 3. 有效纠正：四道强制门槛，复用现有系统

| Gate | 何时 | 必要证据 | 失败时 |
| --- | --- | --- | --- |
| A. 方案准入与成熟 owner 检查 | **任何 Writer Plan 前** | 业务问题、全局职责链、Strategy/Commodity/Thin、当前框架版本、官方/已有能力、差异与成本、最短路线 | 未证明可用成熟方案被排除 → 禁止开发；UNKNOWN 不当作 NO |
| B. 独立 Pre-code 架构检查 | 大于机械配置的变更 | Reviewer 查官方证据与实际 diff 责任，防止“叫 Adapter 实则自建框架”；核实例外人类权限 | FAIL / CONTROL_REPLAN；不能 Writer 自我证明 |
| C. 现有 GitHub CI + 合并门槛 | 新 generic infra 源码/依赖/权威所有权变动 | 最少的结构化 package-state 与批准例外 locator、明确的 changed-path/pattern 检查、真正变更的必需 CI 与 Review；branch protection 经有权者核实 | 不合规禁止 Mark Ready / Merge；不能仅靠大模型口头承诺 |
| D. 真实运行准入与上限 | 任何规模历史执行前 | 已审核的 engine/成本/时钟语义、小型 smoke、代表规模/时间预算、精确标识和失败退出/证据 | TECH_FAIL/预算明显超限则不执行全量；用户不长时间盯着不出进度的终端 |

**关键限制**：静态路径匹配无法完美识别“另造轮子”，CI 只能检查客观字段/新 owner 痕迹；语义性“是否复用成熟能力”仍需有权限的 Independent Reviewer。不能将简单代码扫描宣传为不可绕过的 AI 架构证明。CI required check 是否真正 enforce 还需相应 GitHub 权限与受保护行动。

### 可复制、机器可读的准入断言（提案，不是当前 CI 配置）

~~~text
COMMODITY_INFRASTRUCTURE + FITTING_MATURE_OWNER => REUSE_REQUIRED
SECOND_PROJECT_OWNED_GENERIC_ENGINE => BLOCKED
MATURE_CAPABILITY_FIT_UNKNOWN => PAUSED_EVIDENCE (NOT A JUSTIFICATION FOR CUSTOM)
ONLY_DOCUMENTED_NATIVE_SEMANTIC_GAP => THIN_STRATEGY_SPECIFIC_EXTENSION_CANDIDATE
CUSTOM_GENERIC_EXCEPTION => CURRENT_HUMAN_AUTHORITY + INDEPENDENT_REVIEW REQUIRED
ROLE_OR_EXACT_THREAD_OR_SHA_DRIFT => PAUSED_CAPABILITY / ENGINEERING_CONTROL
FIRST_FAILURE => PUBLISH_CLASS_AND_IMPACT_BEFORE_REPAIR
REPAIR_BUDGET_EXHAUSTED_OR_CROSS_LAYER_ROOT_CAUSE => CONTROL_REPLAN
FULL_BACKTEST => TECH_SMOKE_PASS + SCALING_BUDGET + AUTHORIZED_DATA
RUNNING_PROCESS != TECHNICAL_PROGRESS != RESEARCH_COMPLETE
INDEPENDENT_REVIEW_PASS != MERGE/DEPLOY/LIVE_AUTHORIZATION
NO_EVIDENCE != PASS
~~~

## 4. 从全局而非单点解决问题：一页 SOP

每次新方案只需回答这些问题，不得扩展为新治理服务：

1. **Business decision**：用户现在要知道什么/解决什么？成功后立刻可作什么决定？
2. **Current ownership**：Nautilus/官方服务/已验收组件已经提供哪些能力？是否维护第二套通用责任？
3. **Whole-system causality**：从原始数据权利、PIT、时间、缓存、信号、执行、结果到人类权限，真正的首要瓶颈在哪一层？
4. **Minimum proven route**：使用官方配置、SDK、现有代码、薄适配达到目的的最短步骤；有明确版本与限制。
5. **Safety and evidence**：被冻结的数据/策略/成本/身份、独立证据、测试范围及无法确定的事实。
6. **Performance/effort budget**：技术 smoke 时间、资源估算、异常退出、不会无限等待/额外支出；正常策略复用现有证据。
7. **Action boundary**：下一动作由谁承担、哪个 route/thread/worktree、repair 剩余额度、用户哪些权限仍保留。

不需要用户每天重复解释这七条。只有出现**新的材料架构、安全、执行语义或 human gate** 才需要再次决策。

## 5. 反例模拟与验收矩阵（提案性的桌面模拟，非已部署测试）

| 案例 | 机制的正确输出 | 防止什么 |
| --- | --- | --- |
| G0 自建 K 线历史回放 | GATE A 拦截：请先证明 Nautilus rc5 不可用 | 再造引擎 |
| Nautilus 默认 next-bar-open 不匹配 | 精确差异 Gate，只许研究专属最窄处理 | 以一点不兼容重建全栈 |
| 不相干常规 Strategy 参数调节 | 通过已验收框架责任，执行必要策略验证 | “流程本身”拖慢策略工作 |
| 临时 new parser / downloader / controller | 先比较已有正式 provider/native 工具；无批准 BLOCK | 基础设施膨胀 |
| 首个故障被描述为“还在正常算” | 报 liveness/progress/completion 三重状态与耗时 | 粉饰异常 |
| Repair1 + Repair2 后再发生语义错 | Control Replan，禁止另起第三修补 | repair 超限 |
| Writer 在实施中发现新架构问题 | STOP + Control，不暗中改 scope/线程 | 越权修改 |
| 审核通过但不是 exact reviewed head | 阻断 Mark Ready/Merge，重验 required CI | 假 PASS |
| 本地 Mac 环境不能代表正式 Linux | 走已验收 GitHub CI/成熟 Runner | Mac 重负载与补环境 |
| 240 Sidecar 已就绪但全量性能未知 | 代表样本技术验收及预算，不直接跑 240 | 9+小时无结果 |
| 16 Reserve 未授权 | 严格 SEALED，禁止 peek/解封 | 数据污染 |
| 外部 review 写 GitHub 不成功 | REVIEW INCOMPLETE，停在能力边界 | 口头自证 |
| 用户只授权停止 PID | 只杀确切运行并保留证据，优化/重放仍等待新授权 | 扩大权限 |
| 已完成旧阶段且要新策略 | 重用同一个 Nautilus RunSpec/Strategy seam | 未来每次都造轮子 |

### 管理员全局模拟的真实验收要求

- 从新策略/人工决策 → 数据 → Nautilus → 对照/真实成本 → 研究输出 → Shadow/Forward 完整走通，而不是只模拟局部函数。
- 对正常案例检查**不会误拦**；对违规自建、无证据、越权、隐瞒错误、repair 超限检查**确实阻断**。
- 对任一 UNKNOWN 明确报 UNKNOWN、给最窄所需证据、取消无价值反复查询。
- 仅桌面模拟的结果标为 PLANNED/ANALYTICAL；未接入 CI/分支保护不能标记 ENFORCED。

## 6. 修复“错误的工程考核指标”

不要再将这些算作成功：工程包个数、PR 个数、Review 回合数、脚本数量、系统复杂度、当前进程 CPU 活跃、文档长度。

应报告：
- 从用户提出研究假设到可信结论的实际时间（time-to-decision）；
- 原生/官方现成能力的复用比例与新增通用代码（目标尽可能零）；
- 真实新策略的复用成本及其对现有平台的修改范围；
- 只针对新 claim 的有效测试数与错误分类质量；
- 用户需要亲自操作/提醒/搬运的次数；
- 正确保存的数据/Trial/Reserve/Forward 身份；
- 是否取得真实、扣成本后且有独立证据的交易优势，而非模拟结果好看；
- 超时、废弃工作、后退到 Control 的次数和确切根因。

若业务没有推进，不能写“全部正常 / 已成功”来掩盖未完成。

## 7. 需要流程优化窗口遵守的真实边界

- CURRENT V5 manifest 是唯一宪法权威；本复盘及附录 prompt **仅用于指导提案/解释**。不能偷偷替换 V5、AGENTS 或技能文件。
- 现行项目主要机制已存在：成熟框架准入程序、研究证据决策方法、route A/B/C/D、Pre-code/Final Review、repair 上限、PR/CI/人类门禁。优先填**执行缺口**，不要加并行制度。
- 对合适成熟 owner 无法确定时，只允许一个有价值、时间有界、明确可证伪的官方兼容性验证；不能多建两个/三个 Spike 或把 Spike 变成永久组件。
- 无人授权对生产/runtime/cloud/credentials/钱包/订单/实盘、Mark Ready/Merge/branch deletion 产生任何自动推进；文档/计划 PASS 绝不等于人类授权。
- 复盘涉及的具体 PR #304/#310/#311 等可为风险说明，但**不因用户概括“违规修改”就推断全部这些 PR 已有证实越权**。必须基于精确 frozen package、实际变更路径、repair count、review 和 CI 证据逐项核实。
- 当前 G0 状态：R4 由明确人类授权停止、exit 143，240 Sidecar 完整来源仍作为存量资产、16 Reserve sealed、无 R4 正式研究结果。研究方案讨论稿未批准执行。
- 让 Engine owner 归位 Nautilus 的后续方案见同一文档 PR 的另一个文件：[统一策略研究 SOP](../research/STRATEGY_BACKTEST_AND_OPTIMIZATION_STANDARD_PROPOSAL_2026-10-09.md)。它是**讨论中的统一架构**，不是已验收运行接口。

## 8. 附录 A — 给流程优化 / Engineering Control 窗口的一键复制完整提示词

以下是此前为用户整理的“成熟框架优先、全局架构治理与统一策略研究流程”完整工作要求的独立可复制版本。它是**任务委托提示词而非系统级权威**。整段复制到新窗口即可；现行 GitHub manifest/宪法仍有更高优先级。

~~~~text
# Trade OS — 成熟框架优先、全局架构治理与统一策略研究流程

仓库：woshixiong/trader-assist-v0
角色：Engineering Control
当前阶段：全局架构审查、制度约束方案和策略研究流程设计
当前权限：只读研究和提出方案。未经用户后续明确授权，不修改代码、治理、CI、运行环境或策略，不启动回测，不创建实施 PR，不部署或合并。

## 一、核心目标

本任务必须解决以下长期问题：

1. Trade OS 不能反复开发成熟框架已经具备的能力。
2. NautilusTrader 应当成为通用交易和回测基础设施的主要责任方。
3. 项目自己的研发重点应当是交易策略、交易逻辑、研究假设及其独特的风险政策。
4. 不允许只解决单点故障，而不检查整个执行链路。
5. 后续新建策略、优化策略、重复回测，必须复用统一流程，而不是重新开发回测程序。
6. 优先缩短实际完成目标的时间，降低用户操作次数、工程复杂度和维护成本。
7. 必须建立能够阻断错误架构的实际约束，而不是仅添加提示词或治理条款。

成功标准不是增加了多少规则、文件或测试，而是以后能够更快、更可靠地完成策略研究，同时不再重复建设基础设施。

## 二、必须首先读取的权威信息

GitHub 是唯一的工程权威。新窗口必须从实时 GitHub 开始，不以旧聊天、记忆、历史 SHA 或旧结论作为权威。

严格按照当前项目规定读取：
1. AGENTS.md
2. governance/ACTIVE_GOVERNANCE_MANIFEST.json
3. Manifest 指定的唯一项目宪法
4. 当前任务的精确 Issue/package-state/PR
5. 当前阶段触发的最窄治理程序和技能

本次 G0 案例优先读取：
- 当前 Issue #161 package-state：https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6038693551
- 原 R4 中止证据：https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6064702223
- 已有 Nautilus-first 架构讨论：https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6066539312
- G0 原始研究冻结：https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6017065560

不得因为已有历史讨论就默认某一方案已获批准。

## 三、成熟能力优先的硬性约束

每项工程能力必须明确分类：
- STRATEGY_DIFFERENTIATOR：真正属于 Trade OS 的策略能力。
- COMMODITY_INFRASTRUCTURE：通用框架与基础设施能力。
- THIN_INTEGRATION：项目与成熟框架之间必要的薄适配。

不可仅根据模块或文件名称分类，必须检查实际承担的责任。

原则：如果成熟、经过验证且满足项目要求的实现已经存在，禁止再建设第二套项目自有的通用实现。

对于以下通用能力，首先检查 NautilusTrader 或已经采用的成熟官方方案：
- 历史数据目录、数据加载与标准转换；
- 事件回放、时间推进、调度和缓存；
- Bar 聚合、标准指标与数据订阅；
- 通用撮合、订单和持仓生命周期；
- 账户、组合、费用及标准风险基础设施；
- 回测引擎、运行管理及通用结果能力；
- 标准 CI、自动化运行和观测能力。

任何自研通用组件，在开发前必须提供：
1. 现有框架或现有项目能力的检查结果；
2. 官方文档和对应版本的证据；
3. 精确缺失的功能或不兼容语义；
4. 为什么官方配置、扩展接口或薄适配不能解决；
5. 自研的长期成本与替代、退出方案；
6. 独立审核结果；
7. 当前明确的人类例外授权。

任一必需证据缺失时，不得进入通用基础设施开发。

不能因为已有自建代码、迁移麻烦、时间紧迫、Writer 熟悉旧代码，就继续维持错误的双重架构。

## 四、全局架构审查，而非单点修补

每遇到一个重大性能、功能或兼容问题，必须首先检查从数据到结果的完整链路：
数据来源 → 数据验证 → Nautilus 数据目录 → 历史回放与时间 → 策略回调 → 策略决策 → 执行与费用 → 组合结果 → 研究证据。

检查：
- 是否存在两个组件承担相同基础设施责任；
- 是否重复遍历、转换、聚合或校验相同数据；
- 是否存在多份独立状态或重复的回测引擎；
- 是否错误地把策略规则与通用框架职责混合；
- 是否有官方已解决、我们却自行实现的能力；
- 当前修复是否会在下一个策略或数据集上重复出现。

连续出现相邻模块修复、性能问题或架构冲突时，立即返回 Engineering Control 重新分析全局责任归属，不允许继续连续局部修补。

不能把“缓存旧引擎中的重复计算”自动认定为最佳方案。必须先检查是否应直接让 Nautilus 承担这项通用职责。

## 五、建立一个长期复用的策略回测架构

目标架构：

NautilusTrader：负责成熟的通用回测运行机制。
Trade OS Strategy：负责策略独特的信号、Setup、结构识别、交易决策及策略专属风险规则。
Research Policy：负责试验预注册、样本隔离、候选比较、研究证据、统计充分性和策略晋级标准。

原则上所有策略使用同一个回测入口，通过更换配置、策略实现和已授权数据运行。

要求：
- 不为 Three Setup 专门维护第二个通用回测引擎；
- 不为其他新策略再建设独立历史回放系统；
- 不为不同数据集重复开发数据平台；
- 不为每次参数比较建立新的调参框架；
- 不为一次回测建设新的 CI、调度或监控基础设施。

优先验证当前锁定 Nautilus 版本的 BacktestNode、BacktestEngine、ParquetDataCatalog、Strategy.on_bar、Cache 与官方扩展接口。

注意：当前 G0 使用的 BAR_NEXT_OPEN_STOP_FIRST_V1 研究成交假设，不得未经验证直接认定为 Nautilus 默认 Bar 撮合结果。必须检查具体语义是否等价。若原生不支持，只处理该明确的策略研究差异，不得因此重建通用回测引擎。

## 六、以后所有新策略和优化任务的统一六阶段流程

### Stage 1 — 定义研究问题

冻结：
- 策略假设及其因果机制；
- 适用品种、时间周期和交易时段；
- 基准策略与现有 Champion；
- 预期改善的具体指标；
- 费用、滑点、成交和风险假设；
- 预声明成功、失败和停止条件。

不得为了追求漂亮的历史结果而临时改变目标。

### Stage 2 — 复用现有架构与数据

检查 Nautilus 现有能力和已批准的数据来源。

优先复用已有数据、数据目录、策略接口、测试和成本模型。

仅在真实缺失功能已获确认后，才讨论新增组件。

股票/RWA 与加密资产的数据质量、交易时段和交易成本必须分别正确处理。

### Stage 3 — 小规模技术验证

在正式大规模回测之前，用预先确定的代表性样本验证：
- 时间因果及无未来函数；
- 历史数据完整性和来源；
- 策略状态及事件生成；
- 成交、费用与风险语义；
- 正确的运行身份和结果完整性；
- 资源消耗、计算效率和扩展性。

设定运行时间预算及停止条件。

性能或正确性失败时不启动全量研究，也不得偷偷更换数据、框架版本或研究假设。

### Stage 4 — 正式回测与独立比较

使用已经批准的 Nautilus 原生流程。

执行事先冻结的候选和数据分组；维护完整的材料试验登记，禁止看到结果后追加未登记的候选。

评估至少包括：
- 扣除完整成本后的收益与风险；
- 相对简单基准的增量优势；
- 最大回撤、尾部损失和收益集中度；
- 样本数、独立事件和市场状态覆盖；
- 执行敏感性、滑点和费用敏感性；
- 样本外或后续 Forward 证据；
- 策略复杂度和实际可执行性。

统计工具按实际研究问题选用，不为了形式强制运行所有高级检验。

### Stage 5 — 明确研究结论

每轮研究只能得出有证据支持的结论：
- KEEP：保留当前策略；
- IMPROVE_ONCE：针对明确失败机制进行有界修改；
- MORE_INDEPENDENT_EVIDENCE：缺少真正独立的证据；
- STOP_OR_PARK：停止或暂缓研究。

若新增规则没有证明扣费后的实际增量价值，优先保留更简单的方案。

禁止无限调参、无限追加特征、重复窥探 Holdout 或反复利用相同历史挑选赢家。

### Stage 6 — Forward / Shadow

只有冻结版本可以进入后续验证。

必须保留 Strategy/Data/Code/Environment/Execution 身份，并保持真正独立的后续证据。

策略研究成功不自动授权生产部署、真实下单或实盘交易；遵守现有保护权限和独立晋级关卡。

## 七、未来策略工作应分三类处理

新策略：复用既有 Nautilus 运行环境，增加新的策略实现、配置和预注册研究假设。

优化旧策略：复用原有基准、数据合同和回测环境，只修改获批准的策略变量，并测试增量价值。

重复回测或新增样本：原则上只更换经批准的数据、时间范围或运行配置，不进行基础设施开发。

只有确实出现新的框架级能力需求，才重开成熟能力选择和架构评审。

## 八、把治理规则真正变为阻断机制

在现有治理、Codex 和 GitHub CI 中，设计最小的强制能力归属检查。

要求：
1. 工程包必须有明确的能力分类及现有成熟框架责任方。
2. 如使用自建通用实现，必须有独立核实的例外证据和人类授权。
3. Writer 的 Plan 与独立 Pre-code Review 必须验证责任归属，不能只检查代码是否完成需求。
4. 通过已有 CI 对最少的结构化证据、受控文件范围和未经批准的通用基础设施变更进行机械检查。
5. 需要判断语义归属的部分由独立 Reviewer 审查，不能假装静态脚本可以自动理解所有架构。
6. 使用 GitHub 现有分支保护和必需检查功能；首先核实当前仓库权限，不能假定已经强制生效。
7. 普通策略修改复用已批准的架构证据，不重复进行完整框架选型。
8. 不新增治理服务、审批平台、控制器或第二套 CI。

遵守当前 V5 的角色分离、精确 Writer 续接、Review 写回 GitHub 和受保护动作授权规则，不额外创造平行治理体系。

## 九、管理员模拟必须覆盖完整工作流

在提出最终实施方案之前，以 Engineering Control 的身份进行桌面演练：

情境 A：新建策略，只修改 Strategy 和配置。确认不触发不必要的基础设施开发。
情境 B：发现性能问题。确认首先分析整个数据与执行链路，不能直接对一个函数做无止境优化。
情境 C：Nautilus 存在与研究假设不同的执行语义。确认会停在具体兼容性问题，而不是另造撮合引擎。
情境 D：数据质量不足或样本过少。确认不会偷偷更换数据或提前打开封存样本。
情境 E：连续测试失败。确认按照现有 V5 修复预算返回 Control，不允许循环补丁。
情境 F：当前任务已完成，但出现新策略。确认可复用既有运行平台，不需要重做架构审核和通用回测程序。
情境 G：用户未授权代码或云端运行。确认不能因方案审查 PASS 就自动执行。

必须报告每个情境是否通过、发现的问题和阻断条件。桌面演练不得被宣称为真实运行验证。

## 十、最终交付内容

先只读完成研究并交付：

1. 根因复盘：为什么已有治理没有阻止重复建设。
2. 全局责任清单：哪些能力由 Nautilus 提供，哪些保留在 Trade OS Strategy，哪些自建能力应逐步退役。
3. 长期标准流程：新策略、策略优化、重复回测如何统一操作。
4. 最小治理强化方案：仅列出真正需要补强的现有规则、CI 或审核检查，不新增平台。
5. 一次性迁移方案：如何从现有 G0 自建回放转向统一 Nautilus 路线，并明确成交语义兼容条件。
6. 管理员模拟结果：完整业务链路、失败条件、权限和性能检查。
7. 执行成本与优先级：说明最快能取得研究结果的路线，以及哪些非必要工作应该取消。
8. 明确的实施边界：现在仅输出待批准方案，不得执行实现。

不要用大量 PR、代码行数、测试数量或审查轮数衡量成果。

优先级依次是：
真实业务结果 → 正确性与安全性 → 成熟能力复用 → 简单性 → 执行速度与长期维护成本。

不得以速度为由放宽数据完整性、权限或因果正确性要求，也不得以形式化合规为由不断扩大工程范围。

最后必须给用户一个不超过一页的简明管理总结，说明推荐路线、为什么不是造轮子、哪些旧能力可直接复用、预计最少需要几次实施阶段和还有什么必须由用户决定。

按当前 GitHub 治理，在预期停止处输出：
DECISION=
CANONICAL_GITHUB_REF=
NEXT_DESTINATION=
NEXT_ACTION=
COPY_PASTE_COMMAND_OR_PROMPT=

目前只有审查和方案设计权限。必须等待用户对最终路线单独作出明确决定。
~~~~

## 9. 附录 B — 交付新窗口时的额外纠错提醒（不得替换附录 A）

如果流程优化窗口只抓住“再加入一条口号”或“写个新控制器”，必须立刻 STOP。真正交付的主张是：

- **立法已经存在，缺的是执行门槛**：基于 V5 目前实际 CI/hook 做最小、可验收的阻断；不给正常策略工作增加不必要审核。
- **全局职责检查优先**：已有 Nautilus 官方 owner，不得从优化旧自研 loop 开始。
- **可观察异常必须公开**：进程活跃不代表技术完成；错误类别、repair count、第一真实 blocker 必须写入 GitHub。
- **极简实施**：若获未来许可，一项 narrow capability gate/Review 复用现有 controller/CI；一项统一 Nautilus 策略回测路线，禁止 parallel custom platform。
- **管理员模拟一定包括正常路径与恶意/失败路径**，避免新规则变成另一层维护负担。
- **权限与证据严格分离**：当前文档两份仍为提案，不能借写文档自动推进迁移或 G0 回测。

## 10. 可核查的权威线索与状态

- [AGENTS.md](https://github.com/woshixiong/trader-assist-v0/blob/main/AGENTS.md) → [ACTIVE_GOVERNANCE_MANIFEST.json](https://github.com/woshixiong/trader-assist-v0/blob/main/governance/ACTIVE_GOVERNANCE_MANIFEST.json) → 当前 manifest 指定的唯一宪法。
- [成熟方案评估规范](https://github.com/woshixiong/trader-assist-v0/blob/main/governance/EXTERNAL_MATURE_SOLUTION_SELECTION_AND_ADOPTION_RULE_V1_2026-09-07.md)。
- [研究价值/自适应过拟合/简化判断](https://github.com/woshixiong/trader-assist-v0/blob/main/governance/PROJECT_RESEARCH_EVIDENCE_DECISION_METHOD_V1_2026-08-16.md)。
- [真实 G0 package Revision 22](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6038693551)；[R4 中止 exit143](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6064702223)；[9h 延迟诊断](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6063927940)；[最初缓存/stdlib 提案](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6064480887)；[后续 Nautilus-first 架构纠正](https://github.com/woshixiong/trader-assist-v0/issues/161#issuecomment-6066539312)。
- [一次真实预审 FAIL 示例](https://github.com/woshixiong/trader-assist-v0/issues/163#issuecomment-6058088035) 仅作为系统应正确区分失败与修复的证据，不据此推定该 PR repair 超限。
- [项目现有 CI](https://github.com/woshixiong/trader-assist-v0/blob/main/.github/workflows/ci.yml)、[Codex Hook](https://github.com/woshixiong/trader-assist-v0/blob/main/.codex/hooks/pre_tool_use_policy.py) 可检查当前治理阻断缺口。
- [Nautilus v2.0.0rc5 Strategy](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/docs/concepts/strategies.md)、[Cache](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/docs/concepts/cache.md)、[bar fill 限制](https://github.com/nautechsystems/nautilus_trader/blob/v2.0.0rc5/docs/concepts/backtesting/bar-execution.md)。

## 11. 文档交付之后的决策边界

当前仅按用户明确要求把**两个完整 Markdown 文档提交到 GitHub**，供流程优化窗口阅读；不修改生效 governance，不改 source/config，不授权新研究或修复，不允许合并 Draft PR。

**用户下一步若要求具体实施：** 从 live GitHub 重读身份和现行权限；再决定是否批准最小 V5 强制准入调整、Nautilus-native 迁移，或者只保留文档；三者是互相独立的许可，不可把其中一个当作其他动作的授权。

~~~text
DECISION=FULL_ENGINEERING_RETROSPECTIVE_AND_COPY_PASTE_PROMPT_DOCUMENTED_ONLY
CANONICAL_GITHUB_REF=THIS_DOC_ON_DOCS_BRANCH_PENDING_REVIEW
NEXT_DESTINATION=PROCESS_OPTIMIZATION_CONTROL_DISCUSSION
NEXT_ACTION=READ_BOTH_DOCS;VERIFY_EVIDENCE;PROPOSE_MINIMAL_HARD_GATES_WITHOUT_EXECUTION
COPY_PASTE_COMMAND_OR_PROMPT=USE_APPENDIX_A_AFTER_REFRESHING_LIVE_GITHUB_AND_CURRENT_HUMAN_AUTHORITY
~~~
