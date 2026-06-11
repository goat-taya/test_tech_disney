# Copilot Instructions

This repository is a local take-home document translation pipeline.

- Use only the required mock translation backend in `src/translator/mock_service.py`.
- Do not introduce real translation, LLM, AWS, or cloud-provider calls.
- Route translations through `TranslationService`; document handlers should not call the mock directly.
- Keep format-specific behavior in `src/translator/excel.py`, `src/translator/word.py`, and `src/translator/pdf.py`.
- Preserve structure where supported: Excel keeps existing columns, Word keeps bullets/tables/basic run formatting, and PDF may use a regenerated layout.
- Add or update focused tests before changing behavior.
- Prefer service-layer batching, caching, retries, throttling, and worker queues for scalability discussions or changes.
- Keep the async handler and worker model as the production-oriented path; the synchronous handler is a local convenience.
