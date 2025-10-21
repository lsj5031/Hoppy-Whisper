"""Voice Activity Detection using WebRTC VAD."""

from __future__ import annotations

import logging

import numpy as np
import webrtcvad

LOGGER = logging.getLogger(__name__)


class VoiceActivityDetector:
    """
    Detects voice activity in audio frames using WebRTC VAD.

    Supports auto-stop on trailing silence with configurable duration.
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        frame_duration_ms: int = 30,
        aggressiveness: int = 2,
        trailing_silence_ms: int = 700,
    ) -> None:
        """
        Initialize VAD with specified parameters.

        Args:
            sample_rate: Audio sample rate (8000, 16000, 32000, or 48000 Hz)
            frame_duration_ms: Frame duration in ms (10, 20, or 30)
            aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)
            trailing_silence_ms: Duration of silence to trigger auto-stop
        """
        if sample_rate not in (8000, 16000, 32000, 48000):
            raise ValueError(
                f"Sample rate must be 8000, 16000, 32000, or 48000 Hz, "
                f"got {sample_rate}"
            )

        if frame_duration_ms not in (10, 20, 30):
            raise ValueError(
                f"Frame duration must be 10, 20, or 30 ms, got {frame_duration_ms}"
            )

        if not 0 <= aggressiveness <= 3:
            raise ValueError(f"Aggressiveness must be 0-3, got {aggressiveness}")

        self._sample_rate = sample_rate
        self._frame_duration_ms = frame_duration_ms
        self._aggressiveness = aggressiveness
        self._trailing_silence_ms = trailing_silence_ms

        self._frame_size = (sample_rate * frame_duration_ms) // 1000
        self._vad = webrtcvad.Vad(aggressiveness)

        self._silence_frames = 0
        self._silence_threshold = trailing_silence_ms // frame_duration_ms
        self._has_speech = False

        LOGGER.debug(
            "VAD initialized: %d Hz, %d ms frames, aggressiveness=%d, "
            "silence threshold=%d frames (%.1f ms)",
            sample_rate,
            frame_duration_ms,
            aggressiveness,
            self._silence_threshold,
            trailing_silence_ms,
        )

    @property
    def frame_size(self) -> int:
        """Return the required frame size in samples."""
        return self._frame_size

    @property
    def frame_duration_ms(self) -> int:
        """Return the frame duration in milliseconds."""
        return self._frame_duration_ms

    def reset(self) -> None:
        """Reset VAD state for a new recording session."""
        self._silence_frames = 0
        self._has_speech = False
        LOGGER.debug("VAD state reset")

    def process_frame(self, frame: np.ndarray) -> tuple[bool, bool]:
        """
        Process a single audio frame and detect voice activity.

        Args:
            frame: Audio frame as float32 numpy array,
                shape (frame_size,) or (frame_size, 1)

        Returns:
            Tuple of (is_speech, should_stop):
                - is_speech: True if speech detected in this frame
                - should_stop: True if trailing silence threshold exceeded
        """
        if frame.ndim == 2:
            frame = frame.flatten()

        if len(frame) != self._frame_size:
            raise ValueError(
                f"Frame size mismatch: expected {self._frame_size}, got {len(frame)}"
            )

        # Convert float32 to int16 PCM for WebRTC VAD
        pcm16 = self._float32_to_pcm16(frame)

        # Detect voice activity
        is_speech = self._vad.is_speech(pcm16.tobytes(), self._sample_rate)

        # Update speech detection state
        if is_speech:
            self._has_speech = True
            self._silence_frames = 0
        else:
            self._silence_frames += 1

        # Should stop if we've seen speech and now have trailing silence
        should_stop = (
            self._has_speech and self._silence_frames >= self._silence_threshold
        )

        return is_speech, should_stop

    def process_buffer(self, buffer: np.ndarray, min_speech_frames: int = 3) -> bool:
        """
        Process entire audio buffer and determine if it contains speech.

        Args:
            buffer: Audio buffer as float32 numpy array
            min_speech_frames: Minimum number of speech frames to consider valid

        Returns:
            True if buffer contains sufficient speech
        """
        if buffer.ndim == 2:
            buffer = buffer.flatten()

        # Process buffer in frames
        speech_count = 0
        total_frames = 0

        for i in range(0, len(buffer), self._frame_size):
            frame = buffer[i : i + self._frame_size]

            # Skip incomplete frames at the end
            if len(frame) < self._frame_size:
                break

            pcm16 = self._float32_to_pcm16(frame)
            is_speech = self._vad.is_speech(pcm16.tobytes(), self._sample_rate)

            if is_speech:
                speech_count += 1
            total_frames += 1

        has_speech = speech_count >= min_speech_frames

        LOGGER.debug(
            "Buffer VAD: %d/%d speech frames (%.1f%%), has_speech=%s",
            speech_count,
            total_frames,
            100.0 * speech_count / max(total_frames, 1),
            has_speech,
        )

        return has_speech

    @staticmethod
    def _float32_to_pcm16(audio: np.ndarray) -> np.ndarray:
        """
        Convert float32 audio [-1.0, 1.0] to int16 PCM [-32768, 32767].

        Args:
            audio: Float32 audio array

        Returns:
            Int16 PCM array
        """
        # Clip to valid range and scale to int16
        clipped = np.clip(audio, -1.0, 1.0)
        return (clipped * 32767.0).astype(np.int16)


def create_vad(
    sample_rate: int = 16000,
    aggressiveness: int = 2,
    trailing_silence_ms: int = 700,
) -> VoiceActivityDetector:
    """
    Create a VAD instance with sensible defaults.

    Args:
        sample_rate: Audio sample rate (8000, 16000, 32000, or 48000 Hz)
        aggressiveness: VAD aggressiveness (0-3, higher = more aggressive)
        trailing_silence_ms: Duration of silence to trigger auto-stop

    Returns:
        Configured VoiceActivityDetector instance
    """
    return VoiceActivityDetector(
        sample_rate=sample_rate,
        frame_duration_ms=30,
        aggressiveness=aggressiveness,
        trailing_silence_ms=trailing_silence_ms,
    )
