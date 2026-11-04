import json
import uuid
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.db import get_session
from app.models import AnalysisSession, File as FileModel, Review

router = APIRouter(prefix="/api/session", tags=["session"])
@router.post("/load")
async def load_session(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_session)
):
    try:
        content = await file.read()
        data = json.loads(content)
    except Exception:
        raise HTTPException(status_code=400, detail="Неверный формат JSON-файла")
    new_session = AnalysisSession(name=data.get("session", {}).get("name", "Загруженная сессия"), status="completed")
    db.add(new_session)
    await db.flush()
    for file_data in data.get("files", []):
        new_file = FileModel(
            session_id=new_session.id,
            filename=file_data["filename"],
            filepath="",
            extension=file_data.get("extension", ""),
            status="extracted"
        )
        db.add(new_file)
        await db.flush()
        for review_data in file_data.get("reviews", []):
            new_review = Review(
                file_id=new_file.id,
                text=review_data["text"],
                language=review_data.get("language"),
                sentiment_label=review_data.get("sentiment_label"),
                sentiment_confidence=review_data.get("sentiment_confidence"),
                sentiment_manual=review_data.get("sentiment_manual", False),
                note=review_data.get("note")
            )
            db.add(new_review)
    await db.commit()
    return {"session_id": new_session.id}