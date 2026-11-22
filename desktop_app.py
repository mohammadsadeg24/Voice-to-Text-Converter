"""
================================================================================
          WhisperFlow Studio Pro — تبدیل و بازه‌بندی تخصصی صوت به متن
                  نسخه حرفه‌ای دسکتاپ ویندوز (Windows Desktop App)
================================================================================
ویژگی‌های کلیدی:
۱. لود پایدار مدل در حافظه رم (یک‌بار لود، بدون نیاز به لود مجدد، کاملاً آفلاین و بدون مصرف اینترنت)
۲. قابلیت بازه‌بندی هوشمند ۳۰ ثانیه‌ای (و خروجی تک‌متنی برای فایل‌های زیر ۳۰ ثانیه)
۳. اولویت‌بندی مدل محلی از پوشه models/ جهت پرتابل‌سازی و انتقال به سیستم همکار
۴. رابط کاربری مدرن، تم تیره استاندارد، سازگاری کامل با High-DPI ویندوز
۵. ذخیره خودکار فایل متنی استاندارد UTF-8 و امکان باز کردن مستقیم در Notepad
================================================================================
"""

import os
import re
import sys
import math
import time
import ctypes
import datetime
import threading
import subprocess
from pathlib import Path
from typing import Tuple, List, Optional, Dict, Any

import numpy as np
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# تنظیم High-DPI در ویندوز برای رندر بی‌نهایت شفاف فونت‌ها
if sys.platform == "win32":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# مسیر پایه برنامه (پشتیبانی هوشمند از حالت فایل اجرایی .EXE و اسکریپت)
if getattr(sys, "frozen", False):
    APP_DIR = Path(sys.executable).resolve().parent
else:
    APP_DIR = Path(__file__).resolve().parent

ASSETS_DIR = APP_DIR / "assets"
MODELS_DIR = APP_DIR / "models"
OUTPUT_DIR = APP_DIR / "transcriptions"
EXTRACTIONS_DIR = APP_DIR / "extracted_audio"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
EXTRACTIONS_DIR.mkdir(parents=True, exist_ok=True)

# ------------------------------------------------------------------------------
# تم گرافیکی تیره مدرن و صنعتی (Professional Dark Palette)
# ------------------------------------------------------------------------------
BG_MAIN = "#0d131d"          # رنگ پس‌زمینه اصلی (زغالی تیره عمیق)
CARD_BG = "#16202e"          # رنگ کارت‌ها و فریم‌های میانی
CARD_SURFACE = "#1e2c3f"     # رنگ باکس‌های داخلی و اینپوت‌ها
SURFACE_HOVER = "#27384f"    # رنگ هاور عناصر
BORDER_COLOR = "#2a3c54"     # رنگ حاشیه‌ها و جداکننده‌ها

TEXT_PRIMARY = "#f8fafc"     # متن سفید روشن اصلی
TEXT_SECONDARY = "#94a3b8"   # متن کمکی خاکستری روشن
TEXT_MUTED = "#64748b"       # متن خاموش

ACCENT_BLUE = "#3b82f6"      # آبی نیلی مدرن
ACCENT_BLUE_HOVER = "#60a5fa"
ACCENT_GREEN = "#10b981"     # سبز زمردی موفقیت
ACCENT_GREEN_HOVER = "#34d399"
ACCENT_RED = "#ef4444"       # قرمز هشدار
ACCENT_YELLOW = "#f59e0b"    # کهربایی وضعیت

FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Helvetica"
FONT_PERSIAN = "Tahoma" if sys.platform == "win32" else "Segoe UI"
FONT_MONO = "Consolas" if sys.platform == "win32" else "Courier"


# ------------------------------------------------------------------------------
# موتور صوتی و استخراج بازه‌ها
# ------------------------------------------------------------------------------
import shutil

def setup_ffmpeg_environment() -> bool:
    """شناسایی و اضافه کردن خودکار FFmpeg به PATH سیستم"""
    if shutil.which("ffmpeg"):
        return True

    # ۱. بررسی پوشه‌های محلی پروژه
    local_candidates = [
        APP_DIR,
        APP_DIR / "bin",
        APP_DIR / "assets",
        APP_DIR / "models"
    ]
    for c in local_candidates:
        if (c / "ffmpeg.exe").exists():
            os.environ["PATH"] = str(c) + os.pathsep + os.environ.get("PATH", "")
            if shutil.which("ffmpeg"):
                return True

    # ۲. بررسی پکیج imageio_ffmpeg
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(exe):
            exe_dir = Path(exe).parent
            alias = exe_dir / "ffmpeg.exe"
            if not alias.exists():
                try:
                    shutil.copyfile(exe, alias)
                except Exception:
                    pass
            os.environ["PATH"] = str(exe_dir) + os.pathsep + os.environ.get("PATH", "")
            app_ffmpeg = APP_DIR / "ffmpeg.exe"
            if not app_ffmpeg.exists():
                try:
                    shutil.copyfile(exe, app_ffmpeg)
                except Exception:
                    pass
            if shutil.which("ffmpeg"):
                return True
    except Exception:
        pass

    # ۳. بررسی مسیرهای رایج ویندوز و winget
    candidates = [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        str(Path.home() / "ffmpeg" / "bin"),
    ]
    local_app_data = os.environ.get("LOCALAPPDATA", "")
    if local_app_data:
        winget_dir = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
        if winget_dir.exists():
            for p in winget_dir.glob("*FFmpeg*"):
                for sub in p.rglob("ffmpeg.exe"):
                    candidates.append(str(sub.parent))

    for c in candidates:
        if os.path.exists(os.path.join(c, "ffmpeg.exe")):
            os.environ["PATH"] = c + os.pathsep + os.environ.get("PATH", "")
            if shutil.which("ffmpeg"):
                return True

    return False


def load_audio_safely(filepath: str) -> Tuple[np.ndarray, float]:
    """بارگذاری مستقیم فایل صوتی با soundfile یا whisper/ffmpeg"""
    setup_ffmpeg_environment()
    import soundfile as sf
    import scipy.signal as signal

    try:
        data, sr = sf.read(filepath, dtype="float32")
    except Exception:
        if not shutil.which("ffmpeg"):
            raise RuntimeError(
                "این فایل صوتی (آهنگ / M4A / AAC) برای رمزگشایی به ابزار FFmpeg نیاز دارد.\n\n"
                "روش حل بسیار سریع:\n"
                "۱. روی فایل install.bat دابل کلیک کنید تا بسته صوتی کامل نصب شود.\n"
                "   (یا دستور: pip install imageio-ffmpeg)\n"
                "۲. برنامه را مجدداً باز کنید."
            )
        import whisper
        data = whisper.load_audio(filepath)
        sr = 16000

    # تبدیل استریو به مونو
    if data.ndim > 1:
        data = np.mean(data, axis=1)

    # نرمال‌سازی
    max_val = np.max(np.abs(data))
    if max_val > 1.0:
        data = data / max_val

    # تغییر نمونه‌برداری به ۱۶ کیلوهرتز (فرکانس نیتیو ویسپر)
    if sr != 16000:
        target_len = int(len(data) * 16000 / sr)
        data = signal.resample(data, target_len).astype(np.float32)
        sr = 16000

    duration = len(data) / 16000.0
    return data, duration


def extract_audio_from_video(
    video_path: str,
    output_format: str = "mp3",
    on_process_start=None
) -> Tuple[str, float]:
    """
    استخراج مستقیم و فوق‌سریع صدای ویدیو با استفاده از موتور FFmpeg (بدون افت کیفیت و با قابلیت لغو آنی)
    """
    setup_ffmpeg_environment()
    ffmpeg_exe = shutil.which("ffmpeg")
    if not ffmpeg_exe:
        app_ffmpeg = APP_DIR / "ffmpeg.exe"
        if app_ffmpeg.exists():
            ffmpeg_exe = str(app_ffmpeg)
        else:
            raise RuntimeError(
                "ابزار FFmpeg جهت استخراج صوت از ویدیو یافت نشد.\n\n"
                "لطفاً مطمئن شوید FFmpeg در سیستم نصب است یا فایل ffmpeg.exe در پوشه برنامه قرار دارد."
            )

    clean_name = Path(video_path).stem
    clean_name = clean_name.replace('Ø', 'O').replace('ø', 'o').replace('æ', 'ae').replace('ß', 'ss')
    clean_name = re.sub(r'[\\/*?:"<>| \x00-\x1f]', '_', clean_name)[:35]
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_file = EXTRACTIONS_DIR / f"{clean_name}_{timestamp}.{output_format.lower()}"

    cmd = [ffmpeg_exe, "-y", "-i", str(video_path), "-vn"]
    if output_format.lower() == "mp3":
        cmd += ["-acodec", "libmp3lame", "-b:a", "192k"]
    elif output_format.lower() == "wav":
        cmd += ["-acodec", "pcm_s16le", "-ar", "16000", "-ac", "1"]
    else:
        cmd += ["-acodec", "copy"]
    cmd.append(str(out_file))

    start_t = time.time()
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        startupinfo=startupinfo
    )
    if on_process_start:
        on_process_start(proc)

    stderr_bytes = proc.communicate()[1]
    if proc.returncode != 0:
        if getattr(proc, "_was_cancelled", False):
            if out_file.exists():
                try:
                    out_file.unlink()
                except Exception:
                    pass
            raise InterruptedError("Extraction cancelled by user")

        err_msg = stderr_bytes.decode("utf-8", errors="replace")[-300:]
        raise RuntimeError(f"خطا در استخراج صوت توسط FFmpeg:\n{err_msg}")

    elapsed = time.time() - start_t
    return str(out_file), elapsed


