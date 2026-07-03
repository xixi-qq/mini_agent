from __future__ import annotations

from typing import Any

from .base import tool


@tool(
    "todo",
    "Manage todo items inside the current session. Actions: add, list, clear.",
    parameters={
        "type": "object",
        "properties": {
            "action": {"type": "string", "enum": ["add", "list", "clear"]},
            "item": {"type": "string", "description": "Todo text, required for add"},
        },
        "required": ["action"],
    },
)
def todo(action: str, session_state: dict[str, Any], item: str = "") -> dict[str, Any]:
    todos = session_state.setdefault("todos", [])
    action = str(action).strip()
    if action == "add":
        item = str(item).strip()
        if not item:
            raise ValueError("item is required when action is add")
        todos.append(item)
        return {"action": action, "todos": todos, "added": item}
    if action == "list":
        return {"action": action, "todos": todos}
    if action == "clear":
        todos.clear()
        return {"action": action, "todos": todos}
    raise ValueError(f"Unsupported todo action: {action}")
