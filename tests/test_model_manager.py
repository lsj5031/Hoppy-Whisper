"""Tests for model asset manager."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.transcriber.model_manager import ModelAsset, ModelManager, ModelManifest


@pytest.fixture
def temp_cache(tmp_path: Path) -> Path:
    """Create a temporary cache directory."""
    cache = tmp_path / "models"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


@pytest.fixture
def test_manifest() -> ModelManifest:
    """Create a test manifest with small dummy files."""
    return ModelManifest(
        encoder=ModelAsset(
            name="encoder.onnx",
            url="https://example.com/encoder.onnx",
            sha256="",
            size_bytes=0,
        ),
        decoder=ModelAsset(
            name="decoder.onnx",
            url="https://example.com/decoder.onnx",
            sha256="",
            size_bytes=0,
        ),
        vocab=ModelAsset(
            name="vocab.json",
            url="https://example.com/vocab.json",
            sha256="",
            size_bytes=0,
        ),
    )


def test_model_manager_init(temp_cache: Path, test_manifest: ModelManifest) -> None:
    """Test model manager initialization."""
    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)
    assert manager.cache_dir == temp_cache
    assert manager.manifest == test_manifest


def test_model_manager_default_cache_dir() -> None:
    """Test default cache directory resolution."""
    manager = ModelManager()
    assert manager.cache_dir.exists()
    assert "Parakeet" in str(manager.cache_dir)
    assert "models" in str(manager.cache_dir)


def test_get_model_path(temp_cache: Path, test_manifest: ModelManifest) -> None:
    """Test model path resolution."""
    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)
    encoder_path = manager.get_model_path(test_manifest.encoder)
    assert encoder_path == temp_cache / "encoder.onnx"


def test_is_downloaded_missing_file(
    temp_cache: Path, test_manifest: ModelManifest
) -> None:
    """Test is_downloaded returns False for missing files."""
    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)
    assert not manager.is_downloaded(test_manifest.encoder)


def test_is_downloaded_existing_file(
    temp_cache: Path, test_manifest: ModelManifest
) -> None:
    """Test is_downloaded returns True for existing files."""
    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)
    encoder_path = manager.get_model_path(test_manifest.encoder)
    encoder_path.write_bytes(b"dummy data")
    assert manager.is_downloaded(test_manifest.encoder)


def test_is_downloaded_size_validation(
    temp_cache: Path, test_manifest: ModelManifest
) -> None:
    """Test size validation during is_downloaded check."""
    test_manifest.encoder.size_bytes = 100
    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)

    encoder_path = manager.get_model_path(test_manifest.encoder)
    encoder_path.write_bytes(b"wrong size")

    assert not manager.is_downloaded(test_manifest.encoder)


def test_is_downloaded_hash_validation(
    temp_cache: Path, test_manifest: ModelManifest
) -> None:
    """Test SHA256 validation during is_downloaded check."""
    content = b"test content"
    expected_hash = hashlib.sha256(content).hexdigest()

    test_manifest.encoder.sha256 = expected_hash
    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)

    encoder_path = manager.get_model_path(test_manifest.encoder)
    encoder_path.write_bytes(content)

    assert manager.is_downloaded(test_manifest.encoder)


def test_is_downloaded_hash_mismatch(
    temp_cache: Path, test_manifest: ModelManifest
) -> None:
    """Test hash mismatch detection."""
    test_manifest.encoder.sha256 = "0" * 64
    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)

    encoder_path = manager.get_model_path(test_manifest.encoder)
    encoder_path.write_bytes(b"wrong content")

    assert not manager.is_downloaded(test_manifest.encoder)


def test_compute_sha256(temp_cache: Path, test_manifest: ModelManifest) -> None:
    """Test SHA256 computation."""
    content = b"test data"
    expected = hashlib.sha256(content).hexdigest()

    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)
    test_file = temp_cache / "test.bin"
    test_file.write_bytes(content)

    actual = manager._compute_sha256(test_file)
    assert actual == expected


@patch("app.transcriber.model_manager.urlopen")
def test_download_asset_success(
    mock_urlopen: MagicMock, temp_cache: Path, test_manifest: ModelManifest
) -> None:
    """Test successful asset download."""
    content = b"model data"

    mock_response = MagicMock()
    mock_response.headers.get.return_value = str(len(content))
    mock_response.read.side_effect = [content, b""]
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    mock_urlopen.return_value = mock_response

    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)
    path = manager.download_asset(test_manifest.encoder, max_retries=1)

    assert path.exists()
    assert path.read_bytes() == content


@patch("app.transcriber.model_manager.urlopen")
def test_download_asset_already_cached(
    mock_urlopen: MagicMock, temp_cache: Path, test_manifest: ModelManifest
) -> None:
    """Test skipping download for already cached files."""
    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)
    encoder_path = manager.get_model_path(test_manifest.encoder)
    encoder_path.write_bytes(b"cached data")

    path = manager.download_asset(test_manifest.encoder)

    assert path == encoder_path
    mock_urlopen.assert_not_called()


@patch("app.transcriber.model_manager.urlopen")
def test_download_asset_retry_on_failure(
    mock_urlopen: MagicMock, temp_cache: Path, test_manifest: ModelManifest
) -> None:
    """Test retry logic on download failure."""
    mock_urlopen.side_effect = Exception("Network error")

    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)

    with pytest.raises(RuntimeError, match="Failed to download encoder.onnx after 2"):
        manager.download_asset(test_manifest.encoder, max_retries=2)

    assert mock_urlopen.call_count == 2


def test_get_models_info(temp_cache: Path, test_manifest: ModelManifest) -> None:
    """Test models info retrieval."""
    manager = ModelManager(cache_dir=temp_cache, manifest=test_manifest)

    encoder_path = manager.get_model_path(test_manifest.encoder)
    encoder_path.write_bytes(b"data")

    info = manager.get_models_info()

    assert info["cache_dir"] == str(temp_cache)
    assert info["encoder"]["downloaded"] is True
    assert info["decoder"]["downloaded"] is False
    assert info["vocab"]["downloaded"] is False


def test_get_model_manager_singleton() -> None:
    """Test singleton pattern for get_model_manager."""
    from app.transcriber.model_manager import get_model_manager

    manager1 = get_model_manager()
    manager2 = get_model_manager()

    assert manager1 is manager2
