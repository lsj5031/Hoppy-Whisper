"""Remote transcription via HTTP API."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Any

import requests  # type: ignore[import-untyped]

from .hoppy import TranscriptionResult

logger = logging.getLogger(__name__)


class RemoteTranscriptionError(Exception):
    """Raised when remote transcription fails."""

    pass


class RemoteTranscriber:
    """Remote transcriber that sends audio to a configurable HTTP endpoint."""

    def __init__(
        self,
        endpoint: str,
        api_key: str = "",
        timeout: float = 30.0,
    ) -> None:
        """Initialize the remote transcriber.

        Args:
            endpoint: URL of the transcription endpoint
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds (default: 30.0)
        """
        self.endpoint = endpoint
        self.api_key = api_key
        self.timeout = timeout
        self.provider = "RemoteAPI"
        self.provider_detected = "RemoteAPI"
        self.provider_requested = "RemoteAPI"
        logger.info(f"Remote transcriber initialized with endpoint: {endpoint}")

    def warmup(self) -> None:
        """Warmup is not needed for remote transcription."""
        logger.info("Remote transcriber warmup (no-op)")

    def transcribe_file(self, audio_path: str | Path) -> TranscriptionResult:
        """Transcribe an audio file via remote API.

        Args:
            audio_path: Path to audio file (WAV format recommended)

        Returns:
            TranscriptionResult with text and timing information

        Raises:
            RemoteTranscriptionError: If transcription fails
        """
        audio_path = Path(audio_path)
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        logger.info(f"Transcribing {audio_path.name} via remote API...")
        start_time = time.time()

        try:
            headers: dict[str, str] = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            with open(audio_path, "rb") as audio_file:
                files = {"audio": (audio_path.name, audio_file, "audio/wav")}
                response = requests.post(
                    self.endpoint,
                    files=files,
                    headers=headers,
                    timeout=self.timeout,
                )

            duration_ms = (time.time() - start_time) * 1000

            if response.status_code != 200:
                error_msg = (
                    f"Remote API returned status {response.status_code}: "
                    f"{response.text[:200]}"
                )
                logger.error(error_msg)
                raise RemoteTranscriptionError(error_msg)

            text = self._extract_text_from_response(response.json())

            logger.info(
                f"Remote transcription completed in {duration_ms:.0f} ms: "
                f"'{text[:50]}...'"
            )

            return TranscriptionResult(
                text=text,
                duration_ms=duration_ms,
                model_name="RemoteAPI",
            )

        except requests.exceptions.Timeout as e:
            error_msg = f"Remote API request timed out after {self.timeout}s"
            logger.error(error_msg)
            raise RemoteTranscriptionError(error_msg) from e
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Failed to connect to remote API: {e}"
            logger.error(error_msg)
            raise RemoteTranscriptionError(error_msg) from e
        except requests.exceptions.RequestException as e:
            error_msg = f"Remote API request failed: {e}"
            logger.error(error_msg)
            raise RemoteTranscriptionError(error_msg) from e
        except Exception as e:
            error_msg = f"Unexpected error during remote transcription: {e}"
            logger.error(error_msg)
            raise RemoteTranscriptionError(error_msg) from e

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
            RemoteTranscriptionError: If text cannot be extracted
        """
        if not isinstance(response_data, dict):
            raise RemoteTranscriptionError(
                f"Unexpected response format: expected dict, got {type(response_data)}"
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

        # If we get here, we couldn't find the text
        raise RemoteTranscriptionError(
            f"Could not extract transcription text from response: {response_data}"
        )
