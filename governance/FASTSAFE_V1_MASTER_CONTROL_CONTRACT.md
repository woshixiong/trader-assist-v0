# Trader Assist FastSafe v1 总控合同

**CONTRACT_ID:** `FASTSAFE-V1-2026-07`
**状态：** 正式基线；上一任务 authority-state sync 合并、CI 通过且总控接受后生效
**适用范围：** Trader Assist V0、后续策略、因子研究及工程任务

> 成本口径：仅统计 Codex、DeepSeek API、Claude Code 等执行型 Agent Token/API 成本。ChatGPT 常规对话窗口按当前使用约定不计入本合同的 Agent Token 优化目标。

## 1. 目标

1. 最快完成 First Launch 及后续可产生交易价值的产品里程碑。
2. 保留 exact-object、范围冻结、交易/资金权限、安全边界和独立审查。
3. 删除重复交接、上下文重载、重复取证、低价值 Agent Token 使用。
4. 禁止无限拆分；也禁止通过跳过真实 blocker、CI 或独立审查制造表面速度。

## 2. 权威层级

1. **GitHub 当前 exact objects**：main SHA、PR base/head、PR state、CI run/job/check-out SHA。
2. **Repository governance authority**：产品范围、runtime/账户/交易权限、不可变边界。
3. **Accepted project-control state**：当前任务、lease、accepted blocker、下一授权动作。
4. **Evidence Pack / CI logs / Review report**：执行和验收证据。

旧提示词、PR body、commit message 或未接受的 Agent 摘要不得覆盖当前 exact objects。

## 3. 角色隔离

- **Project Control**：冻结里程碑、scope、lease、门禁和唯一下一步；不得写产品代码或兼任最终 Reviewer/Finalizer。
- **Writer / Repair Writer**：仅在 allowlist 内实现、测试、单 commit 和证据输出；不得扩 scope、push/merge 或自批 PASS。
- **Independent Reviewer**：独立 checkout、完整 diff、生产 consumer、攻击和回归；不得改代码，工具不足必须返回 `TOOLING_UNAVAILABLE`。
- **Finalizer**：只做 body refresh、Mark Ready、expected-head merge、post-merge refreeze；不得 repair、rebase、force push 或启动下一任务。
- **Deterministic Scripts**：状态、证据、哈希、测试和 handoff；不得做 scope、代码安全或最终授权判断。

任一时刻只允许一个 Writer、一个有效 write lease 和一个 exact review object。

## 4. 任务颗粒度

- 最小单元是完整、可独立验收的用户或系统里程碑，不是文件、函数、测试或单个 review comment。
- 同一 exact-head、同一 scope、同一 allowlist 内的 blocker 合并为一个 bounded repair。
- 只有权限边界、不可逆风险、不同 PR/branch、无法共享 allowlist 或修复相互改变审查对象时才拆分。
- 一个产品任务原则上使用一个 branch、一个 Draft PR、一个 Writer。
- 总控最多维护三个剩余关键里程碑。

## 5. 标准生命周期

`Authority Freeze → Bounded Writer → Publish + CI → Independent Review → One Consolidated Repair → Finalization → Post-merge Refreeze → Micro Retrospective`

### Authority Freeze

冻结 `MAIN_SHA / TASK_ID / scope / out-of-scope / branch / PR / lease / allowlist / acceptance criteria / tests / stop conditions`。

### Writer

一次性完成 bounded implementation、targeted tests、必要 full suite、Ruff、Mypy、Compileall、diff check、单 commit 和 Evidence Pack。除对象漂移或需要超出 allowlist 外，不反复请示机械步骤。

### Review

只允许：

- `PASS`
- `BLOCKED_WITH_REPRODUCIBLE_BLOCKERS`
- `TOOLING_UNAVAILABLE`

Blocker 必须包含 exact object、FILE、SYMBOL、可复现输入/攻击、EXPECTED、ACTUAL、生产影响、最小修复边界和回归测试合同。

### Repair

同一 Review 的 accepted blocker 一次合并修复。自动/半自动 repair-review 循环最多一轮；第二次仍 BLOCKED，回总控判断实现、合同、scope 或架构根因。

### Finalization

独立 Finalizer 只做 exact-object preflight、PR body refresh、Mark Ready、expected-head merge、post-merge main 和 CI refreeze。

## 6. Writer 合同字段

```text
TASK_ID:
CONTROL_CONTRACT_ID:
ROLE: BOUNDED_WRITER
PERMISSION: WRITE_WITHIN_ALLOWLIST
START_MAIN_SHA:
BRANCH:
PR_MODE: ONE_DRAFT_PR
WRITE_LEASE:
SCOPE:
OUT_OF_SCOPE:
ALLOWED_PATHS:
FORBIDDEN_PATHS:
ACCEPTANCE_CRITERIA:
TARGETED_TESTS:
FULL_REGRESSION_TRIGGER:
REQUIRED_EVIDENCE:
STOP_CONDITIONS:
PUSH_AUTHORIZATION: EXPLICIT_ONLY
MERGE_AUTHORIZATION: NONE
```

