import json

from openpyxl import Workbook, load_workbook

from translator.async_handler import handler as async_handler
from translator.jobs import JobStore
from translator.worker import process_next_job


def test_async_handler_enqueues_job_and_worker_processes_it(tmp_path):
    source = tmp_path / "input" / "products.xlsx"
    output_dir = tmp_path / "output"
    job_dir = tmp_path / "jobs"
    source.parent.mkdir()

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["sku", "description"])
    sheet.append(["A-001", "Texte scalable"])
    workbook.save(source)

    response = async_handler(
        {
            "storage": "local",
            "input_path": str(source),
            "output_dir": str(output_dir),
            "job_dir": str(job_dir),
        },
        None,
    )

    assert response["statusCode"] == 202
    body = json.loads(response["body"])
    assert body["status"] == "queued"

    store = JobStore(job_dir)
    queued_job = store.get(body["job_id"])
    assert queued_job["status"] == "queued"

    processed = process_next_job(store)

    assert processed["job_id"] == body["job_id"]
    assert processed["status"] == "succeeded"
    rows = list(load_workbook(output_dir / "products_en.xlsx").active.iter_rows(values_only=True))
    assert rows[1][2] == "[EN] Texte scalable"


def test_worker_marks_job_failed_when_translation_errors(tmp_path):
    source = tmp_path / "missing.xlsx"
    store = JobStore(tmp_path / "jobs")
    job = store.enqueue(source, tmp_path / "output")

    processed = process_next_job(store)

    assert processed["job_id"] == job["job_id"]
    assert processed["status"] == "failed"
    assert "error" in processed
