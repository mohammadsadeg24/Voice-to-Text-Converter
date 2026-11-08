"""
Transcript Panel Component
Provides rich text display for transcribed output with automatic Persian RTL / English LTR
alignment, clipboard copy, file opening, and audio metadata badges.
"""

import sys
import tkinter as tk
from tkinter import messagebox
from typing import Optional, Callable

from gui_theme import (
    CARD_BG,
    SURFACE_BG,
    SURFACE_HOVER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    ACCENT_BLUE,
    ACCENT_GREEN,
    ACCENT_RED,
    BORDER_COLOR,
    FONT_FAMILY,
    FONT_PERSIAN,
    FONT_MONO
)
from file_manager import FileManager


class TranscriptPanel(tk.Frame):
    """
    Displays the transcription output with language badges,
    clipboard copy actions, and Persian RTL / English LTR support.
    """

    def __init__(self, parent, file_manager: FileManager, **kwargs):
        super().__init__(parent, bg=CARD_BG, **kwargs)
        self.file_manager = file_manager
        self.last_saved_filepath: Optional[str] = None
        self.is_rtl = False

        self._build_ui()

    def _build_ui(self):
        # 1. Top Header & Toolbar
        self.header_frame = tk.Frame(self, bg=CARD_BG)
        self.header_frame.pack(fill="x", padx=12, pady=(10, 6))

        # Title & Badges
        self.title_box = tk.Frame(self.header_frame, bg=CARD_BG)
        self.title_box.pack(side="left")

        self.lbl_title = tk.Label(
            self.title_box,
            text="📝 Transcribed Text",
            font=(FONT_FAMILY, 12, "bold"),
            fg=TEXT_PRIMARY,
            bg=CARD_BG
        )
        self.lbl_title.pack(side="left", padx=(0, 10))

        # Language Badge
        self.lbl_lang_badge = tk.Label(
            self.title_box,
            text="🌐 Ready",
            font=(FONT_FAMILY, 9, "bold"),
            fg=TEXT_SECONDARY,
            bg=SURFACE_BG,
            padx=8,
            pady=2
        )
        self.lbl_lang_badge.pack(side="left", padx=4)

        # Confidence & Duration Badge
        self.lbl_info_badge = tk.Label(
            self.title_box,
            text="",
            font=(FONT_FAMILY, 8),
            fg=TEXT_MUTED,
            bg=CARD_BG,
            padx=4
        )
        self.lbl_info_badge.pack(side="left", padx=4)

        # Right Action Buttons
        self.action_box = tk.Frame(self.header_frame, bg=CARD_BG)
        self.action_box.pack(side="right")

        # Copy Button
        self.btn_copy = self._create_action_button(
            self.action_box, "📋 Copy", self._copy_to_clipboard
        )
        self.btn_copy.pack(side="left", padx=3)

        # RTL / LTR Toggle Button
        self.btn_rtl = self._create_action_button(
            self.action_box, "⇄ RTL / LTR", self._toggle_rtl
        )
        self.btn_rtl.pack(side="left", padx=3)

        # Open File Button
        self.btn_open_file = self._create_action_button(
            self.action_box, "📂 Open .txt", self._open_saved_file
        )
        self.btn_open_file.pack(side="left", padx=3)

        # Open Folder Button
        self.btn_open_folder = self._create_action_button(
            self.action_box, "📁 Folder", self._open_folder
        )
        self.btn_open_folder.pack(side="left", padx=3)

        # Clear Button
        self.btn_clear = self._create_action_button(
            self.action_box, "🗑️ Clear", self._clear_text
        )
        self.btn_clear.pack(side="left", padx=3)

        # 2. Text Box with Scrollbar
        self.text_container = tk.Frame(
            self,
            bg="#18222d",
            highlightbackground=BORDER_COLOR,
            highlightthickness=1
        )
        self.text_container.pack(fill="both", expand=True, padx=12, pady=4)

        self.scrollbar = tk.Scrollbar(self.text_container)
        self.scrollbar.pack(side="right", fill="y")

        self.text_box = tk.Text(
            self.text_container,
            bg="#18222d",
            fg=TEXT_PRIMARY,
            insertbackground="#2ea6ff",
            selectbackground="#2b5278",
            selectforeground="#ffffff",
            font=(FONT_FAMILY, 12),
            wrap="word",
            relief="flat",
            height=10,
            padx=12,
            pady=10,
            yscrollcommand=self.scrollbar.set
        )
        self.text_box.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.text_box.yview)

        # Configure Tags for RTL and LTR
        self.text_box.tag_configure("rtl", justify="right", font=(FONT_PERSIAN, 12))
        self.text_box.tag_configure("ltr", justify="left", font=(FONT_FAMILY, 12))

        # Initial placeholder
        self.set_placeholder()

        # 3. Bottom File Info Bar
        self.footer_info = tk.Frame(self, bg=CARD_BG)
        self.footer_info.pack(fill="x", padx=14, pady=(4, 8))

        self.lbl_saved_path = tk.Label(
            self.footer_info,
            text="Outputs are automatically saved as UTF-8 text files in ./transcriptions",
            font=(FONT_FAMILY, 8),
            fg=TEXT_MUTED,
            bg=CARD_BG,
            anchor="w"
        )
        self.lbl_saved_path.pack(fill="x")

    def _create_action_button(self, parent, text: str, command: Callable) -> tk.Label:
        """Helper to create sleek modern buttons."""
        btn = tk.Label(
            parent,
            text=text,
            font=(FONT_FAMILY, 9),
            fg=TEXT_PRIMARY,
            bg=SURFACE_BG,
            padx=8,
            pady=4,
            cursor="hand2"
        )
        btn.bind("<Enter>", lambda e: btn.configure(bg=SURFACE_HOVER))
        btn.bind("<Leave>", lambda e: btn.configure(bg=SURFACE_BG))
        btn.bind("<Button-1>", lambda e: command())
        return btn

    def set_placeholder(self):
        """Sets welcoming instructional text."""
        self.text_box.delete("1.0", "end")
        msg = (
            "Welcome to Whisper Speech-to-Text Converter!\n\n"
            "• Use the 🎙️ Microphone button below to record voice notes.\n"
            "• Use the 📎 Select Audio button to transcribe any local MP3, WAV, M4A, or OGG file.\n"
            "• Persian (Farsi) and English spoken languages are detected automatically.\n"
            "• All transcriptions are automatically saved as UTF-8 text files.\n"
        )
        self.text_box.insert("1.0", msg, "ltr")

    def display_transcription(
        self,
        text: str,
        language: str,
        duration: float,
        confidence: Optional[float],
        saved_filepath: Optional[str] = None
    ):
        """
        Updates text box with new transcription, sets RTL/LTR alignment,
        and updates status badges.
        """
        self.last_saved_filepath = saved_filepath
        self.text_box.delete("1.0", "end")

        # Detect if text is predominantly Persian/Arabic
        self.is_rtl = self.file_manager.is_persian_or_arabic(text)
        tag = "rtl" if self.is_rtl else "ltr"

        self.text_box.insert("1.0", text, tag)

        # Update Language Badge
        lang_name = self.file_manager.format_language_name(language)
        self.lbl_lang_badge.configure(
            text=lang_name,
            fg=ACCENT_GREEN if language.lower() in ("fa", "persian") else ACCENT_BLUE
        )

        # Update Info Badge
        conf_str = f" • Confidence: {confidence:.1f}%" if confidence is not None else ""
        dur_str = f"⏱️ {duration:.1f}s"
        self.lbl_info_badge.configure(text=f"{dur_str}{conf_str}")

        # Update Footer with saved filepath
        if saved_filepath:
            self.lbl_saved_path.configure(
                text=f"✓ Saved to: {saved_filepath}",
                fg=ACCENT_GREEN
            )

    def _copy_to_clipboard(self):
        """Copies text to system clipboard with notification."""
        content = self.text_box.get("1.0", "end-1c").strip()
        if not content:
            return

        self.clipboard_clear()
        self.clipboard_append(content)

        # Visual feedback: flash button text
        orig_text = self.btn_copy.cget("text")
        self.btn_copy.configure(text="✓ Copied!", fg=ACCENT_GREEN)
        self.after(1400, lambda: self.btn_copy.configure(text=orig_text, fg=TEXT_PRIMARY))

    def _toggle_rtl(self):
        """Toggles between Right-to-Left and Left-to-Right text alignment."""
        content = self.text_box.get("1.0", "end-1c")
        if not content:
            return

        self.is_rtl = not self.is_rtl
        tag = "rtl" if self.is_rtl else "ltr"

        self.text_box.delete("1.0", "end")
        self.text_box.insert("1.0", content, tag)

    def _open_saved_file(self):
        """Opens the last saved text file in default Windows editor."""
        if self.last_saved_filepath:
            self.file_manager.open_path(self.last_saved_filepath)
        else:
            messagebox.showinfo("Information", "No transcription has been saved yet.")

    def _open_folder(self):
        """Opens the transcriptions output folder in Windows File Explorer."""
        self.file_manager.open_path(str(self.file_manager.transcriptions_dir))

    def _clear_text(self):
        """Clears text box and resets badges."""
        self.text_box.delete("1.0", "end")
        self.lbl_lang_badge.configure(text="🌐 Ready", fg=TEXT_SECONDARY)
        self.lbl_info_badge.configure(text="")
        self.lbl_saved_path.configure(
            text="Outputs are automatically saved as UTF-8 text files in ./transcriptions",
            fg=TEXT_MUTED
        )
        self.last_saved_filepath = None

