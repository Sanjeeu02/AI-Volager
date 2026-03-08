@echo off
TITLE AI Voyager - One Click Launcher
echo 🚀 Launching AI Voyager...
echo.
python start_voyager.py
if %errorlevel% neq 0 (
    echo.
    echo ❌ ERROR: Failed to start. Make sure Python and Streamlit are installed!
    pause
)
pause
