from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import requests

from app.config import settings
from app.services.app_state import app_state_store, utc_now

LOGIN_REQUIRED_TEXT = "Please log in first using the login tool"
LOGIN_URL_PATTERN = re.compile(r"\[Login to Kite\]\((https://[^)]+)\)")
WARNING_PATTERN = re.compile(
    r"WARNING:.*?risk\.\*\*",
    re.IGNORECASE | re.DOTALL,
)


def _headers(session_id: str | None = None) -> Dict[str, str]:
    headers = {
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
    }
    if session_id:
        headers["mcp-session-id"] = session_id
    return headers


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


class HostedKiteMCPClient:
    def __init__(self) -> None:
        self.url = settings.kite_mcp_url

    def initialize_session(self) -> str:
        response = requests.post(
            self.url,
            headers=_headers(),
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-03-26",
                    "capabilities": {},
                    "clientInfo": {"name": "gains-dashboard", "version": "0.1.0"},
                },
            },
            timeout=20,
        )
        response.raise_for_status()
        session_id = response.headers.get("mcp-session-id", "").strip()
        if not session_id:
            raise RuntimeError("Kite MCP did not return a session id.")
        requests.post(
            self.url,
            headers=_headers(session_id),
            json={"jsonrpc": "2.0", "method": "notifications/initialized"},
            timeout=20,
        )
        return session_id

    def call_tool(self, session_id: str, tool_name: str, arguments: Dict[str, Any] | None = None) -> Dict[str, Any]:
        response = requests.post(
            self.url,
            headers=_headers(session_id),
            json={
                "jsonrpc": "2.0",
                "id": int(datetime.now(timezone.utc).timestamp() * 1000),
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments or {}},
            },
            timeout=25,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get("error"):
            return {
                "ok": False,
                "session_id": session_id,
                "error": payload["error"].get("message", "Kite MCP returned an error."),
                "raw": payload,
            }

        result = payload.get("result", {})
        content = result.get("content", [])
        text_parts = [
            item.get("text", "")
            for item in content
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        text = "\n".join(part for part in text_parts if part).strip()
        parsed: Any = None
        if text.startswith("{") or text.startswith("["):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None

        return {
            "ok": not bool(result.get("isError")),
            "session_id": session_id,
            "text": text,
            "data": parsed,
            "raw": payload,
        }


class KiteBridge:
    def __init__(self) -> None:
        self.client = HostedKiteMCPClient()

    def _bridge_ready(self) -> bool:
        return bool(settings.kite_mcp_enabled and settings.kite_mcp_url)

    def _session_is_fresh(self, connection: Dict[str, Any] | None, seconds: int = 45) -> bool:
        if not connection:
            return False
        last_validated_at = _parse_iso(connection.get("lastValidatedAt"))
        if not last_validated_at:
            return False
        return datetime.now(timezone.utc) - last_validated_at < timedelta(seconds=seconds)

    def _extract_login_payload(self, text: str) -> Dict[str, str]:
        login_url_match = LOGIN_URL_PATTERN.search(text or "")
        warning_match = WARNING_PATTERN.search(text or "")
        return {
            "loginUrl": login_url_match.group(1) if login_url_match else "",
            "warningText": warning_match.group(0).strip() if warning_match else "",
        }

    def _ensure_user_session(self, user: Dict[str, Any] | None) -> tuple[str | None, Dict[str, Any] | None]:
        if not user:
            return None, None
        connection = app_state_store.get_kite_connection(user["uid"])
        if connection and connection.get("mcpSessionId"):
            return connection["mcpSessionId"], connection
        return None, connection

    def _create_ephemeral_session(self) -> str:
        return self.client.initialize_session()

    def _refresh_connection(self, user: Dict[str, Any], connection: Dict[str, Any]) -> Dict[str, Any]:
        if self._session_is_fresh(connection):
            return connection

        profile_result = self.client.call_tool(connection["mcpSessionId"], "get_profile", {})
        if profile_result["ok"] and isinstance(profile_result.get("data"), dict):
            refreshed = app_state_store.upsert_kite_connection(
                user["uid"],
                mcpSessionId=connection["mcpSessionId"],
                loginUrl=connection.get("loginUrl", ""),
                warningText=connection.get("warningText", ""),
                status="connected",
                profile=profile_result["data"],
                lastError="",
                lastValidatedAt=utc_now(),
            )
            app_state_store.update_user_fields(user["uid"], kiteConnected=True, onboardingStep="dashboard")
            return refreshed

        status = "auth_required" if LOGIN_REQUIRED_TEXT in profile_result.get("text", "") else "error"
        refreshed = app_state_store.upsert_kite_connection(
            user["uid"],
            mcpSessionId=connection["mcpSessionId"],
            loginUrl=connection.get("loginUrl", ""),
            warningText=connection.get("warningText", ""),
            status=status,
            profile={},
            lastError=profile_result.get("error") or profile_result.get("text", ""),
            lastValidatedAt=utc_now(),
        )
        app_state_store.update_user_fields(user["uid"], kiteConnected=False)
        return refreshed

    def status(self, user: Dict[str, Any] | None = None) -> Dict[str, Any]:
        repo_exists = settings.kite_mcp_repo_path.exists()
        connection = app_state_store.get_kite_connection(user["uid"]) if user else None
        if user and connection:
            try:
                connection = self._refresh_connection(user, connection)
            except Exception as exc:  # pragma: no cover - network guard
                connection = app_state_store.upsert_kite_connection(
                    user["uid"],
                    mcpSessionId=connection.get("mcpSessionId", ""),
                    loginUrl=connection.get("loginUrl", ""),
                    warningText=connection.get("warningText", ""),
                    status="error",
                    profile=connection.get("profile", {}),
                    lastError=str(exc),
                    lastValidatedAt=utc_now(),
                )

        session_status = connection.get("status", "not_connected") if connection else "not_connected"
        kite_connected = session_status == "connected"
        login_url = connection.get("loginUrl", "") if connection else ""
        message = "Connect Kite to unlock holdings, positions, and live quote overlays."
        if kite_connected:
            name = (connection.get("profile") or {}).get("user_name") or (connection.get("profile") or {}).get("user_name")
            message = f"Kite session is live{f' for {name}' if name else ''}."
        elif session_status == "auth_required":
            message = "Kite session exists, but Zerodha login still needs to be completed."
        elif session_status == "pending_login":
            message = "Open the Zerodha link to finish Kite connection."
        elif session_status == "error":
            message = connection.get("lastError") or "Kite MCP is reachable, but the session needs attention."

        return {
            "enabled": settings.kite_mcp_enabled,
            "repo_detected": repo_exists,
            "mode": settings.kite_mcp_mode,
            "hosted_endpoint": settings.kite_mcp_url,
            "bridge_base_url": "/api/kite/connect",
            "bridge_ready": self._bridge_ready(),
            "kite_connected": kite_connected,
            "connect_supported": self._bridge_ready(),
            "session_status": session_status,
            "login_url": login_url,
            "warning_text": connection.get("warningText", "") if connection else "",
            "profile": connection.get("profile", {}) if connection else {},
            "last_error": connection.get("lastError", "") if connection else "",
            "message": message,
        }

    def connect(self, user: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not user:
            return {"available": False, "message": "Please log in before connecting Kite."}
        if not self._bridge_ready():
            return {"available": False, "message": "Kite MCP is not enabled in configuration."}

        session_id, existing = self._ensure_user_session(user)
        if not session_id:
            session_id = self._create_ephemeral_session()

        login_result = self.client.call_tool(session_id, "login", {})
        if not login_result["ok"] and LOGIN_REQUIRED_TEXT not in login_result.get("text", ""):
            app_state_store.upsert_kite_connection(
                user["uid"],
                mcpSessionId=session_id,
                status="error",
                lastError=login_result.get("error") or login_result.get("text", ""),
                lastValidatedAt=utc_now(),
            )
            app_state_store.update_user_fields(user["uid"], kiteConnected=False)
            return {
                "available": False,
                "message": login_result.get("error") or login_result.get("text", "Unable to start Kite login."),
            }

        login_payload = self._extract_login_payload(login_result.get("text", ""))
        status = "connected" if "already logged in as" in login_result.get("text", "") else "pending_login"
        saved = app_state_store.upsert_kite_connection(
            user["uid"],
            mcpSessionId=session_id,
            loginUrl=login_payload["loginUrl"] or existing.get("loginUrl", "") if existing else login_payload["loginUrl"],
            warningText=login_payload["warningText"] or existing.get("warningText", "") if existing else login_payload["warningText"],
            status=status,
            lastError="",
            profile=existing.get("profile", {}) if existing else {},
            lastValidatedAt=utc_now(),
        )

        if status == "connected":
            app_state_store.update_user_fields(user["uid"], kiteConnected=True, onboardingStep="dashboard")
        else:
            app_state_store.update_user_fields(user["uid"], kiteConnected=False)

        return {
            "available": True,
            "session_status": status,
            "login_url": saved.get("loginUrl", ""),
            "warning_text": saved.get("warningText", ""),
            "message": "Kite is already connected." if status == "connected" else "Open the Zerodha login to finish connecting Kite.",
        }

    def search_instruments(self, query: str, user: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not self._bridge_ready():
            return {"available": False, "message": "Kite MCP is not enabled."}
        session_id = None
        if user:
            session_id, _ = self._ensure_user_session(user)
        if not session_id:
            session_id = self._create_ephemeral_session()
        try:
            result = self.client.call_tool(
                session_id,
                "search_instruments",
                {"query": query, "filter_on": "id" if ":" in query else "tradingsymbol", "limit": 20},
            )
            return {
                "available": result["ok"],
                "payload": result.get("data") or {},
                "message": result.get("text", ""),
            }
        except Exception as exc:  # pragma: no cover - network guard
            return {"available": False, "message": f"Kite instrument search failed: {exc}"}

    def get_quotes(self, instruments: List[str], user: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not user:
            return {"available": False, "message": "Please connect Kite to use live quotes."}
        session_id, connection = self._ensure_user_session(user)
        if not session_id:
            return {"available": False, "message": "Connect Kite before requesting live quotes."}
        refreshed = self._refresh_connection(user, connection or {"mcpSessionId": session_id})
        if refreshed.get("status") != "connected":
            return {"available": False, "message": "Complete Zerodha login before requesting live quotes."}
        try:
            result = self.client.call_tool(session_id, "get_quotes", {"instruments": instruments})
            if not result["ok"]:
                return {"available": False, "message": result.get("error") or result.get("text", "Kite quote lookup failed.")}
            return {"available": True, "payload": result.get("data") or {}, "message": result.get("text", "")}
        except Exception as exc:  # pragma: no cover - network guard
            return {"available": False, "message": f"Kite quote lookup failed: {exc}"}

    def get_holdings(self, user: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not user:
            return {"available": False, "message": "Please log in first."}
        session_id, connection = self._ensure_user_session(user)
        if not session_id:
            return {"available": False, "message": "Connect Kite before requesting holdings."}
        refreshed = self._refresh_connection(user, connection or {"mcpSessionId": session_id})
        if refreshed.get("status") != "connected":
            return {"available": False, "message": "Complete Zerodha login before requesting holdings."}
        try:
            result = self.client.call_tool(session_id, "get_holdings", {})
            if not result["ok"]:
                return {"available": False, "message": result.get("error") or result.get("text", "Could not load Kite holdings.")}
            return {"available": True, "payload": result.get("data") or {}, "message": result.get("text", "")}
        except Exception as exc:  # pragma: no cover - network guard
            return {"available": False, "message": f"Could not load Kite holdings: {exc}"}

    def get_positions(self, user: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not user:
            return {"available": False, "message": "Please log in first."}
        session_id, connection = self._ensure_user_session(user)
        if not session_id:
            return {"available": False, "message": "Connect Kite before requesting positions."}
        refreshed = self._refresh_connection(user, connection or {"mcpSessionId": session_id})
        if refreshed.get("status") != "connected":
            return {"available": False, "message": "Complete Zerodha login before requesting positions."}
        try:
            result = self.client.call_tool(session_id, "get_positions", {})
            if not result["ok"]:
                return {"available": False, "message": result.get("error") or result.get("text", "Could not load Kite positions.")}
            return {"available": True, "payload": result.get("data") or {}, "message": result.get("text", "")}
        except Exception as exc:  # pragma: no cover - network guard
            return {"available": False, "message": f"Could not load Kite positions: {exc}"}


kite_bridge = KiteBridge()
