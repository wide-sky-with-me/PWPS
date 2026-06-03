# pWPS Agent 开发阶段规划 development_stages.md

## 1. 文档定位

本文档定义 pWPS Agent 的阶段化开发路线。每个阶段必须明确目标、技术增量、暂不引入的内容、交付物和验收标准。

原则：

> 每一阶段都必须形成可运行、可测试、可回退的工程增量。

---

# Phase 0：项目骨架与环境锁定

## 目标

建立可复现的 Monorepo 开发环境。

## 引入技术

```text
pnpm workspace
uv
FastAPI 空服务
Next.js 空应用
PostgreSQL
Redis
Docker Compose
ruff / mypy / pytest
eslint / prettier / typecheck
```

## 交付物

```text
apps/web
apps/api
infra/docker-compose.yml
.env.example
README 启动说明
```

## 验收标准

1. `pnpm install` 成功。
2. `uv sync` 成功。
3. API health check 可访问。
4. Web 首页可访问。
5. PostgreSQL、Redis 可启动。

---

# Phase 1：领域模型与 Schema

## 目标

用 Pydantic v2 固化核心领域模型。

## 引入技术

```text
Pydantic v2
StrEnum / Enum
schema_version
field_registry_version
```

## 必须实现

```text
FieldSpec
FieldGroupSpec
FieldState
Evidence
DecisionContext
DecisionResult
AuditIssue
AuditResult
WorkflowState
```

## 验收标准

1. 所有状态为枚举，不出现裸字符串状态。
2. Field Registry 可加载。
3. Schema 可序列化和反序列化。
4. 纯 schema 单元测试通过。

---

# Phase 2：Auto CLI 最小闭环

## 目标

跑通 Auto Draft 的最小工作流。

## 技术范围

```text
LangGraph
Pydantic Skill schema
Mock KnowledgeService
Mock / real LLM 可切换
```

## 必须实现

```text
normalize_input
understand_requirement
build_confirmation_queue
confirm_target_subgraph
VirtualDecisionActor
global_audit
finalize_output
```

## 暂不引入

```text
完整 Web UI
Guided interrupt/resume
Qdrant
MinIO
复杂文档解析
```

## 验收标准

输入：

```text
Q345R，12mm，对接焊，平焊，GMAW，生成 pWPS 草案
```

能够输出：

```text
pwps.json
field_report.json
risk_report.json
discussion_trace.json
```

---

# Phase 3：FastAPI API 与持久化

## 目标

把 Auto 闭环接入 API 和数据库。

## 技术增量

```text
FastAPI routes
SQLAlchemy async
Alembic
PostgreSQL JSONB
Redis 状态事件
```

## 必须实现

```text
POST /api/runs
GET /api/runs/{run_id}
GET /api/runs/{run_id}/outputs
GET /api/runs/{run_id}/events
```

## 验收标准

1. Run 可创建。
2. WorkflowState 可持久化。
3. TraceEvent 可查询。
4. 输出可从 API 获取。

---

# Phase 4：Guided 中断恢复

## 目标

实现真实用户参与字段确认。

## 技术增量

```text
HumanDecisionActor
PendingUserDecision
LangGraph checkpoint / resume
Redis pending decision
```

## 必须实现

```text
GET /api/runs/{run_id}/current-decision
POST /api/runs/{run_id}/decision
```

## 验收标准

1. Workflow 可停在等待用户决策。
2. 用户提交后可恢复。
3. current_discussion 不丢失。
4. 重启后 pending decision 可恢复。

---

# Phase 5：前端字段确认工作台

## 目标

实现用户友好的多端字段确认界面。

## 技术增量

```text
Next.js App Router
shadcn/ui
TanStack Query
React Hook Form
Zod
```

## 必须实现

```text
任务创建页
字段确认工作台
证据面板
风险面板
最终输出预览页
```

## 验收标准

1. 桌面端三栏布局可用。
2. 平板端双栏布局可用。
3. 移动端单栏折叠布局可用。
4. 用户能完成 Guided 核心流程。

---

# Phase 6：本地文档检索与证据链增强

## 目标

让 KnowledgeService 从本地文档和简单索引中提供证据。

## 技术增量

```text
Local Document Provider
EvidenceNormalizer
基础文档元数据
```

## 暂不强制引入

```text
Qdrant
MinIO
复杂文档解析服务
```

## 验收标准

1. Evidence 包含 source、section、content、limitations。
2. 字段能挂载 evidence_ids。
3. 证据面板能展示来源。

---

# Phase 7：审计修复闭环 ✅

## 目标

审计问题能转化为 repair target，重新进入字段组确认。

## 技术增量

```text
AuditRuleType
RepairTarget (via FieldTarget)
repair loop (LangGraph conditional edge + guided re-entry)
```

## 实现状态

- `AuditEngine` 5 条规则全部实现：provided_only, process_consumable_match, required_fields, high_risk_auto_confirmation, low_credibility_evidence
- `build_repair_targets` 将审计问题映射为 `FieldTarget`，标记字段为 `NEEDS_REPAIR`
- Auto 工作流：`global_audit` 后条件边判断，HARD/COMPLETENESS 问题触发修复循环（最多 3 轮）
- Guided 工作流：审计后如有可操作问题，重新入队修复目标并生成 `PendingUserDecision`
- Risk report 输出包含 `repair_targets`
- 所有 28 个测试通过，ruff/mypy 检查通过

## 验收标准

1. ✅ GMAW + J422 能被识别为硬冲突。
2. ✅ 元信息 model_prior 能被禁止。
3. ✅ 高风险字段低证据能降级 publishability。
4. ✅ 可生成 repair target。

---

# Phase 8：文档解析、向量库、对象存储

## 目标

接入更完整的知识库能力。

## 技术增量

```text
Milvus (vector store)
MinIO (object storage)
MinerU / Docling (document parsing)
Embedding (SiliconFlow)
Reranker (SiliconFlow)
Document ingestion CLI
```

## 验收标准

1. 文档解析进入统一 IR。
2. 向量检索返回 KnowledgeHit。
3. EvidenceNormalizer 不受具体检索源影响。
4. 文件产物存储可切换 Local FS / MinIO。

---

# Phase 9：评估、观测、安全、部署增强

## 目标

让系统具备长期迭代能力。

## 技术增量

```text
Evaluation dataset
Run trace viewer
Skill call logging
Security checks
Deployment scripts
```

## 验收标准

1. 有固定评估集。
2. 可复现 Skill 版本。
3. 可追踪字段来源。
4. 有基础安全边界和部署说明。

---

## 跨阶段约束

1. 每个阶段都必须可运行。
2. 每个阶段都必须有最小测试。
3. 不允许为了赶阶段跳过 schema。
4. 不允许为了赶阶段绕过审计。
5. 不允许引入未记录的新技术。
6. 不允许保留过时测试误导后续开发。
