"""
Automated PyInstaller Build Script for WhisperFlow Studio Pro
Builds standalone Windows executable with offline model and icon bundling.
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"
MODELS_DIR = BASE_DIR / "models"
ICON_PATH = ASSETS_DIR / "app_icon.ico"


def check_and_install_pyinstaller():
    try:
        import PyInstaller
        print("[OK] PyInstaller is already installed.")
    except ImportError:
        print("[*] Installing PyInstaller...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("[OK] PyInstaller installed successfully.")


def build_app():
    print("=" * 76)
    print("   WhisperFlow Studio Pro — Windows Executable Builder (.EXE)")
    print("=" * 76)

    check_and_install_pyinstaller()

    dist_dir = BASE_DIR / "dist"
    build_dir = BASE_DIR / "build"

    # PyInstaller arguments
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onedir",                       # Standalone folder for fast 1-second startup
        "--windowed",                     # No black console window
        "--name", "WhisperFlow_Studio",
        f"--icon={str(ICON_PATH)}",
        f"--add-data={str(ASSETS_DIR)}{os.pathsep}assets",
        "--collect-all", "whisper",
        "--collect-all", "soundfile",
        "--copy-metadata", "torch",
        "--copy-metadata", "tqdm",
        "--copy-metadata", "regex",
        "--copy-metadata", "requests",
        "--copy-metadata", "packaging",
        "desktop_app.py"
    ]

    print("\n>>> Running PyInstaller build command...")
    print(" ".join(cmd))
    print()

    subprocess.check_call(cmd)

    # Copy local models folder into dist directory for 100% offline distribution
    target_app_dir = dist_dir / "WhisperFlow_Studio"
    target_models_dir = target_app_dir / "models"
    target_models_dir.mkdir(parents=True, exist_ok=True)

    if (MODELS_DIR / "small.pt").exists():
        print(">>> Copying models/small.pt into distribution package...")
        shutil.copyfile(MODELS_DIR / "small.pt", target_models_dir / "small.pt")
        print("[OK] Offline model 'small.pt' bundled successfully!")

    # Copy local ffmpeg.exe if present
    if (BASE_DIR / "ffmpeg.exe").exists():
        print(">>> Copying ffmpeg.exe into distribution package...")
        shutil.copyfile(BASE_DIR / "ffmpeg.exe", target_app_dir / "ffmpeg.exe")
        print("[OK] Standalone FFmpeg bundled successfully!")

    print("\n" + "=" * 76)
    print("🎉 BUILD COMPLETE! Standalone application is ready at:")
    print(f"   --> {target_app_dir}")
    print(f"   --> Executable: {target_app_dir / 'WhisperFlow_Studio.exe'}")
    print("=" * 76)
    print("\nTo share with your colleague:")
    print("1. Right-click the 'WhisperFlow_Studio' folder inside 'dist'")
    print("2. Send to -> Compressed (zipped) folder")
    print("3. Give that ZIP to your colleague. They just extract and double-click WhisperFlow_Studio.exe!")
    print("   (No Python installation needed, and your source code is completely hidden!)")


if __name__ == "__main__":
    build_app()

