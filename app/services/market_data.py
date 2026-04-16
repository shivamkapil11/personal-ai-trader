from __future__ import annotations

import math
from datetime import datetime
from functools import lru_cache
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd
import yfinance as yf

from app.config import settings
from app.services.kite_bridge import kite_bridge

try:
    from jugaad_data.nse import NSELive
except Exception:  # pragma: no cover - optional dependency at runtime
    NSELive = None


class MarketDataError(Exception):
    """Raised when ticker data cannot be resolved."""


# Some NSE-facing names differ from Yahoo Finance's actual tradable symbol.
# Keep the overrides small and explicit so the resolver remains predictable.
YAHOO_SYMBOL_ALIASES = {
    "NALCO": ("NATIONALUM.NS", "NATIONALUM.BO", "NATIONALUM"),
}

PROVIDER_LABELS = {
    "kite_mcp": "Kite MCP",
    "jugaad_data": "jugaad-data",
    "yfinance": "Yahoo Finance",
}


def clean_number(value: Any, digits: int = 2) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return round(number, digits)


def clean_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number) or math.isinf(number):
        return None
    return int(number)


def flatten_history(frame: pd.DataFrame) -> pd.DataFrame:
    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)
    return frame


def pct(value: Any, digits: int = 2) -> float | None:
    number = clean_number(value, digits + 4)
    if number is None:
        return None
    if number > 1:
        return round(number, digits)
    return round(number * 100, digits)


def first_available(frame: pd.DataFrame | None, labels: Iterable[str]) -> float | None:
    if frame is None or frame.empty:
        return None
    index_map = {str(idx).lower(): idx for idx in frame.index}
    for label in labels:
        key = index_map.get(label.lower())
        if key is not None:
            return clean_number(frame.loc[key].iloc[0], 2)
    return None


def growth_rate(current: float | None, previous: float | None) -> float | None:
    if current is None or previous in (None, 0):
        return None
    return round(((current / previous) - 1) * 100, 2)


def classify_trend(series: pd.Series, short: int, long: int) -> str:
    if len(series) < max(short, long):
        return "neutral"
    short_ema = series.ewm(span=short, adjust=False).mean().iloc[-1]
    long_ema = series.ewm(span=long, adjust=False).mean().iloc[-1]
    close = series.iloc[-1]
    if close > short_ema > long_ema:
        return "bullish"
    if close < short_ema < long_ema:
        return "bearish"
    return "neutral"


def benchmark_symbol(resolved_symbol: str) -> str:
    if resolved_symbol.endswith(".NS") or resolved_symbol.endswith(".BO"):
        return "^NSEI"
    return "^GSPC"


def infer_tradingview_symbol(user_query: str, resolved_symbol: str, info: Dict[str, Any]) -> str:
    raw = user_query.strip().upper()
    if ":" in raw:
        return raw

    base = resolved_symbol.split(".")[0].upper()
    if resolved_symbol.endswith(".NS"):
        return f"NSE:{base}"
    if resolved_symbol.endswith(".BO"):
        return f"BSE:{base}"

    exchange = str(info.get("exchange", "")).upper()
    if exchange in {"NMS", "NGM", "NCM"}:
        return f"NASDAQ:{base}"
    if exchange in {"NYQ", "ASE"}:
        return f"NYSE:{base}"
    return base


def unique_ordered(values: Iterable[str]) -> List[str]:
    seen: set[str] = set()
    ordered: List[str] = []
    for value in values:
        cleaned = value.strip().upper()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            ordered.append(cleaned)
    return ordered


def alias_candidates(raw_symbol: str, exchange_prefix: str | None = None) -> List[str]:
    alias_values = list(YAHOO_SYMBOL_ALIASES.get(raw_symbol, ()))
    if not alias_values:
        return []
    if exchange_prefix == "NSE":
        return [value for value in alias_values if value.endswith(".NS")] or alias_values
    if exchange_prefix == "BSE":
        return [value for value in alias_values if value.endswith(".BO")] or alias_values
    return alias_values


