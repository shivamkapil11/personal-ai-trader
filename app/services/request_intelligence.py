from __future__ import annotations

import re
from typing import Any, Dict, List

import yfinance as yf


COMPARE_PATTERN = re.compile(r"\b(compare|vs|versus|against|better than)\b", re.IGNORECASE)
EXPLICIT_SYMBOL_PATTERN = re.compile(r"\b(?:NSE|BSE|NASDAQ|NYSE):[A-Z0-9._-]+\b", re.IGNORECASE)
CLAUSE_SPLIT_PATTERN = re.compile(
    r"\b(?:for|with|based on|looking at|focus on|focusing on|showing|show|and tell me|where|whether|which|because)\b",
    re.IGNORECASE,
)
LEADING_FILLER_PATTERN = re.compile(
    r"^(?:please\s+)?(?:compare|analyse|analyze|review|research|evaluate|check|study|look at|look into|show me|tell me about|help me with|i want to compare|i want to analyze|should i buy|can you review)\s+",
    re.IGNORECASE,
)

STOPWORDS = {
    "A",
    "AN",
    "AND",
    "ARE",
    "AS",
    "AT",
    "BETWEEN",
    "BUY",
    "CAN",
    "CHECK",
    "COMPARE",
    "DO",
    "FOR",
    "GET",
    "GIVE",
    "HELP",
    "I",
    "IN",
    "INTO",
    "IS",
    "IT",
    "LOOK",
    "ME",
    "OF",
    "ON",
    "OR",
    "PLEASE",
    "RESEARCH",
    "REVIEW",
    "SETUP",
    "SHOULD",
    "SHOW",
    "STOCK",
    "STOCKS",
    "TELL",
    "THE",
    "THESE",
    "THIS",
    "TO",
    "VS",
    "VERSUS",
    "WHAT",
    "WHICH",
    "WITH",
}

FOCUS_KEYWORDS = {
    "valuation": {"valuation", "cheap", "expensive", "overvalued", "undervalued", "margin of safety", "pe", "p/e", "pb", "price to book"},
    "dividends": {"dividend", "yield", "payout", "income"},
    "technicals": {"technical", "technicals", "chart", "breakout", "breakdown", "support", "resistance", "rsi", "macd", "stochastic", "ema", "sma", "momentum", "trend"},
    "fundamentals": {"fundamental", "fundamentals", "revenue", "profit", "earnings", "margin", "roe", "roce", "debt", "cash flow", "balance sheet"},
    "business_quality": {"business", "quality", "moat", "competitive advantage", "runway", "durable", "future potential"},
    "management": {"management", "promoter", "capital allocation", "governance", "leadership", "insider"},
    "risk": {"risk", "downside", "avoid", "watchlist", "uncertain", "volatility", "drawdown"},
    "news": {"news", "announcement", "announcements", "results", "trigger", "commentary", "event"},
    "sector": {"sector", "industry", "tailwind", "tailwinds", "cycle", "market opportunity"},
}

SWING_KEYWORDS = {"swing", "trade", "trading", "setup", "breakout", "momentum", "short term", "2 weeks", "4 weeks", "6 weeks"}
LONG_TERM_KEYWORDS = {"long term", "long-term", "investment", "1 year", "2 year", "3 year", "compound", "multiyear", "multi-year", "hold"}

FOCUS_LABELS = {
    "valuation": "Valuation",
    "dividends": "Dividends",
    "technicals": "Technicals",
    "fundamentals": "Fundamentals",
    "business_quality": "Business Quality",
    "management": "Management",
    "risk": "Risk",
    "news": "News",
    "sector": "Sector",
}


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def clean_phrase(phrase: str) -> str:
    cleaned = phrase.strip().strip(".,:;/- ")
    cleaned = LEADING_FILLER_PATTERN.sub("", cleaned)
    cleaned = CLAUSE_SPLIT_PATTERN.split(cleaned, maxsplit=1)[0]
    cleaned = re.sub(r"\b(?:stock|stocks|share|shares)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .,:;/-")
    return cleaned


