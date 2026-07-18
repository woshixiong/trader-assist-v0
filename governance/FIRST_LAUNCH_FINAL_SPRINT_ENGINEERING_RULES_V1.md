# First Launch 最后冲刺工程执行规则 v1

```text
DOCUMENT_ID:
FIRST-LAUNCH-FAST-SAFE-FINAL-SPRINT-ENGINEERING-RULES-V1-2026-07

VERSION:
1.0.0

DATE:
2026-07-19

PARENT_BASELINE:
TRADER-ASSIST-ENGINEERING-OPTIMIZATION-AND-MULTI-AGENT-WORKFLOW-V1-2026-07

REPOSITORY:
woshixiong/trader-assist-v0

DOCUMENT_STATUS:
FROZEN_HUMAN_READABLE_PROCESS_BASELINE

PRODUCT_SCOPE_AUTHORITY:
PRODUCT_FUNCTION_AND_PRIORITY_CONTROL_WINDOW

ENGINEERING_EXECUTION_AUTHORITY:
ENGINEERING_OPTIMIZATION_AND_PROJECT_CONTROL

RUNTIME_OR_TRADING_AUTHORITY_GRANTED:
NO
```

## 1. 目的

本文件冻结 First Launch 最后冲刺期间的工程执行方式。

本文件只决定“如何高效、安全地执行已经冻结的产品计划”，不决定产品功能、策略规则、AWS runtime、账户、钱包、凭证、签名、nonce、Testnet、Mainnet、exchange-write、自动下单、自动取消或自动 SL/TP。

产品功能和优先级由产品功能管理窗口决定。工程优化窗口和 Project Control 只能把产品决定转换为可执行工程合同，不得自行增加或删除产品功能。

## 2. 当前已记录状态

```text
PACKAGE_1:
ACCEPTED_AND_MERGED

PACKAGE_2:
PR_34_MERGED

PACKAGE_2_REVIEWED_HEAD:
66018e1d2ad5ea21aea05fc0a89a8c90284c9929

PACKAGE_2_MERGE_SHA:
8be9922e7e70fa1b2738994c2f31c2c87e866cb2

CURRENT_MAIN_AT_FREEZE:
8be9922e7e70fa1b2738994c2f31c2c87e866cb2

PACKAGE_2_POST_MERGE_MAIN_REFREEZE:
PASS

PACKAGE_2_POST_MERGE_CI_EVIDENCE:
PENDING_AT_TIME_OF_THIS_FREEZE

PACKAGE_3:
NOT_STARTED

PACKAGE_4:
NOT_STARTED

LIVE_SHADOW:
NOT_ACTIVE

ENGINEERING_PR_33:
OPEN_DRAFT_NOT_MERGED

ENGINEERING_AGENT_CAPABILITY_TASK:
READY_BUT_DEFERRED
```

真实状态优先级：

```text
1. GitHub object state
2. exact base / head / merge SHA
3. CI object
4. canonical Evidence Pack
5. PR body narrative
```

PR body 不得覆盖真实 GitHub 对象状态。

## 3. First Launch 最后冲刺模式

```text
MODE:
FIRST_LAUNCH_FAST_SAFE_FINAL_SPRINT

PRODUCT_WRITE_LANES:
1

READ_ONLY_AUXILIARY_LANES:
0_TO_2

FINAL_REVIEW_AUTHORITIES:
1

CONSOLIDATED_FINDINGS_SETS:
1

REPAIR_COMMITS:
0_TO_1

AUTOMATIC_SCOPE_EXPANSION:
PROHIBITED

AUTOMATIC_MARK_READY:
PROHIBITED

AUTOMATIC_MERGE:
PROHIBITED
```

必须维持：

```text
ONE_ACTIVE_WRITER_IDENTITY
ONE_ACTIVE_WRITE_LEASE
ONE_ACTIVE_WRITE_BOUNDARY
```

“单 Writer”不等于必须永远使用同一个 UI 窗口。上下文轮换时，只要 task、base/head、branch/worktree、Write Lease 和 Evidence 连续，并完成正式 handoff，仍视为同一个 Writer。

必须维持：

```text
ONE_FINAL_REVIEW_AUTHORITY
ONE_CONSOLIDATED_FINDINGS_SET
```

辅助 Reviewer 不得分别直接向 Writer 下发修复指令。

## 4. 最短工程执行链

```text
1. 产品窗口冻结产品 Package。

2. Project Control 一次生成完整工程合同：
   task、exact base、branch、worktree、Write Lease、path allowlist、
   acceptance criteria、validation、publication rules 和 stop conditions。

3. Writer 启动前执行环境和工具 preflight。

4. Codex 作为唯一产品 Writer 实现、测试、commit、push并创建 Draft PR。

5. 冻结 exact head，收集 exact-head CI。

6. 一个独立 ChatGPT 窗口承担主 Review。

7. 最多一个辅助只读 Agent 提供非重复证据或候选 findings。

8. Project Control 合并和去重 findings。

9. 若存在 accepted blocker：
   一份 consolidated repair packet
   → 原 Writer最多一个 bounded repair commit。

10. repaired exact head re-review 和 CI。

11. 用户单独授权 Mark Ready 和 merge。

12. merge、main refreeze 和 post-merge evidence。

13. 只记录简短 retrospective，不自动插入新的工程 PR。
```

