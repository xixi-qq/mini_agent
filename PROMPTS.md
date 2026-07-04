# AI Prompt 与问题解决记录

本文记录本项目的 Prompt 设计、LLM 输出协议、工具选择策略，以及实现过程中遇到的问题和取舍。

## System Prompt

当前 `AgentRuntime` 使用的 system prompt 位于 `agent/runtime.py`：

```text
你是一个有用的小助手。
你需要判断能否直接回答用户，还是调用一个工具。
- 每次回答只能返回 JSON！

允许的格式：
{"type":"tool_call","thought":"说明为什么需要工具","tool_name":"calculator","arguments":{"expression":"2+2"}}
{"type":"final","thought":"说明为什么已经可以回答","answer":"给用户的最终答案"}

当用户要求计算、搜索、查询天气或管理待办事项时，使用工具。
收到工具结果后继续判断，直到可以给出最终答案。
```

设计目标：

- 让 LLM 在“直接回答”和“调用工具”之间做选择。
- 强制 LLM 返回 JSON，方便程序解析。
- 要求 LLM 收到工具结果后继续判断，而不是把工具调用当作最终答案。

## 工具选择 Prompt 设计

每次调用 LLM 时，`AgentRuntime._build_messages()` 会附加工具 schema：

```text
Available tools: [...]
```

工具 schema 来自每个工具声明的：

- `name`
- `description`
- `parameters`

LLM 根据工具名、描述和 JSON Schema 参数说明自主决定是否调用工具。当前默认工具包括：

| 工具 | 场景 | 说明 |
| --- | --- | --- |
| `calculator` | 数学计算 | 安全计算基础表达式 |
| `search` | 搜索问题 | mock search，用于展示工具调用链路 |
| `todo` | 待办管理 | 待办数据存放在当前 session state |
| `weather` | 天气查询 | mock weather，用于展示外部查询类工具 |

## LLM 输出协议

LLM 必须返回 JSON，不返回 Markdown。

工具调用：

```json
{
  "type": "tool_call",
  "thought": "需要计算",
  "tool_name": "calculator",
  "arguments": {
    "expression": "2 * (3 + 4)"
  }
}
```

最终回复：

```json
{
  "type": "final",
  "thought": "工具结果已足够回答",
  "answer": "结果是 14。"
}
```

`thought` 字段用于记录模型决策原因。程序不会把它直接展示给用户，但它有助于调试和录屏讲解工具选择过程。

## 输出解析策略

`OutputParser` 负责解析 LLM 输出：

- `type=tool_call`：提取 `thought`、`tool_name`、`arguments`
- `type=final`：提取 `thought`、`answer`

解析器支持从带前后缀的文本中提取第一个 JSON 对象。例如模型偶尔返回：

```text
好的，下面是结果：{"type":"final","thought":"ready","answer":"ok"}
```

解析器仍会尽量提取 JSON，降低真实 LLM 格式漂移导致的失败率。

## Context 与 Memory 放置策略

进入 LLM context 的内容由 `AgentRuntime._build_messages()` 统一构建：

1. system prompt
2. tools schema
3. user preferences
4. session summary
5. recent messages

`SessionStore` 负责短期会话记忆：

- `messages`：最近用户输入、assistant 回复、工具结果
- `summary`：被压缩的旧消息
- `state`：工具维护的结构化状态，例如 todo
- `trace`：工具调用日志
- `context.preferences`：用户偏好

`ContextManager` 只负责偏好类 context，不负责完整对话历史。当前会从用户输入中识别：

- “以后用中文回答”“中文回复” -> `language: 中文`
- “用英文回答”“English” -> `language: English`
- “简洁”“简短”“短一点” -> `reply_style: 简洁`
- “详细”“展开讲”“多解释” -> `reply_style: 详细`

保存后会进入后续 system context，例如：

```text
User preferences: language: 中文; reply_style: 简洁
```

## 为什么 trace 不直接进入 context

trace 主要用于调试、审计和录屏展示，例如：

- 调用了哪个工具
- 传入了什么参数
- 工具返回了什么结果
- 工具是否报错

