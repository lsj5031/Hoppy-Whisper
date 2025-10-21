"""Windows startup registration helpers."""

from __future__ import annotations

import contextlib
import sys
from pathlib import Path
from typing import Generator, Optional

RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"

try:  # pragma: no cover - exercised in tests via monkeypatch
    import winreg
except ModuleNotFoundError:  # pragma: no cover - non-Windows environments
    winreg = None  # type: ignore[assignment]


class StartupError(RuntimeError):
    """Raised when Windows startup registration fails."""


def resolve_startup_command(module: str = "app") -> str:
    """Return the command used when launching at login."""
    if getattr(sys, "frozen", False):
        return f'"{Path(sys.executable).resolve()}"'
    python_exe = Path(sys.executable).resolve()
    return f'"{python_exe}" -m {module}'


def enable_startup(app_name: str, command: str) -> None:
    """Register the app to launch at login via HKCU."""
    _ensure_winreg()
    try:
        with _run_key(write=True, create_if_missing=True) as key:
            winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
    except OSError as exc:  # pragma: no cover - error path validated in production
        raise StartupError(f"Failed to enable startup for {app_name}") from exc


def disable_startup(app_name: str) -> None:
    """Remove the app from the login start list."""
    _ensure_winreg()
    try:
        with _run_key(write=True, create_if_missing=False) as key:
            if key is None:
                return
            try:
                winreg.DeleteValue(key, app_name)
            except FileNotFoundError:
                return
    except OSError as exc:  # pragma: no cover - defensive
        raise StartupError(f"Failed to disable startup for {app_name}") from exc


def is_startup_enabled(app_name: str, expected_command: str | None = None) -> bool:
    """Check whether the registry currently holds the startup entry."""
    _ensure_winreg()
    try:
        with _run_key(write=False, create_if_missing=False) as key:
            if key is None:
                return False
            value, _ = winreg.QueryValueEx(key, app_name)
    except FileNotFoundError:
        return False
    except OSError:  # pragma: no cover - defensive
        return False
    if expected_command is None:
        return True
    return str(value).strip() == expected_command.strip()


@contextlib.contextmanager
def _run_key(
    *, write: bool, create_if_missing: bool
) -> Generator[Optional[object], None, None]:
    """Context manager returning the Run registry key handle."""
    key = None
    if write:
        access = winreg.KEY_SET_VALUE | winreg.KEY_CREATE_SUB_KEY  # type: ignore[operator]
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, access)
        except FileNotFoundError:
            if create_if_missing:
                key = winreg.CreateKeyEx(
                    winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, access
                )
            else:
                key = None
    else:
        access = winreg.KEY_READ  # type: ignore[assignment]
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY_PATH, 0, access)
    try:
        yield key
    finally:
        if key:
            winreg.CloseKey(key)


def _ensure_winreg() -> None:
    if winreg is None:
        raise StartupError("Windows registry is unavailable on this platform")


__all__ = [
    "StartupError",
    "disable_startup",
    "enable_startup",
    "is_startup_enabled",
    "resolve_startup_command",
]
