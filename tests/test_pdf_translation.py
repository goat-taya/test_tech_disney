from pypdf import PdfReader
from reportlab.pdfgen import canvas

from translator.pdf import translate_pdf


def test_pdf_generates_new_pdf_with_translated_text(tmp_path):
    source = tmp_path / "brochure.pdf"
    output = tmp_path / "brochure_en.pdf"

    pdf = canvas.Canvas(str(source))
    pdf.drawString(72, 720, "Description produit francaise")
    pdf.save()

    translate_pdf(source, output)

    assert output.exists()
    text = "\n".join(page.extract_text() or "" for page in PdfReader(str(output)).pages)
    assert "[EN] Description produit francaise" in text
