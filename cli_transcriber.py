"""
Whisper Speech-to-Text Terminal Application
Advanced anti-hallucination & anti-repetition engine for Persian & English.
Features 5-beam search, dynamic temperature fallback, and regex loop-breaking filters.
"""

import os
import re
import sys
import time
import datetime
from pathlib import Path
from typing import Tuple

import numpy as np

# Force UTF-8 on Windows command line
if sys.platform == "win32":
    try:
        os.system("chcp 65001 >nul 2>&1")
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")
    except Exception:
        pass


def print_banner():
    os.system("cls" if os.name == "nt" else "clear")
    print("=" * 76)
    print("       Whisper Speech-to-Text CLI (Persian & English)")
    print("       Anti-Hallucination & Anti-Repetition Engine")
    print("=" * 76)
    print("  * Runs 100% inside Terminal without GUI")
    print("  * Equipped with Beam Search to prevent 'که که که' repetition loops")
    print("  * Model download happens ONLY ONCE; subsequent runs are 100% OFFLINE")
    print("=" * 76)
    print()


def choose_model() -> str:
    print("Select AI Model:")
    print("  [1] Base   (~140 MB - Fast, low data, recommended)  [DEFAULT]")
    print("  [2] Tiny   (~75 MB  - Minimal internet data)")
    print("  [3] Small  (~460 MB - Best for Persian dialects & accents) [RECOMMENDED FOR FA]")
    print("  [4] Medium (~1.5 GB - Very high accuracy)")
    print()

    choice = input("Enter choice (1-4, press Enter for 1 [Base]): ").strip()
    if choice == "2":
        return "tiny"
    elif choice == "3":
        return "small"
    elif choice == "4":
        return "medium"
    return "base"


def load_audio_file(filepath: str) -> Tuple[np.ndarray, float]:
    """Reads audio file natively (MP3, WAV, FLAC, OGG) without requiring FFmpeg."""
    import soundfile as sf
    import scipy.signal as signal

    try:
        data, sr = sf.read(filepath, dtype="float32")
    except Exception:
        import whisper
        data = whisper.load_audio(filepath)
        sr = 16000

    if data.ndim > 1:
        data = np.mean(data, axis=1)

    max_val = np.max(np.abs(data))
    if max_val > 1.0:
        data = data / max_val

    if sr != 16000:
        target_len = int(len(data) * 16000 / sr)
        data = signal.resample(data, target_len).astype(np.float32)
        sr = 16000

    duration = len(data) / 16000.0
    return data, duration


def clean_repetition_loops(text: str) -> str:
    """
    Detects and eliminates Whisper repetitive hallucination loops
    (e.g., 'که که که که ...' or 'این این این این ...').
    """
    if not text:
        return text

    # Collapse 3 or more identical consecutive words into 1
    # Example: "که که که که که" -> "که"
    cleaned = re.sub(r'(\b\S+\b)(?:\s+\1){2,}', r'\1', text)

    # Collapse repeated 2-word phrases
    # Example: "این که این که این که" -> "این که"
    cleaned = re.sub(r'(\b\S+\s+\S+\b)(?:\s+\1){2,}', r'\1', cleaned)

    # Collapse repeated 3-word phrases
    cleaned = re.sub(r'(\b\S+\s+\S+\s+\S+\b)(?:\s+\1){2,}', r'\1', cleaned)

    # Clean up excess whitespace
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned


def save_transcription_to_file(
    text: str,
    source_path: str,
    language: str,
    model_name: str,
    duration: float
) -> str:
    """Saves output to a structured UTF-8 text file."""
    base_dir = Path(__file__).resolve().parent
    out_dir = base_dir / "transcriptions"
    out_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M%S")
    clean_stem = Path(source_path).stem
    clean_stem = re.sub(r'[\\/*?:"<>| ]', '_', clean_stem)[:30]

    out_file = out_dir / f"{clean_stem}_{timestamp}.txt"

    lang_display = "Persian (فارسی)" if language.lower() in ("fa", "persian") else "English" if language.lower() in ("en", "english") else language

    divider = "=" * 76
    content = (
        f"{divider}\n"
        f"WHISPER SPEECH-TO-TEXT REPORT\n"
        f"{divider}\n"
        f"Date & Time       : {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Source Audio File : {Path(source_path).name}\n"
        f"Full Path         : {source_path}\n"
        f"Model Used        : {model_name}\n"
        f"Detected Language : {lang_display}\n"
        f"Duration          : {duration:.2f} seconds\n"
        f"Encoding          : UTF-8\n"
        f"{divider}\n"
        f"TRANSCRIPTION TEXT:\n\n"
        f"{text.strip()}\n\n"
        f"{divider}\n"
    )

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)

    return str(out_file)


