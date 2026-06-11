# Codex Instructions

This repository is a document translation pipeline. Keep changes aligned with these rules:

- Use the mock `translate()` function only. Do not call external LLM or translation APIs.
- Follow TDD for behavior changes: add or update a focused test first, watch it fail, then implement the smallest production change that passes.
- Keep format-specific logic in `src/translator/excel.py`, `src/translator/word.py`, and `src/translator/pdf.py`.
- Preserve document structure where the format supports it. Excel must keep existing columns, Word must keep bullets/tables/basic run formatting, and PDF may use basic regenerated layout.
- Route translation through `TranslationService`; do not add direct calls to `mock_service.translate()` inside document handlers.
- For scalability changes, prefer service-layer batching, caching, retries, and throttling over duplicating logic in each file parser.
- Keep Lambda code deployable in shape but local in behavior. Do not deploy to AWS or require cloud credentials.
- Prefer the async handler and worker model when discussing production scalability. The synchronous handler is only a local convenience.
- Document production assumptions, especially rate limits, batching, retries, and large-file handling.
