@echo off
setlocal enabledelayedexpansion
title WhisperFlow - Install Torch with NVIDIA GPU (CUDA 12.6)
color 0A
cd /d "%~dp0"

set "PYTHON_EXE=C:\Users\Mohammadsadegh\AppData\Local\Programs\Python\Python313\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"

echo ===============================================================================
echo   WhisperFlow Studio Pro - PyTorch CUDA 12.6 Installer (Python 3.13)
echo ===============================================================================
echo.
echo [*] Python: %PYTHON_EXE%
echo [*] Downloading and Installing PyTorch for CUDA 12.6...
echo [*] (Please keep your VPN/Internet connected, downloading ~2.3 GB...)
echo.

"%PYTHON_EXE%" -m pip install --upgrade torch --index-url https://download.pytorch.org/whl/cu126

echo.
echo ===============================================================================
echo [*] Verifying GPU status...
echo ===============================================================================
"%PYTHON_EXE%" -c "import torch; ok=torch.cuda.is_available(); name=torch.cuda.get_device_name(0) if ok else 'N/A'; print(''); print('CUDA AVAILABLE :', ok); print('GPU DEVICE NAME:', name); print(''); print('SUCCESS: PyTorch with GPU acceleration is READY!' if ok else 'NOTE: Torch installed but GPU not detected.')"

echo.
echo ===============================================================================
echo Done! Press any key to close.
echo ===============================================================================
pause
