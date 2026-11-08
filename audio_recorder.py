"""
Live Audio Recorder Module
Provides high-fidelity 16kHz mono audio recording using sounddevice.
Includes real-time RMS audio volume measurement for waveform animation,
timer tracking, and WAV file export.
"""

import os
import time
import queue
import logging
import threading
from typing import Optional, Callable, Tuple

import numpy as np

logger = logging.getLogger("AudioRecorder")


class AudioRecorderError(Exception):
    """Base exception for audio recording errors."""
    pass


class AudioRecorder:
    """
    Manages live microphone capture, real-time volume analysis,
    and export to standard 16-bit 16kHz WAV format.
    """

    SAMPLE_RATE = 16000  # Native Whisper sample rate
    CHANNELS = 1         # Mono channel

    def __init__(self, volume_callback: Optional[Callable[[float], None]] = None):
        self.volume_callback = volume_callback
        self.is_recording = False
        self.start_time: Optional[float] = None
        self.audio_frames: list[np.ndarray] = []
        self.stream = None
        self.lock = threading.Lock()
        self.recent_rms: float = 0.0

    @staticmethod
    def is_sounddevice_available() -> bool:
        """Checks if sounddevice library is installed and available."""
        try:
            import sounddevice as sd
            return True
        except ImportError:
            return False

    @staticmethod
    def get_input_devices() -> list[dict]:
        """Returns a list of available microphone input devices."""
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            input_devs = [
                {"id": i, "name": d["name"], "default": (i == sd.default.device[0])}
                for i, d in enumerate(devices)
                if d.get("max_input_channels", 0) > 0
            ]
            return input_devs
        except Exception:
            return []

    def start_recording(self) -> None:
        """Starts live microphone audio stream in background."""
        if not self.is_sounddevice_available():
            raise AudioRecorderError(
                "Microphone recording library ('sounddevice') is not installed.\n\n"
                "To enable live recording, run:\n"
                "pip install sounddevice"
            )

        import sounddevice as sd

        with self.lock:
            if self.is_recording:
                return

            self.audio_frames.clear()
            self.recent_rms = 0.0

            def audio_callback(indata, frames, time_info, status):
                if status:
                    logger.debug(f"SoundDevice status warning: {status}")

                if not self.is_recording:
                    return

                # Flatten to 1D
                chunk = indata[:, 0].copy()
                self.audio_frames.append(chunk)

                # Compute RMS volume for live waveform visualizer
                rms = float(np.sqrt(np.mean(chunk**2)))
                # Normalize and apply non-linear boost for speech clarity
                boosted = min(1.0, rms * 5.5)
                self.recent_rms = 0.7 * self.recent_rms + 0.3 * boosted

                if self.volume_callback:
                    try:
                        self.volume_callback(self.recent_rms)
                    except Exception:
                        pass

            try:
                self.stream = sd.InputStream(
                    samplerate=self.SAMPLE_RATE,
                    channels=self.CHANNELS,
                    dtype="float32",
                    blocksize=1024,
                    callback=audio_callback
                )
                self.stream.start()
                self.is_recording = True
                self.start_time = time.time()
                logger.info("Microphone recording started.")
            except Exception as e:
                self.is_recording = False
                self.stream = None
                raise AudioRecorderError(
                    f"Could not open microphone:\n{str(e)}\n\n"
                    "Please verify that:\n"
                    "1. A microphone is connected and enabled.\n"
                    "2. Windows microphone permissions are granted for Python apps."
                ) from e

    def stop_recording(self, save_path: Optional[str] = None) -> Tuple[np.ndarray, Optional[str], float]:
        """
        Stops live recording, concatenates audio chunks, and exports to a WAV file.

        Args:
            save_path: Destination WAV file path (optional).

        Returns:
            Tuple of (audio_numpy_array, saved_file_path, duration_seconds)
        """
        with self.lock:
            if not self.is_recording:
                raise AudioRecorderError("Recorder is not active.")

            self.is_recording = False
            duration = time.time() - (self.start_time or time.time())

            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception as e:
                    logger.debug(f"Error closing stream: {e}")
                self.stream = None

            if not self.audio_frames:
                raise AudioRecorderError("No audio was recorded (recording was too brief).")

            # Concatenate all recorded chunks
            full_audio = np.concatenate(self.audio_frames, axis=0).astype(np.float32)

            # Prevent empty audio
            if len(full_audio) < 1600:  # Less than 0.1s
                raise AudioRecorderError("Recording too short. Please speak for at least 1 second.")

            # Save to standard 16-bit PCM WAV if destination path provided
            exported_path = None
            if save_path:
                try:
                    import scipy.io.wavfile as wavfile
                    # Clip to prevent distortion
                    clipped = np.clip(full_audio, -1.0, 1.0)
                    int16_audio = (clipped * 32767.0).astype(np.int16)
                    wavfile.write(save_path, self.SAMPLE_RATE, int16_audio)
                    exported_path = save_path
                    logger.info(f"Recorded audio saved to: {save_path}")
                except Exception as e:
                    logger.error(f"Failed to export WAV file: {e}")

            return full_audio, exported_path, duration

    def cancel_recording(self) -> None:
        """Cancels recording without saving and resets buffers."""
        with self.lock:
            self.is_recording = False
            if self.stream:
                try:
                    self.stream.stop()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
            self.audio_frames.clear()
            self.start_time = None
            logger.info("Recording cancelled.")

    def get_elapsed_seconds(self) -> float:
        """Returns elapsed time in seconds."""
        if not self.is_recording or self.start_time is None:
            return 0.0
        return max(0.0, time.time() - self.start_time)

    def get_elapsed_formatted(self) -> str:
        """Returns elapsed time formatted as MM:SS."""
        secs = int(self.get_elapsed_seconds())
        mins = secs // 60
        secs = secs % 60
        return f"{mins:02d}:{secs:02d}"

