# pWPS Agent 安全与领域风险 security_and_safety.md

## 1. 文档定位

本文档定义文件安全、Prompt Injection 防护、敏感信息保护、领域风险边界和安全约束。

---

## 2. 领域安全边界

1. 系统不生成正式可签发 WPS。
2. 系统不替代 PQR/WPQR。
3. 高风险字段必须标记人工确认。
4. 禁止推断字段不得由模型补全。
5. 输出必须包含风险说明和发布性评级。
6. `draft_publishable` 仍然只是草案可参考，不代表正式合规。

---

## 3. 文件安全

用户上传文件：

```text
限制文件类型
限制文件大小
隔离存储
生成唯一文件 ID
不直接执行文件内容
解析失败要安全退出
```

---

## 4. Prompt Injection 防护

用户上传文档、网页内容、历史 WPS 都可能包含恶意指令。

规则：

1. 文档内容只作为 Evidence 候选。
2. 文档内容不能修改系统 Prompt。
3. 文档内容不能绕过 Field Registry。
4. 文档内容不能直接确认字段。
5. Skill Prompt 必须区分“证据内容”和“系统指令”。

---

## 5. API Key 与环境变量

1. API key 不得进入前端。
2. `.env` 不得提交。
3. 提供 `.env.example`。
4. 日志中脱敏 key、token、文件路径中的敏感信息。

---

## 6. Web 检索风险

1. Web 来源可信度默认低于本地标准和企业知识。
2. Web 不得作为高风险字段唯一证据。
3. Web 内容必须记录来源和 retrieved_at。
4. Web 证据必须显示限制说明。

---

## 7. 审计强制规则

以下问题不得静默通过：

```text
GMAW + J422
provided_only 字段由 model_prior 生成
company/client/contract_no 被模型编造
高风险字段没有证据
热处理字段被草率省略
```

---

## 8. 日志与隐私

日志保存：

```text
run_id
trace event
schema version
skill version
错误类型
```

谨慎保存：

```text
原始上传文件内容
用户企业信息
合同信息
客户信息
API key
```
