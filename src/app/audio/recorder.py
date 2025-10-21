"""WASAPI audio recorder for 16 kHz mono capture."""

from __future__ import annotations

import logging
import threading
import time
from typing import Optional

import numpy as np
import sounddevice as sd

from .exceptions import AudioCaptureError, AudioDeviceError

LOGGER = logging.getLogger(__name__)

SAMPLE_RATE = 16000
CHANNELS = 1
DTYPE = np.float32
BLOCKSIZE = 512  # ~32 ms per callback at 16 kHz


class AudioRecorder:
    """Records audio from the default input device at 16 kHz mono."""

    def __init__(
        self,
        sample_rate: int = SAMPLE_RATE,
        channels: int = CHANNELS,
        dtype: type = DTYPE,
        blocksize: int = BLOCKSIZE,
    ) -> None:
        self._sample_rate = sample_rate
        self._channels = channels
        self._dtype = dtype
        self._blocksize = blocksize
        self._stream: Optional[sd.InputStream] = None
        self._buffer: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._recording = False
        self._start_time: Optional[float] = None

    @property
    def sample_rate(self) -> int:
        """Return the configured sample rate."""
        return self._sample_rate

    @property
    def channels(self) -> int:
        """Return the configured channel count."""
        return self._channels

    @property
    def is_recording(self) -> bool:
        """Check if recording is currently active."""
        return self._recording

    def start(self) -> None:
        """Start capturing audio from the default input device."""
        if self._recording:
            LOGGER.warning("Recorder already started, ignoring start request")
            return

        try:
            self._verify_device_available()
        except AudioDeviceError:
            raise

        with self._lock:
            self._buffer.clear()
            self._recording = True
            self._start_time = time.monotonic()

        try:
            self._stream = sd.InputStream(
                samplerate=self._sample_rate,
                channels=self._channels,
                dtype=self._dtype,
                blocksize=self._blocksize,
                callback=self._audio_callback,
                latency="low",
            )
            self._stream.start()
            LOGGER.debug(
                "Started audio capture: %d Hz, %d channel(s)",
                self._sample_rate,
                self._channels,
            )
        except Exception as exc:
            self._recording = False
            self._start_time = None
            raise AudioCaptureError(f"Failed to start audio stream: {exc}") from exc

    def stop(self) -> np.ndarray:
        """
        Stop capturing and return the accumulated audio buffer.

        Returns:
            numpy array of shape (samples, channels) with float32 audio data.
        """
        if not self._recording:
            LOGGER.warning("Recorder not started, returning empty buffer")
            return np.array([], dtype=self._dtype).reshape(0, self._channels)

        self._recording = False

        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as exc:  # pragma: no cover
                LOGGER.debug("Error closing stream: %s", exc)
            finally:
                self._stream = None

        with self._lock:
            result: np.ndarray
            if not self._buffer:
                result = np.array([], dtype=self._dtype).reshape(0, self._channels)
            else:
                result = np.concatenate(self._buffer, axis=0)
            self._buffer.clear()

        if self._start_time is not None:
            elapsed = time.monotonic() - self._start_time
            latency = (time.monotonic() - self._start_time - elapsed) * 1000
            LOGGER.debug(
                "Stopped audio capture: %.2f s recorded, buffer latency ~%.1f ms",
                elapsed,
                latency,
            )
            self._start_time = None

        return result

    def get_buffer_duration(self) -> float:
        """
        Return the current buffer duration in seconds.

        Returns:
            float: Duration in seconds of captured audio.
        """
        with self._lock:
            if not self._buffer:
                return 0.0
            total_samples = sum(chunk.shape[0] for chunk in self._buffer)
            return total_samples / self._sample_rate

    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: object,
        status: sd.CallbackFlags,
    ) -> None:
        """
        Callback invoked by sounddevice for each audio block.

        This runs in a separate thread managed by PortAudio.
        """
        if status:
            LOGGER.warning("Audio callback status: %s", status)

        if not self._recording:
            return

        with self._lock:
            # Copy to prevent data corruption when sounddevice reuses buffers
            self._buffer.append(indata.copy())

    def _verify_device_available(self) -> None:
        """
        Check that an input device is available.

        Raises:
            AudioDeviceError: If no input device is found or default is invalid.
        """
        try:
            _devices = sd.query_devices()  # noqa: F841
            default_input = sd.default.device[0]

            if default_input is None or default_input < 0:
                raise AudioDeviceError(
                    "No default input device configured. Please connect a microphone."
                )

            device_info = sd.query_devices(default_input, kind="input")

            if device_info["max_input_channels"] < self._channels:
                raise AudioDeviceError(
                    f"Input device has {device_info['max_input_channels']} channels, "
                    f"but {self._channels} required."
                )

            LOGGER.debug(
                "Using input device: %s (%d channels max)",
                device_info["name"],
                device_info["max_input_channels"],
            )

        except Exception as exc:
            raise AudioDeviceError(f"Audio device check failed: {exc}") from exc


def list_audio_devices() -> list[dict]:
    """
    Return a list of available audio input devices.

    Returns:
        List of device info dictionaries with keys: name, index, channels.
    """
    try:
        devices = sd.query_devices()
        return [
            {
                "name": dev["name"],
                "index": idx,
                "channels": dev["max_input_channels"],
            }
            for idx, dev in enumerate(devices)
            if dev["max_input_channels"] > 0
        ]
    except Exception as exc:  # pragma: no cover
        LOGGER.debug("Failed to enumerate devices: %s", exc)
        return []
