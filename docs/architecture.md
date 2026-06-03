# pWPS Agent 系统架构设计 architecture.md

## 1. 文档定位

本文档定义 pWPS Agent 的整体技术架构、模块边界、调用关系、工程分层和项目结构。

---

## 2. 总体架构

推荐架构：

```text
确定性 LangGraph 工作流
  +
字段级 LLM Skill
  +
统一 KnowledgeService
  +
DecisionActor 决策对象
  +
Pydantic v2 状态模型
  +
确定性 Audit Engine
  +
独立 Output / Render 模块
```

系统不采用全局自由 Supervisor 作为主控。主控流程由 LangGraph 的确定性节点负责；LLM 只作为节点内部的结构化 Skill 使用。

---

## 3. 分层架构

```text
Presentation Layer
  Web UI / CLI / API

Application Layer
  FastAPI Routes
  Run Service
  Session Service
  Workflow Orchestrator

Domain Layer
  Field Registry
  Field Policies
  Field Dependencies
  Discussion Manager
  Audit Engine

AI Skill Layer
  Requirement Understanding Skill
  Field Summary Skill
  Field Planning Skill
  Candidate Generation Skill
  Override Evaluation Skill
  Virtual Decision Skill
  Global Audit Skill

Knowledge Layer
  KnowledgeService
  EvidenceNormalizer
  Structured KB Provider
  Local Document Provider
  Vector Store Provider
  Web Provider
  History WPS/PQR Provider

Persistence Layer
  PostgreSQL
  Redis
  Local FS / MinIO
  LangGraph Checkpoint Store

Output Layer
  JSON Builder
  Report Builder
  Markdown Renderer
  DOCX/PDF Renderer
```

---

## 4. Monorepo 项目结构

```text
pwps-agent/
  apps/
    web/
      app/
      components/
      lib/
      hooks/
      package.json
    api/
      pyproject.toml
      uv.lock
      src/pwps_agent_api/
        main.py
        api/
        core/
        workflow/
        fields/
        schemas/
        skills/
        actors/
        knowledge/
        audit/
        output/
        storage/
        db/
      tests/
  packages/
    shared/              # 可选：OpenAPI 生成类型或共享 TS 类型
  docs/
  infra/
    docker-compose.yml
    postgres/
    redis/
  scripts/
```

---

## 5. 模块边界

### 5.1 Workflow

负责确定性编排，不直接拼 Prompt，不直接查询数据库细节，不直接修改渲染结果。

### 5.2 Skill

负责一次结构化 LLM 能力调用。每个 Skill 必须有 input schema、output schema、prompt、runner、validator、retry policy、examples。

### 5.3 DecisionActor

负责字段确认决策。`VirtualDecisionActor` 只审候选、选候选、请求补证，不自由生成新字段。

### 5.4 KnowledgeService

负责检索和证据归一化，不决定字段最终值。

### 5.5 AuditEngine

负责确定性规则审计和 LLM 辅助解释，不允许静默修复字段。

### 5.6 Output / Render

Output Builder 生成结构化数据；Render 只渲染，不修改字段事实。

---

## 6. 状态与持久化原则

所有核心状态使用 Pydantic v2 模型和枚举定义。

必须持久化：

```text
run_id
raw_input
mode
field_states
target_queue
current_target
discussion_sessions
evidence_store
audit_result
final_output
trace
schema_version
field_registry_version
skill_versions
```

可缓存或可重建：

```text
raw_search_results
evidence_summary
candidate_bundle
render_payload
LLM intermediate response
```

---

## 7. 技术演进边界

MVP 不做微服务拆分。所有核心能力先在单 FastAPI 服务中实现。

后续如果拆分，优先拆：

```text
Document Ingestion Worker
Embedding / Rerank Worker
Rendering Worker
Evaluation Worker
```

不要过早拆分 Workflow、Field Registry、Audit Engine。

---

## 8. 架构禁区

1. Workflow Node 直接拼 Prompt。
2. 前端实现字段推理逻辑。
3. KnowledgeService 直接写 FieldState.confirmed。
4. Render 模块修改字段内容。
5. LLM 直接输出最终可签发 WPS。
6. 用临时 patch 绕过 Field Registry、Audit Engine 或 State Machine。
7. 为单个 bug 引入大而重的新框架。
