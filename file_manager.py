"""
File Manager Module
Handles automatic saving of UTF-8 encoded transcription text files,
organization of recorded audio files, and system explorer interactions.
"""

import os
import re
import sys
import datetime
from pathlib import Path
from typing import Optional


class FileManager:
    """Manages transcriptions and recordings directories, file naming, and auto-saving."""

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir is None:
            self.base_dir = Path(__file__).resolve().parent
        else:
            self.base_dir = Path(base_dir).resolve()

        self.transcriptions_dir = self.base_dir / "transcriptions"
        self.recordings_dir = self.base_dir / "recordings"

        # Ensure output directories exist
        self.transcriptions_dir.mkdir(parents=True, exist_ok=True)
        self.recordings_dir.mkdir(parents=True, exist_ok=True)

    def save_transcription(
        self,
        text: str,
        source_name: str,
        language: str = "auto",
        model_name: str = "large-v3",
        duration: float = 0.0,
        confidence: Optional[float] = None
    ) -> str:
        """
        Saves extracted text to a clean, UTF-8 encoded .txt file in the transcriptions folder.

        Args:
            text: Transcribed text string
            source_name: Name of audio file or 'Live Recording'
            language: Detected or specified language (e.g. 'fa', 'en')
            model_name: Whisper model used (e.g. 'large-v3')
            duration: Audio duration in seconds
            confidence: Language probability or confidence score (0-100%)

        Returns:
            The absolute path of the created text file.
        """
        now = datetime.datetime.now()
        timestamp_str = now.strftime("%Y%m%d_%H%M%S")
        readable_date = now.strftime("%Y-%m-%d %H:%M:%S")

        # Sanitize source name for filename
        clean_source = Path(source_name).stem
        clean_source = re.sub(r'[\\/*?:"<>| ]', '_', clean_source)[:30]
        if not clean_source or clean_source == "Live_Recording":
            clean_source = "voice_note"

        filename = f"transcription_{clean_source}_{timestamp_str}.txt"
        filepath = self.transcriptions_dir / filename

        # Format language display
        lang_display = self.format_language_name(language)
        conf_str = f" [Confidence: {confidence:.1f}%]" if confidence is not None else ""

        # Build structured file content
        divider = "=" * 80
        content = (
            f"{divider}\n"
            f"WHISPER SPEECH-TO-TEXT TRANSCRIPTION REPORT\n"
            f"{divider}\n"
            f"Date & Time      : {readable_date}\n"
            f"Source Audio     : {source_name}\n"
            f"Whisper Model    : {model_name}\n"
            f"Detected Language: {lang_display}{conf_str}\n"
            f"Audio Duration   : {duration:.2f} seconds\n"
            f"Encoding         : UTF-8\n"
            f"{divider}\n"
            f"TRANSCRIPTION TEXT:\n\n"
            f"{text.strip()}\n\n"
            f"{divider}\n"
        )

        # Write as UTF-8
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        return str(filepath)

    def get_new_recording_path(self) -> str:
        """Generates a timestamped path for saving live audio recordings (.wav)."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rec_{timestamp}.wav"
        return str(self.recordings_dir / filename)

    @staticmethod
    def format_language_name(lang_code: str) -> str:
        """Converts language code to human-readable string with flag emoji."""
        code = lang_code.lower().strip()
        if code in ("fa", "persian", "farsi"):
            return "🇮🇷 Persian (فارسی)"
        elif code in ("en", "english"):
            return "🇬🇧 English"
        elif code in ("ar", "arabic"):
            return "🇸🇦 Arabic"
        elif code in ("de", "german"):
            return "🇩🇪 German"
        elif code in ("fr", "french"):
            return "🇫🇷 French"
        elif code in ("es", "spanish"):
            return "🇪🇸 Spanish"
        elif code in ("tr", "turkish"):
            return "🇹🇷 Turkish"
        elif code == "auto":
            return "Auto-Detect"
        return f"🌐 {code.upper()}"

    @staticmethod
    def is_persian_or_arabic(text: str) -> bool:
        """
        Detects if text contains predominantly Persian / Arabic Unicode characters.
        Useful for auto-aligning text (RTL vs LTR) in the UI.
        """
        persian_count = sum(
            1 for c in text
            if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F'
            or '\uFB50' <= c <= '\uFDFF' or '\uFE70' <= c <= '\uFEFF'
        )
        latin_count = sum(
            1 for c in text
            if ('a' <= c <= 'z') or ('A' <= c <= 'Z')
        )
        return persian_count >= latin_count and persian_count > 0

    @staticmethod
    def open_path(path: str) -> bool:
        """Opens a file or folder in Windows Explorer or default application safely."""
        try:
            if sys.platform == "win32":
                os.startfile(path)
                return True
            else:
                import subprocess
                subprocess.run(["xdg-open", path], check=False)
                return True
        except Exception as e:
            print(f"Error opening path {path}: {e}")
            return False

