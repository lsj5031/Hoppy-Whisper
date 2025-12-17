"""Settings management window for Hoppy Whisper."""

from __future__ import annotations

import ctypes
import json
import logging
import sys
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable, Optional

import customtkinter as ctk

from app.hotkey import (
    HotkeyInUseError,
    HotkeyParseError,
    HotkeyRegistrationError,
    ensure_hotkey_available,
    parse_hotkey,
)
from app.settings import AppSettings
from app.ui.hotkey_capture import capture_hotkey

LOGGER = logging.getLogger("hoppy_whisper.settings")


def _get_icon_path() -> Optional[Path]:
    """Get the path to the application icon."""
    # Try relative to this file first (development)
    base = Path(__file__).resolve().parent.parent.parent.parent
    icon_path = base / "icos" / "BunnyStandby.ico"
    if icon_path.exists():
        return icon_path

    # PyInstaller (onefile extracts datas under sys._MEIPASS; onedir keeps next to exe)
    if getattr(sys, "frozen", False):
        if hasattr(sys, "_MEIPASS"):
            icon_path = Path(sys._MEIPASS) / "icos" / "BunnyStandby.ico"
            if icon_path.exists():
                return icon_path

        icon_path = Path(sys.executable).parent / "icos" / "BunnyStandby.ico"
        if icon_path.exists():
            return icon_path
    return None


