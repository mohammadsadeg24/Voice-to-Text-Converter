@echo off
setlocal enabledelayedexpansion
title WhisperFlow - Build Windows EXE Package
color 0A

cd /d "%~dp0"

echo ===============================================================================
echo        WhisperFlow Studio Pro -- Windows Executable Builder (.EXE)
echo ===============================================================================
echo.

set "PYTHON_EXE="
if exist "C:\Users\Mohammadsadegh\AppData\Local\Programs\Python\Python313\python.exe" (
    set "PYTHON_EXE=C:\Users\Mohammadsadegh\AppData\Local\Programs\Python\Python313\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" build_exe.py

if %errorlevel% neq 0 (
    echo.
    echo ===============================================================================
    echo [ERROR] An issue occurred during EXE build.
    echo ===============================================================================
    echo.
)

pause

