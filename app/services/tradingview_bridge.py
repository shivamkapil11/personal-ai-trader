from __future__ import annotations

import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from app.config import settings


class TradingViewBridge:
    def __init__(self) -> None:
        self.repo_path = settings.tradingview_repo_path
        self.desktop_repo_path = settings.tradingview_desktop_repo_path

    def desktop_status(self) -> Dict[str, Any]:
        if not settings.tradingview_desktop_enabled:
            return {"available": False, "message": "Desktop TradingView bridge is turned off in configuration."}
        if not self.desktop_repo_path.exists():
            return {"available": False, "message": f"TradingView Desktop bridge repo was not found at {self.desktop_repo_path}."}
        try:
            status = self._run_desktop_cli("status")
            return {
                "available": True,
                "message": "TradingView Desktop bridge is connected.",
                "details": status,
            }
        except RuntimeError as exc:
            return {
                "available": False,
                "message": (
                    f"TradingView Desktop is installed but not connected yet. "
                    f"Launch it in debug mode with: cd {self.desktop_repo_path} && node src/cli/index.js launch --no-kill"
                ),
                "error": str(exc),
            }

    def browser_status(self) -> Dict[str, Any]:
        if not settings.tradingview_enabled:
            return {"available": False, "message": "Browser TradingView snapshots are turned off in configuration."}
        if not self.repo_path.exists():
            return {"available": False, "message": f"TradingView MCP repo was not found at {self.repo_path}."}
        if not settings.tradingview_configured:
            return {
                "available": False,
                "message": "Add TRADINGVIEW_SESSION_ID and TRADINGVIEW_SESSION_ID_SIGN to stock-dashboard/.env to enable live snapshots.",
            }
        return {"available": True, "message": "TradingView snapshots are ready."}

    def status(self) -> Dict[str, Any]:
        desktop = self.desktop_status()
        if desktop["available"]:
            return {
                "available": True,
                "source": "desktop",
                "message": desktop["message"],
                "details": desktop.get("details"),
            }
        browser = self.browser_status()
        if browser["available"]:
            return {"available": True, "source": "browser", "message": browser["message"]}
        return {
            "available": False,
            "source": None,
            "message": desktop["message"] if settings.tradingview_desktop_enabled else browser["message"],
            "desktop": desktop,
            "browser": browser,
        }

    def _run_desktop_cli(self, *args: str) -> Dict[str, Any]:
        command = ["node", "src/cli/index.js", *args]
        result = subprocess.run(
            command,
            cwd=self.desktop_repo_path,
            capture_output=True,
            text=True,
            timeout=90,
        )
        output = (result.stdout or result.stderr).strip()
        payload: Dict[str, Any]
        try:
            payload = json.loads(output) if output else {}
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Unexpected TradingView Desktop CLI output: {output}") from exc

        if result.returncode != 0 or payload.get("success") is False:
            raise RuntimeError(payload.get("error") or output or "TradingView Desktop CLI failed.")
        return payload

    @staticmethod
    def _file_to_data_url(path: str | Path) -> str:
        file_path = Path(path)
        encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    def _capture_desktop(self, tradingview_symbol: str, interval: str) -> Dict[str, Any]:
        original_symbol = None
        original_resolution = None
        restored = True
        try:
            status = self._run_desktop_cli("status")
            original_symbol = status.get("chart_symbol")
            original_resolution = status.get("chart_resolution")

            if original_symbol and original_symbol != tradingview_symbol:
                self._run_desktop_cli("symbol", tradingview_symbol)
            if original_resolution and original_resolution != interval:
                self._run_desktop_cli("timeframe", interval)

            screenshot = self._run_desktop_cli("screenshot", "-r", "chart")
            image_url = self._file_to_data_url(screenshot["file_path"])
            return {
                "status": "ready",
                "image_url": image_url,
                "interval": interval,
                "symbol": tradingview_symbol,
                "source": "tradingview-desktop-mcp",
                "note": "Captured from TradingView Desktop and restored to the previous chart state.",
            }
        except Exception as exc:
            return {"status": "error", "message": f"Desktop TradingView capture failed: {exc}"}
        finally:
            try:
                if original_resolution and original_resolution != interval:
                    self._run_desktop_cli("timeframe", original_resolution)
                if original_symbol and original_symbol != tradingview_symbol:
                    self._run_desktop_cli("symbol", original_symbol)
            except Exception:
                restored = False
            if not restored:
                # Best-effort restore note if capture succeeded.
                pass

    def _capture_browser(self, tradingview_symbol: str, interval: str) -> Dict[str, Any]:
        state = self.browser_status()
        if not state["available"]:
            return {"status": "unavailable", "message": state["message"]}

        if str(self.repo_path) not in sys.path:
            sys.path.insert(0, str(self.repo_path))

        os.environ["TRADINGVIEW_SESSION_ID"] = settings.tradingview_session_id
        os.environ["TRADINGVIEW_SESSION_ID_SIGN"] = settings.tradingview_session_id_sign

        try:
            from tview_scraper import TradingViewScraper
        except Exception as exc:  # pragma: no cover - import path guard
            return {"status": "error", "message": f"Unable to import TradingView scraper: {exc}"}

        kwargs = {
            "headless": settings.tradingview_headless,
            "window_size": settings.tradingview_window_size,
            "use_save_shortcut": True,
        }
        if settings.tradingview_chart_page_id:
            kwargs["chart_page_id"] = settings.tradingview_chart_page_id

        try:
            with TradingViewScraper(**kwargs) as scraper:
                image_url = scraper.get_chart_image_url(tradingview_symbol, interval)
        except Exception as exc:
            return {"status": "error", "message": f"TradingView capture failed: {exc}"}

        if not image_url:
            return {"status": "error", "message": "TradingView returned an empty snapshot."}

        return {
            "status": "ready",
            "image_url": image_url,
            "interval": interval,
            "symbol": tradingview_symbol,
            "source": "tradingview-chart-mcp",
        }

    def capture(self, tradingview_symbol: str, interval: str) -> Dict[str, Any]:
        desktop = self.desktop_status()
        if desktop["available"]:
            return self._capture_desktop(tradingview_symbol, interval)
        browser = self.browser_status()
        if browser["available"]:
            return self._capture_browser(tradingview_symbol, interval)
        return {"status": "unavailable", "message": desktop["message"] or browser["message"]}


tradingview_bridge = TradingViewBridge()