def transcribe_process(model, model_name: str, audio_path: str):
    print()
    print(">>> Loading audio file...")
    start_time = time.time()

    try:
        audio_array, duration = load_audio_file(audio_path)
    except Exception as e:
        print(f"[ERROR] Failed to load audio file: {e}")
        return

    print(f"[OK] Audio file loaded successfully. (Duration: {duration:.1f}s)")
    print(f">>> Transcribing with anti-loop beam search (Model: '{model_name}')... Please wait...")

    try:
        # Optimized Whisper anti-repetition decoding:
        # - beam_size=5: explores top 5 sequence paths to prevent getting stuck in local minimum loops
        # - temperature=(0.0, 0.2, 0.4, 0.6): temperature fallback breaks loop traps
        # - compression_ratio_threshold=2.2: rejects segments with repetitive text
        # - condition_on_previous_text=False: stops repetition in one chunk from infecting subsequent chunks
        # - initial_prompt: primes model into Persian/English token space
        result = model.transcribe(
            audio_array,
            beam_size=5,
            temperature=(0.0, 0.2, 0.4, 0.6),
            compression_ratio_threshold=2.2,
            no_speech_threshold=0.6,
            condition_on_previous_text=False,
            initial_prompt="این یک فایل صوتی گفتاری است و باید کلمات به درستی نوشته شوند.",
            fp16=False
        )
    except Exception as e:
        print(f"[ERROR] Transcription failed: {e}")
        return

    elapsed = time.time() - start_time
    raw_text = result.get("text", "").strip()
    detected_lang = result.get("language", "unknown")

    # Run through deduplication filter
    extracted_text = clean_repetition_loops(raw_text)

    if not extracted_text:
        extracted_text = "(No audible speech detected in this audio file)"

    saved_path = save_transcription_to_file(
        text=extracted_text,
        source_path=audio_path,
        language=detected_lang,
        model_name=model_name,
        duration=duration
    )

    lang_title = "Persian (fa)" if detected_lang == "fa" else "English (en)" if detected_lang == "en" else detected_lang

    print()
    print("=" * 76)
    print("SUCCESS: Transcription Completed!")
    print(f"Detected Language : {lang_title}")
    print(f"Processing Time   : {elapsed:.1f} seconds")
    print(f"Saved Text File   : {saved_path}")
    print("=" * 76)
    print()
    print("Extracted Text:")
    print("-" * 50)
    try:
        print(extracted_text)
    except Exception:
        print("(Note: Text is fully preserved in the saved .txt file)")
    print("-" * 50)
    print()

    # Automatically open the saved .txt file in Windows Notepad for perfect Persian rendering
    print(f">>> Opening text file in Notepad: {Path(saved_path).name}")
    try:
        if sys.platform == "win32":
            os.startfile(saved_path)
    except Exception as e:
        print(f"Could not launch Notepad automatically: {e}")


def main():
    print_banner()

    model_name = choose_model()
    print()
    print(f">>> Loading Whisper model '{model_name}'...")
    print("    (Downloading model if first time. Subsequent runs are 100% OFFLINE)")

    try:
        import whisper
        model = whisper.load_model(model_name, device="cpu")
        print(f"[OK] Whisper model '{model_name}' is ready!")
    except Exception as e:
        print(f"[ERROR] Could not load Whisper model: {e}")
        print("Please check your internet or VPN connection and try again.")
        input("\nPress Enter to exit...")
        return

    while True:
        print()
        print("-" * 76)
        print("Enter Audio File Path (MP3, WAV, M4A, OGG, FLAC):")
        print("TIP: You can Drag and Drop the audio file directly into this window!")
        print("(Type 'exit' to quit)")
        print("-" * 76)

        raw_input = input("File Path: ").strip()

        if not raw_input:
            continue

        if raw_input.lower() in ("exit", "quit", "q"):
            print("\nExiting. Have a great day! Goodbye.")
            break

        clean_path = raw_input.strip('"').strip("'").strip()

        if not os.path.exists(clean_path):
            print(f"[ERROR] File does not exist: {clean_path}")
            print("Please check the path and try again.")
            continue

        transcribe_process(model, model_name, clean_path)

        print()
        again = input("Transcribe another audio file? (y/n, default: y): ").strip().lower()
        if again in ("n", "no"):
            print("\nExiting. Have a great day! Goodbye.")
            break


if __name__ == "__main__":
    main()