def format_timestamp(seconds: float) -> str:
    """فرمت‌دهی ثانیه‌ها به دقیقه:ثانیه (00:00)"""
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins:02d}:{secs:02d}"


def format_display_name(name: str, max_chars: int = 42) -> str:
    """کوتاه‌سازی هوشمند نام فایل‌های طولانی برای جلوگیری از به‌هم‌ریختگی المان‌های UI"""
    if len(name) <= max_chars:
        return name
    half = (max_chars - 3) // 2
    return f"{name[:half]}...{name[-half:]}"


def segment_transcription_text(
    segments: list,
    total_duration: float,
    interval_seconds: float = 30.0,
    enable_intervals: bool = True
) -> Dict[str, Any]:
    """
    محاسبه بازه‌بندی هوشمند:
    - اگر صدا کمتر یا مساوی بازه (مثلا ۳۰ ثانیه) باشد، یک متن یکپارچه تولید می‌کند.
    - اگر صدا بیشتر از ۳۰ ثانیه باشد، خروجی را با تگ‌های [00:00 - 00:30] بازه‌بندی می‌کند.
    """
    if not segments:
        return {
            "file_text": "(هیچ صدایی تشخیص داده نشد)",
            "ui_text": "(بدون کلام)",
            "full_text": "(بدون کلام)",
            "is_single": True,
            "bucket_count": 0
        }

    # متن یکپارچه بدون بازه
    full_text = " ".join(s.get("text", "").strip() for s in segments if s.get("text", "").strip())
    full_text = re.sub(r'\s+', ' ', full_text).strip()

    # اگر تیک بازه‌بندی برداشته شده یا طول صدا زیر ۳۰ ثانیه باشد:
    if not enable_intervals or total_duration <= interval_seconds:
        return {
            "file_text": full_text,
            "ui_text": full_text,
            "full_text": full_text,
            "is_single": True,
            "bucket_count": 1
        }

    # ایجاد باکت‌های بازه ۳۰ ثانیه‌ای
    num_buckets = int(math.ceil(total_duration / interval_seconds))
    buckets = [[] for _ in range(num_buckets)]

    for s in segments:
        start_time = s.get("start", 0.0)
        bucket_idx = min(int(start_time // interval_seconds), num_buckets - 1)
        text = s.get("text", "").strip()
        if text:
            buckets[bucket_idx].append(text)

    file_blocks = []
    ui_blocks = []

    for i, texts in enumerate(buckets):
        start_sec = i * interval_seconds
        end_sec = min((i + 1) * interval_seconds, total_duration)
        time_tag = f"[{format_timestamp(start_sec)} - {format_timestamp(end_sec)}]"
        body = " ".join(texts).strip() if texts else "(سکوت / بدون گفتار)"
        body = re.sub(r'\s+', ' ', body)

        file_blocks.append(f"{time_tag}\n{body}\n")
        ui_blocks.append(f"{time_tag}\n{body}\n")

    separator = "\n" + ("-" * 78) + "\n"
    file_output = separator.join(file_blocks)
    ui_output = "\n" + ("=" * 45) + "\n".join(ui_blocks)

    return {
        "file_text": file_output,
        "ui_text": ui_output,
        "full_text": full_text,
        "is_single": False,
        "bucket_count": num_buckets
    }


def save_transcription_report(
    segmented_text: str,
    full_text: str,
    source_path: str,
    model_name: str,
    language: str,
    duration: float,
    is_interval_active: bool,
    interval_seconds: float = 30.0
) -> str:
    """ذخیره گزارش جامع در فایل متنی با انکودینگ بین‌المللی UTF-8"""
    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    clean_stem = Path(source_path).stem
    # تبدیل کاراکترهای خاص غیرانگلیسی مثل Ø برای جلوگیری از خطای زیپ ویندوز
    clean_stem = clean_stem.replace('Ø', 'O').replace('ø', 'o').replace('æ', 'ae').replace('ß', 'ss')
    clean_stem = re.sub(r'[\\/*?:"<>| \x00-\x1f]', '_', clean_stem)
    clean_stem = re.sub(r'[^a-zA-Z0-9_\-\u0600-\u06FF.]', '_', clean_stem)[:30]

    out_file = OUTPUT_DIR / f"{clean_stem}_transcription_{timestamp}.txt"
    lang_display = "فارسی (Persian)" if language.lower() in ("fa", "persian") else "English" if language.lower() in ("en", "english") else language

    mode_label = (
        f"بازه‌بندی بر اساس بازه‌های {int(interval_seconds)} ثانیه‌ای"
        if is_interval_active and duration > interval_seconds
        else f"متن پیوسته یکپارچه (طول صوت زیر {int(interval_seconds)} ثانیه)"
    )

    divider = "=" * 80
    sub_div = "-" * 80

    report = (
        f"{divider}\n"
        f"گزارش تبدیل و بازه‌بندی صوت به متن — WHISPERFLOW STUDIO PRO\n"
        f"{divider}\n"
        f"تاریخ و زمان ثبت    : {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"نام فایل صوتی       : {Path(source_path).name}\n"
        f"مسیر کامل فایل       : {source_path}\n"
        f"مدل استفاده‌شده      : {model_name}\n"
        f"زبان تشخیص‌داده‌شده  : {lang_display}\n"
        f"مدت کل فایل صوتی    : {duration:.2f} ثانیه ({format_timestamp(duration)})\n"
        f"حالت خروجی           : {mode_label}\n"
        f"انکودینگ فایل        : UTF-8 (سازگار با ویندوز، لینوکس و مک)\n"
        f"{divider}\n\n"
        f"بخش ۱: متن استخراج‌شده (همراه با بازه‌های زمانی):\n"
        f"{sub_div}\n"
        f"{segmented_text.strip()}\n"
        f"{sub_div}\n\n"
        f"بخش ۲: متن کامل و پیوسته (بدون برچسب‌های زمانی):\n"
        f"{sub_div}\n"
        f"{full_text.strip()}\n"
        f"{divider}\n"
    )

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(report)

    return str(out_file)


# ------------------------------------------------------------------------------
# کلاس اصلی نرم‌افزار دسکتاپ (WhisperFlowStudio)
# ------------------------------------------------------------------------------
class WhisperFlowStudio(tk.Tk):
    """
    نرم‌افزار حرفه‌ای تبدیل گفتار به نوشتار:
    - نگهداری دائمی مدل در حافظه RAM برای جلوگیری از مصرف اینترنت و لود مکرر
    - بازه‌بندی دقیق ۳۰ ثانیه‌ای
    - استایل مدرن تلگرام / دیسکورد
    """

    def __init__(self):
        super().__init__()

        self.title("WhisperFlow Studio Pro — تبدیل و بازه‌بندی صوت به متن")
        self.configure(bg=BG_MAIN)

        # ست کردن آیکون برنامه
        self._setup_window_icon()

        # فعال‌سازی Dark Titlebar بومی ویندوز ۱۰ و ۱۱
        self._apply_windows_dark_titlebar()

        # تنظیم هوشمند ابعاد و واکنش‌گرایی پنجره (Responsive Window)
        self._setup_responsive_window()

        # وضعیت‌های برنامه
        self.current_model_name = "small"  # بهینه‌ترین مدل (سبک، پرسرعت، دقت عالی فارسی، بدون کرش VRAM)
        self.whisper_model = None
        self.is_loading_model = False
        self.is_transcribing = False
        self._cancel_transcription_requested = False

        # سخت‌افزار پیش‌فرض (GPU در صورت وجود، در غیر این صورت CPU)
        default_dev, _ = self._detect_best_device()
        self._target_device = default_dev
        self._active_device = default_dev

        self.selected_file_path: Optional[str] = None
        self.current_audio_duration: float = 0.0
        self.last_saved_filepath: Optional[str] = None
        self.last_results: Optional[Dict[str, Any]] = None

        # وضعیت‌های تب‌بندی و استخراج ویدیو
        self.current_main_tab = "transcribe"
        self.selected_video_path: Optional[str] = None
        self.is_extracting_audio = False
        self.last_extracted_audio_path: Optional[str] = None
        self._current_video_proc = None

        # ساخت لایه‌های گرافیکی
        self._build_interface()

        # لود مدل در رم به صورت خودکار در آغاز برنامه
        self.after(300, self._load_model_into_memory)

    def _setup_responsive_window(self):
        """
        تنظیم ابعاد کاملاً واکنش‌گرا و پویا متناسب با ابعاد مانیتور کاربر (Responsive Design):
        ۱. شناسایی ابعاد و رزولوشن صفحه نمایش
        ۲. محاسبه اندازه متناسب برای حالت پنجره‌ای (Restore Down)
        ۳. مرکزچین کردن پنجره در وسط مانیتور
        ۴. اجرای خودکار در حالت ماکزیمایز (Maximized/Zoomed) در ویندوز جهت استفاده بهینه از تمام صفحه
        ۵. مانیتورینگ تغییر سایز برای تطبیق خودکار عرض متون و المان‌ها
        """
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()

        # ابعاد منعطف برای حالت پنجره‌ای عادی (Restore Down)
        target_w = max(960, min(1420, int(screen_w * 0.86)))
        target_h = max(640, min(860, int(screen_h * 0.86)))
        pos_x = max(0, (screen_w - target_w) // 2)
        pos_y = max(0, (screen_h - target_h) // 2 - 25)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
        self.minsize(860, 540)

        # اجرای پنجره در حالت ماکزیمایز در ویندوز
        if sys.platform == "win32":
            try:
                self.state("zoomed")
            except Exception:
                pass

        # لیسنر واکنش‌گرای تغییر سایز پنجره
        self.last_win_width = 0
        self.bind("<Configure>", self._on_window_resize)

    def _on_window_resize(self, event):
        if event.widget == self:
            w = event.width
            if abs(w - self.last_win_width) > 30:
                self.last_win_width = w
                # تنظیم خودکار طول سطر متن توضیحات متناسب با عرض پنجره و تب فعال
                if hasattr(self, "lbl_desc"):
                    right_offset = 550 if getattr(self, "current_main_tab", "transcribe") == "transcribe" else 360
                    safe_wrap = max(260, w - right_offset)
                    self.lbl_desc.configure(wraplength=safe_wrap)

    def _setup_window_icon(self):
        ico_file = ASSETS_DIR / "app_icon.ico"
        png_file = ASSETS_DIR / "app_icon.png"

        if ico_file.exists():
            try:
                self.iconbitmap(str(ico_file))
            except Exception:
                pass
        elif png_file.exists():
            try:
                img = tk.PhotoImage(file=str(png_file))
                self.iconphoto(True, img)
            except Exception:
                pass

    def _apply_windows_dark_titlebar(self):
        if sys.platform == "win32":
            try:
                self.update()
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                val = ctypes.c_int(1)
                ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ctypes.byref(val), ctypes.sizeof(val))
            except Exception:
                pass

    def _build_interface(self):
        # ----------------- ۱. هدر اصلی برنامه (Top Header Card) -----------------
        header = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        header.pack(fill="x", padx=18, pady=(14, 8))

        # اطلاعات برند و نسخه (سمت چپ)
        brand_box = tk.Frame(header, bg=CARD_BG)
        brand_box.pack(side="left", padx=16, pady=10)

        title_row = tk.Frame(brand_box, bg=CARD_BG)
        title_row.pack(anchor="w")

        lbl_logo = tk.Label(title_row, text="🎙️", font=(FONT_FAMILY, 16), bg=CARD_BG)
        lbl_logo.pack(side="left", padx=(0, 6))

        lbl_title = tk.Label(
            title_row,
            text="WhisperFlow Studio Pro",
            font=(FONT_FAMILY, 15, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_BG
        )
        lbl_title.pack(side="left")

        lbl_ver = tk.Label(
            title_row,
            text=" v3.0 Enterprise ",
            font=(FONT_FAMILY, 8, "bold"),
            fg=ACCENT_BLUE_HOVER,
            bg=CARD_SURFACE,
            padx=4,
            pady=1
        )
        lbl_ver.pack(side="left", padx=8)

        lbl_desc = tk.Label(
            brand_box,
            text="سامانه تخصصی تبدیل صوت به متن با بازه‌بندی زمانی ۳۰ ثانیه‌ای | فارسی و انگلیسی",
            font=(FONT_PERSIAN, 9),
            fg=TEXT_SECONDARY,
            bg=CARD_BG,
            justify="left"
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))
        self.lbl_desc = lbl_desc

        # کنترل‌های وضعیت مدل و سخت‌افزار (مخصوص تب تبدیل صوت به متن)
        self.top_ctrl_transcribe = tk.Frame(header, bg=CARD_BG)
        self.top_ctrl_transcribe.pack(side="right", padx=16, pady=10)

        # بج وضعیت لود مدل در RAM
        self.lbl_ram_status = tk.Label(
            self.top_ctrl_transcribe,
            text="⏳ در حال لود اولیه مدل در RAM...",
            font=(FONT_PERSIAN, 9, "bold"),
            fg=ACCENT_YELLOW,
            bg=CARD_SURFACE,
            padx=12,
            pady=5
        )
        self.lbl_ram_status.pack(side="right", padx=(10, 0))

        # دراپ‌داون انتخاب مدل
        model_frame = tk.Frame(self.top_ctrl_transcribe, bg=CARD_BG)
        model_frame.pack(side="right", padx=8)

        tk.Label(
            model_frame,
            text="مدل هوش مصنوعی:",
            font=(FONT_PERSIAN, 9),
            fg=TEXT_SECONDARY,
            bg=CARD_BG
        ).pack(side="left", padx=(0, 4))

        self.model_var = tk.StringVar(value="small (پیشنهادی — سرعت و دقت بهینه)")
        self.model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            values=[
                "small (پیشنهادی — سرعت و دقت بهینه)",
                "base (سریع و سبک)",
                "tiny (فوق‌العاده سبک)"
            ],
            state="readonly",
            width=28
        )
        self.model_combo.pack(side="left")
        self.model_combo.bind("<<ComboboxSelected>>", self._on_change_model)

        # کنترل‌های وضعیت مخصوص تب استخراج ویدیو (در آغاز پنهان)
        self.top_ctrl_video = tk.Frame(header, bg=CARD_BG)
        lbl_video_badge = tk.Label(
            self.top_ctrl_video,
            text="⚡ موتور استخراج: FFmpeg فوق‌سریع (بدون افت کیفیت)",
            font=(FONT_PERSIAN, 9, "bold"),
            fg=ACCENT_GREEN,
            bg=CARD_SURFACE,
            padx=12,
            pady=5
        )
        lbl_video_badge.pack(side="right")

        # ----------------- نوار تب‌های اصلی برنامه (Main Navigation Tabs) -----------------
        nav_container = tk.Frame(self, bg=BG_MAIN)
        nav_container.pack(fill="x", padx=18, pady=(4, 6))

        tab_nav_box = tk.Frame(nav_container, bg=CARD_SURFACE, highlightbackground=BORDER_COLOR, highlightthickness=1)
        tab_nav_box.pack(side="left")

        self.btn_nav_transcribe = tk.Label(
            tab_nav_box,
            text="🎙️ تبدیل صوت به متن (Speech-to-Text)",
            font=(FONT_PERSIAN, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=ACCENT_BLUE,
            padx=18,
            pady=8,
            cursor="hand2"
        )
        self.btn_nav_transcribe.pack(side="left")
        self.btn_nav_transcribe.bind("<Button-1>", lambda e: self._switch_main_tab("transcribe"))

        self.btn_nav_video = tk.Label(
            tab_nav_box,
            text="🎬 استخراج صوت از ویدیو (Video-to-Audio)",
            font=(FONT_PERSIAN, 10),
            fg=TEXT_SECONDARY,
            bg=CARD_SURFACE,
            padx=18,
            pady=8,
            cursor="hand2"
        )
        self.btn_nav_video.pack(side="left")
        self.btn_nav_video.bind("<Button-1>", lambda e: self._switch_main_tab("video"))

        # محفظه صفحات اصلی (Pages Container)
        self.pages_container = tk.Frame(self, bg=BG_MAIN)
        self.pages_container.pack(fill="both", expand=True)

        # صفحه ۱: تبدیل صوت به متن
        self.page_transcribe = tk.Frame(self.pages_container, bg=BG_MAIN)
        self.page_transcribe.pack(fill="both", expand=True)

        # صفحه ۲: استخراج صوت از ویدیو
        self.page_video = tk.Frame(self.pages_container, bg=BG_MAIN)

        # ----------------- ۲. کارت انتخاب فایل و تنظیمات بازه‌بندی -----------------
        panel_cfg = tk.Frame(self.page_transcribe, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        panel_cfg.pack(fill="x", padx=18, pady=4)

        cfg_inner = tk.Frame(panel_cfg, bg=CARD_BG)
        cfg_inner.pack(fill="x", padx=16, pady=12)

        # ردیف ۱: انتخاب فایل صوتی
        row_file = tk.Frame(cfg_inner, bg=CARD_BG)
        row_file.pack(fill="x", pady=(0, 8))

        self.btn_browse = self._create_modern_btn(
            row_file,
            text="📁 انتخاب فایل صوتی (Browse Audio)",
            bg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            command=self._browse_audio
        )
        self.btn_browse.pack(side="left")

        self.lbl_file_display = tk.Label(
            row_file,
            text="هیچ فایل صوتی انتخاب نشده است (فرمت‌های MP3, WAV, M4A, OGG, FLAC پشتیبانی می‌شوند)",
            font=(FONT_FAMILY, 9),
            fg=TEXT_MUTED,
            bg=CARD_BG,
            anchor="w"
        )
        self.lbl_file_display.pack(side="left", fill="x", expand=True, padx=14)

        # دکمه شروع تبدیل
        self.btn_transcribe = self._create_modern_btn(
            row_file,
            text="🚀 شروع استخراج و بازه‌بندی",
            bg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            command=self._start_transcription_thread
        )
        self.btn_transcribe.pack(side="right")

        # دکمه لغو تبدیل (در زمان شروع پردازش در کنار دکمه شروع قرار می‌گیرد)
        self.btn_cancel_transcribe = self._create_modern_btn(
            row_file,
            text="⏹️ لغو تبدیل",
            bg_color=ACCENT_RED,
            hover_color="#dc2626",
            command=self._cancel_transcription
        )

        # ردیف ۲: آپشن‌های بازه‌بندی ۳۰ ثانیه‌ای، انتخاب سخت‌افزار و وضعیت
        row_opts = tk.Frame(cfg_inner, bg=CARD_BG)
        row_opts.pack(fill="x", pady=(6, 0))

        # چک‌باکس بازه‌بندی ۳۰ ثانیه‌ای
        self.interval_active_var = tk.BooleanVar(value=True)
        self.chk_interval = tk.Checkbutton(
            row_opts,
            text="بازه‌بندی بر اساس بازه زمانی ۳۰ ثانیه‌ای",
            variable=self.interval_active_var,
            font=(FONT_PERSIAN, 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_BG,
            activebackground=CARD_BG,
            activeforeground=TEXT_PRIMARY,
            selectcolor=CARD_SURFACE
        )
        self.chk_interval.pack(side="left")

        # طول بازه زمانی
        interval_box = tk.Frame(row_opts, bg=CARD_BG)
        interval_box.pack(side="left", padx=8)

        tk.Label(interval_box, text="طول هر بازه:", font=(FONT_PERSIAN, 8), fg=TEXT_SECONDARY, bg=CARD_BG).pack(side="left", padx=(0, 4))
        self.interval_sec_var = tk.StringVar(value="30")
        self.interval_sec_var.trace_add("write", lambda *args: self._on_interval_changed())
        self.combo_interval = ttk.Combobox(
            interval_box,
            textvariable=self.interval_sec_var,
            values=["15", "30", "45", "60", "90"],
            state="readonly",
            width=4
        )
        self.combo_interval.pack(side="left")
        self.combo_interval.bind("<<ComboboxSelected>>", self._on_interval_changed)
        tk.Label(interval_box, text="ثانیه", font=(FONT_PERSIAN, 8), fg=TEXT_SECONDARY, bg=CARD_BG).pack(side="left", padx=(4, 0))

        # دراپ‌داون انتخاب سخت‌افزار پردازشی (GPU یا CPU)
        hw_box = tk.Frame(row_opts, bg=CARD_BG)
        hw_box.pack(side="left", padx=10)

        tk.Label(
            hw_box,
            text="سخت‌افزار:",
            font=(FONT_PERSIAN, 8, "bold"),
            fg=TEXT_SECONDARY,
            bg=CARD_BG
        ).pack(side="left", padx=(0, 4))

        gpu_avail = False
        try:
            import torch
            gpu_avail = torch.cuda.is_available()
        except Exception:
            pass

        self.device_options = []
        if gpu_avail:
            self.device_options.append("⚡ کارت گرافیک (GPU)")
        self.device_options.append("🖥️ پردازنده (CPU)")

        init_choice = self.device_options[0] if gpu_avail and self._target_device == "cuda" else "🖥️ پردازنده (CPU)"
        self.device_var = tk.StringVar(value=init_choice)
        self.combo_device = ttk.Combobox(
            hw_box,
            textvariable=self.device_var,
            values=self.device_options,
            state="readonly",
            width=17
        )
        self.combo_device.pack(side="left")
        self.combo_device.bind("<<ComboboxSelected>>", self._on_device_changed)

        # راهنما
        self.lbl_interval_hint = tk.Label(
            row_opts,
            text="(ویس‌های زیر ۳۰ ثانیه خودکار یکپارچه می‌شوند)",
            font=(FONT_PERSIAN, 8),
            fg=TEXT_MUTED,
            bg=CARD_BG
        )
        self.lbl_interval_hint.pack(side="left", padx=8)

        # وضعیت پردازش زنده
        self.lbl_progress_status = tk.Label(
            row_opts,
            text="",
            font=(FONT_FAMILY, 9, "bold"),
            fg=ACCENT_BLUE_HOVER,
            bg=CARD_BG
        )
        self.lbl_progress_status.pack(side="right")

        # ----------------- ۳. فضای کار و نمایش متن (Workspace) -----------------
        panel_output = tk.Frame(self.page_transcribe, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        panel_output.pack(fill="both", expand=True, padx=18, pady=(6, 14))

        # هدر تولبار نتایج
        bar_tools = tk.Frame(panel_output, bg=CARD_BG)
        bar_tools.pack(fill="x", padx=16, pady=(10, 6))

        # دکمه‌های تب (نمای بازه‌بندی شده / نمای متن پیوسته)
        self.active_view = "segmented"  # 'segmented' or 'full'

        tab_box = tk.Frame(bar_tools, bg=CARD_SURFACE, padx=2, pady=2)
        tab_box.pack(side="left")

        self.btn_tab_segmented = tk.Label(
            tab_box,
            text="⏱️ نمای بازه‌بندی ۳۰ ثانیه‌ای",
            font=(FONT_PERSIAN, 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=ACCENT_BLUE,
            padx=12,
            pady=4,
            cursor="hand2"
        )
        self.btn_tab_segmented.pack(side="left")
        self.btn_tab_segmented.bind("<Button-1>", lambda e: self._switch_view("segmented"))

        self.btn_tab_full = tk.Label(
            tab_box,
            text="📄 نمای متن یکپارچه",
            font=(FONT_PERSIAN, 9),
            fg=TEXT_SECONDARY,
            bg=CARD_SURFACE,
            padx=12,
            pady=4,
            cursor="hand2"
        )
        self.btn_tab_full.pack(side="left")
        self.btn_tab_full.bind("<Button-1>", lambda e: self._switch_view("full"))

        # متادیتا صوت
        self.lbl_file_meta = tk.Label(
            bar_tools,
            text="",
            font=(FONT_FAMILY, 8),
            fg=TEXT_MUTED,
            bg=CARD_BG
        )
        self.lbl_file_meta.pack(side="left", padx=14)

        # دکمه‌های اکشن (کپی، نوت‌پد، پوشه)
        action_bar = tk.Frame(bar_tools, bg=CARD_BG)
        action_bar.pack(side="right")

        self.btn_notepad = self._create_small_btn(action_bar, "📝 باز کردن در Notepad", self._open_notepad)
        self.btn_notepad.pack(side="right", padx=3)

        self.btn_copy = self._create_small_btn(action_bar, "📋 کپی متن", self._copy_current_text)
        self.btn_copy.pack(side="right", padx=3)

        self.btn_folder = self._create_small_btn(action_bar, "📁 پوشه خروجی", self._open_output_folder)
        self.btn_folder.pack(side="right", padx=3)

        self.btn_rtl = self._create_small_btn(action_bar, "⇄ تغییر جهت (RTL/LTR)", self._toggle_rtl)
        self.btn_rtl.pack(side="right", padx=3)

        # کادر متن با اسکرول‌بار
        txt_box = tk.Frame(panel_output, bg="#111822", highlightbackground=BORDER_COLOR, highlightthickness=1)
        txt_box.pack(fill="both", expand=True, padx=16, pady=(4, 12))

        scrollbar = tk.Scrollbar(txt_box)
        scrollbar.pack(side="right", fill="y")

        self.text_editor = tk.Text(
            txt_box,
            bg="#111822",
            fg=TEXT_PRIMARY,
            insertbackground="#38bdf8",
            selectbackground="#2b5278",
            selectforeground="#ffffff",
            font=(FONT_PERSIAN, 11),
            wrap="word",
            relief="flat",
            padx=16,
            pady=14,
            yscrollcommand=scrollbar.set
        )
        self.text_editor.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.text_editor.yview)

        # تگ‌های جهت متن
        self.text_editor.tag_configure("rtl", justify="right", font=(FONT_PERSIAN, 11))
        self.text_editor.tag_configure("ltr", justify="left", font=(FONT_FAMILY, 11))
        self.current_is_rtl = True

        self._render_welcome_message()
        self._build_video_extractor_ui()

    def _create_modern_btn(self, parent, text: str, bg_color: str, hover_color: str, command):
        btn = tk.Label(
            parent,
            text=text,
            font=(FONT_PERSIAN, 9, "bold"),
            fg=TEXT_PRIMARY,
            bg=bg_color,
            padx=16,
            pady=8,
            cursor="hand2"
        )
        btn.bind("<Enter>", lambda e: btn.configure(bg=hover_color))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg_color))
        btn.bind("<Button-1>", lambda e: command())
        return btn

    def _create_small_btn(self, parent, text: str, command):
        btn = tk.Label(
            parent,
            text=text,
            font=(FONT_PERSIAN, 8),
            fg=TEXT_PRIMARY,
            bg=CARD_SURFACE,
            padx=9,
            pady=5,
            cursor="hand2"
        )
        btn.bind("<Enter>", lambda e: btn.configure(bg=SURFACE_HOVER))
        btn.bind("<Leave>", lambda e: btn.configure(bg=CARD_SURFACE))
        btn.bind("<Button-1>", lambda e: command())
        return btn

    def _render_welcome_message(self):
        self.text_editor.delete("1.0", "end")
        msg = (
            "به نرم‌افزار WhisperFlow Studio Pro v3.0 خوش آمدید!\n\n"
            "ویژگی‌های کلیدی نرم‌افزار:\n"
            "۱. مدل هوش مصنوعی بهینه Small: مدل فوق‌العاده سریع و دقیق، کاملاً سازگار با انواع کارت گرافیک و پردازنده بدون مصرف بی‌رویه رم یا کرش سیستم.\n"
            "۲. انتخاب سخت‌افزار پردازشی: امکان سوییچ آزادانه بین کارت گرافیک (GPU) و پردازنده (CPU) قبل از شروع هر تبدیل.\n"
            "۳. دکمه لغو آنی: امکان لغو و انصراف در هر لحظه از فرآیند تبدیل به متن یا استخراج ویدیو با یک کلیک.\n"
            "۴. بازه‌بندی هوشمند ۳۰ ثانیه‌ای: تفکیک دقیق متن‌ها به بازه‌های زمانی استاندارد [00:00 - 00:30] برای سهولت بازخوانی.\n"
            "۵. استخراج صوت از ویدیو: جداسازی بی‌درنگ صدای ویدیوها با موتور FFmpeg در تب مجزا.\n"
            "۶. خروجی استاندارد UTF-8 و امکان باز کردن مستقیم در Notepad ویندوز.\n\n"
            "برای شروع، فایل صوتی خود را انتخاب کرده و روی «شروع استخراج و بازه‌بندی» کلیک کنید."
        )
        self.text_editor.insert("1.0", msg, "rtl")

    # --------------------------------------------------------------------------
    # مدیریت مدل در حافظه RAM و انتخاب سخت‌افزار (GPU / CPU)
    # --------------------------------------------------------------------------
    def _detect_best_device(self):
        """شناسایی خودکار بهترین سخت‌افزار پردازشی (CUDA GPU > CPU)"""
        try:
            import torch
            if torch.cuda.is_available():
                gpu_name = torch.cuda.get_device_name(0)
                vram_gb = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                return "cuda", f"{gpu_name} ({vram_gb:.1f} GB)"
        except Exception:
            pass
        return "cpu", "CPU"

    def _load_model_into_memory(self):
        """لود مدل هوش مصنوعی در رم متناسب با سخت‌افزار انتخابی کاربر (GPU یا CPU)"""
        def worker():
            self.is_loading_model = True
            model_target = self.current_model_name
            target_device = getattr(self, "_target_device", "cpu")

            hw_label = "کارت گرافیک (GPU)" if target_device == "cuda" else "پردازنده (CPU)"

            self.after(0, lambda: self.lbl_ram_status.configure(
                text=f"⏳ بارگذاری مدل {model_target.upper()} روی {hw_label}...",
                fg=ACCENT_YELLOW
            ))

            try:
                import whisper

                # ۱. بررسی فایل مدل در پوشه محلی models/
                local_model_file = MODELS_DIR / f"{model_target}.pt"
                model_path_or_name = str(local_model_file) if local_model_file.exists() else model_target

                # لود مدل روی سخت‌افزار مدنظر کاربر
                model = whisper.load_model(model_path_or_name, device=target_device)
                self.whisper_model = model
                self._active_device = target_device

                speed_label = "⚡ GPU — سرعت بالا" if target_device == "cuda" else "🖥️ CPU"
                self.after(0, lambda: self.lbl_ram_status.configure(
                    text=f"🟢 مدل {model_target.upper()} آماده ({speed_label})",
                    fg=ACCENT_GREEN
                ))

            except Exception as e:
                # اگر روی GPU خطا داد، فال‌بک خودکار به CPU
                if target_device == "cuda":
                    try:
                        import whisper as w2
                        local_model_file = MODELS_DIR / f"{model_target}.pt"
                        path_or_name = str(local_model_file) if local_model_file.exists() else model_target
                        model = w2.load_model(path_or_name, device="cpu")
                        self.whisper_model = model
                        self._active_device = "cpu"
                        self._target_device = "cpu"
                        self.after(0, lambda: self.device_var.set("🖥️ پردازنده (CPU)"))
                        self.after(0, lambda: self.lbl_ram_status.configure(
                            text=f"🟢 مدل {model_target.upper()} آماده (🖥️ CPU — فال‌بک خودکار)",
                            fg=ACCENT_GREEN
                        ))
                        return
                    except Exception:
                        pass

                self.after(0, lambda: self.lbl_ram_status.configure(
                    text=f"❌ خطا در بارگذاری: {str(e)[:40]}",
                    fg=ACCENT_RED
                ))
            finally:
                self.is_loading_model = False

        threading.Thread(target=worker, daemon=True).start()

    def _on_device_changed(self, event=None):
        """تغییر سخت‌افزار پردازشی توسط کاربر (GPU / CPU)"""
        if getattr(self, "is_transcribing", False) or getattr(self, "is_loading_model", False):
            messagebox.showinfo("لطفاً صبر کنید", "در حین پردازش یا بارگذاری امکان تغییر سخت‌افزار وجود ندارد.")
            cur = "⚡ کارت گرافیک (GPU)" if getattr(self, "_target_device", "cpu") == "cuda" else "🖥️ پردازنده (CPU)"
            self.device_var.set(cur)
            return

        choice = self.device_var.get()
        target = "cuda" if "GPU" in choice else "cpu"
        if target != getattr(self, "_target_device", "cpu"):
            self._target_device = target
            self._load_model_into_memory()

    def _on_change_model(self, event=None):
        if getattr(self, "is_transcribing", False) or getattr(self, "is_loading_model", False):
            messagebox.showinfo("لطفاً صبر کنید", "در حین پردازش یا بارگذاری امکان تغییر مدل وجود ندارد.")
            return
        selected_raw = self.model_var.get().split()[0].lower()
        if selected_raw != self.current_model_name:
            self.current_model_name = selected_raw
            self._load_model_into_memory()

    def _on_interval_changed(self, event=None):
        """بروزرسانی بلادرنگ متن چک‌باکس، تب نمایش و راهنما بر اساس ثانیه انتخابی کاربر"""
        val = self.interval_sec_var.get().strip() if hasattr(self, "interval_sec_var") else "30"
        if not val:
            val = "30"

        # ۱. بروزرسانی عنوان چک‌باکس بازه‌بندی
        if hasattr(self, "chk_interval"):
            self.chk_interval.configure(text=f"بازه‌بندی بر اساس بازه زمانی {val} ثانیه‌ای")

        # ۲. بروزرسانی دکمه تب نتایج در فضای کار
        if hasattr(self, "btn_tab_segmented"):
            self.btn_tab_segmented.configure(text=f"⏱️ نمای بازه‌بندی {val} ثانیه‌ای")

        # ۳. بروزرسانی برچسب راهنمای زیر بازه
        if hasattr(self, "lbl_interval_hint"):
            self.lbl_interval_hint.configure(text=f"(ویس‌های زیر {val} ثانیه خودکار یکپارچه می‌شوند)")

    # --------------------------------------------------------------------------
    # انتخاب و پردازش فایل صوتی
    # --------------------------------------------------------------------------
    def _browse_audio(self):
        chosen = filedialog.askopenfilename(
            title="انتخاب فایل صوتی برای تبدیل و بازه‌بندی",
            filetypes=[
                ("All Supported Audio", "*.mp3 *.wav *.m4a *.ogg *.flac *.aac *.opus"),
                ("MP3 Files", "*.mp3"),
                ("WAV Files", "*.wav"),
                ("All Files", "*.*")
            ]
        )
        if chosen:
            self.selected_file_path = chosen
            name = Path(chosen).name
            disp_name = format_display_name(name, 45)
            size_mb = os.path.getsize(chosen) / (1024 * 1024)
            self.lbl_file_display.configure(
                text=f"✓ انتخاب شد: {disp_name} ({size_mb:.1f} MB)",
                fg=ACCENT_GREEN
            )

    def _cancel_transcription(self):
        """درخواست لغو فرآیند تبدیل صوت به متن توسط کاربر"""
        self._cancel_transcription_requested = True
        self.lbl_progress_status.configure(text="⏳ در حال لغو عملیات...", fg=ACCENT_YELLOW)
        self.btn_cancel_transcribe.configure(bg=TEXT_MUTED, cursor="wait")

    def _on_transcription_cancelled(self):
        """بازنشانی رابط کاربری پس از لغو موفقیت‌آمیز تبدیل"""
        self.btn_transcribe.configure(bg=ACCENT_GREEN, cursor="hand2")
        self.btn_cancel_transcribe.pack_forget()
        self.lbl_progress_status.configure(text="⏹️ عملیات تبدیل به متن توسط کاربر لغو شد.", fg=ACCENT_YELLOW)

    def _start_transcription_thread(self):
        if not self.selected_file_path:
            messagebox.showwarning("توجه", "لطفاً ابتدا یک فایل صوتی را با دکمه «انتخاب فایل صوتی» مشخص کنید.")
            return

        if self.is_loading_model:
            messagebox.showinfo("لطفاً صبر کنید", "مدل هوش مصنوعی در حال بارگذاری در حافظه رم است. چند لحظه دیگر امتحان کنید.")
            return

        if self.whisper_model is None:
            messagebox.showerror("خطا", "مدل ویسپر در حافظه لود نشده است. لطفاً پنجره را ببندید و مجدداً باز کنید.")
            return

        if self.is_transcribing:
            return

        self._cancel_transcription_requested = False
        self.is_transcribing = True
        self.btn_transcribe.configure(bg=TEXT_MUTED, cursor="wait")
        self.btn_cancel_transcribe.pack(side="right", padx=(0, 8))
        self.lbl_progress_status.configure(text="⏳ در حال خواندن صوت و آماده‌سازی...", fg=ACCENT_BLUE_HOVER)

        def worker():
            start_t = time.time()
            orig_decode = None
            try:
                # ۱. خواندن ایمن فایل صوتی بدون نیاز به FFmpeg
                audio_arr, duration = load_audio_safely(self.selected_file_path)
                self.current_audio_duration = duration

                if getattr(self, "_cancel_transcription_requested", False):
                    raise InterruptedError("Cancelled")

                self.after(0, lambda: self.lbl_progress_status.configure(
                    text=f"⏳ در حال پردازش کلمات با مدل {self.current_model_name.upper()} ({duration:.1f}s)..."
                ))

                # هوک لغو بلادرنگ بر روی متد decode مدل ویسپر
                if self.whisper_model and hasattr(self.whisper_model, "decode"):
                    orig_decode = self.whisper_model.decode
                    def cancellable_decode(*args, **kwargs):
                        if getattr(self, "_cancel_transcription_requested", False):
                            raise InterruptedError("Cancelled")
                        return orig_decode(*args, **kwargs)
                    self.whisper_model.decode = cancellable_decode

                # ۲. استخراج کلمات و تایم‌استمپ‌ها
                use_cuda = getattr(self, '_active_device', 'cpu') == 'cuda'
                if use_cuda:
                    try:
                        import torch
                        torch.cuda.empty_cache()
                    except Exception:
                        pass
                    transcribe_params = dict(
                        beam_size=5,
                        best_of=5,
                        temperature=0.0,
                        fp16=False
                    )
                else:
                    transcribe_params = dict(
                        beam_size=1,
                        best_of=1,
                        temperature=0.0,
                        fp16=False
                    )

                result = self.whisper_model.transcribe(
                    audio_arr,
                    compression_ratio_threshold=2.4,
                    logprob_threshold=-1.0,
                    no_speech_threshold=0.6,
                    condition_on_previous_text=True,
                    initial_prompt="این یک فایل صوتی گفتاری به زبان فارسی و انگلیسی است. لطفاً تمام کلمات را با دقت بالا رونویسی کنید.",
                    **transcribe_params
                )

                if getattr(self, "_cancel_transcription_requested", False):
                    raise InterruptedError("Cancelled")

                elapsed = time.time() - start_t
                detected_lang = result.get("language", "fa")
                segments = result.get("segments", [])

                # ۳. بازه‌بندی هوشمند بر اساس آپشن کاربر
                is_active = self.interval_active_var.get()
                try:
                    interval_len = float(self.interval_sec_var.get())
                except Exception:
                    interval_len = 30.0

                seg_result = segment_transcription_text(
                    segments=segments,
                    total_duration=duration,
                    interval_seconds=interval_len,
                    enable_intervals=is_active
                )

                # ۴. ذخیره گزارش کامل در فایل متنی UTF-8
                saved_file = save_transcription_report(
                    segmented_text=seg_result["file_text"],
                    full_text=seg_result["full_text"],
                    source_path=self.selected_file_path,
                    model_name=self.current_model_name,
                    language=detected_lang,
                    duration=duration,
                    is_interval_active=is_active,
                    interval_seconds=interval_len
                )
                self.last_saved_filepath = saved_file
                self.last_results = seg_result

                # ۵. به‌روزرسانی UI
                self.after(0, lambda: self._on_transcription_complete(
                    results=seg_result,
                    saved_path=saved_file,
                    elapsed=elapsed,
                    duration=duration,
                    lang=detected_lang
                ))

            except InterruptedError:
                self.after(0, self._on_transcription_cancelled)
            except Exception as e:
                err_str = str(e) if str(e) else repr(e)
                self.after(0, lambda msg=err_str: self._on_transcription_error(msg))
            finally:
                if orig_decode and self.whisper_model:
                    self.whisper_model.decode = orig_decode
                self.is_transcribing = False
                self._cancel_transcription_requested = False
                try:
                    import torch
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                except Exception:
                    pass
                self.after(0, lambda: self.btn_cancel_transcribe.pack_forget())
                self.after(0, lambda: self.btn_transcribe.configure(bg=ACCENT_GREEN, cursor="hand2"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_transcription_complete(self, results: Dict[str, Any], saved_path: str, elapsed: float, duration: float, lang: str):
        self.btn_transcribe.configure(bg=ACCENT_GREEN, cursor="hand2")
        self.lbl_progress_status.configure(text=f"✓ تکمیل شد در {elapsed:.1f} ثانیه!", fg=ACCENT_GREEN)

        lang_title = "فارسی (Persian)" if lang == "fa" else "English" if lang == "en" else lang
        self.lbl_file_meta.configure(
            text=f"مدت صوت: {duration:.1f}s | زبان: {lang_title} | فایل: {Path(saved_path).name}",
            fg=TEXT_SECONDARY
        )

        # رندر متن در ویو
        self._switch_view("segmented")

        # باز کردن خودکار در نوت‌پد
        try:
            if sys.platform == "win32":
                os.startfile(saved_path)
        except Exception:
            pass

    def _on_transcription_error(self, err_msg: str):
        self.btn_transcribe.configure(bg=ACCENT_GREEN, cursor="hand2")
        self.lbl_progress_status.configure(text="❌ خطا در پردازش فایل", fg=ACCENT_RED)
        messagebox.showerror("خطا در پردازش صوت", f"خطایی رخ داد:\n\n{err_msg}")

    # --------------------------------------------------------------------------
    # مدیریت ویوها و دکمه‌های اکشن
    # --------------------------------------------------------------------------
    def _switch_view(self, mode: str):
        self.active_view = mode
        if mode == "segmented":
            self.btn_tab_segmented.configure(bg=ACCENT_BLUE, fg=TEXT_PRIMARY, font=(FONT_PERSIAN, 9, "bold"))
            self.btn_tab_full.configure(bg=CARD_SURFACE, fg=TEXT_SECONDARY, font=(FONT_PERSIAN, 9))
            if self.last_results:
                text_to_show = self.last_results["ui_text"]
            else:
                text_to_show = ""
        else:
            self.btn_tab_full.configure(bg=ACCENT_BLUE, fg=TEXT_PRIMARY, font=(FONT_PERSIAN, 9, "bold"))
            self.btn_tab_segmented.configure(bg=CARD_SURFACE, fg=TEXT_SECONDARY, font=(FONT_PERSIAN, 9))
            if self.last_results:
                text_to_show = self.last_results["full_text"]
            else:
                text_to_show = ""

        if text_to_show:
            self.text_editor.delete("1.0", "end")
            tag = "rtl" if self._has_persian(text_to_show) else "ltr"
            self.current_is_rtl = (tag == "rtl")
            self.text_editor.insert("1.0", text_to_show, tag)

    def _open_notepad(self):
        if self.last_saved_filepath and os.path.exists(self.last_saved_filepath):
            os.startfile(self.last_saved_filepath)
        else:
            messagebox.showinfo("پیام", "هنوز فایلی تبدیل نشده است.")

    def _copy_current_text(self):
        content = self.text_editor.get("1.0", "end-1c").strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            orig = self.btn_copy.cget("text")
            self.btn_copy.configure(text="✓ کپی شد!", fg=ACCENT_GREEN)
            self.after(1400, lambda: self.btn_copy.configure(text=orig, fg=TEXT_PRIMARY))

    def _open_output_folder(self):
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        os.startfile(str(OUTPUT_DIR))

    def _toggle_rtl(self):
        self.current_is_rtl = not self.current_is_rtl
        tag = "rtl" if self.current_is_rtl else "ltr"
        content = self.text_editor.get("1.0", "end-1c")
        self.text_editor.delete("1.0", "end")
        self.text_editor.insert("1.0", content, tag)

    @staticmethod
    def _has_persian(text: str) -> bool:
        return any('\u0600' <= c <= '\u06FF' for c in text)

    # --------------------------------------------------------------------------
    # بخش تب استخراج صوت از ویدیو (Video to Audio Extractor)
    # --------------------------------------------------------------------------
    def _switch_main_tab(self, tab_id: str):
        """تغییر تب اصلی برنامه بین تبدیل صوت به متن و استخراج از ویدیو و نمایش کنترل‌های اختصاصی هر تب"""
        self.current_main_tab = tab_id
        if tab_id == "transcribe":
            self.btn_nav_transcribe.configure(bg=ACCENT_BLUE, fg=TEXT_PRIMARY, font=(FONT_PERSIAN, 10, "bold"))
            self.btn_nav_video.configure(bg=CARD_SURFACE, fg=TEXT_SECONDARY, font=(FONT_PERSIAN, 10))

            # نمایش کنترل‌های هوش مصنوعی و وضعیت مدل
            if hasattr(self, "top_ctrl_video"):
                self.top_ctrl_video.pack_forget()
            if hasattr(self, "top_ctrl_transcribe"):
                self.top_ctrl_transcribe.pack(side="right", padx=16, pady=10)

            if hasattr(self, "lbl_desc"):
                self.lbl_desc.configure(text="سامانه تخصصی تبدیل صوت به متن با بازه‌بندی زمانی ۳۰ ثانیه‌ای | فارسی و انگلیسی")
                safe_wrap = max(260, self.winfo_width() - 550)
                self.lbl_desc.configure(wraplength=safe_wrap)

            self.page_video.pack_forget()
            self.page_transcribe.pack(fill="both", expand=True)
        else:
            self.btn_nav_video.configure(bg=ACCENT_BLUE, fg=TEXT_PRIMARY, font=(FONT_PERSIAN, 10, "bold"))
            self.btn_nav_transcribe.configure(bg=CARD_SURFACE, fg=TEXT_SECONDARY, font=(FONT_PERSIAN, 10))

            # پنهان‌سازی کنترل‌های هوش مصنوعی و نمایش وضعیت موتور استخراج ویدیو
            if hasattr(self, "top_ctrl_transcribe"):
                self.top_ctrl_transcribe.pack_forget()
            if hasattr(self, "top_ctrl_video"):
                self.top_ctrl_video.pack(side="right", padx=16, pady=10)

            if hasattr(self, "lbl_desc"):
                self.lbl_desc.configure(text="استخراج فوق‌سریع صوت از انواع ویدیو و کلیپ بدون افت کیفیت با موتور FFmpeg")
                safe_wrap = max(260, self.winfo_width() - 360)
                self.lbl_desc.configure(wraplength=safe_wrap)

            self.page_transcribe.pack_forget()
            self.page_video.pack(fill="both", expand=True)
            self._refresh_recent_extractions()

    def _build_video_extractor_ui(self):
        """طراحی رابط کاربری حرفه‌ای استخراج صوت از ویدیو"""
        # ۱. پنل انتخاب ویدیو و تنظیمات
        panel_v_input = tk.Frame(self.page_video, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        panel_v_input.pack(fill="x", padx=18, pady=4)

        v_inner = tk.Frame(panel_v_input, bg=CARD_BG)
        v_inner.pack(fill="x", padx=16, pady=12)

        title_box = tk.Frame(v_inner, bg=CARD_BG)
        title_box.pack(fill="x", pady=(0, 10))

        tk.Label(
            title_box,
            text="🎬 استخراج فایل صوتی از انواع کلیپ و ویدیو",
            font=(FONT_PERSIAN, 11, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_BG
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="استخراج فوق‌سریع صدا از ویدیوهای MP4, MKV, MOV, AVI, WEBM, FLV بدون افت کیفیت جهت آماده‌سازی برای ویسپر",
            font=(FONT_PERSIAN, 9),
            fg=TEXT_SECONDARY,
            bg=CARD_BG
        ).pack(anchor="w", pady=(2, 0))

        # ردیف انتخاب ویدیو
        row_file = tk.Frame(v_inner, bg=CARD_BG)
        row_file.pack(fill="x", pady=(4, 10))

        self.btn_browse_video = self._create_modern_btn(
            row_file,
            text="📁 انتخاب فایل ویدیو (Browse Video)",
            bg_color=ACCENT_BLUE,
            hover_color=ACCENT_BLUE_HOVER,
            command=self._browse_video
        )
        self.btn_browse_video.pack(side="left")

        self.lbl_video_display = tk.Label(
            row_file,
            text="هیچ فایل ویدیویی انتخاب نشده است (فرمت‌های MP4, MKV, MOV, AVI, WEBM, FLV پشتیبانی می‌شوند)",
            font=(FONT_FAMILY, 9),
            fg=TEXT_MUTED,
            bg=CARD_BG,
            anchor="w"
        )
        self.lbl_video_display.pack(side="left", fill="x", expand=True, padx=14)

        self.btn_extract_audio = self._create_modern_btn(
            row_file,
            text="⚡ شروع استخراج صوت",
            bg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            command=self._start_video_extraction_thread
        )
        self.btn_extract_audio.pack(side="right")

        # دکمه لغو استخراج ویدیو (در زمان استخراج در کنار دکمه شروع قرار می‌گیرد)
        self.btn_cancel_video = self._create_modern_btn(
            row_file,
            text="⏹️ لغو استخراج",
            bg_color=ACCENT_RED,
            hover_color="#dc2626",
            command=self._cancel_video_extraction
        )

        # ردیف تنظیمات فرمت و انتقال خودکار
        row_opts = tk.Frame(v_inner, bg=CARD_BG)
        row_opts.pack(fill="x", pady=(2, 0))

        tk.Label(row_opts, text="فرمت صوت استخراجی:", font=(FONT_PERSIAN, 9), fg=TEXT_SECONDARY, bg=CARD_BG).pack(side="left", padx=(0, 6))

        self.video_fmt_var = tk.StringVar(value="MP3 (کیفیت 192k - سبک)")
        self.combo_video_fmt = ttk.Combobox(
            row_opts,
            textvariable=self.video_fmt_var,
            values=[
                "MP3 (کیفیت 192k - سبک)",
                "WAV (16kHz - نیتیو ویسپر)"
            ],
            state="readonly",
            width=26
        )
        self.combo_video_fmt.pack(side="left", padx=(0, 16))

        self.auto_switch_var = tk.BooleanVar(value=True)
        self.chk_auto_switch = tk.Checkbutton(
            row_opts,
            text="انتقال خودکار به بخش تبدیل به متن پس از استخراج",
            variable=self.auto_switch_var,
            font=(FONT_PERSIAN, 9),
            fg=TEXT_PRIMARY,
            bg=CARD_BG,
            activebackground=CARD_BG,
            activeforeground=TEXT_PRIMARY,
            selectcolor=CARD_SURFACE
        )
        self.chk_auto_switch.pack(side="left")

        self.lbl_video_status = tk.Label(
            row_opts,
            text="",
            font=(FONT_PERSIAN, 9, "bold"),
            fg=ACCENT_BLUE_HOVER,
            bg=CARD_BG
        )
        self.lbl_video_status.pack(side="right")

        # ۲. پنل نتیجه استخراج و تاریخچه فایل‌ها
        panel_history = tk.Frame(self.page_video, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
        panel_history.pack(fill="both", expand=True, padx=18, pady=(6, 14))

        # بنر تبریک موفقیت استخراج (داینامیک)
        self.frame_video_success = tk.Frame(panel_history, bg=CARD_SURFACE, highlightbackground=ACCENT_GREEN, highlightthickness=1)

        success_top = tk.Frame(self.frame_video_success, bg=CARD_SURFACE)
        success_top.pack(fill="x", padx=16, pady=(10, 4))

        tk.Label(
            success_top,
            text="✅ فایل صوتی ویدیو با موفقیت استخراج شد!",
            font=(FONT_PERSIAN, 11, "bold"),
            fg=ACCENT_GREEN,
            bg=CARD_SURFACE
        ).pack(side="left")

        self.lbl_video_success_meta = tk.Label(
            success_top,
            text="",
            font=(FONT_FAMILY, 9),
            fg=TEXT_SECONDARY,
            bg=CARD_SURFACE
        )
        self.lbl_video_success_meta.pack(side="left", padx=16)

        success_actions = tk.Frame(self.frame_video_success, bg=CARD_SURFACE)
        success_actions.pack(fill="x", padx=16, pady=(4, 10))

        self.btn_send_direct = self._create_modern_btn(
            success_actions,
            text="🚀 ارسال مستقیم به بخش تبدیل به متن (Whisper)",
            bg_color=ACCENT_GREEN,
            hover_color=ACCENT_GREEN_HOVER,
            command=self._send_last_extracted_to_transcriber
        )
        self.btn_send_direct.pack(side="left", padx=(0, 8))

        self.btn_play_direct = self._create_small_btn(
            success_actions,
            "▶️ پخش صوت در ویندوز",
            self._play_last_extracted_audio
        )
        self.btn_play_direct.pack(side="left", padx=4)

        self.btn_folder_direct = self._create_small_btn(
            success_actions,
            "📂 باز کردن پوشه فایل‌ها",
            self._open_extractions_folder
        )
        self.btn_folder_direct.pack(side="left", padx=4)

        # تاریخچه استخراج‌ها
        hist_header = tk.Frame(panel_history, bg=CARD_BG)
        hist_header.pack(fill="x", padx=16, pady=(12, 6))

        tk.Label(
            hist_header,
            text="📋 فایل‌های صوتی استخراج‌شده اخیر (پوشه extracted_audio):",
            font=(FONT_PERSIAN, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_BG
        ).pack(side="left")

        btn_refresh = self._create_small_btn(hist_header, "🔄 بروزرسانی", self._refresh_recent_extractions)
        btn_refresh.pack(side="right", padx=3)

        btn_open_dir = self._create_small_btn(hist_header, "📁 پوشه خروجی", self._open_extractions_folder)
        btn_open_dir.pack(side="right", padx=3)

        # کانتینر اسکرول‌پذیر و ریسپانسیو تاریخچه
        list_container = tk.Frame(panel_history, bg="#111822", highlightbackground=BORDER_COLOR, highlightthickness=1)
        list_container.pack(fill="both", expand=True, padx=16, pady=(4, 14))

        self.canvas_recent = tk.Canvas(list_container, bg="#111822", highlightthickness=0)
        recent_scroll = tk.Scrollbar(list_container, orient="vertical", command=self.canvas_recent.yview)

        self.frame_recent_list = tk.Frame(self.canvas_recent, bg="#111822")
        self.frame_recent_list.bind(
            "<Configure>",
            lambda e: self.canvas_recent.configure(scrollregion=self.canvas_recent.bbox("all"))
        )
        self.canvas_recent_window = self.canvas_recent.create_window((0, 0), window=self.frame_recent_list, anchor="nw")
        self.canvas_recent.bind(
            "<Configure>",
            lambda e: self.canvas_recent.itemconfig(self.canvas_recent_window, width=e.width)
        )
        self.canvas_recent.configure(yscrollcommand=recent_scroll.set)

        self.canvas_recent.pack(side="left", fill="both", expand=True)
        recent_scroll.pack(side="right", fill="y")

        self.canvas_recent.bind_all(
            "<MouseWheel>",
            lambda e: self.canvas_recent.yview_scroll(int(-1 * (e.delta / 120)), "units") if getattr(self, "current_main_tab", "") == "video" else None
        )

        self._refresh_recent_extractions()

    def _browse_video(self):
        chosen = filedialog.askopenfilename(
            title="انتخاب فایل ویدیو برای استخراج صدا",
            filetypes=[
                ("All Supported Videos", "*.mp4 *.mkv *.mov *.avi *.webm *.flv *.wmv *.m4v *.3gp"),
                ("MP4 Files", "*.mp4"),
                ("MKV Files", "*.mkv"),
                ("MOV Files", "*.mov"),
                ("All Files", "*.*")
            ]
        )
        if chosen:
            self.selected_video_path = chosen
            name = Path(chosen).name
            disp_name = format_display_name(name, 45)
            size_mb = os.path.getsize(chosen) / (1024 * 1024)
            self.lbl_video_display.configure(
                text=f"✓ انتخاب شد: {disp_name} ({size_mb:.1f} MB)",
                fg=ACCENT_GREEN
            )

    def _cancel_video_extraction(self):
        """لغو فرآیند استخراج صوت از ویدیو توسط کاربر"""
        if hasattr(self, "_current_video_proc") and self._current_video_proc:
            self._current_video_proc._was_cancelled = True
            try:
                self._current_video_proc.kill()
            except Exception:
                pass
        self.lbl_video_status.configure(text="⏳ در حال لغو استخراج...", fg=ACCENT_YELLOW)
        self.btn_cancel_video.configure(bg=TEXT_MUTED, cursor="wait")

    def _on_video_extraction_cancelled(self):
        """بازنشانی رابط کاربری پس از لغو استخراج ویدیو"""
        self.btn_extract_audio.configure(bg=ACCENT_GREEN, cursor="hand2")
        self.btn_cancel_video.pack_forget()
        self.lbl_video_status.configure(text="⏹️ عملیات استخراج ویدیو توسط کاربر لغو شد.", fg=ACCENT_YELLOW)

    def _start_video_extraction_thread(self):
        if not self.selected_video_path or not os.path.exists(self.selected_video_path):
            messagebox.showwarning("توجه", "لطفاً ابتدا یک فایل ویدیویی را با دکمه «انتخاب فایل ویدیو» مشخص کنید.")
            return

        if self.is_extracting_audio:
            return

        self.is_extracting_audio = True
        self.btn_extract_audio.configure(bg=TEXT_MUTED, cursor="wait")
        self.btn_cancel_video.pack(side="right", padx=(0, 8))
        self.lbl_video_status.configure(text="⏳ در حال استخراج صدا با موتور FFmpeg...", fg=ACCENT_YELLOW)

        fmt_raw = self.combo_video_fmt.get().split()[0].lower()
        output_fmt = "wav" if "wav" in fmt_raw else "mp3"

        def on_proc(proc):
            self._current_video_proc = proc

        def worker():
            try:
                out_file, elapsed = extract_audio_from_video(
                    self.selected_video_path,
                    output_fmt,
                    on_process_start=on_proc
                )
                self.last_extracted_audio_path = out_file
                self.after(0, lambda: self._on_video_extraction_complete(out_file, elapsed))
            except InterruptedError:
                self.after(0, self._on_video_extraction_cancelled)
            except Exception as e:
                err_str = str(e) if str(e) else repr(e)
                self.after(0, lambda msg=err_str: self._on_video_extraction_error(msg))
            finally:
                self.is_extracting_audio = False
                self._current_video_proc = None
                self.after(0, lambda: self.btn_cancel_video.pack_forget())
                self.after(0, lambda: self.btn_extract_audio.configure(bg=ACCENT_GREEN, cursor="hand2"))

        threading.Thread(target=worker, daemon=True).start()

    def _on_video_extraction_complete(self, out_file: str, elapsed: float):
        self.btn_extract_audio.configure(bg=ACCENT_GREEN, cursor="hand2")
        self.lbl_video_status.configure(text=f"✓ استخراج با موفقیت در {elapsed:.1f} ثانیه انجام شد!", fg=ACCENT_GREEN)

        name = Path(out_file).name
        size_mb = os.path.getsize(out_file) / (1024 * 1024)
        self.lbl_video_success_meta.configure(
            text=f"فایل: {name}  |  حجم: {size_mb:.2f} MB  |  زمان استخراج: {elapsed:.1f}s ⚡"
        )
        self.frame_video_success.pack(fill="x", padx=16, pady=8)
        self._refresh_recent_extractions()

        if self.auto_switch_var.get():
            self.after(600, lambda: self._send_extracted_to_transcriber(out_file))

    def _on_video_extraction_error(self, err_msg: str):
        self.btn_extract_audio.configure(bg=ACCENT_GREEN, cursor="hand2")
        self.lbl_video_status.configure(text="❌ خطا در استخراج صوت", fg=ACCENT_RED)
        messagebox.showerror("خطا در استخراج صوت", f"خطایی رخ داد:\n\n{err_msg}")

    def _send_last_extracted_to_transcriber(self):
        if self.last_extracted_audio_path and os.path.exists(self.last_extracted_audio_path):
            self._send_extracted_to_transcriber(self.last_extracted_audio_path)
        else:
            messagebox.showinfo("پیام", "فایلی برای انتقال یافت نشد.")

    def _send_extracted_to_transcriber(self, filepath: str):
        if not os.path.exists(filepath):
            messagebox.showerror("خطا", "فایل صوتی یافت نشد.")
            return

        self.selected_file_path = filepath
        name = Path(filepath).name
        disp_name = format_display_name(name, 45)
        size_mb = os.path.getsize(filepath) / (1024 * 1024)
        self.lbl_file_display.configure(
            text=f"✓ انتخاب شد از ویدیو: {disp_name} ({size_mb:.1f} MB)",
            fg=ACCENT_GREEN
        )
        self._switch_main_tab("transcribe")

    def _play_last_extracted_audio(self):
        if self.last_extracted_audio_path and os.path.exists(self.last_extracted_audio_path):
            self._play_audio(Path(self.last_extracted_audio_path))

    def _play_audio(self, filepath: Path):
        try:
            if sys.platform == "win32":
                os.startfile(str(filepath))
        except Exception as e:
            messagebox.showerror("خطا", f"امکان پخش فایل وجود ندارد:\n{e}")

    def _delete_extracted_file(self, filepath: Path):
        try:
            if filepath.exists():
                filepath.unlink()
                self._refresh_recent_extractions()
        except Exception as e:
            messagebox.showerror("خطا", f"خطا در حذف فایل:\n{e}")

    def _open_extractions_folder(self):
        EXTRACTIONS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(EXTRACTIONS_DIR))
        except Exception:
            pass

    def _refresh_recent_extractions(self):
        if not hasattr(self, 'frame_recent_list'):
            return

        for child in self.frame_recent_list.winfo_children():
            child.destroy()

        files = list(EXTRACTIONS_DIR.glob("*.mp3")) + list(EXTRACTIONS_DIR.glob("*.wav"))
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        if not files:
            lbl_empty = tk.Label(
                self.frame_recent_list,
                text="هنوز هیچ فایل صوتی استخراج نشده است. با انتخاب ویدیو در بالا، فایل صوتی آن اینجا ذخیره می‌شود.",
                font=(FONT_PERSIAN, 9),
                fg=TEXT_MUTED,
                bg="#111822"
            )
            lbl_empty.pack(pady=35)
            return

        for p in files[:30]:
            row = tk.Frame(self.frame_recent_list, bg=CARD_SURFACE, highlightbackground=BORDER_COLOR, highlightthickness=1)
            row.pack(fill="x", pady=3, padx=10)

            size_mb = p.stat().st_size / (1024 * 1024)
            mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            disp_name = format_display_name(p.name, 42)
            info_text = f"🎵  {disp_name}   |   {size_mb:.2f} MB   |   {mtime}"

            lbl_info = tk.Label(row, text=info_text, font=(FONT_FAMILY, 9), fg=TEXT_PRIMARY, bg=CARD_SURFACE, anchor="w")
            lbl_info.pack(side="left", padx=10, fill="x", expand=True)

            btn_del = tk.Label(row, text="🗑️", font=(FONT_FAMILY, 9), fg=TEXT_MUTED, bg=CARD_SURFACE, cursor="hand2", padx=6, pady=4)
            btn_del.pack(side="right", padx=3)
            btn_del.bind("<Button-1>", lambda e, path=p: self._delete_extracted_file(path))

            btn_play = tk.Label(row, text="▶️ پخش", font=(FONT_PERSIAN, 8), fg=TEXT_SECONDARY, bg="#27384f", cursor="hand2", padx=8, pady=4)
            btn_play.pack(side="right", padx=3)
            btn_play.bind("<Button-1>", lambda e, path=p: self._play_audio(path))

            btn_send = tk.Label(row, text="🚀 ارسال به متن‌نویس", font=(FONT_PERSIAN, 8, "bold"), fg=TEXT_PRIMARY, bg=ACCENT_GREEN, cursor="hand2", padx=10, pady=4)
            btn_send.pack(side="right", padx=5)
            btn_send.bind("<Button-1>", lambda e, path=p: self._send_extracted_to_transcriber(str(path)))


# ==============================================================================
# تابع ورود به برنامه
# ==============================================================================
def main():
    app = WhisperFlowStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
