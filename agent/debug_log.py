from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
LLM_RAW_LOG = PROJECT_ROOT / "llm_raw.log"


def _logger() -> logging.Logger:
    logger = logging.getLogger("mini_agent.llm_raw")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    if not logger.handlers:
        handler = logging.FileHandler(LLM_RAW_LOG, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        logger.addHandler(handler)
    return logger


def _write(level: str, payload: dict[str, Any], exc_info: bool = False) -> None:
    try:
        message = json.dumps(payload, ensure_ascii=False)
        logger = _logger()
        if level == "error":
            logger.error(message, exc_info=exc_info)
        else:
            logger.info(message)
    except Exception:
        pass


def log_llm_raw(session_id: str, user_input: str, raw: str) -> None:
    payload = {
        "event": "llm_raw_output",
        "session_id": session_id,
        "user_input": user_input,
        "raw": raw,
    }
    _write("info", payload)


def log_parse_error(session_id: str, user_input: str, raw: str, error: Exception) -> None:
    payload: dict[str, Any] = {
        "event": "llm_parse_error",
        "session_id": session_id,
        "user_input": user_input,
        "raw": raw,
        "error": str(error),
    }
    _write("error", payload)


def log_llm_error(session_id: str, user_input: str, error: Exception) -> None:
    payload = {
        "event": "llm_request_error",
        "session_id": session_id,
        "user_input": user_input,
        "error": str(error),
    }
    _write("error", payload, exc_info=True)
