from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.config import PROJECT_ROOT


DISCOVERY_HINTS = [
    "industry",
    "sector",
    "theme",
    "space",
    "ecosystem",
    "which stocks",
    "find stocks",
    "stocks in",
    "companies in",
    "industry segmentation",
]


class IndustryRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def read(self) -> Dict[str, Any]:
        if not self.path.exists():
            return {"industries": []}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"industries": []}

    def industries(self) -> List[Dict[str, Any]]:
        return self.read().get("industries", [])

    def match(self, text: str) -> Dict[str, Any] | None:
        lowered = text.lower()
        best: Dict[str, Any] | None = None
        best_score = 0
        for industry in self.industries():
            score = 0
            for alias in industry.get("aliases", []):
                alias_lower = alias.lower()
                if alias_lower in lowered:
                    score = max(score, len(alias_lower))
            if score > best_score:
                best_score = score
                best = industry
        return best

    def should_segment(self, text: str) -> bool:
        lowered = text.lower()
        return any(hint in lowered for hint in DISCOVERY_HINTS)

    def resolve(self, text: str) -> Dict[str, Any] | None:
        match = self.match(text)
        if not match:
            return None
        candidates = match.get("candidates", [])
        return {
            "id": match.get("id"),
            "label": match.get("label"),
            "description": match.get("description"),
            "segments": match.get("segments", []),
            "candidates": candidates,
            "shortlist_symbols": [item["symbol"] for item in candidates[:3] if item.get("symbol")],
        }


industry_registry = IndustryRegistry(PROJECT_ROOT / "data" / "industry_segments.json")
