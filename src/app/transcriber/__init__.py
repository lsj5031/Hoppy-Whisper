"""Speech-to-text transcription utilities."""

from .hoppy import HoppyTranscriber, TranscriptionResult, get_transcriber
from .model_manager import ModelAsset, ModelManager, ModelManifest, get_model_manager
from .onnx_session import (
    OnnxSessionManager,
    ProviderInfo,
    get_session_manager,
)
from .remote import RemoteTranscriber, RemoteTranscriptionError

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
    "RemoteTranscriber",
    "RemoteTranscriptionError",
]


def load_transcriber(
    remote_enabled: bool = False,
    remote_endpoint: str = "",
    remote_api_key: str = "",
) -> HoppyTranscriber | RemoteTranscriber:
    """Load and warm up the transcriber.

    Uses a late import of get_transcriber to make it patch-friendly in tests.

    Args:
        remote_enabled: If True, use remote transcription instead of local ONNX
        remote_endpoint: URL of the remote transcription endpoint
        remote_api_key: Optional API key for remote authentication

    Returns:
        Either a HoppyTranscriber (local) or RemoteTranscriber (remote)
    """
    if remote_enabled:
        if not remote_endpoint:
            raise ValueError(
                "Remote transcription enabled but no endpoint configured. "
                "Please set remote_transcription_endpoint in settings."
            )
        remote_transcriber = RemoteTranscriber(
            endpoint=remote_endpoint,
            api_key=remote_api_key,
        )
        remote_transcriber.warmup()
        return remote_transcriber

    from . import hoppy as hoppy_module
    from .onnx_session import get_session_manager

    session_manager = get_session_manager()
    providers, provider_options = session_manager.get_providers()

    local_transcriber = hoppy_module.get_transcriber(
        providers=providers, provider_options=provider_options
    )
    local_transcriber.warmup()

    return local_transcriber
