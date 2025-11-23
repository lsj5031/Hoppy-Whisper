"""Speech-to-text transcription utilities."""

from .hoppy import HoppyTranscriber, TranscriptionResult, get_transcriber
from .model_manager import ModelAsset, ModelManager, ModelManifest, get_model_manager
from .onnx_session import (
    OnnxSessionManager,
    ProviderInfo,
    get_session_manager,
)

__all__ = [
    "OnnxSessionManager",
    "ProviderInfo",
    "get_session_manager",
    "ModelManager",
    "ModelAsset",
    "ModelManifest",
    "get_model_manager",
    "HoppyTranscriber",
    "TranscriptionResult",
    "get_transcriber",
]


def load_transcriber() -> HoppyTranscriber:
    """Load and warm up the transcriber.

    Uses a late import of get_transcriber to make it patch-friendly in tests.
    """
    from . import hoppy as hoppy_module
    from .onnx_session import get_session_manager

    session_manager = get_session_manager()
    providers, provider_options = session_manager.get_providers()

    transcriber = hoppy_module.get_transcriber(
        providers=providers, provider_options=provider_options
    )
    transcriber.warmup()

    return transcriber
