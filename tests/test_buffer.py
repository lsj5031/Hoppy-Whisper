"""Tests for audio buffer utilities."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from app.audio import (
    TempWavFile,
    audio_buffer_to_pcm16_bytes,
    float32_to_pcm16,
    save_audio_buffer,
    write_wav,
)


def test_float32_to_pcm16_conversion():
    """Test conversion from float32 to int16 PCM."""
    float32_audio = np.array([-1.0, -0.5, 0.0, 0.5, 1.0], dtype=np.float32)
    pcm16 = float32_to_pcm16(float32_audio)

    assert pcm16.dtype == np.int16
    assert pcm16[0] == -32767
    assert pcm16[2] == 0
    assert pcm16[4] == 32767


def test_write_wav_with_float32_audio(tmp_path: Path):
    """Test writing float32 audio to WAV file."""
    output_path = tmp_path / "test_float32.wav"

    sample_rate = 16000
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), dtype=np.float32)
    audio = np.sin(2 * np.pi * 440 * t).astype(np.float32) * 0.5

    write_wav(output_path, audio, sample_rate, channels=1)

    assert output_path.exists()

    with wave.open(str(output_path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == sample_rate


def test_temp_wav_file_context_manager_with_cleanup():
    """Test TempWavFile context manager with cleanup enabled."""
    sample_rate = 16000
    audio = np.random.randn(16000).astype(np.float32) * 0.5

    file_path = None
    with TempWavFile(audio, sample_rate, cleanup=True) as wav_path:
        file_path = wav_path
        assert file_path.exists()

    assert file_path is not None
    assert not file_path.exists()


def test_save_audio_buffer(tmp_path: Path):
    """Test save_audio_buffer utility function."""
    output_path = tmp_path / "saved_audio.wav"
    sample_rate = 16000
    audio = np.random.randn(16000).astype(np.float32) * 0.5

    result_path = save_audio_buffer(audio, output_path, sample_rate)

    assert result_path == output_path
    assert output_path.exists()


def test_audio_buffer_to_pcm16_bytes_with_float32():
    """Test converting float32 buffer to PCM16 bytes."""
    audio = np.array([-1.0, 0.0, 1.0], dtype=np.float32)
    pcm_bytes = audio_buffer_to_pcm16_bytes(audio)

    assert isinstance(pcm_bytes, bytes)
    assert len(pcm_bytes) == len(audio) * 2

    pcm16 = np.frombuffer(pcm_bytes, dtype=np.int16)
    assert pcm16[0] == -32767
    assert pcm16[1] == 0
    assert pcm16[2] == 32767
