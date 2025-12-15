@echo off
echo =============================================================
echo  ✨ InK Studio
echo  AI-Powered Document Transformation
echo =============================================================
echo.
echo Installing dependencies...
pip install -r requirements.txt
echo.
echo Starting server...
echo.
echo ✓ Server will be available at: http://localhost:8000
echo.
python start_fastapi.py
