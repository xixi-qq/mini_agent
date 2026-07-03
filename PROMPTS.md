# AI Prompt 与问题解决记录

## System Prompt

```text
你是一个最小化 Agent 运行时。
判断应该直接回答用户，还是调用一个工具。
只能返回 JSON，不要返回 Markdown。

允许的格式：
{"type":"tool_call","thought":"说明为什么需要工具","tool_name":"calculator","arguments":{"expression":"2+2"}}
{"type":"final","thought":"说明为什么已经可以回答","answer":"给用户的最终答案"}

当用户要求计算、搜索、查询天气或管理待办事项时，使用工具。
收到工具结果后继续判断，直到可以给出最终答案。
```

## 工具选择 Prompt 设计

每次调用 LLM 时会附加工具 schema：

```text
Available tools: [...]
```

LLM 根据工具 `name`、`description`、`parameters` 自主决定是否调用工具。

## 输出解析策略

要求 LLM 返回 JSON：

- `type=tool_call`：提取 `thought`、`tool_name`、`arguments`
- `type=final`：提取 `thought`、`answer`

解析器支持从带前后缀的文本中提取第一个 JSON 对象，用于降低模型偶发格式漂移带来的失败率。

## 问题与解决

### 1. 如何避免依赖 Agent 框架

主流程全部由 `AgentRuntime` 实现：

- 构建 context
- 调 LLM
- 解析输出
- 调工具
- 写回工具结果
- 控制 loop

工具注册、session、memory 也都是本项目内实现。

### 2. 如何实现 session 隔离

使用 `SessionStore.get(session_id)` 返回独立 session 字典。todo 状态放在 `session["state"]` 中，因此不同窗口的 todo 不共享。

### 3. 哪些信息放入 LLM context

放入：

- system prompt
- 工具 schema
- context preferences
- summary
- 最近用户输入、assistant 输出、tool 结果

不直接放入完整 trace。trace 更适合调试和录屏展示。

### 4. context 过长如何处理

短期消息由 `SessionStore` 管理。当前实现用最大消息数限制，超过后把旧消息拼接进 summary，并保留最近消息。这样可以保留基本状态，同时避免 LLM context 无限制增长。

`ContextManager` 不负责短期消息压缩，只负责保存和注入偏好类信息，例如语言、输出风格、用户习惯等。

当前实现会从用户输入中识别简单偏好：

- “以后用中文回答”“中文回复” -> `language: 中文`
- “用英文回答”“English” -> `language: English`
- “简洁”“简短”“短一点” -> `reply_style: 简洁`
- “详细”“展开讲”“多解释” -> `reply_style: 详细`

### 5. 如何测试真实 LLM 不稳定问题

单元测试不调用真实 LLM，而是用 `FakeLLM` 返回固定 JSON。这样可以稳定测试 runtime 行为。真实 LLM 通过 CLI 做集成演示。
