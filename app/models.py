from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class AnalysisRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Comma or newline separated stock symbols")
    thoughts: str = Field(default="", description="Optional user notes or natural-language prompt")
    chart_interval: str = Field(default="D", description="TradingView interval code")
    include_tradingview_snapshot: bool = True

    @field_validator("chart_interval")
    @classmethod
    def validate_interval(cls, value: str) -> str:
        allowed = {"1", "5", "15", "30", "60", "240", "D", "W", "M"}
        cleaned = value.strip().upper()
        if cleaned not in allowed:
            raise ValueError("Unsupported chart interval.")
        return cleaned

    @field_validator("query", "thoughts")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()
