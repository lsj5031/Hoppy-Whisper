"""Model asset manager for downloading and caching ASR models."""

from __future__ import annotations

import hashlib
import logging
import sys
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any


# Expose urlopen at module scope for test patching; wrapper forwards to urllib
def urlopen(*args, **kwargs):  # type: ignore[override]
    return urllib.request.urlopen(*args, **kwargs)

logger = logging.getLogger(__name__)


@dataclass
class ModelAsset:
    """Information about a model asset file."""

    name: str
    url: str
    sha256: str
    size_bytes: int


@dataclass
class ModelManifest:
    """Manifest of all required model assets."""

    encoder: ModelAsset
    decoder: ModelAsset
    vocab: ModelAsset
    extra_assets: tuple[ModelAsset, ...] = ()


DEFAULT_MANIFEST = ModelManifest(
    encoder=ModelAsset(
        name="encoder-model.int8.onnx",
        url=(
            "https://huggingface.co/istupakov/"
            "parakeet-tdt-0.6b-v3-onnx/resolve/main/encoder-model.int8.onnx"
        ),
        sha256="",
        size_bytes=0,
    ),
    decoder=ModelAsset(
        name="decoder_joint-model.int8.onnx",
        url=(
            "https://huggingface.co/istupakov/"
            "parakeet-tdt-0.6b-v3-onnx/resolve/main/decoder_joint-model.int8.onnx"
        ),
        sha256="",
        size_bytes=0,
    ),
    vocab=ModelAsset(
        name="vocab.txt",
        url=(
            "https://huggingface.co/istupakov/"
            "parakeet-tdt-0.6b-v3-onnx/resolve/main/vocab.txt"
        ),
        sha256="",
        size_bytes=0,
    ),
    extra_assets=(
        ModelAsset(
            name="nemo128.onnx",
            url=(
                "https://huggingface.co/istupakov/"
                "parakeet-tdt-0.6b-v3-onnx/resolve/main/nemo128.onnx"
            ),
            sha256="",
            size_bytes=0,
        ),
    ),
)


