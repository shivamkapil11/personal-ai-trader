from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

from app.config import settings
from app.services.app_state import app_state_store


def _configured_path(path: Path | None) -> str:
    if path is None:
        return ""
    return str(path).strip()


def _dir_ready(path: Path | None) -> bool:
    normalized = _configured_path(path)
    if normalized in {"", ".", "./"}:
        return False
    return bool(path and path.exists() and path.is_dir())


def _file_ready(path: Path | None) -> bool:
    normalized = _configured_path(path)
    if normalized in {"", ".", "./"}:
        return False
    return bool(path and path.exists() and path.is_file())


def infrastructure_status() -> Dict[str, Any]:
    storage = app_state_store.storage_status()
    return {
        "postgres": {
            "enabled": settings.postgres_enabled,
            "dsn_configured": bool(settings.postgres_dsn),
            "migrations_path": str(settings.postgres_migrations_path),
            "migrations_ready": _dir_ready(settings.postgres_migrations_path),
            "mode": storage.get("mode", "local-json-fallback"),
            "ready": storage.get("ready", False),
            "message": storage.get("message", ""),
        },
        "firestore": {
            "enabled": settings.feedback_firestore_enabled,
            "project_id": settings.feedback_firestore_project_id or settings.firebase_project_id or "",
            "credentials_ready": _file_ready(settings.feedback_firestore_credentials_path)
            or _file_ready(settings.firebase_admin_credentials_path),
            "collection": settings.feedback_firestore_collection,
        },
    }
