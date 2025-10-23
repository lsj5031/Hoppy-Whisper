"""Tests for Parakeet transcriber."""

from __future__ import annotations

import wave
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.transcriber.parakeet import (
    PARAKEET_MODEL_NAME,
    ParakeetTranscriber,
    TranscriptionResult,
)


@pytest.fixture
def mock_onnx_asr():
    """Mock the onnx_asr module."""
    mock_model = MagicMock()
    mock_model.recognize.return_value = "test transcription"

    mock_module = MagicMock()
    mock_module.load_model.return_value = mock_model

    with patch.dict("sys.modules", {"onnx_asr": mock_module}):
        yield mock_module


@pytest.fixture
def test_audio_file(tmp_path: Path) -> Path:
    """Create a test audio file."""
    audio_path = tmp_path / "test.wav"

    # Create a 1-second silent WAV file
    with wave.open(str(audio_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00" * 32000)

    return audio_path


def test_transcriber_init() -> None:
    """Test transcriber initialization."""
    transcriber = ParakeetTranscriber()
    assert transcriber._model is None
    assert not transcriber._warmed_up


def test_transcriber_init_with_providers() -> None:
    """Test transcriber initialization with custom providers."""
    providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
    provider_options = [{"device_id": 0}, {}]

    transcriber = ParakeetTranscriber(
        providers=providers, provider_options=provider_options
    )

    assert transcriber._providers == providers
    assert transcriber._provider_options == provider_options


def test_ensure_model_loaded_import_error() -> None:
    """Test model loading with missing onnx_asr."""
    # Remove onnx_asr from sys.modules if it exists
    import sys

    saved_module = sys.modules.pop("onnx_asr", None)

    try:
        with patch.dict("sys.modules", {"onnx_asr": None}):
            transcriber = ParakeetTranscriber()

            with pytest.raises(RuntimeError, match="onnx-asr not installed"):
                transcriber._ensure_model_loaded()
    finally:
        if saved_module is not None:
            sys.modules["onnx_asr"] = saved_module


def test_ensure_model_loaded_success(mock_onnx_asr) -> None:
    """Test successful model loading."""
    transcriber = ParakeetTranscriber()
    transcriber._ensure_model_loaded()

    assert transcriber._model is not None
    mock_onnx_asr.load_model.assert_called_once()
    args, kwargs = mock_onnx_asr.load_model.call_args
    assert args[0] == PARAKEET_MODEL_NAME
    # Providers may be passed as None; ensure keyword keys exist
    assert "providers" in kwargs
    assert "provider_options" in kwargs


def test_ensure_model_loaded_only_once(mock_onnx_asr) -> None:
    """Test model is only loaded once."""
    transcriber = ParakeetTranscriber()
    transcriber._ensure_model_loaded()
    transcriber._ensure_model_loaded()

    mock_onnx_asr.load_model.assert_called_once()


def test_warmup(mock_onnx_asr) -> None:
    """Test model warmup."""
    transcriber = ParakeetTranscriber()
    transcriber.warmup()

    assert transcriber._warmed_up
    assert transcriber._model.recognize.called


def test_warmup_only_once(mock_onnx_asr) -> None:
    """Test warmup is only done once."""
    transcriber = ParakeetTranscriber()
    transcriber.warmup()
    call_count_first = transcriber._model.recognize.call_count

    transcriber.warmup()
    call_count_second = transcriber._model.recognize.call_count

    assert call_count_first == call_count_second


def test_transcribe_file_not_found(mock_onnx_asr) -> None:
    """Test transcribing non-existent file."""
    transcriber = ParakeetTranscriber()

    with pytest.raises(FileNotFoundError, match="Audio file not found"):
        transcriber.transcribe_file("nonexistent.wav")


def test_transcribe_file_success(mock_onnx_asr, test_audio_file: Path) -> None:
    """Test successful file transcription."""
    transcriber = ParakeetTranscriber()
    result = transcriber.transcribe_file(test_audio_file)

    assert isinstance(result, TranscriptionResult)
    assert result.text == "test transcription"
    assert result.duration_ms > 0
    assert result.model_name == PARAKEET_MODEL_NAME


def test_transcribe_file_model_error(mock_onnx_asr, test_audio_file: Path) -> None:
    """Test transcription with model error."""
    mock_onnx_asr.load_model.return_value.recognize.side_effect = Exception(
        "Model error"
    )

    transcriber = ParakeetTranscriber()

    with pytest.raises(RuntimeError, match="Transcription failed"):
        transcriber.transcribe_file(test_audio_file)


def test_transcribe_buffer_success(mock_onnx_asr) -> None:
    """Test successful buffer transcription."""
    audio_data = b"\x00" * 32000  # 1 second of silence at 16kHz

    transcriber = ParakeetTranscriber()
    result = transcriber.transcribe_buffer(audio_data)

    assert isinstance(result, TranscriptionResult)
    assert result.text == "test transcription"
    assert result.duration_ms > 0


def test_transcribe_buffer_custom_sample_rate(mock_onnx_asr) -> None:
    """Test buffer transcription with custom sample rate."""
    audio_data = b"\x00" * 48000  # 1 second at 48kHz

    transcriber = ParakeetTranscriber()
    result = transcriber.transcribe_buffer(audio_data, sample_rate=48000)

    assert isinstance(result, TranscriptionResult)
    assert result.text == "test transcription"


def test_get_transcriber_singleton() -> None:
    """Test singleton pattern for get_transcriber."""
    from app.transcriber.parakeet import get_transcriber

    transcriber1 = get_transcriber()
    transcriber2 = get_transcriber()

    assert transcriber1 is transcriber2


def test_get_transcriber_with_providers() -> None:
    """Test get_transcriber with custom providers."""
    from app.transcriber.parakeet import get_transcriber

    providers = ["DmlExecutionProvider"]
    provider_options = [{"device_id": 0}]

    # Reset singleton for this test
    import app.transcriber.parakeet as parakeet_module

    parakeet_module._transcriber = None

    transcriber = get_transcriber(
        providers=providers, provider_options=provider_options
    )

    assert transcriber._providers == providers
    assert transcriber._provider_options == provider_options
