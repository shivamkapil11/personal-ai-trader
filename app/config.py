from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


def _as_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    app_title: str
    app_host: str
    app_port: int
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
    width = os.getenv("TRADINGVIEW_WINDOW_WIDTH", "1400")
    height = os.getenv("TRADINGVIEW_WINDOW_HEIGHT", "1400")
    return Settings(
        app_title="Local Stock Research Dashboard",
        app_host=os.getenv("APP_HOST", "127.0.0.1"),
        app_port=int(os.getenv("APP_PORT", "8008")),
        tradingview_enabled=_as_bool(os.getenv("TRADINGVIEW_ENABLED"), True),
        tradingview_desktop_enabled=_as_bool(os.getenv("TRADINGVIEW_DESKTOP_ENABLED"), True),
        tradingview_desktop_repo_path=Path(
            os.getenv("TRADINGVIEW_DESKTOP_REPO_PATH", str(PROJECT_ROOT.parent / "tradingview-mcp"))
        ),
        tradingview_repo_path=Path(os.getenv("TRADINGVIEW_REPO_PATH", str(repo_default))),
        tradingview_session_id=os.getenv("TRADINGVIEW_SESSION_ID", "").strip(),
        tradingview_session_id_sign=os.getenv("TRADINGVIEW_SESSION_ID_SIGN", "").strip(),
        tradingview_headless=_as_bool(os.getenv("TRADINGVIEW_HEADLESS"), True),
        tradingview_window_size=f"{width},{height}",
        tradingview_chart_page_id=os.getenv("TRADINGVIEW_CHART_PAGE_ID", "").strip(),
    )


settings = get_settings()
