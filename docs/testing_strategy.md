# pWPS Agent 测试策略 testing_strategy.md

## 1. 文档定位

本文档定义测试分层、测试边界、LLM Mock、前后端测试范围，以及避免过度测试和过时测试的规则。

---

## 2. 测试原则

1. 测核心业务，不测第三方库。
2. 测状态转换，不测实现细枝末节。
3. 测领域规则，不测 UI 组件库本身。
4. LLM 相关测试使用 mock / fixture。
5. 能合并的测试合并。
6. 过时测试及时删除。
7. 不为覆盖率制造脆弱测试。

---

## 3. 测试分层

### P0：纯函数和 Schema 测试

必须覆盖：

```text
FieldSpec validation
FieldState validation
build_confirmation_queue
audit rule mapping
publishability mapping
schema serialization
```

### P1：Workflow 集成测试

必须覆盖：

```text
Auto 模式完整跑通
Guided interrupt/resume
审计发现问题生成 repair target
blocked 状态处理
```

### P2：API Contract 测试

必须覆盖：

```text
POST /api/runs
GET /api/runs/{run_id}
GET /api/runs/{run_id}/current-decision
POST /api/runs/{run_id}/decision
GET /api/runs/{run_id}/outputs
```

### P3：前端关键路径测试

必须覆盖：

```text
创建任务
查看字段确认卡
提交用户决策
查看风险和证据
查看最终结果
```

### P4：Skill 测试

必须覆盖：

```text
输出 schema 校验
缺字段恢复
禁止推断字段不被编造
候选必须带 evidence_ids
```

---

## 4. 不应该测试什么

```text
不为 getter/setter 写测试
不测试 shadcn/ui 基础组件行为
不测试 FastAPI / SQLAlchemy / React Query 的内部行为
不保留已经不符合当前 workflow 的旧测试
不为了覆盖率测试无业务价值分支
```

---

## 5. LLM Mock 策略

稳定测试中不调用真实模型。

推荐：

```text
MockRequirementUnderstandingSkill
MockCandidateGenerationSkill
MockVirtualDecisionSkill
MockGlobalAuditSkill
```

真实模型调用只用于：

```text
手动验收
评估集运行
回归评估
```

---

## 6. 测试删除规则

测试过时后必须删除或重写。过时测试包括：

```text
测试旧 API
测试旧字段名
测试旧 workflow
测试已废弃行为
测试临时 patch 行为
```

删除测试时要说明原因。
