# Minimal Agent Runtime

这是一个从零实现的最小可用 Agent 框架，没有依赖 langgraph、openhands、openclaw 等现有 Agent 框架。核心目标是展示 Agent loop、工具注册、LLM 输出解析、session 隔离、context 管理、异常处理和 trace。

## 目录结构

```text
agent/
  runtime.py        # Agent 主循环
  llm.py            # OpenAI-compatible LLM API 封装
  parser.py         # 解析 LLM JSON 输出
  session.py        # 多 session、短期消息、消息压缩
  memory.py         # 偏好 context 管理
  trace.py          # 工具调用日志
  tools/
    base.py         # Tool 抽象与注册表
    calculator.py   # 数学计算工具
    search.py       # mock search
    todo.py         # session 内待办
    weather.py      # mock weather
main.py             # CLI 入口
tests/              # 单元测试
```

## 运行方式

使用真实 LLM API：

```powershell
$env:OPENAI_API_KEY="你的 API Key"
$env:OPENAI_MODEL="gpt-4.1-mini"
python .\main.py --session window1
```

如使用 OpenAI-compatible 服务：

```powershell
$env:OPENAI_BASE_URL="https://your-provider.example/v1"
$env:OPENAI_API_KEY="你的 API Key"
$env:OPENAI_MODEL="模型名"
python .\main.py --session window2
```

运行测试：

```powershell
python -m unittest discover -s tests
```

## Agent Loop

每次用户输入后，`AgentRuntime.run()` 执行以下流程：

1. 将用户输入写入当前 `session` 的 messages。
2. 构建 LLM context：system prompt、工具 schema、偏好 context、session summary、最近消息。
3. 调用真实 LLM API。
4. 通过 `OutputParser` 解析 LLM 输出。
5. 如果是 `tool_call`，从 `ToolRegistry` 找到工具并执行。
6. 将工具结果或错误写入 trace，并作为普通消息放回 session。
7. 继续 loop，直到 LLM 返回 `final` 或达到最大轮次。

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

## 工具注册机制

所有工具继承 `Tool`，必须提供：

- `name`
- `description`
- `parameters` JSON Schema
- `run(arguments, session_state)`

默认注册工具：

- `calculator`：安全计算基础数学表达式
- `search`：mock 搜索
- `todo`：当前 session 内新增、查询、清空待办
- `weather`：mock 天气查询

## Session 管理

`SessionStore` 使用 `session_id` 隔离状态。比如：

```powershell
python .\main.py --session window1
python .\main.py --session window2
```

`window1` 和 `window2` 拥有独立的：

- messages
- summary
- context preferences
- state
- trace

因此用户 A 的窗口 1 可以记录“查天气”，窗口 2 可以记录“写周报”，两边不会互相污染。

## Session、Context 与 Memory 策略

进入 LLM context 的内容：

- system prompt
- 工具 schema
- context preferences
- session summary
- 最近 N 条消息
- 工具执行结果摘要

`session` 是全量会话容器，负责保存和管理短期消息：

- `messages`：最近对话与工具结果
- `summary`：被压缩的旧消息
- `state`：工具维护的结构化状态
- `trace`：工具调用日志
- `context.preferences`：用户偏好

`ContextManager` 不再管理短期对话消息，只负责把偏好类信息转换成 system context。比如语言、输出风格、展示偏好等。

当前支持从用户输入中轻量识别并保存偏好：

- 语言：如“以后用中文回答”“用英文回答”
- 回复风格：如“回复简洁一点”“详细解释”

保存后会进入后续 LLM context，例如：

```text
User preferences: language: 中文; reply_style: 简洁
```

不把完整长期 trace 全部塞入 LLM context。trace 用于调试和审计，只有工具结果摘要作为普通消息进入最近上下文。

压缩触发时机：

- `SessionStore.max_messages` 默认 12。
- 超过后，将更早消息拼入 `summary`。
- 保留最近消息，支持追问和后续工具调用。

这是 session 内的基础短期记忆压缩，不做复杂语义总结，适合笔试中的最小实现。

## 异常处理

- LLM 输出不是合法 JSON：返回格式错误说明。
- 工具不存在：记录 trace error，并把错误结果交给 LLM 继续处理。
- 工具参数错误或执行失败：记录 trace error。
- 超过最大 loop：返回轮次限制提示。

## 测试覆盖

测试位于 `tests/test_runtime.py`，覆盖：

- calculator 工具调用
- todo 多 session 隔离
- 工具异常处理
- 最大 loop 限制
- LLM 输出解析
- session 消息压缩
- context 偏好注入
