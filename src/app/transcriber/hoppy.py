"""ONNX transcriber implementation for Hoppy Whisper."""

from __future__ import annotations

import logging
import os
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


HOPPY_MODEL_REPO = "nemo-parakeet-tdt-0.6b-v3"


@dataclass
class TranscriptionResult:
    """Result of a transcription operation."""

    text: str
    duration_ms: float
    model_name: str


class HoppyTranscriber:
    """ONNX transcriber with optional DirectML support."""

    def __init__(
        self,
        model_path: Path | None = None,
        providers: list[str] | None = None,
        provider_options: list[dict[str, Any]] | None = None,
    ) -> None:
        """Initialize the transcriber.

        Args:
            model_path: Path to model directory (encoder/decoder/vocab).
                If None, uses default.
            providers: ONNX Runtime providers list. If None, auto-detected.
            provider_options: Provider options list. If None, uses defaults.
        """
        self.model_path = model_path
        self._model: Any = None
        self._providers = providers
        self._provider_options = provider_options
        self._warmed_up = False
        # Provider reporting
        self.provider_requested: str = (
            ",".join(providers) if providers else "CPUExecutionProvider"
        )
        self.provider_detected: str = "CPUExecutionProvider"
        # Initialize detected provider based on environment capability
        self._update_provider_detection()

        logger.info("Transcriber initialized")

    def _ensure_model_loaded(self) -> None:
        """Ensure the model is loaded and ready."""
        if self._model is not None:
            return

        # Ensure ORT DLL directories are available in frozen mode before imports
        try:
            from .onnx_session import ensure_ort_dll_search_paths

            ensure_ort_dll_search_paths()
        except Exception:
            pass

        # Best-effort: patch onnxruntime to default to DirectML if available
        # This lets third-party libs that don't pass providers (e.g., onnx_asr)
        # still pick up GPU acceleration without code changes upstream.
        try:
            import onnxruntime as ort  # type: ignore

            # Resolve preferred providers from our session manager
            try:
                from .onnx_session import get_session_manager

                provs, prov_opts = (
                    (self._providers, self._provider_options)
                    if self._providers is not None
                    else get_session_manager().get_providers()
                )
            except Exception:
                provs, prov_opts = (self._providers or ["CPUExecutionProvider"], [{}])

            _OriginalIS = ort.InferenceSession

            def _PatchedInferenceSession(*args, **kwargs):  # type: ignore
                if "providers" not in kwargs or kwargs.get("providers") is None:
                    kwargs["providers"] = provs
                    kwargs["provider_options"] = prov_opts
                return _OriginalIS(*args, **kwargs)

            # Only patch once per process
            if not getattr(ort, "_hoppy_patched", False):
                ort.InferenceSession = _PatchedInferenceSession  # type: ignore[assignment]
                ort._hoppy_patched = True
        except Exception:
            # If ORT isn't available yet or patch fails, continue without it.
            pass

        try:
            import onnx_asr
        except ImportError as e:
            msg = str(e)
            if "onnxruntime" in msg or "onnxruntime_pybind11_state" in msg:
                raise RuntimeError(
                    f"ONNX Runtime failed to load native bindings: {msg}"
                ) from e
            raise RuntimeError(
                "onnx-asr not installed. Please install it to use transcription."
            ) from e

        logger.info("Loading TDT 0.6b model...")
        start_time = time.time()

        # Record requested providers for metrics/debugging
        if self._providers:
            logger.info(f"Requested providers: {self._providers}")

        # Resolve local model directory (prefer bundled models when frozen)
        local_model_dir: Path | None = None
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            try:
                from .model_manager import get_model_manager

                enc, dec, voc = get_model_manager().ensure_models()
                # Parent dir should contain all required assets
                candidate = enc.parent
                if candidate.exists():
                    local_model_dir = candidate
            except Exception:
                # Best-effort; continue and let onnx_asr decide
                local_model_dir = None

        # Suppress progress bars in windowed builds to avoid tqdm writing to None
        os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")
        os.environ.setdefault("TQDM_DISABLE", "1")
        # Prefer offline mode when we have a local directory
        if local_model_dir is not None:
            os.environ.setdefault("HF_HUB_OFFLINE", "1")

        # Load the model (use model name + model_dir when available;
        # otherwise, repo name)
        try:
            # Prefer passing providers if the API supports it; otherwise rely on
            # our ORT monkey-patch above to enforce provider order.
            if local_model_dir is not None:
                # Bundled case: pass known model name with explicit model_dir
                try:
                    logger.info(f"Loading model locally from: {local_model_dir}")
                    self._model = onnx_asr.load_model(
                        HOPPY_MODEL_REPO,
                        model_dir=str(local_model_dir),
                        providers=self._providers,
                        provider_options=self._provider_options,
                    )
                except TypeError:
                    # Fallbacks for older signatures
                    try:
                        self._model = onnx_asr.load_model(
                            HOPPY_MODEL_REPO,
                            model_dir=str(local_model_dir),
                        )
                    except TypeError:
                        self._model = onnx_asr.load_model(HOPPY_MODEL_REPO)
            else:
                # Non-frozen or no local bundle: use repo name, allow download/cache
                try:
                    self._model = onnx_asr.load_model(
                        HOPPY_MODEL_REPO,
                        providers=self._providers,
                        provider_options=self._provider_options,
                    )
                except TypeError:
                    self._model = onnx_asr.load_model(HOPPY_MODEL_REPO)
        except Exception as e:
            if isinstance(e, ModuleNotFoundError) and e.name == "huggingface_hub":
                friendly = (
                    "huggingface-hub not installed. "
                    "Install it to download model assets."
                )
            else:
                friendly = str(e)
            logger.error(f"Failed to load model: {friendly}")
            raise RuntimeError(f"Failed to load model: {friendly}") from e

        load_time = (time.time() - start_time) * 1000
        logger.info(f"Model loaded in {load_time:.0f} ms")
        # Re-evaluate detected provider after model load
        self._update_provider_detection()

    def warmup(self) -> None:
        """Warm up the model with a dummy inference."""
        if self._warmed_up:
            return

        logger.info("Warming up model...")
        self._ensure_model_loaded()

        # Create a short silent audio file for warmup
        import tempfile
        import wave

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # Create 1 second of silence at 16kHz
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(16000)
                wf.writeframes(b"\x00" * 32000)  # 1 second of silence

            start_time = time.time()
            _ = self._model.recognize(temp_path)
            warmup_time = (time.time() - start_time) * 1000

            logger.info(f"Model warmup completed in {warmup_time:.0f} ms")
            self._warmed_up = True
            # Ensure provider detection is up to date
            self._update_provider_detection()

        finally:
            import os

            if os.path.exists(temp_path):
                os.unlink(temp_path)

    def _update_provider_detection(self) -> None:
        """Update provider_detected based on available ONNX Runtime providers.

        This reflects environment capability, not a guaranteed runtime binding
        of onnx_asr.
        """
        try:
            # Lazy import to avoid circular dependencies
            from .onnx_session import get_session_manager

            devices = get_session_manager().get_device_info()
            names = [d.name for d in devices if d.available]
            if "DmlExecutionProvider" in names:
                self.provider_detected = "DmlExecutionProvider"
            elif "CPUExecutionProvider" in names:
                self.provider_detected = "CPUExecutionProvider"
            else:
                self.provider_detected = "Unknown"
        except Exception:
            # Default to CPU if detection fails
            self.provider_detected = "CPUExecutionProvider"

    @property
    def provider(self) -> str:
        """Return the detected provider for compatibility with existing callers."""
        return self.provider_detected

    def transcribe_file(self, audio_path: str | Path) -> TranscriptionResult:
        """Transcribe an audio file.

        Args:
            audio_path: Path to audio file (WAV, 16kHz, mono recommended)

        Returns:
            TranscriptionResult with text and timing information

        Raises:
            RuntimeError: If transcription fails
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        self._ensure_model_loaded()

        logger.info(f"Transcribing {audio_path.name}...")
        start_time = time.time()

        try:
            text = self._model.recognize(str(audio_path))
            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Transcription completed in {duration_ms:.0f} ms: '{text[:50]}...'"
            )

            return TranscriptionResult(
                text=text,
                duration_ms=duration_ms,
                model_name=HOPPY_MODEL_REPO,
            )

        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            raise RuntimeError(f"Transcription failed: {e}") from e

    def transcribe_buffer(
        self, audio_data: bytes, sample_rate: int = 16000
    ) -> TranscriptionResult:
        """Transcribe audio from a buffer.

        Args:
            audio_data: Raw PCM16 audio bytes
            sample_rate: Sample rate in Hz (default: 16000)

        Returns:
            TranscriptionResult with text and timing information

        Raises:
            RuntimeError: If transcription fails
        """
        import tempfile
        import wave

        # Write to temporary WAV file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            with wave.open(temp_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data)

            result = self.transcribe_file(temp_path)
            return result

        finally:
            import os

            if os.path.exists(temp_path):
                os.unlink(temp_path)


_transcriber: HoppyTranscriber | None = None


def get_transcriber(
    providers: list[str] | None = None,
    provider_options: list[dict[str, Any]] | None = None,
) -> HoppyTranscriber:
    """Get or create the global transcriber singleton.

    Args:
        providers: ONNX Runtime providers (only used on first call)
        provider_options: Provider options (only used on first call)

    Returns:
        The global transcriber instance
    """
    global _transcriber
    if _transcriber is None:
        _transcriber = HoppyTranscriber(
            providers=providers,
            provider_options=provider_options,
        )
    return _transcriber
