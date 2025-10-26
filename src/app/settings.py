"""Persistent application settings and convenience helpers."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Optional

SETTINGS_ENV_VAR = "HOPPY_WHISPER_SETTINGS_PATH"


@dataclass
class AppSettings:
    """User-adjustable settings persisted to disk."""

    hotkey_chord: str = "CTRL+SHIFT+;"
    paste_window_seconds: float = 2.0
    start_with_windows: bool = False
    first_run_complete: bool = False
    cleanup_mode: str = "standard"
    cleanup_enabled: bool = True
    auto_paste: bool = True
    history_retention_days: int = 90
    telemetry_enabled: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the settings to a dictionary."""
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "AppSettings":
        """Create a settings instance from a dictionary payload."""
        data = dict(payload)
        if "hotkey_chord" in data and isinstance(data["hotkey_chord"], str):
            data["hotkey_chord"] = data["hotkey_chord"].upper()
        if "paste_window_seconds" in data:
            data["paste_window_seconds"] = float(data["paste_window_seconds"])
        return cls(
            **{
                field: data.get(field, getattr(cls, field))
                for field in cls.__annotations__
            }
        )

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "AppSettings":
        """Load settings from disk, falling back to defaults."""
        settings_path = path or default_settings_path()
        if settings_path.is_file():
            try:
                payload = json.loads(settings_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                payload = {}
            return cls.from_dict(payload)
        return cls()

    def save(self, path: Optional[Path] = None) -> None:
        """Persist the settings to disk."""
        settings_path = path or default_settings_path()
        settings_path.parent.mkdir(parents=True, exist_ok=True)
        serialized = json.dumps(self.to_dict(), indent=2, sort_keys=True)
        settings_path.write_text(serialized, encoding="utf-8")


def default_settings_path() -> Path:
    """Resolve the path used to persist settings."""
    # Use explicit env var when provided
    override = os.getenv(SETTINGS_ENV_VAR)
    if override:
        return Path(override)
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / "AppData" / "Local"
    return base / "Hoppy Whisper" / "settings.json"


def default_history_db_path() -> Path:
    """Resolve the default path for the history database."""
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / "AppData" / "Local"
    return base / "Hoppy Whisper" / "history.db"


def default_metrics_log_path() -> Path:
    """Resolve the default path for performance metrics log."""
    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        base = Path(local_app_data)
    else:
        base = Path.home() / "AppData" / "Local"
    return base / "Hoppy Whisper" / "metrics.log"
