# Trader Assist 工程优化与多 Agent 工作流总方案 v1

```text
DOCUMENT_ID:
TRADER-ASSIST-ENGINEERING-OPTIMIZATION-AND-MULTI-AGENT-WORKFLOW-V1-2026-07

VERSION:
1.0.0

DATE:
2026-07-19

APPLICABILITY:
- Trader Assist V0
- First Launch
- Trade OS 主线项目
- 后续独立策略、数据、执行、Dashboard 与工程自动化任务

PRIMARY_OBJECTIVE:
在不降低质量、安全性、可审计性和权限隔离的前提下，缩短开发关键路径，提高开发速度，减少用户等待、复制粘贴和人工转述工作。

DOCUMENT_STATUS:
HUMAN_READABLE_ENGINEERING_BASELINE

MACHINE_ENFORCEMENT_STATUS:
PARTIAL

RUNTIME_OR_TRADING_AUTHORITY_GRANTED:
NO
```

---

## 1. 文档定位

本文件统一冻结以下内容：

1. 既有工程优化方案；
2. 新的多 Agent 协作方案；
3. Codex、ChatGPT、Trae、OpenCode 与候选 Agent 的职责；
4. 单 Writer 与未来双 Writer 的边界；
5. 逐阶段自动化和并行化路线；
6. 降低用户复制粘贴、等待和人工核对成本的长期方案；
7. 适用于 First Launch、V0 和 Trade OS 主线的共同规则。

本文件只控制工程工作流，不授予以下权限：

- 产品范围扩张；
- 账户、钱包、凭证、签名或 nonce；
- Testnet 或 Mainnet 交易写入；
- 自动下单、取消、自动 SL/TP；
- LIVE_SHADOW 或生产运行；
- 自动 Mark Ready、merge 或分支删除；
- 资金和交易权限。

当本文件与旧的人类可读 Agent 路由规则冲突时，本文件代表最新工程优化裁定。  
现有机器脚本、Schema 和测试在完成 `ENGINEERING-AGENT-CAPABILITY-REGISTRY-AND-ROUTING-V1` 前仍可能包含旧的 30%/10% 路由，因此必须 fail closed，不得依赖旧脚本自动切换 Writer。

---

## 2. 核心目标和优先级

工程优化的优先级固定为：

1. **质量与交易安全**
2. **项目上线速度**
3. **缩短关键路径**
4. **减少人工传递与等待**
5. **降低 Codex Token、Agent API 和重复 Review 成本**
6. **提高自动化程度**
7. **保持审计、回滚和权限隔离**

效率优化不得通过以下方式实现：

- 多个 Agent 同时修改同一文件；
- Writer 与最终 Reviewer 合并为同一角色；
- 跳过 exact-base、exact-head、测试、CI 或独立 Review；
- 自动扩大 scope；
- 自动绕过 Write Lease；
- 自动 merge；
- 未验证 Agent 直接写交易关键代码；
- 用更多 Agent 制造重复报告和整合负担。

---

## 3. 控制平面与执行平面

### 3.1 控制平面

普通 ChatGPT 窗口承担：

- 工程优化；
- Project Control；
- 项目状态判断；
- 任务拆分；
- scope、base、branch、allowlist 和验收标准冻结；
- Agent 选择与路由；
- Review 结果合并；
- repair 授权；
- finalization 提示词；
- 窗口轮换；
- 里程碑、时间和风险控制。

规则：

```text
DEFAULT_PERMISSION:
STRICT_READ_ONLY

MODEL_POLICY:
使用当时平台可用的最高能力模型和最高思考等级。

PRODUCT_WRITE_AUTHORITY:
NONE，除非单独明确授权。
```

控制平面输出必须尽量形成一次可执行的完整 Packet，避免用户在总控、工程优化、Writer 和 Reviewer 之间反复搬运增量补丁。

### 3.2 执行平面

执行平面包括：

- Codex；
- Trae 中的指定模型；
- OpenCode + 用户自有 DeepSeek API；
- 后续通过验证的其他 Agent Harness；
- 本地 deterministic scripts。

默认结构：

```text
PRODUCT_WRITE_LANES:
1

READ_ONLY_AUXILIARY_LANES:
最多 2

INTEGRATION_WRITE_LANES:
0，直到并行写入协议通过试点
```

