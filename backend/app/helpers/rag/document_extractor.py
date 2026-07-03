"""Extract plain text from uploaded knowledge-base files."""

import io
import os
from typing import Tuple

from fastapi import HTTPException

ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".pdf", ".docx", ".doc"}
MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB


def _ext(filename: str) -> str:
    return os.path.splitext(filename or "")[1].lower()


def extract_text_from_bytes(raw: bytes, filename: str) -> Tuple[str, str]:
    ext = _ext(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            400,
            f"Unsupported file type '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    if len(raw) > MAX_FILE_BYTES:
        raise HTTPException(400, "File too large. Maximum size is 10 MB.")
    if not raw.strip():
        raise HTTPException(400, "File is empty.")

    if ext in {".txt", ".md", ".csv"}:
        for encoding in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                return raw.decode(encoding), ext.lstrip(".")
            except UnicodeDecodeError:
                continue
        raise HTTPException(400, "Could not decode text file.")

    if ext == ".pdf":
        return _extract_pdf(raw), "pdf"

    if ext in {".docx", ".doc"}:
        if ext == ".doc":
            raise HTTPException(400, "Legacy .doc files are not supported. Please upload .docx or .pdf.")
        return _extract_docx(raw), "docx"

    raise HTTPException(400, "Unsupported file type.")


def _extract_pdf(raw: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise HTTPException(500, "PDF support is not installed on the server.") from exc

    reader = PdfReader(io.BytesIO(raw))
    pages = []
    for page in reader.pages:
        text = page.extract_text() or ""
        if text.strip():
            pages.append(text.strip())
    if not pages:
        raise HTTPException(400, "No readable text found in this PDF. Try a text-based PDF or paste content manually.")
    return "\n\n".join(pages)


def _extract_docx(raw: bytes) -> str:
    try:
        from docx import Document as DocxDocument
    except ImportError as exc:
        raise HTTPException(500, "DOCX support is not installed on the server.") from exc

    doc = DocxDocument(io.BytesIO(raw))
    paragraphs = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    if not paragraphs:
        raise HTTPException(400, "No readable text found in this Word document.")
    return "\n\n".join(paragraphs)
