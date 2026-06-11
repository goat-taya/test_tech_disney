from translator.service import TranslationService


def test_translation_service_deduplicates_and_preserves_order():
    calls = []

    def backend(text, source="fr", target="en"):
        calls.append(text)
        return f"[EN] {text}"

    service = TranslationService(backend=backend, batch_size=2)

    result = service.translate_many(
        [
            "Texte A",
            "Texte B",
            "Texte A",
            "",
            "Texte C",
            "Texte B",
        ]
    )

    assert result == [
        "[EN] Texte A",
        "[EN] Texte B",
        "[EN] Texte A",
        "",
        "[EN] Texte C",
        "[EN] Texte B",
    ]
    assert calls == ["Texte A", "Texte B", "Texte C"]


def test_translation_service_reuses_cache_across_calls():
    calls = []

    def backend(text, source="fr", target="en"):
        calls.append(text)
        return f"[EN] {text}"

    service = TranslationService(backend=backend)

    assert service.translate_text("Texte A") == "[EN] Texte A"
    assert service.translate_text("Texte A") == "[EN] Texte A"

    assert calls == ["Texte A"]


def test_translation_service_retries_transient_backend_errors():
    calls = []

    def backend(text, source="fr", target="en"):
        calls.append(text)
        if len(calls) == 1:
            raise RuntimeError("temporary outage")
        return f"[EN] {text}"

    service = TranslationService(backend=backend, max_retries=1, retry_delay_seconds=0)

    assert service.translate_text("Texte A") == "[EN] Texte A"
    assert calls == ["Texte A", "Texte A"]


def test_translation_service_throttles_between_uncached_batches():
    sleeps = []

    def backend(text, source="fr", target="en"):
        return f"[EN] {text}"

    service = TranslationService(
        backend=backend,
        batch_size=2,
        throttle_seconds=0.25,
        sleep=sleeps.append,
    )

    assert service.translate_many(["A", "B", "C"]) == ["[EN] A", "[EN] B", "[EN] C"]
    assert sleeps == [0.25]
