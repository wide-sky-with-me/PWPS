# 证据充分性审计规则

## 规则 1: 高风险字段证据要求 (high_risk_evidence)

**类型**: RISK
**严重度**: HIGH
**检查字段**: 所有 high_risk=True 的字段

**规则描述**:
高风险字段必须有充分的证据支持，不能仅靠模型先验。

高风险字段包括：
- consumable (焊材)
- current_range (电流)
- voltage_range (电压)
- travel_speed (焊接速度)
- heat_input (热输入)
- preheat_temperature (预热温度)
- interpass_temperature (层间温度)
- pwht (焊后热处理)

**证据可信度分级**:

| 来源 | 可信度 | 说明 |
|------|--------|------|
| 用户输入 | 1.0 | 用户明确提供 |
| 企业标准 | 0.9 | 企业内部标准 |
| 本地标准 | 0.8 | NB/T, GB/T, SY/T 等 |
| 结构化知识库 | 0.7 | 结构化的焊接知识库 |
| 历史 PQR | 0.7 | 工艺评定记录 |
| 历史 WPS | 0.65 | 焊接工艺规程 |
| 教材/手册 | 0.6 | 焊接教材、手册 |
| 本地文档 | 0.55 | 企业内部文档 |
| 网络搜索 | 0.3 | 网络搜索结果 |
| 模型先验 | 0.35 | LLM 模型知识 |

**检查方法**:
1. 获取高风险字段的所有证据
2. 找到最强可信度
3. 如果最强可信度 < 0.5，标记为证据不足

**修复建议**:
- 从标准文档中查找对应条款
- 参考历史 WPS/PQR
- 由焊接工程师提供依据

---

## 规则 2: 高风险自动确认检查 (high_risk_auto_confirmation)

**类型**: RISK
**严重度**: HIGH
**检查字段**: 所有 high_risk=True 的字段

**规则描述**:
在 Auto 模式下，高风险字段如果被自动确认（needs_human_confirmation=True），
必须标记为需要人工复核。

**检查方法**:
```
if field.high_risk and field.status == CONFIRMED and field.needs_human_confirmation:
    标记为风险
```

**修复建议**:
- 将字段状态改为 NEEDS_REPAIR
- 提交给焊接工程师复核
