import json
from pathlib import Path

from translator.jobs import JobStore


def handler(event, context):
    """Async Lambda-style entrypoint: enqueue work and return immediately."""
    if event.get("storage", "local") != "local":
        raise NotImplementedError("Only local storage is implemented for the take-home test")

    store = JobStore(event.get("job_dir", "jobs"))
    if event.get("action") == "status":
        job = store.get(event["job_id"])
        return {
            "statusCode": 200,
            "body": json.dumps(job),
        }

    job = store.enqueue(
        Path(event["input_path"]),
        Path(event.get("output_dir", "output")),
        max_attempts=int(event.get("max_attempts", 1)),
        retry_delay_seconds=float(event.get("retry_delay_seconds", 0)),
    )

    return {
        "statusCode": 202,
        "body": json.dumps(
            {
                "job_id": job["job_id"],
                "status": job["status"],
                "status_url": f"/jobs/{job['job_id']}",
            }
        ),
    }