@lru_cache(maxsize=256)
def has_nse_live_symbol(raw_symbol: str) -> bool:
    if NSELive is None or not raw_symbol or "." in raw_symbol or ":" in raw_symbol:
        return False
    try:
        payload = NSELive().stock_quote(raw_symbol)
    except Exception:
        return False
    return bool(payload and not payload.get("error") and payload.get("priceInfo"))


def symbol_candidates(query: str) -> List[str]:
    raw = query.strip().upper()
    if ":" in raw:
        prefix, base = raw.split(":", 1)
        if prefix == "NSE":
            return unique_ordered([*alias_candidates(base, "NSE"), f"{base}.NS", base, f"{base}.BO"])
        if prefix == "BSE":
            return unique_ordered([*alias_candidates(base, "BSE"), f"{base}.BO", base, f"{base}.NS"])
        return unique_ordered([*alias_candidates(base), base])
    if "." in raw:
        return unique_ordered([raw, *alias_candidates(raw.split(".", 1)[0])])
    if has_nse_live_symbol(raw):
        return unique_ordered([*alias_candidates(raw), f"{raw}.NS", f"{raw}.BO", raw])
    return unique_ordered([*alias_candidates(raw), raw, f"{raw}.NS", f"{raw}.BO"])


def provider_label(provider_id: str) -> str:
    return PROVIDER_LABELS.get(provider_id, provider_id.replace("_", " ").title())


def provider_order() -> List[str]:
    return [item for item in settings.market_data_provider_order if item in PROVIDER_LABELS]


def indian_symbol_base(query: str, resolved_symbol: str) -> str | None:
    raw = query.strip().upper()
    if raw.startswith("NSE:") or raw.startswith("BSE:"):
        return raw.split(":", 1)[1]
    if resolved_symbol.endswith(".NS") or resolved_symbol.endswith(".BO"):
        return resolved_symbol.split(".", 1)[0].upper()
    return None


def quote_from_jugaad_payload(payload: Dict[str, Any], symbol: str) -> Dict[str, Any] | None:
    if not payload or payload.get("error") or "priceInfo" not in payload:
        return None

    price_info = payload.get("priceInfo", {})
    security_info = payload.get("securityInfo", {})
    metadata = payload.get("metadata", {})

    return {
        "provider": "jugaad_data",
        "provider_label": provider_label("jugaad_data"),
        "instrument": symbol,
        "company_name": security_info.get("companyName") or metadata.get("companyName"),
        "current_price": clean_number(price_info.get("lastPrice")),
        "open": clean_number(price_info.get("open")),
        "previous_close": clean_number(price_info.get("previousClose")),
        "day_high": clean_number(price_info.get("intraDayHighLow", {}).get("max")),
        "day_low": clean_number(price_info.get("intraDayHighLow", {}).get("min")),
        "fifty_two_week_high": clean_number(price_info.get("weekHighLow", {}).get("max")),
        "fifty_two_week_low": clean_number(price_info.get("weekHighLow", {}).get("min")),
        "volume": clean_int(price_info.get("totalTradedVolume")),
        "raw": payload,
    }


def kite_instrument_key(query: str, resolved_symbol: str) -> str:
    raw = query.strip().upper()
    if raw.startswith("NSE:") or raw.startswith("BSE:"):
        return raw
    base = resolved_symbol.split(".", 1)[0].upper()
    if resolved_symbol.endswith(".NS"):
        return f"NSE:{base}"
    if resolved_symbol.endswith(".BO"):
        return f"BSE:{base}"
    return base


def quote_from_kite_payload(payload: Dict[str, Any], instrument: str) -> Dict[str, Any] | None:
    if not isinstance(payload, dict):
        return None
    quote = payload.get(instrument) or next(iter(payload.values()), None)
    if not isinstance(quote, dict):
        return None
    ohlc = quote.get("ohlc", {}) if isinstance(quote.get("ohlc"), dict) else {}
    return {
        "provider": "kite_mcp",
        "provider_label": provider_label("kite_mcp"),
        "instrument": instrument,
        "company_name": instrument,
        "current_price": clean_number(quote.get("last_price") or quote.get("lastPrice")),
        "open": clean_number(ohlc.get("open")),
        "previous_close": clean_number(ohlc.get("close") or quote.get("close")),
        "day_high": clean_number(ohlc.get("high")),
        "day_low": clean_number(ohlc.get("low")),
        "fifty_two_week_high": None,
        "fifty_two_week_low": None,
        "volume": clean_int(quote.get("volume")),
        "raw": payload,
    }


