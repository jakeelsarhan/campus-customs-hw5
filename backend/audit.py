"""Append-only agent-loop audit trail. Never wipe on startup."""

from __future__ import annotations

import fcntl
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger("campus_customs.audit")

HW5 = Path(__file__).resolve().parents[1]
AUDIT_PATH = HW5 / "output" / "audit_trail.json"


def _clip(value: Any, limit: int = 400) -> Any:
    if isinstance(value, str):
        cleaned = " ".join(value.split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1] + "…"
    if isinstance(value, dict):
        return {str(k): _clip(v, limit=limit) for k, v in list(value.items())[:40]}
    if isinstance(value, list):
        return [_clip(v, limit=limit) for v in value[:40]]
    return value


def append_event(
    *,
    run_id: str,
    agent: str,
    step: str,
    detail: dict[str, Any] | str | None = None,
    path: Path | None = None,
) -> None:
    """Append one agent-loop step. Existing rows stay."""
    target = path or AUDIT_PATH
    event = {
        "time": datetime.now().astimezone().isoformat(timespec="seconds"),
        "run_id": run_id,
        "agent": agent,
        "step": step,
        "detail": _clip(detail if detail is not None else {}),
    }
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a+", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        handle.seek(0)
        raw = handle.read()
        try:
            data = json.loads(raw) if raw.strip() else []
        except json.JSONDecodeError:
            logger.error("audit trail is not valid JSON; left %s untouched", target)
            return
        if not isinstance(data, list):
            logger.error("audit trail is not a list; left %s untouched", target)
            return
        data.append(event)
        handle.seek(0)
        handle.truncate()
        json.dump(data, handle, indent=2)
        handle.write("\n")
        handle.flush()


def ensure_audit_file() -> None:
    """Create an empty list file if missing — never clears an existing trail."""
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not AUDIT_PATH.is_file():
        AUDIT_PATH.write_text("[]\n", encoding="utf-8")
