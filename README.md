# 🎙️ WhisperFlow — Advanced Speech-to-Text Desktop App
### Telegram & WhatsApp Style Voice Note Input Bar for Persian (Farsi) & English
#### Powered by OpenAI Whisper (`large-v3`) with Near-Zero Error Rate

---

![UI Style](https://img.shields.io/badge/GUI-Telegram--Style%20Dark-2481cc?style=for-the-badge)
![Whisper](https://img.shields.io/badge/Model-OpenAI%20Whisper%20large--v3-00a884?style=for-the-badge)
![Languages](https://img.shields.io/badge/Languages-Persian%20%26%20English-e53935?style=for-the-badge)
![Accuracy](https://img.shields.io/badge/Accuracy-Near--Zero%20Error%20Rate-fbc02d?style=for-the-badge)

---

## 🌟 Overview / معرفی برنامه

**WhisperFlow** is an advanced desktop graphical application designed specifically for converting spoken speech into text with maximum recognition accuracy. The application replicates the familiar, fluid user experience of **Telegram and WhatsApp chat input bars**, featuring an interactive voice note recording button, live animated waveform, system audio file importer, and automatic Right-to-Left (RTL) / Left-to-Right (LTR) text handling for **Persian (فارسی)** and **English**.

**برنامه WhisperFlow** یک نرم‌افزار پیشرفته دسکتاپ برای تبدیل گفتار به نوشتار با بالاترین دقت ممکن است. رابط کاربری این برنامه با الهام از نوار پیام‌رسان‌های تلگرام و واتساپ طراحی شده و با بهره‌گیری از قدرتمندترین مدل هوش مصنوعی **OpenAI Whisper (large-v3)**، خطای تشخیص کلمات در زبان‌های **فارسی و انگلیسی** را به صفر نزدیک می‌کند.

---

## 🚀 Key Features / ویژگی‌های کلیدی

1. **Telegram-Style Chat Input Bar**:
   - **Live Voice Note Recording (`🎙️`)**: Click the Telegram-style circular blue microphone button to start recording. It transforms into a recording console with a pulsing `🔴 REC` indicator, live timer (`00:05`), real-time dynamic audio waveform visualizer bouncing to your voice volume, and instant Cancel/Done controls.
   - **Local Audio/MP3 File Importer (`📎`)**: System file explorer dialog supporting MP3, WAV, M4A, OGG, FLAC, AAC, OPUS, and WMA formats.

2. **Maximum Accuracy Engine (Near-Zero Error Rate)**:
   - Utilizes OpenAI Whisper's **`large-v3`** model with 5-beam search decoding and deterministic greedy parameters (`temperature=0.0`) to eradicate hallucinations and maximize transcription accuracy for Persian vocabulary and English syntax.
   - **Automatic Language Detection**: Spoken language (Persian vs English) is automatically detected with confidence scores.

3. **Output & File Management**:
   - **Automatic UTF-8 Export**: Transcriptions are automatically saved to structured `.txt` files with UTF-8 encoding in the `./transcriptions/` folder.
   - **Interactive In-App Display**: Shows the text with one-click clipboard copy (`📋 Copy`), direct file opening (`📂 Open .txt`), and directory navigation.
   - **Intelligent RTL/LTR Alignment**: Automatically detects Persian/Arabic Unicode characters to align text to the right (RTL), while aligning English to the left (LTR). Manual toggle button (`⇄ RTL / LTR`) also included.
   - **Original Audio Preservation**: Recorded voice notes are preserved as standard 16kHz mono WAV files in `./recordings/`.

4. **Robust & Crash-Proof Architecture**:
   - **Zero UI Freezing**: Background worker threads handle model loading and transcription asynchronously.
   - **Direct In-Memory Microphone Pipeline**: Live voice recordings pass directly as float32 audio arrays into Whisper, working 100% natively without requiring FFmpeg.
   - **Graceful Hardware Detection**: Automatically detects NVIDIA CUDA GPUs vs CPU, applying `fp16=False` on CPU to prevent PyTorch crashes.

---

## 📦 Required Libraries & Installation / نیازمندی‌ها و نصب

### 1. Standard Installation (CPU & General Use):
Open your terminal (PowerShell or Command Prompt) and run:
```bash
pip install -r requirements.txt
```
Or install directly:
```bash
pip install openai-whisper sounddevice soundfile scipy numpy customtkinter Pillow imageio-ffmpeg
```

### 2. NVIDIA GPU Acceleration (Optional, for instant large-v3 speed):
If you have an NVIDIA graphics card with CUDA:
```bash
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install openai-whisper sounddevice soundfile scipy numpy customtkinter Pillow imageio-ffmpeg
```

### 3. FFmpeg Setup (For compressed files like MP3 / M4A):
- **Windows (PowerShell with Winget)**:
  ```powershell
  winget install Gyan.FFmpeg
  ```
- *Note*: Live microphone voice recording works natively in Python and does **not** require FFmpeg!

---

## 🖥️ Running the Application / نحوه اجرا

### Option 1: Double-Click Batch File (Windows)
Double-click [`run.bat`](run.bat). It verifies your Python environment and opens the GUI.

### Option 2: Command Line
```bash
python app.py
```

---

## 📁 Project Structure / ساختار پروژه

```
Voice-to-Text Converter/
│
├── app.py                     # Main application entry point & GUI controller
├── whisper_engine.py          # OpenAI Whisper large-v3 engine & beam search decoder
├── audio_recorder.py          # sounddevice live microphone recorder & RMS analyzer
├── file_manager.py            # UTF-8 text file saver & Windows explorer connector
│
├── chat_input_bar.py          # Telegram-style chat input bar with circular mic
├── transcript_panel.py        # Text viewer with Persian RTL & English LTR support
├── waveform_visualizer.py     # Live animated audio waveform canvas
├── top_toolbar.py             # Model selector, language mode & hardware badge
├── help_dialog.py             # Setup dialog with copyable pip commands
├── gui_theme.py               # Telegram dark palette & typography constants
│
├── transcriptions/            # Output folder for auto-saved UTF-8 .txt files
├── recordings/                # Output folder for recorded .wav voice notes
│
├── requirements.txt           # Pip dependencies list
├── run.bat                    # Windows batch launcher
└── README.md                  # Complete documentation (Persian & English)
```

---

## 📝 Generated Text File Sample / نمونه فایل متنی ذخیره‌شده

Each transcription is automatically saved as a UTF-8 text file:
```txt
================================================================================
WHISPER SPEECH-TO-TEXT TRANSCRIPTION REPORT
================================================================================
Date & Time      : 2026-11-07 01:25:00
Source Audio     : voice_note_001.wav
Whisper Model    : large-v3
Detected Language: 🇮🇷 Persian (فارسی) [Confidence: 99.4%]
Audio Duration   : 12.40 seconds
Encoding         : UTF-8
================================================================================
TRANSCRIPTION TEXT:

درود و وقت بخیر، این یک تبدیل صدای ضبط‌شده به متن با بالاترین دقت ممکن با مدل ویسپر است.
================================================================================
```

---

## ❓ Troubleshooting / رفع مشکلات احتمالی

- **Microphone permission error**: Go to Windows Settings > Privacy & Security > Microphone, and make sure "Let desktop apps access your microphone" is enabled.
- **FFmpeg error when opening MP3**: Run `winget install Gyan.FFmpeg` or `pip install imageio-ffmpeg`. WAV files and live recordings work even without FFmpeg.
- **Whisper model download speed**: On first use, Whisper downloads the `large-v3` weights (~3 GB) from OpenAI. This only happens once; subsequent runs load instantly from local cache.

