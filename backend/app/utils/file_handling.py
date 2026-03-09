import io
import os

import aiofiles
from fastapi import UploadFile
from PyPDF2 import PdfReader
from docx import Document

from app.config import settings

ALLOWED_EXTENSIONS = {ext.strip() for ext in settings.allowed_extensions.split(",")}


def validate_file(file: UploadFile) -> None:
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}"
            )


def _extract_text_from_pdf(content: bytes) -> str:
    reader = PdfReader(io.BytesIO(content))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_text_from_docx(content: bytes) -> str:
    doc = Document(io.BytesIO(content))
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def _extract_text_from_txt(content: bytes) -> str:
    return content.decode("utf-8")


async def read_upload_text(file: UploadFile) -> str:
    content = await file.read()
    ext = ""
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()

    if ext == ".pdf":
        return _extract_text_from_pdf(content)
    elif ext in (".docx", ".doc"):
        return _extract_text_from_docx(content)
    else:
        return _extract_text_from_txt(content)


async def save_upload_file(file: UploadFile) -> str:
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, file.filename or "transcript.txt")

    content = await file.read()
    async with aiofiles.open(file_path, "wb") as f:
        await f.write(content)

    await file.seek(0)
    return file_path
