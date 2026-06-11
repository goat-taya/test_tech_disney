from translator.jobs import JobStore
from translator.pipeline import translate_file
from translator.service import TranslationService


def process_next_job(store: JobStore | None = None) -> dict | None:
    store = store or JobStore()
    job = store.next_queued()
    if job is None:
        return None

    store.mark_running(job)
    try:
        service = TranslationService()
        translated_path = translate_file(job["input_path"], job["output_dir"], service=service)
    except Exception as exc:
        if store.should_retry(job):
            return store.mark_retryable_failure(job, exc)
        return store.mark_failed(job, exc)

    return store.mark_succeeded(job, translated_path)


def process_available_jobs(store: JobStore | None = None, max_jobs: int | None = None) -> list[dict]:
    store = store or JobStore()
    processed = []

    while max_jobs is None or len(processed) < max_jobs:
        job = process_next_job(store)
        if job is None:
            break
        processed.append(job)

    return processed


def main() -> None:
    processed = process_available_jobs()
    if not processed:
        print("No queued jobs")
    else:
        for job in processed:
            print(job)


if __name__ == "__main__":
    main()