多 Agent 并行默认表示：

- 一个正式 Writer；
- 一个只读 contract/test-gap/CI 辅助 Agent；
- 一个独立只读 Review 或 capability pilot Agent。

不表示三个 Agent 同时修改同一代码范围。

---

## 4. Codex 配额和连续性规则

```text
CODEX_PRIMARY_WRITER_THRESHOLD:
remaining >= 40%

CODEX_CONTINUITY_INTAKE_TRIGGER:
remaining < 40%

CODEX_EMERGENCY_RESERVE:
20%
```

### 4.1 Codex 剩余额度不低于 40%

Codex 默认作为主要产品 Writer，适合：

- 关键产品代码；
- 状态机；
- 风险、TradePlan 和交易安全逻辑；
- 跨文件语义实现；
- 独立 Review 后的唯一 repair；
- CI 修复；
- 提交、push 和 Draft PR 发布。

### 4.2 Codex 剩余额度低于 40%

必须先执行 resource-continuity intake：

- 评估当前任务剩余工作；
- 判断 Codex 是否应完成当前任务；
- 保留 20% 紧急储备；
- 缩小后续 Codex 任务；
- 评估是否存在已验证的 alternate Writer；
- 不得在任务中途无控制转移；
- 不得把未验证 Agent 自动升级为 Writer。

### 4.3 Alternate Writer 必要条件

非 Codex Writer 必须同时满足：

1. 精确 Harness + Model 组合已通过 capability qualification；
2. 当前 qualification 未失效；
3. 正式 handoff 完成；
4. 新的 exact Write Lease 已签发并确认；
5. 独立 branch、worktree 和 path allowlist 已冻结；
6. 任务不属于禁止试点的高风险范围；
7. Project Control 明确授权。

---

## 5. Agent 能力矩阵

能力属于**精确 Harness + Model 组合**，不得把某个模型在一个 Harness 中的表现迁移到另一个 Harness。

### 5.1 Codex

```text
ROLE:
PRIMARY_PRODUCT_WRITER

CAPABILITY:
产品写入、测试、commit、push、Draft PR

WRITE_REQUIREMENT:
exact active Write Lease

CURRENT_PRIORITY:
Codex remaining >= 40% 时优先

FINAL_REVIEW_ROLE:
PROHIBITED_FOR_ITS_OWN_PR
```

每个任务记录平台实际显示或用户报告的模型和 reasoning level；无法验证时不得虚构。

### 5.2 Trae + DeepSeek-V4-Pro

```text
CURRENT_LEVEL:
LEVEL_1_READ_ONLY_PREPARATION_APPROVED

PRODUCT_WRITE_AUTHORITY:
NO
```

默认任务：

- 复杂 contract attack；
- 状态机边界分析；
- test-gap analysis；
- 架构冲突识别；
- CI 失败根因分析；
- exact-head 辅助 Review；
- repair 建议准备。

### 5.3 Trae + DeepSeek-V4-Flash

```text
CURRENT_LEVEL:
PILOT_REQUIRED
PRODUCT_WRITE_AUTHORITY:
NO
```

候选任务：

- 长日志压缩；
- CI step 与 exit-code 核对；
- changed-file inventory；
- Evidence Pack 整理；
- 报告结构和格式检查；
- 低成本机械分析。

通过 bounded read-only pilot 后可晋级为低成本只读辅助资源。

### 5.4 Trae + GLM-5.2

```text
CURRENT_LEVEL:
LEVEL_0_RETAINED

PRODUCT_WRITE_AUTHORITY:
NO

NEXT_GATE:
一次额外 bounded read-only pilot
```

既有表现：

- 总体方向正确；
- 没有仓库 mutation；
- 没有 blocking false positive；
- 漏掉一个 authoritative LOW；
- 报告 Schema 和长度要求未完全满足。

晋级 Level 1 的最低条件：

```text
TOTAL_BOUNDED_PILOTS:
2

MISSED_CRITICAL_OR_HIGH:
0

MISSED_AUTHORITATIVE_MEDIUM:
0

BLOCKING_FALSE_POSITIVE:
0

REPORT_SCHEMA_COMPLIANCE:
PASS

LENGTH_COMPLIANCE:
PASS

REPOSITORY_MUTATION:
NONE
```

