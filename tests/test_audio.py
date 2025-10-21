"""Tests for audio capture and recording."""

from __future__ import annotations

from unittest.mock import MagicMock, Mock

import numpy as np
import pytest

from app.audio import (
    AudioDeviceError,
    AudioRecorder,
    initialize_audio_pipeline,
    list_audio_devices,
)
from app.audio.exceptions import AudioCaptureError


@pytest.fixture
def mock_sounddevice(monkeypatch: pytest.MonkeyPatch):
    """Mock sounddevice module for testing."""
    mock_sd = MagicMock()

    # Device list for query_devices() without args
    devices = [
        {
            "name": "Mock Microphone",
            "max_input_channels": 2,
            "max_output_channels": 0,
        },
        {
            "name": "Mock Speakers",
            "max_input_channels": 0,
            "max_output_channels": 2,
        },
    ]

    # Mock query_devices to return list when called without args,
    # or specific device dict when called with device index
    def query_devices_mock(device=None, kind=None):
        if device is None:
            return devices
        # Return the specific device
        return devices[device]

    mock_sd.query_devices = Mock(side_effect=query_devices_mock)

    # Mock default device
    mock_sd.default.device = [0, 1]  # input, output

    # Mock stream
    mock_stream = MagicMock()
    mock_sd.InputStream.return_value = mock_stream

    monkeypatch.setattr("app.audio.recorder.sd", mock_sd)

    return mock_sd


def test_list_audio_devices_returns_input_devices(mock_sounddevice):
    """Test that list_audio_devices returns only input-capable devices."""
    devices = list_audio_devices()

    assert len(devices) == 1
    assert devices[0]["name"] == "Mock Microphone"
    assert devices[0]["index"] == 0
    assert devices[0]["channels"] == 2


def test_initialize_audio_pipeline_succeeds_with_devices(mock_sounddevice):
    """Test that initialize_audio_pipeline succeeds when devices are available."""
    initialize_audio_pipeline()
    mock_sounddevice.query_devices.assert_called()


def test_initialize_audio_pipeline_fails_without_devices(mock_sounddevice):
    """Test that initialize_audio_pipeline raises when no devices are found."""

    # Override to return only output devices
    def query_devices_no_input(device=None, kind=None):
        return [
            {"name": "Speakers Only", "max_input_channels": 0, "max_output_channels": 2}
        ]

    mock_sounddevice.query_devices.side_effect = query_devices_no_input

    with pytest.raises(AudioDeviceError, match="No audio input devices detected"):
        initialize_audio_pipeline()


def test_audio_recorder_initialization(mock_sounddevice):
    """Test AudioRecorder initializes with correct defaults."""
    recorder = AudioRecorder()

    assert recorder.sample_rate == 16000
    assert recorder.channels == 1
    assert not recorder.is_recording


def test_audio_recorder_start_creates_stream(mock_sounddevice):
    """Test that start() creates and starts an audio stream."""
    recorder = AudioRecorder()
    recorder.start()

    assert recorder.is_recording
    mock_sounddevice.InputStream.assert_called_once()

    # Verify stream configuration
    call_kwargs = mock_sounddevice.InputStream.call_args.kwargs
    assert call_kwargs["samplerate"] == 16000
    assert call_kwargs["channels"] == 1
    assert call_kwargs["dtype"] == np.float32
    assert call_kwargs["latency"] == "low"
    assert "callback" in call_kwargs

    mock_stream = mock_sounddevice.InputStream.return_value
    mock_stream.start.assert_called_once()


def test_audio_recorder_start_raises_on_missing_device(mock_sounddevice):
    """Test that start() raises AudioDeviceError when device is missing."""
    mock_sounddevice.default.device = [None, 1]

    recorder = AudioRecorder()
    with pytest.raises(AudioDeviceError, match="No default input device configured"):
        recorder.start()

    assert not recorder.is_recording


def test_audio_recorder_start_raises_on_insufficient_channels(mock_sounddevice):
    """Test that start() raises when device has insufficient channels."""

    # Override the mock to return a device with insufficient channels
    def query_devices_limited(device=None, kind=None):
        if device is None:
            return [
                {"name": "Mock Mic", "max_input_channels": 0, "max_output_channels": 0}
            ]
        return {"name": "Mock Mic", "max_input_channels": 0, "max_output_channels": 0}

    mock_sounddevice.query_devices.side_effect = query_devices_limited

    recorder = AudioRecorder(channels=2)
    with pytest.raises(AudioDeviceError, match="has 0 channels"):
        recorder.start()


