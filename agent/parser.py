from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Literal


@dataclass
class AgentDecision:
    type: Literal["tool_call", "final"]
    thought: str
    tool_name: str | None = None
    arguments: dict[str, Any] | None = None
    answer: str | None = None


class OutputParser:
    def parse(self, raw: str) -> AgentDecision:
        payload = self._load_json(raw)
        decision_type = payload.get("type")
        if decision_type == "tool_call":
            tool_name = payload.get("tool_name")
            arguments = payload.get("arguments", {})
            if not isinstance(tool_name, str) or not tool_name:
                raise ValueError("tool_call requires tool_name")
            if not isinstance(arguments, dict):
                raise ValueError("tool_call arguments must be an object")
            return AgentDecision(
                type="tool_call",
                thought=str(payload.get("thought", "")),
                tool_name=tool_name,
                arguments=arguments,
            )
        if decision_type == "final":
            return AgentDecision(
                type="final",
                thought=str(payload.get("thought", "")),
                answer=str(payload.get("answer", "")),
            )
        raise ValueError("LLM output type must be tool_call or final")

    def _load_json(self, raw: str) -> dict[str, Any]:
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if not match:
                raise ValueError("LLM output is not valid JSON")
            payload = json.loads(match.group(0))
        if not isinstance(payload, dict):
            raise ValueError("LLM output JSON must be an object")
        return payload
