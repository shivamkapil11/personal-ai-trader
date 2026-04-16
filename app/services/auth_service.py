from __future__ import annotations

import base64
import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict

from fastapi import Request

from app.config import settings
from app.services.app_state import app_state_store, utc_now

try:
    import firebase_admin
    from firebase_admin import auth as firebase_auth
    from firebase_admin import credentials as firebase_credentials
except Exception:  # pragma: no cover - optional dependency at runtime
    firebase_admin = None
    firebase_auth = None
    firebase_credentials = None


SESSION_COOKIE = "gains_session"


def _firebase_client_config() -> Dict[str, str]:
    return {
        "apiKey": settings.firebase_api_key,
        "authDomain": settings.firebase_auth_domain,
        "projectId": settings.firebase_project_id,
        "storageBucket": settings.firebase_storage_bucket,
        "messagingSenderId": settings.firebase_messaging_sender_id,
        "appId": settings.firebase_app_id,
        "measurementId": settings.firebase_measurement_id,
    }


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(payload: Dict[str, Any]) -> str:
    encoded = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = hmac.new(settings.app_secret.encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256).digest()
    return f"{encoded}.{_b64(signature)}"


def _unsign(token: str) -> Dict[str, Any] | None:
    if "." not in token:
        return None
    encoded, provided = token.split(".", 1)
    expected = _b64(hmac.new(settings.app_secret.encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256).digest())
    if not hmac.compare_digest(expected, provided):
        return None
    try:
        payload = json.loads(_b64decode(encoded))
    except Exception:
        return None
    expires_at = payload.get("exp")
    if not expires_at:
        return None
    try:
        expiry = datetime.fromisoformat(expires_at)
    except ValueError:
        return None
    if expiry < datetime.now(timezone.utc):
        return None
    return payload


def firebase_backend_ready() -> bool:
    return (
        settings.firebase_enabled
        and bool(settings.firebase_project_id and settings.firebase_api_key and settings.firebase_auth_domain)
    )


def _firebase_admin_credentials_from_env() -> Dict[str, Any] | None:
    raw = settings.firebase_admin_credentials_json.strip()
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def firebase_admin_ready() -> bool:
    configured_path = str(settings.firebase_admin_credentials_path).strip()
    return (
        firebase_admin is not None
        and (
            _firebase_admin_credentials_from_env() is not None
            or (
                configured_path not in {"", ".", "./"}
                and Path(settings.firebase_admin_credentials_path).exists()
                and Path(settings.firebase_admin_credentials_path).is_file()
            )
        )
    )


def _ensure_firebase_admin() -> None:
    if not firebase_admin_ready():
        return
    if firebase_admin._apps:  # type: ignore[attr-defined]
        return
    inline_credentials = _firebase_admin_credentials_from_env()
    credential = firebase_credentials.Certificate(inline_credentials or str(settings.firebase_admin_credentials_path))
    firebase_admin.initialize_app(credential)  # type: ignore[union-attr]


def verify_google_session(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("id_token") and firebase_admin_ready():
        try:
            _ensure_firebase_admin()
            decoded = firebase_auth.verify_id_token(payload["id_token"])  # type: ignore[union-attr]
        except Exception as exc:
            raise ValueError(f"Firebase could not verify the Google sign-in token: {exc}") from exc
        return {
            "uid": decoded["uid"],
            "name": decoded.get("name") or payload.get("name") or "Gains user",
            "email": decoded.get("email") or payload.get("email") or "",
            "image": decoded.get("picture") or payload.get("image") or "",
            "provider": "google",
            "verified": True,
        }

    if settings.auth_allow_dev_fallback:
        return {
            "uid": payload["uid"],
            "name": payload.get("name") or "Local Gains user",
            "email": payload.get("email") or "",
            "image": payload.get("image") or "",
            "provider": payload.get("provider", "google"),
            "verified": False,
        }

    raise ValueError("Firebase backend verification is not configured yet.")


def _firebase_missing_bits() -> list[str]:
    missing: list[str] = []
    if not settings.firebase_api_key:
        missing.append("FIREBASE_API_KEY")
    if not settings.firebase_auth_domain:
        missing.append("FIREBASE_AUTH_DOMAIN")
    if not settings.firebase_project_id:
        missing.append("FIREBASE_PROJECT_ID")
    if not settings.firebase_app_id:
        missing.append("FIREBASE_APP_ID")
    if not settings.firebase_storage_bucket:
        missing.append("FIREBASE_STORAGE_BUCKET")
    if not settings.firebase_messaging_sender_id:
        missing.append("FIREBASE_MESSAGING_SENDER_ID")
    if not firebase_admin_ready():
        missing.append("FIREBASE_ADMIN_CREDENTIALS_PATH or FIREBASE_ADMIN_CREDENTIALS_JSON")
    return missing


def request_is_secure(request: Request) -> bool:
    forwarded_proto = request.headers.get("x-forwarded-proto", "")
    return request.url.scheme == "https" or forwarded_proto.lower() == "https"


def create_session_cookie(user: Dict[str, Any]) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(days=14)
    session_payload = {
        "uid": user["uid"],
        "email": user["email"],
        "name": user["name"],
        "image": user.get("image", ""),
        "provider": user.get("provider", "google"),
        "kiteConnected": user.get("kiteConnected", False),
        "isKiteUser": user.get("isKiteUser"),
        "onboardingStep": user.get("onboardingStep", "auth"),
        "exp": expires_at.isoformat(),
    }
    return _sign(session_payload)


def get_session_from_request(request: Request) -> Dict[str, Any] | None:
    cookie = request.cookies.get(SESSION_COOKIE)
    if not cookie:
        return None
    payload = _unsign(cookie)
    if not payload:
        return None
    user = app_state_store.get_user(payload["uid"])
    return user or payload


def bootstrap_auth_state(request: Request) -> Dict[str, Any]:
    return {
        "firebase_enabled": settings.firebase_enabled,
        "firebase_backend_ready": firebase_backend_ready(),
        "firebase_admin_ready": firebase_admin_ready(),
        "firebase_missing": _firebase_missing_bits() if settings.firebase_enabled else [],
        "allow_dev_fallback": settings.auth_allow_dev_fallback,
        "firebase_client_config": _firebase_client_config(),
        "session": get_session_from_request(request),
    }


def auth_status_snapshot() -> Dict[str, Any]:
    return {
        "firebase_enabled": settings.firebase_enabled,
        "firebase_backend_ready": firebase_backend_ready(),
        "firebase_admin_ready": firebase_admin_ready(),
        "firebase_missing": _firebase_missing_bits() if settings.firebase_enabled else [],
        "allow_dev_fallback": settings.auth_allow_dev_fallback,
    }


def login_user(payload: Dict[str, Any]) -> Dict[str, Any]:
    verified = verify_google_session(payload)
    existing = app_state_store.get_user(verified["uid"]) or {}
    user = app_state_store.upsert_user(
        {
            "uid": verified["uid"],
            "name": verified["name"],
            "email": verified["email"],
            "image": verified.get("image", ""),
            "provider": verified.get("provider", "google"),
            "kiteConnected": existing.get("kiteConnected", False),
            "isKiteUser": existing.get("isKiteUser"),
            "onboardingStep": existing.get("onboardingStep", "choose-kite"),
        }
    )
    return {
        "user": user,
        "session_cookie": create_session_cookie(user),
        "verified": verified["verified"],
        "timestamp": utc_now(),
    }


def logout_payload() -> Dict[str, Any]:
    return {"ok": True, "timestamp": utc_now()}
