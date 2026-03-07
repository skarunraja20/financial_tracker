@echo off
TITLE Financial Tracker - Installer
echo ============================================
echo  Financial Tracker - Installation
echo ============================================
echo.

python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
python -m venv "%~dp0venv"
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to create virtual environment.
    pause
    exit /b 1
)

echo [2/4] Installing dependencies...
call "%~dp0venv\Scripts\activate.bat"
pip install --upgrade pip --quiet
pip install -r "%~dp0requirements.txt"
IF %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)

echo [3/4] Creating data directories...
if not exist "%~dp0data\backups" mkdir "%~dp0data\backups"

echo [4/4] Creating __init__.py files...
type nul > "%~dp0app\__init__.py"
type nul > "%~dp0app\core\__init__.py"
type nul > "%~dp0app\models\__init__.py"
type nul > "%~dp0app\ui\__init__.py"
type nul > "%~dp0app\ui\debt\__init__.py"
type nul > "%~dp0app\ui\equity\__init__.py"
type nul > "%~dp0app\ui\gold\__init__.py"
type nul > "%~dp0app\ui\real_estate\__init__.py"
type nul > "%~dp0app\ui\liabilities\__init__.py"
type nul > "%~dp0app\ui\reports\__init__.py"
type nul > "%~dp0app\ui\import_export\__init__.py"
type nul > "%~dp0app\ui\settings\__init__.py"
type nul > "%~dp0app\services\__init__.py"

echo.
echo ============================================
echo  Installation complete!
echo  Run run.bat to launch the application.
echo ============================================
pause
