from __future__ import annotations

import json
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Deque, Dict, List

from app.config import settings


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ActivityLog:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()

    def _ensure(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text("", encoding="utf-8")

    def write(
        self,
        category: str,
        action: str,
        *,
        status: str = "info",
        message: str = "",
        user_id: str | None = None,
        route: str | None = None,
        symbol: str | None = None,
        duration_ms: int | None = None,
        details: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        event = {
            "timestamp": _utc_now(),
            "category": category,
            "action": action,
            "status": status,
            "message": message,
            "user_id": user_id,
            "route": route,
            "symbol": symbol,
            "duration_ms": duration_ms,
            "details": details or {},
        }
        self._ensure()
        with self._lock:
            with self.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, ensure_ascii=True) + "\n")
        return event

    def recent(self, limit: int = 60) -> List[Dict[str, Any]]:
        self._ensure()
        rows: Deque[Dict[str, Any]] = deque(maxlen=limit)
        with self._lock:
            for line in self.path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return list(rows)[::-1]


activity_log = ActivityLog(settings.activity_log_path)