## 5. 状态报告压缩

第一次激活任务时生成完整 Task Contract。之后默认只返回：

```text
DELTA
CHANGED_OBJECTS
NEW_EVIDENCE
NEW_BLOCKERS
NEXT_AUTHORIZED_ACTION
```

只有窗口轮换、task/base/head/lease实质变化、Evidence矛盾、scope变化请求、finalization或安全停止后重新激活时，才重新生成完整 Packet。

## 6. 角色规则

### Writer

- 默认 Codex；
- 用户报告额度不低于40%时优先；
- 低于40%触发continuity intake；
- 保留20% emergency reserve；
- 未验证 alternate Agent不得自动接管；
- 环境 preflight 必须先于编码；
- 一个初始实现commit，加最多一个授权repair commit；
- 禁止扩大allowlist或启动后续Package。

### Reviewer

- strict read-only；
- 核验exact base/head、files、scope、tests、CI、权限和Evidence；
- 不依赖Writer自述；
- 不修改代码、不Mark Ready、不merge；
- 主Reviewer负责最终finding authority。

### Repair

- Project Control先去重和合并findings；
- Writer只接收一份repair packet；
- 只修accepted blockers；
- 不扩scope；
- 最多一个repair commit；
- repair后重新冻结exact head；
- 第二次仍失败则停止。

### Finalizer

- exact expected head guard；
- exact-head Review和CI；
- 用户单独授权；
- 不自动删source branch；
- 不自动启动下一Package；
- post-merge CI工具限制必须标记为limitation，不能伪装成PASS。

## 7. 可并行工作

不占产品Writer lane、不扩产品scope、不增加明显用户传递负担时，可以并行：

- contract attack；
- test-gap analysis；
- changed-file inventory；
- CI/log分析；
- deployment checklist；
- Review evidence准备；
- PR body与exact-head一致性检查；
- stale SHA和state drift检测；
- 一个有明确目的的bounded capability pilot；
- retrospective指标采集。

辅助Agent不得修改产品代码、创建产品scope、创建repair commit、直接给Writer下达冲突指令、未经批准成为Writer或启动下一Package。

## 8. 默认后移

最后冲刺期间默认后移：

- 完整Agent Capability Registry实现；
- 大型Project Snapshot平台；
- 完整Evidence Pack平台；
- 完整Handoff Generator；
- OpenCode Writer资格任务；
- 双Writer试点；
- Integration Branch自动化；
- Multi-Agent Orchestrator；
- Agent成本平台；
- 大规模治理重构；
- 非必要capability pilot。

只有真实Writer路由错误、权限错误、最小自动化缺失导致产品无法继续、产品窗口确认自然空档或用户明确授权时，才允许插入工程任务。

## 9. PR #33与工程任务

```text
PR_33:
KEEP_OPEN_DRAFT

MUST_MERGE_BEFORE_NEXT_PRODUCT_TASK:
NO

PRODUCT_BLOCKER:
NO
```

```text
TASK:
ENGINEERING-AGENT-CAPABILITY-REGISTRY-AND-ROUTING-V1

ENTRY_GATE:
SATISFIED

STATUS:
READY_BUT_DEFERRED

PRODUCT_BLOCKER:
NO
```

只要最后冲刺人工明确：

```text
Codex = Writer
ChatGPT = Control and final Review
Trae/OpenCode = read-only unless separately authorized
```

旧机器路由不构成当前产品阻塞项。

## 10. Agent路由

| 角色 | 默认Agent | 最后冲刺裁定 |
|---|---|---|
| 产品Writer | Codex | 正式唯一产品Writer |
| Project Control | ChatGPT普通窗口 | 最高可用模型和思考等级 |
| 最终独立Review | 独立ChatGPT窗口 | 唯一最终Review authority |
| Contract/Test Gap | Trae + DeepSeek-V4-Pro | 可选只读辅助 |
| Log/Evidence | Trae + DeepSeek-V4-Flash | 仅小范围或Pilot后使用 |
| GLM Pilot | Trae + GLM-5.2 | 默认暂停，除非零关键路径和低用户负担 |
| OpenCode | OpenCode + DeepSeek | 可后移只读qualification；不得写关键代码 |
| Claude Code | Claude Code + DeepSeek | 未验证，不进入默认路径 |

不是每个任务都必须启用所有Agent。

## 11. 自动化优先级

1. 最小Project Snapshot；
2. exact SHA / branch / PR / changed-files drift checker；
3. CI和Review状态自动收集；
4. 统一Evidence Block；
5. Writer / Reviewer / Finalizer Packet Generator；
6. PR body stale-state检测；
7. consolidated repair packet生成器；
8. 环境preflight；
9. 用户复制内容压缩；
10. 时间、Token、Review和repair指标；
11. Agent Adapter；
12. 多Writer Orchestrator。

