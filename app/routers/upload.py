import logging
import os
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.extract_text import extract_text
from app.models import AnalysisSession, File as FileModel, Review
from app.schemas import FileOut, SessionOut, UploadResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["upload"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXT = {".txt", ".docx", ".pdf", ".xlsx", ".csv"}

@router.post("/upload", response_model=UploadResponse)
async def upload_files(
    files: list[UploadFile] = File(...),
    session: AsyncSession = Depends(get_session),
):
    if not files:
        raise HTTPException(status_code=400, detail="Не передано ни одного файла")
    analysis = AnalysisSession(status="pending")
    session.add(analysis)
    await session.flush()
    saved_files: list[FileModel] = []
    skipped: list[str] = []
    for upload in files:
        ext = os.path.splitext(upload.filename or "")[1].lower()
        if ext not in ALLOWED_EXT:
            skipped.append(f"{upload.filename} (неподдерживаемый формат)")
            continue
        unique_name = f"{uuid.uuid4().hex}{ext}"
        disk_path = os.path.join(UPLOAD_DIR, unique_name)
        try:
            contents = await upload.read()
            with open(disk_path, "wb") as f:
                f.write(contents)
        except Exception as e:
            logger.exception(f"Ошибка сохранения {upload.filename}: {e}")
            skipped.append(f"{upload.filename} (ошибка записи)")
            continue
        text = extract_text(disk_path)
        file_status = "extracted" if text else "error"
        extraction_error = None if text else "Не удалось извлечь текст"
        file_model = FileModel(
            session_id=analysis.id,
            filename=upload.filename or unique_name,
            filepath=disk_path,
            extension=ext,
            size_bytes=len(contents),
            extracted_text=text,
            extraction_error=extraction_error,
            status=file_status,
        )
        session.add(file_model)
        await session.flush()
        if text:
            session.add(Review(file_id=file_model.id, text=text))
        saved_files.append(file_model)
        if not text:
            skipped.append(f"{upload.filename} (без текстового слоя)")
    if not saved_files:
        analysis.status = "error"
    else:
        analysis.status = "uploaded"
    await session.commit()
    await session.refresh(analysis)
    for f in saved_files:
        await session.refresh(f)
    return UploadResponse(
        session=SessionOut.model_validate(analysis),
        files=[FileOut.model_validate(f) for f in saved_files],
        skipped=skipped,
    )