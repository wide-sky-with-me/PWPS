# pWPS Agent Skill 设计规范 skill_design.md

## 1. 文档定位

本文档定义 pWPS Agent 中 Skill 的标准结构。Skill 不是简单 Prompt，而是可复用、可测试、可版本化的结构化能力单元。

---

## 2. Skill 原则

1. Skill owns prompt。
2. Workflow 不直接拼 Prompt。
3. Actor 可以调用 Skill，但不直接拼 Prompt。
4. 每个 Skill 必须有输入 schema 和输出 schema。
5. 每个 Skill 必须有 validator。
6. 每个 Skill 必须记录版本。
7. 每个 Skill 调用必须可观测、可调试、可复现。

---

## 3. 标准目录结构

```text
skills/
  candidate_generation/
    skill.yaml
    prompt.yaml
    schemas.py
    examples/
      basic_q345r_gmaw.json
    evaluator.py
    runner.py
    tests/
```

### MVP 简化结构（当前实现）

MVP 阶段采用扁平文件结构，每个 Skill 一个 `.py` 文件，内含 prompt、schema、runner：

```text
skills/
  requirement_understanding.py   # prompt + ExtractedFields schema + run()
  candidate_generation.py        # prompt + CandidateResponse schema + run()
```

**有意简化理由**：
- MVP 阶段 Skill 数量少（2 个），目录化增加的开销大于收益
- Prompt 和 schema 在同一文件内更易维护和调试
- 版本通过 `skill_version` / `prompt_version` 属性追踪

**演进计划**：当 Skill 数量超过 4 个或需要独立 prompt 版本管理时，迁移到标准目录结构。

---

## 4. skill.yaml

```yaml
name: candidate_generation
version: 1.0.0
purpose: Generate field candidates based on known fields and evidence.
model_tier: strong
allowed_tools: []
input_schema: CandidateGenerationInput
output_schema: CandidateGenerationOutput
prompt_version: 1.0.0
retry_policy:
  max_retries: 2
  retry_on_schema_error: true
failure_modes:
  - missing_evidence
  - invalid_field_value
  - unsupported_process
```

---

## 5. 必备 Skill

```text
requirement_understanding    ✅ implemented (LLM + regex fallback)
field_summary                ✅ implemented (LLM + deterministic fallback)
field_planning               ✅ implemented (LLM + deterministic fallback)
candidate_generation         ✅ implemented (LLM + deterministic fallback)
override_evaluation          ✅ implemented (LLM + deterministic fallback)
virtual_user_decision        ✅ implemented as actors/virtual.py (DecisionActor base)
global_audit                 ✅ implemented as audit/engine.py (deterministic)
risk_summary                 ✅ implemented (LLM + deterministic fallback)
```

---

## 6. 输入输出示例

```python
from pydantic import BaseModel, Field, ConfigDict

class CandidateGenerationInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    target_fields: list[str]
    field_specs: list[dict]
    known_fields: dict
    evidence: list[dict]
    discussion_history: list[dict] = Field(default_factory=list)

class CandidateItem(BaseModel):
    value: str
    confidence: float = Field(ge=0, le=1)
    reason: str
    evidence_ids: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)

class CandidateGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates: dict[str, list[CandidateItem]]
    recommended: dict[str, str]
    warnings: list[str] = Field(default_factory=list)
```

---

## 7. VirtualDecisionActor Skill 限制

`virtual_user_decision` 不允许自由创造候选外字段值。

允许：

```text
accept_recommended
choose_alternative
request_more_info
reject
override only with explicit rationale and requires_replan=true
```

禁止：

```text
直接生成新焊材
直接生成标准编号
填充 company/client/contract_no
忽略低证据风险
```

---

## 8. Skill 版本记录

每次调用必须记录：

```text
skill_name
skill_version
prompt_version
input_schema_version
output_schema_version
model_name
model_parameters
input_hash
output_hash
validation_status
```

---

## 9. Skill 测试

每个核心 Skill 至少有：

```text
schema validation test
golden example test
invalid output recovery test
no fabrication test
```

不要依赖真实 LLM 做稳定单元测试。稳定测试应使用固定响应或 mock model。
