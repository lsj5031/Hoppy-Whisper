"""Tests for ONNX Runtime session management."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.transcriber.onnx_session import (
    OnnxSessionManager,
    get_session_manager,
)


class TestOnnxSessionManager:
    """Tests for OnnxSessionManager."""

    def test_detect_directml_available(self) -> None:
        """Test provider detection when DirectML is available."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = [
            "DmlExecutionProvider",
            "CPUExecutionProvider",
        ]

        with patch.dict("sys.modules", {"onnxruntime": mock_ort}):
            manager = OnnxSessionManager()
            providers, options = manager.get_providers()

            assert providers == ["DmlExecutionProvider", "CPUExecutionProvider"]
            assert len(options) == 2
            assert options[0] == {"device_id": 0}
            assert options[1] == {}

    def test_detect_cpu_only(self) -> None:
        """Test provider detection when only CPU is available."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]

        with patch.dict("sys.modules", {"onnxruntime": mock_ort}):
            manager = OnnxSessionManager()
            providers, options = manager.get_providers()

            assert providers == ["CPUExecutionProvider"]
            assert len(options) == 1
            assert options[0] == {}

    def test_fallback_when_onnxruntime_not_installed(self) -> None:
        """Test fallback to CPU when onnxruntime is not installed."""
        with patch.dict("sys.modules", {"onnxruntime": None}):
            manager = OnnxSessionManager()
            providers, options = manager.get_providers()

            assert providers == ["CPUExecutionProvider"]
            assert len(options) == 1

    def test_get_device_info_with_directml(self) -> None:
        """Test device info when DirectML is available."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = [
            "DmlExecutionProvider",
            "CPUExecutionProvider",
        ]

        with patch.dict("sys.modules", {"onnxruntime": mock_ort}):
            manager = OnnxSessionManager()
            devices = manager.get_device_info()

            assert len(devices) == 2
            assert devices[0].name == "DmlExecutionProvider"
            assert devices[0].available is True
            assert "DirectML" in devices[0].device_name
            assert devices[1].name == "CPUExecutionProvider"
            assert devices[1].available is True

    def test_get_device_info_cpu_only(self) -> None:
        """Test device info when only CPU is available."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]

        with patch.dict("sys.modules", {"onnxruntime": mock_ort}):
            manager = OnnxSessionManager()
            devices = manager.get_device_info()

            assert len(devices) == 1
            assert devices[0].name == "CPUExecutionProvider"
            assert devices[0].available is True

    def test_get_device_info_no_onnxruntime(self) -> None:
        """Test device info when onnxruntime is not installed."""
        with patch.dict("sys.modules", {"onnxruntime": None}):
            manager = OnnxSessionManager()
            devices = manager.get_device_info()

            assert len(devices) == 1
            assert devices[0].name == "CPUExecutionProvider"
            assert "not installed" in devices[0].device_name

    def test_create_session_success(self) -> None:
        """Test successful session creation."""
        mock_ort = MagicMock()
        mock_session = MagicMock()
        mock_session.get_providers.return_value = ["DmlExecutionProvider"]
        mock_ort.InferenceSession.return_value = mock_session
        mock_ort.get_available_providers.return_value = [
            "DmlExecutionProvider",
            "CPUExecutionProvider",
        ]

        with patch.dict("sys.modules", {"onnxruntime": mock_ort}):
            manager = OnnxSessionManager()
            session = manager.create_session("model.onnx")

            assert session is not None
            mock_ort.InferenceSession.assert_called_once()

    def test_create_session_with_options(self) -> None:
        """Test session creation with custom options."""
        mock_ort = MagicMock()
        mock_session = MagicMock()
        mock_session.get_providers.return_value = ["CPUExecutionProvider"]
        mock_ort.InferenceSession.return_value = mock_session
        mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]

        with patch.dict("sys.modules", {"onnxruntime": mock_ort}):
            manager = OnnxSessionManager()
            session = manager.create_session(
                "model.onnx",
                graph_optimization_level=3,
                intra_op_num_threads=4,
            )

            assert session is not None

    def test_create_session_fails_without_onnxruntime(self) -> None:
        """Test session creation fails gracefully without onnxruntime."""
        with patch.dict("sys.modules", {"onnxruntime": None}):
            manager = OnnxSessionManager()

            with pytest.raises(
                RuntimeError, match="onnxruntime-directml not installed"
            ):
                manager.create_session("model.onnx")

    def test_create_session_handles_failure(self) -> None:
        """Test session creation handles failures properly."""
        mock_ort = MagicMock()
        mock_ort.get_available_providers.return_value = ["CPUExecutionProvider"]
        mock_ort.InferenceSession.side_effect = Exception("Model load failed")

        with patch.dict("sys.modules", {"onnxruntime": mock_ort}):
            manager = OnnxSessionManager()

            with pytest.raises(Exception, match="Model load failed"):
                manager.create_session("invalid_model.onnx")


def test_get_session_manager_singleton() -> None:
    """Test that get_session_manager returns a singleton."""
    manager1 = get_session_manager()
    manager2 = get_session_manager()

    assert manager1 is manager2
