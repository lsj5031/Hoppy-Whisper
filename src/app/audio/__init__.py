"""Audio capture and processing interfaces."""

from __future__ import annotations

import logging

from .buffer import (
    TempWavFile,
    audio_buffer_to_pcm16_bytes,
    float32_to_pcm16,
    save_audio_buffer,
    write_wav,
)
from .exceptions import AudioCaptureError, AudioDeviceError
from .recorder import AudioRecorder, list_audio_devices
from .vad import VoiceActivityDetector, create_vad

__all__ = [
    "AudioCaptureError",
    "AudioDeviceError",
    "AudioRecorder",
    "VoiceActivityDetector",
    "TempWavFile",
    "audio_buffer_to_pcm16_bytes",
    "create_vad",
    "float32_to_pcm16",
    "initialize_audio_pipeline",
    "list_audio_devices",
    "save_audio_buffer",
    "write_wav",
]

LOGGER = logging.getLogger(__name__)


def initialize_audio_pipeline() -> None:
    """
    Verify audio subsystem is available and log device information.

    Raises:
        AudioDeviceError: If no input devices are available.
    """
    devices = list_audio_devices()
    if not devices:
        raise AudioDeviceError("No audio input devices detected")

    LOGGER.info("Found %d audio input device(s)", len(devices))
    for device in devices:
        LOGGER.debug(
            "  [%d] %s (%d channels)",
            device["index"],
            device["name"],
            device["channels"],
        )
