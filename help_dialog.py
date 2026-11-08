"""
Setup & Pip Requirements Dialog
Displays clear installation commands, system dependency check, and tips.
"""

import sys
import tkinter as tk
from tkinter import ttk

from gui_theme import (
    CARD_BG,
    SURFACE_BG,
    SURFACE_HOVER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    ACCENT_BLUE,
    ACCENT_GREEN,
    FONT_FAMILY,
    FONT_MONO
)


class HelpDialog(tk.Toplevel):
    """Modal dialog displaying setup commands and system status."""

    def __init__(self, parent, is_ffmpeg_found: bool, is_cuda: bool):
        super().__init__(parent)
        self.title("Setup Guide & Pip Installation")
        self.geometry("640x520")
        self.configure(bg=CARD_BG)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build_ui(is_ffmpeg_found, is_cuda)

    def _build_ui(self, is_ffmpeg_found: bool, is_cuda: bool):
        pad_x, pad_y = 18, 12

        # Title
        tk.Label(
            self,
            text="🛠️ System Setup & Dependencies Guide",
            font=(FONT_FAMILY, 14, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_BG
        ).pack(anchor="w", padx=pad_x, pady=(pad_y, 4))

        # Status pills
        status_frame = tk.Frame(self, bg=CARD_BG)
        status_frame.pack(fill="x", padx=pad_x, pady=4)

        ffmpeg_status = "✓ FFmpeg Available" if is_ffmpeg_found else "⚠ FFmpeg Missing (Needed for MP3)"
        ffmpeg_color = ACCENT_GREEN if is_ffmpeg_found else "#fbc02d"
        tk.Label(
            status_frame,
            text=ffmpeg_status,
            font=(FONT_FAMILY, 9, "bold"),
            fg=ffmpeg_color,
            bg=SURFACE_BG,
            padx=8,
            pady=3
        ).pack(side="left", padx=(0, 6))

        cuda_status = "⚡ CUDA GPU Active" if is_cuda else "💻 CPU Mode (FP32)"
        cuda_color = ACCENT_GREEN if is_cuda else "#4fc3f7"
        tk.Label(
            status_frame,
            text=cuda_status,
            font=(FONT_FAMILY, 9, "bold"),
            fg=cuda_color,
            bg=SURFACE_BG,
            padx=8,
            pady=3
        ).pack(side="left")

        # 1. Pip Install Command Section
        tk.Label(
            self,
            text="1. Exact Pip Installation Commands:",
            font=(FONT_FAMILY, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_BG
        ).pack(anchor="w", padx=pad_x, pady=(10, 2))

        pip_cmd = (
            "pip install openai-whisper sounddevice soundfile scipy numpy customtkinter imageio-ffmpeg"
        )
        self._create_code_box(pip_cmd)

        # 2. CUDA PyTorch (Optional)
        tk.Label(
            self,
            text="2. Optional NVIDIA CUDA Acceleration (for fast large-v3 execution):",
            font=(FONT_FAMILY, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_BG
        ).pack(anchor="w", padx=pad_x, pady=(8, 2))

        cuda_cmd = (
            "pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124"
        )
        self._create_code_box(cuda_cmd)

        # 3. FFmpeg Command
        tk.Label(
            self,
            text="3. Install FFmpeg on Windows (PowerShell):",
            font=(FONT_FAMILY, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_BG
        ).pack(anchor="w", padx=pad_x, pady=(8, 2))

        ffmpeg_cmd = "winget install Gyan.FFmpeg"
        self._create_code_box(ffmpeg_cmd)

        # 4. Info Tips
        tips = (
            "💡 Pro-Tips:\n"
            "• Live Microphone recording works 100% natively without needing FFmpeg.\n"
            "• OpenAI Whisper large-v3 delivers near-zero error rates for Persian and English.\n"
            "• All transcriptions are automatically saved in UTF-8 format inside ./transcriptions."
        )
        tk.Label(
            self,
            text=tips,
            font=(FONT_FAMILY, 9),
            fg=TEXT_SECONDARY,
            bg=CARD_BG,
            justify="left"
        ).pack(anchor="w", padx=pad_x, pady=(10, 6))

        # Close button
        btn_close = tk.Label(
            self,
            text="Close",
            font=(FONT_FAMILY, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=ACCENT_BLUE,
            padx=20,
            pady=6,
            cursor="hand2"
        )
        btn_close.pack(anchor="e", padx=pad_x, pady=(6, 12))
        btn_close.bind("<Button-1>", lambda e: self.destroy())

    def _create_code_box(self, code_text: str):
        box_frame = tk.Frame(self, bg="#111922", padx=8, pady=6)
        box_frame.pack(fill="x", padx=18, pady=2)

        lbl = tk.Label(
            box_frame,
            text=code_text,
            font=(FONT_MONO, 8),
            fg="#79c0ff",
            bg="#111922",
            anchor="w"
        )
        lbl.pack(side="left", fill="x", expand=True)

        btn_copy = tk.Label(
            box_frame,
            text="📋 Copy",
            font=(FONT_FAMILY, 8),
            fg=TEXT_PRIMARY,
            bg=SURFACE_BG,
            padx=6,
            pady=2,
            cursor="hand2"
        )
        btn_copy.pack(side="right")
        btn_copy.bind("<Enter>", lambda e: btn_copy.configure(bg=SURFACE_HOVER))
        btn_copy.bind("<Leave>", lambda e: btn_copy.configure(bg=SURFACE_BG))
        btn_copy.bind("<Button-1>", lambda e: self._copy(code_text, btn_copy))

    def _copy(self, text: str, btn: tk.Label):
        self.clipboard_clear()
        self.clipboard_append(text)
        btn.configure(text="✓ Copied!", fg=ACCENT_GREEN)
        self.after(1200, lambda: btn.configure(text="📋 Copy", fg=TEXT_PRIMARY))

