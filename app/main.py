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
from app.services.analysis_engine import build_comparison, build_report
from app.services.auth_service import (
    SESSION_COOKIE,
    auth_status_snapshot,
    bootstrap_auth_state,
    get_session_from_request,
    login_user,
    logout_payload,
)
from app.services.app_state import app_state_store, utc_now
from app.services.kite_bridge import kite_bridge
from app.services.knowledge_registry import knowledge_registry
from app.services.market_data import MarketDataError, collect_stock_data, market_data_status
from app.services.portfolio_service import build_portfolio_insights
from app.services.infrastructure_status import infrastructure_status
from app.services.request_intelligence import interpret_user_request
from app.services.tradingview_bridge import tradingview_bridge
from app.models import (
    AnalysisRequest,
    AuthSessionRequest,
    FeedbackCreateRequest,
    KiteChoiceRequest,
    WatchlistCreateRequest,
)


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
    provider_status = market_data_status()
    session = get_session_from_request(request)
    bootstrap_data = {
        "auth": bootstrap_auth_state(request),
        "session": session,
        "market_data": provider_status,
        "tradingview": tradingview_bridge.status(),
        "knowledge": knowledge_registry.summary(),
        "infrastructure": infrastructure_status(),
        "kite": kite_bridge.status(session),
        "search_history": app_state_store.get_search_history(session["uid"]) if session else [],
        "watchlist": app_state_store.get_watchlist(session["uid"]) if session else [],
    }
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": settings.app_title,
            "tradingview_enabled": settings.tradingview_enabled or settings.tradingview_desktop_enabled,
            "tradingview_configured": tradingview_bridge.status()["available"],
            "market_data_status": provider_status,
            "market_data_order_label": " -> ".join(provider_status["order"]),
            "auth_state": bootstrap_auth_state(request),
            "session_user": session,
            "knowledge_summary": knowledge_registry.summary(),
            "infrastructure_status": infrastructure_status(),
            "bootstrap_data": bootstrap_data,
        },
    )


@app.get("/health")
async def health() -> Dict[str, Any]:
    storage = app_state_store.storage_status()
    return {
        "status": "ok",
        "app": settings.app_title,
        "tradingview": tradingview_bridge.status(),
        "market_data": market_data_status(),
        "kite": kite_bridge.status(),
        "auth": auth_status_snapshot(),
        "storage": storage,
        "knowledge": knowledge_registry.summary(),
        "infrastructure": infrastructure_status(),
    }


def emit(job_id: str, step: str, message: str, progress: int, symbol: str | None = None) -> None:
    job_manager.publish(
        job_id,
        step=step,
        message=message,
        progress=progress,
        symbol=symbol,
    )


@app.get("/api/bootstrap")
async def bootstrap(request: Request) -> Dict[str, Any]:
    session = get_session_from_request(request)
    user = app_state_store.get_user(session["uid"]) if session else None
    return {
        "session": user,
        "auth": bootstrap_auth_state(request),
        "market_data": market_data_status(),
        "tradingview": tradingview_bridge.status(),
        "knowledge": knowledge_registry.summary(),
        "infrastructure": infrastructure_status(),
        "kite": kite_bridge.status(user),
        "search_history": app_state_store.get_search_history(user["uid"]) if user else [],
        "watchlist": app_state_store.get_watchlist(user["uid"]) if user else [],
    }


@app.post("/api/auth/session")
async def create_auth_session(payload: AuthSessionRequest) -> JSONResponse:
    login = login_user(payload.model_dump())
    response = JSONResponse({"user": login["user"], "verified": login["verified"], "timestamp": login["timestamp"]})
    response.set_cookie(SESSION_COOKIE, login["session_cookie"], httponly=True, samesite="lax", secure=False, max_age=14 * 24 * 3600)
    return response


@app.post("/api/auth/logout")
async def logout() -> JSONResponse:
    response = JSONResponse(logout_payload())
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.post("/api/onboarding/kite-choice")
async def set_kite_choice(payload: KiteChoiceRequest, request: Request) -> JSONResponse:
    session = get_session_from_request(request)
    if not session:
        raise HTTPException(status_code=401, detail="Please log in first.")
    step = "kite-connect" if payload.is_kite_user else "dashboard"
    user = app_state_store.update_user_fields(session["uid"], isKiteUser=payload.is_kite_user, onboardingStep=step)
    return JSONResponse({"user": user, "kite": kite_bridge.status(user)})


@app.post("/api/onboarding/complete")
async def complete_onboarding(request: Request) -> JSONResponse:
    session = get_session_from_request(request)
    if not session:
        raise HTTPException(status_code=401, detail="Please log in first.")
    user = app_state_store.update_user_fields(session["uid"], onboardingStep="dashboard")
    return JSONResponse({"user": user})


@app.get("/api/kite/status")
async def kite_status(request: Request) -> JSONResponse:
    user = get_session_from_request(request)
    return JSONResponse(kite_bridge.status(user))


@app.post("/api/kite/connect")
async def kite_connect(request: Request) -> JSONResponse:
    user = get_session_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first.")
    payload = kite_bridge.connect(user)
    return JSONResponse(
        {
            "kite": kite_bridge.status(app_state_store.get_user(user["uid"]) or user),
            "connect": payload,
        }
    )


