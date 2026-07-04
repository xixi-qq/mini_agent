# Minimal Agent Runtime

一个从零实现的最小可用 Agent 运行时，用于展示 Agent loop、工具注册、LLM 输出解析、session 隔离、context 管理、基础记忆压缩、异常处理和工具 trace。

项目不依赖 LangGraph、OpenHands、OpenClaw 等现有 Agent 框架，核心调度流程由 `AgentRuntime` 自行实现。

## 功能概览

- **Agent Loop**：接收用户输入，判断直接回复或调用工具，拿到工具结果后继续推理，直到返回最终答案。
- **工具注册机制**：每个工具声明 `name`、`description`、`parameters` JSON Schema，LLM 基于 schema 自主选择工具。
- **多 Session 隔离**：不同 `session_id` 拥有独立 messages、summary、state、trace 和用户偏好。
- **Context 管理**：组合 system prompt、工具 schema、用户偏好、session summary 和最近消息。
- **基础记忆压缩**：超过消息数量上限后，将旧消息压缩进 `summary`，保留最近上下文用于追问。
- **异常与 Trace**：解析失败、工具不存在、工具执行失败、最大轮次限制都有处理；工具调用会写入 trace。
- **可测试设计**：单元测试使用 `FakeLLM` 固定输出，避免真实 LLM 不稳定影响 runtime 行为测试。

## 目录结构

```text
mini_agent/
  agent/
    runtime.py        # Agent 主循环与上下文组装
    llm.py            # OpenAI-compatible Chat Completions API 封装
    parser.py         # 解析 LLM JSON 输出
    session.py        # 多 session、短期消息与消息压缩
    memory.py         # 用户偏好 context 管理
    trace.py          # 工具调用日志
    debug_log.py      # LLM 原始输出与错误日志
    tools/
      base.py         # Tool 抽象、装饰器与注册表
      calculator.py   # 安全数学计算工具
      search.py       # mock 搜索工具
      todo.py         # session 内待办工具
      weather.py      # mock 天气工具
  tests/
    test_runtime.py   # runtime、parser、session、context 单元测试
  main.py             # CLI 入口
  PROMPTS.md          # Prompt 设计与问题解决记录
  README.md
```

## 环境要求

- Python 3.10+
- 可访问的 OpenAI-compatible Chat Completions API
- 无第三方 Python 包依赖，使用标准库实现

## 快速开始

进入项目目录：

```powershell
cd .\mini_agent
```

配置真实 LLM API。当前代码默认使用 DeepSeek compatible endpoint：

```powershell
$env:DEEPSEEK_API_KEY="你的 API Key"
python .\main.py --session window1
```

启动后输入问题：

```text
session=window1. Type /exit to quit.
user> 帮我算一下 2 * (3 + 4)
agent> 结果是 14。
```

退出：

```text
/exit
```

## 使用其他 OpenAI-compatible 服务

`agent/llm.py` 的 `OpenAICompatibleLLM` 封装调用的是 `/chat/completions` 接口。当前默认参数是：

```text
base_url = https://api.deepseek.com
model    = deepseek-v4-pro
api_key  = DEEPSEEK_API_KEY
```

如果要切换到其他服务，可以在初始化 `OpenAICompatibleLLM` 时显式传入：

```python
runtime = AgentRuntime(
    llm=OpenAICompatibleLLM(
        api_key="你的 API Key",
        model="模型名",
        base_url="https://your-provider.example/v1",
    )
)
```

## 运行测试

```powershell
cd .\mini_agent
python -m unittest discover -s tests
```

测试覆盖：

- calculator 工具调用链路
- todo 多 session 隔离
- 工具异常处理
- 最大 loop 限制
- LLM 输出解析
- session 消息压缩
- context 偏好注入

## Agent Loop 设计

`AgentRuntime.run(session_id, user_input)` 是主入口：

1. 根据 `session_id` 获取独立 session。
2. 将用户输入写入 session messages。
3. 从用户输入中识别偏好，例如语言和回复风格。
4. 构建 LLM messages：
   - system prompt
   - tools schema
   - user preferences
   - session summary
   - recent messages
