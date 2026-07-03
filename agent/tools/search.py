from __future__ import annotations

from typing import Any

from .base import tool


@tool(
    "search",
    "Mock search engine. Returns deterministic snippets for a query.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "limit": {"type": "integer", "description": "Maximum result count", "default": 3},
        },
        "required": ["query"],
    },
)
def search(query: str, limit: int = 3) -> dict[str, Any]:
    query = str(query).strip()
    if not query:
        raise ValueError("query is required")
    limit = int(limit)
    results = [
        {"title": f"Mock result {idx + 1}", "snippet": f"Information about {query} #{idx + 1}"}
        for idx in range(max(1, min(limit, 5)))
    ]
    return {"query": query, "results": results}
