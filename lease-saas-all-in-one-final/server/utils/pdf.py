from typing import Tuple
from pypdf import PdfReader
def extract_text_from_pdf(file) -> Tuple[str, str]:
    reader = PdfReader(file)
    pages = []
    for p in reader.pages:
        try:
            pages.append(p.extract_text() or "")
        except Exception:
            pages.append("")
    text = "\n".join(pages)
    excerpt = text[:2000]
    return text, excerpt