在晋级前，不得作为产品 Writer或唯一最终 Reviewer。

### 5.5 OpenCode + 用户自有 DeepSeek API

```text
STATUS:
PLANNED_PRIMARY_ALTERNATE_HARNESS

CURRENT_VALIDATION:
UNVALIDATED

PRODUCT_WRITE_AUTHORITY:
NO
```

建议模型路由：

- DeepSeek-V4-Pro：复杂只读 Review、测试设计、低风险工程代码候选；
- DeepSeek-V4-Flash：日志、证据、机械任务和低成本批处理。

晋级路线：

1. Provider 和工具连接预检；
2. exact-object 只读 intake；
3. 第一次 bounded read-only Review；
4. 第二次 bounded read-only Review；
5. 非关键工程工具 Writer pilot；
6. 独立低风险模块 Writer pilot；
7. alternate product Writer candidate。

首个 Writer pilot 不得使用：

- First Launch 关键 runtime；
- 风险计算；
- TradePlan；
- 订单执行；
- account、wallet、credentials；
- persistence 核心 Schema；
- LIVE_SHADOW；
- Testnet/Mainnet 写入。

### 5.6 Kimi-K2.7-Code、MiniMax-M3 和其他 Trae 模型

当前状态：

```text
VALIDATION_STATUS:
UNVALIDATED

DEFAULT_PRODUCTION_ROUTE:
NO
```

可以做小型只读 pilot。只有在以下至少一项明显优于现有组合时才纳入长期默认路由：

- blocker recall；
- 误报率；
- 速度；
- 长上下文；
- 报告遵循；
- 成本；
- 工具使用稳定性。

不因为模型数量多而全部纳入，以避免能力注册和维护成本膨胀。

### 5.7 Claude Code + DeepSeek

```text
STATUS:
PROVIDER_CONNECTION_ONLY
UNVALIDATED_EMERGENCY_FALLBACK

PRODUCT_WRITE_AUTHORITY:
NO
```

不得被旧脚本自动路由为 Writer。未来若使用，必须重新完成精确 Harness + Model capability pilot。

---

## 6. 单 Writer 和并行写入规则

### 6.1 当前 First Launch

```text
FIRST_LAUNCH_PRODUCT_WRITE_LANES:
1
```

Package 2、3、4 使用共享 runtime 路径并存在顺序依赖，继续串行。

允许同步的只读任务：

- contract attack；
- test-gap analysis；
- CI/log 分析；
- exact-head Review；
- capability pilot；
- Evidence 准备。

### 6.2 未来 V0 和 Trade OS 主线

未来允许最多两个产品 Writer，但只有在 `ENGINEERING-PARALLEL-WRITE-LANES-V1` 通过后生效。

```text
V0_OR_MAINLINE_MAX_PRODUCT_WRITE_LANES:
2

READ_ONLY_AUXILIARY_LANES:
2

INTEGRATION_WRITE_LANES:
1
```

### 6.3 双 Writer 必要条件

两个 Writer 并行写代码必须满足：

1. 两个任务的 path allowlist 完全不重叠；
2. 不共享可变 Schema、migration、lockfile、package export、配置或生成文件；
3. 接口先冻结；
4. 各自有独立测试；
5. 一个 Lane 失败不会使另一个实现失效；
6. 每个 Lane 有独立任务 ID、branch、worktree、Writer 和 Write Lease；
7. 有单独的 Integrator；
8. 集成成本预计小于关键路径节省；
9. 最终组合对象有完整集成测试和独立 Review；
10. 用户单独授权最终 merge。

### 6.4 禁止的双 Writer 方式

禁止：

- 同一 branch；
- 同一 worktree；
- 同一文件；
- 同一状态机；
- 同一数据库 migration；
- 同一 persistence Schema；
- 同一风险计算链；
- 同一订单执行链；
- 相互 cherry-pick 未冻结中间对象；
- Writer 自行扩大到另一 Lane 的范围；
- 两个 Agent 同时改依赖或 lockfile。

发现需要跨 Lane 修改时必须返回：

```text
PARALLEL_LANE_BOUNDARY_BLOCKED
```

### 6.5 推荐 Integration Branch 模型