def try_kite_mcp_quote(query: str, resolved_symbol: str, user: Dict[str, Any] | None = None) -> Tuple[Dict[str, Any] | None, str]:
    if not settings.kite_mcp_enabled:
        return None, "Kite MCP is turned off in configuration."
    if not settings.kite_mcp_url:
        return None, "Kite MCP endpoint is not configured."
    if not user:
        return None, "Kite MCP is available, but this run is not linked to a connected Kite session."
    instrument = kite_instrument_key(query, resolved_symbol)
    result = kite_bridge.get_quotes([instrument], user)
    if not result.get("available"):
        return None, result.get("message", "Kite quote lookup is not available.")
    quote = quote_from_kite_payload(result.get("payload", {}), instrument)
    if not quote:
        return None, f"Kite MCP returned a response, but no usable quote was found for {instrument}."
    return quote, f"Live quote resolved through Kite MCP for {instrument}."


def try_jugaad_quote(query: str, resolved_symbol: str) -> Tuple[Dict[str, Any] | None, str]:
    if NSELive is None:
        return None, "jugaad-data is not installed."

    symbol = indian_symbol_base(query, resolved_symbol)
    if not symbol:
        return None, "jugaad-data only applies to NSE/BSE instruments."

    try:
        payload = NSELive().stock_quote(symbol)
    except Exception as exc:  # pragma: no cover - network/provider guard
        return None, f"jugaad-data quote lookup failed: {exc}"

    quote = quote_from_jugaad_payload(payload, symbol)
    if not quote:
        return None, f"jugaad-data did not return a valid live quote for {symbol}."
    return quote, f"Live quote resolved through jugaad-data for {symbol}."


def yfinance_quote(info: Dict[str, Any], history: pd.DataFrame, resolved_symbol: str) -> Tuple[Dict[str, Any], str]:
    latest_close = clean_number(history["Close"].dropna().iloc[-1]) if not history.empty else None
    latest_open = clean_number(history["Open"].dropna().iloc[-1]) if not history.empty else None
    latest_high = clean_number(history["High"].dropna().iloc[-1]) if not history.empty else None
    latest_low = clean_number(history["Low"].dropna().iloc[-1]) if not history.empty else None
    latest_volume = clean_int(history["Volume"].dropna().iloc[-1]) if not history.empty else None
    quote = {
        "provider": "yfinance",
        "provider_label": provider_label("yfinance"),
        "instrument": resolved_symbol,
        "company_name": info.get("longName") or resolved_symbol,
        "current_price": clean_number(info.get("currentPrice")) or clean_number(info.get("regularMarketPrice")) or latest_close,
        "open": clean_number(info.get("open")) or latest_open,
        "previous_close": clean_number(info.get("previousClose")),
        "day_high": clean_number(info.get("dayHigh")) or latest_high,
        "day_low": clean_number(info.get("dayLow")) or latest_low,
        "fifty_two_week_high": clean_number(info.get("fiftyTwoWeekHigh")),
        "fifty_two_week_low": clean_number(info.get("fiftyTwoWeekLow")),
        "volume": clean_int(info.get("volume")) or latest_volume,
        "raw": None,
    }
    return quote, f"Used Yahoo Finance as the market quote source for {resolved_symbol}."