@app.get("/api/kite/search")
async def kite_search(query: str, request: Request) -> JSONResponse:
    user = get_session_from_request(request)
    return JSONResponse({"kite": kite_bridge.status(user), "result": kite_bridge.search_instruments(query, user)})


@app.get("/api/portfolio")
async def portfolio(request: Request) -> JSONResponse:
    user = get_session_from_request(request)
    if not user:
        raise HTTPException(status_code=401, detail="Please log in first.")
    holdings = kite_bridge.get_holdings(user)
    positions = kite_bridge.get_positions(user)
    insights = build_portfolio_insights(holdings.get("payload", {}), positions.get("payload", {}))
    if insights.get("available"):
        app_state_store.store_portfolio_snapshot(
            user["uid"],
            "kite_mcp",
            holdings.get("payload", {}),
            positions.get("payload", {}),
            insights.get("summary", {}),
        )
    return JSONResponse(
        {
            "kite": kite_bridge.status(user),
            "holdings_status": holdings,
            "positions_status": positions,
            "insights": insights,
        }
    )


@app.get("/api/search-history")
async def search_history(request: Request) -> JSONResponse:
    session = get_session_from_request(request)
    if not session:
        return JSONResponse({"items": []})
    return JSONResponse({"items": app_state_store.get_search_history(session["uid"])})


@app.get("/api/watchlist")
async def watchlist(request: Request) -> JSONResponse:
    session = get_session_from_request(request)
    if not session:
        return JSONResponse({"items": []})
    return JSONResponse({"items": app_state_store.get_watchlist(session["uid"])})


@app.post("/api/watchlist")
async def create_watchlist_item(payload: WatchlistCreateRequest, request: Request) -> JSONResponse:
    session = get_session_from_request(request)
    if not session:
        raise HTTPException(status_code=401, detail="Please log in first.")
    items = app_state_store.add_watchlist_item(session["uid"], payload.symbol, payload.note)
    return JSONResponse({"items": items})


@app.post("/api/feedback")
async def create_feedback(payload: FeedbackCreateRequest, request: Request) -> JSONResponse:
    session = get_session_from_request(request)
    stored = app_state_store.store_feedback_local(
        {
            "message": payload.message,
            "route": payload.route,
            "metadata": payload.metadata,
            "user_id": session["uid"] if session else None,
            "is_kite_user": bool(session and session.get("isKiteUser")),
        }
    )
    return JSONResponse(
        {
            "stored": stored,
            "firestore_enabled": settings.feedback_firestore_enabled,
            "message": "Stored locally. Firestore delivery is ready for configuration." if settings.feedback_firestore_enabled else "Stored locally until Firestore is configured.",
        }
    )


@app.get("/api/knowledge")
async def knowledge() -> JSONResponse:
    return JSONResponse({"summary": knowledge_registry.summary(), "sources": knowledge_registry.sources()})


def analyze_symbol_sync(
    job_id: str,
    symbol: str,
    interval: str,
    include_snapshot: bool,
    request_context: Dict[str, Any] | None = None,
    user: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    emit(job_id, "providers", f"Checking market data providers in order: {' -> '.join(market_data_status()['order'])}.", 4, symbol)
    emit(job_id, "resolve", f"Resolving live symbol for {symbol}.", 6, symbol)
    stock = collect_stock_data(symbol, user=user)
    emit(
        job_id,
        "market-source",
        f"Using {stock['market_context']['quote_provider_label']} as the live quote source for {stock['resolved_symbol']}.",
        12,
        symbol,
    )
    emit(job_id, "market", f"Fetched market profile and price history for {stock['resolved_symbol']}.", 18, symbol)
    emit(job_id, "technicals", f"Computed technical indicators for {stock['resolved_symbol']}.", 34, symbol)
    emit(job_id, "fundamentals", f"Built the fundamentals snapshot for {stock['resolved_symbol']}.", 48, symbol)
    emit(job_id, "news", f"Pulled recent headline context for {stock['resolved_symbol']}.", 58, symbol)

    report = build_report(stock, request_context=request_context)
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


async def run_job(job_id: str, payload: AnalysisRequest, user: Dict[str, Any] | None = None) -> None:
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
                request_context,
                user,
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
        if user:
            app_state_store.record_search(
                user["uid"],
                {
                    "query": payload.query,
                    "thoughts": payload.thoughts,
                    "mode": request_context["mode"],
                    "symbols": request_context["symbols"],
                    "timestamp": utc_now(),
                },
            )
        job_manager.complete(job_id, result)
    except ValueError as exc:
        job_manager.fail(job_id, str(exc))
    except MarketDataError as exc:
        job_manager.fail(job_id, str(exc))
    except Exception as exc:  # pragma: no cover - top-level guard
        job_manager.fail(job_id, f"Unexpected analysis failure: {exc}")


@app.post("/api/analyze")
async def analyze(payload: AnalysisRequest, request: Request) -> JSONResponse:
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Please enter a stock prompt or symbol list.")

    try:
        interpret_user_request(payload.query, payload.thoughts)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    job = job_manager.create()
    asyncio.create_task(run_job(job.id, payload, user=get_session_from_request(request)))
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
