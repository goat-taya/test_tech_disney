import json
from pathlib import Path

from translator.jobs import JobStore


def handler(event, context):
    """Async Lambda-style entrypoint: enqueue work and return immediately."""
    if event.get("storage", "local") != "local":
        raise NotImplementedError("Only local storage is implemented for the take-home test")

    store = JobStore(event.get("job_dir", "jobs"))
    job = store.enqueue(Path(event["input_path"]), Path(event.get("output_dir", "output")))

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
