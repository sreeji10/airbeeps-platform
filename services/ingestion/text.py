from __future__ import annotations

import io
from pathlib import Path

from pypdf import PdfReader


SUPPORTED_TEXT_EXTENSIONS = {".txt", ".md", ".markdown", ".json", ".csv", ".py"}


def extract_text(*, filename: str, content_type: str | None, content: bytes) -> str:
    extension = Path(filename).suffix.lower()
    if content_type == "application/pdf" or extension == ".pdf":
        return _extract_pdf_text(content)

    if (
        extension in SUPPORTED_TEXT_EXTENSIONS
        or content_type
        and content_type.startswith("text/")
    ):
        return content.decode("utf-8", errors="ignore")

    return content.decode("utf-8", errors="ignore")


def _extract_pdf_text(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def chunk_text(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    normalized = " ".join(text.split())
    if not normalized:
        return []

    size = max(200, chunk_size)
    overlap_size = max(0, min(overlap, size // 2))
    step = size - overlap_size
    chunks: list[str] = []

    cursor = 0
    while cursor < len(normalized):
        window = normalized[cursor : cursor + size]
        if not window:
            break

        if cursor + size < len(normalized):
            split_idx = window.rfind(" ")
            if split_idx > int(size * 0.5):
                window = window[:split_idx]

        chunks.append(window.strip())
        cursor += step

    return [chunk for chunk in chunks if chunk]
