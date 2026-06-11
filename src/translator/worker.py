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
        return store.mark_failed(job, exc)

    return store.mark_succeeded(job, translated_path)


def main() -> None:
    processed = process_next_job()
    if processed is None:
        print("No queued jobs")
    else:
        print(processed)


if __name__ == "__main__":
    main()
