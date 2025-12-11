"""Remote transcription via HTTP API."""

from __future__ import annotations

import logging
import time
import wave
from enum import Enum
from pathlib import Path
from typing import Any

import requests  # type: ignore[import-untyped]

from .hoppy import TranscriptionResult

logger = logging.getLogger(__name__)


class RemoteTranscriptionErrorType(Enum):
    """Categorizes the failure mode of remote transcription."""

    NETWORK_TIMEOUT = "network_timeout"
    CONNECTION_FAILED = "connection_failed"
    HTTP_ERROR = "http_error"
    PARSE_ERROR = "parse_error"
    FORMAT_ERROR = "format_error"
    UNKNOWN = "unknown"


class RemoteTranscriptionError(Exception):
    """Structured exception for remote transcription failures.

    Preserves original exception details and provides categorized error types
    for caller-specific recovery logic.

    Attributes:
        error_type: Category of the failure (enum)
        context: Human-readable description of what was attempted
        original_exception: The underlying exception that caused the failure
        status_code: HTTP status code (if applicable)
        response_text: API response text (if applicable)
    """

    def __init__(
        self,
        error_type: RemoteTranscriptionErrorType,
        context: str,
        original_exception: Exception | None = None,
        status_code: int | None = None,
        response_text: str | None = None,
    ) -> None:
        """Initialize RemoteTranscriptionError with structured context.

        Args:
            error_type: Category of the failure
            context: Human-readable description of what failed
            original_exception: The underlying exception (preserved via __cause__)
            status_code: HTTP status code (if applicable)
            response_text: API response body (if applicable)
        """
        self.error_type = error_type
        self.context = context
        self.original_exception = original_exception
        self.status_code = status_code
        self.response_text = response_text

        # Build user-facing message
        message = f"{context}"
        if status_code is not None:
            message = f"{message} (HTTP {status_code})"
        if original_exception is not None:
            message = f"{message}: {original_exception}"

        super().__init__(message)

        # Preserve exception chain for debugging
        if original_exception is not None:
            self.__cause__ = original_exception

    def is_retryable(self) -> bool:
        """Determine if the error represents a transient failure.

        Returns:
            True if operation might succeed on retry, False for permanent errors
        """
        retryable_types = {
            RemoteTranscriptionErrorType.NETWORK_TIMEOUT,
            RemoteTranscriptionErrorType.CONNECTION_FAILED,
        }
        return self.error_type in retryable_types

    def __repr__(self) -> str:
        """Return detailed representation for debugging."""
        return (
            f"RemoteTranscriptionError(type={self.error_type.value}, "
            f"context={self.context!r}, status_code={self.status_code})"
        )


