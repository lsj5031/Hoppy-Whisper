"""Basic package import smoke tests."""


def test_app_imports() -> None:
    """Ensure the top-level package metadata is importable."""
    import app  # noqa: PLC0415

    assert hasattr(app, "__all__")
