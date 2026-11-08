"""
Live Waveform Visualizer Component
Canvas-based animated audio visualizer mimicking Telegram's voice note waveform.
"""

import math
import random
import tkinter as tk
from typing import List

from gui_theme import (
    INPUT_BAR_BG,
    ACCENT_BLUE,
    ACCENT_BLUE_HOVER,
    ACCENT_RED,
    TEXT_MUTED
)


class WaveformVisualizer(tk.Canvas):
    """
    Animated audio waveform canvas displaying reactive bars
    matching Telegram's voice note recording interface.
    """

    NUM_BARS = 30
    BAR_WIDTH = 4
    BAR_GAP = 3
    MIN_BAR_HEIGHT = 4
    MAX_BAR_HEIGHT = 32

    def __init__(self, parent, height: int = 40, **kwargs):
        width = self.NUM_BARS * (self.BAR_WIDTH + self.BAR_GAP) + 10
        super().__init__(
            parent,
            width=width,
            height=height,
            bg=INPUT_BAR_BG,
            highlightthickness=0,
            **kwargs
        )
        self.height = height
        self.width = width
        self.bar_heights: List[float] = [self.MIN_BAR_HEIGHT] * self.NUM_BARS
        self.target_heights: List[float] = [self.MIN_BAR_HEIGHT] * self.NUM_BARS
        self.is_active = False
        self.color = "#2ea6ff"
        self._anim_job = None

        self._draw_waveform()

    def set_active(self, active: bool, color: str = "#2ea6ff"):
        """Enables or disables live animation."""
        self.is_active = active
        self.color = color
        if active:
            if not self._anim_job:
                self._animate()
        else:
            if self._anim_job:
                self.after_cancel(self._anim_job)
                self._anim_job = None
            self.target_heights = [self.MIN_BAR_HEIGHT] * self.NUM_BARS
            self.bar_heights = [self.MIN_BAR_HEIGHT] * self.NUM_BARS
            self._draw_waveform()

    def update_volume(self, rms_normalized: float):
        """
        Receives normalized RMS volume (0.0 to 1.0) and injects into bars.
        Creates an organic wave effect across the visualizer.
        """
        if not self.is_active:
            return

        # Shift existing heights to the left
        self.target_heights.pop(0)

        # Scale volume non-linearly for speech responsiveness
        scaled = math.pow(min(1.0, rms_normalized * 1.4), 0.7)
        jitter = random.uniform(0.85, 1.15)
        new_h = self.MIN_BAR_HEIGHT + scaled * (self.MAX_BAR_HEIGHT - self.MIN_BAR_HEIGHT) * jitter
        new_h = max(self.MIN_BAR_HEIGHT, min(self.MAX_BAR_HEIGHT, new_h))

        self.target_heights.append(new_h)

    def _animate(self):
        """Smoothly interpolates bar heights towards target heights."""
        if not self.is_active:
            return

        # Smooth interpolation (lerp)
        for i in range(self.NUM_BARS):
            diff = self.target_heights[i] - self.bar_heights[i]
            self.bar_heights[i] += diff * 0.45

        self._draw_waveform()
        self._anim_job = self.after(33, self._animate)  # ~30 FPS

    def _draw_waveform(self):
        """Redraws all visualizer bars on canvas."""
        self.delete("all")
        mid_y = self.height / 2.0
        start_x = 5

        for i, h in enumerate(self.bar_heights):
            x0 = start_x + i * (self.BAR_WIDTH + self.BAR_GAP)
            y0 = mid_y - (h / 2.0)
            x1 = x0 + self.BAR_WIDTH
            y1 = mid_y + (h / 2.0)

            # Draw rounded or rectangle bar
            self.create_rectangle(
                x0, y0, x1, y1,
                fill=self.color if self.is_active else TEXT_MUTED,
                outline=""
            )

