"""Audio buffer utilities for WAV file writing and PCM16 conversion."""

from __future__ import annotations

import logging
import os
import tempfile
import wave
from pathlib import Path
from typing import Optional

import numpy as np

LOGGER = logging.getLogger(__name__)


def float32_to_pcm16(audio: np.ndarray) -> np.ndarray:
    """
    Convert float32 audio [-1.0, 1.0] to int16 PCM [-32768, 32767].

    Args:
        audio: Float32 audio array

    Returns:
        Int16 PCM array
    """
    clipped = np.clip(audio, -1.0, 1.0)
    return (clipped * 32767.0).astype(np.int16)


def pcm16_to_bytes(pcm16: np.ndarray) -> bytes:
    """
    Convert int16 PCM array to bytes.

    Args:
        pcm16: Int16 PCM audio array

    Returns:
        Raw PCM bytes
    """
    return pcm16.tobytes()


def write_wav(
    file_path: Path | str,
    audio: np.ndarray,
    sample_rate: int,
    channels: int = 1,
) -> None:
    """
    Write float32 or int16 audio to a WAV file.

    Args:
        file_path: Output WAV file path
        audio: Audio data as numpy array (float32 or int16)
        sample_rate: Audio sample rate in Hz
        channels: Number of audio channels (default: 1 for mono)
    """
    file_path = Path(file_path)

    # Convert to int16 if needed
    if audio.dtype == np.float32 or audio.dtype == np.float64:
        audio_int16 = float32_to_pcm16(audio)
    elif audio.dtype == np.int16:
        audio_int16 = audio
    else:
        raise ValueError(f"Unsupported audio dtype: {audio.dtype}")

    # Ensure correct shape for wave module
    if audio_int16.ndim == 1:
        audio_int16 = audio_int16.reshape(-1, 1)
    elif audio_int16.ndim == 2 and audio_int16.shape[1] != channels:
        raise ValueError(
            f"Audio has {audio_int16.shape[1]} channels, expected {channels}"
        )

    try:
        with wave.open(str(file_path), "wb") as wav_file:
            wav_file.setnchannels(channels)
            wav_file.setsampwidth(2)  # 2 bytes for int16
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        LOGGER.debug(
            "Wrote WAV file: %s (%d samples, %d Hz)", file_path, len(audio), sample_rate
        )
    except Exception as exc:
        LOGGER.error("Failed to write WAV file %s: %s", file_path, exc)
        raise


class TempWavFile:
    """
    Context manager for temporary WAV files with automatic cleanup.

    Example:
        with TempWavFile(audio, sample_rate, cleanup=True) as wav_path:
            # Use wav_path
            pass
        # File automatically deleted if cleanup=True
    """

    def __init__(
        self,
        audio: np.ndarray,
        sample_rate: int,
        channels: int = 1,
        cleanup: bool = True,
        prefix: str = "parakeet_",
        suffix: str = ".wav",
    ) -> None:
        """
        Initialize temp WAV file.

        Args:
            audio: Audio data as numpy array
            sample_rate: Audio sample rate in Hz
            channels: Number of audio channels
            cleanup: If True, delete file on context exit
            prefix: Temp file name prefix
            suffix: Temp file name suffix
        """
        self._audio = audio
        self._sample_rate = sample_rate
        self._channels = channels
        self._cleanup = cleanup
        self._prefix = prefix
        self._suffix = suffix
        self._file_path: Optional[Path] = None
        self._fd: Optional[int] = None

    def __enter__(self) -> Path:
        """Create and write the temporary WAV file."""
        # Create temp file with a file descriptor to prevent race conditions
        self._fd, temp_path = tempfile.mkstemp(
            prefix=self._prefix, suffix=self._suffix
        )

        try:
            self._file_path = Path(temp_path)
            write_wav(self._file_path, self._audio, self._sample_rate, self._channels)
            LOGGER.debug("Created temp WAV: %s", self._file_path)
            return self._file_path
        except Exception:
            # Clean up on error
            if self._fd is not None:
                os.close(self._fd)
                self._fd = None
            if self._file_path and self._file_path.exists():
                self._file_path.unlink()
            raise

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up temporary file if requested."""
        # Close file descriptor
        if self._fd is not None:
            try:
                os.close(self._fd)
            except Exception as exc:  # pragma: no cover
                LOGGER.debug("Error closing temp file descriptor: %s", exc)
            finally:
                self._fd = None

        # Delete file if cleanup requested
        if self._cleanup and self._file_path:
            try:
                if self._file_path.exists():
                    self._file_path.unlink()
                    LOGGER.debug("Deleted temp WAV: %s", self._file_path)
            except Exception as exc:  # pragma: no cover
                LOGGER.warning("Failed to delete temp WAV %s: %s", self._file_path, exc)


def save_audio_buffer(
    audio: np.ndarray,
    output_path: Path | str,
    sample_rate: int = 16000,
    channels: int = 1,
) -> Path:
    """
    Save audio buffer to WAV file.

    Args:
        audio: Audio data as numpy array
        output_path: Output file path
        sample_rate: Audio sample rate in Hz
        channels: Number of audio channels

    Returns:
        Path to the written file
    """
    output_path = Path(output_path)
    write_wav(output_path, audio, sample_rate, channels)
    return output_path


def audio_buffer_to_pcm16_bytes(audio: np.ndarray) -> bytes:
    """
    Convert audio buffer to PCM16 bytes for inference.

    Args:
        audio: Float32 or int16 audio array

    Returns:
        PCM16 bytes
    """
    if audio.dtype == np.float32 or audio.dtype == np.float64:
        pcm16 = float32_to_pcm16(audio)
    elif audio.dtype == np.int16:
        pcm16 = audio
    else:
        raise ValueError(f"Unsupported audio dtype: {audio.dtype}")

    return pcm16_to_bytes(pcm16)
