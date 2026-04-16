from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class JobState:
    id: str
    status: str = "queued"
    progress: int = 0
    events: List[Dict[str, Any]] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: str = field(default_factory=utc_now)
    finished_at: Optional[str] = None

    def snapshot(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "events": self.events,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "finished_at": self.finished_at,
        }


class JobManager:
    def __init__(self) -> None:
        self._jobs: Dict[str, JobState] = {}
        self._lock = Lock()

    def create(self) -> JobState:
        job = JobState(id=str(uuid4()))
        with self._lock:
            self._jobs[job.id] = job
        return job

    def get(self, job_id: str) -> Optional[JobState]:
        with self._lock:
            return self._jobs.get(job_id)

    def publish(
        self,
        job_id: str,
        *,
        step: str,
        message: str,
        progress: int,
        symbol: str | None = None,
        kind: str = "progress",
        payload: Dict[str, Any] | None = None,
    ) -> None:
        event = {
            "kind": kind,
            "step": step,
            "message": message,
            "progress": max(0, min(100, progress)),
            "symbol": symbol,
            "payload": payload or {},
            "timestamp": utc_now(),
        }
        with self._lock:
            job = self._jobs[job_id]
            job.status = "running"
            job.progress = max(job.progress, event["progress"])
            job.events.append(event)

    def complete(self, job_id: str, result: Dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "completed"
            job.progress = 100
            job.result = result
            job.finished_at = utc_now()
            job.events.append(
                {
                    "kind": "complete",
                    "step": "complete",
                    "message": "Research package ready.",
                    "progress": 100,
                    "symbol": None,
                    "payload": {},
                    "timestamp": job.finished_at,
                }
            )

    def fail(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = "failed"
            job.error = error
            job.finished_at = utc_now()
            job.events.append(
                {
                    "kind": "error",
                    "step": "failed",
                    "message": error,
                    "progress": job.progress,
                    "symbol": None,
                    "payload": {},
                    "timestamp": job.finished_at,
                }
            )

    def event_stream_payload(self, job_id: str, index: int) -> str:
        job = self.get(job_id)
        if not job:
            return ""
        if index >= len(job.events):
            return ""
        return json.dumps(job.events[index])


job_manager = JobManager()