def candidate_phrases(text: str) -> List[str]:
    working = text.replace("\n", ",")
    working = re.sub(r"\b(?:vs|versus|against)\b", ",", working, flags=re.IGNORECASE)
    segments: List[str] = []
    for chunk in re.split(r"[,;/]+", working):
        for part in re.split(r"\band\b", chunk, flags=re.IGNORECASE):
            cleaned = clean_phrase(part)
            if cleaned:
                segments.append(cleaned)
    return segments


def ticker_like(phrase: str) -> bool:
    compact = phrase.replace(" ", "")
    return bool(re.fullmatch(r"(?:[A-Z]{1,6}:[A-Z0-9._-]{1,20}|[A-Z0-9._-]{1,15})", compact))


def score_quote(quote: Dict[str, Any], phrase: str) -> int:
    symbol = str(quote.get("symbol", "")).upper()
    exchange = str(quote.get("exchange", "")).upper()
    quote_type = str(quote.get("quoteType", "")).upper()
    phrase_upper = phrase.upper()
    score = 0
    if quote_type in {"EQUITY", "MUTUALFUND", "ETF"}:
        score += 4
    if exchange in {"NSI", "NSE"}:
        score += 6
    elif exchange in {"BSE"}:
        score += 5
    elif exchange in {"NMS", "NASDAQ"}:
        score += 4
    elif exchange in {"NYQ", "NYSE"}:
        score += 4
    if symbol == phrase_upper:
        score += 7
    if symbol.split(".")[0] == phrase_upper.replace(" ", ""):
        score += 5
    short_name = str(quote.get("shortname", "")).upper()
    long_name = str(quote.get("longname", "")).upper()
    if phrase_upper in short_name or phrase_upper in long_name:
        score += 3
    return score


def lookup_symbol(phrase: str) -> str | None:
    if not phrase:
        return None

    explicit = EXPLICIT_SYMBOL_PATTERN.search(phrase)
    if explicit:
        return normalize_symbol(explicit.group(0))

    cleaned = phrase.strip()
    compact = cleaned.replace(" ", "").upper()
    if ticker_like(compact) and compact not in STOPWORDS:
        return normalize_symbol(compact)

    try:
        search = yf.Search(cleaned, max_results=8)
        quotes = getattr(search, "quotes", []) or []
    except Exception:
        quotes = []

    ranked = sorted(quotes, key=lambda quote: score_quote(quote, cleaned), reverse=True)
    for quote in ranked:
        symbol = str(quote.get("symbol", "")).strip()
        if symbol:
            return normalize_symbol(symbol)
    return None


def dedupe(symbols: List[str]) -> List[str]:
    unique: List[str] = []
    for symbol in symbols:
        normalized = normalize_symbol(symbol)
        if normalized and normalized not in unique:
            unique.append(normalized)
    return unique


def extract_symbols_from_text(text: str) -> List[str]:
    symbols = [normalize_symbol(match.group(0)) for match in EXPLICIT_SYMBOL_PATTERN.finditer(text)]
    for phrase in candidate_phrases(text):
        symbol = lookup_symbol(phrase)
        if symbol:
            symbols.append(symbol)
    return dedupe(symbols)


def detect_focus_areas(text: str) -> List[str]:
    lowered = text.lower()
    focus_areas: List[str] = []
    for key, keywords in FOCUS_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            focus_areas.append(key)
    if not focus_areas:
        focus_areas = ["technicals", "fundamentals", "risk"]
    return focus_areas


def detect_time_horizon(text: str) -> str:
    lowered = text.lower()
    swing = any(keyword in lowered for keyword in SWING_KEYWORDS)
    long_term = any(keyword in lowered for keyword in LONG_TERM_KEYWORDS)
    if swing and long_term:
        return "mixed"
    if swing:
        return "swing"
    if long_term:
        return "long-term"
    return "balanced"


def summarize_notes(thoughts: str) -> List[str]:
    if not thoughts.strip():
        return []
    sentences = re.split(r"(?<=[.!?])\s+|\n+", thoughts.strip())
    highlights: List[str] = []
    for sentence in sentences:
        cleaned = sentence.strip(" -")
        if len(cleaned) >= 12 and cleaned not in highlights:
            highlights.append(cleaned)
        if len(highlights) == 4:
            break
    return highlights


