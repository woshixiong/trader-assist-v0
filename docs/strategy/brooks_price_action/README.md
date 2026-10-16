# Brooks / Louie 价格行为：人工交易与量化研究库

**研究包**：`PA_BROOKS_LOUIE_LIBRARY_20261016` · **日期**：2026-10-16 · **状态**：`RESEARCH_CANDIDATE / NON_EXECUTABLE / UNVALIDATED`  
**控制记录**：[Issue #343](https://github.com/woshixiong/trader-assist-v0/issues/343) · **来源**：Louie / 方方土 PriceAction 的公开视频及字幕 + Al Brooks 官方公开材料。

本目录是**策略知识库**而非可执行交易配置：不修改现有 Three Setup、不启用新 Setup、不更改风险/仓位/实盘策略，不具有 Shadow、订单、账户、部署或资金操作权限。研究结论不是已验证优势，不得把讲师演示收益或经验概率套用于 Hyperliquid RWA。

## 文件与使用方式

| 文件 | 用途 | 适用人群 |
|---|---|---|
| [HUMAN_TRADING_PLAYBOOK_V0_20261016.md](HUMAN_TRADING_PLAYBOOK_V0_20261016.md) | 一屏执行清单、行情模式选择、反转/突破/二次入场、风险与持仓决策 | 人类交易员 |
| [QUANT_STRATEGY_CANDIDATES_V0_20261016.md](QUANT_STRATEGY_CANDIDATES_V0_20261016.md) | Q0~Q8 待验证候选、三大 Setup 映射、因果信号、数据需求、对照、否证 | Strategy 研究、回测 |
| [EVIDENCE_AND_VALIDATION_PLAN_V0_20261016.md](EVIDENCE_AND_VALIDATION_PLAN_V0_20261016.md) | 公开证据/视频索引、实验顺序、数据要求、验证门槛、试验台账 | Strategy / Independent Validation |

## 定位和优先级

优先级建议：**(1) 环境过滤 Q1；(2) 假突破与跟随确认 Q2/Q4；(3) 二次入场 Q3；(4) 止损与出场 Q6/Q7；(5) 开盘反转与高潮楔形 Q8/Q5。**
上述仅为研究顺序，不是已证明的 Alpha 排名。

```text
CURRENT_DIRECTIONAL_AUTHORITY=THREE_SETUP_ONLY
CURRENT_THREE_SETUP=SWEEP_RECLAIM | BREAKOUT_RETEST | RANGE_EDGE_REJECTION
BROOKS_MATERIAL=FEATURE / CONTEXT / ENTRY / EXIT CHALLENGERS
NEW_AUTHORIZED_FOURTH_SETUP=NO
AUTOMATED_EXECUTION=NO
RESEARCH_CANDIDATE_EDGE=UNPROVEN
```

**边界**：人工交易可参考短清单，但已有安全/风险/临时阶段规则优先；量化候选的方向权威只来自现有三大 Setup。独立 Brooks 形态方向预测仅能在隔离的 OFFLINE_MECHANISM 诊断中探索，不能作为当前 Shadow/Live 的第四个 Setup。

**既有规范**：[Strategy 主索引](../README.md) · [Issue #161](https://github.com/woshixiong/trader-assist-v0/issues/161) · [Issue #150](https://github.com/woshixiong/trader-assist-v0/issues/150) · [既有 Strategy 规格](../TA_VNEXT_E4_C1_STRATEGY_SPEC_2026-09-11.md) · [验证标准](../TA_VNEXT_VALIDATION_BACKTEST_SHADOW_AND_PROMOTION_STANDARD_V1_2026-09-11.md)。
