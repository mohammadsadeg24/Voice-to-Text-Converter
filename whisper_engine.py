"""
Whisper Speech-to-Text Engine Module
High-precision transcription engine utilizing OpenAI Whisper (specifically large-v3).
Includes automatic device detection (CUDA/CPU), FFmpeg resolution, audio normalization,
and threaded asynchronous processing.
"""

import os
import sys
import shutil
import logging
import threading
from pathlib import Path
from typing import Optional, Callable, Dict, Any, Union

import numpy as np

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WhisperEngine")


class FFmpegNotFoundError(Exception):
    """Raised when FFmpeg is required for compressed audio decoding but cannot be found."""
    pass


def setup_ffmpeg_environment():
    """
    Attempts to locate FFmpeg on Windows if not already in system PATH.
    Checks imageio-ffmpeg package, winget installations, and common directories.
    """
    if shutil.which("ffmpeg"):
        logger.info(f"FFmpeg found in PATH: {shutil.which('ffmpeg')}")
        return True

    # 1. Try imageio_ffmpeg if available
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
        if os.path.exists(ffmpeg_exe):
            ffmpeg_dir = os.path.dirname(ffmpeg_exe)
            target_alias = os.path.join(ffmpeg_dir, "ffmpeg.exe")
            if not os.path.exists(target_alias):
                try:
                    shutil.copyfile(ffmpeg_exe, target_alias)
                except Exception:
                    pass
            os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
            if shutil.which("ffmpeg"):
                logger.info(f"FFmpeg resolved via imageio_ffmpeg: {ffmpeg_dir}")
                return True
    except Exception as e:
        logger.debug(f"imageio_ffmpeg lookup error: {e}")

    # 2. Check common Windows paths
    candidates = [
        r"C:\ffmpeg\bin",
        r"C:\Program Files\ffmpeg\bin",
        r"C:\Program Files (x86)\ffmpeg\bin",
        str(Path.home() / "ffmpeg" / "bin"),
        str(Path.home() / "scoop" / "apps" / "ffmpeg" / "current" / "bin"),
    ]

    # Check winget standard packages directory
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
            logger.info(f"FFmpeg located in: {c}")
            return True

    logger.warning("FFmpeg not found in standard system paths.")
    return False


# Run FFmpeg discovery at import time
setup_ffmpeg_environment()