```text
main@FROZEN_BASE
        |
        +-- integration/<epic>
               |
               +-- lane-a/<task-a>
               |
               +-- lane-b/<task-b>
```

流程：

1. 从 exact main 创建 integration branch；
2. Lane A/B 从同一个 integration base 创建；
3. 各自实现、测试和独立 Review；
4. Lane PR 目标为 integration branch；
5. 独立 Integrator 按冻结顺序整合；
6. 对 integration head 执行完整集成测试；
7. 创建 integration → main 的最终 PR；
8. 对 exact integration head 做独立 Review；
9. 用户授权 merge。

### 6.6 最适合双 Writer 的任务

- 两个独立交易所 adapter；
- 两个独立数据源 connector；
- Dashboard 前端与冻结 API 后端；
- 两个独立策略模块；
- 报表引擎与采集模块；
- CLI 与后台服务；
- Project Snapshot 与 Handoff Generator；
- 不同 package、service 或 repository。

---

## 7. 标准产品任务节奏

```text
T0 — Project Control
冻结 task、base、branch、worktree、allowlist、Writer、测试和停止条件。

T1 — Parallel Preparation
Writer 开始实现。
辅助 Agent 做只读 contract attack 或 test-gap。
另一 Agent 做 capability pilot、日志或 Evidence 准备。

T2 — Exact Head Publication
Writer commit、push、创建 Draft PR。
冻结 exact head SHA。

T3 — Parallel Read-Only Review
独立 ChatGPT exact-head Review。
最多一个辅助 Agent Review，避免重复报告。

T4 — Consolidation
Project Control 去重 findings，只保留真实 blocker，生成一份 repair Packet。

T5 — One Writer Repair
原 Writer 执行最多一个 consolidated repair commit。

T6 — Exact Re-review
复核 repaired exact head。

T7 — User Finalization
单独授权 Mark Ready、merge 和 main refreeze。

T8 — Micro Retrospective
记录耗时、等待、Token、返工、Agent表现和下一自动化候选。
```

---

## 8. 现有工程自动化路线与多 Agent 方案合并

### Milestone E0 — 本文档基线

交付：

- 本文件；
- 本地 Markdown 留底；
- GitHub 独立文档分支和 Draft PR；
- 不修改产品代码；
- 不激活 runtime 或交易权限。

### Milestone E1 — Agent Capability Registry 与路由修复

```text
TASK_ID:
ENGINEERING-AGENT-CAPABILITY-REGISTRY-AND-ROUTING-V1

CHECKPOINT:
Package 2 merge + post-merge main refreeze 后

ESTIMATED_ACTIVE_ENGINEERING:
5–8 小时

ESTIMATED_REVIEW_AND_REPAIR:
2–4 小时
```

内容：

- 40% continuity threshold；
- 20% emergency reserve；
- 精确 Harness + Model 注册；
- pilot evidence；
- promotion/demotion；
- alternate Writer handoff；
- exact Write Lease 机器门；
- 删除旧 30%/10% 自动路由；
- 禁止未验证 Agent 成为 Writer；
- Schema、脚本和测试同步。

### Milestone E2 — Deterministic Project Snapshot 与 Evidence Pack

```text
CHECKPOINT:
Package 3 merge 后

ESTIMATED_ACTIVE_ENGINEERING:
6–10 小时
```

交付候选：

- `scripts/control/project_snapshot.py`
- `scripts/control/evidence_pack.py`
- drift check
- project snapshot Schema
- evidence pack Schema
- deterministic tests

目标：

- 自动收集 main、branch、base/head、PR、CI、lease 和 scope；
- 用户不再手工搬运大段状态；
- Writer、Reviewer 和 Finalizer 共享同一 Evidence Pack。

### Milestone E3 — Handoff Generator、Agent Cost 与 Retrospective

```text
CHECKPOINT:
Package 4 周期或其后

ESTIMATED_ACTIVE_ENGINEERING:
8–14 小时，按独立小任务拆分
```

交付：

- role-specific handoff generator；
- Agent cost log；
- micro retrospective；
- engineering backlog 更新；
- 固定的 Packet Schema；
- 用户机械复制步骤显著下降。

### Milestone E4 — OpenCode Agent Adapter 与能力试点

内容：

