import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status


CV_STORAGE_DIR = Path("storage/cvs")

ALLOWED_EXTENSIONS = {
    ".pdf",
    ".docx",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


async def save_cv_file(file: UploadFile) -> dict:
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No filename provided.",
        )

    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF and DOCX files are allowed.",
        )

    content = await file.read(MAX_FILE_SIZE + 1)

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is empty.",
        )

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="CV file must not exceed 5 MB.",
        )

    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid PDF.",
        )

    if extension == ".docx" and not content.startswith(b"PK"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded file is not a valid DOCX file.",
        )

    CV_STORAGE_DIR.mkdir(parents=True, exist_ok=True)

    stored_filename = f"{uuid.uuid4().hex}{extension}"
    file_path = CV_STORAGE_DIR / stored_filename

    file_path.write_bytes(content)

    return {
        "original_filename": file.filename,
        "stored_filename": stored_filename,
        "file_path": str(file_path),
        "file_size": len(content),
        "file_type": extension.lstrip("."),
    }