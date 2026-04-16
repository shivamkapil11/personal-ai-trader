from __future__ import annotations

from typing import Any, Dict, List


def pill(value: str, label: str) -> Dict[str, str]:
    return {"tone": value, "label": label}


def numeric_or_default(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def score_swing(stock: Dict[str, Any]) -> Dict[str, Any]:
    t = stock["technicals"]
    f = stock["fundamentals"]
    score = 0
    reasons: List[str] = []

    trend_points = 0
    for key, points, reason in [
        ("trend_daily", 9, "Daily trend is constructive."),
        ("trend_weekly", 9, "Weekly trend supports follow-through."),
        ("trend_monthly", 5, "Longer trend is aligned."),
    ]:
        if t.get(key) == "bullish":
            trend_points += points
            reasons.append(reason)
    score += min(trend_points, 25)

    if t.get("rsi14") is not None:
        if 55 <= t["rsi14"] <= 70:
            score += 8
            reasons.append("RSI is strong without being overheated.")
        elif 45 <= t["rsi14"] < 55:
            score += 4
    if t.get("macd") is not None and t.get("macd_signal") is not None and t["macd"] > t["macd_signal"]:
        score += 6
        reasons.append("MACD is above signal.")
    if t.get("stochastic_k") is not None and t["stochastic_k"] >= 70:
        score += 3
    if t.get("relative_strength_60d") is not None and t["relative_strength_60d"] > 0:
        score += 3
        reasons.append("Relative strength versus the benchmark is positive.")

    if all(
        t.get(field) is not None
        for field in ["current_price", "ema20", "ema50", "ema200"]
    ):
        if t["current_price"] > t["ema20"] > t["ema50"] > t["ema200"]:
            score += 12
            reasons.append("Price is stacked above key EMAs.")

    if t.get("volume_ratio_5v20") is not None:
        if t["volume_ratio_5v20"] >= 1.1:
            score += 7
            reasons.append("Recent volume is expanding.")
        elif t["volume_ratio_5v20"] >= 0.95:
            score += 4

    if all(t.get(field) is not None for field in ["current_price", "resistance_1", "support_1", "atr14"]):
        distance_to_resistance = abs(t["resistance_1"] - t["current_price"])
        if distance_to_resistance <= max(t["atr14"], 0.01) * 1.5:
            score += 6
            reasons.append("Price is close to a breakout trigger.")
        if t["current_price"] - t["support_1"] <= max(t["atr14"], 0.01) * 2:
            score += 6
            reasons.append("Support is visible enough to define risk.")

    if f.get("financial_status") != "weakening":
        score += 8
    if f.get("debt_to_equity") is not None and f["debt_to_equity"] < 160:
        score += 2

    return {
        "score": min(score, 100),
        "tier": "strong" if score >= 75 else "watch" if score >= 60 else "weak",
        "reasons": reasons[:5],
    }


def score_long_term(stock: Dict[str, Any]) -> Dict[str, Any]:
    f = stock["fundamentals"]
    score = 0
    reasons: List[str] = []

    if f.get("profit_margin") is not None:
        if f["profit_margin"] >= 20:
            score += 10
            reasons.append("Profit margins are healthy.")
        elif f["profit_margin"] >= 10:
            score += 6

    if f.get("operating_margin") is not None:
        if f["operating_margin"] >= 18:
            score += 8
            reasons.append("Operating margin profile is supportive.")
        elif f["operating_margin"] >= 10:
            score += 4

    if f.get("revenue_growth") is not None:
        if f["revenue_growth"] >= 10:
            score += 10
            reasons.append("Revenue growth is solid.")
        elif f["revenue_growth"] >= 4:
            score += 6

    if f.get("earnings_growth") is not None:
        if f["earnings_growth"] >= 10:
            score += 10
            reasons.append("Earnings growth is supportive.")
        elif f["earnings_growth"] >= 4:
            score += 6

    if f.get("roe") is not None:
        if f["roe"] >= 15:
            score += 8
            reasons.append("ROE is attractive.")
        elif f["roe"] >= 10:
            score += 4

    if f.get("roce") is not None:
        if f["roce"] >= 12:
            score += 7
            reasons.append("ROCE indicates good capital productivity.")
        elif f["roce"] >= 8:
            score += 3

    if f.get("debt_to_equity") is not None:
        if f["debt_to_equity"] <= 80:
            score += 8
        elif f["debt_to_equity"] <= 160:
            score += 5
        else:
            score += 2

    if f.get("free_cash_flow") is not None and f["free_cash_flow"] > 0:
        score += 8
        reasons.append("Free cash flow is positive.")
    elif f.get("operating_cash_flow") is not None and f["operating_cash_flow"] > 0:
        score += 4

    if f.get("dividend_yield") is not None and f["dividend_yield"] >= 2:
        score += 4
        reasons.append("Dividend yield adds carry while you hold.")

    if f.get("trailing_pe") is not None:
        if f["trailing_pe"] <= 18:
            score += 8
        elif f["trailing_pe"] <= 25:
            score += 5
        elif f["trailing_pe"] <= 35:
            score += 2

    governance_risk = f.get("overall_governance_risk")
    if governance_risk is not None:
        if governance_risk <= 3:
            score += 7
            reasons.append("Governance risk metrics are reasonable.")
        elif governance_risk <= 6:
            score += 4
    else:
        score += 4

    return {
        "score": min(score, 100),
        "tier": "strong" if score >= 75 else "watch" if score >= 60 else "weak",
        "reasons": reasons[:5],
    }


def build_swing_plan(stock: Dict[str, Any], swing_score: int) -> Dict[str, Any]:
    t = stock["technicals"]
    if swing_score < 60 or any(t.get(field) is None for field in ["current_price", "atr14", "support_1", "resistance_1"]):
        return {
            "qualifies": False,
            "why_not": "Setup is not clean enough for a defined swing entry yet.",
        }

    atr = max(t["atr14"], 0.01)
    current = t["current_price"]
    support = t["support_1"]
    resistance = t["resistance_1"]
    breakout_bias = current >= resistance * 0.98

    if breakout_bias:
        entry_low = round(resistance, 2)
        entry_high = round(resistance + atr * 0.5, 2)
        stop_loss = round(max(support, resistance - atr * 1.6), 2)
        target_1 = round(entry_high + atr * 1.8, 2)
        target_2 = round(entry_high + atr * 3.2, 2)
    else:
        entry_low = round(max(support, current - atr * 0.8), 2)
        entry_high = round(current, 2)
        stop_loss = round(max(0.01, support - atr * 0.8), 2)
        target_1 = round(resistance, 2)
        target_2 = round(resistance + atr * 2.2, 2)

    expected_return = round(((target_1 + target_2) / 2 / max(entry_high, 0.01) - 1) * 100, 2)
    risk = max(entry_high - stop_loss, 0.01)
    reward = max(((target_1 + target_2) / 2) - entry_high, 0.01)

    return {
        "qualifies": True,
        "entry_zone": f"{entry_low} - {entry_high}",
        "stop_loss": stop_loss,
        "target_1": target_1,
        "target_2": target_2,
        "expected_return_pct": expected_return,
        "holding_period": "2-6 weeks",
        "technical_reason": "Trend, EMA alignment, and momentum keep the setup actionable.",
        "invalidation": f"Breakdown below {stop_loss} or failed hold after trigger.",
        "probability": "High" if swing_score >= 78 else "Medium",
        "risk_reward_ratio": round(reward / risk, 2),
    }


def build_risks(stock: Dict[str, Any], label: str) -> Dict[str, Any]:
    f = stock["fundamentals"]
    t = stock["technicals"]
    risks = []
    risk_score = 4

    if f.get("debt_to_equity") is not None and f["debt_to_equity"] > 150:
        risks.append("Leverage is elevated enough to deserve monitoring.")
        risk_score += 2
    if f.get("trailing_pe") is not None and f["trailing_pe"] > 30:
        risks.append("Valuation leaves less room for execution misses.")
        risk_score += 1
    if t.get("rsi14") is not None and t["rsi14"] > 72:
        risks.append("Momentum is getting stretched in the short term.")
        risk_score += 1
    if t.get("support_1") is not None and t.get("current_price") is not None and t["support_1"] < t["current_price"] * 0.93:
        risks.append("Nearest chart support is not especially tight.")
        risk_score += 1
    if f.get("financial_status") == "weakening":
        risks.append("Recent growth trends look weaker than ideal.")
        risk_score += 2

    if not risks:
        risks.append("Normal market volatility and sector rotation remain the main risks.")

    return {
        "items": risks,
        "rating": min(risk_score, 10),
        "downside_scenario": "A softer tape, earnings miss, or failed breakout could push the stock back toward lower support zones.",
    }


def pick_label(swing_score: int, long_term_score: int) -> str:
    if long_term_score >= 70 and long_term_score >= swing_score - 8:
        return "Long-Term Investment"
    if swing_score >= 75 and swing_score > long_term_score + 8:
        return "Swing Trade"
    if max(swing_score, long_term_score) >= 60:
        return "Watchlist"
    return "Avoid for now"


def confidence_level(label: str, conviction: float) -> str:
    if label in {"Long-Term Investment", "Swing Trade"} and conviction >= 8:
        return "High"
    if conviction >= 6:
        return "Medium"
    return "Low"


def build_report(stock: Dict[str, Any]) -> Dict[str, Any]:
    swing = score_swing(stock)
    long_term = score_long_term(stock)
    label = pick_label(swing["score"], long_term["score"])
    risks = build_risks(stock, label)
    swing_plan = build_swing_plan(stock, swing["score"])
    market_context = stock.get("market_context", {})

    conviction = round(
        max(1.0, min(10.0, ((max(swing["score"], long_term["score"]) * 0.6) + ((10 - risks["rating"]) * 10 * 0.4)) / 10)),
        1,
    )

    t = stock["technicals"]
    f = stock["fundamentals"]
    trend = t.get("trend_daily", "neutral")

    decision_reasons = []
    if label == "Long-Term Investment":
        decision_reasons = long_term["reasons"][:4] or [
            "Business quality and balance sheet profile are stronger than the near-term trading setup."
        ]
    elif label == "Swing Trade":
        decision_reasons = swing["reasons"][:4] or [
            "Technicals are stronger than the longer-duration business case right now."
        ]
    elif label == "Watchlist":
        decision_reasons = [
            "The story is interesting, but either timing or valuation still needs work.",
            "Wait for cleaner confirmation before treating it as a high-conviction position.",
        ]
    else:
        decision_reasons = [
            "The current mix of fundamentals and setup quality does not provide a clean edge.",
            "Preserving capital looks better than forcing a trade here.",
        ]

    long_term_base = max(8, round(long_term["score"] * 0.32, 1))
    long_term_bull = round(long_term_base + 12, 1)
    long_term_bear = round(-min(18, risks["rating"] * 2.0), 1)

    return {
        "identity": {
            "input_symbol": stock["input_symbol"],
            "resolved_symbol": stock["resolved_symbol"],
            "company_name": stock["company_name"],
            "currency": stock["currency"],
            "tradingview_symbol": stock["tradingview_symbol"],
            "quote_provider_label": market_context.get("quote_provider_label"),
        },
        "summary": {
            "current_price": t.get("current_price"),
            "market_cap": f.get("market_cap"),
            "sector": f.get("sector"),
            "industry": f.get("industry"),
            "fifty_two_week_high": t.get("fifty_two_week_high"),
            "fifty_two_week_low": t.get("fifty_two_week_low"),
            "trend_status": trend,
            "trend_pill": pill(
                "green" if trend == "bullish" else "yellow" if trend == "neutral" else "red",
                trend.title(),
            ),
            "decision": label,
            "decision_pill": pill(
                "green" if label in {"Long-Term Investment", "Swing Trade"} else "yellow" if label == "Watchlist" else "red",
                label,
            ),
            "quote_source": market_context.get("quote_provider_label", "Unknown"),
            "conviction_score": conviction,
            "confidence_level": confidence_level(label, conviction),
        },
        "decision": {
            "label": label,
            "reasons": decision_reasons,
            "swing_score": swing["score"],
            "long_term_score": long_term["score"],
        },
        "technicals": t,
        "fundamentals": f,
        "market_context": market_context,
        "swing_plan": swing_plan,
        "long_term_view": {
            "qualifies": label == "Long-Term Investment" or long_term["score"] >= 70,
            "thesis": "Business quality, financial resilience, and trend support make the stock fit better as a multi-quarter idea."
            if label == "Long-Term Investment"
            else "The long-term thesis is present but not strong enough yet to outrank timing or valuation concerns.",
            "business_quality": "Strong" if long_term["score"] >= 75 else "Mixed" if long_term["score"] >= 60 else "Weak",
            "growth_drivers": long_term["reasons"][:3],
            "valuation_comfort": "Comfortable" if (f.get("trailing_pe") or 99) <= 22 else "Fair" if (f.get("trailing_pe") or 99) <= 32 else "Tight",
            "expected_return_1_3y": long_term_base,
        },
        "risks": risks,
        "return_framework": {
            "swing_return_pct": swing_plan.get("expected_return_pct") if swing_plan.get("qualifies") else None,
            "long_term_return_pct": long_term_base,
            "bull_case_pct": long_term_bull,
            "base_case_pct": long_term_base,
            "bear_case_pct": long_term_bear,
            "estimated_total_return_range": f"{long_term_bear}% to {long_term_bull}%",
            "risk_reward_ratio": swing_plan.get("risk_reward_ratio") if swing_plan.get("qualifies") else None,
        },
        "news": stock["news"],
        "snapshot": None,
    }


def score_prompt_fit(report: Dict[str, Any], request_context: Dict[str, Any]) -> float:
    decision = report["decision"]
    fundamentals = report["fundamentals"]
    risks = report["risks"]
    focus_areas = set(request_context.get("focus_areas", []))
    horizon = request_context.get("time_horizon")
    score = 0.0

    if horizon == "swing":
        score += decision["swing_score"] * 0.7
    elif horizon == "long-term":
        score += decision["long_term_score"] * 0.7
    else:
        score += (decision["swing_score"] + decision["long_term_score"]) * 0.35

    if "valuation" in focus_areas:
        trailing_pe = numeric_or_default(fundamentals.get("trailing_pe"), 32)
        score += max(0.0, 18.0 - min(trailing_pe, 50.0) / 2.5)
    if "dividends" in focus_areas:
        score += min(numeric_or_default(fundamentals.get("dividend_yield")) * 2.6, 12.0)
    if "technicals" in focus_areas:
        score += decision["swing_score"] * 0.18
    if focus_areas.intersection({"fundamentals", "business_quality", "management", "sector"}):
        score += decision["long_term_score"] * 0.18
    if "risk" in focus_areas:
        score += max(0.0, (10 - numeric_or_default(risks.get("rating"), 10)) * 1.5)
    if "news" in focus_areas:
        score += 4.0

    return round(score, 1)


def build_comparison(reports: List[Dict[str, Any]], request_context: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if len(reports) <= 1:
        return {}

    table = []
    for report in reports:
        row = {
            "symbol": report["identity"]["resolved_symbol"],
            "company": report["identity"]["company_name"],
            "decision": report["summary"]["decision"],
            "price": report["summary"]["current_price"],
            "trend": report["summary"]["trend_status"],
            "conviction": report["summary"]["conviction_score"],
            "swing_score": report["decision"]["swing_score"],
            "long_term_score": report["decision"]["long_term_score"],
            "risk_rating": report["risks"]["rating"],
            "dividend_yield": report["fundamentals"].get("dividend_yield"),
            "trailing_pe": report["fundamentals"].get("trailing_pe"),
            "revenue_growth": report["fundamentals"].get("revenue_growth"),
            "earnings_growth": report["fundamentals"].get("earnings_growth"),
        }
        if request_context:
            row["prompt_fit_score"] = score_prompt_fit(report, request_context)
        table.append(row)

    top_long_term = max(reports, key=lambda item: item["decision"]["long_term_score"])
    top_swing = max(reports, key=lambda item: item["decision"]["swing_score"])
    lowest_risk = min(reports, key=lambda item: item["risks"]["rating"])

    summary = {
        "best_long_term": top_long_term["identity"]["resolved_symbol"],
        "best_swing": top_swing["identity"]["resolved_symbol"],
        "lowest_risk": lowest_risk["identity"]["resolved_symbol"],
    }
    if request_context:
        best_fit = max(reports, key=lambda item: score_prompt_fit(item, request_context))
        summary["best_fit_for_prompt"] = best_fit["identity"]["resolved_symbol"]

    return {
        "table": table,
        "summary": summary,
    }
