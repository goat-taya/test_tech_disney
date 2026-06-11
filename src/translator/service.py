from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from translator.mock_service import translate


TranslateBackend = Callable[[str, str, str], str]


@dataclass
class TranslationService:
    """Scalable translation facade around the current mock backend.

    The mock still translates one string at a time, but callers use this facade
    so a real API client can later add bulk requests, throttling, and retries in
    one place.
    """

    backend: TranslateBackend = translate
    source: str = "fr"
    target: str = "en"
    batch_size: int = 100
    cache: dict[tuple[str, str, str], str] = field(default_factory=dict)

    def translate_text(self, text: str) -> str:
        if not text.strip():
            return text

        key = (self.source, self.target, text)
        if key not in self.cache:
            self.cache[key] = self.backend(text, self.source, self.target)
        return self.cache[key]

    def translate_many(self, texts: Iterable[str]) -> list[str]:
        items = list(texts)
        unique_uncached = []
        seen = set()

        for text in items:
            if not text.strip():
                continue

            key = (self.source, self.target, text)
            if key not in self.cache and key not in seen:
                unique_uncached.append(text)
                seen.add(key)

        for batch in _chunks(unique_uncached, self.batch_size):
            for text in batch:
                self.translate_text(text)

        return [self.translate_text(text) if text.strip() else text for text in items]


def _chunks(items: list[str], size: int) -> Iterable[list[str]]:
    if size < 1:
        raise ValueError("batch_size must be greater than zero")

    for index in range(0, len(items), size):
        yield items[index : index + size]