def resolve_live_quote(
    query: str,
    resolved_symbol: str,
    info: Dict[str, Any],
    history: pd.DataFrame,
    user: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    trace: List[Dict[str, Any]] = []
    for provider_id in provider_order():
        if provider_id == "kite_mcp":
            quote, message = try_kite_mcp_quote(query, resolved_symbol, user)
        elif provider_id == "jugaad_data":
            quote, message = try_jugaad_quote(query, resolved_symbol)
        elif provider_id == "yfinance":
            quote, message = yfinance_quote(info, history, resolved_symbol)
        else:
            continue

        trace.append(
            {
                "provider": provider_id,
                "label": provider_label(provider_id),
                "status": "ready" if quote else "skipped",
                "message": message,
            }
        )
        if quote:
            quote["trace"] = trace
            return quote

    raise MarketDataError(f"Could not assemble any market quote source for '{query}'.")


def apply_live_quote(technicals: Dict[str, Any], live_quote: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(technicals)
    if live_quote.get("current_price") is not None:
        merged["current_price"] = live_quote["current_price"]
    if live_quote.get("fifty_two_week_high") is not None:
        merged["fifty_two_week_high"] = live_quote["fifty_two_week_high"]
    if live_quote.get("fifty_two_week_low") is not None:
        merged["fifty_two_week_low"] = live_quote["fifty_two_week_low"]
    merged["live_open"] = live_quote.get("open")
    merged["live_previous_close"] = live_quote.get("previous_close")
    merged["live_day_high"] = live_quote.get("day_high")
    merged["live_day_low"] = live_quote.get("day_low")
    merged["live_volume"] = live_quote.get("volume")
    return merged


def market_data_status() -> Dict[str, Any]:
    providers: List[Dict[str, Any]] = []
    providers.append(
        {
            "id": "kite_mcp",
            "label": provider_label("kite_mcp"),
            "enabled": settings.kite_mcp_enabled,
            "available": bool(settings.kite_mcp_enabled and (settings.kite_mcp_url or settings.kite_mcp_repo_path.exists())),
            "message": (
                f"Kite MCP hosted endpoint is set to {settings.kite_mcp_url}."
                if settings.kite_mcp_url
                else f"Clone zerodha/kite-mcp-server into {settings.kite_mcp_repo_path} or configure the hosted endpoint."
            ),
        }
    )
    providers.append(
        {
            "id": "jugaad_data",
            "label": provider_label("jugaad_data"),
            "enabled": True,
            "available": NSELive is not None,
            "message": "Ready to use NSE public quote data." if NSELive is not None else "Install jugaad-data to use NSE public quote fallback.",
        }
    )
    providers.append(
        {
            "id": "yfinance",
            "label": provider_label("yfinance"),
            "enabled": True,
            "available": True,
            "message": "Ready for history, fundamentals, and headline fallback.",
        }
    )
    return {
        "order": [provider_label(item) for item in provider_order()],
        "providers": providers,
    }


def resolve_symbol(query: str) -> Tuple[str, yf.Ticker, Dict[str, Any], pd.DataFrame]:
    last_error = None
    for candidate in symbol_candidates(query):
        try:
            history = flatten_history(
                yf.download(candidate, period="1y", interval="1d", auto_adjust=False, progress=False)
            ).dropna(how="all")
            if history.empty:
                continue
            ticker = yf.Ticker(candidate)
            info = ticker.info or {}
            return candidate, ticker, info, history
        except Exception as exc:  # pragma: no cover - defensive against provider quirks
            last_error = exc
    raise MarketDataError(f"Could not resolve a live symbol for '{query}'. Last error: {last_error}")


def fetch_news(ticker: yf.Ticker) -> List[Dict[str, Any]]:
    try:
        items = ticker.news or []
    except Exception:
        items = []

    news: List[Dict[str, Any]] = []
    for item in items[:5]:
        content = item.get("content", {}) if isinstance(item, dict) else {}
        canonical = content.get("canonicalUrl", {}) if isinstance(content, dict) else {}
        published = content.get("pubDate") or item.get("providerPublishTime")
        if isinstance(published, (int, float)):
            published = datetime.utcfromtimestamp(published).isoformat() + "Z"
        news.append(
            {
                "title": content.get("title") or item.get("title"),
                "publisher": content.get("provider", {}).get("displayName") if isinstance(content.get("provider"), dict) else item.get("publisher"),
                "url": canonical.get("url") or item.get("link"),
                "published_at": published,
                "summary": content.get("summary"),
            }
        )
    return news


def compute_technicals(history: pd.DataFrame, benchmark_history: pd.DataFrame) -> Dict[str, Any]:
    df = history.copy()
    close = df["Close"]
    high = df["High"]
    low = df["Low"]
    volume = df["Volume"]

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    macd_signal = macd.ewm(span=9, adjust=False).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / 14, min_periods=14, adjust=False).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    sma20 = close.rolling(20).mean()
    std20 = close.rolling(20).std()
    bb_upper = sma20 + 2 * std20
    bb_lower = sma20 - 2 * std20

    low14 = low.rolling(14).min()
    high14 = high.rolling(14).max()
    stoch_k = 100 * ((close - low14) / (high14 - low14))
    stoch_d = stoch_k.rolling(3).mean()

    ema20 = close.ewm(span=20, adjust=False).mean()
    ema50 = close.ewm(span=50, adjust=False).mean()
    ema200 = close.ewm(span=200, adjust=False).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()

    true_range = pd.concat(
        [
            high - low,
            (high - close.shift()).abs(),
            (low - close.shift()).abs(),
        ],
        axis=1,
    ).max(axis=1)
    atr14 = true_range.rolling(14).mean()

    weekly = df.resample("W-FRI").agg({"Close": "last"}).dropna()
    monthly = df.resample("ME").agg({"Close": "last"}).dropna()

    benchmark_close = benchmark_history["Close"].dropna()
    relative_60d = None
    if len(close) > 61 and len(benchmark_close) > 61:
        stock_return = close.iloc[-1] / close.iloc[-61]
        benchmark_return = benchmark_close.iloc[-1] / benchmark_close.iloc[-61]
        relative_60d = round((stock_return / benchmark_return - 1) * 100, 2)

    return {
        "current_price": clean_number(close.iloc[-1]),
        "trend_daily": classify_trend(close, 10, 30),
        "trend_weekly": classify_trend(weekly["Close"], 10, 30),
        "trend_monthly": classify_trend(monthly["Close"], 4, 10),
        "rsi14": clean_number(rsi.iloc[-1]),
        "macd": clean_number(macd.iloc[-1]),
        "macd_signal": clean_number(macd_signal.iloc[-1]),
        "macd_histogram": clean_number((macd - macd_signal).iloc[-1]),
        "bollinger_mid": clean_number(sma20.iloc[-1]),
        "bollinger_upper": clean_number(bb_upper.iloc[-1]),
        "bollinger_lower": clean_number(bb_lower.iloc[-1]),
        "stochastic_k": clean_number(stoch_k.iloc[-1]),
        "stochastic_d": clean_number(stoch_d.iloc[-1]),
        "ema20": clean_number(ema20.iloc[-1]),
        "ema50": clean_number(ema50.iloc[-1]),
        "ema200": clean_number(ema200.iloc[-1]),
        "sma50": clean_number(sma50.iloc[-1]),
        "sma200": clean_number(sma200.iloc[-1]),
        "atr14": clean_number(atr14.iloc[-1]),
        "support_1": clean_number(low.tail(10).min()),
        "support_2": clean_number(low.tail(30).min()),
        "resistance_1": clean_number(high.tail(10).max()),
        "resistance_2": clean_number(high.tail(30).max()),
        "fifty_two_week_high": clean_number(high.tail(252).max() if len(high) >= 252 else high.max()),
        "fifty_two_week_low": clean_number(low.tail(252).min() if len(low) >= 252 else low.min()),
        "volume_ratio_5v20": clean_number(volume.tail(5).mean() / volume.tail(20).mean(), 3),
        "return_20d": clean_number((close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) > 21 else None),
        "return_60d": clean_number((close.iloc[-1] / close.iloc[-61] - 1) * 100 if len(close) > 61 else None),
        "return_120d": clean_number((close.iloc[-1] / close.iloc[-121] - 1) * 100 if len(close) > 121 else None),
        "relative_strength_60d": relative_60d,
    }


def compute_fundamentals(ticker: yf.Ticker, info: Dict[str, Any]) -> Dict[str, Any]:
    income = ticker.income_stmt
    quarterly_income = ticker.quarterly_income_stmt
    balance = ticker.balance_sheet
    cashflow = ticker.cashflow

    revenue_now = first_available(quarterly_income, ["Total Revenue", "Operating Revenue", "Revenue"])
    revenue_prev = None
    net_income_now = first_available(
        quarterly_income,
        [
            "Net Income",
            "Net Income Common Stockholders",
            "Net Income From Continuing Operation Net Minority Interest",
        ],
    )
    net_income_prev = None

    if quarterly_income is not None and not quarterly_income.empty and quarterly_income.shape[1] >= 4:
        quarterly_index = {str(idx).lower(): idx for idx in quarterly_income.index}
        for label in ["Total Revenue", "Operating Revenue", "Revenue"]:
            key = quarterly_index.get(label.lower())
            if key is not None:
                revenue_prev = clean_number(quarterly_income.loc[key].iloc[3], 2)
                break
        for label in [
            "Net Income",
            "Net Income Common Stockholders",
            "Net Income From Continuing Operation Net Minority Interest",
        ]:
            key = quarterly_index.get(label.lower())
            if key is not None:
                net_income_prev = clean_number(quarterly_income.loc[key].iloc[3], 2)
                break

    annual_revenue = first_available(income, ["Total Revenue", "Operating Revenue", "Revenue"])
    annual_revenue_prev = None
    annual_profit = first_available(
        income,
        [
            "Net Income",
            "Net Income Common Stockholders",
            "Net Income From Continuing Operation Net Minority Interest",
        ],
    )
    annual_profit_prev = None

    if income is not None and not income.empty and income.shape[1] >= 2:
        income_index = {str(idx).lower(): idx for idx in income.index}
        for label in ["Total Revenue", "Operating Revenue", "Revenue"]:
            key = income_index.get(label.lower())
            if key is not None:
                annual_revenue_prev = clean_number(income.loc[key].iloc[1], 2)
                break
        for label in [
            "Net Income",
            "Net Income Common Stockholders",
            "Net Income From Continuing Operation Net Minority Interest",
        ]:
            key = income_index.get(label.lower())
            if key is not None:
                annual_profit_prev = clean_number(income.loc[key].iloc[1], 2)
                break

    equity_now = first_available(balance, ["Common Stock Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"])
    equity_prev = None
    debt_now = first_available(balance, ["Total Debt", "Net Debt"])
    invested_capital = first_available(balance, ["Invested Capital"])
    current_assets = first_available(balance, ["Current Assets", "Total Current Assets"])
    current_liabilities = first_available(balance, ["Current Liabilities", "Total Current Liabilities"])
    ebit = first_available(income, ["EBIT", "Operating Income"])
    operating_cash_flow = first_available(cashflow, ["Operating Cash Flow", "Cash Flow From Continuing Operating Activities"])
    free_cash_flow = first_available(cashflow, ["Free Cash Flow"])
    capital_expenditure = first_available(cashflow, ["Capital Expenditure"])

    if balance is not None and not balance.empty and balance.shape[1] >= 2:
        balance_index = {str(idx).lower(): idx for idx in balance.index}
        for label in ["Common Stock Equity", "Stockholders Equity", "Total Equity Gross Minority Interest"]:
            key = balance_index.get(label.lower())
            if key is not None:
                equity_prev = clean_number(balance.loc[key].iloc[1], 2)
                break

    average_equity = None
    if equity_now is not None and equity_prev is not None:
        average_equity = (equity_now + equity_prev) / 2

    roe = None
    if annual_profit is not None and average_equity not in (None, 0):
        roe = round((annual_profit / average_equity) * 100, 2)

    roce = None
    if ebit is not None and invested_capital not in (None, 0):
        roce = round((ebit / invested_capital) * 100, 2)

    current_ratio = None
    if current_assets not in (None, 0) and current_liabilities not in (None, 0):
        current_ratio = round(current_assets / current_liabilities, 2)

    return {
        "market_cap": clean_int(info.get("marketCap")),
        "enterprise_value": clean_int(info.get("enterpriseValue")),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "trailing_pe": clean_number(info.get("trailingPE")),
        "forward_pe": clean_number(info.get("forwardPE")),
        "price_to_book": clean_number(info.get("priceToBook")),
        "dividend_yield": pct(info.get("dividendYield")),
        "payout_ratio": pct(info.get("payoutRatio")),
        "profit_margin": pct(info.get("profitMargins")),
        "operating_margin": pct(info.get("operatingMargins")),
        "ebitda_margin": pct(info.get("ebitdaMargins")),
        "revenue_growth": pct(info.get("revenueGrowth")),
        "earnings_growth": pct(info.get("earningsGrowth")),
        "debt_to_equity": clean_number(info.get("debtToEquity")),
        "beta": clean_number(info.get("beta")),
        "book_value": clean_number(info.get("bookValue")),
        "quarterly_revenue_yoy": growth_rate(revenue_now, revenue_prev),
        "quarterly_profit_yoy": growth_rate(net_income_now, net_income_prev),
        "annual_revenue_growth": growth_rate(annual_revenue, annual_revenue_prev),
        "annual_profit_growth": growth_rate(annual_profit, annual_profit_prev),
        "roe": roe,
        "roce": roce,
        "current_ratio": current_ratio,
        "operating_cash_flow": clean_number(operating_cash_flow),
        "free_cash_flow": clean_number(free_cash_flow),
        "capital_expenditure": clean_number(capital_expenditure),
        "total_debt": clean_number(debt_now),
        "equity": clean_number(equity_now),
        "financial_status": None,
        "business_summary": info.get("longBusinessSummary"),
        "employees": clean_int(info.get("fullTimeEmployees")),
        "audit_risk": clean_int(info.get("auditRisk")),
        "board_risk": clean_int(info.get("boardRisk")),
        "compensation_risk": clean_int(info.get("compensationRisk")),
        "shareholder_rights_risk": clean_int(info.get("shareHolderRightsRisk")),
        "overall_governance_risk": clean_int(info.get("overallRisk")),
    }


def financial_status(fundamentals: Dict[str, Any]) -> str:
    growth_flags = [
        fundamentals.get("revenue_growth"),
        fundamentals.get("earnings_growth"),
        fundamentals.get("quarterly_revenue_yoy"),
        fundamentals.get("quarterly_profit_yoy"),
    ]
    positives = sum(1 for item in growth_flags if item is not None and item > 0)
    negatives = sum(1 for item in growth_flags if item is not None and item < 0)
    if positives >= 3 and negatives == 0:
        return "improving"
    if negatives >= 2:
        return "weakening"
    return "stable"


def collect_stock_data(query: str, user: Dict[str, Any] | None = None) -> Dict[str, Any]:
    resolved_symbol, ticker, info, history = resolve_symbol(query)
    benchmark = flatten_history(
        yf.download(benchmark_symbol(resolved_symbol), period="1y", interval="1d", auto_adjust=False, progress=False)
    ).dropna(how="all")

    live_quote = resolve_live_quote(query, resolved_symbol, info, history, user)
    technicals = apply_live_quote(compute_technicals(history, benchmark), live_quote)
    fundamentals = compute_fundamentals(ticker, info)
    fundamentals["financial_status"] = financial_status(fundamentals)

    return {
        "input_symbol": query,
        "resolved_symbol": resolved_symbol,
        "company_name": info.get("longName") or resolved_symbol,
        "currency": info.get("currency"),
        "exchange": info.get("exchange"),
        "quote_type": info.get("quoteType"),
        "tradingview_symbol": infer_tradingview_symbol(query, resolved_symbol, info),
        "technicals": technicals,
        "fundamentals": fundamentals,
        "news": fetch_news(ticker),
        "market_context": {
            "provider_order": provider_order(),
            "quote_provider": live_quote["provider"],
            "quote_provider_label": live_quote["provider_label"],
            "quote_message": live_quote["trace"][-1]["message"] if live_quote.get("trace") else "",
            "quote_trace": live_quote.get("trace", []),
            "quote_snapshot": {
                "current_price": live_quote.get("current_price"),
                "open": live_quote.get("open"),
                "previous_close": live_quote.get("previous_close"),
                "day_high": live_quote.get("day_high"),
                "day_low": live_quote.get("day_low"),
                "volume": live_quote.get("volume"),
            },
        },
    }
