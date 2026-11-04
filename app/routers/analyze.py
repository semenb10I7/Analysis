import logging
from app.schemas import ResultFileOut, StatusResponse, ReviewUpdate, ReviewOut
import uuid
from typing import Annotated
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db import get_session, async_session_maker
from app.language import detect_language
from app.models import AnalysisSession, File as FileModel, Review
from app.schemas import ResultFileOut, StatusResponse
from app.sentiment import predict_sentiment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api", tags=["analyze"])

async def _run_analysis(session_id: uuid.UUID):
    async with async_session_maker() as db:
        session = await db.get(AnalysisSession, session_id)
        if not session:
            return
        session.status = "processing"
        await db.commit()
        stmt = (
            select(FileModel)
            .where(FileModel.session_id == session_id)
            .options(selectinload(FileModel.reviews))
        )
        result = await db.execute(stmt)
        files = result.scalars().all()
        for file in files:
            for review in file.reviews:
                if not review.text.strip():
                    continue
                if not review.language:
                    lang = detect_language(review.text) or "ru"
                    review.language = lang
                if not review.sentiment_manual:
                    res = predict_sentiment(review.text, lang=review.language)
                    if res:
                        review.sentiment_label = res["label"]
                        review.sentiment_confidence = res["confidence"]
                
                await db.flush()
        session.status = "completed"
        await db.commit()
        logger.info(f"Анализ сессии {session_id} завершён")

@router.post("/analyze/{session_id}", status_code=202)
async def start_analysis(
    session_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    session = await db.get(AnalysisSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    if session.status == "processing":
        raise HTTPException(status_code=409, detail="Анализ уже идёт")
    background_tasks.add_task(_run_analysis, session_id)
    return {"message": "Анализ запущен", "session_id": session_id}

@router.get("/status/{session_id}", response_model=StatusResponse)
async def get_status(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    session = await db.get(AnalysisSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    total_stmt = (
        select(func.count(Review.id))
        .join(FileModel)
        .where(FileModel.session_id == session_id)
    )
    total = (await db.execute(total_stmt)).scalar() or 0

    processed_stmt = (
        select(func.count(Review.id))
        .join(FileModel)
        .where(FileModel.session_id == session_id, Review.sentiment_label.isnot(None))
    )
    processed = (await db.execute(processed_stmt)).scalar() or 0

    progress = int((processed / total * 100)) if total > 0 else 100

    return StatusResponse(
        session_id=session.id,
        status=session.status,
        processed=processed,
        total=total,
        progress=progress,
    )

@router.get("/results/{session_id}", response_model=list[ResultFileOut])
async def get_results(
    session_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    stmt = (
        select(FileModel)
        .where(FileModel.session_id == session_id)
        .options(selectinload(FileModel.reviews))
    )
    result = await db.execute(stmt)
    files = result.scalars().all()
    if not files:
        raise HTTPException(status_code=404, detail="Файлы для этой сессии не найдены")
    return files

@router.patch("/reviews/{review_id}", response_model=ReviewOut)
async def update_review_sentiment(
    review_id: uuid.UUID,
    payload: ReviewUpdate,
    db: Annotated[AsyncSession, Depends(get_session)],
):
    review = await db.get(Review, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Отзыв не найден")
    review.sentiment_label = payload.sentiment_label
    review.sentiment_confidence = None 
    review.sentiment_manual = True
    await db.commit()
    await db.refresh(review)
    return review