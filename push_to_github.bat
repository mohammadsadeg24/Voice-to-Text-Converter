@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ========================================================
echo  🚀 WhisperFlow Studio - GitHub Push Script
echo ========================================================
echo.
echo Pushing local commits to GitHub (mohammadsadeg24)...
git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo  ✅ پروژه با موفقیت در گیت‌هاب آپلود شد!
    echo ========================================================
) else (
    echo.
    echo ========================================================
    echo  ❌ خطا در پوش کردن!
    echo  لطفا ابتدا به آدرس زیر بروید و یک مخزن خالی بسازید:
    echo  https://github.com/new
    echo  نام مخزن را Voice-to-Text-Converter بگذارید.
    echo ========================================================
)
echo.
pause

