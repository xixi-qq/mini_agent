from __future__ import annotations

from typing import Any


class ContextManager:
    def set_preference(self, session: dict[str, Any], key: str, value: str) -> None:
        preferences = session.setdefault("context", {}).setdefault("preferences", {})
        preferences[key] = value

    def update_preferences_from_text(self, session: dict[str, Any], text: str) -> None:
        lowered = text.lower()

        if "以后用中文" in text or "用中文回答" in text or "中文回复" in text:
            self.set_preference(session, "language", "中文")
        elif "以后用英文" in text or "用英文回答" in text or "english" in lowered:
            self.set_preference(session, "language", "English")

        if "简洁" in text or "简短" in text or "短一点" in text or "concise" in lowered:
            self.set_preference(session, "reply_style", "简洁")
        elif "详细" in text or "展开讲" in text or "多解释" in text or "detailed" in lowered:
            self.set_preference(session, "reply_style", "详细")

    def build_context(self, session: dict[str, Any]) -> list[dict[str, str]]:
        preferences = session.setdefault("context", {}).setdefault("preferences", {})
        if not preferences:
            return []
        preference_text = "; ".join(f"{key}: {value}" for key, value in preferences.items())
        return [{"role": "system", "content": f"User preferences: {preference_text}"}]
