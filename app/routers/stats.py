import re
import uuid
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db import get_session
from app.models import AnalysisSession, File as FileModel

router = APIRouter(prefix="/api", tags=["stats"])
STOP_WORDS = set("""
и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по только ее мне было вот от меня еще нет о из ему теперь когда даже ну вдруг ли если уже или ни быть был него до вас нибудь опять уж вам ведь там потом себя ничего ей может они тут где есть надо ней ней для мы тебя их чем была сам чтоб без будто чего раз тоже себе под будет ж тогда кто этот того потому этого какой совсем ним здесь этом один почти мой тем чтобы нее сейчас были куда зачем сказать всех никогда сегодня можно при наконец два об другой хоть после над больше тот через эти нас про всего них какая много разве три эту моя впрочем хорошо свою этой перед иногда лучше чуть том нельзя такой им более всегда конечно всю между
the a an and or but if while of to in for on with without at by from up about into over after beneath under above is are was were be been being have has had do does did not no nor so as than that this these those it its i you he she they we me him her them us my your his their our
""".split())
@router.get("/stats/{session_id}")
async def get_stats(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    stmt = (
        select(AnalysisSession)
        .where(AnalysisSession.id == session_id)
        .options(selectinload(AnalysisSession.files).selectinload(FileModel.reviews))
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}
    all_texts = []
    for file in session.files:
        for review in file.reviews:
            if review.sentiment_label in sentiment_counts:
                sentiment_counts[review.sentiment_label] += 1
            if review.text:
                all_texts.append(review.text)
    words = []
    for text in all_texts:
        tokens = re.findall(r'[а-яА-ЯёЁa-zA-Z]{3,}', text.lower())
        for token in tokens:
            if token not in STOP_WORDS:
                words.append(token)
    word_frequencies = Counter(words).most_common(50) # Топ-50 слов
    return {
        "sentiment_counts": sentiment_counts,
        "total_reviews": sum(sentiment_counts.values()),
        "word_frequencies": [{"word": w, "count": c} for w, c in word_frequencies]
    }