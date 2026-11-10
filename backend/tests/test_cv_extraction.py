
from types import SimpleNamespace

from app.services.cv import text_extractor


def test_extract_pdf_text(monkeypatch, tmp_path):
    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(b"%PDF-1.4")

    fake_pages = [
        SimpleNamespace(extract_text=lambda: "John Doe"),
        SimpleNamespace(extract_text=lambda: "Python Developer"),
    ]

    monkeypatch.setattr(
        text_extractor,
        "PdfReader",
        lambda _: SimpleNamespace(pages=fake_pages),
    )

    extracted_text = text_extractor.extract_cv_text(str(pdf_path))

    assert extracted_text == "John Doe\nPython Developer"
