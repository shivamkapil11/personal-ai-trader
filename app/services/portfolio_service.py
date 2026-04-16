from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from app.services.analysis_engine import build_report
from app.services.market_data import MarketDataError, collect_stock_data


def _numeric(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _holding_symbol(item: Dict[str, Any]) -> str:
    exchange = item.get("exchange") or item.get("exchange_segment") or "NSE"
    symbol = item.get("tradingsymbol") or item.get("symbol") or ""
    if ":" in symbol:
        return symbol
    return f"{exchange}:{symbol}".upper()


def _normalize_holdings(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    items = payload.get("holdings") or payload.get("data") or []
    normalized = []
    for item in items:
        quantity = _numeric(item.get("quantity") or item.get("t1_quantity") or item.get("used_quantity"), 0.0)
        last_price = _numeric(item.get("last_price") or item.get("lastPrice") or item.get("ltp"))
        average_price = _numeric(item.get("average_price") or item.get("averagePrice") or item.get("avg_price"))
        pnl = _numeric(item.get("pnl"), (last_price - average_price) * quantity)
        normalized.append(
            {
                "symbol": _holding_symbol(item),
                "quantity": quantity,
                "last_price": last_price,
                "average_price": average_price,
                "market_value": _numeric(item.get("market_value"), last_price * quantity),
                "pnl": pnl,
                "raw": item,
            }
        )
    return normalized


def _normalize_positions(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not payload:
        return []
    if isinstance(payload.get("data"), dict):
        combined = []
        for group in payload["data"].values():
            if isinstance(group, list):
                combined.extend(group)
        items = combined
    else:
        items = payload.get("data") or payload.get("positions") or []
    normalized = []
    for item in items:
        normalized.append(
            {
                "symbol": _holding_symbol(item),
                "quantity": _numeric(item.get("quantity"), 0.0),
                "pnl": _numeric(item.get("pnl"), 0.0),
                "product": item.get("product"),
                "raw": item,
            }
        )
    return normalized


def build_portfolio_insights(holdings_payload: Dict[str, Any], positions_payload: Dict[str, Any]) -> Dict[str, Any]:
    holdings = _normalize_holdings(holdings_payload)
    positions = _normalize_positions(positions_payload)
    if not holdings and not positions:
        return {
            "available": False,
            "message": "No Kite holdings or positions are available yet.",
        }

    total_value = sum(item["market_value"] for item in holdings)
    total_pnl = sum(item["pnl"] for item in holdings) + sum(item["pnl"] for item in positions)
    top_holdings = sorted(holdings, key=lambda item: item["market_value"], reverse=True)[:5]
    top_gainers = sorted(holdings, key=lambda item: item["pnl"], reverse=True)[:5]
    top_losers = sorted(holdings, key=lambda item: item["pnl"])[:5]
    concentration = max((item["market_value"] / total_value) for item in holdings) * 100 if total_value else 0.0

    sector_allocation: Dict[str, float] = defaultdict(float)
    conviction_items = []
    risk_flags = []

    for item in holdings[:12]:
        try:
            stock = collect_stock_data(item["symbol"])
        except MarketDataError:
            continue
        report = build_report(stock)
        sector = stock["fundamentals"].get("sector") or "Unknown"
        sector_allocation[sector] += item["market_value"]
        conviction_items.append(
            {
                "symbol": report["identity"]["resolved_symbol"],
                "label": report["decision"]["label"],
                "conviction": report["summary"]["conviction_score"],
                "risk_rating": report["risks"]["rating"],
            }
        )
        if report["risks"]["rating"] >= 7:
            risk_flags.append(f"{report['identity']['resolved_symbol']} looks high-risk on the current model.")
        if report["decision"]["label"] == "Swing Trade":
            risk_flags.append(f"{report['identity']['resolved_symbol']} behaves more like a swing candidate than a core hold.")

    sector_view = [
        {
            "sector": sector,
            "value": round(value, 2),
            "weight_pct": round((value / total_value) * 100, 2) if total_value else 0.0,
        }
        for sector, value in sorted(sector_allocation.items(), key=lambda item: item[1], reverse=True)
    ]

    diversification = "Diversified" if len(sector_view) >= 5 and concentration < 25 else "Needs work"
    concentration_risk = "High" if concentration >= 30 else "Medium" if concentration >= 20 else "Low"

    return {
        "available": True,
        "summary": {
            "total_value": round(total_value, 2),
            "total_pnl": round(total_pnl, 2),
            "holdings_count": len(holdings),
            "positions_count": len(positions),
            "diversification_view": diversification,
            "concentration_risk": concentration_risk,
            "top_position_weight_pct": round(concentration, 2),
        },
        "sector_allocation": sector_view,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "top_holdings": top_holdings,
        "classification": {
            "high_risk": [item for item in conviction_items if item["risk_rating"] >= 7],
            "stable": [item for item in conviction_items if item["risk_rating"] <= 4],
            "swing_like": [item for item in conviction_items if item["label"] == "Swing Trade"],
            "long_term_like": [item for item in conviction_items if item["label"] == "Long-Term Investment"],
        },
        "risk_summary": risk_flags[:10] or ["Portfolio risk looks acceptable on the current snapshot."],
        "conviction_insights": conviction_items[:10],
    }
