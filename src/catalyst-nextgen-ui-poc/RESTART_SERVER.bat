@echo off
echo ==========================================
echo  Restarting AI Document Transformer
echo ==========================================
echo.

echo Stopping any existing servers...
taskkill /F /IM python.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo Starting server...
cd /d "%~dp0"
.venv\Scripts\python.exe -m uvicorn app_fastapi:app --host 0.0.0.0 --port 8000 --reload

pause


