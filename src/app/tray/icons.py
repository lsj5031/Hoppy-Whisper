"""Icon generation helpers for the Parakeet tray application."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from functools import lru_cache
from typing import Dict, Iterable, Tuple

from PIL import Image, ImageDraw

from .state import TrayState

ICON_SIZES: Tuple[int, ...] = (16, 20, 24, 32, 40, 48, 64)
SPINNER_FRAMES = 12


class TrayTheme(str, Enum):
    """Supported tray icon themes."""

    LIGHT = "light"
    DARK = "dark"


@dataclass(frozen=True)
class _IconKey:
    state: TrayState
    theme: TrayTheme
    size: int
    frame: int


class TrayIconFactory:
    """Generates and caches Pillow images for tray icon states."""

    def __init__(
        self, sizes: Iterable[int] = ICON_SIZES, spinner_frames: int = SPINNER_FRAMES
    ) -> None:
        self._sizes = tuple(sorted(set(sizes)))
        self._spinner_frames = spinner_frames

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

    @lru_cache(maxsize=256)
    def _load_frame(self, key: _IconKey) -> Image.Image:
        """Generate the icon for the supplied cache key."""
        size = key.size
        background, border, accents = _palette_for_theme(key.theme)
        image = Image.new("RGBA", (size, size), background)
        draw = ImageDraw.Draw(image)

        inset = max(1, size // 16)
        bounds = (inset, inset, size - inset, size - inset)

        draw.ellipse(bounds, outline=border, width=max(1, size // 16))

        if key.state is TrayState.IDLE:
            _draw_idle(draw, bounds, accents, size)
        elif key.state is TrayState.LISTENING:
            _draw_listening(draw, bounds, accents, size)
        elif key.state is TrayState.TRANSCRIBING:
            _draw_spinner(
                draw, bounds, accents, border, size, key.frame, self._spinner_frames
            )
        elif key.state is TrayState.COPIED:
            _draw_checkmark(draw, bounds, accents, size)
        elif key.state is TrayState.PASTED:
            _draw_paste_arrow(draw, bounds, accents, size)
        elif key.state is TrayState.ERROR:
            _draw_error(draw, bounds, accents, size)
        else:  # pragma: no cover - defensive
            raise ValueError(f"Unhandled tray state {key.state}")

        return image


def _palette_for_theme(
    theme: TrayTheme,
) -> Tuple[
    Tuple[int, int, int, int],
    Tuple[int, int, int, int],
    Dict[str, Tuple[int, int, int, int]],
]:
    if theme is TrayTheme.DARK:
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


def _draw_idle(
    draw: ImageDraw.ImageDraw,
    bounds: Tuple[int, int, int, int],
    accents: Dict[str, Tuple[int, int, int, int]],
    size: int,
) -> None:
    radius = size // 6
    center = size // 2
    draw.ellipse(
        (center - radius, center - radius, center + radius, center + radius),
        fill=accents["idle"],
    )


def _draw_listening(
    draw: ImageDraw.ImageDraw,
    bounds: Tuple[int, int, int, int],
    accents: Dict[str, Tuple[int, int, int, int]],
    size: int,
) -> None:
    bar_width = max(1, size // 12)
    gap = bar_width
    base = bounds[0] + (bounds[2] - bounds[0]) // 2
    heights = (size * 0.55, size * 0.8, size * 0.65)
    for idx, height in enumerate(heights):
        x = base + (idx - 1) * (bar_width + gap)
        draw.rounded_rectangle(
            (
                x - bar_width,
                size / 2 - height / 2,
                x + bar_width,
                size / 2 + height / 2,
            ),
            radius=bar_width,
            fill=accents["listening"],
        )


def _draw_spinner(
    draw: ImageDraw.ImageDraw,
    bounds: Tuple[int, int, int, int],
    accents: Dict[str, Tuple[int, int, int, int]],
    border: Tuple[int, int, int, int],
    size: int,
    frame: int,
    total_frames: int,
) -> None:
    thickness = max(2, size // 12)
    inner_inset = thickness * 3 // 2
    inner = (
        bounds[0] + inner_inset,
        bounds[1] + inner_inset,
        bounds[2] - inner_inset,
        bounds[3] - inner_inset,
    )
    draw.ellipse(inner, outline=border, width=thickness)
    sweep = 360 / 6
    start_angle = (frame / total_frames) * 360
    end_angle = start_angle + sweep
    draw.pieslice(inner, start=start_angle, end=end_angle, fill=accents["spinner"])


def _draw_checkmark(
    draw: ImageDraw.ImageDraw,
    bounds: Tuple[int, int, int, int],
    accents: Dict[str, Tuple[int, int, int, int]],
    size: int,
) -> None:
    thickness = max(2, size // 10)
    points = [
        (bounds[0] + size * 0.25, bounds[1] + size * 0.55),
        (bounds[0] + size * 0.42, bounds[1] + size * 0.72),
        (bounds[0] + size * 0.75, bounds[1] + size * 0.32),
    ]
    draw.line(points, fill=accents["copied"], width=thickness, joint="curve")


def _draw_paste_arrow(
    draw: ImageDraw.ImageDraw,
    bounds: Tuple[int, int, int, int],
    accents: Dict[str, Tuple[int, int, int, int]],
    size: int,
) -> None:
    arrow_width = max(2, size // 8)
    center_x = size // 2
    tip_y = bounds[3] - size * 0.2
    stem_top = bounds[1] + size * 0.3
    draw.line(
        [(center_x, stem_top), (center_x, tip_y)],
        fill=accents["pasted"],
        width=arrow_width,
    )
    half_span = size * 0.18
    draw.polygon(
        [
            (center_x - half_span, tip_y - arrow_width),
            (center_x + half_span, tip_y - arrow_width),
            (center_x, bounds[3] - size * 0.08),
        ],
        fill=accents["pasted"],
    )


def _draw_error(
    draw: ImageDraw.ImageDraw,
    bounds: Tuple[int, int, int, int],
    accents: Dict[str, Tuple[int, int, int, int]],
    size: int,
) -> None:
    thickness = max(2, size // 10)
    margin = size * 0.3
    draw.line(
        [
            (bounds[0] + margin, bounds[1] + margin),
            (bounds[2] - margin, bounds[3] - margin),
        ],
        fill=accents["error"],
        width=thickness,
    )
    draw.line(
        [
            (bounds[2] - margin, bounds[1] + margin),
            (bounds[0] + margin, bounds[3] - margin),
        ],
        fill=accents["error"],
        width=thickness,
    )
