import os

from fastapi import UploadFile

from app.config import settings

ALLOWED_EXTENSIONS = {ext.strip() for ext in settings.allowed_extensions.split(",")}


def validate_file(file: UploadFile) -> None:
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"File type '{ext}' not allowed. Allowed: {ALLOWED_EXTENSIONS}"
            )


async def read_upload_text(file: UploadFile) -> str:
    content = await file.read()
    return content.decode("utf-8")


async def save_upload_file(file: UploadFile) -> str:
    os.makedirs(settings.upload_dir, exist_ok=True)
    file_path = os.path.join(settings.upload_dir, file.filename or "transcript.txt")

    content = await file.read()
    with open(file_path, "wb") as f:
        f.write(content)

    await file.seek(0)
    return file_path
