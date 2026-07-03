from __future__ import annotations

import inspect
from typing import Any, Callable


class Tool:
    def __init__(self, name: str, description: str, parameters: dict[str, Any], func: Callable[[dict[str, Any], dict[str, Any]], Any]):
        self.name:  str = name
        self.description:  str = description
        self.parameters: dict[str, Any] = parameters
        self.func: Callable[[dict[str, Any], dict[str, Any]], Any] = func

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def run(self, arguments: dict[str, Any], session_state: dict[str, Any]) -> Any:
        signature = inspect.signature(self.func)
        kwargs = {}

        for param_name, param in signature.parameters.items():
            if param_name == "session_state":
                kwargs[param_name] = session_state
                continue

            if param_name in arguments:
                kwargs[param_name] = arguments[param_name]
                continue

            if param.default is inspect.Parameter.empty:
                raise ValueError(f"Missing required argument: {param_name}")

        return self.func(**kwargs)


def tool(name: str, description: str, parameters: dict[str, Any]):
    def decorator(func: Callable[[dict[str, Any], dict[str, Any]], Any]) -> Tool:
        _tool = Tool(name = name,
        description = description,
        parameters = parameters,
        func = func)

        return tools.register(_tool)

    return decorator


class Tools:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool_obj: Tool) -> Tool:
        if tool_obj.name in self._tools:
            raise ValueError(f"Tool already registered: {tool_obj.name}")
        self._tools[tool_obj.name] = tool_obj
        return tool_obj

    def get(self, name: str) -> Tool:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        return self._tools[name]

    def schemas(self) -> list[dict[str, Any]]:
        return [tool.schema() for tool in self._tools.values()]

    def names(self) -> list[str]:
        return list(self._tools.keys())

    def all(self) -> dict[str, Tool]:
        return dict(self._tools)


tools = Tools()


