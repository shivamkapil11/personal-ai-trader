from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _path_from_env(name: str, default: Path) -> Path:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        return default
    return Path(raw.strip())


def _runtime_data_root() -> Path:
    # Vercel and similar serverless runtimes only allow writes under /tmp.
    if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
        return Path("/tmp/gains-runtime")
    return PROJECT_ROOT / "data"


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    app_title: str
    app_host: str
    app_port: int
    app_secret: str
    app_state_path: Path
    knowledge_registry_path: Path
    activity_log_path: Path
    postgres_enabled: bool
    postgres_dsn: str
    postgres_migrations_path: Path
    market_data_provider_order: tuple[str, ...]
    kite_mcp_enabled: bool
    kite_mcp_mode: str
    kite_mcp_url: str
    kite_mcp_repo_path: Path
    kite_mcp_bridge_base_url: str
    kite_mcp_bridge_api_key: str
    firebase_enabled: bool
    firebase_api_key: str
    firebase_auth_domain: str
    firebase_project_id: str
    firebase_storage_bucket: str
    firebase_messaging_sender_id: str
    firebase_app_id: str
    firebase_measurement_id: str
    firebase_admin_credentials_path: Path
    firebase_admin_credentials_json: str
    auth_allow_dev_fallback: bool
    feedback_firestore_enabled: bool
    feedback_firestore_collection: str
    feedback_firestore_project_id: str
    feedback_firestore_credentials_path: Path
    tradingview_enabled: bool
    tradingview_desktop_enabled: bool
    tradingview_desktop_repo_path: Path
    tradingview_repo_path: Path
    tradingview_session_id: str
    tradingview_session_id_sign: str
    tradingview_headless: bool
    tradingview_window_size: str
    tradingview_chart_page_id: str

    @property
    def tradingview_configured(self) -> bool:
        return bool(self.tradingview_session_id and self.tradingview_session_id_sign)


def get_settings() -> Settings:
    repo_default = PROJECT_ROOT.parent / "tradingview-chart-mcp"
    kite_repo_default = PROJECT_ROOT.parent / "kite-mcp-server"
    runtime_data_root = _runtime_data_root()
    data_default = runtime_data_root / "app_state.json"
    knowledge_default = PROJECT_ROOT / "data" / "knowledge_registry.json"
    activity_log_default = runtime_data_root / "logs" / "activity.jsonl"
    migrations_default = PROJECT_ROOT / "infrastructure" / "postgres" / "migrations"
    width = os.getenv("TRADINGVIEW_WINDOW_WIDTH", "1400")
    height = os.getenv("TRADINGVIEW_WINDOW_HEIGHT", "1400")
    provider_order_raw = os.getenv("MARKET_DATA_PROVIDER_ORDER", "kite_mcp,jugaad_data,yfinance")
    provider_order = tuple(
        item.strip().lower()
        for item in provider_order_raw.split(",")
        if item.strip()
    )
    return Settings(
        app_title=os.getenv("APP_TITLE", "Gains"),
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "8008")),
        app_secret=os.getenv("APP_SECRET", "local-stock-dashboard-secret").strip(),
        app_state_path=_path_from_env("APP_STATE_PATH", data_default),
        knowledge_registry_path=_path_from_env("KNOWLEDGE_REGISTRY_PATH", knowledge_default),
        activity_log_path=_path_from_env("ACTIVITY_LOG_PATH", activity_log_default),
        postgres_enabled=_as_bool(os.getenv("POSTGRES_ENABLED"), False),
        postgres_dsn=os.getenv("POSTGRES_DSN", "").strip(),
        postgres_migrations_path=_path_from_env("POSTGRES_MIGRATIONS_PATH", migrations_default),
        market_data_provider_order=provider_order or ("kite_mcp", "jugaad_data", "yfinance"),
        kite_mcp_enabled=_as_bool(os.getenv("KITE_MCP_ENABLED"), True),
        kite_mcp_mode=os.getenv("KITE_MCP_MODE", "hosted").strip().lower() or "hosted",
        kite_mcp_url=os.getenv("KITE_MCP_URL", "https://mcp.kite.trade/mcp").strip(),
        kite_mcp_repo_path=_path_from_env("KITE_MCP_REPO_PATH", kite_repo_default),
        kite_mcp_bridge_base_url=os.getenv("KITE_MCP_BRIDGE_BASE_URL", "").strip(),
        kite_mcp_bridge_api_key=os.getenv("KITE_MCP_BRIDGE_API_KEY", "").strip(),
        firebase_enabled=_as_bool(os.getenv("FIREBASE_ENABLED"), False),
        firebase_api_key=os.getenv("FIREBASE_API_KEY", "").strip(),
        firebase_auth_domain=os.getenv("FIREBASE_AUTH_DOMAIN", "").strip(),
        firebase_project_id=os.getenv("FIREBASE_PROJECT_ID", "").strip(),
        firebase_storage_bucket=os.getenv("FIREBASE_STORAGE_BUCKET", "").strip(),
        firebase_messaging_sender_id=os.getenv("FIREBASE_MESSAGING_SENDER_ID", "").strip(),
        firebase_app_id=os.getenv("FIREBASE_APP_ID", "").strip(),
        firebase_measurement_id=os.getenv("FIREBASE_MEASUREMENT_ID", "").strip(),
        firebase_admin_credentials_path=Path(os.getenv("FIREBASE_ADMIN_CREDENTIALS_PATH", "")),
        firebase_admin_credentials_json=os.getenv("FIREBASE_ADMIN_CREDENTIALS_JSON", "").strip(),
        auth_allow_dev_fallback=_as_bool(os.getenv("AUTH_ALLOW_DEV_FALLBACK"), True),
        feedback_firestore_enabled=_as_bool(os.getenv("FEEDBACK_FIRESTORE_ENABLED"), False),
        feedback_firestore_collection=os.getenv("FEEDBACK_FIRESTORE_COLLECTION", "feedback"),
        feedback_firestore_project_id=os.getenv("FEEDBACK_FIRESTORE_PROJECT_ID", "").strip(),
        feedback_firestore_credentials_path=Path(os.getenv("FEEDBACK_FIRESTORE_CREDENTIALS_PATH", "")),
        tradingview_enabled=_as_bool(os.getenv("TRADINGVIEW_ENABLED"), True),
        tradingview_desktop_enabled=_as_bool(os.getenv("TRADINGVIEW_DESKTOP_ENABLED"), True),
        tradingview_desktop_repo_path=_path_from_env("TRADINGVIEW_DESKTOP_REPO_PATH", PROJECT_ROOT.parent / "tradingview-mcp"),
        tradingview_repo_path=_path_from_env("TRADINGVIEW_REPO_PATH", repo_default),
        tradingview_session_id=os.getenv("TRADINGVIEW_SESSION_ID", "").strip(),
        tradingview_session_id_sign=os.getenv("TRADINGVIEW_SESSION_ID_SIGN", "").strip(),
        tradingview_headless=_as_bool(os.getenv("TRADINGVIEW_HEADLESS"), True),
        tradingview_window_size=f"{width},{height}",
        tradingview_chart_page_id=os.getenv("TRADINGVIEW_CHART_PAGE_ID", "").strip(),
    )


settings = get_settings()
