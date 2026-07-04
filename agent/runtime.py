from __future__ import annotations

import json
from typing import Any

from .debug_log import log_llm_error, log_llm_raw, log_parse_error
from .llm import LLMClient
from .memory import ContextManager
from .parser import OutputParser
from .session import SessionStore
from .trace import record_trace
from .tools import tools, Tools

SYSTEM_PROMPT = """你是一个有用的小助手。
你需要判断能否直接回答用户，还是调用一个工具。
- 每次回答只能返回 JSON！

允许的格式：
{"type":"tool_call","thought":"说明为什么需要工具","tool_name":"calculator","arguments":{"expression":"2+2"}}
{"type":"final","thought":"说明为什么已经可以回答","answer":"给用户的最终答案"}

当用户要求计算、搜索、查询天气或管理待办事项时，使用工具。
收到工具结果后继续判断，直到可以给出最终答案。"""


class AgentRuntime:
    def __init__(
        self,
        llm: LLMClient,
        sessions: SessionStore | None = None,
        tools: Tools | None = tools,
        max_steps: int = 5,
        context: ContextManager | None = None,
    ) -> None:
        self.llm = llm
        self.sessions = sessions or SessionStore()
        self.tools = tools
        self.max_steps = max_steps
        self.context = context or ContextManager()
        self.parser = OutputParser()

    def run(self, session_id: str, user_input: str) -> str:
        session = self.sessions.get(session_id)
        self.sessions.append_message(session, "user", user_input)
        self.context.update_preferences_from_text(session, user_input)

        for _ in range(self.max_steps):
            try:
                raw = self.llm.invoke(self._build_messages(session))
                log_llm_raw(session_id, user_input, raw)
            except Exception as exc:
                log_llm_error(session_id, user_input, exc)
                raise
            try:
                decision = self.parser.parse(raw)
            except Exception as exc:
                log_parse_error(session_id, user_input, raw, exc)
                answer = f"模型输出格式错误，无法继续执行：{exc}"
                self.sessions.append_message(session, "assistant", answer)
                return answer

            if decision.type == "final":
                answer = decision.answer or ""
                self.sessions.append_message(session, "assistant", answer)
                return answer

            tool_name = decision.tool_name or ""
            arguments = decision.arguments or {}
            try:
                tool = self.tools.get(tool_name)
                result = tool.run(arguments, session["state"])
                record_trace(session, tool_name, arguments, result=result)
                tool_message = {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "result": result,
                }
            except Exception as exc:
                record_trace(session, tool_name, arguments, error=str(exc))
                tool_message = {
                    "tool_name": tool_name,
                    "arguments": arguments,
                    "error": str(exc),
                }
            self.sessions.append_message(
                session,
                "user",
                f"Tool result: {json.dumps(tool_message, ensure_ascii=False)}",
            )

        answer = "已达到最大工具调用轮次，请缩小问题范围后重试。"
        self.sessions.append_message(session, "assistant", answer)
        return answer

    def _build_messages(self, session: dict[str, Any]) -> list[dict[str, str]]:
        tool_schemas = json.dumps(self.tools.schemas(), ensure_ascii=False)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": f"Available tools: {tool_schemas}"},
        ]
        messages.extend(self.context.build_context(session))
        messages.extend(self.sessions.build_message_context(session))
        return messages