- OpenCode + DeepSeek provider/tool preflight；
- exact-object 只读任务；
- 两次 Review pilot；
- 非关键工程工具 Writer pilot；
- Evidence 格式统一；
- capability registry 自动读取。

### Milestone E5 — Parallel Write Lanes Pilot

```text
TASK_ID:
ENGINEERING-PARALLEL-WRITE-LANES-V1

ENTRY_GATE:
- E1 完成
- E2/E3 关键基础可用
- OpenCode alternate Writer qualification 通过
- M1.5 稳定性门通过

FIRST_PILOT:
Lane A — Project Snapshot
Lane B — Handoff Generator
```

要求：

- 完全不重叠路径；
- 独立 branch/worktree/lease；
- Integration Branch；
- 独立 Review；
- 最终集成测试；
- 零 Writer collision；
- 零 scope drift。

### Milestone E6 — Bounded Multi-Agent Orchestrator

目标链：

```text
Task Contract
→ State Snapshot
→ Worktree Manager
→ Agent Lane Scheduler
→ Writer
→ Validation Runner
→ Evidence Pack
→ Independent Review
→ One Repair Loop
→ Integration
→ Human Finalization
```

Orchestrator 必须：

- 默认 fail closed；
- 不自动 merge；
- 不自动扩 scope；
- 不传递 secrets；
- 不授权 runtime 或资金；
- 第二次 Review 仍失败时停止；
- 所有副作用可审计；
- 每条 Lane 有独立权限和 Evidence。

### Milestone E7 — Exception-Only Human Operation

长期目标：

用户只处理：

- scope 和优先级；
- blocker 和例外；
- 高风险架构；
- alternate Writer 晋级；
- runtime/账户/资金；
- final merge。

其余机械工作由脚本和已验证 Agent 自动完成。

---

## 9. 降低复制粘贴和等待的自动化架构

目前的主要低效来源：

1. 用户在窗口之间复制完整 Prompt；
2. 用户等待一个窗口返回后再交给另一个窗口；
3. 总控无法自动取得本地状态；
4. 工程优化需要反复纠正角色和权限；
5. Writer、Reviewer 和 Finalizer 重复读取仓库；
6. Evidence、日志和 CI 结果由用户手工传递；
7. 不同窗口可能使用过期 SHA 或旧权限规则；
8. 环境问题与代码问题混合处理。

目标架构：

### 9.1 GitHub 作为共享事实面

每个任务固定保存：

- task contract；
- exact base/head；
- Write Lease；
- Agent combination；
- scope allowlist；
- validation commands；
- Evidence Pack；
- Review findings；
- repair authority；
- finalization record。

Agent 不再依赖用户转述项目事实，而是读取 GitHub 当前对象。

### 9.2 本地控制目录

建议未来建立：

```text
engineering/control/
schemas/control/
scripts/control/
tests/control/
```

输出放在 worktree 外或 ignored artifact 目录，避免污染产品 diff。

### 9.3 Agent Adapter

为每个 Harness 实现统一适配层：

```text
AgentAdapter
- capability_id
- allowed_roles
- read_only
- write_authorized
- launch()
- collect_result()
- verify_side_effects()
- cost_metrics()
```

优先适配：

1. Codex；
2. OpenCode + DeepSeek；
3. Trae 手动/半自动任务；
4. 后续验证的其他 Harness。

### 9.4 用户交互压缩

目标是从：

```text
用户复制 Prompt
→ 等待
→ 复制结果
→ 请求纠正
→ 再复制
```

演进到：

```text
用户授权任务
→ Project Control 生成机器可读合同
→ Orchestrator 启动已验证 Agent
→ 自动收集 Evidence
→ 仅在 blocker/权限/merge 时通知用户
```

### 9.5 环境预检分离

环境问题必须在 Writer 启动前完成：

- repository/origin；
- branch/worktree；
- Python/venv；
- Git/gh；
- dependency install；
- test commands；
- CI evidence route；
- secrets exposure；
- disk/permission；
- Harness availability。

环境失败不得在产品实现中途才发现。

---

## 10. 工程指标

每个任务至少记录：