5. 调用 LLM。
6. 使用 `OutputParser` 解析 LLM 返回的 JSON。
7. 如果是 `final`，写入 assistant message 并返回答案。
8. 如果是 `tool_call`，从 `Tools` 注册表查找工具并执行。
9. 将工具结果或错误写入 trace，并作为消息放回 session。
10. 继续 loop，直到得到最终答案或达到最大轮次。

## LLM 输出协议

LLM 必须返回 JSON，不返回 Markdown。

工具调用格式：

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

最终回复格式：

```json
{
  "type": "final",
  "thought": "工具结果已足够回答",
  "answer": "结果是 14。"
}
```

解析器支持从带有前后缀的文本中提取第一个 JSON 对象，以降低模型偶发格式漂移带来的失败率。

## 工具系统

所有工具通过 `@tool(...)` 装饰器注册到全局 `Tools` 注册表。工具需要提供：

- `name`：工具名
- `description`：能力描述，供 LLM 选择工具
- `parameters`：JSON Schema 参数说明
- `func`：实际执行逻辑

默认工具：

| 工具 | 作用 | 说明 |
| --- | --- | --- |
| `calculator` | 数学计算 | 使用 AST 限制表达式类型，避免执行任意代码 |
| `search` | 搜索 | mock 数据，用于演示工具调用 |
| `todo` | 待办管理 | 待办列表保存在当前 session 的 `state` 中 |
| `weather` | 天气查询 | mock 天气数据，用于演示查询类工具 |

## Session 与 Memory 策略

`SessionStore` 用 `session_id` 隔离状态。例如：

```powershell
python .\main.py --session window1
python .\main.py --session window2
```

`window1` 和 `window2` 分别拥有：

- `messages`：最近用户消息、助手回复和工具结果
- `summary`：被压缩的旧消息
- `state`：工具维护的结构化状态，例如 todo 列表
- `trace`：工具调用记录
- `context.preferences`：用户偏好

`ContextManager` 只负责用户偏好类信息，不负责保存完整对话。当前支持从用户输入中识别：

- “以后用中文回答”“中文回复” -> `language: 中文`
- “用英文回答”“English” -> `language: English`
- “简洁”“简短”“短一点” -> `reply_style: 简洁`
- “详细”“展开讲”“多解释” -> `reply_style: 详细`

这些偏好会进入后续 system context，例如：

```text
User preferences: language: 中文; reply_style: 简洁
```

完整 trace 不直接塞入 LLM context。trace 用于调试和审计；工具结果摘要作为普通消息进入最近上下文，支持后续追问和继续调用工具。

## Context 压缩策略

`SessionStore.max_messages` 默认值为 12。超过上限后：

1. 将更早消息拼接到 `summary`。
2. 保留最近消息。
3. 后续构建 context 时同时放入 `summary` 和最近消息。


## 异常处理

- LLM 请求失败：记录 debug log 后抛出异常。
- LLM 输出不是合法 JSON：返回格式错误说明。
- 工具不存在：记录 trace error，并把错误结果交给 LLM 继续处理。
- 工具参数缺失或执行失败：记录 trace error。
- 超过最大 loop：返回轮次限制提示。

## 设计取舍

- **不引入 Agent 框架**：主循环、工具分发、session 和 context 都在本项目中实现，便于展示核心机制。
- **测试不调用真实 LLM**：单元测试使用 `FakeLLM`，保证测试稳定、可重复。
- **搜索和天气使用 mock**：重点是验证工具 schema、调用、结果回填和 trace，而不是外部 API 集成。
- **压缩策略保持简单**：当前只做基于消息数量的基础压缩，适合最小可用版本。

## 相关文档

- [PROMPTS.md](./PROMPTS.md)：AI Prompt、工具选择策略、问题解决记录
- [tests/test_runtime.py](./tests/test_runtime.py)：核心行为测试用例
