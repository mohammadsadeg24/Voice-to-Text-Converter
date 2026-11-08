"""
Telegram-Inspired Theme Constants and Styling Helper
"""

import sys

# Color Palette (Telegram Desktop Dark Theme)
BG_MAIN = "#0e1621"          # Deep dark window background
CARD_BG = "#17212b"          # Main panel background
SURFACE_BG = "#242f3d"       # Card / bubble surface
SURFACE_HOVER = "#2b394b"    # Hover surface
INPUT_BAR_BG = "#1e2c3a"     # Chat input bar background
INPUT_BAR_BORDER = "#2f4156" # Chat input border
BORDER_COLOR = "#232e3c"     # Card and element border

# Text Colors
TEXT_PRIMARY = "#ffffff"     # Main white text
TEXT_SECONDARY = "#8da0b6"   # Muted slate text
TEXT_MUTED = "#607489"       # Subdued text
TEXT_LINK = "#54a9eb"        # Telegram blue link

# Accent Colors
ACCENT_BLUE = "#2481cc"      # Telegram primary blue
ACCENT_BLUE_HOVER = "#2da3f0"# Hover blue
ACCENT_GREEN = "#2ecc71"     # Success / Persian flag green
ACCENT_RED = "#e53935"       # Recording / error red
ACCENT_RED_HOVER = "#f44336" # Red hover
ACCENT_YELLOW = "#fbc02d"    # Warning yellow

# Fonts (Graceful fallback across Windows systems)
FONT_FAMILY = "Segoe UI" if sys.platform == "win32" else "Helvetica"
FONT_EMOJI = "Segoe UI Emoji" if sys.platform == "win32" else "Apple Color Emoji"
FONT_MONO = "Consolas" if sys.platform == "win32" else "Courier"
FONT_PERSIAN = "Tahoma" if sys.platform == "win32" else "Vazirmatn"