## 7. Evidence Pack v1

```text
EVIDENCE_PACK_VERSION: 1
TASK_ID:
CONTROL_CONTRACT_ID:
GENERATED_AT:
BASE_SHA:
HEAD_SHA:
PARENT_SHA:
BRANCH:
COMMIT_MESSAGE:
CHANGED_PATHS:
DIFF_STAT:
ALLOWED_PATH_CHECK:
TARGETED_TESTS:
FULL_TESTS:
RUFF:
MYPY:
COMPILEALL:
DIFF_CHECK:
WORKTREE_STATUS:
CI_RUN:
CI_JOB:
CI_CHECKOUT_SHA:
RAW_LOG_HASH:
AGENT_EXECUTION_CLASS:
AGENT_TOKEN_NOTES:
RESULT: PASS | BLOCKED
```

PASS 必须满足全部条件；命令成功但 SHA、路径、父提交、message 或 worktree 不匹配仍为 BLOCKED。

## 8. 短 Handoff

```text
CONTROL_CONTRACT_ID:
AUTHORITY_MAIN_SHA:
TASK_ID:
ROLE:
PERMISSION:
PR:
BASE_SHA:
HEAD_SHA:
SCOPE_SUMMARY:
ALLOWED_PATHS:
ACCEPTANCE_CRITERIA:
EVIDENCE_PACK_ID:
ACCEPTED_BLOCKERS:
NEXT_ACTION:
STOP_CONDITIONS:
```

完整细节保存在 GitHub exact objects、治理文件、Evidence Pack、CI logs 和 accepted Review；禁止递归复制完整历史。

## 9. Agent Token 路由

### Codex 余额 ≥ 30%

Codex-first：产品实现、复杂跨文件语义、交易安全/风险/状态机、疑难 repair、高价值代码 Review。状态、证据、日志、diff 和格式化交给脚本。

### Codex 余额 < 30%

DeepSeek/Claude Code-first：普通 bounded implementation、测试补充、仓库调查和证据整理。Codex仅处理高风险 blocker、疑难修复和关键复核。

### Codex 余额 < 10%

Emergency reserve：只有 First Launch 关键路径受阻且替代方案失败时使用。项目不因 Codex 额度暂停。

原则：能用确定性脚本就不用 Agent；能用低成本 Agent 就不使用高价值 Agent；Agent 输入只包含 exact object、最小 diff 和当前合同。

## 10. 防发散与进度

每次总控更新必须报告：关键路径、最多三个剩余里程碑、delay、delay cause、scope drift、extra work、可删除/合并/自动化步骤。无可验证 WBS 时不用虚假百分比。

## 11. 自动自我评估

每个产品里程碑后自动运行 Micro Retrospective：

1. 哪些动作重复至少两次？
2. 哪些完全确定性，可脚本化？
3. 哪些需要 AI 但可用低成本 Agent？
4. 哪些必须保留人工或独立隔离？
5. 哪些未降低真实风险或产生独立验收价值？
6. 哪些 Agent Token 产生新代码/新判断，哪些只是重复读取、取证或格式化？
7. 是否因工具不匹配、过度拆分、重复全量测试或上下文重载延期？
8. 哪个候选能在未来两个任务内回收成本？
9. FastSafe 需要什么最小修订？
10. Engineering Backlog 新增、关闭或降级什么？

每个动作只能归入 `KEEP / MERGE / AUTOMATE / DELETE / DEFER`。

## 12. Pilot 目标

下一两个完整产品里程碑作为 pilot：

- 人工 handoff 减少约 60%-80%；
- 低价值 Agent Token/调用减少约 25%-50%；
- Repair 循环控制在 0-1 轮；
- Reviewer 工具不足在开始前识别；
- 未经批准的 scope drift 为 0；
- 用户机械搬运减少约 70%。

这些是比较目标，不是保证。

## 13. 激活输出

```text
FASTSAFE_ACTIVATION_STATUS: PASS | BLOCKED
CONTROL_CONTRACT_ID: FASTSAFE-V1-2026-07
AUTHORITY_MAIN_SHA:
POST_MERGE_CI:
ACTIVE_TASK:
ACTIVE_WRITE_LEASE:
NEXT_PRODUCT_MILESTONE:
SCOPE:
OUT_OF_SCOPE:
WRITER_ALLOWLIST:
ACCEPTANCE_CRITERIA:
MODEL_ROUTE:
UNIQUE_NEXT_ACTION:
STOP_CONDITIONS:
```

## 14. GitHub 建议位置

```text
governance/FASTSAFE_V1_MASTER_CONTROL_CONTRACT.md
schemas/control/evidence-pack-v1.schema.json
schemas/control/handoff-v1.schema.json
```