```text
END_TO_END_ELAPSED_TIME
ACTIVE_ENGINEERING_TIME
USER_WAIT_TIME
USER_COPY_PASTE_EVENTS
PROJECT_CONTROL_ROUND_TRIPS
WRITER_CONTEXTS
REVIEWER_CONTEXTS
REVIEW_ROUNDS
REPAIR_COMMITS
CI_RUNS
AGENT_TOKEN_OR_API_COST
SCOPE_DRIFT_EVENTS
WRITER_COLLISIONS
STATE_DRIFT_EVENTS
INTEGRATION_FAILURES
TOOLING_FAILURES
```

阶段目标：

### E1–E3

- 用户复制粘贴次数下降 50%；
- handoff 长度下降 60%；
- 状态核对重复工作下降 50%；
- 零错误 Writer 路由；
- 零 writer collision。

### E4–E6

- 产品任务关键路径缩短 25%–40%；
- 用户机械操作下降 70%；
- 常规 Evidence 和 CI 汇总接近零高价值 Agent Token；
- repair 保持 0–1 轮；
- 并行 Lane 的集成失败率保持可接受并持续下降。

这些是优化目标，不得以降低安全门换取达成。

---

## 11. Capability Pilot 规则

每个 Pilot 必须记录：

```text
PILOT_ID
HARNESS
MODEL
MODEL_VERSION_OR_USER_REPORTED_NAME
ROLE
TASK
BASE_SHA
HEAD_SHA
READ_ONLY
MUTATIONS
EXPECTED_FINDINGS
ACTUAL_FINDINGS
FALSE_POSITIVES
MISSED_FINDINGS
REPORT_SCHEMA_COMPLIANCE
LENGTH_COMPLIANCE
TOOL_USE_RESULT
COST
ELAPSED_TIME
FINAL_LEVEL
PROMOTION_OR_DEMOTION
```

晋级必须基于保留证据，不得凭主观印象。

触发降级：

- 仓库 mutation 越权；
- missed CRITICAL/HIGH；
- blocking false positive；
- scope 扩张；
- 伪造工具证据；
- 违反报告合同；
- Harness 或模型版本发生重大变化；
- 连续稳定性下降。

---

## 12. Review 和 Finalization

### 12.1 Review

最终独立 Reviewer：

- strict read-only；
- 不修改文件；
- 不提交、push、rebase、reset 或 amend；
- 不 Mark Ready；
- 不 merge；
- 不依赖 Writer 自述；
- 核验 exact base/head、diff、文件、测试、CI 和权限；
- 状态漂移立即停止。

辅助 Agent Review 只能提供 evidence 和候选 findings，最终裁决由独立 Reviewer 和 Project Control 合并。

### 12.2 Repair

- 原 Writer优先；
- 最多一个 consolidated repair commit；
- 只修 accepted blockers；
- 不扩大 scope；
- repair 后重新冻结 exact head；
- 仍失败则停止，不进入无限循环。

### 12.3 Finalization

必须单独授权：

- exact-head Review PASS；
- exact-head CI PASS；
- base/head 未漂移；
- 无未解决 blocker；
- merge method 冻结；
- 用户明确授权；
- 不自动删除 source branch。

---

## 13. 安全停止条件

出现以下任一情况必须停止：

- main/base/head 不匹配；
- branch/worktree 污染；
- active Git operation；
- Write Lease 不存在或不匹配；
- path allowlist 需要扩张；
- Writer collision；
- Agent 越权 mutation；
- 未验证 Agent 被选为 Writer；
- 测试或 CI 未通过；
- tooling limitation 被伪装为 PASS；
- Review 超过允许 repair；
- 需要账户、凭证或交易权限；
- 并行 Lane 出现共享文件或接口未冻结；
- Integrator 需要重写两个 Lane 的核心逻辑；
- 成本和整合时间超过并行节省。

标准返回：

```text
BLOCKED
EXPECTED
ACTUAL
OBJECT_IDENTITY
MUTATIONS
SAFE_STOP_POINT
REQUIRED_AUTHORITY
```

---

## 14. 当前执行顺序

