# AI Document Translation Pipeline

Scalable local document translation pipeline for extracting French business text from Excel, Word, and PDF files, passing it through the required mock translation service, and writing translated files back through an asynchronous job model.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

Run the tests:

```bash
pytest -q
```

Submit work through the scalable async path:

```bash
python - <<'PY'
import json
from translator.async_handler import handler

event = json.load(open("events/sample_async_event.json"))
print(handler(event, None))
PY
```

Process queued jobs with the worker:

```bash
python -m translator.worker
```

The synchronous CLI still exists for local debugging and test fixtures:

```bash
python -m translator.pipeline input/products.xlsx output
python -m translator.pipeline input output
```

## Design

The code uses one dispatcher in `src/translator/pipeline.py` and keeps document handling isolated by format:

- `excel.py`: uses `openpyxl` to add `description_en` next to `description` while preserving other columns.
- `word.py`: uses `python-docx` to replace paragraph and table-cell text while preserving paragraph style and first-run formatting.
- `pdf.py`: uses `pypdf` for extraction and `reportlab` to generate a translated PDF with basic formatting.
- `mock_service.py`: contains the required mock translation function.
- `service.py`: wraps the mock service with batching, deduplication, caching, retry, and throttle hooks.
- `async_handler.py`: accepts work asynchronously, returns a job id, and exposes job status.
- `jobs.py` and `worker.py`: provide a local durable job store, attempt tracking, retry requeueing, and worker draining.

The document handlers do not call the mock directly. They receive a `TranslationService`, which means large jobs can share one cache across Excel, Word, and PDF files during a directory run. This also creates a single place to add real API behavior later: rate limiting, retries, request batching, telemetry, and circuit breaking.

The scalable path is asynchronous. Requests enqueue translation jobs and return `202 Accepted`; workers then process jobs under service-layer batching, throttling, caching, and retry rules. The synchronous CLI remains useful for local demos and tests, but it is not the production delivery path.

## TDD And Tests

This was implemented with a TDD loop:

1. Add failing tests for Excel, Word, PDF, pipeline dispatch, and the Lambda-style handler.
2. Implement the smallest format-specific modules needed to pass.
3. Keep the tests as regression coverage for the assignment requirements.

The current suite verifies:

- Excel inserts `description_en` next to `description`.
- Existing Excel data remains intact.
- Word text is translated while bullets, tables, and bold text survive.
- PDF output is generated and contains translated text.
- The pipeline dispatches based on file extension.
- The Lambda handler can process a local file event.
- The async handler enqueues a job and the worker processes it later.
- Job status can be queried through the async handler.
- Retryable worker failures are requeued until `max_attempts` is exhausted.
- Workers can drain multiple queued jobs in one run.
- Repeated translation strings are deduplicated and cached through `TranslationService`.
- Translation backend calls can be retried and throttled between batches.
- The integration suite processes Excel, Word, and PDF together through `translate_directory()`.

## Lambda Handler Bonus

`src/translator/lambda_handler.py` is structured as an AWS Lambda entrypoint but runs locally for the test. It accepts an event like:

```json
{
  "storage": "local",
  "input_path": "input/products.xlsx",
  "output_dir": "output"
}
```

Local invocation example:

```bash
python - <<'PY'
import json
from translator.lambda_handler import handler

event = json.load(open("events/sample_local_event.json"))
print(handler(event, None))
PY
```

In production, the local path handling would be replaced by an S3 storage adapter using `boto3`, while keeping `translate_file()` unchanged.

## Async Worker Delivery Path

For scalability, large documents are not processed synchronously inside the request handler. The async version is represented by:

- `src/translator/async_handler.py`: validates the event, creates a job, and returns immediately with `202 Accepted`.
- `src/translator/jobs.py`: stores local JSON job records with `queued`, `running`, `retry_scheduled`, `succeeded`, and `failed` states, plus attempt counts and errors.
- `src/translator/worker.py`: claims queued jobs, processes available work, requeues retryable failures, and records terminal failures.
- `src/translator/service.py`: centralizes deduplication, batching, retry, and throttle behavior around the translation backend.

Local async submission:

