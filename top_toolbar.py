"""
Top Toolbar Component
Houses the application branding, Whisper model selector, language mode selector,
hardware accelerator status badge, and system setup guide dialog.
"""

import sys
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from gui_theme import (
    CARD_BG,
    SURFACE_BG,
    SURFACE_HOVER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    ACCENT_BLUE,
    ACCENT_GREEN,
    BORDER_COLOR,
    FONT_FAMILY,
    FONT_EMOJI,
    FONT_MONO
)


class TopToolbar(tk.Frame):
    """
    Top control strip for configuring model, language, and inspecting hardware acceleration.
    Designed with a clean, responsive 2-row layout that never clips on high-DPI screens.
    """

    def __init__(
        self,
        parent,
        current_model: str,
        available_models: list[str],
        device_description: str,
        is_cuda: bool,
        on_model_change: Callable[[str], None],
        on_language_change: Callable[[str], None],
        on_show_help: Callable[[], None],
        **kwargs
    ):
        super().__init__(parent, bg=CARD_BG, **kwargs)

        self.current_model = current_model
        self.available_models = available_models
        self.device_description = device_description
        self.is_cuda = is_cuda
        self.on_model_change = on_model_change
        self.on_language_change = on_language_change
        self.on_show_help = on_show_help

        self._build_ui()

    def _build_ui(self):
        # ----------------- ROW 1: Title & System Status -----------------
        row1 = tk.Frame(self, bg=CARD_BG)
        row1.pack(fill="x", padx=14, pady=(10, 4))

        # Title
        title_lbl = tk.Label(
            row1,
            text="🎙️ WhisperFlow STT",
            font=(FONT_FAMILY, 15, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_BG
        )
        title_lbl.pack(side="left")

        # Right Side of Row 1: Setup & Hardware Badges
        r1_right = tk.Frame(row1, bg=CARD_BG)
        r1_right.pack(side="right")

        # Help Button
        btn_help = tk.Label(
            r1_right,
            text="❓ Setup & Pip",
            font=(FONT_FAMILY, 9),
            fg=TEXT_PRIMARY,
            bg=SURFACE_BG,
            padx=10,
            pady=4,
            cursor="hand2"
        )
        btn_help.pack(side="right", padx=(6, 0))
        btn_help.bind("<Enter>", lambda e: btn_help.configure(bg=SURFACE_HOVER))
        btn_help.bind("<Leave>", lambda e: btn_help.configure(bg=SURFACE_BG))
        btn_help.bind("<Button-1>", lambda e: self.on_show_help())

        # Hardware Accelerator Badge
        hw_text = f"⚡ {self.device_description}" if self.is_cuda else f"💻 {self.device_description}"
        hw_color = ACCENT_GREEN if self.is_cuda else "#4fc3f7"

        hw_badge = tk.Label(
            r1_right,
            text=hw_text,
            font=(FONT_FAMILY, 8, "bold"),
            fg=hw_color,
            bg=SURFACE_BG,
            padx=10,
            pady=4
        )
        hw_badge.pack(side="right", padx=6)

        # ----------------- ROW 2: Subtitle & Selectors -----------------
        row2 = tk.Frame(self, bg=CARD_BG)
        row2.pack(fill="x", padx=14, pady=(2, 10))

        # Subtitle
        sub_lbl = tk.Label(
            row2,
            text="Telegram-Style Speech-to-Text | Persian (فارسی) & English",
            font=(FONT_FAMILY, 9),
            fg=TEXT_SECONDARY,
            bg=CARD_BG
        )
        sub_lbl.pack(side="left")

        # Right Side of Row 2: Model & Language Selectors
        r2_right = tk.Frame(row2, bg=CARD_BG)
        r2_right.pack(side="right")

        # Language Selector
        lang_frame = tk.Frame(r2_right, bg=CARD_BG)
        lang_frame.pack(side="right", padx=(10, 0))

        tk.Label(
            lang_frame,
            text="Language:",
            font=(FONT_FAMILY, 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=CARD_BG
        ).pack(side="left", padx=(0, 5))

        self.lang_var = tk.StringVar(value="Auto-Detect (fa / en)")
        self.lang_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.lang_var,
            values=[
                "Auto-Detect (fa / en)",
                "Persian (فارسی)",
                "English (en)"
            ],
            state="readonly",
            width=20
        )
        self.lang_combo.pack(side="left")
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang_selected)

        # Model Selector
        model_frame = tk.Frame(r2_right, bg=CARD_BG)
        model_frame.pack(side="right", padx=6)

        tk.Label(
            model_frame,
            text="Model:",
            font=(FONT_FAMILY, 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=CARD_BG
        ).pack(side="left", padx=(0, 5))

        self.model_var = tk.StringVar(value=self.current_model)
        self.model_combo = ttk.Combobox(
            model_frame,
            textvariable=self.model_var,
            values=self.available_models,
            state="readonly",
            width=13
        )
        self.model_combo.pack(side="left")
        self.model_combo.bind("<<ComboboxSelected>>", self._on_model_selected)

    def _on_model_selected(self, event=None):
        selected = self.model_var.get()
        self.on_model_change(selected)

    def _on_lang_selected(self, event=None):
        val = self.lang_var.get()
        if "Persian" in val:
            code = "fa"
        elif "English" in val:
            code = "en"
        else:
            code = "auto"
        self.on_language_change(code)
