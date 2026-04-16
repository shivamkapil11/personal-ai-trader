from __future__ import annotations

import asyncio
import json
from typing import Any, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.config import PROJECT_ROOT, settings
from app.jobs import job_manager
from app.models import AnalysisRequest
from app.services.analysis_engine import build_comparison, build_report
from app.services.market_data import MarketDataError, collect_stock_data
from app.services.request_intelligence import interpret_user_request
from app.services.tradingview_bridge import tradingview_bridge


app = FastAPI(title=settings.app_title)
app.mount("/static", StaticFiles(directory=str(PROJECT_ROOT / "app" / "static")), name="static")
templates = Jinja2Templates(directory=str(PROJECT_ROOT / "app" / "templates"))


def compact_number(value: int | float | None) -> str:
    if value is None:
        return "N/A"
    number = float(value)
    abs_number = abs(number)
    if abs_number >= 1_00_00_00_00_000:
        return f"{number / 1_00_00_00_00_000:.2f}L Cr"
    if abs_number >= 1_00_00_00_000:
        return f"{number / 1_00_00_00_000:.2f}Cr"
    if abs_number >= 1_000_000_000:
        return f"{number / 1_000_000_000:.2f}B"
    if abs_number >= 1_000_000:
        return f"{number / 1_000_000:.2f}M"
    return f"{number:.2f}"


