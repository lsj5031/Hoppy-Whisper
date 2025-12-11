"""Tests for remote transcription via HTTP API."""

from __future__ import annotations

import tempfile
import wave
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from app.transcriber.remote import RemoteTranscriber, RemoteTranscriptionError


@pytest.fixture
def sample_audio_file():
    """Create a temporary WAV file for testing."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = Path(f.name)

    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00" * 16000)

    yield wav_path
    wav_path.unlink()


def test_remote_transcriber_init():
    """Test RemoteTranscriber initialization."""
    transcriber = RemoteTranscriber(
        endpoint="http://localhost:8000/transcribe",
        api_key="test-key",
    )
    assert transcriber.endpoint == "http://localhost:8000/transcribe"
    assert transcriber.api_key == "test-key"
    assert transcriber.provider == "RemoteAPI"


def test_remote_transcriber_warmup():
    """Test warmup is a no-op for remote transcriber."""
    transcriber = RemoteTranscriber(endpoint="http://localhost:8000/transcribe")
    transcriber.warmup()


@patch("app.transcriber.remote.requests.post")
def test_transcribe_file_success(mock_post, sample_audio_file):
    """Test successful remote transcription."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "hello world"}
    mock_post.return_value = mock_response

    transcriber = RemoteTranscriber(endpoint="http://localhost:8000/transcribe")
    result = transcriber.transcribe_file(sample_audio_file)

    assert result.text == "hello world"
    assert result.model_name == "RemoteAPI"
    assert result.duration_ms > 0
    mock_post.assert_called_once()


@patch("app.transcriber.remote.requests.post")
def test_transcribe_file_with_api_key(mock_post, sample_audio_file):
    """Test remote transcription with API key."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"text": "hello world"}
    mock_post.return_value = mock_response

    transcriber = RemoteTranscriber(
        endpoint="http://localhost:8000/transcribe",
        api_key="test-api-key",
    )
    result = transcriber.transcribe_file(sample_audio_file)

    assert result.text == "hello world"
    call_kwargs = mock_post.call_args[1]
    assert "headers" in call_kwargs
    assert call_kwargs["headers"]["Authorization"] == "Bearer test-api-key"


@patch("app.transcriber.remote.requests.post")
def test_transcribe_file_non_200_status(mock_post, sample_audio_file):
    """Test error handling for non-200 response."""
    mock_response = Mock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"
    mock_post.return_value = mock_response

    transcriber = RemoteTranscriber(endpoint="http://localhost:8000/transcribe")

    with pytest.raises(RemoteTranscriptionError) as exc_info:
        transcriber.transcribe_file(sample_audio_file)

    assert "500" in str(exc_info.value)


@patch("app.transcriber.remote.requests.post")
def test_transcribe_file_timeout(mock_post, sample_audio_file):
    """Test timeout handling."""
    import requests  # type: ignore[import-untyped]

    mock_post.side_effect = requests.exceptions.Timeout()

    transcriber = RemoteTranscriber(
        endpoint="http://localhost:8000/transcribe", timeout=1.0
    )

    with pytest.raises(RemoteTranscriptionError) as exc_info:
        transcriber.transcribe_file(sample_audio_file)

    assert "timed out" in str(exc_info.value).lower()


@patch("app.transcriber.remote.requests.post")
def test_transcribe_file_connection_error(mock_post, sample_audio_file):
    """Test connection error handling."""
    import requests  # type: ignore[import-untyped]

    mock_post.side_effect = requests.exceptions.ConnectionError()

    transcriber = RemoteTranscriber(endpoint="http://localhost:8000/transcribe")

    with pytest.raises(RemoteTranscriptionError) as exc_info:
        transcriber.transcribe_file(sample_audio_file)

    assert "connect" in str(exc_info.value).lower()


def test_transcribe_file_not_found():
    """Test error when audio file doesn't exist."""
    transcriber = RemoteTranscriber(endpoint="http://localhost:8000/transcribe")

    with pytest.raises(FileNotFoundError):
        transcriber.transcribe_file("nonexistent.wav")


@pytest.mark.parametrize(
    "response_data,expected_text",
    [
        ({"text": "hello"}, "hello"),
        ({"transcription": "world"}, "world"),
        ({"result": "test"}, "test"),
        ({"results": [{"text": "from array"}]}, "from array"),
        ({"results": ["simple string"]}, "simple string"),
        ({"data": {"text": "nested"}}, "nested"),
        ({"data": {"transcription": "nested2"}}, "nested2"),
    ],
)
@patch("app.transcriber.remote.requests.post")
def test_extract_text_from_various_formats(
    mock_post, sample_audio_file, response_data, expected_text
):
    """Test extraction of text from various response formats."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = response_data
    mock_post.return_value = mock_response

    transcriber = RemoteTranscriber(endpoint="http://localhost:8000/transcribe")
    result = transcriber.transcribe_file(sample_audio_file)

    assert result.text == expected_text


@patch("app.transcriber.remote.requests.post")
def test_extract_text_unsupported_format(mock_post, sample_audio_file):
    """Test error when response format is not recognized."""
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"unknown_key": "value"}
    mock_post.return_value = mock_response

    transcriber = RemoteTranscriber(endpoint="http://localhost:8000/transcribe")

    with pytest.raises(RemoteTranscriptionError) as exc_info:
        transcriber.transcribe_file(sample_audio_file)

    assert "extract transcription text" in str(exc_info.value).lower()
