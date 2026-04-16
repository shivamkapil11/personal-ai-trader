from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class AnalysisRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Comma or newline separated stock symbols")
    thoughts: str = Field(default="", description="Optional user notes or natural-language prompt")
    chart_interval: str = Field(default="D", description="TradingView interval code")
    agent_preset: str = Field(default="auto", description="Optional local research agent preset")
    include_tradingview_snapshot: bool = True

    @field_validator("chart_interval")
    @classmethod
    def validate_interval(cls, value: str) -> str:
        allowed = {"1", "5", "15", "30", "60", "240", "D", "W", "M"}
        cleaned = value.strip().upper()
        if cleaned not in allowed:
            raise ValueError("Unsupported chart interval.")
        return cleaned

    @field_validator("query", "thoughts", "agent_preset")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class AuthSessionRequest(BaseModel):
    uid: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    email: str = Field(..., min_length=3)
    image: str = ""
    id_token: str = ""
    provider: str = "google"

    @field_validator("uid", "name", "email", "image", "id_token", "provider")
    @classmethod
    def strip_auth_text(cls, value: str) -> str:
        return value.strip()


class KiteChoiceRequest(BaseModel):
    is_kite_user: bool


class WatchlistCreateRequest(BaseModel):
    symbol: str = Field(..., min_length=1)
    note: str = ""

    @field_validator("symbol", "note")
    @classmethod
    def strip_watchlist_text(cls, value: str) -> str:
        return value.strip()


class FeedbackCreateRequest(BaseModel):
    message: str = Field(..., min_length=1)
    route: str = "/"
    metadata: dict = Field(default_factory=dict)

    @field_validator("message", "route")
    @classmethod
    def strip_feedback_text(cls, value: str) -> str:
        return value.strip()


class SearchHistoryEntry(BaseModel):
    query: str
    thoughts: str = ""
    mode: str = "single"
    symbols: list[str] = Field(default_factory=list)
    timestamp: str


class UserSession(BaseModel):
    uid: str
    name: str
    email: str
    image: str = ""
    provider: str = "google"
    kite_connected: bool = False
    onboarding_step: str = "auth"
    is_kite_user: Optional[bool] = None
