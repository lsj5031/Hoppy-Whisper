"""Speech-to-text transcription utilities."""

from .model_manager import ModelAsset, ModelManager, ModelManifest, get_model_manager
from .onnx_session import OnnxSessionManager, ProviderInfo, get_session_manager
from .parakeet import ParakeetTranscriber, TranscriptionResult

__all__ = [
    "OnnxSessionManager",
    "ProviderInfo",
    "get_session_manager",
    "ModelManager",
    "ModelAsset",
    "ModelManifest",
    "get_model_manager",
    "ParakeetTranscriber",
    "TranscriptionResult",
    "get_transcriber",
]


def load_transcriber() -> ParakeetTranscriber:
    """Load and warm up the transcriber.

    Uses a late import of get_transcriber to make it patch-friendly in tests.
    """
    from .onnx_session import get_session_manager
    from . import parakeet as parakeet_module

    session_manager = get_session_manager()
    providers, provider_options = session_manager.get_providers()

    transcriber = parakeet_module.get_transcriber(
        providers=providers, provider_options=provider_options
    )
    transcriber.warmup()

    return transcriber
