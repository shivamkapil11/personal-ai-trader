from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from app.config import PROJECT_ROOT


class AgentRegistry:
    def __init__(self, path: Path) -> None:
        self.path = path

    def _default_registry(self) -> Dict[str, Any]:
        return {"presets": []}

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

    def presets(self) -> List[Dict[str, Any]]:
        return self.read().get("presets", [])

    def by_id(self, preset_id: str | None) -> Dict[str, Any] | None:
        if not preset_id:
            return None
        normalized = preset_id.strip().lower()
        for preset in self.presets():
            if preset.get("id") == normalized:
                return preset
        return None

    def selectable(self) -> List[Dict[str, Any]]:
        return [
            {
                "id": preset.get("id"),
                "label": preset.get("label"),
                "description": preset.get("description"),
                "tone": preset.get("tone", "yellow"),
                "best_for": preset.get("best_for", []),
            }
            for preset in self.presets()
        ]

    def summary(self) -> Dict[str, Any]:
        presets = self.presets()
        return {
            "count": len(presets),
            "selectable": self.selectable(),
        }

    def resolve(self, query: str, thoughts: str = "", explicit_id: str = "auto") -> Dict[str, Any]:
        preset = self.by_id(explicit_id)
        if preset and preset.get("id") != "auto":
            return {
                **preset,
                "selection_mode": "manual",
                "selection_reason": f"{preset.get('label')} was chosen manually.",
            }

        combined = f"{query}\n{thoughts}".lower()
        ranked: List[tuple[int, Dict[str, Any]]] = []
        for candidate in self.presets():
            if candidate.get("id") == "auto":
                continue
            score = 0
            for keyword in candidate.get("trigger_keywords", []):
                if keyword.lower() in combined:
                    score += 2
            for focus in candidate.get("focus_areas", []):
                if focus.replace("_", " ") in combined:
                    score += 1
            if score > 0:
                ranked.append((score, candidate))

        if ranked:
            ranked.sort(key=lambda item: item[0], reverse=True)
            best = ranked[0][1]
            return {
                **best,
                "selection_mode": "auto",
                "selection_reason": f"Auto-selected {best.get('label')} from your wording and focus.",
            }

        fallback = self.by_id("investment_committee") or {}
        return {
            **fallback,
            "selection_mode": "auto",
            "selection_reason": f"Auto-selected {fallback.get('label', 'Investment Committee')} as the balanced default.",
        }


agent_registry = AgentRegistry(PROJECT_ROOT / "data" / "agent_presets.json")
