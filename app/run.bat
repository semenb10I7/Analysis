@echo off
chcp 65001 >nul
echo   ЗАПУСК ПРИЛОЖЕНИЯ АНАЛИЗА ТОНАЛЬНОСТИ
echo.
if not exist ".venv\Scripts\activate.bat" (
    echo [ОШИБКА] Виртуальное окружение .venv не найдено!
    echo Убедитесь, что вы установили зависимости согласно инструкции.
    pause
    exit /b
)
call .venv\Scripts\activate.bat
echo [1/2] Запуск локального сервера...
echo [2/2] Открытие браузера...
start "" cmd /c "timeout /t 2 >nul && start http://127.0.0.1:8000"
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause