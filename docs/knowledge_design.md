# pWPS Agent 知识检索与证据设计 knowledge_design.md

## 1. 文档定位

本文档定义 KnowledgeService、知识来源、检索结果结构、统一 IR、证据归一化、RAG 演进和证据可信度策略。

---

## 2. 知识层目标

Knowledge Layer 不直接生成字段，不决定最终字段值。它只为候选生成和审计提供可追踪证据。

职责：

1. 根据字段组检索计划执行多源检索。
2. 统一不同知识源返回结构。
3. 将检索结果归一化为 Evidence。
4. 将 Evidence 挂载到目标字段。
5. 保留来源、页码、章节、限制说明和可信度。

---

## 3. 知识源优先级

```text
用户明确输入
  >
企业标准 / 本地标准
  >
结构化知识库
  >
历史 WPS/PQR
  >
教材 / 手册 / 本地文档
  >
公开网页
  >
模型常识
```

模型常识只能作为低置信辅助，不得作为高风险字段唯一依据。

---

## 4. KnowledgeProvider 接口

```python
class KnowledgeQuery(BaseModel):
    query: str
    target_fields: list[str]
    preferred_sources: list[SourceType]
    purpose: str
    context: dict

class KnowledgeHit(BaseModel):
    source_type: SourceType
    source_id: str
    title: str
    section_path: list[str] = []
    content: str
    page: int | None = None
    table_id: str | None = None
    score: float | None = None
    metadata: dict = {}
    limitations: str | None = None

class KnowledgeProvider:
    async def search(self, query: KnowledgeQuery) -> list[KnowledgeHit]:
        ...
```

---

## 5. EvidenceNormalizer

```text
KnowledgeHit -> Evidence
```

归一化时必须处理：

```text
source_type
source_title
source_ref
section_path
content
target_fields
credibility
limitations
retrieved_at
metadata
```

用户上传文档和网页内容只能作为证据候选，不得直接覆盖字段状态。

---

## 6. 统一 IR

文档解析后不直接入向量库，应先进入统一 IR。

```json
{
  "doc_id": "doc_001",
  "source_type": "standard",
  "title": "...",
  "sections": [],
  "tables": [],
  "figures": [],
  "metadata": {},
  "field_tags": [],
  "doc_version": "1.0.0"
}
```

---

## 7. 分阶段实现

### MVP

```text
Local Document Provider
Web Provider 可选
Model Prior Provider
EvidenceNormalizer
```

### V1 ✅

```text
Milvus Vector Store (SiliconFlow embedding)
MinIO Object Storage (docker-compose only, app integration pending)
Embedding Service (SiliconFlow Qwen/Qwen3-Embedding-0.6B)
Reranker (SiliconFlow BAAI/bge-reranker-v2-m3)
```

### V2

```text
MinerU / Docling 文档解析
结构化 KB
历史 WPS/PQR 管理
标准 Profile
```

---

## 8. 检索策略

字段组确认时，先由 `field_planning_skill` 生成检索计划，然后 KnowledgeService 执行。

检索计划必须包含：

```text
target_fields
query
purpose
preferred_sources
required_evidence_type
```

---

## 9. 证据可信度

不要过度依赖单个数值分数。可信度由来源类型、命中质量、上下文适配性和限制说明共同决定。

推荐：

```text
user_input / enterprise_standard / history_pqr: high
local_standard / structured_kb / history_wps: high-medium
textbook / handbook / local_document: medium
web: medium-low
model_prior: low
```

---

## 10. 安全边界

1. 文档内容不能绕过 EvidenceNormalizer。
2. 网页内容不能作为高风险字段唯一证据。
3. 用户上传内容可能包含 Prompt Injection，必须视为非可信输入。
4. Evidence 只支持候选生成和审计，不直接提交字段。
