@echo off
setlocal enabledelayedexpansion
title WhisperFlow Pro - Speech to Text App
color 0B

:: Ensure working directory is this folder
cd /d "%~dp0"

:: Detect Python executable
set "PYTHON_EXE="
if exist "C:\Users\Mohammadsadegh\AppData\Local\Programs\Python\Python313\python.exe" (
    set "PYTHON_EXE=C:\Users\Mohammadsadegh\AppData\Local\Programs\Python\Python313\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo Starting WhisperFlow Pro Windows Desktop Application...
"%PYTHON_EXE%" desktop_app.py

if %errorlevel% neq 0 (
    echo.
    echo ===============================================================================
    echo [ERROR] An error occurred while running the application.
    echo ===============================================================================
    pause
)
