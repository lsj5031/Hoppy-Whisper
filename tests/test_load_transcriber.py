"""Tests for load_transcriber factory function."""

from __future__ import annotations

import pytest

from app.transcriber import RemoteTranscriber, load_transcriber


def test_load_transcriber_remote_mode():
    """Test load_transcriber creates RemoteTranscriber when remote_enabled=True."""
    transcriber = load_transcriber(
        remote_enabled=True,
        remote_endpoint="http://localhost:8000/transcribe",
        remote_api_key="test-key",
        remote_model="test-model",
    )

    assert isinstance(transcriber, RemoteTranscriber)
    assert transcriber.endpoint == "http://localhost:8000/transcribe"
    assert transcriber.api_key == "test-key"
    assert transcriber.model == "test-model"
    assert transcriber.provider == "RemoteAPI"


def test_load_transcriber_remote_missing_endpoint():
    """Test load_transcriber raises error when remote enabled but no endpoint."""
    with pytest.raises(ValueError) as exc_info:
        load_transcriber(remote_enabled=True, remote_endpoint="")

    assert "endpoint" in str(exc_info.value).lower()


def test_load_transcriber_remote_optional_api_key():
    """Test load_transcriber works without API key."""
    transcriber = load_transcriber(
        remote_enabled=True,
        remote_endpoint="http://localhost:8000/transcribe",
    )

    assert isinstance(transcriber, RemoteTranscriber)
    assert transcriber.api_key == ""
