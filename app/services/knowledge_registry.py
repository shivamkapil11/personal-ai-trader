from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.config import settings


class KnowledgeRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _default_registry(self) -> Dict[str, Any]:
        return {
            "sources": [],
            "notes": "Populate this registry with books, frameworks, reports, and internal specs to influence reasoning.",
        }

    def _ensure(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.path.write_text(json.dumps(self._default_registry(), indent=2), encoding="utf-8")

    def read(self) -> Dict[str, Any]:
        self._ensure()
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return self._default_registry()

    def sources(self) -> List[Dict[str, Any]]:
        return self.read().get("sources", [])

    def summary(self) -> Dict[str, Any]:
        sources = self.sources()
        return {
            "count": len(sources),
            "categories": sorted({source.get("category", "general") for source in sources}),
            "path": str(self.path),
        }

    def select(self, *, focus_areas: List[str] | None = None, label: str | None = None, mode: str = "analysis") -> Dict[str, Any]:
        focus_areas = focus_areas or []
        relevant: List[Dict[str, Any]] = []
        for source in self.sources():
            tags = set(source.get("tags", []))
            score = 0
            if mode in tags:
                score += 3
            if label and label.lower().replace(" ", "-") in tags:
                score += 2
            score += sum(1 for area in focus_areas if area in tags)
            if score > 0:
                relevant.append({**source, "_score": score})

        ranked = sorted(relevant, key=lambda item: item["_score"], reverse=True)[:4]
        principles = []
        for item in ranked:
            for principle in item.get("principles", [])[:2]:
                if principle not in principles:
                    principles.append(principle)
        return {
            "sources": [
                {
                    "id": item.get("id"),
                    "title": item.get("title"),
                    "category": item.get("category"),
                    "path": item.get("path"),
                }
                for item in ranked
            ],
            "principles": principles[:6],
        }


knowledge_registry = KnowledgeRegistry(settings.knowledge_registry_path)
