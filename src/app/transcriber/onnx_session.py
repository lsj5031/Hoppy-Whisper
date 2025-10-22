"""ONNX Runtime session management with DirectML support."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ProviderInfo:
    """Information about an ONNX Runtime execution provider."""

    name: str
    available: bool
    device_name: str | None = None
    error: str | None = None


class OnnxSessionManager:
    """Manages ONNX Runtime sessions with provider preference."""

    def __init__(self) -> None:
        self._providers: list[str] = []
        self._provider_options: list[dict[str, Any]] = []
        self._detect_providers()

    def _detect_providers(self) -> None:
        """Detect available ONNX Runtime providers and prefer DirectML."""
        try:
            import onnxruntime as ort
        except ImportError:
            logger.warning("onnxruntime-directml not installed, falling back to CPU")
            self._providers = ["CPUExecutionProvider"]
            self._provider_options = [{}]
            return

        available = ort.get_available_providers()
        logger.info(f"Available ONNX Runtime providers: {available}")

        if "DmlExecutionProvider" in available:
            logger.info("DirectML provider detected, will use GPU acceleration")
            self._providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
            self._provider_options = [
                {"device_id": 0},
                {},
            ]
        else:
            logger.info("DirectML not available, using CPU")
            self._providers = ["CPUExecutionProvider"]
            self._provider_options = [{}]

    def get_providers(self) -> tuple[list[str], list[dict[str, Any]]]:
        """Return the detected providers and their options."""
        return self._providers, self._provider_options

    def get_device_info(self) -> list[ProviderInfo]:
        """Get detailed information about available providers."""
        devices: list[ProviderInfo] = []

        try:
            import onnxruntime as ort
        except ImportError:
            devices.append(
                ProviderInfo(
                    name="CPUExecutionProvider",
                    available=True,
                    device_name="CPU (onnxruntime not installed)",
                )
            )
            return devices

        available = set(ort.get_available_providers())

        if "DmlExecutionProvider" in available:
            devices.append(
                ProviderInfo(
                    name="DmlExecutionProvider",
                    available=True,
                    device_name="DirectML GPU",
                )
            )

        if "CPUExecutionProvider" in available:
            devices.append(
                ProviderInfo(
                    name="CPUExecutionProvider",
                    available=True,
                    device_name="CPU",
                )
            )

        if not devices:
            devices.append(
                ProviderInfo(
                    name="Unknown",
                    available=False,
                    error="No providers detected",
                )
            )

        return devices

    def create_session(
        self,
        model_path: str,
        **session_options: Any,
    ) -> Any:
        """Create an ONNX Runtime inference session with preferred providers."""
        try:
            import onnxruntime as ort
        except ImportError as e:
            raise RuntimeError(
                "onnxruntime-directml not installed. "
                "Please install it to use transcription."
            ) from e

        sess_opts = ort.SessionOptions()

        for key, value in session_options.items():
            setattr(sess_opts, key, value)

        providers, provider_options = self.get_providers()

        logger.info(f"Creating session with providers: {providers}")

        try:
            session = ort.InferenceSession(
                model_path,
                sess_options=sess_opts,
                providers=providers,
                provider_options=provider_options,
            )
            logger.info(f"Session created with provider: {session.get_providers()}")
            return session
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise


_session_manager: OnnxSessionManager | None = None


def get_session_manager() -> OnnxSessionManager:
    """Get or create the global session manager singleton."""
    global _session_manager
    if _session_manager is None:
        _session_manager = OnnxSessionManager()
    return _session_manager
