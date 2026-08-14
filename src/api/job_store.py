"""
Thread-safe in-memory job store.

Each pipeline run is a Job identified by a UUID string. The store keeps
all jobs in a plain dict protected by a threading.Lock so that FastAPI's
background thread and the polling endpoint never race.
"""

from __future__ import annotations

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class Job:
    job_id: str
    place_name: str                     # human-readable label shown in the UI
    bounds: dict[str, float]            # {south, north, west, east} in WGS84
    status: str = "queued"              # queued | running | done | error
    progress: int = 0                   # 0–100
    step: str = "Waiting to start"
    result: dict[str, Any] | None = None
    error: str | None = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    finished_at: datetime | None = None


class JobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def create(self, place_name: str, bounds: dict[str, float]) -> Job:
        job = Job(
            job_id=str(uuid.uuid4()),
            place_name=place_name,
            bounds=bounds,
        )
        with self._lock:
            self._jobs[job.job_id] = job
        return job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def update(self, job_id: str, **kwargs: Any) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            for key, value in kwargs.items():
                setattr(job, key, value)

    def mark_done(self, job_id: str, result: dict[str, Any]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "done"
            job.progress = 100
            job.step = "Complete"
            job.result = result
            job.finished_at = datetime.now(timezone.utc)

    def mark_error(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return
            job.status = "error"
            job.error = error
            job.finished_at = datetime.now(timezone.utc)

    def as_dict(self, job: Job) -> dict[str, Any]:
        return {
            "job_id": job.job_id,
            "place_name": job.place_name,
            "bounds": job.bounds,
            "status": job.status,
            "progress": job.progress,
            "step": job.step,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at.isoformat(),
            "finished_at": job.finished_at.isoformat() if job.finished_at else None,
        }


# Module-level singleton shared across the FastAPI app.
store = JobStore()
