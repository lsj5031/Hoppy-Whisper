"""Icon helpers for the Hoppy Whisper tray application.

Loads artist-provided bunny ICOs from an "icos" folder (if present). Animated
transcription uses multiple BunnyTranscribe*.ico frames when available.
No more programmatic shape drawing is used.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from PIL import Image

from .state import TrayState

ICON_SIZES: Tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64)
SPINNER_FRAMES = 12


class TrayTheme(str, Enum):
    """Supported tray icon themes."""

    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"


@dataclass(frozen=True)
class _IconKey:
    state: TrayState
    theme: TrayTheme
    size: int
    frame: int


class TrayIconFactory:
    """Generates and caches Pillow images for tray icon states."""

    def __init__(
        self,
        sizes: Iterable[int] = ICON_SIZES,
        spinner_frames: Optional[int] = None,
    ) -> None:
        self._sizes = tuple(sorted(set(sizes)))
        # Discover bunny ICO assets (if present)
        self._icons_dir: Optional[Path] = _resolve_icons_dir()
        self._idle_icon: Optional[Path] = None
        self._listening_icon: Optional[Path] = None
        self._transcribe_frames: List[Path] = []

        if self._icons_dir:
            self._idle_icon = _optional_file(self._icons_dir, "BunnyStandby.ico")
            # Prefer a specific listening icon; fall back to standby if absent
            self._listening_icon = (
                _optional_file(self._icons_dir, "BunnyStandby.ico")
                or _optional_file(self._icons_dir, "BunnyPause.ico")
            )
            self._transcribe_frames = _transcribe_frame_files(self._icons_dir)

        detected_frames = len(self._transcribe_frames)
        if spinner_frames is not None:
            self._spinner_frames = spinner_frames
        else:
            self._spinner_frames = detected_frames if detected_frames > 0 else 1

    @property
    def sizes(self) -> Tuple[int, ...]:
        """Return the available icon sizes."""
        return self._sizes

    @property
    def spinner_frames(self) -> int:
        """Return the number of animation frames used for the spinner."""
        return self._spinner_frames

    def frame(
        self,
        state: TrayState,
        theme: TrayTheme,
        size: int,
        frame: int = 0,
    ) -> Image.Image:
        """Fetch a Pillow image for the requested state/frame combination."""
        if size not in self._sizes:
            raise ValueError(f"Unsupported tray icon size {size}")
        if state.animated:
            frame %= self._spinner_frames
        else:
            frame = 0
        icon_key = _IconKey(state=state, theme=theme, size=size, frame=frame)
        return self._load_frame(icon_key)

    def state_frames(
        self,
        state: TrayState,
        theme: TrayTheme,
    ) -> Dict[int, Tuple[Image.Image, ...]]:
        """Retrieve all frames for the given state grouped by icon size."""
        frame_count = self._spinner_frames if state.animated else 1
        result: Dict[int, Tuple[Image.Image, ...]] = {}
        for size in self._sizes:
            frames = tuple(
                self.frame(state, theme, size, idx) for idx in range(frame_count)
            )
            result[size] = frames
        return result

    @lru_cache(maxsize=256)  # noqa: B019
    def _load_frame(self, key: _IconKey) -> Image.Image:
        """Load the icon image for the given state/frame.

        Uses ICO assets only; falls back to a transparent placeholder when
        specific assets are missing to keep the tray responsive.
        """
        # Transcribing animation frames
        if self._icons_dir and key.state is TrayState.TRANSCRIBING and self._transcribe_frames:
            idx = key.frame % len(self._transcribe_frames)
            img = _open_ico_scaled(self._transcribe_frames[idx], key.size)
            if img is not None:
                return img

        # Static states: map to available assets
        candidate: Optional[Path] = None
        if self._icons_dir:
            if key.state in (TrayState.IDLE, TrayState.LISTENING):
                candidate = self._idle_icon or self._listening_icon
            elif key.state in (TrayState.COPIED, TrayState.PASTED):
                candidate = self._idle_icon or self._listening_icon
            elif key.state is TrayState.ERROR:
                candidate = _optional_file(self._icons_dir, "BunnyPause.ico") or self._idle_icon or self._listening_icon
            if candidate:
                img = _open_ico_scaled(candidate, key.size)
                if img is not None:
                    return img

        # Last resort: transparent placeholder
        return Image.new("RGBA", (key.size, key.size), (0, 0, 0, 0))


# ---------------------------------------------------------------------------
# Bunny ICO asset helpers
# ---------------------------------------------------------------------------

def _resolve_icons_dir() -> Optional[Path]:
    """Locate the icos directory with bunny assets if present.

    Order:
    1) HOPPY_WHISPER_ICONS_DIR env var (legacy alternate also supported)
    2) PyInstaller bundle dir (sys._MEIPASS)/icos
    3) Search upward from this file for a folder named "icos" containing BunnyStandby.ico
    """
    import os
    import sys

    env_dir = os.getenv("HOPPY_WHISPER_ICONS_DIR") or os.getenv("PARAKEET_ICONS_DIR")
    if env_dir:
        p = Path(env_dir)
        if p.is_dir():
            return p

    base = getattr(sys, "_MEIPASS", None)
    if base:
        p = Path(base) / "icos"
        if p.is_dir():
            return p

    here = Path(__file__).resolve()
    for parent in [here.parent, *here.parents]:
        p = parent / "icos"
        if (p / "BunnyStandby.ico").exists():
            return p
    return None


def _optional_file(folder: Path, name: str) -> Optional[Path]:
    path = folder / name
    return path if path.exists() else None


def _transcribe_frame_files(folder: Path) -> List[Path]:
    files = sorted(folder.glob("BunnyTranscribe*.ico"), key=lambda p: _suffix_number(p.name))
    return [p for p in files if p.exists()]


def _suffix_number(name: str) -> int:
    import re

    m = re.search(r"(\d+)(?=\.[^.]+$)", name)
    return int(m.group(1)) if m else 0


def _open_ico_scaled(path: Path, size: int) -> Optional[Image.Image]:
    """Open an ICO and return RGBA image scaled to (size, size)."""
    try:
        with Image.open(path) as im:
            getimage = getattr(im, "getimage", None)
            target = None
            if callable(getimage):
                try:
                    target = getimage((size, size))
                except Exception:
                    target = None
            if target is None:
                target = im.convert("RGBA")
            if target.size != (size, size):
                target = target.resize((size, size), Image.LANCZOS)
            return target.copy()
    except Exception:
        return None


def _palette_for_theme(
    theme: TrayTheme,
) -> Tuple[
    Tuple[int, int, int, int],
    Tuple[int, int, int, int],
    Dict[str, Tuple[int, int, int, int]],
]:
    """Legacy color palette for tests and accessibility checks.

    The app no longer draws programmatic shapes, but tests rely on these
    constants to validate theme accessibility.
    """
    if theme is TrayTheme.HIGH_CONTRAST:
        background = (0, 0, 0, 0)
        border = (255, 255, 255, 255)
        accents = {
            "idle": (0, 255, 255, 255),
            "listening": (255, 255, 0, 255),
            "spinner": (0, 255, 255, 255),
            "copied": (0, 255, 0, 255),
            "pasted": (255, 0, 255, 255),
            "error": (255, 0, 0, 255),
        }
    elif theme is TrayTheme.DARK:
        background = (30, 30, 30, 0)
        border = (230, 230, 230, 255)
        accents = {
            "idle": (120, 200, 255, 255),
            "listening": (255, 170, 0, 255),
            "spinner": (180, 220, 255, 255),
            "copied": (120, 220, 180, 255),
            "pasted": (160, 160, 255, 255),
            "error": (255, 110, 110, 255),
        }
    else:
        background = (255, 255, 255, 0)
        border = (50, 50, 50, 255)
        accents = {
            "idle": (30, 136, 229, 255),
            "listening": (255, 111, 0, 255),
            "spinner": (56, 142, 255, 255),
            "copied": (67, 160, 71, 255),
            "pasted": (123, 31, 162, 255),
            "error": (211, 47, 47, 255),
        }
    return background, border, accents
