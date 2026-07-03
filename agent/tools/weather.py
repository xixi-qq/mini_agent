from __future__ import annotations

from typing import Any
from .base import tool

@tool("weather", "Mock weather lookup for a city.", parameters = {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "City name"},
            "date": {"type": "string", "description": "Date or relative day, optional"},
        },
        "required": ["city"],
    }
)
def weather(city: str, date: str = "today") -> dict[str, Any]:
    """Lookup weather for a city.

    Args:
        city (str): City name
        date (str, optional): Date or relative day, optional. Defaults to "today".

    Returns:
        dict[str, Any]: Weather information
    """
    return {
        "city": city,
        "date": date,
        "forecast": "cloudy",
        "temperature_c": 26,
        "note": "mock weather data",
    }