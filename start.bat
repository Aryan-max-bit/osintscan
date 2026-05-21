@echo off
REM One-click start for Windows — keeps terminal open so you see errors
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found.
    echo Run first: python -m venv venv
    echo Then:       venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

call venv\Scripts\activate.bat
echo.
echo Starting Flask server...
echo.
python run.py
pause
