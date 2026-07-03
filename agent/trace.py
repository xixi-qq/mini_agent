from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def record_trace(
    session: dict[str, Any],
    tool_name: str,
    arguments: dict[str, Any],
    result: Any = None,
    error: str | None = None,
) -> None:
    session.setdefault("trace", []).append(
        {
            "ts": datetime.now(timezone.utc).isoformat(),
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
            "error": error,
        }
    )
