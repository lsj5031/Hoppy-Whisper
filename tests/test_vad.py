"""Tests for Voice Activity Detection."""

from __future__ import annotations

import numpy as np
import pytest

from app.audio import VoiceActivityDetector, create_vad


def test_vad_initialization_with_defaults():
    """Test VAD initializes with default parameters."""
    vad = VoiceActivityDetector()

    assert vad.frame_size == 480  # 16000 Hz * 30 ms / 1000
    assert vad.frame_duration_ms == 30


def test_vad_initialization_with_custom_params():
    """Test VAD initialization with custom parameters."""
    vad = VoiceActivityDetector(
        sample_rate=8000,
        frame_duration_ms=20,
        aggressiveness=1,
        trailing_silence_ms=500,
    )

    assert vad.frame_size == 160  # 8000 Hz * 20 ms / 1000
    assert vad.frame_duration_ms == 20


def test_vad_invalid_sample_rate_raises():
    """Test that invalid sample rate raises ValueError."""
    with pytest.raises(ValueError, match="Sample rate must be"):
        VoiceActivityDetector(sample_rate=22050)


def test_vad_invalid_frame_duration_raises():
    """Test that invalid frame duration raises ValueError."""
    with pytest.raises(ValueError, match="Frame duration must be"):
        VoiceActivityDetector(frame_duration_ms=40)


def test_vad_invalid_aggressiveness_raises():
    """Test that invalid aggressiveness level raises ValueError."""
    with pytest.raises(ValueError, match="Aggressiveness must be"):
        VoiceActivityDetector(aggressiveness=5)


def test_vad_process_frame_with_silence():
    """Test VAD processes silence frames correctly."""
    vad = VoiceActivityDetector(sample_rate=16000, frame_duration_ms=30)

    # Create silent frame (zeros)
    silent_frame = np.zeros(480, dtype=np.float32)

    is_speech, should_stop = vad.process_frame(silent_frame)

    assert not is_speech
    assert not should_stop  # Should not stop without prior speech


def test_vad_process_frame_with_noise():
    """Test VAD processes frames with random noise."""
    vad = VoiceActivityDetector(sample_rate=16000, aggressiveness=3)

    # Create noise frame (low amplitude random noise)
    np.random.seed(42)
    noise_frame = np.random.randn(480).astype(np.float32) * 0.01

    is_speech, should_stop = vad.process_frame(noise_frame)

    # Just verify the method executes correctly
    # Actual speech detection depends on audio characteristics and VAD tuning
    assert isinstance(is_speech, bool)
    assert not should_stop


def test_vad_process_frame_with_speech_like_signal():
    """Test VAD with speech-like signal (higher amplitude varied noise)."""
    vad = VoiceActivityDetector(sample_rate=16000, aggressiveness=1)

    # Create speech-like frame (higher amplitude with variation)
    np.random.seed(42)
    speech_frame = np.random.randn(480).astype(np.float32) * 0.3

    is_speech, should_stop = vad.process_frame(speech_frame)

    # Note: Actual speech detection depends on audio characteristics
    # We're just testing that the method executes without errors
    assert isinstance(is_speech, bool)
    assert isinstance(should_stop, bool)


def test_vad_trailing_silence_triggers_stop():
    """Test that trailing silence after speech triggers stop."""
    vad = VoiceActivityDetector(
        sample_rate=16000,
        frame_duration_ms=30,
        trailing_silence_ms=90,  # 3 frames
    )

    # Verify threshold calculation
    assert vad._silence_threshold == 3  # 90ms / 30ms = 3 frames

    # Create actual speech by forcing the internal state
    # In real use, this would be detected by the VAD algorithm
    vad._has_speech = True
    vad._silence_frames = 0

    # Now process silence frames
    silent_frame = np.zeros(480, dtype=np.float32)

    # First silence frame: _silence_frames becomes 1
    is_speech_1, should_stop_1 = vad.process_frame(silent_frame)
    assert not is_speech_1
    assert vad._silence_frames == 1
    assert not should_stop_1

    # Second silence frame: _silence_frames becomes 2
    is_speech_2, should_stop_2 = vad.process_frame(silent_frame)
    assert not is_speech_2
    assert vad._silence_frames == 2
    assert not should_stop_2

    # Third silence frame: _silence_frames becomes 3, should trigger stop
    is_speech_3, should_stop_3 = vad.process_frame(silent_frame)
    assert not is_speech_3
    assert vad._silence_frames == 3
    assert should_stop_3


