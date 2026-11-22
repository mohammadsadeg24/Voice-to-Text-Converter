@echo off
setlocal enabledelayedexpansion
title WhisperFlow - Quick Restore Torch (Standard)
color 0B
cd /d "%~dp0"

set "PYTHON_EXE=C:\Users\Mohammadsadegh\AppData\Local\Programs\Python\Python313\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo ===============================================================================
echo   WhisperFlow Studio Pro - Fast Torch Re-installer
echo ===============================================================================
echo.
echo Installing standard PyTorch from PyPI (Fast download ~140 MB)...
"%PYTHON_EXE%" -m pip install torch

echo.
echo Done! Now you can run run.bat
pause

