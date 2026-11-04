import io
import json
import uuid
import os
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from app.db import get_session
from app.models import AnalysisSession, File as FileModel

router = APIRouter(prefix="/api/export", tags=["export"])
async def _get_session_data(session_id: uuid.UUID, db: AsyncSession):
    stmt = (
        select(AnalysisSession)
        .where(AnalysisSession.id == session_id)
        .options(selectinload(AnalysisSession.files).selectinload(FileModel.reviews))
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    data = []
    for file in session.files:
        for review in file.reviews:
            data.append({
                "Файл": file.filename,
                "Текст": review.text,
                "Язык": review.language,
                "Тональность": review.sentiment_label,
                "Уверенность": "вручную" if review.sentiment_manual else review.sentiment_confidence,
                "Заметка": review.note or ""
            })
    return data

@router.get("/csv/{session_id}")
async def export_csv(session_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    data = await _get_session_data(session_id, db)
    df = pd.DataFrame(data)
    stream = io.BytesIO()
    df.to_csv(stream, index=False, sep=';', encoding='utf-8-sig')
    headers = {
        "Content-Disposition": f'attachment; filename="report_{session_id}.csv"'
    }
    return Response(content=stream.getvalue(), media_type="text/csv", headers=headers)

@router.get("/excel/{session_id}")
async def export_excel(session_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    data = await _get_session_data(session_id, db)
    df = pd.DataFrame(data)
    stream = io.BytesIO()
    with pd.ExcelWriter(stream, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Результаты')
    headers = {
        "Content-Disposition": f'attachment; filename="report_{session_id}.xlsx"'
    }
    return Response(
        content=stream.getvalue(), 
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", 
        headers=headers
    )

@router.get("/pdf/{session_id}")
async def export_pdf(session_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    data = await _get_session_data(session_id, db)
    if not data:
        raise HTTPException(status_code=404, detail="Нет данных для экспорта")
    stream = io.BytesIO()
    doc = SimpleDocTemplate(stream, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
    font_name = "Helvetica"
    possible_fonts = [
        "C:\\Windows\\Fonts\\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf"
    ]
    for font_path in possible_fonts:
        if os.path.exists(font_path):
            pdfmetrics.registerFont(TTFont('CustomFont', font_path))
            font_name = 'CustomFont'
            break
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='Title', parent=styles['Heading1'], fontName=font_name, alignment=1, spaceAfter=20)
    elements.append(Paragraph(f"Отчёт по анализу тональности", title_style))
    elements.append(Paragraph(f"ID сессии: {session_id}", ParagraphStyle(name='Normal', fontName=font_name, fontSize=10, alignment=1)))
    elements.append(Spacer(1, 20))
    table_data = [["Файл", "Текст", "Язык", "Тональность", "Уверенность"]]
    cell_style = ParagraphStyle(name='Cell', fontName=font_name, fontSize=8)
    for row in data:
        text_para = Paragraph(row["Текст"][:200] + "..." if len(row["Текст"]) > 200 else row["Текст"], cell_style)
        conf = row["Уверенность"]
        conf_str = str(round(conf * 100)) + "%" if isinstance(conf, float) else str(conf)
        table_data.append([
            Paragraph(row["Файл"], cell_style),
            text_para,
            row["Язык"],
            row["Тональность"],
            conf_str
        ])
    col_widths = [100, 450, 50, 80, 80]
    t = Table(table_data, colWidths=col_widths)
    table_style = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, -1), font_name),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#e5e7eb')),
    ]
    for i, row in enumerate(data, start=1):
        if row["Тональность"] == "positive":
            table_style.append(('BACKGROUND', (3, i), (3, i), colors.HexColor('#10b981')))
            table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.white))
        elif row["Тональность"] == "negative":
            table_style.append(('BACKGROUND', (3, i), (3, i), colors.HexColor('#ef4444')))
            table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.white))
        elif row["Тональность"] == "neutral":
            table_style.append(('BACKGROUND', (3, i), (3, i), colors.HexColor('#6b7280')))
            table_style.append(('TEXTCOLOR', (3, i), (3, i), colors.white))
    t.setStyle(TableStyle(table_style))
    elements.append(t)
    doc.build(elements)
    headers = {
        "Content-Disposition": f'attachment; filename="report_{session_id}.pdf"'
    }
    return Response(content=stream.getvalue(), media_type="application/pdf", headers=headers)

@router.get("/json/{session_id}")
async def export_json(session_id: uuid.UUID, db: AsyncSession = Depends(get_session)):
    stmt = (
        select(AnalysisSession)
        .where(AnalysisSession.id == session_id)
        .options(selectinload(AnalysisSession.files).selectinload(FileModel.reviews))
    )
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Сессия не найдена")
    data = {
        "session": {
            "name": session.name,
            "status": session.status,
            "created_at": session.created_at.isoformat()
        },
        "files": []
    }
    for file in session.files:
        file_data = {
            "filename": file.filename,
            "extension": file.extension,
            "reviews": []
        }
        for review in file.reviews:
            file_data["reviews"].append({
                "text": review.text,
                "language": review.language,
                "sentiment_label": review.sentiment_label,
                "sentiment_confidence": review.sentiment_confidence,
                "sentiment_manual": review.sentiment_manual,
                "note": review.note
            })
        data["files"].append(file_data)
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    headers = {
        "Content-Disposition": f'attachment; filename="session_{session_id}.json"'
    }
    return Response(content=json_str, media_type="application/json", headers=headers)