class ModelManager:
    """Manages model asset downloading, caching, and validation."""

    def __init__(
        self,
        cache_dir: Path | None = None,
        manifest: ModelManifest | None = None,
    ) -> None:
        """Initialize the model manager.

        Args:
            cache_dir: Directory for cached models. Defaults to
                %LOCALAPPDATA%/Hoppy Whisper/models
            manifest: Model manifest. Defaults to TDT 0.6b
        """
        if cache_dir is None:
            import os

            app_data = Path(os.environ.get("LOCALAPPDATA", "~/.local/share"))
            cache_dir = app_data / "Hoppy Whisper" / "models"

        self.cache_dir = cache_dir.expanduser().resolve()
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.manifest = manifest or DEFAULT_MANIFEST

        logger.info(f"Model cache directory: {self.cache_dir}")

    def _bundled_model_path(self, asset: ModelAsset) -> Path | None:
        """Return path to bundled asset when running from a frozen build."""
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            p = Path(sys._MEIPASS) / "models" / asset.name
            if p.exists():
                return p
        return None

    def get_model_path(self, asset: ModelAsset) -> Path:
        """Get the preferred local path for a model asset.

        In frozen builds, prefer bundled models under sys._MEIPASS/models.
        Otherwise, use the writable cache directory.
        """
        bundled = self._bundled_model_path(asset)
        return bundled if bundled is not None else (self.cache_dir / asset.name)

    def is_downloaded(self, asset: ModelAsset) -> bool:
        """Check if a model asset is already downloaded."""
        path = self.get_model_path(asset)
        if not path.exists():
            return False

        # Validate size if specified
        if asset.size_bytes > 0:
            actual_size = path.stat().st_size
            if actual_size != asset.size_bytes:
                logger.warning(
                    f"{asset.name} size mismatch: expected {asset.size_bytes}, "
                    f"got {actual_size}"
                )
                return False

        # Validate SHA256 if specified
        if asset.sha256:
            actual_hash = self._compute_sha256(path)
            if actual_hash != asset.sha256.lower():
                logger.warning(
                    f"{asset.name} hash mismatch: expected {asset.sha256}, "
                    f"got {actual_hash}"
                )
                return False

        return True

    def _compute_sha256(self, path: Path) -> str:
        """Compute SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def download_asset(
        self,
        asset: ModelAsset,
        progress_callback: Any = None,
        max_retries: int = 3,
    ) -> Path:
        """Download a model asset with retry and validation.

        Args:
            asset: The asset to download
            progress_callback: Optional callback(downloaded_bytes, total_bytes)
            max_retries: Maximum number of retry attempts

        Returns:
            Path to the downloaded file

        Raises:
            RuntimeError: If download fails after all retries
        """
        path = self.get_model_path(asset)

        # Check if already valid
        if self.is_downloaded(asset):
            logger.info(f"{asset.name} already downloaded and valid")
            return path

        logger.info(f"Downloading {asset.name} from {asset.url}")

        for attempt in range(max_retries):
            try:
                self._download_with_progress(asset, path, progress_callback)

                # Validate after download
                if asset.size_bytes > 0:
                    actual_size = path.stat().st_size
                    if actual_size != asset.size_bytes:
                        raise ValueError(
                            f"Size mismatch: expected {asset.size_bytes}, "
                            f"got {actual_size}"
                        )

                if asset.sha256:
                    actual_hash = self._compute_sha256(path)
                    if actual_hash != asset.sha256.lower():
                        raise ValueError(
                            f"Hash mismatch: expected {asset.sha256}, got {actual_hash}"
                        )

                logger.info(f"Successfully downloaded and validated {asset.name}")
                return path

            except Exception as e:
                logger.warning(f"Download attempt {attempt + 1} failed: {e}")
                if path.exists():
                    path.unlink()

                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"Failed to download {asset.name} after {max_retries} attempts"
                    ) from e

                # Exponential backoff
                import time

                backoff_seconds = 2 ** (attempt + 1)
                logger.info(f"Retrying in {backoff_seconds} seconds...")
                time.sleep(backoff_seconds)

        raise RuntimeError(f"Failed to download {asset.name}")

    def _download_with_progress(
        self,
        asset: ModelAsset,
        path: Path,
        progress_callback: Any = None,
    ) -> None:
        """Download a file with optional progress tracking."""
        request = urllib.request.Request(asset.url)
        request.add_header("User-Agent", "HoppyWhisper/0.1.0")

        with urlopen(request, timeout=30) as response:
            total_size = int(response.headers.get("Content-Length", 0))
            downloaded = 0

            with open(path, "wb") as f:
                while True:
                    chunk = response.read(8192)
                    if not chunk:
                        break

                    f.write(chunk)
                    downloaded += len(chunk)

                    if progress_callback:
                        progress_callback(downloaded, total_size or downloaded)

    def ensure_models(
        self,
        progress_callback: Any = None,
    ) -> tuple[Path, Path, Path]:
        """Ensure all required models are downloaded and valid.

        Args:
            progress_callback: Optional callback(asset_name, downloaded_bytes,
                total_bytes)

        Returns:
            Tuple of (encoder_path, decoder_path, vocab_path)

        Raises:
            RuntimeError: If any model fails to download
        """
        def _resolve(asset: ModelAsset, tag: str) -> Path:
            bundled = self._bundled_model_path(asset)
            if bundled is not None:
                logger.info(f"Using bundled model: {asset.name}")
                return bundled
            return self.download_asset(
                asset,
                lambda d, t: (
                    progress_callback(tag, d, t) if progress_callback else None
                ),
            )

        encoder_path = _resolve(self.manifest.encoder, "encoder")
        decoder_path = _resolve(self.manifest.decoder, "decoder")
        vocab_path = _resolve(self.manifest.vocab, "vocab")

        for extra in self.manifest.extra_assets:
            _ = _resolve(extra, extra.name)

        return encoder_path, decoder_path, vocab_path

    def get_models_info(self) -> dict[str, Any]:
        """Get information about the current models."""
        return {
            "cache_dir": str(self.cache_dir),
            "encoder": {
                "name": self.manifest.encoder.name,
                "downloaded": self.is_downloaded(self.manifest.encoder),
                "path": str(self.get_model_path(self.manifest.encoder)),
            },
            "decoder": {
                "name": self.manifest.decoder.name,
                "downloaded": self.is_downloaded(self.manifest.decoder),
                "path": str(self.get_model_path(self.manifest.decoder)),
            },
            "vocab": {
                "name": self.manifest.vocab.name,
                "downloaded": self.is_downloaded(self.manifest.vocab),
                "path": str(self.get_model_path(self.manifest.vocab)),
            },
        }


_model_manager: ModelManager | None = None


def get_model_manager(cache_dir: Path | None = None) -> ModelManager:
    """Get or create the global model manager singleton."""
    global _model_manager
    if _model_manager is None:
        _model_manager = ModelManager(cache_dir=cache_dir)
    return _model_manager