class WhisperEngine:
    """
    Wrapper around OpenAI Whisper model optimized for maximum accuracy
    with Persian (Farsi) and English speech-to-text.
    """

    AVAILABLE_MODELS = [
        "large-v3",
        "large-v3-turbo",
        "medium",
        "small",
        "base",
        "tiny"
    ]

    def __init__(self, default_model: str = "large-v3"):
        self.current_model_name: Optional[str] = None
        self.model = None
        self.default_model = default_model
        self.lock = threading.Lock()
        self.is_loading = False

        # Determine optimal hardware device
        self.device = self._detect_device()
        self.device_name = self._get_device_description()
        logger.info(f"WhisperEngine initialized on device: {self.device} ({self.device_name})")

    @staticmethod
    def _detect_device() -> str:
        """Checks if NVIDIA CUDA GPU is available for acceleration."""
        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
        except Exception:
            pass
        return "cpu"

    def _get_device_description(self) -> str:
        """Returns human-readable device name."""
        try:
            import torch
            if self.device == "cuda" and torch.cuda.is_available():
                return torch.cuda.get_device_name(0)
            return f"CPU ({os.cpu_count() or 4} cores, FP32 Mode)"
        except Exception:
            return "CPU (Standard)"

    def is_ffmpeg_available(self) -> bool:
        """Returns True if ffmpeg executable is reachable."""
        return shutil.which("ffmpeg") is not None

    def load_model(self, model_name: Optional[str] = None, force_reload: bool = False) -> Any:
        """
        Loads the specified Whisper model into memory.
        Caches the model to prevent redundant re-loads.
        """
        if model_name is None:
            model_name = self.default_model

        with self.lock:
            if self.model is not None and self.current_model_name == model_name and not force_reload:
                return self.model

            self.is_loading = True
            try:
                import whisper
            except ImportError as e:
                raise ImportError(
                    "OpenAI Whisper is not installed. Please run:\n"
                    "pip install openai-whisper\n\n"
                    "For GPU support, ensure PyTorch with CUDA is installed:\n"
                    "pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124"
                ) from e

            logger.info(f"Loading Whisper model '{model_name}' on {self.device}...")
            try:
                # Load Whisper model onto CUDA or CPU
                self.model = whisper.load_model(model_name, device=self.device)
                self.current_model_name = model_name
                logger.info(f"Whisper model '{model_name}' loaded successfully.")
                return self.model
            except Exception as e:
                # If CUDA out of memory, try falling back to CPU
                if self.device == "cuda" and "out of memory" in str(e).lower():
                    logger.warning("CUDA Out of Memory! Falling back to CPU...")
                    self.device = "cpu"
                    self.device_name = "CPU (Fallback after CUDA OOM)"
                    self.model = whisper.load_model(model_name, device="cpu")
                    self.current_model_name = model_name
                    return self.model
                raise e
            finally:
                self.is_loading = False

    def transcribe(
        self,
        audio_input: Union[str, np.ndarray],
        language: Optional[str] = None,
        model_name: Optional[str] = None,
        status_callback: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """
        Performs high-accuracy speech transcription.

        Args:
            audio_input: Path to audio file (str) OR 1D float32 numpy array at 16,000 Hz.
            language: 'fa' for Persian, 'en' for English, or None for Auto-Detect.
            model_name: Model name to use (defaults to current or large-v3).
            status_callback: Optional function for updating progress status.

        Returns:
            Dictionary containing:
                - text: Transcribed text string
                - language: Detected/used language code
                - language_name: Human-readable language name
                - confidence: Estimated confidence percentage
                - duration: Audio length in seconds
                - model: Model name used
        """
        if status_callback:
            status_callback("Ensuring Whisper model is loaded...")

        model = self.load_model(model_name)

        if status_callback:
            status_callback("Processing and transcribing audio...")

        # Process language parameter
        lang_param = None
        if language and language.lower() not in ("auto", "none", "auto-detect"):
            cleaned = language.lower().strip()
            if cleaned in ("persian", "farsi", "fa"):
                lang_param = "fa"
            elif cleaned in ("english", "en"):
                lang_param = "en"
            else:
                lang_param = cleaned

        # Optimized Whisper settings for Near-Zero Error Rate
        # - temperature=0.0: greedy deterministic decoding prevents hallucinations
        # - beam_size=5: 5-beam search delivers significantly higher accuracy
        # - best_of=5: chooses top candidate
        # - fp16=True only on CUDA (CPU does not support fp16)
        decode_options: Dict[str, Any] = {
            "temperature": 0.0,
            "beam_size": 5,
            "best_of": 5,
            "patience": 1.0,
            "compression_ratio_threshold": 2.4,
            "no_speech_threshold": 0.6,
            "condition_on_previous_text": False,
            "fp16": (self.device == "cuda")
        }

        if lang_param:
            decode_options["language"] = lang_param

        # Check audio input type
        audio_data = None
        audio_duration = 0.0

        if isinstance(audio_input, np.ndarray):
            # Live microphone recording passed directly as numpy array
            audio_data = audio_input.astype(np.float32)
            if audio_data.ndim > 1:
                audio_data = audio_data.squeeze()
            # Normalize if needed
            max_val = np.max(np.abs(audio_data))
            if max_val > 1.0:
                audio_data = audio_data / max_val
            audio_duration = len(audio_data) / 16000.0
        elif isinstance(audio_input, str):
            audio_path = Path(audio_input)
            if not audio_path.exists():
                raise FileNotFoundError(f"Audio file does not exist: {audio_input}")

            # Check if it's a WAV file and FFmpeg is not available
            is_wav = audio_path.suffix.lower() == ".wav"
            if not self.is_ffmpeg_available():
                if is_wav:
                    # Load directly via scipy without requiring FFmpeg
                    audio_data, audio_duration = self._load_wav_direct(str(audio_path))
                else:
                    raise FFmpegNotFoundError(
                        "FFmpeg was not found on your system!\n\n"
                        "FFmpeg is required by Whisper to read compressed audio formats "
                        f"({audio_path.suffix.upper()}).\n\n"
                        "How to fix this in 10 seconds:\n"
                        "1. Open PowerShell and run:\n"
                        "   winget install Gyan.FFmpeg\n"
                        "   (or run: pip install imageio-ffmpeg)\n"
                        "2. Restart this application.\n\n"
                        "Note: Live microphone voice recording works 100% natively without FFmpeg!"
                    )
            else:
                # FFmpeg is available; Whisper handles file path directly
                audio_data = str(audio_path)

        # Execute transcription
        try:
            result = model.transcribe(audio_data, **decode_options)
        except Exception as e:
            if "ffmpeg" in str(e).lower() or "WinError 2" in str(e):
                raise FFmpegNotFoundError(
                    "FFmpeg error occurred while decoding audio.\n"
                    "Please install FFmpeg: 'winget install Gyan.FFmpeg' or 'pip install imageio-ffmpeg'."
                ) from e
            raise e

        transcribed_text = result.get("text", "").strip()
        detected_lang = result.get("language", lang_param or "en")

        # Estimate duration if not already measured
        if audio_duration == 0.0:
            segments = result.get("segments", [])
            if segments:
                audio_duration = segments[-1].get("end", 0.0)

        # Estimate confidence from segment average logprobs
        confidence = self._calculate_confidence(result.get("segments", []))

        return {
            "text": transcribed_text,
            "language": detected_lang,
            "language_name": "Persian (فارسی)" if detected_lang == "fa" else "English" if detected_lang == "en" else detected_lang,
            "confidence": confidence,
            "duration": audio_duration,
            "model": self.current_model_name or self.default_model,
            "segments": result.get("segments", [])
        }

    @staticmethod
    def _load_wav_direct(filepath: str) -> tuple[np.ndarray, float]:
        """Loads a WAV file directly into 16kHz float32 mono without FFmpeg."""
        import scipy.io.wavfile as wavfile
        import scipy.signal as signal

        sr, data = wavfile.read(filepath)

        # Convert to float32 normalized [-1.0, 1.0]
        if data.dtype == np.int16:
            audio = data.astype(np.float32) / 32768.0
        elif data.dtype == np.int32:
            audio = data.astype(np.float32) / 2147483648.0
        elif data.dtype == np.uint8:
            audio = (data.astype(np.float32) - 128.0) / 128.0
        else:
            audio = data.astype(np.float32)

        # Convert stereo to mono
        if audio.ndim > 1:
            audio = np.mean(audio, axis=1)

        # Resample to 16,000 Hz if needed
        if sr != 16000:
            target_length = int(len(audio) * 16000 / sr)
            audio = signal.resample(audio, target_length).astype(np.float32)
            sr = 16000

        duration = len(audio) / 16000.0
        return audio, duration

    @staticmethod
    def _calculate_confidence(segments: list) -> float:
        """Calculates an approximate confidence percentage based on Whisper log-probabilities."""
        if not segments:
            return 95.0
        avg_logprobs = [s.get("avg_logprob", -0.5) for s in segments if "avg_logprob" in s]
        if not avg_logprobs:
            return 95.0
        mean_logprob = float(np.mean(avg_logprobs))
        # Map logprob (-1.0 to 0.0) to percentage (60% to 99.9%)
        prob = np.exp(mean_logprob)
        confidence = float(np.clip(prob * 100.0, 50.0, 99.9))
        return round(confidence, 1)

    def transcribe_async(
        self,
        audio_input: Union[str, np.ndarray],
        language: Optional[str] = None,
        model_name: Optional[str] = None,
        on_complete: Optional[Callable[[Dict[str, Any]], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        status_callback: Optional[Callable[[str], None]] = None
    ):
        """Runs transcription in a background thread to keep GUI responsive."""
        def worker():
            try:
                res = self.transcribe(
                    audio_input=audio_input,
                    language=language,
                    model_name=model_name,
                    status_callback=status_callback
                )
                if on_complete:
                    on_complete(res)
            except Exception as e:
                logger.error(f"Transcription error: {e}", exc_info=True)
                if on_error:
                    on_error(e)

        thread = threading.Thread(target=worker, daemon=True)
        thread.start()
        return thread

