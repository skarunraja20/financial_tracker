@echo off
TITLE Financial Tracker
cd /d "%~dp0"
call "%~dp0venv\Scripts\activate.bat"
python "%~dp0main.py"
IF %ERRORLEVEL% NEQ 0 (
    echo.
    echo Application exited with an error. Check the output above.
    pause
)
