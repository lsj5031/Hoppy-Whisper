"""Audio capture exception types."""

from __future__ import annotations


class AudioDeviceError(Exception):
    """Raised when an audio device is missing or unavailable."""


class AudioCaptureError(Exception):
    """Raised when audio capture fails during recording."""
