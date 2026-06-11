import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class JobStore:
    """Small local job store standing in for a durable queue/job table."""

    def __init__(self, root: str | Path = "jobs"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def enqueue(self, input_path: str | Path, output_dir: str | Path) -> dict[str, Any]:
        now = _utc_now()
        job = {
            "job_id": uuid.uuid4().hex,
            "status": "queued",
            "input_path": str(input_path),
            "output_dir": str(output_dir),
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
            if job["status"] == "queued":
                return job
        return None

    def mark_running(self, job: dict[str, Any]) -> dict[str, Any]:
        job["status"] = "running"
        self.save(job)
        return job

    def mark_succeeded(self, job: dict[str, Any], translated_file: str | Path) -> dict[str, Any]:
        job["status"] = "succeeded"
        job["translated_file"] = str(translated_file)
        job.pop("error", None)
        self.save(job)
        return job

    def mark_failed(self, job: dict[str, Any], error: Exception) -> dict[str, Any]:
        job["status"] = "failed"
        job["error"] = str(error)
        self.save(job)
        return job

    def _path(self, job_id: str) -> Path:
        return self.root / f"{job_id}.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()
