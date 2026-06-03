# 部署与运行指南 deployment_guide.md

## 1. 文档定位

本文档定义 pWPS Agent 的本地开发、测试环境和后续部署的基础规则。

---

## 2. 环境类型

```text
local      本地开发
staging    测试 / 演示环境
production 生产环境
```

MVP 只要求 local 可稳定运行。

---

## 3. 本地开发启动顺序

```bash
# 1. 启动基础服务（PostgreSQL + Redis + Milvus 栈）
cd infra
docker compose up -d

# 2. 后端
cd ../apps/api
uv sync
uv run alembic upgrade head
uv run fastapi dev src/pwps_agent_api/main.py

# 3. 前端
cd ../web
pnpm install
pnpm dev

# 4. 文档入库（可选，需要 EMBEDDING_API_KEY）
uv run python -m pwps_agent_api.cli.ingest --source data/knowledge_base/local_documents.json
```

---

## 4. 环境变量

必须提供 `.env.example`。

推荐字段：

```text
DATABASE_URL=
REDIS_URL=
LOCAL_ARTIFACT_DIR=./storage/artifacts

# LLM (deepseek | openai)
LLM_PROVIDER=deepseek
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash

# Embedding (SiliconFlow)
EMBEDDING_API_KEY=
EMBEDDING_BASE_URL=https://api.siliconflow.cn/v1
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-0.6B

# Reranker (SiliconFlow)
RERANKER_API_KEY=
RERANKER_BASE_URL=https://api.siliconflow.cn/v1
RERANKER_MODEL=BAAI/bge-reranker-v2-m3

# Milvus
MILVUS_URI=http://localhost:19530
```

禁止：

```text
提交 .env
把 API key 写入前端
把密钥写入文档示例真实值
```

---

## 5. 数据库迁移

数据库结构变更必须：

```text
修改 SQLAlchemy model
生成 Alembic migration
本地 upgrade 测试
必要时写 downgrade 或回滚说明
更新 change_management.md 相关记录
```

---

## 6. 文件存储

MVP 使用 Local FS：

```text
storage/uploads
storage/artifacts
storage/parsed_docs
```

后续切换 MinIO 时，业务代码应通过 StorageService 访问，不直接依赖本地路径。

---

## 7. 备份与恢复

至少考虑：

```text
PostgreSQL run 数据
上传文件
生成 artifacts
Skill 调用记录
评估集
```

MVP 可以手动备份；企业级阶段需要自动备份。

---

## 8. 健康检查

后端至少提供：

```http
GET /health
GET /ready
```

`/health` 检查服务进程。

`/ready` 检查 PostgreSQL、Redis、必要配置。当前实现通过数据库 `select 1` 和 Redis `PING` 验证连通性。

---

## 9. 部署阶段建议

### MVP local

```text
Docker Compose + 本机 Web/API
```

### Demo staging

```text
单机部署
PostgreSQL + Redis + API + Web
反向代理
```

### Production

```text
容器化部署
独立数据库
对象存储
日志采集
权限与审计
备份恢复
```

---

## 10. 部署禁区

1. 不在生产环境使用开发密钥。
2. 不把 LLM key 暴露到前端。
3. 不使用本机临时路径作为生产文件存储。
4. 不跳过数据库迁移。
5. 不在未脱敏日志中保存敏感文件内容。
