from __future__ import annotations

from typing import Any


class SessionStore:
    def __init__(self, max_messages: int = 12) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}
        self.max_messages = max_messages

    def get(self, session_id: str) -> dict[str, Any]:
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "id": session_id,
                "messages": [],
                "summary": "",
                "context": {"preferences": {}},
                "state": {},
                "trace": [],
            }
        return self._sessions[session_id]

    def append_message(self, session: dict[str, Any], role: str, content: str) -> None:
        session.setdefault("messages", []).append({"role": role, "content": content})
        self.compress_messages(session)

    def compress_messages(self, session: dict[str, Any]) -> None:
        messages = session.setdefault("messages", [])
        if len(messages) <= self.max_messages:
            return
        overflow_count = len(messages) - self.max_messages
        old_messages = messages[:overflow_count]
        old_summary = session.get("summary", "")
        fragment = " ".join(f"{msg['role']}: {msg['content']}" for msg in old_messages)
        session["summary"] = (old_summary + " " + fragment).strip()
        session["messages"] = messages[overflow_count:]

    def build_message_context(self, session: dict[str, Any]) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        summary = session.get("summary")
        if summary:
            messages.append({"role": "system", "content": f"Session summary: {summary}"})
        messages.extend(session.get("messages", []))
        return messages

    def all(self) -> dict[str, dict[str, Any]]:
        return self._sessions
