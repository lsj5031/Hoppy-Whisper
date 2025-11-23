"""High-level controller for the tray icon and context menu."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable, Optional

try:  # pragma: no cover - optional dependency shim for type checking
    import pystray  # type: ignore
except ImportError as exc:  # pragma: no cover - pystray is required at runtime
    raise RuntimeError("pystray must be installed to use the tray controller") from exc

from .icons import TrayIconFactory, TrayTheme
from .state import TrayState

_LOGGER = logging.getLogger(__name__)


@dataclass
class TrayMenuActions:
    """Callbacks invoked by tray menu selections."""

    toggle_recording: Callable[[], None]
    show_settings: Callable[[], None]
    show_history: Callable[[], None]
    restart_app: Callable[[], None]
    set_start_with_windows: Callable[[bool], None]
    quit_app: Callable[[], None]


class TrayController:
    """Manage the tray icon lifecycle, menu, and state transitions."""

    FIRST_RUN_TITLE = "Hoppy Whisper"
    FIRST_RUN_MESSAGE = (
        "Press Ctrl+Shift+; to start recording. "
        "Hold to capture speech, release to stop."
    )

    def __init__(
        self,
        app_name: str,
        menu_actions: TrayMenuActions,
        *,
        icon_factory: Optional[TrayIconFactory] = None,
        theme: Optional[TrayTheme] = None,
        start_with_windows: bool = False,
        show_first_run_tip: bool = False,
    ) -> None:
        self._app_name = app_name
        self._menu_actions = menu_actions
        self._icon_factory = icon_factory or TrayIconFactory()
        self._theme = theme or detect_tray_theme()
        sizes = self._icon_factory.sizes
        self._display_size = 32 if 32 in sizes else sizes[-1]
        self._icon: Optional["pystray.Icon"] = None
        self._state = TrayState.IDLE
        self._spinner_thread: Optional[threading.Thread] = None
        self._spinner_stop = threading.Event()
        self._current_frame = 0
        self._start_with_windows = start_with_windows
        self._show_first_run_tip = show_first_run_tip

    @property
    def icon(self) -> Optional["pystray.Icon"]:
        """Return the underlying pystray icon instance."""
        return self._icon

    @property
    def state(self) -> TrayState:
        """Expose the current tray state."""
        return self._state

    @property
    def start_with_windows_enabled(self) -> bool:
        """Return whether the app should start with Windows."""
        return self._start_with_windows

    def start(self) -> None:
        """Create and display the tray icon."""
        if self._icon is not None:
            return
        menu = self._build_menu()
        image = self._icon_factory.frame(self._state, self._theme, self._display_size)
        icon = pystray.Icon(self._app_name, icon=image, title=self._app_name, menu=menu)
        self._icon = icon
        if self._show_first_run_tip:
            # Notify after the icon is visible to avoid lost toasts.
            icon.notify(self.FIRST_RUN_MESSAGE, self.FIRST_RUN_TITLE)
            self._show_first_run_tip = False
        threading.Thread(target=icon.run, daemon=True).start()

    def stop(self) -> None:
        """Shut down the tray icon and animation loop."""
        self._stop_spinner()
        if self._icon:
            try:
                self._icon.stop()
            except RuntimeError:  # pragma: no cover - pystray quirks
                _LOGGER.debug("pystray stop called after icon closed", exc_info=True)
            self._icon = None

    def set_state(self, state: TrayState) -> None:
        """Update the tray icon to reflect a new state."""
        if state == self._state and (not state.animated or self._spinner_thread):
            return
        self._state = state
        self._current_frame = 0
        self._update_icon_image()
        if state.animated:
            self._start_spinner()
        else:
            self._stop_spinner()

    def toggle_start_with_windows(self) -> None:
        """Flip the start-with-Windows flag and notify callbacks."""
        self._start_with_windows = not self._start_with_windows
        self._menu_actions.set_start_with_windows(self._start_with_windows)
        if self._icon:
            self._icon.update_menu()

    def _start_spinner(self) -> None:
        if self._spinner_thread and self._spinner_thread.is_alive():
            return
        self._spinner_stop.clear()
        self._spinner_thread = threading.Thread(target=self._spin, daemon=True)
        self._spinner_thread.start()

    def _stop_spinner(self) -> None:
        self._spinner_stop.set()
        if self._spinner_thread and self._spinner_thread.is_alive():
            self._spinner_thread.join(timeout=0.2)
        self._spinner_thread = None

    def _spin(self) -> None:
        interval = 0.15
        while not self._spinner_stop.wait(interval):
            self._current_frame = (
                self._current_frame + 1
            ) % self._icon_factory.spinner_frames
            self._update_icon_image(frame=self._current_frame)

    def _update_icon_image(self, frame: int = 0) -> None:
        image = self._icon_factory.frame(
            self._state, self._theme, self._display_size, frame
        )
        if self._icon:
            self._icon.icon = image

    def _build_menu(self) -> "pystray.Menu":
        return pystray.Menu(
            pystray.MenuItem(
                "Toggle Recording", self._wrap(self._menu_actions.toggle_recording)
            ),
            pystray.MenuItem("Settings", self._wrap(self._menu_actions.show_settings)),
            pystray.MenuItem("History", self._wrap(self._menu_actions.show_history)),
            pystray.MenuItem("Restart", self._wrap(self._menu_actions.restart_app)),
            pystray.MenuItem(
                "Start with Windows",
                self._wrap(lambda: self.toggle_start_with_windows()),
                checked=lambda _: self._start_with_windows,
            ),
            pystray.MenuItem("Quit", self._wrap(self._menu_actions.quit_app)),
        )

    def _wrap(
        self, func: Callable[[], None]
    ) -> Callable[["pystray.Icon", "pystray.MenuItem"], None]:
        def wrapper(icon: "pystray.Icon", item: "pystray.MenuItem") -> None:
            del icon, item
            try:
                func()
            except Exception:  # pragma: no cover - defensive logging
                _LOGGER.exception("Unhandled exception in tray menu callback")

        return wrapper


def detect_tray_theme() -> TrayTheme:
    """Best-effort detection of the Windows theme preference."""
    try:
        import winreg
    except ModuleNotFoundError:  # pragma: no cover - not running on Windows
        return TrayTheme.LIGHT

    # Check for high-contrast mode first
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Control Panel\Accessibility\HighContrast",
        ) as key:  # type: ignore[attr-defined]
            flags, _ = winreg.QueryValueEx(key, "Flags")
            # HCF_HIGHCONTRASTON = 0x01
            if int(flags) & 0x01:
                _LOGGER.info("High-contrast mode detected")
                return TrayTheme.HIGH_CONTRAST
    except (FileNotFoundError, OSError):
        pass  # High-contrast not enabled or key not found

    # Check light/dark theme preference
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
    value_name = "AppsUseLightTheme"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:  # type: ignore[attr-defined]
            value, _ = winreg.QueryValueEx(key, value_name)
    except FileNotFoundError:
        return TrayTheme.LIGHT
    except OSError:  # pragma: no cover - registry access failure
        _LOGGER.debug("Failed to query Windows theme preference", exc_info=True)
        return TrayTheme.LIGHT
    return TrayTheme.LIGHT if int(value) else TrayTheme.DARK
