from __future__ import annotations

import ast
import operator
from typing import Any

from .base import tool


_BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


@tool(
    "calculator",
    "Evaluate a basic arithmetic expression. Supports +, -, *, /, %, ** and parentheses.",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "Arithmetic expression, for example: 2 * (3 + 4)",
            }
        },
        "required": ["expression"],
    },
)
def calculator(expression: str) -> dict[str, Any]:
    expression = str(expression).strip()
    if not expression:
        raise ValueError("expression is required")
    node = ast.parse(expression, mode="eval")
    result = _eval(node.body)
    return {"expression": expression, "result": result}


def _eval(node: ast.AST) -> float | int:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPS:
        return _BINARY_OPS[type(node.op)](_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPS:
        return _UNARY_OPS[type(node.op)](_eval(node.operand))
    raise ValueError("Only arithmetic expressions are allowed")
