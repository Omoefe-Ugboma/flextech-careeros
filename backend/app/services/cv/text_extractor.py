from pathlib import Path

from docx import Document
from pypdf import PdfReader


def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)

    extracted_pages = []

    for page in reader.pages:
        page_text = page.extract_text() or ""
        extracted_pages.append(page_text)

    return "\n".join(extracted_pages).strip()


def extract_text_from_docx(file_path: str) -> str:
    document = Document(file_path)

    paragraphs = []

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()

        if text:
            paragraphs.append(text)

    return "\n".join(paragraphs)


def extract_cv_text(file_path: str) -> str:
    path = Path(file_path)

    extension = path.suffix.lower()

    if extension == ".pdf":
        return extract_text_from_pdf(file_path)

    if extension == ".docx":
        return extract_text_from_docx(file_path)

    raise ValueError("Unsupported CV document format.")