class _CustomInputDialog(ctk.CTkToplevel):
    """Custom input dialog with app icon support."""

    def __init__(
        self,
        parent: ctk.CTk,
        title: str = "Input",
        text: str = "Enter value:",
    ):
        super().__init__(parent)
        self.title(title)
        self.geometry("300x180")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._result: Optional[str] = None

        # Set window icon (must be done after window is mapped)
        def _set_icon():
            icon_path = _get_icon_path()
            if icon_path:
                try:
                    self.iconbitmap(str(icon_path))
                except Exception:
                    pass

        self.after(50, _set_icon)

        # Label
        ctk.CTkLabel(self, text=text, wraplength=260).pack(pady=(20, 10), padx=20)

        # Entry
        self._entry = ctk.CTkEntry(self, width=260)
        self._entry.pack(pady=10, padx=20)
        self._entry.focus()

        # Buttons frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=(10, 20))

        ctk.CTkButton(btn_frame, text="OK", width=80, command=self._on_ok).pack(
            side="left", padx=5
        )
        ctk.CTkButton(
            btn_frame,
            text="Cancel",
            width=80,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._on_cancel,
        ).pack(side="left", padx=5)

        self._entry.bind("<Return>", lambda e: self._on_ok())
        self._entry.bind("<Escape>", lambda e: self._on_cancel())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Center on parent
        self.update_idletasks()
        px = parent.winfo_x() + (parent.winfo_width() // 2) - (self.winfo_width() // 2)
        py = (
            parent.winfo_y() + (parent.winfo_height() // 2) - (self.winfo_height() // 2)
        )
        self.geometry(f"+{px}+{py}")

    def _on_ok(self) -> None:
        self._result = self._entry.get()
        self.destroy()

    def _on_cancel(self) -> None:
        self._result = None
        self.destroy()

    def get_input(self) -> Optional[str]:
        """Show dialog and return entered value or None if cancelled."""
        self.wait_window()
        return self._result


def _get_version() -> str:
    """Get the application version."""
    try:
        from importlib.metadata import version

        return version("hoppy-whisper")
    except Exception:
        return "1.1.0"


def get_windows_dpi_scale() -> float:
    """Get the Windows DPI scale factor using the Windows API.

    Returns a scale factor (1.0 = 100%, 1.5 = 150%, 2.0 = 200%).
    Falls back to 1.0 if detection fails or not on Windows.
    """
    if sys.platform != "win32":
        return 1.0

    try:
        # Set DPI awareness to per-monitor aware (Windows 8.1+)
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass

        dpi = 96  # Default standard DPI

        # Method 1: GetDpiForSystem (Windows 10 1607+)
        try:
            dpi = ctypes.windll.user32.GetDpiForSystem()
        except (AttributeError, OSError):
            pass

        # Method 2: GetDeviceCaps if Method 1 failed
        if dpi == 96:
            try:
                hdc = ctypes.windll.user32.GetDC(0)
                if hdc:
                    dpi = ctypes.windll.gdi32.GetDeviceCaps(hdc, 88)
                    ctypes.windll.user32.ReleaseDC(0, hdc)
            except (AttributeError, OSError):
                pass

        scale = dpi / 96.0
        LOGGER.debug("Detected Windows DPI: %d, scale factor: %.2f", dpi, scale)
        return scale

    except Exception as e:
        LOGGER.warning("Failed to detect Windows DPI scale: %s", e)
        return 1.0


class SettingsWindow:
    """Settings window with modern UI."""

    ACCENT_COLOR = "#3b82f6"

    def __init__(
        self,
        settings: AppSettings,
        on_apply: Optional[Callable[[], None]] = None,
    ):
        self._settings = settings
        self._on_apply = on_apply
        self._root: Optional[ctk.CTk] = None
        self._original_settings = settings.to_dict()
        self._modified = False

        # Timing variables (initialized in _create_hotkey_tab)
        self._transcribe_start_delay_var: Optional[ctk.IntVar] = None
        self._paste_predelay_var: Optional[ctk.IntVar] = None
        self._idle_reset_delay_var: Optional[ctk.IntVar] = None

    def show(self) -> None:
        """Show the settings window."""
        if self._root and self._root.winfo_exists():
            self._root.lift()
            return

        self._create_window()
        self._setup_tabs()

        if self._root:
            self._root.mainloop()

    def _create_window(self) -> None:
        """Create the settings window."""
        # Detect DPI scale factor
        dpi_scale = get_windows_dpi_scale()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Reset customtkinter scaling to 1.0 to prevent double-scaling
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)

        self._root = ctk.CTk()
        self._root.title("Hoppy Whisper Settings")

        # Set window icon (use after() to ensure it overrides customtkinter default)
        def _set_icon() -> None:
            root = self._root
            if not root:
                return
            icon_path = _get_icon_path()
            if icon_path:
                try:
                    root.iconbitmap(str(icon_path))
                    try:
                        root.iconbitmap(default=str(icon_path))
                    except Exception:
                        pass
                except Exception:
                    LOGGER.debug("Failed to set settings window icon", exc_info=True)

        self._root.after(10, _set_icon)

        # Target dimensions we want on screen (at any DPI)
        # Divide by DPI scale to compensate for system scaling
        target_width = 750
        target_height = 650
        min_width = 600
        min_height = 500
        actual_width = int(target_width / dpi_scale)
        actual_height = int(target_height / dpi_scale)
        actual_min_width = int(min_width / dpi_scale)
        actual_min_height = int(min_height / dpi_scale)

        self._root.geometry(f"{actual_width}x{actual_height}")
        self._root.resizable(True, True)
        self._root.minsize(actual_min_width, actual_min_height)

        # Main container
        main_frame = ctk.CTkFrame(self._root, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)

        # Tabview
        self._tabview = ctk.CTkTabview(main_frame, corner_radius=12)
        self._tabview.grid(row=0, column=0, sticky="nsew")

        # Button frame
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.grid(row=1, column=0, sticky="ew", pady=(15, 0))

        help_label = ctk.CTkLabel(
            button_frame,
            text="Settings are saved when you click OK or Apply",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        )
        help_label.pack(side="left")

        ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=90,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._on_cancel,
        ).pack(side="right", padx=(10, 0))

        self._apply_button = ctk.CTkButton(
            button_frame,
            text="Apply",
            width=90,
            state="disabled",
            command=self._on_apply_click,
        )
        self._apply_button.pack(side="right", padx=(10, 0))

        ctk.CTkButton(
            button_frame,
            text="OK",
            width=90,
            command=self._on_ok,
        ).pack(side="right")

        self._root.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self._center_window()

    def _center_window(self) -> None:
        """Center the window on the screen."""
        if not self._root:
            return
        self._root.update_idletasks()
        w = self._root.winfo_width()
        h = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() // 2) - (w // 2)
        y = (self._root.winfo_screenheight() // 2) - (h // 2)
        self._root.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_tabs(self) -> None:
        """Setup all settings tabs."""
        self._tabview.add("General")
        self._tabview.add("Hotkey")
        self._tabview.add("Transcription")
        self._tabview.add("History")
        self._tabview.add("Advanced")

        self._create_general_tab(self._tabview.tab("General"))
        self._create_hotkey_tab(self._tabview.tab("Hotkey"))
        self._create_transcription_tab(self._tabview.tab("Transcription"))
        self._create_history_tab(self._tabview.tab("History"))
        self._create_advanced_tab(self._tabview.tab("Advanced"))

    def _create_section(
        self, parent: ctk.CTkFrame, title: str, **kwargs
    ) -> ctk.CTkFrame:
        """Create a section frame with title."""
        frame = ctk.CTkFrame(parent, corner_radius=12, **kwargs)
        frame.pack(fill="x", pady=8)

        ctk.CTkLabel(
            frame,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 10))

        return frame

    def _create_general_tab(self, parent: ctk.CTkFrame) -> None:
        """Create the general settings tab."""
        parent.grid_columnconfigure(0, weight=1)

        # Scrollable frame
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Startup section
        startup_frame = self._create_section(scroll, "Startup")

        self._start_with_windows_var = ctk.BooleanVar(
            value=self._settings.start_with_windows
        )
        ctk.CTkCheckBox(
            startup_frame,
            text="Start Hoppy Whisper with Windows",
            variable=self._start_with_windows_var,
            command=self._mark_modified,
        ).pack(anchor="w", padx=20, pady=(0, 15))

        # About section
        about_frame = self._create_section(scroll, "About")

        version = _get_version()
        about_text = (
            "Hoppy Whisper - Speech Transcription Tool\n"
            f"Version: {version}\n\n"
            "Transform your speech into text with privacy-first\n"
            "local transcription or flexible remote options.\n\n"
            "© 2025 Hoppy Whisper"
        )

        ctk.CTkLabel(
            about_frame,
            text=about_text,
            font=ctk.CTkFont(size=12),
            justify="left",
            text_color="gray",
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def _create_hotkey_tab(self, parent: ctk.CTkFrame) -> None:
        """Create the hotkey settings tab."""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Hotkey configuration
        hotkey_frame = self._create_section(scroll, "Hotkey Configuration")

        ctk.CTkLabel(
            hotkey_frame,
            text="Current Hotkey:",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=20, pady=(0, 5))

        self._hotkey_var = ctk.StringVar(value=self._settings.hotkey_chord)

        self._hotkey_entry = ctk.CTkEntry(
            hotkey_frame,
            textvariable=self._hotkey_var,
            font=ctk.CTkFont(family="Consolas", size=14),
            height=40,
            justify="center",
        )
        self._hotkey_entry.pack(fill="x", padx=20, pady=(0, 10))
        self._hotkey_entry.insert(0, self._settings.hotkey_chord)
        self._hotkey_entry.configure(state="readonly")

        buttons_frame = ctk.CTkFrame(hotkey_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(
            buttons_frame,
            text="Change Hotkey",
            width=130,
            command=self._change_hotkey,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            buttons_frame,
            text="Reset to Default",
            width=130,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._reset_hotkey,
        ).pack(side="left")

        # Behavior settings
        behavior_frame = self._create_section(scroll, "Behavior")

        self._auto_paste_var = ctk.BooleanVar(value=self._settings.auto_paste)
        ctk.CTkCheckBox(
            behavior_frame,
            text="Automatically paste transcribed text",
            variable=self._auto_paste_var,
            command=self._mark_modified,
        ).pack(anchor="w", padx=20, pady=(0, 10))

        # Re-paste timeout
        ctk.CTkLabel(
            behavior_frame,
            text="Press hotkey again within this time to re-paste transcription:",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", padx=20, pady=(5, 5))

        paste_frame = ctk.CTkFrame(behavior_frame, fg_color="transparent")
        paste_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkLabel(
            paste_frame,
            text="Re-paste timeout:",
            font=ctk.CTkFont(size=12),
        ).pack(side="left")

        self._paste_window_var = ctk.DoubleVar(
            value=self._settings.paste_window_seconds
        )
        paste_slider = ctk.CTkSlider(
            paste_frame,
            from_=0.5,
            to=10.0,
            number_of_steps=19,
            variable=self._paste_window_var,
            width=200,
            command=lambda v: self._mark_modified(),
        )
        paste_slider.pack(side="left", padx=(10, 10))

        self._paste_window_label = ctk.CTkLabel(
            paste_frame,
            text=f"{self._paste_window_var.get():.1f}s",
            font=ctk.CTkFont(size=12),
            width=40,
        )
        self._paste_window_label.pack(side="left")

        self._paste_window_var.trace_add(
            "write",
            lambda *args: self._paste_window_label.configure(
                text=f"{self._paste_window_var.get():.1f}s"
            ),
        )

    def _create_timing_slider(
        self,
        parent: ctk.CTkFrame,
        label: str,
        min_val: int,
        max_val: int,
        current: int,
        var_name: str,
        description: Optional[str] = None,
    ) -> None:
        """Create a timing slider with label and optional description."""
        container = ctk.CTkFrame(parent, fg_color="transparent")
        container.pack(fill="x", padx=20, pady=5)

        frame = ctk.CTkFrame(container, fg_color="transparent")
        frame.pack(fill="x")

        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(size=12), width=150).pack(
            side="left"
        )

        var = ctk.IntVar(value=current)
        setattr(self, var_name, var)

        slider = ctk.CTkSlider(
            frame,
            from_=min_val,
            to=max_val,
            number_of_steps=(max_val - min_val) // 50,
            variable=var,
            width=250,
            command=lambda v: self._mark_modified(),
        )
        slider.pack(side="left", padx=(10, 10))

        value_label = ctk.CTkLabel(
            frame,
            text=f"{current}ms",
            font=ctk.CTkFont(size=12),
            width=60,
        )
        value_label.pack(side="left")

        var.trace_add(
            "write", lambda *args: value_label.configure(text=f"{var.get()}ms")
        )

        if description:
            ctk.CTkLabel(
                container,
                text=description,
                font=ctk.CTkFont(size=10),
                text_color="gray",
            ).pack(anchor="w", padx=(150, 0))

    def _create_transcription_tab(self, parent: ctk.CTkFrame) -> None:
        """Create the transcription settings tab."""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Mode selection
        mode_frame = self._create_section(scroll, "Transcription Method")

        self._remote_enabled_var = ctk.BooleanVar(
            value=self._settings.remote_transcription_enabled
        )

        # Local option
        local_frame = ctk.CTkFrame(mode_frame, fg_color="transparent")
        local_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkRadioButton(
            local_frame,
            variable=self._remote_enabled_var,
            value=False,
            text="Local Transcription (Recommended)",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_transcription_mode_change,
        ).pack(anchor="w")

        ctk.CTkLabel(
            local_frame,
            text="Speech is processed locally. Better privacy, works offline.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", padx=25, pady=(2, 10))

        # Remote option
        remote_frame = ctk.CTkFrame(mode_frame, fg_color="transparent")
        remote_frame.pack(fill="x", padx=20, pady=5)

        ctk.CTkRadioButton(
            remote_frame,
            variable=self._remote_enabled_var,
            value=True,
            text="Remote Transcription",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._on_transcription_mode_change,
        ).pack(anchor="w")

        ctk.CTkLabel(
            remote_frame,
            text="Speech sent to remote service. Requires internet.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", padx=25, pady=(2, 10))

        ctk.CTkLabel(mode_frame, text="").pack(pady=2)

        # Remote settings
        self._remote_settings_frame = self._create_section(
            scroll, "Remote Transcription Settings"
        )

        self._remote_endpoint_var = ctk.StringVar(
            value=self._settings.remote_transcription_endpoint
        )
        self._remote_api_key_var = ctk.StringVar(
            value=self._settings.remote_transcription_api_key
        )
        self._remote_model_var = ctk.StringVar(
            value=self._settings.remote_transcription_model
        )

        # Endpoint
        ctk.CTkLabel(
            self._remote_settings_frame,
            text="Endpoint URL:",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=20, pady=(0, 2))

        self._endpoint_entry = ctk.CTkEntry(
            self._remote_settings_frame,
            textvariable=self._remote_endpoint_var,
            placeholder_text="https://api.example.com/transcribe",
        )
        self._endpoint_entry.pack(fill="x", padx=20, pady=(0, 10))
        if self._settings.remote_transcription_endpoint:
            self._endpoint_entry.insert(0, self._settings.remote_transcription_endpoint)
        self._endpoint_entry.bind("<KeyRelease>", lambda e: self._mark_modified())

        # API Key
        ctk.CTkLabel(
            self._remote_settings_frame,
            text="API Key:",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=20, pady=(0, 2))

        self._api_key_entry = ctk.CTkEntry(
            self._remote_settings_frame,
            textvariable=self._remote_api_key_var,
            show="•",
            placeholder_text="Your API key",
        )
        self._api_key_entry.pack(fill="x", padx=20, pady=(0, 10))
        if self._settings.remote_transcription_api_key:
            self._api_key_entry.insert(0, self._settings.remote_transcription_api_key)
        self._api_key_entry.bind("<KeyRelease>", lambda e: self._mark_modified())

        # Model
        ctk.CTkLabel(
            self._remote_settings_frame,
            text="Model:",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=20, pady=(0, 2))

        self._model_entry = ctk.CTkEntry(
            self._remote_settings_frame,
            textvariable=self._remote_model_var,
            placeholder_text="whisper-1",
        )
        self._model_entry.pack(fill="x", padx=20, pady=(0, 10))
        if self._settings.remote_transcription_model:
            self._model_entry.insert(0, self._settings.remote_transcription_model)
        self._model_entry.bind("<KeyRelease>", lambda e: self._mark_modified())

        # Test button
        self._test_connection_button = ctk.CTkButton(
            self._remote_settings_frame,
            text="Test Connection",
            width=140,
            command=self._test_remote_connection,
        )
        self._test_connection_button.pack(padx=20, pady=(5, 15))

        self._on_transcription_mode_change()

    def _on_transcription_mode_change(self) -> None:
        """Handle transcription mode change."""
        self._mark_modified()
        if self._remote_enabled_var.get():
            self._remote_settings_frame.pack(fill="x", pady=8)
        else:
            self._remote_settings_frame.pack_forget()

    def _create_history_tab(self, parent: ctk.CTkFrame) -> None:
        """Create the history settings tab."""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Retention
        retention_frame = self._create_section(scroll, "History Retention")

        ret_row = ctk.CTkFrame(retention_frame, fg_color="transparent")
        ret_row.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkLabel(
            ret_row,
            text="Keep history for (days):",
            font=ctk.CTkFont(size=12),
        ).pack(side="left")

        self._history_retention_var = ctk.IntVar(
            value=self._settings.history_retention_days
        )

        retention_slider = ctk.CTkSlider(
            ret_row,
            from_=7,
            to=365,
            number_of_steps=358,
            variable=self._history_retention_var,
            width=200,
            command=lambda v: self._mark_modified(),
        )
        retention_slider.pack(side="left", padx=(10, 10))

        self._retention_label = ctk.CTkLabel(
            ret_row,
            text=f"{self._history_retention_var.get()} days",
            font=ctk.CTkFont(size=12),
            width=70,
        )
        self._retention_label.pack(side="left")

        self._history_retention_var.trace_add(
            "write",
            lambda *args: self._retention_label.configure(
                text=f"{self._history_retention_var.get()} days"
            ),
        )

        # Actions
        actions_frame = self._create_section(scroll, "History Actions")

        buttons_row = ctk.CTkFrame(actions_frame, fg_color="transparent")
        buttons_row.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkButton(
            buttons_row,
            text="Export History",
            width=140,
            command=self._export_history,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            buttons_row,
            text="Clear All History",
            width=140,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            command=self._clear_history,
        ).pack(side="left")

        ctk.CTkLabel(
            actions_frame,
            text="History is stored locally and never leaves your device.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", padx=20, pady=(5, 15))

    def _create_advanced_tab(self, parent: ctk.CTkFrame) -> None:
        """Create the advanced settings tab."""
        scroll = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=5, pady=5)

        # Timing settings
        timing_frame = self._create_section(scroll, "Timing")

        ctk.CTkLabel(
            timing_frame,
            text="Fine-tune delays for transcription and pasting behavior.",
            font=ctk.CTkFont(size=11),
            text_color="gray",
        ).pack(anchor="w", padx=20, pady=(0, 10))

        # Transcribe start delay
        self._create_timing_slider(
            timing_frame,
            "Transcription delay:",
            100,
            2000,
            int(self._settings.transcribe_start_delay_ms),
            "_transcribe_start_delay_var",
            "Wait time after releasing hotkey before transcription starts",
        )

        # Paste predelay
        self._create_timing_slider(
            timing_frame,
            "Paste delay:",
            50,
            500,
            int(self._settings.paste_predelay_ms),
            "_paste_predelay_var",
            "Wait time before pasting text (allows focus to return)",
        )

        # Idle reset delay
        self._create_timing_slider(
            timing_frame,
            "Idle reset delay:",
            500,
            5000,
            int(self._settings.idle_reset_delay_ms),
            "_idle_reset_delay_var",
            "Time before app returns to idle state after transcription",
        )

        ctk.CTkLabel(timing_frame, text="").pack(pady=5)

        # Configuration
        config_frame = self._create_section(scroll, "Configuration Management")

        buttons_row = ctk.CTkFrame(config_frame, fg_color="transparent")
        buttons_row.pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkButton(
            buttons_row,
            text="Export Settings",
            width=130,
            command=self._export_settings,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            buttons_row,
            text="Import Settings",
            width=130,
            command=self._import_settings,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            buttons_row,
            text="Reset to Defaults",
            width=130,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._reset_to_defaults,
        ).pack(side="left")

        ctk.CTkLabel(config_frame, text="").pack(pady=2)

        # Diagnostics
        diag_frame = self._create_section(scroll, "Diagnostics")

        ctk.CTkButton(
            diag_frame,
            text="View Log File",
            width=130,
            command=self._view_logs,
        ).pack(anchor="w", padx=20, pady=(0, 15))

        # Onboarding
        onboard_frame = self._create_section(scroll, "Onboarding")

        ctk.CTkButton(
            onboard_frame,
            text="Reset First-Run Setup",
            width=160,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._reset_first_run,
        ).pack(anchor="w", padx=20, pady=(0, 15))

    def _mark_modified(self) -> None:
        """Mark settings as modified."""
        self._modified = True
        self._apply_button.configure(state="normal")

    def _change_hotkey(self) -> None:
        """Capture a new hotkey chord from the keyboard."""
        root = self._root
        if not root:
            return

        hotkey = capture_hotkey(root, title="Change Hotkey")
        if not hotkey:
            return

        self._hotkey_var.set(hotkey)
        self._hotkey_entry.configure(state="normal")
        self._hotkey_entry.delete(0, "end")
        self._hotkey_entry.insert(0, hotkey)
        self._hotkey_entry.configure(state="readonly")
        self._mark_modified()

    def _reset_hotkey(self) -> None:
        """Reset hotkey to default."""
        default_hotkey = AppSettings().hotkey_chord
        self._hotkey_var.set(default_hotkey)
        self._hotkey_entry.configure(state="normal")
        self._hotkey_entry.delete(0, "end")
        self._hotkey_entry.insert(0, default_hotkey)
        self._hotkey_entry.configure(state="readonly")
        self._mark_modified()

    def _test_remote_connection(self) -> None:
        """Test the remote transcription connection."""
        root = self._root
        if not root:
            return

        endpoint = self._remote_endpoint_var.get().strip()
        api_key = self._remote_api_key_var.get().strip()
        model = self._remote_model_var.get().strip()

        if not endpoint:
            messagebox.showerror("Test Failed", "Please enter an endpoint URL first.")
            return

        btn = getattr(self, "_test_connection_button", None)
        if btn is not None:
            try:
                btn.configure(state="disabled", text="Testing...")
            except Exception:
                pass

        def finish_button() -> None:
            if btn is None:
                return
            try:
                btn.configure(state="normal", text="Test Connection")
            except Exception:
                pass

        def show_success(details: str) -> None:
            messagebox.showinfo("Test Successful", details)
            finish_button()

        def show_error(details: str) -> None:
            messagebox.showerror("Test Failed", details)
            finish_button()

        def run_test() -> None:
            try:
                from app.transcriber import RemoteTranscriber, RemoteTranscriptionError
            except Exception as exc:
                details = f"Failed to load remote transcription client: {exc}"
                root.after(0, lambda details=details: show_error(details))
                return

            try:
                transcriber = RemoteTranscriber(
                    endpoint=endpoint,
                    api_key=api_key,
                    timeout=10.0,
                    model=model,
                )
                text = transcriber.test_connection()

                summary = "Connected successfully."
                text_preview = text.strip()
                if text_preview:
                    summary = (
                        "Connected successfully.\n\n"
                        f"Response text: {text_preview[:200]}"
                    )

                root.after(0, lambda: show_success(summary))

            except RemoteTranscriptionError as exc:
                details = str(exc)
                if exc.response_text:
                    details = f"{details}\nResponse: {exc.response_text}"
                root.after(0, lambda details=details: show_error(details))
            except Exception as exc:
                details = f"Unexpected error: {exc}"
                root.after(0, lambda details=details: show_error(details))

        import threading

        threading.Thread(target=run_test, daemon=True).start()

    def _export_history(self) -> None:
        """Export history to a file."""
        messagebox.showinfo(
            "Export History",
            "Use the History window from the tray menu to export your history.",
        )

    def _clear_history(self) -> None:
        """Clear all history with confirmation."""
        if not messagebox.askyesno(
            "Clear History",
            "Are you sure you want to delete all transcription history?\n\n"
            "This action cannot be undone.",
            icon="warning",
        ):
            return

        try:
            from app.history.dao import HistoryDAO
            from app.settings import default_history_db_path

            dao = HistoryDAO(
                default_history_db_path(),
                retention_days=self._settings.history_retention_days,
            )
            dao.open()
            deleted = dao.clear_all()
            dao.close()

            messagebox.showinfo("Clear History", f"Deleted {deleted} records.")
        except Exception as exc:
            messagebox.showerror("Clear Failed", f"Failed to clear history: {exc}")

    def _export_settings(self) -> None:
        """Export current settings to a file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialfile="hoppy_whisper_settings.json",
            title="Export Settings",
        )

        if not file_path:
            return

        try:
            settings_data = self._settings.to_dict()
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(settings_data, f, indent=2, sort_keys=True)

            messagebox.showinfo(
                "Export Settings", f"Settings exported to:\n{file_path}"
            )
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Failed to export settings: {exc}")

    def _import_settings(self) -> None:
        """Import settings from a file."""
        file_path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Settings",
        )

        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                settings_data = json.load(f)

            new_settings = AppSettings.from_dict(settings_data)

            if messagebox.askyesno(
                "Import Settings",
                "This will replace your current settings. Continue?",
            ):
                self._settings = new_settings
                messagebox.showinfo(
                    "Import Settings", "Settings imported successfully."
                )
                self._cleanup()
        except Exception as exc:
            messagebox.showerror("Import Failed", f"Failed to import settings: {exc}")

    def _reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        if not messagebox.askyesno(
            "Reset Settings",
            "This will reset all settings to defaults. Continue?",
        ):
            return

        try:
            self._settings = AppSettings()
            messagebox.showinfo("Reset Settings", "Settings reset to defaults.")
            self._cleanup()
        except Exception as exc:
            messagebox.showerror("Reset Failed", f"Failed to reset settings: {exc}")

    def _view_logs(self) -> None:
        """Open the log file in the default text editor."""
        try:
            import subprocess
            import sys

            from app.settings import default_metrics_log_path

            log_path = default_metrics_log_path()

            if log_path.exists():
                if sys.platform == "win32":
                    subprocess.Popen(["notepad.exe", str(log_path)])
                else:
                    subprocess.Popen(["xdg-open", str(log_path)])
            else:
                messagebox.showinfo("Logs", "No log file found yet.")
        except Exception as exc:
            messagebox.showerror("View Logs", f"Failed to open log file: {exc}")

    def _reset_first_run(self) -> None:
        """Reset the first-run flag to show onboarding again."""
        if messagebox.askyesno(
            "Reset Onboarding",
            "The onboarding wizard will appear next time you start the app.\n\n"
            "Continue?",
        ):
            self._settings.first_run_complete = False
            self._settings.save()
            messagebox.showinfo(
                "Reset Onboarding", "First-run setup will appear on next startup."
            )

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if self._modified:
            if not messagebox.askyesno(
                "Discard Changes",
                "You have unsaved changes. Discard them?",
            ):
                return

        self._cleanup()

    def _on_ok(self) -> None:
        """Handle OK button click."""
        if self._apply_changes():
            self._cleanup()

    def _on_apply_click(self) -> None:
        """Handle apply button click."""
        self._apply_changes()

    def _apply_changes(self) -> bool:
        """Apply the settings changes."""
        try:
            new_hotkey = self._hotkey_var.get().strip().upper()
            if new_hotkey != self._settings.hotkey_chord:
                chord = parse_hotkey(new_hotkey)
                if chord.modifier_mask == 0:
                    raise HotkeyParseError(
                        "Hotkey must include at least one modifier (Ctrl/Shift/Alt/Win)"
                    )
                ensure_hotkey_available(chord)

            self._settings.start_with_windows = self._start_with_windows_var.get()
            self._settings.hotkey_chord = new_hotkey
            self._settings.paste_window_seconds = self._paste_window_var.get()
            self._settings.auto_paste = self._auto_paste_var.get()

            transcribe_start_delay_var = self._transcribe_start_delay_var
            paste_predelay_var = self._paste_predelay_var
            idle_reset_delay_var = self._idle_reset_delay_var
            if (
                transcribe_start_delay_var is None
                or paste_predelay_var is None
                or idle_reset_delay_var is None
            ):
                raise RuntimeError("Timing controls were not initialized")

            self._settings.transcribe_start_delay_ms = float(
                transcribe_start_delay_var.get()
            )
            self._settings.paste_predelay_ms = float(paste_predelay_var.get())
            self._settings.idle_reset_delay_ms = float(idle_reset_delay_var.get())
            self._settings.history_retention_days = self._history_retention_var.get()

            self._settings.remote_transcription_enabled = self._remote_enabled_var.get()
            if self._remote_enabled_var.get():
                self._settings.remote_transcription_endpoint = (
                    self._remote_endpoint_var.get()
                )
                self._settings.remote_transcription_api_key = (
                    self._remote_api_key_var.get()
                )
                self._settings.remote_transcription_model = self._remote_model_var.get()

            self._settings.save()

            self._modified = False
            self._apply_button.configure(state="disabled")

            if self._on_apply:
                self._on_apply()

            return True

        except HotkeyInUseError as exc:
            messagebox.showerror("Hotkey Unavailable", str(exc))
            return False
        except HotkeyParseError as exc:
            messagebox.showerror("Invalid Hotkey", str(exc))
            return False
        except HotkeyRegistrationError as exc:
            messagebox.showerror("Hotkey Error", str(exc))
            return False

        except Exception as exc:
            LOGGER.error("Failed to apply settings: %s", exc)
            messagebox.showerror("Apply Failed", f"Failed to apply settings: {exc}")
            return False

    def _cleanup(self) -> None:
        """Cleanup the settings window."""
        if self._root:
            try:
                self._root.quit()
                self._root.destroy()
            except Exception:
                pass
            self._root = None
