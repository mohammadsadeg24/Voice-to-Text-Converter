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
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

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


def format_timestamp(seconds: float) -> str:
    """فرمت‌دهی ثانیه‌ها به دقیقه:ثانیه (00:00)"""
    mins = int(seconds) // 60
    secs = int(seconds) % 60
    return f"{mins:02d}:{secs:02d}"


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
        else "متن پیوسته یکپارچه (طول صوت زیر ۳۰ ثانیه)"
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
        self.geometry("1020x760")
        self.minsize(860, 600)
        self.configure(bg=BG_MAIN)

        # ست کردن آیکون برنامه
        self._setup_window_icon()

        # فعال‌سازی Dark Titlebar بومی ویندوز ۱۰ و ۱۱
        self._apply_windows_dark_titlebar()

        # وضعیت‌های برنامه
        self.current_model_name = "small"  # بهترین مدل برای فارسی و انگلیسی
        self.whisper_model = None
        self.is_loading_model = False
        self.is_transcribing = False

        self.selected_file_path: Optional[str] = None
        self.current_audio_duration: float = 0.0
        self.last_saved_filepath: Optional[str] = None
        self.last_results: Optional[Dict[str, Any]] = None

        # ساخت لایه‌های گرافیکی
        self._build_interface()

        # لود مدل در رم به صورت خودکار در آغاز برنامه
        self.after(300, self._load_model_into_memory)

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
            text=" v2.5 Enterprise ",
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
            bg=CARD_BG
        )
        lbl_desc.pack(anchor="w", pady=(2, 0))

        # کنترل‌های وضعیت مدل و سخت‌افزار (سمت راست)
        top_ctrl = tk.Frame(header, bg=CARD_BG)
        top_ctrl.pack(side="right", padx=16, pady=10)

        # بج وضعیت لود مدل در RAM
        self.lbl_ram_status = tk.Label(
            top_ctrl,
            text="⏳ در حال لود اولیه مدل در RAM...",
            font=(FONT_PERSIAN, 9, "bold"),
            fg=ACCENT_YELLOW,
            bg=CARD_SURFACE,
            padx=12,
            pady=5
        )
        self.lbl_ram_status.pack(side="right", padx=(10, 0))

        # دراپ‌داون انتخاب مدل
        model_frame = tk.Frame(top_ctrl, bg=CARD_BG)
        model_frame.pack(side="right", padx=8)

        tk.Label(
            model_frame,
            text="مدل هوش مصنوعی:",
            font=(FONT_PERSIAN, 9),
            fg=TEXT_SECONDARY,
            bg=CARD_BG
        ).pack(side="left", padx=(0, 4))

        self.model_var = tk.StringVar(value="small (پیشنهادی - بالاترین دقت فارسی)")
        self.model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            values=[
                "small (پیشنهادی - بالاترین دقت فارسی)",
                "base (سریع و سبک)",
                "tiny (فوق‌العاده سبک)"
            ],
            state="readonly",
            width=28
        )
        self.model_combo.pack(side="left")
        self.model_combo.bind("<<ComboboxSelected>>", self._on_change_model)

        # ----------------- ۲. کارت انتخاب فایل و تنظیمات بازه‌بندی -----------------
        panel_cfg = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
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

        # ردیف ۲: آپشن‌های بازه‌بندی ۳۰ ثانیه‌ای و زبان
        row_opts = tk.Frame(cfg_inner, bg=CARD_BG)
        row_opts.pack(fill="x", pady=(6, 0))

        # چک‌باکس بازه‌بندی ۳۰ ثانیه‌ای
        self.interval_active_var = tk.BooleanVar(value=True)
        self.chk_interval = tk.Checkbutton(
            row_opts,
            text="بازه‌بندی متن‌ها بر اساس بازه زمانی ۳۰ ثانیه‌ای",
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
        interval_box.pack(side="left", padx=14)

        tk.Label(interval_box, text="طول هر بازه:", font=(FONT_PERSIAN, 8), fg=TEXT_SECONDARY, bg=CARD_BG).pack(side="left", padx=(0, 4))
        self.interval_sec_var = tk.StringVar(value="30")
        self.combo_interval = ttk.Combobox(
            interval_box,
            textvariable=self.interval_sec_var,
            values=["15", "30", "45", "60", "90"],
            state="readonly",
            width=5
        )
        self.combo_interval.pack(side="left")
        tk.Label(interval_box, text="ثانیه", font=(FONT_PERSIAN, 8), fg=TEXT_SECONDARY, bg=CARD_BG).pack(side="left", padx=(4, 0))

        # راهنما
        lbl_hint = tk.Label(
            row_opts,
            text="(نکته: فایل‌ها و ویس‌های کمتر از ۳۰ ثانیه خودکار به عنوان یک متن خروجی داده می‌شوند)",
            font=(FONT_PERSIAN, 8),
            fg=TEXT_MUTED,
            bg=CARD_BG
        )
        lbl_hint.pack(side="left", padx=10)

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
        panel_output = tk.Frame(self, bg=CARD_BG, highlightbackground=BORDER_COLOR, highlightthickness=1)
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
            "به نرم‌افزار WhisperFlow Studio Pro خوش آمدید!\n\n"
            "ویژگی‌های کلیدی و فرآیند کار:\n"
            "۱. نگهداری مدل در حافظه RAM: مدل هوش مصنوعی فقط یک‌بار لود می‌شود و در حافظه فعال می‌ماند.\n"
            "   (از این رو می‌توانید بی‌شمار فایل را بدون فوت وقت و بدون مصرف اینترنت تبدیل کنید).\n"
            "۲. بازه‌بندی هوشمند ۳۰ ثانیه‌ای: فایل‌های طولانی به بازه‌های [00:00 - 00:30] و ... تفکیک می‌شوند.\n"
            "۳. فایل‌های صوتی کمتر از ۳۰ ثانیه به صورت خودکار به شکل یک متن یکپارچه نمایش داده می‌شوند.\n"
            "۴. خروجی در قالب فایل متنی استاندارد UTF-8 ذخیره شده و با یک کلیک در Notepad باز می‌شود.\n\n"
            "برای شروع، روی دکمه «📁 انتخاب فایل صوتی» کلیک کنید."
        )
        self.text_editor.insert("1.0", msg, "rtl")

    # --------------------------------------------------------------------------
    # مدیریت مدل در حافظه RAM (یک‌بار لود، مصرف اینترنت: صفر)
    # --------------------------------------------------------------------------
    def _load_model_into_memory(self):
        """لود مدل هوش مصنوعی در رم و بررسی پوشه محلی models/"""
        def worker():
            self.is_loading_model = True
            model_target = self.current_model_name

            self.after(0, lambda: self.lbl_ram_status.configure(
                text=f"⏳ در حال بارگذاری مدل {model_target.upper()} در RAM...",
                fg=ACCENT_YELLOW
            ))

            try:
                import whisper

                # ۱. بررسی اینکه آیا فایل مدل در پوشه محلی models/ وجود دارد یا خیر (برای پرتابل بودن روی سیستم همکار)
                local_model_file = MODELS_DIR / f"{model_target}.pt"
                if local_model_file.exists():
                    model_path_or_name = str(local_model_file)
                else:
                    model_path_or_name = model_target

                # لود پایدار روی پردازنده سیستم
                model = whisper.load_model(model_path_or_name, device="cpu")
                self.whisper_model = model

                self.after(0, lambda: self.lbl_ram_status.configure(
                    text=f"🟢 مدل {model_target.upper()} آماده در رم (آفلاین)",
                    fg=ACCENT_GREEN
                ))

            except Exception as e:
                self.after(0, lambda: self.lbl_ram_status.configure(
                    text=f"❌ خطا در بارگذاری: {str(e)[:30]}",
                    fg=ACCENT_RED
                ))
            finally:
                self.is_loading_model = False

        threading.Thread(target=worker, daemon=True).start()

    def _on_change_model(self, event=None):
        selected_raw = self.model_var.get().split()[0].lower()
        if selected_raw != self.current_model_name:
            self.current_model_name = selected_raw
            self._load_model_into_memory()

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
            size_mb = os.path.getsize(chosen) / (1024 * 1024)
            self.lbl_file_display.configure(
                text=f"✓ انتخاب شد: {name} ({size_mb:.1f} MB)",
                fg=ACCENT_GREEN
            )

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

        self.is_transcribing = True
        self.btn_transcribe.configure(bg=TEXT_MUTED, cursor="wait")
        self.lbl_progress_status.configure(text="⏳ در حال خواندن صوت و آماده‌سازی...", fg=ACCENT_BLUE_HOVER)

        def worker():
            start_t = time.time()
            try:
                # ۱. خواندن ایمن فایل صوتی بدون نیاز به FFmpeg
                audio_arr, duration = load_audio_safely(self.selected_file_path)
                self.current_audio_duration = duration

                self.after(0, lambda: self.lbl_progress_status.configure(
                    text=f"⏳ در حال پردازش کلمات با مدل {self.current_model_name.upper()} ({duration:.1f}s)..."
                ))

                # ۲. استخراج کلمات و تایم‌استمپ‌ها با الگوریتم Beam Search
                # - جلوگیری از لوپ تکرار کلمات
                # - فال‌بک داینامیک دما
                result = self.whisper_model.transcribe(
                    audio_arr,
                    beam_size=5,
                    temperature=(0.0, 0.2, 0.4),
                    compression_ratio_threshold=2.2,
                    condition_on_previous_text=False,
                    initial_prompt="این یک فایل صوتی گفتاری به زبان فارسی و انگلیسی است.",
                    fp16=False
                )

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

            except Exception as e:
                self.after(0, lambda: self._on_transcription_error(str(e)))
            finally:
                self.is_transcribing = False

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


# ==============================================================================
# تابع ورود به برنامه
# ==============================================================================
def main():
    app = WhisperFlowStudio()
    app.mainloop()


if __name__ == "__main__":
    main()