完整 trace 通常包含重复信息和调试信息，如果全部塞进 LLM context，会浪费上下文窗口，也可能干扰模型判断。

当前策略是：

- trace 保存在 session 中，供程序和调试查看。
- 工具结果摘要作为普通消息写回 `messages`。
- 后续 LLM 只看到必要的工具结果，不看到完整调试日志。

## Context 过长如何处理

`SessionStore.max_messages` 默认值为 12。

当消息数量超过上限时：

1. 将更早的消息拼接到 `summary`。
2. 保留最近消息。
3. 构建 context 时同时放入 `summary` 和最近消息。

这个方案不是复杂语义总结，而是最小可用的基础压缩。它适合笔试场景，可以展示“不会无限增长 context”，同时保留追问所需的近期信息。

## 问题与解决

### 1. 如何避免依赖 Agent 框架

主流程全部由 `AgentRuntime` 实现：

- 构建 context
- 调用 LLM
- 解析 LLM 输出
- 调用工具
- 写回工具结果
- 控制最大 loop

工具注册、session、memory、trace 也都是本项目内实现，没有依赖 LangGraph、OpenHands、OpenClaw 等 Agent 框架。

### 2. 如何实现 session 隔离

使用 `SessionStore.get(session_id)` 返回独立 session 字典。

例如：

```powershell
python .\main.py --session window1
python .\main.py --session window2
```

`window1` 和 `window2` 有独立的：

- messages
- summary
- state
- trace
- context preferences

todo 数据存放在 `session["state"]` 中，因此不同窗口的待办事项不会互相污染。

### 3. 如何处理工具失败

工具调用失败时不会直接中断 Agent loop。

当前处理方式：

1. 将错误写入 trace。
2. 构造带 `error` 字段的工具结果。
3. 把错误结果写回 messages。
4. 交给 LLM 继续判断如何回复用户。

这样可以让 LLM 对工具错误做自然语言解释，而不是程序直接返回内部异常。

### 4. 如何测试真实 LLM 不稳定问题

单元测试不调用真实 LLM，而是使用 `FakeLLM` 返回固定 JSON。

原因：

- 真实 LLM 输出可能受网络、模型版本、温度和服务状态影响。
- 单元测试应该稳定验证 runtime 行为。
- CLI 再使用真实 LLM 做集成演示。

测试覆盖：

- calculator 工具调用
- todo session 隔离
- 工具异常处理
- 最大 loop 限制
- 输出解析
- session 压缩
- 用户偏好注入

### 5. 为什么 search 和 weather 使用 mock

本项目重点是展示 Agent Runtime 的核心机制：

- 工具 schema 如何暴露给 LLM
- LLM 如何选择工具
- runtime 如何执行工具
- 工具结果如何回填 context
- trace 如何记录调用过程

search 和 weather 使用 mock 可以减少外部 API 依赖，使演示和测试更稳定。

## 真实 LLM API 说明

`agent/llm.py` 使用 OpenAI-compatible Chat Completions API。

当前默认配置：

```text
base_url = https://api.deepseek.com
model    = deepseek-v4-pro
api_key  = DEEPSEEK_API_KEY
```

运行 CLI 前配置：

```powershell
$env:DEEPSEEK_API_KEY="你的 API Key"
python .\main.py --session window1
```

如果使用其他 OpenAI-compatible 服务，可以在创建 `OpenAICompatibleLLM` 时传入自定义 `api_key`、`model`、`base_url`。

## 演示建议

建议录屏或答辩时按以下顺序展示：

1. **calculator 工具调用**：输入数学表达式，展示 LLM 选择工具、工具返回结果、Agent 最终回答。
2. **todo session 隔离**：分别启动 `window1` 和 `window2`，添加不同待办，证明 state 不互相污染。
3. **context preference**：输入“以后用中文回答，回复简洁一点”，展示偏好进入后续 context。
4. **异常处理**：输入危险或非法表达式，展示工具报错后 Agent 仍能返回可读解释。
5. **测试用例**：运行 `python -m unittest discover -s tests`，展示核心行为有自动化测试覆盖。
