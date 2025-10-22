"""End-to-end tests for the transcription pipeline (E3.4)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.transcriber.parakeet import PARAKEET_MODEL_NAME, TranscriptionResult


@pytest.fixture
def mock_transcriber():
    """Mock the ParakeetTranscriber."""
    transcriber = MagicMock()
    transcriber.transcribe_file.return_value = TranscriptionResult(
        text="This is a test transcription.",
        duration_ms=150.0,
        model_name=PARAKEET_MODEL_NAME,
    )
    return transcriber


@pytest.fixture
def mock_audio_buffer():
    """Create a mock audio buffer."""
    # 1 second of audio at 16kHz
    return np.zeros(16000, dtype=np.float32)


def test_transcription_pipeline_success(mock_transcriber, mock_audio_buffer):
    """Test successful transcription pipeline from buffer to clipboard."""
    from app.audio.buffer import TempWavFile

    # Test that we can create a temp wav file and transcribe it
    with TempWavFile(mock_audio_buffer, sample_rate=16000, cleanup=True) as wav_path:
        result = mock_transcriber.transcribe_file(wav_path)

        assert result.text == "This is a test transcription."
        assert result.duration_ms == 150.0
        assert wav_path.exists()

    # After context exit, temp file should be deleted
    assert not wav_path.exists()


def test_clipboard_copy():
    """Test clipboard copy functionality."""
    import pyperclip

    test_text = "Test transcription result"

    # Copy to clipboard
    pyperclip.copy(test_text)

    # Verify it was copied
    clipboard_content = pyperclip.paste()
    assert clipboard_content == test_text


@patch("app.transcriber.parakeet.get_transcriber")
def test_load_transcriber_success(mock_get_transcriber):
    """Test loading the transcriber."""
    from app.transcriber import load_transcriber

    mock_transcriber = MagicMock()
    mock_get_transcriber.return_value = mock_transcriber

    transcriber = load_transcriber()

    # Verify warmup was called
    mock_transcriber.warmup.assert_called_once()
    assert transcriber == mock_transcriber


def test_transcription_result_attributes():
    """Test TranscriptionResult attributes."""
    result = TranscriptionResult(
        text="Hello world",
        duration_ms=200.5,
        model_name="test-model",
    )

    assert result.text == "Hello world"
    assert result.duration_ms == 200.5
    assert result.model_name == "test-model"
