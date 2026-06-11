from pathlib import Path

from pypdf import PdfReader
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from translator.service import TranslationService


def translate_pdf(
    input_path: str | Path,
    output_path: str | Path,
    service: TranslationService | None = None,
) -> Path:
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    service = service or TranslationService()

    reader = PdfReader(str(input_path))
    page_texts = [(page.extract_text() or "").strip() for page in reader.pages]
    translated_pages = service.translate_many(page_texts)

    pdf = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter

    for page_text in translated_pages or [""]:
        text_object = pdf.beginText(72, height - 72)
        text_object.setFont("Helvetica", 11)
        for line in _wrap_lines(page_text):
            text_object.textLine(line)
        pdf.drawText(text_object)
        pdf.showPage()

    pdf.save()
    return output_path


def _wrap_lines(text: str, max_chars: int = 90) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines() or [""]:
        words = raw_line.split()
        current = ""
        for word in words:
            candidate = f"{current} {word}".strip()
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines or [""]
