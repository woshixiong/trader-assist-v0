# Trader Assist Engineering Automation Track v1

**TRACK_ID:** `ENGINEERING-AUTOMATION-TRACK-V1-2026-07`
**定位：** 与产品主线并行的长期工程能力主线
**目标：** 降低交付时间、用户机械操作和执行型 Agent Token/API 成本，同时保留 exact-object、权限隔离和独立审查

> ChatGPT 常规总控/讨论窗口不计入本 Track 的 Agent Token 预算。成本优化对象是 Codex、DeepSeek API、Claude Code 等执行型 Agent 和外部 API。

## 1. 原则

- 产品开发不中断；自动化以短、可回收、可独立验收的任务穿插推进。
- 自动化不能削弱 Writer/Reviewer/Finalizer 隔离、scope、CI 和人工授权门。
- 先自动化确定性重复劳动，再做 Agent orchestration，最后才做项目控制辅助。
- 自动化系统本身也走 branch、PR、测试、Review 和回滚。
- 一个自动化任务若能短期解除关键瓶颈并惠及大量后续任务，可与产品任务同等或更高优先，但必须通过 payback gate。

## 2. 阶段路线图

| 阶段 | 名称 | 核心能力 | 进入下一阶段门槛 |
|---|---|---|---|
| M0 | Baseline & Contract Freeze | FastSafe、统一 handoff、Evidence Pack schema、测量基线 | authority sync 完成；合同生效；首个 pilot 冻结 |
| M1 | Deterministic Workflow Automation | 状态快照、证据包、handoff、工具预检、Agent 成本分类 | 连续 2 个产品任务使用脚本，无证据错误/流程回滚 |
| M2 | Bounded Development Orchestration | worktree、Agent 调用、测试、单 repair loop、人工 gate | 连续 2-3 个任务，无 collision、scope drift 或无限循环 |
| M3 | Project-Control Assistance | 进度、自动化候选、模型路由、backlog、延期预警 | 至少 5 个任务数据，建议可核验且不越权 |
| M4 | Scaled Strategy/Research Factory（可选） | 多策略、因子研究、实验批次和复现包 | 产品需要且 M1-M3 稳定、收益高于维护成本 |

## 3. M0：基线与合同冻结

交付：

- `FASTSAFE_V1_MASTER_CONTROL_CONTRACT.md`
- Handoff v1 字段
- Evidence Pack v1 schema
- PR #19 与首个 pilot 的基线指标
- Engineering Backlog

退出条件：authority sync 完成；FastSafe 激活；首个产品 pilot 开始使用统一 handoff 和 Evidence Pack。

## 4. M1：第一阶段确定性流程自动化

M1 只做无歧义机械操作，脚本运行本身为 **0 Agent Token**。

### 4.1 组件

| 组件 | 建议路径 | 输出 |
|---|---|---|
| Project Snapshot | `scripts/control/project_snapshot.py` | main/branch/PR/head/base/status/CI/lease 快照 |
| Evidence Pack | `scripts/control/evidence_pack.py` | `evidence-pack.json` + `.md` |
| Handoff Generator | `scripts/control/handoff.py` | 固定短 handoff |
| Tooling Preflight | `scripts/control/tooling_preflight.py` | Writer/Reviewer/Finalizer 能力检查 |
| Agent Cost Classifier | `scripts/control/agent_cost_log.py` | 实现、Review、repair、取证、格式化分类 |
| Retrospective Generator | `scripts/control/retrospective.py` | 固定 10 问 + backlog 候选 |

### 4.2 边界

- 默认只读 Git/GitHub；不得 push、merge、delete branch 或改产品文件。
- 测试命令来自 task contract，脚本不得自行扩大测试或 scope。
- 输出在 worktree 外或 ignored 目录。
- 输出包含 schema version、timestamp、source SHA、command、exit code 和 integrity hash。
- 异常 fail closed；不得自动修复。
- M1 不调用外部 Agent 自动写代码。

### 4.3 子里程碑

| 子里程碑 | 内容 | 退出标准 |
|---|---|---|
| M1.1 | Execution Launch Packet schema + Tooling Preflight CLI + validation | schema tests 全通过 |
| M1.2 | Project Snapshot + Evidence CLI | 在至少两个对象上可重复生成一致结果 |
| M1.3 | Handoff Generator and role templates | 三类角色模板通过 |
| M1.4 | Agent Cost + Retrospective | 自动更新 Engineering Backlog |
| M1.5 | Hardening、跨平台、错误处理、CI | 连续 2 个产品任务无证据错误/流程回滚 |

第一版是若干小型 Python CLI，不是大型服务；复杂工作从 M2 开始。

## 5. M2：Bounded Development Orchestration

自动连接：

`Task Contract → Isolated Worktree → Agent Writer → Tests → Evidence → Independent Review → One Repair Loop → Finalizer Packet`

必须保留：

- 单 Writer、单 lease；
- 最多一次自动 repair；
- 无 force push/rebase；
- 无自动 merge；
- 不传递 secrets；
- scope/allowlist 变化和最终授权由人工决定；
- 第二次 Review 仍 BLOCKED 时停止。

进入条件：M1 连续两个产品任务无证据漂移、无 scope 越界。
退出条件：连续 2-3 个低/中风险 pilot 完成，零 writer collision、零未批准 scope drift、零无限循环。

## 6. M3：项目控制辅助自动化

自动化建议和监控，不自动化最终 authority：

- 关键路径、里程碑、等待时间和 process delay；
- 过度拆分、重复全量测试、工具不匹配和重复 handoff；
- 依据风险、Agent 余额和历史效果建议模型路由；
- 自动化候选评分和 backlog；
- 建议唯一下一步，由总控接受后生效。

