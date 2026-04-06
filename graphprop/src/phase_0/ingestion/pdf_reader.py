from pathlib import Path
from PyPDF2 import PdfReader


def extract_text_from_pdf(pdf_path: str | Path) -> str:
    """
    Extract plain text from a PDF.
    """
    path = Path(pdf_path)
    reader = PdfReader(str(path))
    text_parts: list[str] = []

    for page in reader.pages:
        text_parts.append(page.extract_text() or "")

    return "\n".join(text_parts)