最后冲刺只允许实现小而直接有收益的工具，不建立大型控制平台。

## 12. 工程效率目标

```text
PRODUCT_WRITER_IDENTITIES_PER_TASK:
1

FINAL_REVIEW_AUTHORITIES_PER_TASK:
1

REPAIR_COMMITS_TARGET:
0_TO_1

STALE_SHA_EVENTS:
0

WRITER_COLLISIONS:
0

SCOPE_DRIFT_EVENTS:
0

PRODUCT_ENGINEERING_MIXED_PR:
0

UNNECESSARY_FULL_STATE_REPORTS:
0
```

流程主动时间目标：

```text
PREACTIVATION_AND_PREFLIGHT:
15_TO_30_MINUTES

REVIEW_INTAKE_AND_CONSOLIDATION:
30_TO_90_MINUTES

REPAIR_PACKET:
15_TO_30_MINUTES

FINALIZATION_AND_REFREEZE:
20_TO_45_MINUTES

MICRO_RETROSPECTIVE:
10_TO_15_MINUTES
```

## 13. 用户最少动作

1. 批准产品窗口冻结的Package；
2. 将一份完整Writer Packet交给Codex；
3. 只在真实blocker时批准一次repair；
4. 最后批准merge。

```text
USER_DECISION_POINTS:
2_TO_4

FULL_PACKET_COPY_EVENTS:
1_TO_2

MANUAL_STATE_VALIDATION:
NEAR_ZERO
```

## 14. 上线前和上线后Backlog

上线前只保留：

- 轻量环境preflight；
- exact-state核验；
- consolidated Review；
- stale-state检测；
- 简短Evidence Block；
- 用户传递压缩；
- 必要post-merge CI evidence。

上线后或自然空档再实施：

1. PR #33独立文档Review和合并决策；
2. Agent Capability Registry；
3. 40%/20%机器路由；
4. Project Snapshot；
5. Evidence Pack；
6. Handoff Generator；
7. OpenCode qualification；
8. 双Writer和Integration Lane；
9. Multi-Agent Orchestrator；
10. exception-only人工管理。

## 15. 关键节点

```text
NODE_A:
产品窗口提交最终First Launch冲刺计划
ACTION:
仅翻译为最短关键路径工程合同，不改变产品功能。

NODE_B:
下一产品Package Draft PR发布
ACTION:
启用一个主Review authority，最多一个非重复辅助Reviewer。

NODE_C:
First Launch最终产品Package合并并main refreeze
ACTION:
评估启动ENGINEERING-AGENT-CAPABILITY-REGISTRY-AND-ROUTING-V1。

NODE_D:
Agent Capability Registry合并并稳定
ACTION:
启动最小Project Snapshot / Evidence Pack。

NODE_E:
Snapshot / Evidence Pack稳定
ACTION:
实施Handoff Generator和用户复制压缩。

NODE_F:
OpenCode完成两次只读Pilot和一个低风险Writer Pilot
ACTION:
评估ENGINEERING-PARALLEL-WRITE-LANES-V1。

NODE_G:
双Writer试点稳定
ACTION:
只对V0/Trade OS完全独立模块开放两个Writer Lane。

NODE_H:
连续产品任务满足M1.5稳定性门
ACTION:
评估bounded Multi-Agent Orchestrator。
```

## 16. 安全停止

遇到main/base/head不匹配、worktree污染、active Git operation、lease不匹配、allowlist扩大、Writer collision、越权mutation、未验证Writer、测试/CI失败、tooling limitation伪装PASS、超过repair预算、产品与工程混写、需要runtime/账户/交易权限、PR body状态无法解析或重复人工搬运时停止。

```text
BLOCKED
EXPECTED
ACTUAL
OBJECT_IDENTITY
MUTATIONS
SAFE_STOP_POINT
REQUIRED_AUTHORITY
```

## 17. 当前冻结动作

```text
WAIT_FOR_PRODUCT_WINDOW_FINAL_SPRINT_DECISION:
YES

START_NEXT_PRODUCT_PACKAGE:
NO

START_ENGINEERING_AGENT_REGISTRY_TASK:
NO

MODIFY_PRODUCT_SCOPE:
NO

AUTOMATICALLY_CONTINUE:
NO

CURRENT_ACTION:
RECORD_STATE_AND_HOLD
```

## 18. Change Log

```text
1.0.0 — 2026-07-19
- 冻结First Launch Fast-Safe Final Sprint工程模式；
- 权限分离；
- 单Writer identity/lease/write boundary；
- 一个最终Review authority和一个consolidated findings set；
- delta-only状态更新；
- PR body低于GitHub对象和exact Evidence；
- PR #33不阻塞产品；
- Agent Capability Registry设为Ready but Deferred；
- capability pilot默认不占关键路径；
- 固定上线前/上线后Backlog和关键节点。
```