class RemoteTranscriber:
    """Remote transcriber that sends audio to a configurable HTTP endpoint."""

    def __init__(
        self,
        endpoint: str,
        api_key: str = "",
        timeout: float = 30.0,
        model: str = "",
    ) -> None:
        """Initialize the remote transcriber.

        Args:
            endpoint: URL of the transcription endpoint
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds (default: 30.0)
            model: Optional model identifier for the remote API
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
        self.model = model
        self.provider = "RemoteAPI"
        self.provider_detected = "RemoteAPI"
        self.provider_requested = "RemoteAPI"
        logger.info(f"Remote transcriber initialized with endpoint: {endpoint}")

    def warmup(self) -> None:
        """Warmup is not needed for remote transcription."""
        logger.info("Remote transcriber warmup (no-op)")

    def _get_audio_duration_ms(self, audio_path: Path) -> float:
        """Calculate the duration of an audio file in milliseconds.

        Args:
            audio_path: Path to audio file (WAV format)

        Returns:
            Duration in milliseconds

        Raises:
            Exception: If audio file cannot be read
        """
        try:
            with wave.open(str(audio_path), "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration_seconds = frames / float(rate)
                return duration_seconds * 1000
        except Exception as e:
            logger.warning(f"Could not determine audio duration: {e}")
            return 0.0

    def transcribe_file(self, audio_path: str | Path) -> TranscriptionResult:
        """Transcribe an audio file via remote API.

        Args:
            audio_path: Path to audio file (WAV format recommended)

        Returns:
            TranscriptionResult with text and timing information

        Raises:
            FileNotFoundError: If audio file doesn't exist
            RemoteTranscriptionError: If transcription fails (categorized by type)
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing {audio_path.name} via remote API...")

        # Calculate duration from audio file, not HTTP request time
        duration_ms = self._get_audio_duration_ms(audio_path)

        start_time = time.time()

        try:
            headers: dict[str, str] = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            with open(audio_path, "rb") as audio_file:
                files = {"file": (audio_path.name, audio_file, "audio/wav")}
                data = {}
                if self.model:
                    data["model"] = self.model
                response = requests.post(
                    self.endpoint,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=self.timeout,
                )

            request_time_ms = (time.time() - start_time) * 1000

            if response.status_code != 200:
                logger.error(
                    "Remote API returned non-200 status",
                    extra={
                        "status_code": response.status_code,
                        "response_preview": response.text[:500],
                    },
                )
                raise RemoteTranscriptionError(
                    error_type=RemoteTranscriptionErrorType.HTTP_ERROR,
                    context="Remote API returned error",
                    status_code=response.status_code,
                    response_text=response.text[:500],
                )

            text = self._extract_text_from_response(response.json())

            logger.info(
                f"Remote transcription completed in {request_time_ms:.0f} ms: "
                f"'{text[:50]}...' (audio duration: {duration_ms:.0f} ms)"
            )

            return TranscriptionResult(
                text=text,
                duration_ms=duration_ms,
                model_name="RemoteAPI",
            )

        except RemoteTranscriptionError:
            # Already properly categorized, re-raise as-is
            raise
        except requests.exceptions.Timeout as e:
            logger.warning(
                "Remote API request timed out",
                extra={"timeout_seconds": self.timeout},
                exc_info=e,
            )
            raise RemoteTranscriptionError(
                error_type=RemoteTranscriptionErrorType.NETWORK_TIMEOUT,
                context=f"Remote API request timed out after {self.timeout}s",
                original_exception=e,
            ) from e
        except requests.exceptions.ConnectionError as e:
            logger.warning(
                "Failed to connect to remote API",
                extra={"endpoint": self.endpoint},
                exc_info=e,
            )
            raise RemoteTranscriptionError(
                error_type=RemoteTranscriptionErrorType.CONNECTION_FAILED,
                context="Failed to connect to remote API",
                original_exception=e,
            ) from e
        except requests.exceptions.RequestException as e:
            logger.error(
                "Remote API request failed",
                extra={"endpoint": self.endpoint},
                exc_info=e,
            )
            raise RemoteTranscriptionError(
                error_type=RemoteTranscriptionErrorType.UNKNOWN,
                context="Remote API request failed",
                original_exception=e,
            ) from e
        except Exception as e:
            logger.error(
                "Unexpected error during remote transcription",
                exc_info=e,
            )
            raise RemoteTranscriptionError(
                error_type=RemoteTranscriptionErrorType.UNKNOWN,
                context="Unexpected error during remote transcription",
                original_exception=e,
            ) from e

    def _extract_text_from_response(self, response_data: Any) -> str:
        """Extract transcription text from API response.

        Supports common response formats:
        - {"text": "transcription"}
        - {"transcription": "transcription"}
        - {"result": "transcription"}
        - {"results": [{"text": "transcription"}]}
        - {"data": {"text": "transcription"}}

        Args:
            response_data: Parsed JSON response from API

        Returns:
            Extracted transcription text

        Raises:
            RemoteTranscriptionError: If text cannot be extracted or format invalid
        """
        if not isinstance(response_data, dict):
            response_type = type(response_data).__name__
            logger.error(
                "Unexpected response type",
                extra={"expected": "dict", "got": response_type},
            )
            raise RemoteTranscriptionError(
                error_type=RemoteTranscriptionErrorType.FORMAT_ERROR,
                context=f"API response must be JSON object, got {response_type}",
                response_text=str(response_data)[:500],
            )

        # Try common top-level keys
        for key in ["text", "transcription", "result"]:
            if key in response_data and isinstance(response_data[key], str):
                return response_data[key]

        # Try results array
        if "results" in response_data:
            results = response_data["results"]
            if isinstance(results, list) and len(results) > 0:
                first_result = results[0]
                if isinstance(first_result, dict):
                    for key in ["text", "transcription"]:
                        if key in first_result and isinstance(first_result[key], str):
                            return first_result[key]
                elif isinstance(first_result, str):
                    return first_result

        # Try nested data object
        if "data" in response_data and isinstance(response_data["data"], dict):
            data = response_data["data"]
            for key in ["text", "transcription", "result"]:
                if key in data and isinstance(data[key], str):
                    return data[key]

        # If we get here, couldn't find text in any expected format
        logger.error(
            "Could not extract text from response",
            extra={
                "response_keys": list(response_data.keys()),
                "response_sample": str(response_data)[:500],
            },
        )
        raise RemoteTranscriptionError(
            error_type=RemoteTranscriptionErrorType.PARSE_ERROR,
            context="API response does not contain transcription text",
            response_text=str(response_data)[:500],
        )