def serialize(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {key: serialize(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [serialize(item) for item in obj]
    if hasattr(obj, "item"):
        return serialize(obj.item())
    if isinstance(obj, float):
        if obj != obj or obj in {float("inf"), float("-inf")}:
            return None
        return obj
    return obj


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
        "request": request,
        "title": settings.app_title,
        "tradingview_enabled": settings.tradingview_enabled or settings.tradingview_desktop_enabled,
        "tradingview_configured": tradingview_bridge.status()["available"],
    },
)


@app.get("/health")
async def health() -> Dict[str, Any]:
    return {
        "status": "ok",
        "app": settings.app_title,
        "tradingview": tradingview_bridge.status(),
    }


def emit(job_id: str, step: str, message: str, progress: int, symbol: str | None = None) -> None:
    job_manager.publish(
        job_id,
        step=step,
        message=message,
        progress=progress,
        symbol=symbol,
    )


def analyze_symbol_sync(job_id: str, symbol: str, interval: str, include_snapshot: bool) -> Dict[str, Any]:
    emit(job_id, "resolve", f"Resolving live symbol for {symbol}.", 6, symbol)
    stock = collect_stock_data(symbol)
    emit(job_id, "market", f"Fetched market profile and price history for {stock['resolved_symbol']}.", 18, symbol)
    emit(job_id, "technicals", f"Computed technical indicators for {stock['resolved_symbol']}.", 34, symbol)
    emit(job_id, "fundamentals", f"Built the fundamentals snapshot for {stock['resolved_symbol']}.", 48, symbol)
    emit(job_id, "news", f"Pulled recent headline context for {stock['resolved_symbol']}.", 58, symbol)

    report = build_report(stock)
    emit(job_id, "scoring", f"Scored swing and long-term fit for {stock['resolved_symbol']}.", 72, symbol)

    if include_snapshot:
        emit(job_id, "snapshot", f"Checking TradingView snapshot status for {report['identity']['resolved_symbol']}.", 82, symbol)
        report["snapshot"] = tradingview_bridge.capture(report["identity"]["tradingview_symbol"], interval)
        snapshot_status = report["snapshot"]["status"]
        if snapshot_status == "ready":
            emit(job_id, "snapshot", f"Captured TradingView snapshot for {report['identity']['resolved_symbol']}.", 88, symbol)
        else:
            emit(job_id, "snapshot", f"Skipped live snapshot for {report['identity']['resolved_symbol']}: {report['snapshot']['message']}", 88, symbol)
    else:
        report["snapshot"] = {"status": "unavailable", "message": "TradingView snapshot was turned off for this run."}

    report["display"] = {
        "market_cap_compact": compact_number(report["summary"]["market_cap"]),
        "enterprise_value_compact": compact_number(report["fundamentals"].get("enterprise_value")),
    }
    emit(job_id, "assemble", f"Assembled the dashboard payload for {report['identity']['resolved_symbol']}.", 92, symbol)
    return report


async def run_job(job_id: str, payload: AnalysisRequest) -> None:
    try:
        emit(job_id, "interpret", "Reading your request and extracting the stocks you meant.", 4)
        request_context = await asyncio.to_thread(interpret_user_request, payload.query, payload.thoughts)
        symbols = request_context["symbols"]
        emit(
            job_id,
            "organize",
            f"Structured this as a {request_context['mode_label'].lower()} for {', '.join(symbols)}.",
            9,
        )
        if request_context["notes_highlights"]:
            emit(job_id, "thoughts", "Turned your notes into a cleaner stock-thinking checklist.", 12)

        reports = []
        per_symbol_start = 12
        per_symbol_span = 83 // max(len(symbols), 1)

        emit(job_id, "queue", f"Starting research run for {', '.join(symbols)}.", 14)
        for index, symbol in enumerate(symbols):
            base_progress = per_symbol_start + (index * per_symbol_span)
            job_manager.publish(
                job_id,
                step="stock-start",
                message=f"Starting analysis for {symbol}.",
                progress=min(95, base_progress + 2),
                symbol=symbol,
            )
            report = await asyncio.to_thread(
                analyze_symbol_sync,
                job_id,
                symbol,
                payload.chart_interval,
                payload.include_tradingview_snapshot,
            )
            reports.append(report)
            job_manager.publish(
                job_id,
                step="stock-complete",
                message=f"Completed analysis for {report['identity']['resolved_symbol']}.",
                progress=min(95, base_progress + per_symbol_span),
                symbol=report["identity"]["resolved_symbol"],
            )

        comparison = build_comparison(reports, request_context)
        emit(job_id, "compare", "Built the comparison view and ranking summary.", 97 if len(reports) > 1 else 95)
        result = serialize(
            {
                "request": {
                    "symbols": request_context["symbols"],
                    "interval": payload.chart_interval,
                    "include_tradingview_snapshot": payload.include_tradingview_snapshot,
                    "query": payload.query,
                    "thoughts": payload.thoughts,
                },
                "request_context": request_context,
                "reports": reports,
                "comparison": comparison,
            }
        )
        job_manager.complete(job_id, result)
    except ValueError as exc:
        job_manager.fail(job_id, str(exc))
    except MarketDataError as exc:
        job_manager.fail(job_id, str(exc))
    except Exception as exc:  # pragma: no cover - top-level guard
        job_manager.fail(job_id, f"Unexpected analysis failure: {exc}")


@app.post("/api/analyze")
async def analyze(payload: AnalysisRequest) -> JSONResponse:
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Please enter a stock prompt or symbol list.")

    try:
        interpret_user_request(payload.query, payload.thoughts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = job_manager.create()
    asyncio.create_task(run_job(job.id, payload))
    return JSONResponse({"job_id": job.id, "status": job.status})


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str) -> JSONResponse:
    job = job_manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return JSONResponse(job.snapshot())


@app.get("/api/jobs/{job_id}/events")
async def job_events(job_id: str) -> StreamingResponse:
    if not job_manager.get(job_id):
        raise HTTPException(status_code=404, detail="Job not found.")

    async def event_generator() -> Any:
        index = 0
        while True:
            job = job_manager.get(job_id)
            if not job:
                break

            while index < len(job.events):
                payload = json.dumps(job.events[index])
                yield f"data: {payload}\n\n"
                index += 1

            if job.status in {"completed", "failed"}:
                terminal = json.dumps(
                    {
                        "kind": "terminal",
                        "status": job.status,
                        "progress": job.progress,
                        "error": job.error,
                        "result": job.result,
                    }
                )
                yield f"data: {terminal}\n\n"
                break

            await asyncio.sleep(0.35)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
