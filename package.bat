@echo off
setlocal enabledelayedexpansion
title Financial Tracker — Package Builder

set "APP_DIR=%~dp0"
cd /d "%APP_DIR%"

echo.
echo  ============================================================
echo   Financial Tracker — Portable Windows Package Builder
echo  ============================================================
echo.

:: ── Check venv exists ────────────────────────────────────────────────────────
if not exist "venv\Scripts\activate.bat" (
    echo  [ERROR] Virtual environment not found.
    echo          Run install.bat first to create it.
    pause
    exit /b 1
)

:: ── Activate venv ────────────────────────────────────────────────────────────
echo  [1/5] Activating virtual environment...
call venv\Scripts\activate.bat

:: ── Install / upgrade PyInstaller ────────────────────────────────────────────
echo  [2/5] Installing PyInstaller...
pip install pyinstaller --quiet --upgrade
if errorlevel 1 (
    echo  [ERROR] Failed to install PyInstaller.
    pause
    exit /b 1
)

:: ── Clean previous build artefacts ───────────────────────────────────────────
echo  [3/5] Cleaning previous build...
if exist "build"  rmdir /s /q "build"
if exist "dist"   rmdir /s /q "dist"
if exist "FinancialTracker_Portable.zip" del /f /q "FinancialTracker_Portable.zip"

:: ── Run PyInstaller ──────────────────────────────────────────────────────────
echo  [4/5] Building application (this may take 2-5 minutes)...
echo.
pyinstaller FinancialTracker.spec --noconfirm
echo.
if errorlevel 1 (
    echo  [ERROR] PyInstaller build failed.
    echo          Check the output above for details.
    pause
    exit /b 1
)

:: ── Verify the exe was created ───────────────────────────────────────────────
if not exist "dist\FinancialTracker\FinancialTracker.exe" (
    echo  [ERROR] Expected exe not found at dist\FinancialTracker\FinancialTracker.exe
    pause
    exit /b 1
)

:: ── Create ZIP archive ───────────────────────────────────────────────────────
echo  [5/5] Creating ZIP archive...
powershell -NoProfile -Command ^
    "Compress-Archive -Path 'dist\FinancialTracker' -DestinationPath 'FinancialTracker_Portable.zip' -Force"

if errorlevel 1 (
    echo.
    echo  [WARNING] ZIP creation failed.
    echo            Manually zip the folder:  dist\FinancialTracker\
) else (
    echo.
    echo  ============================================================
    echo   BUILD SUCCESSFUL
    echo  ============================================================
    echo.
    echo   Portable ZIP :  %APP_DIR%FinancialTracker_Portable.zip
    echo   Raw folder   :  %APP_DIR%dist\FinancialTracker\
    echo.
    echo   To run on another PC:
    echo     1. Copy FinancialTracker_Portable.zip to the target machine
    echo     2. Extract the ZIP anywhere (e.g. Desktop or D:\)
    echo     3. Open the FinancialTracker folder
    echo     4. Double-click  FinancialTracker.exe
    echo.
    echo   The app creates its data\ folder automatically on first run.
    echo  ============================================================
)

echo.
pause
