"""
Telegram-Style Chat Input Bar Component
Replicates Telegram & WhatsApp's voice note recording and audio file selection bar.
Includes file attachment button, recording status, animated waveform, timer, and circular mic button.
"""

import tkinter as tk
from typing import Callable, Optional

from gui_theme import (
    INPUT_BAR_BG,
    INPUT_BAR_BORDER,
    SURFACE_BG,
    SURFACE_HOVER,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
    TEXT_MUTED,
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    ACCENT_RED,
    ACCENT_RED_HOVER,
    ACCENT_GREEN,
    FONT_FAMILY,
    FONT_EMOJI,
    FONT_MONO
)
from waveform_visualizer import WaveformVisualizer


class ChatInputBar(tk.Frame):
    """
    Bottom chat input bar resembling Telegram Desktop's voice message interface.
    """

    STATE_IDLE = "idle"
    STATE_RECORDING = "recording"
    STATE_TRANSCRIBING = "transcribing"

    def __init__(
        self,
        parent,
        on_select_file: Callable[[], None],
        on_mic_click: Callable[[], None],
        on_cancel_recording: Callable[[], None],
        on_finish_recording: Callable[[], None],
        **kwargs
    ):
        super().__init__(parent, bg=INPUT_BAR_BG, highlightbackground=INPUT_BAR_BORDER, highlightthickness=1, **kwargs)

        self.on_select_file = on_select_file
        self.on_mic_click = on_mic_click
        self.on_cancel_recording = on_cancel_recording
        self.on_finish_recording = on_finish_recording

        self.current_state = self.STATE_IDLE
        self._pulse_timer = None
        self._pulse_phase = False

        self._build_ui()
        self.set_state(self.STATE_IDLE)

    def _build_ui(self):
        """Constructs the widgets inside the chat bar."""
        # Main layout: 3 sections (Left: File Button, Center: Dynamic Area, Right: Circular Mic)

        # ----------------- LEFT: File Attachment Button -----------------
        self.left_frame = tk.Frame(self, bg=INPUT_BAR_BG)
        self.left_frame.pack(side="left", padx=(12, 6), pady=8)

        # File Select Button (Paperclip + text)
        self.btn_file = tk.Frame(self.left_frame, bg=SURFACE_BG, cursor="hand2", padx=10, pady=6)
        self.btn_file.pack()

        self.lbl_clip = tk.Label(
            self.btn_file,
            text="📎",
            font=(FONT_EMOJI, 13),
            fg=TEXT_SECONDARY,
            bg=SURFACE_BG
        )
        self.lbl_clip.pack(side="left", padx=(0, 5))

        self.lbl_file_text = tk.Label(
            self.btn_file,
            text="Select Audio/MP3",
            font=(FONT_FAMILY, 10, "bold"),
            fg=TEXT_PRIMARY,
            bg=SURFACE_BG
        )
        self.lbl_file_text.pack(side="left")

        # Hover effects on File button
        for w in (self.btn_file, self.lbl_clip, self.lbl_file_text):
            w.bind("<Enter>", lambda e: self._on_hover_file(True))
            w.bind("<Leave>", lambda e: self._on_hover_file(False))
            w.bind("<Button-1>", lambda e: self.on_select_file())

        # ----------------- CENTER: Dynamic Context Frame -----------------
        self.center_frame = tk.Frame(self, bg=INPUT_BAR_BG)
        self.center_frame.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        # --- A. Idle State Center View ---
        self.idle_view = tk.Frame(self.center_frame, bg=INPUT_BAR_BG)

        self.lbl_placeholder = tk.Label(
            self.idle_view,
            text="Click 🎙️ to record voice note or 📎 to upload audio file...",
            font=(FONT_FAMILY, 10),
            fg=TEXT_SECONDARY,
            bg=INPUT_BAR_BG,
            anchor="w"
        )
        self.lbl_placeholder.pack(fill="x", pady=(2, 0))

        self.lbl_subtext = tk.Label(
            self.idle_view,
            text="Supports: MP3, WAV, M4A, OGG, FLAC | Auto-Detects Persian & English | Whisper large-v3",
            font=(FONT_FAMILY, 8),
            fg=TEXT_MUTED,
            bg=INPUT_BAR_BG,
            anchor="w"
        )
        self.lbl_subtext.pack(fill="x")

        # --- B. Recording State Center View (Telegram Voice Note Style) ---
        self.rec_view = tk.Frame(self.center_frame, bg=INPUT_BAR_BG)

        # Red recording dot + label
        self.rec_indicator = tk.Label(
            self.rec_view,
            text="● REC",
            font=(FONT_FAMILY, 10, "bold"),
            fg=ACCENT_RED,
            bg=INPUT_BAR_BG
        )
        self.rec_indicator.pack(side="left", padx=(0, 6))

        # Elapsed Timer (MM:SS)
        self.lbl_timer = tk.Label(
            self.rec_view,
            text="00:00",
            font=(FONT_MONO, 11, "bold"),
            fg=TEXT_PRIMARY,
            bg=INPUT_BAR_BG
        )
        self.lbl_timer.pack(side="left", padx=(0, 10))

        # Live animated waveform
        self.waveform = WaveformVisualizer(self.rec_view, height=36)
        self.waveform.pack(side="left", fill="x", expand=True, padx=4)

        # Cancel Button
        self.btn_cancel = tk.Label(
            self.rec_view,
            text="✕ Cancel",
            font=(FONT_FAMILY, 9, "bold"),
            fg=ACCENT_RED,
            bg=INPUT_BAR_BG,
            cursor="hand2",
            padx=8,
            pady=4
        )
        self.btn_cancel.pack(side="left", padx=4)
        self.btn_cancel.bind("<Enter>", lambda e: self.btn_cancel.configure(fg=ACCENT_RED_HOVER))
        self.btn_cancel.bind("<Leave>", lambda e: self.btn_cancel.configure(fg=ACCENT_RED))
        self.btn_cancel.bind("<Button-1>", lambda e: self.on_cancel_recording())

        # Done Checkmark Button
        self.btn_done = tk.Label(
            self.rec_view,
            text="✓ Transcribe",
            font=(FONT_FAMILY, 9, "bold"),
            fg=ACCENT_GREEN,
            bg=SURFACE_BG,
            cursor="hand2",
            padx=8,
            pady=4
        )
        self.btn_done.pack(side="left", padx=4)
        self.btn_done.bind("<Enter>", lambda e: self.btn_done.configure(bg=SURFACE_HOVER))
        self.btn_done.bind("<Leave>", lambda e: self.btn_done.configure(bg=SURFACE_BG))
        self.btn_done.bind("<Button-1>", lambda e: self.on_finish_recording())

        # --- C. Transcribing State Center View ---
        self.transcribing_view = tk.Frame(self.center_frame, bg=INPUT_BAR_BG)

        self.lbl_transcribing_status = tk.Label(
            self.transcribing_view,
            text="⏳ Transcribing audio with Whisper large-v3... Please wait.",
            font=(FONT_FAMILY, 10, "bold"),
            fg=ACCENT_BLUE_HOVER,
            bg=INPUT_BAR_BG,
            anchor="w"
        )
        self.lbl_transcribing_status.pack(fill="x", pady=5)

        # ----------------- RIGHT: Telegram Circular Mic Button -----------------
        self.right_frame = tk.Frame(self, bg=INPUT_BAR_BG)
        self.right_frame.pack(side="right", padx=(6, 12), pady=6)

        # 46x46 circular canvas mic button
        self.mic_size = 46
        self.mic_canvas = tk.Canvas(
            self.right_frame,
            width=self.mic_size,
            height=self.mic_size,
            bg=INPUT_BAR_BG,
            highlightthickness=0,
            cursor="hand2"
        )
        self.mic_canvas.pack()

        # Bind events
        self.mic_canvas.bind("<Enter>", self._on_mic_hover)
        self.mic_canvas.bind("<Leave>", self._on_mic_leave)
        self.mic_canvas.bind("<Button-1>", lambda e: self.on_mic_click())

        self._draw_mic_button(ACCENT_BLUE)

    def _draw_mic_button(self, circle_color: str, icon_text: str = "🎙️"):
        """Draws a smooth circular button on the canvas."""
        self.mic_canvas.delete("all")
        margin = 3
        # Circle background
        self.mic_canvas.create_oval(
            margin, margin,
            self.mic_size - margin, self.mic_size - margin,
            fill=circle_color,
            outline=""
        )
        # Center Icon
        self.mic_canvas.create_text(
            self.mic_size / 2,
            self.mic_size / 2,
            text=icon_text,
            font=(FONT_EMOJI, 14),
            fill="white"
        )

    def _on_hover_file(self, entering: bool):
        bg = SURFACE_HOVER if entering else SURFACE_BG
        self.btn_file.configure(bg=bg)
        self.lbl_clip.configure(bg=bg, fg=ACCENT_BLUE if entering else TEXT_SECONDARY)
        self.lbl_file_text.configure(bg=bg)

    def _on_mic_hover(self, event):
        if self.current_state == self.STATE_IDLE:
            self._draw_mic_button(ACCENT_BLUE_HOVER, "🎙️")
        elif self.current_state == self.STATE_RECORDING:
            self._draw_mic_button(ACCENT_RED_HOVER, "⏹")

    def _on_mic_leave(self, event):
        if self.current_state == self.STATE_IDLE:
            self._draw_mic_button(ACCENT_BLUE, "🎙️")
        elif self.current_state == self.STATE_RECORDING:
            self._draw_mic_button(ACCENT_RED, "⏹")

    def set_state(self, state: str):
        """Switches the UI between Idle, Recording, and Transcribing."""
        self.current_state = state

        # Hide all center views first
        self.idle_view.pack_forget()
        self.rec_view.pack_forget()
        self.transcribing_view.pack_forget()

        if state == self.STATE_IDLE:
            self.idle_view.pack(fill="both", expand=True)
            self._draw_mic_button(ACCENT_BLUE, "🎙️")
            self.waveform.set_active(False)
            self._stop_pulse()
            self.btn_file.configure(cursor="hand2")

        elif state == self.STATE_RECORDING:
            self.rec_view.pack(fill="both", expand=True)
            self._draw_mic_button(ACCENT_RED, "⏹")
            self.waveform.set_active(True, color="#2ea6ff")
            self.lbl_timer.configure(text="00:00")
            self._start_pulse()

        elif state == self.STATE_TRANSCRIBING:
            self.transcribing_view.pack(fill="both", expand=True)
            self._draw_mic_button(TEXT_MUTED, "⏳")
            self.waveform.set_active(False)
            self._stop_pulse()

    def update_recording_timer(self, time_str: str):
        """Updates the elapsed recording timer display."""
        if self.current_state == self.STATE_RECORDING:
            self.lbl_timer.configure(text=time_str)

    def update_waveform_volume(self, rms_normalized: float):
        """Passes real-time RMS volume to waveform visualizer."""
        if self.current_state == self.STATE_RECORDING:
            self.waveform.update_volume(rms_normalized)

    def set_transcribing_text(self, text: str):
        """Updates status text during transcription."""
        self.lbl_transcribing_status.configure(text=text)

    def _start_pulse(self):
        """Pulsing animation for REC indicator."""
        self._pulse_phase = not self._pulse_phase
        color = ACCENT_RED if self._pulse_phase else "#ff7675"
        self.rec_indicator.configure(fg=color)
        self._pulse_timer = self.after(500, self._start_pulse)

    def _stop_pulse(self):
        if self._pulse_timer:
            self.after_cancel(self._pulse_timer)
            self._pulse_timer = None

