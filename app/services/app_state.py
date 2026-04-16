from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, List

from app.config import settings

try:
    import psycopg
    from psycopg.rows import dict_row
    from psycopg.types.json import Jsonb
except Exception:  # pragma: no cover - optional dependency guard
    psycopg = None
    dict_row = None
    Jsonb = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class AppStateStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = Lock()
        self._postgres_schema_ready = False

    def _default_state(self) -> Dict[str, Any]:
        return {
            "users": {},
            "preferences": {},
            "search_history": {},
            "watchlists": {},
            "feedback_local": [],
            "kite_connections": {},
            "portfolio_snapshots": {},
        }

    def _ensure(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps(self._default_state(), indent=2), encoding="utf-8")

    def _read(self) -> Dict[str, Any]:
        self._ensure()
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            raw = self._default_state()
        state = self._default_state()
        state.update(raw)
        return state

    def _write(self, state: Dict[str, Any]) -> None:
        self._ensure()
        self.path.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _postgres_enabled(self) -> bool:
        return bool(settings.postgres_enabled and settings.postgres_dsn and psycopg is not None)

    def _connect(self) -> "psycopg.Connection[Any]":
        if not self._postgres_enabled():
            raise RuntimeError("PostgreSQL is not configured.")
        return psycopg.connect(settings.postgres_dsn, row_factory=dict_row, autocommit=True)

    def _ensure_postgres_schema(self) -> None:
        if not self._postgres_enabled() or self._postgres_schema_ready:
            return
        with self._lock:
            if self._postgres_schema_ready:
                return
            migration_files = sorted(settings.postgres_migrations_path.glob("*.sql"))
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    for migration_path in migration_files:
                        sql = migration_path.read_text(encoding="utf-8").strip()
                        if sql:
                            cursor.execute(sql)
            self._postgres_schema_ready = True

    def _serialize_json(self, value: Any) -> Any:
        if Jsonb is None:
            return value
        return Jsonb(value)

    def _map_user_row(self, row: Dict[str, Any] | None) -> Dict[str, Any] | None:
        if not row:
            return None
        return {
            "uid": row["uid"],
            "name": row.get("name", ""),
            "email": row.get("email", ""),
            "image": row.get("image", ""),
            "provider": row.get("provider", "google"),
            "createdAt": row.get("created_at").isoformat() if row.get("created_at") else utc_now(),
            "lastLoginAt": row.get("last_login_at").isoformat() if row.get("last_login_at") else utc_now(),
            "kiteConnected": bool(row.get("kite_connected")),
            "isKiteUser": row.get("is_kite_user"),
            "onboardingStep": row.get("onboarding_step", "auth"),
        }

    def get_user(self, uid: str) -> Dict[str, Any] | None:
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            u.uid,
                            u.name,
                            u.email,
                            u.image,
                            u.provider,
                            u.kite_connected,
                            u.is_kite_user,
                            u.onboarding_step,
                            u.created_at,
                            u.last_login_at
                        FROM users u
                        WHERE u.uid = %s
                        """,
                        (uid,),
                    )
                    row = cursor.fetchone()
            return self._map_user_row(row)

        with self._lock:
            state = self._read()
            user = state["users"].get(uid)
            return deepcopy(user) if user else None

    def upsert_user(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            existing = self.get_user(profile["uid"]) or {}
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO users (
                            uid,
                            name,
                            email,
                            image,
                            provider,
                            kite_connected,
                            is_kite_user,
                            onboarding_step,
                            created_at,
                            last_login_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
                        ON CONFLICT (uid) DO UPDATE SET
                            name = EXCLUDED.name,
                            email = EXCLUDED.email,
                            image = EXCLUDED.image,
                            provider = EXCLUDED.provider,
                            kite_connected = EXCLUDED.kite_connected,
                            is_kite_user = EXCLUDED.is_kite_user,
                            onboarding_step = EXCLUDED.onboarding_step,
                            last_login_at = NOW()
                        """,
                        (
                            profile["uid"],
                            profile.get("name", existing.get("name", "")),
                            profile.get("email", existing.get("email", "")),
                            profile.get("image", existing.get("image", "")),
                            profile.get("provider", existing.get("provider", "google")),
                            profile.get("kiteConnected", existing.get("kiteConnected", False)),
                            profile.get("isKiteUser", existing.get("isKiteUser")),
                            profile.get("onboardingStep", existing.get("onboardingStep", "auth")),
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO user_preferences (uid, theme, compare_mode)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (uid) DO NOTHING
                        """,
                        (profile["uid"], "gains-dark", True),
                    )
            return self.get_user(profile["uid"]) or {}

        with self._lock:
            state = self._read()
            existing = state["users"].get(profile["uid"], {})
            merged = {
                "uid": profile["uid"],
                "name": profile.get("name", existing.get("name", "")),
                "email": profile.get("email", existing.get("email", "")),
                "image": profile.get("image", existing.get("image", "")),
                "provider": profile.get("provider", existing.get("provider", "google")),
                "createdAt": existing.get("createdAt", utc_now()),
                "lastLoginAt": utc_now(),
                "kiteConnected": profile.get("kiteConnected", existing.get("kiteConnected", False)),
                "isKiteUser": profile.get("isKiteUser", existing.get("isKiteUser")),
                "onboardingStep": profile.get("onboardingStep", existing.get("onboardingStep", "auth")),
            }
            state["users"][profile["uid"]] = merged
            state["preferences"].setdefault(profile["uid"], {"theme": "gains-dark", "compareMode": True})
            state["search_history"].setdefault(profile["uid"], [])
            state["watchlists"].setdefault(profile["uid"], [])
            state["kite_connections"].setdefault(profile["uid"], {})
            state["portfolio_snapshots"].setdefault(profile["uid"], [])
            self._write(state)
            return deepcopy(merged)

    def update_user_fields(self, uid: str, **fields: Any) -> Dict[str, Any] | None:
        if self._postgres_enabled():
            allowed = {
                "name": "name",
                "email": "email",
                "image": "image",
                "provider": "provider",
                "kiteConnected": "kite_connected",
                "isKiteUser": "is_kite_user",
                "onboardingStep": "onboarding_step",
            }
            updates = []
            values: List[Any] = []
            for key, column in allowed.items():
                if key in fields:
                    updates.append(f"{column} = %s")
                    values.append(fields[key])
            if not updates:
                return self.get_user(uid)
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"UPDATE users SET {', '.join(updates)} WHERE uid = %s",
                        (*values, uid),
                    )
            return self.get_user(uid)

        with self._lock:
            state = self._read()
            user = state["users"].get(uid)
            if not user:
                return None
            user.update(fields)
            state["users"][uid] = user
            self._write(state)
            return deepcopy(user)

    def get_preferences(self, uid: str) -> Dict[str, Any]:
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT theme, compare_mode FROM user_preferences WHERE uid = %s", (uid,))
                    row = cursor.fetchone()
            return {
                "theme": row.get("theme", "gains-dark") if row else "gains-dark",
                "compareMode": bool(row.get("compare_mode", True)) if row else True,
            }

        with self._lock:
            state = self._read()
            return deepcopy(state["preferences"].get(uid, {"theme": "gains-dark", "compareMode": True}))

    def record_search(self, uid: str, entry: Dict[str, Any]) -> List[Dict[str, Any]]:
        payload = {
            "query": entry.get("query", ""),
            "thoughts": entry.get("thoughts", ""),
            "mode": entry.get("mode", "single"),
            "symbols": entry.get("symbols", []),
            "timestamp": entry.get("timestamp", utc_now()),
        }
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO search_history (uid, query, thoughts, mode, symbols, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            uid,
                            payload["query"],
                            payload["thoughts"],
                            payload["mode"],
                            self._serialize_json(payload["symbols"]),
                            payload["timestamp"],
                        ),
                    )
            return self.get_search_history(uid)

        with self._lock:
            state = self._read()
            history = state["search_history"].setdefault(uid, [])
            history.insert(0, payload)
            state["search_history"][uid] = history[:12]
            self._write(state)
            return deepcopy(state["search_history"][uid])

    def get_search_history(self, uid: str) -> List[Dict[str, Any]]:
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT query, thoughts, mode, symbols, created_at
                        FROM search_history
                        WHERE uid = %s
                        ORDER BY created_at DESC
                        LIMIT 12
                        """,
                        (uid,),
                    )
                    rows = cursor.fetchall()
            return [
                {
                    "query": row["query"],
                    "thoughts": row.get("thoughts", ""),
                    "mode": row.get("mode", "single"),
                    "symbols": row.get("symbols", []),
                    "timestamp": row["created_at"].isoformat() if row.get("created_at") else utc_now(),
                }
                for row in rows
            ]

        with self._lock:
            state = self._read()
            return deepcopy(state["search_history"].get(uid, []))

    def add_watchlist_item(self, uid: str, symbol: str, note: str = "") -> List[Dict[str, Any]]:
        normalized = symbol.strip().upper()
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO watchlist_items (uid, symbol, note, created_at, updated_at)
                        VALUES (%s, %s, %s, NOW(), NOW())
                        ON CONFLICT (uid, symbol) DO UPDATE SET
                            note = EXCLUDED.note,
                            updated_at = NOW()
                        """,
                        (uid, normalized, note),
                    )
            return self.get_watchlist(uid)

        with self._lock:
            state = self._read()
            watchlist = state["watchlists"].setdefault(uid, [])
            existing = next((item for item in watchlist if item["symbol"] == normalized), None)
            if existing:
                existing["note"] = note or existing.get("note", "")
                existing["updatedAt"] = utc_now()
            else:
                watchlist.insert(
                    0,
                    {
                        "symbol": normalized,
                        "note": note,
                        "createdAt": utc_now(),
                        "updatedAt": utc_now(),
                    },
                )
            state["watchlists"][uid] = watchlist[:30]
            self._write(state)
            return deepcopy(state["watchlists"][uid])

    def get_watchlist(self, uid: str) -> List[Dict[str, Any]]:
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT symbol, note, created_at, updated_at
                        FROM watchlist_items
                        WHERE uid = %s
                        ORDER BY updated_at DESC
                        LIMIT 30
                        """,
                        (uid,),
                    )
                    rows = cursor.fetchall()
            return [
                {
                    "symbol": row["symbol"],
                    "note": row.get("note", ""),
                    "createdAt": row["created_at"].isoformat() if row.get("created_at") else utc_now(),
                    "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else utc_now(),
                }
                for row in rows
            ]

        with self._lock:
            state = self._read()
            return deepcopy(state["watchlists"].get(uid, []))

    def store_feedback_local(self, feedback: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "message": feedback.get("message", ""),
            "route": feedback.get("route", "/"),
            "metadata": feedback.get("metadata", {}),
            "user_id": feedback.get("user_id"),
            "is_kite_user": feedback.get("is_kite_user"),
            "timestamp": utc_now(),
        }
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO feedback_events (uid, route, message, metadata, is_kite_user, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            payload["user_id"],
                            payload["route"],
                            payload["message"],
                            self._serialize_json(payload["metadata"]),
                            bool(payload["is_kite_user"]),
                            payload["timestamp"],
                        ),
                    )
            return payload

        with self._lock:
            state = self._read()
            state["feedback_local"].insert(0, payload)
            state["feedback_local"] = state["feedback_local"][:100]
            self._write(state)
            return deepcopy(payload)

    def get_kite_connection(self, uid: str) -> Dict[str, Any] | None:
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            uid,
                            mcp_session_id,
                            login_url,
                            warning_text,
                            status,
                            profile,
                            last_error,
                            created_at,
                            updated_at,
                            last_validated_at
                        FROM kite_connections
                        WHERE uid = %s
                        """,
                        (uid,),
                    )
                    row = cursor.fetchone()
            if not row:
                return None
            return {
                "uid": row["uid"],
                "mcpSessionId": row["mcp_session_id"],
                "loginUrl": row.get("login_url", ""),
                "warningText": row.get("warning_text", ""),
                "status": row.get("status", "pending"),
                "profile": row.get("profile") or {},
                "lastError": row.get("last_error", ""),
                "createdAt": row["created_at"].isoformat() if row.get("created_at") else utc_now(),
                "updatedAt": row["updated_at"].isoformat() if row.get("updated_at") else utc_now(),
                "lastValidatedAt": row["last_validated_at"].isoformat() if row.get("last_validated_at") else None,
            }

        with self._lock:
            state = self._read()
            item = state["kite_connections"].get(uid)
            return deepcopy(item) if item else None

    def upsert_kite_connection(self, uid: str, **fields: Any) -> Dict[str, Any]:
        payload = {
            "uid": uid,
            "mcpSessionId": fields.get("mcpSessionId", ""),
            "loginUrl": fields.get("loginUrl", ""),
            "warningText": fields.get("warningText", ""),
            "status": fields.get("status", "pending"),
            "profile": fields.get("profile", {}),
            "lastError": fields.get("lastError", ""),
            "createdAt": fields.get("createdAt", utc_now()),
            "updatedAt": utc_now(),
            "lastValidatedAt": fields.get("lastValidatedAt"),
        }
        existing = self.get_kite_connection(uid) or {}
        merged = {
            **existing,
            **{key: value for key, value in payload.items() if value not in (None, "") or key in {"status", "profile"}},
        }
        merged["uid"] = uid
        merged["updatedAt"] = utc_now()

        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO kite_connections (
                            uid,
                            mcp_session_id,
                            login_url,
                            warning_text,
                            status,
                            profile,
                            last_error,
                            created_at,
                            updated_at,
                            last_validated_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s)
                        ON CONFLICT (uid) DO UPDATE SET
                            mcp_session_id = EXCLUDED.mcp_session_id,
                            login_url = EXCLUDED.login_url,
                            warning_text = EXCLUDED.warning_text,
                            status = EXCLUDED.status,
                            profile = EXCLUDED.profile,
                            last_error = EXCLUDED.last_error,
                            updated_at = NOW(),
                            last_validated_at = EXCLUDED.last_validated_at
                        """,
                        (
                            uid,
                            merged.get("mcpSessionId", ""),
                            merged.get("loginUrl", ""),
                            merged.get("warningText", ""),
                            merged.get("status", "pending"),
                            self._serialize_json(merged.get("profile", {})),
                            merged.get("lastError", ""),
                            merged.get("lastValidatedAt"),
                        ),
                    )
            return self.get_kite_connection(uid) or merged

        with self._lock:
            state = self._read()
            state["kite_connections"][uid] = merged
            self._write(state)
            return deepcopy(merged)

    def clear_kite_connection(self, uid: str) -> None:
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("DELETE FROM kite_connections WHERE uid = %s", (uid,))
            return

        with self._lock:
            state = self._read()
            state["kite_connections"].pop(uid, None)
            self._write(state)

    def store_portfolio_snapshot(
        self,
        uid: str,
        snapshot_source: str,
        holdings: Any,
        positions: Any,
        summary: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = {
            "snapshotSource": snapshot_source,
            "holdings": holdings,
            "positions": positions,
            "summary": summary,
            "createdAt": utc_now(),
        }
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO portfolio_snapshots (uid, snapshot_source, holdings, positions, summary, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            uid,
                            snapshot_source,
                            self._serialize_json(holdings),
                            self._serialize_json(positions),
                            self._serialize_json(summary),
                            payload["createdAt"],
                        ),
                    )
            return payload

        with self._lock:
            state = self._read()
            snapshots = state["portfolio_snapshots"].setdefault(uid, [])
            snapshots.insert(0, payload)
            state["portfolio_snapshots"][uid] = snapshots[:10]
            self._write(state)
            return deepcopy(payload)

    def get_latest_portfolio_snapshot(self, uid: str) -> Dict[str, Any] | None:
        if self._postgres_enabled():
            self._ensure_postgres_schema()
            with self._connect() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT snapshot_source, holdings, positions, summary, created_at
                        FROM portfolio_snapshots
                        WHERE uid = %s
                        ORDER BY created_at DESC
                        LIMIT 1
                        """,
                        (uid,),
                    )
                    row = cursor.fetchone()
            if not row:
                return None
            return {
                "snapshotSource": row["snapshot_source"],
                "holdings": row.get("holdings") or [],
                "positions": row.get("positions") or [],
                "summary": row.get("summary") or {},
                "createdAt": row["created_at"].isoformat() if row.get("created_at") else utc_now(),
            }

        with self._lock:
            state = self._read()
            snapshots = state["portfolio_snapshots"].get(uid, [])
            return deepcopy(snapshots[0]) if snapshots else None

    def storage_status(self) -> Dict[str, Any]:
        if self._postgres_enabled():
            try:
                self._ensure_postgres_schema()
                with self._connect() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("SELECT 1")
                        cursor.fetchone()
                return {
                    "mode": "postgres",
                    "ready": True,
                    "dsn_configured": True,
                    "migrations_path": str(settings.postgres_migrations_path),
                }
            except Exception as exc:  # pragma: no cover - connectivity guard
                return {
                    "mode": "postgres",
                    "ready": False,
                    "dsn_configured": True,
                    "migrations_path": str(settings.postgres_migrations_path),
                    "message": str(exc),
                }

        self._ensure()
        return {
            "mode": "local-json",
            "path": str(self.path),
            "ready": self.path.exists(),
        }


app_state_store = AppStateStore(settings.app_state_path)