def test_audio_recorder_stop_returns_buffer(mock_sounddevice):
    """Test that stop() returns accumulated audio buffer."""
    recorder = AudioRecorder()
    recorder.start()

    # Simulate audio callbacks
    callback = mock_sounddevice.InputStream.call_args.kwargs["callback"]

    # Add some mock audio data
    chunk1 = np.random.rand(512, 1).astype(np.float32)
    chunk2 = np.random.rand(512, 1).astype(np.float32)

    callback(chunk1, 512, None, MagicMock())
    callback(chunk2, 512, None, MagicMock())

    buffer = recorder.stop()

    assert not recorder.is_recording
    assert buffer.shape == (1024, 1)
    assert buffer.dtype == np.float32

    mock_stream = mock_sounddevice.InputStream.return_value
    mock_stream.stop.assert_called_once()
    mock_stream.close.assert_called_once()


def test_audio_recorder_stop_when_not_recording_returns_empty(mock_sounddevice):
    """Test that stop() without start() returns empty buffer."""
    recorder = AudioRecorder()
    buffer = recorder.stop()

    assert buffer.shape == (0, 1)
    assert buffer.dtype == np.float32


def test_audio_recorder_start_when_already_started_is_noop(mock_sounddevice):
    """Test that calling start() when already recording is ignored."""
    recorder = AudioRecorder()
    recorder.start()

    mock_sounddevice.InputStream.reset_mock()
    recorder.start()

    mock_sounddevice.InputStream.assert_not_called()


def test_audio_recorder_buffer_duration_calculation(mock_sounddevice):
    """Test that get_buffer_duration returns correct duration."""
    recorder = AudioRecorder(sample_rate=16000)
    recorder.start()

    callback = mock_sounddevice.InputStream.call_args.kwargs["callback"]

    # Add 16000 samples = 1 second at 16 kHz
    for _ in range(32):  # 32 chunks of 512 samples = 16384 samples
        chunk = np.random.rand(512, 1).astype(np.float32)
        callback(chunk, 512, None, MagicMock())

    duration = recorder.get_buffer_duration()
    assert 1.0 <= duration <= 1.1  # ~1 second


def test_audio_recorder_callback_copies_data(mock_sounddevice):
    """Test that audio callback copies data to prevent corruption."""
    recorder = AudioRecorder()
    recorder.start()

    callback = mock_sounddevice.InputStream.call_args.kwargs["callback"]

    original_chunk = np.ones((512, 1), dtype=np.float32)
    callback(original_chunk, 512, None, MagicMock())

    # Modify original chunk
    original_chunk.fill(0.0)

    buffer = recorder.stop()

    # Buffer should still contain original values (not zeros)
    assert buffer[0, 0] == 1.0


def test_audio_recorder_handles_stream_error(mock_sounddevice):
    """Test that recorder handles stream creation errors gracefully."""
    mock_sounddevice.InputStream.side_effect = Exception("Stream error")

    recorder = AudioRecorder()
    with pytest.raises(AudioCaptureError, match="Failed to start audio stream"):
        recorder.start()

    assert not recorder.is_recording


def test_audio_recorder_custom_sample_rate_and_channels(mock_sounddevice):
    """Test that recorder respects custom sample rate and channel configuration."""
    recorder = AudioRecorder(sample_rate=48000, channels=2)
    recorder.start()

    call_kwargs = mock_sounddevice.InputStream.call_args.kwargs
    assert call_kwargs["samplerate"] == 48000
    assert call_kwargs["channels"] == 2


def test_audio_recorder_reports_callback_status_warnings(mock_sounddevice, caplog):
    """Test that recorder logs warnings from audio callback status flags."""
    recorder = AudioRecorder()
    recorder.start()

    callback = mock_sounddevice.InputStream.call_args.kwargs["callback"]

    # Simulate callback with status flags
    status_mock = MagicMock()
    status_mock.__bool__ = lambda self: True
    status_mock.__str__ = lambda self: "input overflow"

    chunk = np.random.rand(512, 1).astype(np.float32)
    callback(chunk, 512, None, status_mock)

    assert "Audio callback status" in caplog.text


def test_list_audio_devices_handles_errors_gracefully(monkeypatch: pytest.MonkeyPatch):
    """Test that list_audio_devices returns empty list on errors."""
    mock_sd = MagicMock()
    mock_sd.query_devices.side_effect = Exception("Device enumeration failed")
    monkeypatch.setattr("app.audio.recorder.sd", mock_sd)

    devices = list_audio_devices()
    assert devices == []
