# pWPS Agent 技术选型与开发环境 tech_stack.md

## 1. 文档定位

本文档明确 pWPS Agent 的开发环境、技术栈、基础服务、依赖管理、启动方式和技术引入规则。

---

## 2. 总体技术栈

```text
Frontend:
  pnpm + Next.js App Router + TypeScript + Tailwind CSS + shadcn/ui + TanStack Query

Backend:
  uv + Python 3.12+ + FastAPI + Pydantic v2 + LangGraph + SQLAlchemy async + Alembic

Storage:
  PostgreSQL + Redis + Local FS

Knowledge V1+:
  Milvus + MinIO + MinerU / Docling + Embedding + Reranker
```

---

## 3. 前端环境

必须使用：

```text
pnpm
Node.js LTS
pnpm-workspace.yaml
pnpm-lock.yaml
```

禁止：

```text
npm install
yarn install
混用 lockfile
```

常用命令：

```bash
pnpm install
pnpm --filter web dev
pnpm --filter web build
pnpm --filter web lint
pnpm --filter web typecheck
```

---

## 4. 后端环境

必须使用：

```text
uv
Python 3.12+
pyproject.toml
uv.lock
.venv
```

禁止：

```text
pip install 直接改环境
poetry
conda 作为项目依赖管理器
未提交 uv.lock
```

常用命令：

```bash
cd apps/api
uv sync
uv run fastapi dev src/pwps_agent_api/main.py
uv run pytest
uv run ruff check .
uv run mypy .
```

---

## 5. 前端技术选择

| 技术 | 用途 |
|---|---|
| Next.js App Router | 页面、路由、服务端渲染能力 |
| TypeScript | 类型安全 |
| Tailwind CSS | 样式系统 |
| shadcn/ui | 可定制组件基础 |
| TanStack Query | 服务端状态、请求缓存、mutation |
| React Hook Form + Zod | 表单校验 |
| React Flow | 可选：流程图 / 状态流展示 |
| Recharts | 可选：指标和评估图表 |
| react-markdown | Markdown 预览 |

前端默认不引入 Redux。除非出现明确的复杂客户端状态需求。

---

## 6. 后端技术选择

| 技术 | 用途 |
|---|---|
| FastAPI | API 服务 |
| Pydantic v2 | Schema、状态、LLM 输出校验 |
| LangGraph | 工作流编排、checkpoint、中断恢复 |
| SQLAlchemy async | PostgreSQL ORM |
| Alembic | 数据库迁移 |
| Redis | 缓存、事件、pending decision、轻量队列 |
| ruff | lint / format |
| mypy | 类型检查 |
| pytest | 测试 |

---

## 7. 基础服务

### MVP

```text
PostgreSQL
Redis
Local FS
```

### V1/V2

```text
Milvus (vector store)
MinIO (object storage)
MinerU / Docling (document parsing)
Embedding Service (SiliconFlow)
Reranker Service (SiliconFlow)
```

---

## 8. docker-compose

```yaml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: pwps_agent
      POSTGRES_USER: pwps
      POSTGRES_PASSWORD: pwps
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  # Milvus vector store stack
  etcd:
    image: quay.io/coreos/etcd:v3.5.18

  minio:
    image: minio/minio:RELEASE.2023-03-20T20-16-18Z
    ports:
      - "9000:9000"
      - "9001:9001"

  milvus:
    image: milvusdb/milvus:v2.5.13
    ports:
      - "19530:19530"
```

---

## 9. 新技术引入规则

任何新技术、新包、新服务引入前，必须先完成小型调查并写入变更说明：

```text
目的是什么？
现有技术是否能解决？
替代方案有哪些？
是否增加部署复杂度？
是否影响性能、安全、包体积、维护成本？
是否需要新增测试？
是否需要更新文档？
回滚成本如何？
```

---

## 10. 版本锁定

必须提交：

```text
pnpm-lock.yaml
uv.lock
alembic migration
.env.example
```

禁止依赖“本机刚好能跑”的环境状态。