def build_framework(mode: str, horizon: str, focus_areas: List[str]) -> Dict[str, List[str]]:
    steps = [
        "Start by separating the stock story from the stock price setup so business quality and timing do not get mixed together.",
        "Decide early whether the main goal is a swing, a long-term investment, or simply building a watchlist.",
    ]
    if mode == "compare":
        steps[1] = "Rank the names separately for swing quality, long-term quality, and risk instead of forcing one absolute winner."

    checklist = [
        "What is the main thesis in one sentence?",
        "What evidence would confirm the thesis over the next few weeks or quarters?",
        "What would invalidate the thesis and make the idea weaker?",
    ]

    if horizon in {"swing", "mixed"} or "technicals" in focus_areas:
        steps.append("Use the chart to define timing, entry zone, invalidation, and whether momentum is actually supporting the trade.")
        checklist.append("Is momentum aligned across daily, weekly, and support-resistance structure?")
    if horizon in {"long-term", "mixed", "balanced"} or any(area in focus_areas for area in {"fundamentals", "business_quality", "management"}):
        steps.append("Check whether the business can keep compounding through revenue, margins, ROE/ROCE, balance-sheet strength, and management quality.")
        checklist.append("Are the fundamentals improving enough to justify owning it beyond the current setup?")
    if "valuation" in focus_areas:
        steps.append("Ask whether the upside is still attractive after valuation, rather than assuming a good company is automatically a good buy.")
        checklist.append("How much optimism is already priced into the valuation?")
    if "risk" in focus_areas:
        steps.append("Write the downside case before the upside case so the risk-reward stays honest.")
        checklist.append("What is the most realistic downside scenario if the thesis is wrong?")

    return {"steps": steps[:5], "checklist": checklist[:6]}


def build_intent_summary(symbols: List[str], mode: str, horizon: str, focus_labels: List[str]) -> str:
    stock_text = ", ".join(symbols)
    mode_text = "compare" if mode == "compare" else "analyze"
    focus_text = ", ".join(focus_labels[:3]) if focus_labels else "core stock factors"
    if horizon == "balanced":
        return f"The engine will {mode_text} {stock_text} with a balanced lens across technicals, fundamentals, and risk."
    return f"The engine will {mode_text} {stock_text} with a {horizon} bias, while prioritizing {focus_text}."


def interpret_user_request(query: str, thoughts: str = "") -> Dict[str, Any]:
    query = query.strip()
    thoughts = thoughts.strip()
    combined = "\n".join(part for part in [query, thoughts] if part).strip()

    symbols = extract_symbols_from_text(query)
    if not symbols and thoughts:
        symbols = extract_symbols_from_text(thoughts)
    if not symbols:
        symbols = extract_symbols_from_text(combined)

    if not symbols:
        raise ValueError("I could not detect any stock symbols or company names from your request.")
    if len(symbols) > 3:
        raise ValueError("You can compare up to three stocks at a time.")

    mode = "compare" if len(symbols) > 1 else "single"
    horizon = detect_time_horizon(combined)
    focus_areas = detect_focus_areas(combined)
    focus_labels = [FOCUS_LABELS[item] for item in focus_areas]
    framework = build_framework(mode, horizon, focus_areas)
    notes_highlights = summarize_notes(thoughts)

    return {
        "raw_query": query,
        "raw_thoughts": thoughts,
        "symbols": symbols,
        "mode": mode,
        "mode_label": "Comparison Run" if mode == "compare" else "Single-Stock Run",
        "time_horizon": horizon,
        "time_horizon_label": "Balanced" if horizon == "balanced" else horizon.title(),
        "focus_areas": focus_areas,
        "focus_labels": focus_labels,
        "notes_highlights": notes_highlights,
        "intent_summary": build_intent_summary(symbols, mode, horizon, focus_labels),
        "organized_prompt": f"{'Compare' if mode == 'compare' else 'Analyze'} {', '.join(symbols)}. Prioritize {', '.join(focus_labels[:4]).lower()} and clearly separate swing-trade quality from long-term investment quality.",
        "framework_steps": framework["steps"],
        "thinking_checklist": framework["checklist"],
    }