```bash
python - <<'PY'
import json
from translator.async_handler import handler

event = json.load(open("events/sample_async_event.json"))
print(handler(event, None))
PY
```

Process queued jobs:

```bash
python -m translator.worker
```

Status lookup:

```bash
python - <<'PY'
from translator.async_handler import handler

print(handler({"action": "status", "storage": "local", "job_id": "replace-with-job-id"}, None))
PY
```

Production shape:

```mermaid
flowchart TD
    A[Teams or API upload] --> B[Async request handler]
    B --> C[Create job record]
    B --> D[Enqueue translation job]
    B --> E[Return 202 with job id]
    D --> F[Worker pool]
    F --> G[TranslationService batching/cache/retry/throttle]
    G --> H[Write translated file]
    H --> I[Mark job succeeded]
    F --> J[Schedule retryable failures]
    J --> F
    F --> K[Mark terminal failures]
```

This lets the system scale by increasing worker count while still enforcing a global translation API budget. The local file-backed job store is intentionally replaceable; in production it should become SQS or another queue plus DynamoDB/Postgres for queryable job state. The important boundary is stable: request handlers enqueue, workers process, and `TranslationService` owns backend pressure.

## Power Automate Bonus

Recommended Teams flow:

```mermaid
flowchart TD
    A[User uploads file in Teams] --> B[Power Automate trigger on SharePoint file]
    B --> C[Validate extension: xlsx, docx, pdf]
    C --> D[Get file content]
    D --> E[POST file to translation endpoint]
    E --> F[Lambda/API runs translation pipeline]
    F --> G[Return translated file or storage URL]
    G --> H[Post translated file back to Teams]
    C --> I[Notify user when file type is unsupported]
```

The endpoint would return either binary file content or a temporary download URL. For a production flow, I would also include correlation IDs, retry handling, and user-facing error messages.

## Real API And 50,000 Rows

If the mock became a real translation API with rate limits and large Excel files, I would change the service layer before changing document parsing:

- Batch translation units through `TranslationService.translate_many()` instead of calling the API per cell.
- Deduplicate repeated strings before translation. This is already implemented for the local service facade.
- Add distributed request throttling, exponential backoff, and timeout handling inside `TranslationService`.
- Cache translations by source text, source language, target language, and model/API version. The in-memory cache already proves the interface; production would use Redis, DynamoDB, or a database table depending on deployment.
- Stream or chunk large workbooks where possible.
- Persist checkpoints so a failed 50,000-row job can resume.
- Track job status, attempts, partial failures, and translated-row counts. The local job store already records status and attempts.
- Add structured logs and metrics for latency, API errors, and cost.

For 50,000 rows, the pipeline should treat translation as a job rather than a single request/response call. A production version would enqueue work, process batches with controlled concurrency, update progress after each committed batch, and write partial results safely so the job can resume after a failure.

Rate limiting would live at the worker/service boundary:

- Workers claim jobs only when capacity is available.
- `TranslationService` groups translation units into batches.
- A shared rate limiter controls requests per minute across workers.
- `429` responses honor `Retry-After` and requeue the batch instead of blocking the whole system.
- Job state tracks `queued`, `running`, `retry_scheduled`, `succeeded`, and `failed`; a production queue would move delayed retries into the queue instead of local JSON timestamps.

## AI Configuration

This repo uses Codex as the AI coding assistant, with portable IDE-agent rules for other tools:

- `AGENTS.md` steers Codex and other terminal agents.
- `.cursor/rules/translation-pipeline.mdc` gives Cursor the same repository constraints.
- `.github/copilot-instructions.md` gives GitHub Copilot concise project rules.

These rules tell AI assistants to:

- use only the mock translation service,
- work test-first,
- keep format-specific code isolated,
- preserve document structure,
- avoid cloud deployment,
- document scaling assumptions.

## Known Limitations

- PDF layout is regenerated rather than preserved.
- Word translation currently preserves paragraph style and first-run formatting, but does not preserve mixed formatting inside a sentence perfectly.
- Excel assumes the source column is named `description`.
- The Lambda handlers are local-only and intentionally do not use AWS credentials.
- The local job store uses JSON files, so it is useful for deterministic local testing but not safe for multiple distributed workers.
