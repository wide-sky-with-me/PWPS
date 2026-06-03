# 模板与标准 Profile 设计 template_profile_design.md

## 1. 文档定位

本文档定义 pWPS Agent 中字段注册表、标准 Profile、行业/企业模板和最终渲染模板之间的关系。

系统必须避免把“字段能力”和“文档样式”混在一起。

---

## 2. 核心分层

```text
Field Registry
  定义系统支持哪些字段、字段依赖、推断策略、审计规则。

Code Profile
  定义不同标准体系对字段、范围、术语、审计规则的差异。

Industry / Scenario Profile
  定义压力容器、管道、钢结构、不锈钢、碳钢等场景差异。

Company Profile
  定义企业字段偏好、知识源优先级、模板默认值、内部命名。

Render Template
  定义最终 Markdown / DOCX / PDF / Web 页面如何展示。
```

---

## 3. 不同层的职责

| 层级 | 负责什么 | 不负责什么 |
|---|---|---|
| Field Registry | 字段定义、依赖、策略 | 具体文档排版 |
| Code Profile | 标准差异、术语、审计规则增强 | 用户界面 |
| Company Profile | 企业默认配置、知识源优先级 | 修改核心工作流 |
| Render Template | 文档布局、字段展示顺序 | 推理和审计 |

---

## 4. Profile 加载建议

```python
registry = RegistryFactory.load(
    code_profile="default",
    industry_profile="pressure_vessel",
    company_profile=None,
)
```

MVP 可以只实现 `default`，但结构上要允许后续扩展。

---

## 5. 模板原则

1. 模板不得修改字段事实。
2. 模板不得改变 publishability。
3. 模板只能决定展示顺序、标题、格式、说明文字。
4. 模板缺字段时应显示空值或待确认，不得自行补全。
5. 模板版本必须记录在 final output 中。

---

## 6. 推荐模板输出

```text
render_payload.json
  meta
  sections
  field_display_items
  risk_blocks
  evidence_blocks
  audit_summary
  template_version
```

---

## 7. 阶段规划

### MVP

```text
固定 default template
固定 default field registry
```

### V1

```text
Markdown template 可配置
字段显示顺序可配置
```

### V2

```text
Code Profile
Company Profile
DOCX/PDF 模板
```

### V3

```text
企业模板管理
标准体系配置
多模板切换
```
