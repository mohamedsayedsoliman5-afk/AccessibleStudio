@echo off
title AccessibleStudio Console Launcher
cd /d "%~dp0"
echo ============================================================
echo Starting AccessibleStudio in Diagnostic Console Mode...
echo ============================================================
AccessibleStudio.exe %*
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ============================================================
    echo AccessibleStudio exited with error code %ERRORLEVEL%.
    echo Please review the errors above or check studio_debug.log / crash.log.
    echo ============================================================
    pause
)
