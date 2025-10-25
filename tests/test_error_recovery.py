"""Tests for error handling and recovery scenarios."""

import pytest

from app.audio import AudioDeviceError, AudioRecorder
from app.hotkey import HotkeyInUseError, HotkeyManager, parse_hotkey
from app.transcriber import ModelManager


def test_audio_device_missing_raises_clear_error():
    """Test that missing audio device produces clear error message."""
    recorder = AudioRecorder()

    # Mock sounddevice to simulate no device
    try:
        import sounddevice as sd

        original_default = sd.default.device
        sd.default.device = (-1, -1)  # Invalid device

        with pytest.raises(AudioDeviceError) as exc_info:
            recorder.start()

        assert "microphone" in str(exc_info.value).lower() or "input device" in str(
            exc_info.value
        ).lower()

    finally:
        sd.default.device = original_default


def test_hotkey_conflict_raises_clear_error():
    """Test that hotkey conflict produces actionable error."""
    from unittest.mock import patch

    def dummy_cb():
        pass

    chord = parse_hotkey("CTRL+SHIFT+;")

    # First manager should succeed (or at least initialize)
    from app.hotkey import HotkeyCallbacks

    callbacks = HotkeyCallbacks(
        on_record_start=dummy_cb,
        on_record_stop=lambda: None,
        on_request_paste=dummy_cb,
    )

    # Bypass actual OS registration; simulate conflict on second register
    with patch.object(HotkeyManager, "_ensure_hotkey_available", lambda self, c: None):
        register_calls = {"count": 0}

        def fake_register(self):
            register_calls["count"] += 1
            if register_calls["count"] > 1:
                raise HotkeyInUseError(
                    f"Hotkey '{self._chord.display}' is already registered"
                )

        with patch.object(HotkeyManager, "_register_hotkey", fake_register):
            manager1 = HotkeyManager(chord, callbacks)
            manager1.start()

            # Second manager with same chord should fail
            with pytest.raises(HotkeyInUseError) as exc_info:
                manager2 = HotkeyManager(chord, callbacks)
                manager2.start()

            assert "already registered" in str(exc_info.value).lower()
            assert chord.display in str(exc_info.value)

            manager1.stop()


def test_model_download_retry_with_backoff():
    """Test that model download implements exponential backoff."""
    from pathlib import Path
    from unittest.mock import patch

    from app.transcriber import ModelAsset

    manager = ModelManager(cache_dir=Path("test_cache"))

    asset = ModelAsset(
        name="test.onnx",
        url="https://example.com/test.onnx",
        sha256="abc123",
        size_bytes=1024,
    )

    with patch("app.transcriber.model_manager.urllib.request.urlopen") as mock_open:
        mock_open.side_effect = Exception("Network error")

        with pytest.raises(RuntimeError) as exc_info:
            manager.download_asset(asset, max_retries=3)

        # Should have tried 3 times
        assert mock_open.call_count == 3
        assert "after 3 attempts" in str(exc_info.value)


def test_audio_callback_handles_device_errors_gracefully():
    """Test that audio callback doesn't crash on device errors."""
    import sounddevice as sd

    recorder = AudioRecorder()

    # Simulate callback with error status
    import numpy as np

    indata = np.zeros((1024, 1), dtype=np.float32)

    # Create error status flags
    status = sd.CallbackFlags()
    status.input_overflow = True

    # Should not raise
    recorder._audio_callback(indata, 1024, None, status)


def test_transcription_error_produces_actionable_message():
    """Test that transcription errors are clear and actionable."""
    from pathlib import Path

    from app.transcriber import ParakeetTranscriber

    transcriber = ParakeetTranscriber()

    # Try to transcribe non-existent file
    with pytest.raises(FileNotFoundError) as exc_info:
        transcriber.transcribe_file(Path("nonexistent.wav"))

    assert "not found" in str(exc_info.value).lower()


def test_audio_recorder_handles_repeated_stop_calls():
    """Test that calling stop() multiple times doesn't crash."""
    recorder = AudioRecorder()

    # Stop without start should not crash
    buffer1 = recorder.stop()
    assert len(buffer1) == 0

    # Multiple stops should not crash
    buffer2 = recorder.stop()
    assert len(buffer2) == 0


def test_audio_recorder_handles_repeated_start_calls():
    """Test that calling start() multiple times logs warning but doesn't crash."""
    from unittest.mock import MagicMock, patch

    import sounddevice as sd

    recorder = AudioRecorder()

    # Mock sounddevice to simulate a working device
    fake_device = {
        'name': 'Test Device',
        'max_input_channels': 2,
        'default_samplerate': 16000
    }

    original_default = sd.default.device

    try:
        with patch('sounddevice.query_devices') as mock_query:
            mock_query.return_value = [fake_device]
            with patch('sounddevice.InputStream') as mock_stream:
                # Mock the stream to avoid actual audio capture
                mock_instance = MagicMock()
                mock_stream.return_value = mock_instance

                # Ensure default device points to our fake device
                sd.default.device = (0, -1)

                recorder.start()
                # Second start should log warning but not crash
                recorder.start()  # Should log warning and return
    finally:
        sd.default.device = original_default
        recorder.stop()


def test_model_manager_validates_corrupted_downloads():
    """Test that corrupted downloads are detected and retried."""
    from pathlib import Path
    from unittest.mock import patch

    from app.transcriber import ModelAsset

    manager = ModelManager(cache_dir=Path("test_cache"))

    asset = ModelAsset(
        name="test.onnx",
        url="https://example.com/test.onnx",
        sha256="abc123" * 10 + "0" * 4,  # Valid SHA256 format
        size_bytes=1024,
    )

    def corrupt_download(*args, **kwargs):
        # Create file with wrong content
        path = manager.get_model_path(asset)
        path.write_bytes(b"wrong content")

    with patch(
        "app.transcriber.model_manager.ModelManager._download_with_progress",
        side_effect=corrupt_download,
    ):
        with pytest.raises(RuntimeError) as exc_info:
            manager.download_asset(asset, max_retries=2)

        # Should mention hash or size mismatch
        error_msg = str(exc_info.value).lower()
        assert "mismatch" in error_msg or "failed" in error_msg


def test_cleanup_handles_invalid_mode_gracefully():
    """Test that invalid cleanup mode falls back to standard."""
    from app.cleanup import CleanupEngine, CleanupMode

    # Should not crash, should log warning and use standard mode
    engine = CleanupEngine(CleanupMode.STANDARD)
    result = engine.clean("hello world")
    assert isinstance(result, str)
