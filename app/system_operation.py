"""Process-wide lock for disruptive console maintenance operations."""

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock


_lock = Lock()
_operation: dict | None = None


def begin_operation(kind: str, title: str, message: str, phase: str) -> dict | None:
    global _operation
    with _lock:
        if _operation is not None:
            return None
        _operation = {
            "active": True,
            "kind": kind,
            "title": title,
            "message": message,
            "phase": phase,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        return deepcopy(_operation)


def update_operation(*, title: str | None = None, message: str | None = None, phase: str | None = None) -> None:
    with _lock:
        if _operation is None:
            return
        if title is not None:
            _operation["title"] = title
        if message is not None:
            _operation["message"] = message
        if phase is not None:
            _operation["phase"] = phase


def current_operation() -> dict | None:
    with _lock:
        return deepcopy(_operation)


def clear_operation() -> None:
    global _operation
    with _lock:
        _operation = None