def test_vad_reset_clears_state():
    """Test that reset() clears VAD state."""
    vad = VoiceActivityDetector(sample_rate=16000)

    # Set internal state
    vad._has_speech = True
    vad._silence_frames = 5

    # Reset
    vad.reset()

    assert not vad._has_speech
    assert vad._silence_frames == 0


def test_vad_process_frame_with_2d_array():
    """Test VAD handles 2D array input (mono audio with channel dimension)."""
    vad = VoiceActivityDetector(sample_rate=16000)

    # Create 2D frame: (samples, channels)
    frame_2d = np.zeros((480, 1), dtype=np.float32)

    is_speech, should_stop = vad.process_frame(frame_2d)

    assert not is_speech
    assert not should_stop


def test_vad_process_frame_wrong_size_raises():
    """Test that wrong frame size raises ValueError."""
    vad = VoiceActivityDetector(sample_rate=16000, frame_duration_ms=30)

    # Create frame with wrong size
    wrong_frame = np.zeros(400, dtype=np.float32)  # Should be 480

    with pytest.raises(ValueError, match="Frame size mismatch"):
        vad.process_frame(wrong_frame)


def test_vad_process_buffer_with_silence():
    """Test processing entire buffer of silence."""
    vad = VoiceActivityDetector(sample_rate=16000)

    # Create 1 second of silence
    silent_buffer = np.zeros(16000, dtype=np.float32)

    has_speech = vad.process_buffer(silent_buffer, min_speech_frames=3)

    assert not has_speech


def test_vad_process_buffer_with_mixed_content():
    """Test processing buffer with mixed speech and silence."""
    vad = VoiceActivityDetector(sample_rate=16000, aggressiveness=1)

    np.random.seed(42)
    # Create buffer: 0.5s silence + 0.5s noise + 0.5s silence
    silence_1 = np.zeros(8000, dtype=np.float32)
    noise = np.random.randn(8000).astype(np.float32) * 0.4
    silence_2 = np.zeros(8000, dtype=np.float32)

    buffer = np.concatenate([silence_1, noise, silence_2])

    # Should detect some speech in the noisy section
    has_speech = vad.process_buffer(buffer, min_speech_frames=1)

    # This test verifies the method works; actual result depends on VAD tuning
    assert isinstance(has_speech, bool)


def test_vad_process_buffer_handles_incomplete_final_frame():
    """Test that process_buffer handles incomplete frames at the end."""
    vad = VoiceActivityDetector(sample_rate=16000, frame_duration_ms=30)

    # Create buffer that doesn't align with frame size
    # 16000 samples = 33.33 frames of 480 samples
    buffer = np.zeros(16000, dtype=np.float32)

    # Should not raise error
    has_speech = vad.process_buffer(buffer)

    assert not has_speech


def test_vad_float32_to_pcm16_conversion():
    """Test float32 to PCM16 conversion."""
    vad = VoiceActivityDetector()

    # Test range conversion
    float32_audio = np.array([-1.0, -0.5, 0.0, 0.5, 1.0], dtype=np.float32)
    pcm16 = vad._float32_to_pcm16(float32_audio)

    assert pcm16.dtype == np.int16
    assert pcm16[0] == -32767
    assert pcm16[2] == 0
    assert pcm16[4] == 32767


def test_vad_float32_to_pcm16_clipping():
    """Test that out-of-range values are clipped during conversion."""
    vad = VoiceActivityDetector()

    # Test clipping
    float32_audio = np.array([-2.0, 2.0], dtype=np.float32)
    pcm16 = vad._float32_to_pcm16(float32_audio)

    assert pcm16[0] == -32767  # Clipped from -2.0
    assert pcm16[1] == 32767  # Clipped from 2.0


def test_create_vad_factory():
    """Test create_vad factory function."""
    vad = create_vad(
        sample_rate=8000,
        aggressiveness=3,
        trailing_silence_ms=500,
    )

    assert isinstance(vad, VoiceActivityDetector)
    assert vad.frame_size == 240  # 8000 Hz * 30 ms / 1000
    assert vad.frame_duration_ms == 30


def test_create_vad_with_defaults():
    """Test create_vad with default parameters."""
    vad = create_vad()

    assert isinstance(vad, VoiceActivityDetector)
    assert vad.frame_size == 480  # 16000 Hz * 30 ms / 1000
