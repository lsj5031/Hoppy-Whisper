"""ONNX Runtime session management with DirectML support."""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path
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
        """Detect available ONNX Runtime providers and prefer DirectML.

        Environment overrides:
        - HOPPY_WHISPER_FORCE_CPU=1  -> force CPUExecutionProvider only
        - HOPPY_WHISPER_DISABLE_DML=1 -> ignore DmlExecutionProvider even if present
        """
        ensure_ort_dll_search_paths()
        try:
            import onnxruntime as ort
        except ImportError as e:
            logger.warning(
                "onnxruntime import failed (%s); falling back to CPU", str(e)
            )
            self._providers = ["CPUExecutionProvider"]
            self._provider_options = [{}]
            return

        force_cpu_env = os.getenv("HOPPY_WHISPER_FORCE_CPU", "").strip().lower()
        disable_dml_env = os.getenv("HOPPY_WHISPER_DISABLE_DML", "").strip().lower()
        force_cpu = force_cpu_env in ("1", "true", "yes", "on")
        disable_dml = disable_dml_env in ("1", "true", "yes", "on")

        available = ort.get_available_providers()
        logger.info("Available ONNX Runtime providers: %s", available)

        if force_cpu:
            logger.info(
                "Forcing CPUExecutionProvider due to HOPPY_WHISPER_FORCE_CPU=%s",
                force_cpu_env,
            )
            self._providers = ["CPUExecutionProvider"]
            self._provider_options = [{}]
            return

        if "DmlExecutionProvider" in available and not disable_dml:
            logger.info("DirectML provider detected, will use GPU acceleration")
            self._providers = ["DmlExecutionProvider", "CPUExecutionProvider"]
            self._provider_options = [
                {"device_id": 0},
                {},
            ]
        else:
            if "DmlExecutionProvider" in available and disable_dml:
                logger.info(
                    "DirectML provider detected but disabled via "
                    "HOPPY_WHISPER_DISABLE_DML=%s",
                    disable_dml_env,
                )
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


def ensure_ort_dll_search_paths() -> None:
    """Ensure DLL search paths include bundled ONNX Runtime locations in frozen apps.

    Mirrors the runtime hook behavior for robustness.
    """
    try:
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            base = Path(sys._MEIPASS)
            candidates = (
                base / "onnxruntime" / "capi",
                base / "onnxruntime" / "providers" / "dml",
                base / "onnxruntime",
                base / "onnxruntime.libs",
                base / "onnxruntime" / "libs",
                base / "numpy.libs",
                base,
            )
            for p in candidates:
                try:
                    if p.is_dir():
                        os.add_dll_directory(str(p))  # type: ignore[attr-defined]
                        os.environ["PATH"] = (
                            str(p) + os.pathsep + os.environ.get("PATH", "")
                        )
                except Exception:
                    continue
    except Exception:
        # Best effort only
        pass