不得自动授权产品范围、runtime、账户、Testnet/Mainnet、交易、资金或 merge。

进入条件：至少 5 个 FastSafe 任务数据。

## 7. M4：规模化策略/因子研究工厂（方向性）

在多策略、因子研究和大量实验阶段再冻结细节。可包括数据快照、批次实验、参数/结果 hash、复现包和策略注册流程。研究 Agent 不得自动晋升策略到生产 registry；回测、shadow、Review、enable 和真实交易权限继续分离。

## 8. 自动发现与自我迭代

每个产品里程碑结束后，系统自动运行 Micro Retrospective，无需用户提醒。候选评分：

```text
REPETITION: 0-3
DETERMINISM: 0-3
AGENT_TOKEN_SAVING: 0-3
HUMAN_TIME_SAVING: 0-3
RISK_REDUCTION: 0-3
BUILD_COST: 0-3
FAILURE_RISK: 0-3
PAYBACK_TASKS: 1-5+
DECISION: KEEP | MERGE | AUTOMATE | DELETE | DEFER
```

默认自动化准入：重复≥2 或未来高频；确定性≥2；失败可安全停止；预计 2-5 个任务回收；不削弱角色隔离或 authority。

## 9. Engineering Backlog

```text
CANDIDATE_ID:
SOURCE_TASK:
ACTION_DESCRIPTION:
CURRENT_MANUAL_STEPS:
FREQUENCY:
DETERMINISM:
AGENT_TOKEN_CLASS:
ESTIMATED_TOKEN_SAVING:
ESTIMATED_HUMAN_TIME_SAVING:
BUILD_COST:
MAINTENANCE_COST:
FAILURE_MODE:
SAFE_STOP:
PAYBACK_TASKS:
TARGET_MILESTONE:
OWNER:
STATUS: PROPOSED | APPROVED | BUILDING | PILOT | ACCEPTED | REJECTED | DEFERRED
ACCEPTANCE_TESTS:
RESULT_METRICS:
```

## 10. Agent Token 成本等级

| 等级 | 工作 | 默认资源 |
|---|---|---|
| P0 Deterministic | git/SHA/diff/test/CI/log hash/schema | 本地脚本，0 Agent Token |
| P1 Low-cost cognition | 日志摘要、机械 patch、测试候选、长文本整理 | DeepSeek/低成本 Agent |
| P2 Product implementation | bounded 功能、跨文件语义、复杂测试 | Codex-first（余额≥30%） |
| P3 Critical reasoning | 交易安全、状态机、risk、precision、疑难 blocker | Codex/高能力 Reviewer |
| P4 Human authority | scope、权限、merge、runtime/资金 | 用户 + Project Control |

优化方法：delta context、共享 Evidence Pack、脚本先压缩日志、禁止多个 Agent 重复仓库调查、低于 30% 切执行层而非暂停开发、低于 10% Codex 紧急保留。

## 11. 产品与工程主线节奏

- 产品里程碑冻结：引用 FastSafe，记录基线。
- 产品执行中：工程线只收集事件和候选，不改当前流程。
- 产品闭环：自动短复盘，选择 0-1 个最高回报候选。
- 两个产品任务之间：完成一个 bounded Engineering task。
- 高重复痛点已阻塞产品：通过 payback gate 后可提升工程任务优先级。

## 12. 阶段指标

M1：handoff 减少 60%-80%，低价值 Agent 使用减少 25%-50%，用户机械操作减少约 70%，连续两个任务零证据错误。
M2：状态/证据接近零高价值 Agent 调用，人工只处理授权和异常，repair 0-1 轮。
M3：exception-based management，自动发现流程漂移和模型路由机会。

任何出现证据错误、writer collision、未批准 scope drift、无限循环或错误 merge，立即降级到上一稳定阶段。

## 13. GitHub 结构

```text
governance/FASTSAFE_V1_MASTER_CONTROL_CONTRACT.md
governance/ENGINEERING_AUTOMATION_TRACK_V1.md
engineering/control/README.md
schemas/control/project-snapshot-v1.schema.json
schemas/control/evidence-pack-v1.schema.json
schemas/control/handoff-v1.schema.json
schemas/control/engineering-backlog-v1.schema.json
scripts/control/project_snapshot.py
scripts/control/evidence_pack.py
scripts/control/handoff.py
scripts/control/tooling_preflight.py
scripts/control/agent_cost_log.py
scripts/control/retrospective.py
tests/control/...
# M2 可选：
.github/workflows/control-evidence.yml
scripts/control/orchestrator.py
```

## 14. 首批 Backlog

1. E1 — Evidence Pack CLI
2. E2 — Project Snapshot + drift check
3. E3 — Role-specific short handoff generator
4. E4 — Reviewer tooling preflight
5. E5 — Micro retrospective + backlog update
6. E6 — Agent cost classifier
7. E7 — Bounded orchestrator pilot（M2）

## 15. 启动顺序

1. 当前 authority-state sync 合并、post-merge CI 通过并被总控接受。
2. 新总控激活 FastSafe v1，冻结下一完整产品里程碑。
3. 两份合同通过独立 governance-only PR 存入 GitHub。
4. 首个产品 pilot 使用统一 handoff/Evidence 格式并收集 baseline。
5. 执行 M1.1-M1.2。
6. 第二个产品任务使用 M1 脚本；完成 M1.3-M1.4。
7. 连续两个任务稳定后评估 M2。
8. 至少五个任务数据后再决定 M3。
