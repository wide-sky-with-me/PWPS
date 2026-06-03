# Phase 8: LLM 集成与向量检索

## 决策记录

| 决策 | 结论 |
|------|------|
| LLM 提供商 | 可切换抽象层，MVP 用 langchain-openai（OpenAI 兼容 API） |
| 异步改造 | 一次性全量改造 |
| 向量库 | Milvus（Docker 本地部署，支持混合检索和分区） |
| Embedding | OpenAI 兼容 API（通过 OPENAI_BASE_URL 指向自建或云服务） |
| 文档解析 | MVP 跳过，先用手动准备的文档验证全链路 |
| 文件存储 | MVP 保持 Local FS，设计 StorageBackend 接口 |
| 结构化输出 | LangChain with_structured_output() |
| 文档入库 | CLI 预处理脚本 |

## 实施步骤

### Step 1: 异步全量改造
- Skills run 方法 → async
- KnowledgeService → async
- KnowledgeProviders → async
- VirtualDecisionActor → async
- LangGraph 节点 → async def
- 工作流入口 → async
- CLI → asyncio.run()
- 测试适配 pytest-asyncio

### Step 2: LLM 抽象层集成
- 添加 langchain-openai 依赖
- 创建 LLM 工厂模块
- RequirementUnderstandingSkill 改用 LLM
- CandidateGenerationSkill 改用 LLM

### Step 3: Milvus 向量库集成
- docker-compose 加入 Milvus 栈
- 添加 langchain-milvus 依赖
- 创建 VectorStoreProvider
- CLI 文档入库脚本

### Step 4: KnowledgeService 重构
- VectorStoreProvider 接入
- 扩充测试数据
- EvidenceNormalizer 适配

### Step 5: VirtualDecisionActor 改造
- 用 LLM 评估候选值

### Step 6: 验证与修复
- 全链路端到端测试
- 修复硬编码时间戳
- 更新文档
