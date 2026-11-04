import os
import logging
from typing import Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import docx
except ImportError:
    docx = None
    logger.warning("python-docx не установлен. .docx файлы не будут обрабатываться.")

try:
    import pdfplumber
except ImportError:
    pdfplumber = None
    logger.warning("pdfplumber не установлен.")

try:
    import openpyxl
except ImportError:
    openpyxl = None
    logger.warning("openpyxl не установлен.")

try:
    import pandas as pd
except ImportError:
    pd = None
    logger.warning("pandas не установлен.")


def extract_text(filepath: str) -> Optional[str]:
    if not os.path.exists(filepath):
        logger.error(f"Файл не найден: {filepath}")
        return None

    ext = os.path.splitext(filepath)[1].lower()

    try:
        if ext == ".txt":
            return _extract_txt(filepath)
        elif ext == ".docx":
            return _extract_docx(filepath)
        elif ext == ".pdf":
            return _extract_pdf(filepath)
        elif ext == ".xlsx":
            return _extract_xlsx(filepath)
        elif ext == ".csv":
            return _extract_csv(filepath)
        else:
            logger.error(f"Неподдерживаемый формат файла: {ext}")
            return None
    except Exception as e:
        logger.exception(f"Ошибка при извлечении текста из {filepath}: {e}")
        return None

def _extract_txt(filepath: str) -> str:
    with open(filepath, "r", encoding="utf-8") as f:
        return f.read()


def _extract_docx(filepath: str) -> str:
    if docx is None:
        logger.error("Библиотека python-docx не установлена.")
        return None
    document = docx.Document(filepath)
    paragraphs = [para.text for para in document.paragraphs]
    return "\n".join(paragraphs)


def _extract_pdf(filepath: str) -> Optional[str]:
    if pdfplumber is None:
        logger.error("Библиотека pdfplumber не установлена.")
        return None

    text_parts = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

    if not text_parts:
        logger.warning(f"PDF без текстового слоя: {filepath}")
        return None

    return "\n".join(text_parts)


def _extract_xlsx(filepath: str) -> str:
    if openpyxl is None:
        logger.error("Библиотека openpyxl не установлена.")
        return None

    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    lines = []
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            row_values = [str(cell) for cell in row if cell is not None]
            if row_values:
                lines.append("\t".join(row_values))
    wb.close()
    return "\n".join(lines)


def _extract_csv(filepath: str) -> str:
    if pd is None:
        logger.error("Библиотека pandas не установлена.")
        return None
    try:
        df = pd.read_csv(filepath, sep=None, engine="python")
        return df.to_csv(index=False, sep="\t")
    except Exception as e:
        logger.warning(f"pandas не смог прочитать CSV ({e})")
        with open(filepath, "r", encoding="utf-8") as f:
            return f.read()