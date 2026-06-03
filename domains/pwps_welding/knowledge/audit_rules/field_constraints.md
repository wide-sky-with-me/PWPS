# 字段约束审计规则

## 规则 1: 禁止推断字段检查 (provided_only_check)

**类型**: HARD
**严重度**: HIGH
**检查字段**: project_name, client_name, document_number

**规则描述**:
以下字段的 inference_policy 为 PROVIDED_ONLY，只能由用户提供，不能由模型推断：
- project_name (项目名称)
- client_name (客户名称)
- document_number (文件编号)

**检查方法**:
```
if field.inference_policy == PROVIDED_ONLY and field.value is not None and field.source_type != USER_INPUT:
    违规！
```

**修复建议**:
- 清空该字段的值
- 或请求用户提供明确的值

---

## 规则 2: 必填字段完整性 (required_field_completeness)

**类型**: COMPLETENESS
**严重度**: MEDIUM
**检查字段**: 所有 required_for_draft=True 的字段

**规则描述**:
required_for_draft=True 的字段必须有值才能生成草案。

必填字段包括：
- base_material (母材)
- thickness (厚度)
- welding_process (焊法)
- joint_type (接头形式)
- welding_position (焊接位置)
- consumable (焊材)

**检查方法**:
```
if field.required_for_draft and (field.value is None or field.value == ""):
    缺失！
```

**修复建议**:
- 补充缺失字段的值
- 通过知识检索或用户输入获取

---

## 规则 3: 厚度合理性检查 (thickness_range_check)

**类型**: RISK
**严重度**: MEDIUM-HIGH
**检查字段**: thickness

**规则描述**:
厚度值应在合理范围内：

| 范围 | 风险 | 说明 |
|------|------|------|
| < 1.0mm | HIGH | 超薄板，需要特殊焊接工艺 |
| 1.0-6.0mm | LOW | 薄板 |
| 6.0-25mm | LOW | 中厚板 |
| 25-50mm | MEDIUM | 厚板，需要预热和 PWHT |
| > 100mm | HIGH | 超厚板，需要特殊工艺方案 |

**检查方法**:
从厚度值中提取数字，检查是否在合理范围内。

**修复建议**:
- 超薄板：确认是否需要特殊工艺
- 超厚板：确认是否有详细的热过程控制方案
