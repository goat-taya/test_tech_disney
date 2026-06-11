import json
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


class JobStore:
    """Small local job store standing in for a durable queue/job table."""

    def __init__(self, root: str | Path = "jobs"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def enqueue(
        self,
        input_path: str | Path,
        output_dir: str | Path,
        max_attempts: int = 1,
        retry_delay_seconds: float = 0,
    ) -> dict[str, Any]:
        if max_attempts < 1:
            raise ValueError("max_attempts must be greater than zero")
        if retry_delay_seconds < 0:
            raise ValueError("retry_delay_seconds cannot be negative")

        now = _utc_now()
        job = {
            "job_id": uuid.uuid4().hex,
            "status": "queued",
            "input_path": str(input_path),
            "output_dir": str(output_dir),
            "attempts": 0,
            "max_attempts": max_attempts,
            "retry_delay_seconds": retry_delay_seconds,
            "created_at": now,
            "updated_at": now,
        }
        self.save(job)
        return job

    def get(self, job_id: str) -> dict[str, Any]:
        path = self._path(job_id)
        if not path.exists():
            raise KeyError(f"Unknown job id: {job_id}")
        return json.loads(path.read_text())

    def save(self, job: dict[str, Any]) -> None:
        job["updated_at"] = _utc_now()
        self._path(job["job_id"]).write_text(json.dumps(job, indent=2, sort_keys=True))

    def next_queued(self) -> dict[str, Any] | None:
        for path in sorted(self.root.glob("*.json")):
            job = json.loads(path.read_text())
            if job["status"] == "queued" or _retry_is_due(job):
                return job
        return None

    def mark_running(self, job: dict[str, Any]) -> dict[str, Any]:
        job["status"] = "running"
        job["attempts"] = int(job.get("attempts", 0)) + 1
        job.pop("retry_available_at", None)
        self.save(job)
        return job

    def mark_succeeded(self, job: dict[str, Any], translated_file: str | Path) -> dict[str, Any]:
        job["status"] = "succeeded"
        job["translated_file"] = str(translated_file)
        job.pop("error", None)
        job.pop("last_error", None)
        self.save(job)
        return job

    def mark_retryable_failure(self, job: dict[str, Any], error: Exception) -> dict[str, Any]:
        job["status"] = "retry_scheduled"
        job["last_error"] = str(error)
        delay = float(job.get("retry_delay_seconds", 0))
        job["retry_available_at"] = _utc_now(delay)
        self.save(job)
        return job

    def mark_failed(self, job: dict[str, Any], error: Exception) -> dict[str, Any]:
        job["status"] = "failed"
        job["error"] = str(error)
        job["last_error"] = str(error)
        self.save(job)
        return job

    def should_retry(self, job: dict[str, Any]) -> bool:
        return int(job.get("attempts", 0)) < int(job.get("max_attempts", 1))

    def _path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.json"

def _utc_now(offset_seconds: float = 0) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=offset_seconds)).isoformat()


def _retry_is_due(job: dict[str, Any]) -> bool:
    if job["status"] != "retry_scheduled":
        return False

    retry_available_at = job.get("retry_available_at")
    if retry_available_at is None:
        return True

    return datetime.fromisoformat(retry_available_at) <= datetime.now(timezone.utc)
