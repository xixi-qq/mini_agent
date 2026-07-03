import json
import unittest

from agent.memory import ContextManager
from agent.parser import OutputParser
from agent.runtime import AgentRuntime
from agent.session import SessionStore


class FakeLLM:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        if not self.outputs:
            raise AssertionError("No fake LLM output left")
        return self.outputs.pop(0)


def as_json(payload):
    return json.dumps(payload, ensure_ascii=False)


class RuntimeTests(unittest.TestCase):
    def test_calculator_tool_loop(self):
        llm = FakeLLM(
            [
                as_json(
                    {
                        "type": "tool_call",
                        "thought": "need calculation",
                        "tool_name": "calculator",
                        "arguments": {"expression": "2 * (3 + 4)"},
                    }
                ),
                as_json({"type": "final", "thought": "has result", "answer": "结果是 14。"}),
            ]
        )
        runtime = AgentRuntime(llm=llm)

        answer = runtime.run("s1", "2 * (3 + 4) 等于多少")

        self.assertEqual(answer, "结果是 14。")
        trace = runtime.sessions.get("s1")["trace"]
        self.assertEqual(trace[0]["tool"], "calculator")
        self.assertEqual(trace[0]["result"]["result"], 14)

    def test_todo_is_isolated_by_session(self):
        llm = FakeLLM(
            [
                as_json(
                    {
                        "type": "tool_call",
                        "thought": "add todo",
                        "tool_name": "todo",
                        "arguments": {"action": "add", "item": "查天气"},
                    }
                ),
                as_json({"type": "final", "thought": "done", "answer": "窗口1已记录。"}),
                as_json(
                    {
                        "type": "tool_call",
                        "thought": "add todo",
                        "tool_name": "todo",
                        "arguments": {"action": "add", "item": "写周报"},
                    }
                ),
                as_json({"type": "final", "thought": "done", "answer": "窗口2已记录。"}),
            ]
        )
        sessions = SessionStore()
        runtime = AgentRuntime(llm=llm, sessions=sessions)

        runtime.run("window1", "帮我记待办：查天气")
        runtime.run("window2", "帮我记待办：写周报")

        self.assertEqual(sessions.get("window1")["state"]["todos"], ["查天气"])
        self.assertEqual(sessions.get("window2")["state"]["todos"], ["写周报"])

    def test_tool_error_is_returned_to_llm_then_final(self):
        llm = FakeLLM(
            [
                as_json(
                    {
                        "type": "tool_call",
                        "thought": "bad expression",
                        "tool_name": "calculator",
                        "arguments": {"expression": "__import__('os').system('echo bad')"},
                    }
                ),
                as_json({"type": "final", "thought": "explain error", "answer": "计算表达式不合法。"}),
            ]
        )
        runtime = AgentRuntime(llm=llm)

        answer = runtime.run("s1", "算一下危险表达式")

        self.assertEqual(answer, "计算表达式不合法。")
        self.assertIn("error", runtime.sessions.get("s1")["trace"][0])

    def test_max_steps_limit(self):
        llm = FakeLLM(
            [
                as_json(
                    {
                        "type": "tool_call",
                        "thought": "loop",
                        "tool_name": "search",
                        "arguments": {"query": "agent"},
                    }
                ),
                as_json(
                    {
                        "type": "tool_call",
                        "thought": "loop again",
                        "tool_name": "search",
                        "arguments": {"query": "agent"},
                    }
                ),
            ]
        )
        runtime = AgentRuntime(llm=llm, max_steps=2)

        answer = runtime.run("s1", "一直搜索")

        self.assertIn("最大工具调用轮次", answer)

    def test_parser_extracts_json_from_text(self):
        decision = OutputParser().parse(
            'prefix {"type":"final","thought":"ready","answer":"ok"} suffix'
        )

        self.assertEqual(decision.type, "final")
        self.assertEqual(decision.answer, "ok")

    def test_session_compression_keeps_recent_messages(self):
        sessions = SessionStore(max_messages=3)
        session = sessions.get("s1")

        for idx in range(5):
            sessions.append_message(session, "user", f"message-{idx}")

        self.assertIn("message-0", session["summary"])
        self.assertEqual(len(session["messages"]), 3)
        self.assertEqual(session["messages"][0]["content"], "message-2")

    def test_context_manager_only_builds_preference_context(self):
        context = ContextManager()
        session = SessionStore().get("s1")

        context.set_preference(session, "language", "中文")
        messages = context.build_context(session)

        self.assertEqual(messages[0]["role"], "system")
        self.assertIn("language: 中文", messages[0]["content"])

    def test_runtime_updates_preferences_from_user_message(self):
        llm = FakeLLM(
            [
                as_json(
                    {
                        "type": "final",
                        "thought": "preference saved",
                        "answer": "好的，之后会用中文并保持简洁。",
                    }
                )
            ]
        )
        runtime = AgentRuntime(llm=llm)

        runtime.run("s1", "以后用中文回答，回复简洁一点")

        preferences = runtime.sessions.get("s1")["context"]["preferences"]
        self.assertEqual(preferences["language"], "中文")
        self.assertEqual(preferences["reply_style"], "简洁")
        system_messages = [msg["content"] for msg in llm.calls[0] if msg["role"] == "system"]
        self.assertTrue(any("language: 中文" in msg for msg in system_messages))
        self.assertTrue(any("reply_style: 简洁" in msg for msg in system_messages))


if __name__ == "__main__":
    unittest.main()
