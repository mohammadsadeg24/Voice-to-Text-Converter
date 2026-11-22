@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ================================================================
echo  🚀 WhisperFlow Studio Pro v3.0 — Build Complete Package
echo ================================================================
echo.
echo  مرحله ۱: دانلود مدل large-v3 (حدود ۱.۵ گیگابایت — فقط یک‌بار)
echo ================================================================
echo.

python -c "import whisper; print('Downloading large-v3 model...'); whisper.load_model('large-v3', device='cpu'); print('Model downloaded successfully!')"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  ❌ خطا در دانلود مدل! لطفا اینترنت خود را بررسی کنید.
    pause
    exit /b 1
)

echo.
echo ================================================================
echo  مرحله ۲: کپی مدل در پوشه dist برای بسته‌بندی
echo ================================================================
echo.

python -c "import shutil, os; cache=os.path.join(os.path.expanduser('~'),'.cache','whisper','large-v3.pt'); dst=r'dist\WhisperFlow_Studio\models\large-v3.pt'; os.makedirs(os.path.dirname(dst),exist_ok=True); shutil.copy2(cache,dst); print(f'Model copied: {os.path.getsize(dst)/1024/1024:.0f} MB')"

echo.
echo ================================================================
echo  مرحله ۳: ساخت فایل ZIP برای همکار
echo ================================================================
echo.

python -c "import zipfile,os;zf=zipfile.ZipFile(r'dist\WhisperFlow_Studio_v3.zip','w',zipfile.ZIP_DEFLATED);src=r'dist\WhisperFlow_Studio';[zf.write(os.path.join(r,f),os.path.relpath(os.path.join(r,f),r'dist'))for r,d,fs in os.walk(src)for f in fs];zf.close();print(f'ZIP created: {os.path.getsize(r\"dist\WhisperFlow_Studio_v3.zip\")/1024/1024:.0f} MB')"

echo.
echo ================================================================
echo  ✅ تمام! فایل ZIP آماده تحویل به همکار:
echo  dist\WhisperFlow_Studio_v3.zip
echo ================================================================
echo.
pause