```text
1. 使用 corrected Package 2 Codex Packet。
2. Codex 完成 Package 2 并发布 Draft PR。
3. 独立 ChatGPT exact-head Review。
4. Trae + GLM-5.2 执行第二次 bounded read-only pilot。
5. 必要时一次 consolidated repair。
6. Package 2 merge + main refreeze。
7. 启动 ENGINEERING-AGENT-CAPABILITY-REGISTRY-AND-ROUTING-V1。
8. Package 3 产品线继续。
9. Package 3 merge 后实施 Project Snapshot 与 Evidence Pack。
10. Package 4 周期实施 Handoff、Cost Log 和 Retrospective。
11. M1.5 稳定后启动 OpenCode Writer pilot。
12. 再启动 ENGINEERING-PARALLEL-WRITE-LANES-V1。
13. 双 Writer试点通过后用于 V0 和 Trade OS 主线的完全独立模块。
14. 最终建设 bounded multi-Agent orchestrator，转向 exception-only 人工管理。
```

---

## 15. 当前 GitHub 固化状态

截至本文件创建时：

```text
HUMAN_READABLE_WORKFLOW:
本文件形成统一基线

EXISTING_PROJECT_CONTROL_POLICY:
已存在，但部分 Agent 路由规则过时

EXECUTION_LAUNCH_SCHEMA:
已存在，但仍使用泛化 Harness 和旧配额等级

TOOLING_PREFLIGHT:
已存在，但路由语义需要 E1 修复

AGENT_CAPABILITY_REGISTRY:
未实现

PILOT_EVIDENCE_REGISTRY:
未实现

PROJECT_SNAPSHOT:
未实现

EVIDENCE_PACK:
未实现

HANDOFF_GENERATOR:
未实现

MULTI_AGENT_ORCHESTRATOR:
未实现

PARALLEL_WRITE_LANES:
未授权
```

本文件合并后成为工程优化的人类可读基线；机器执行能力必须通过后续独立任务逐项实现和测试。

---

## 16. 不可变原则摘要

```text
QUALITY_AND_SAFETY_BEFORE_SPEED

CHATGPT_CONTROL_PLANE_IS_READ_ONLY_BY_DEFAULT

ONE_WRITER_PER_WRITE_BOUNDARY

MORE_AGENTS_DOES_NOT_MEAN_MORE_WRITERS

READ_ONLY_WORK_SHOULD_PARALLELIZE_EARLY

TWO_WRITERS_REQUIRE_DISJOINT_PATHS_AND_AN_INTEGRATOR

CAPABILITY_IS_EXACT_HARNESS_PLUS_MODEL

NO QUALIFICATION TRANSFER_ACROSS_HARNESSES

READ_ONLY_QUALIFICATION_DOES_NOT_GRANT_WRITE_AUTHORITY

CODEX_PRIMARY_AT_OR_ABOVE_40_PERCENT

BELOW_40_PERCENT_REQUIRES_CONTINUITY_INTAKE

PRESERVE_20_PERCENT_EMERGENCY_RESERVE

EVERY_WRITER_REQUIRES_AN_EXACT_WRITE_LEASE

NO_AUTOMATIC_SCOPE_EXPANSION

NO_AUTOMATIC_MERGE

NO_AUTOMATIC_RUNTIME_OR_TRADING_AUTHORITY

ONE_CONSOLIDATED_REPAIR_LOOP

GITHUB_AND_EVIDENCE_ARE_THE_SHARED_FACT_SOURCE

AUTOMATE_MECHANICAL_WORK; KEEP_HUMAN_AUTHORITY
```

---

## 17. 版本管理

后续修订必须：

1. 更新版本号；
2. 记录变更原因；
3. 通过独立文档/治理 PR；
4. 不直接覆盖历史版本证据；
5. 同步更新 capability registry、Schema、脚本和测试；
6. 若机器实现与本文冲突，机器路由必须 fail closed；
7. 重大变化在下一个干净 checkpoint 生效，不在活跃产品任务中途改变。

### Change Log

```text
1.0.0 — 2026-07-19
- 合并既有工程优化路线和多 Agent 工作流；
- 冻结 40% Codex continuity threshold 和 20% reserve；
- 定义 Trae、GLM-5.2、DeepSeek V4 Pro/Flash、OpenCode 和候选模型边界；
- 定义未来双 Writer 与 Integration Branch 模型；
- 定义减少复制粘贴和等待的自动化路线；
- 定义 E0–E7 渐进里程碑；
- 明确 First Launch 当前仍为单产品 Writer。
```
