@echo off
title Financial Tracker — Reset Data

echo.
echo  ============================================================
echo   Financial Tracker — Reset to First-Time Setup
echo  ============================================================
echo.
echo  WARNING: This will permanently delete ALL your financial data,
echo           including the database, all entries, and backups.
echo.
echo  This CANNOT be undone.
echo.
set /p "CONFIRM=  Type YES to confirm reset, or press Enter to cancel: "

if /i not "%CONFIRM%"=="YES" (
    echo.
    echo  Reset cancelled. No data was deleted.
    pause
    exit /b 0
)

echo.
echo  Deleting data...

set "DATA_DIR=%~dp0data"

if exist "%DATA_DIR%\financial_app.db" (
    del /f /q "%DATA_DIR%\financial_app.db"
    echo   - Deleted: data\financial_app.db
)

if exist "%DATA_DIR%\backups" (
    rmdir /s /q "%DATA_DIR%\backups"
    echo   - Deleted: data\backups\
)

echo.
echo  Reset complete.
echo  The next time you launch the app it will show the first-time setup wizard.
echo.
pause
