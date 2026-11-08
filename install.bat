@echo off
setlocal enabledelayedexpansion
title WhisperFlow - Install Dependencies & FFmpeg
color 0A

cd /d "%~dp0"

echo ===============================================================================
echo        WhisperFlow -- Installing Dependencies & Audio Decoders (FFmpeg)
echo ===============================================================================
echo.
echo Installing audio packages: sounddevice, soundfile, openai-whisper, imageio-ffmpeg...
echo (Please ensure your VPN / Internet is active)
echo.

set "PYTHON_EXE="
if exist "C:\Users\Mohammadsadegh\AppData\Local\Programs\Python\Python313\python.exe" (
    set "PYTHON_EXE=C:\Users\Mohammadsadegh\AppData\Local\Programs\Python\Python313\python.exe"
) else (
    set "PYTHON_EXE=python"
)

"%PYTHON_EXE%" -m pip install sounddevice soundfile openai-whisper imageio-ffmpeg

echo.
echo Checking and extracting standalone ffmpeg.exe into project folder...
"%PYTHON_EXE%" -c "import imageio_ffmpeg, shutil, os; exe = imageio_ffmpeg.get_ffmpeg_exe(); shutil.copyfile(exe, 'ffmpeg.exe'); print('[OK] ffmpeg.exe extracted to project folder successfully!')"

echo.
if exist "ffmpeg.exe" (
    echo ===============================================================================
    echo [SUCCESS] FFmpeg audio decoder is extracted and ready in your folder!
    echo You can now process ANY music, song, MP3, M4A, or voice recording.
    echo ===============================================================================
) else (
    echo ===============================================================================
    echo [OK] Setup completed. If you had VPN on, imageio-ffmpeg is ready.
    echo ===============================================================================
)
echo.
pause
