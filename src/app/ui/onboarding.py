"""First-run onboarding wizard for new users."""

from __future__ import annotations

import ctypes
import logging
import sys
import threading
from dataclasses import dataclass
from pathlib import Path
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
from app.transcriber import load_transcriber
from app.ui.hotkey_capture import capture_hotkey

LOGGER = logging.getLogger("hoppy_whisper.onboarding")


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


def get_windows_dpi_scale() -> float:
    """Get the Windows DPI scale factor using the Windows API.

    Returns a scale factor (1.0 = 100%, 1.5 = 150%, 2.0 = 200%).
    Falls back to 1.0 if detection fails or not on Windows.
    """
    if sys.platform != "win32":
        return 1.0

    try:
        # Set DPI awareness to per-monitor aware (Windows 8.1+)
        # This must be called before any window is created
        try:
            # PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except (AttributeError, OSError):
            # Fallback for older Windows versions
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except (AttributeError, OSError):
                pass

        # Get DPI using multiple methods for reliability
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
                    # LOGPIXELSX = 88
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


@dataclass
class OnboardingStep:
    """Represents a step in the onboarding process."""

    title: str
    description: str
    can_skip: bool = True
    validation_func: Optional[Callable[[], bool]] = None


class OnboardingWizard:
    """First-run onboarding wizard with modern UI."""

    ACCENT_COLOR = "#3b82f6"
    SUCCESS_COLOR = "#22c55e"
    ERROR_COLOR = "#ef4444"

    def __init__(
        self,
        settings: AppSettings,
        on_complete: Optional[Callable[[], None]] = None,
    ):
        self._settings = settings
        self._on_complete = on_complete
        self._root: Optional[ctk.CTk] = None
        self._current_step = 0
        self._steps: list[OnboardingStep] = []
        self._is_complete = False

        # UI variables
        self._hotkey_var: Optional[ctk.StringVar] = None
        self._transcription_mode: Optional[ctk.StringVar] = None
        self._endpoint_var: Optional[ctk.StringVar] = None
        self._api_key_var: Optional[ctk.StringVar] = None
        self._model_var: Optional[ctk.StringVar] = None

        # UI widgets (used only while a step is visible)
        self._hotkey_entry: Optional[ctk.CTkEntry] = None
        self._endpoint_entry: Optional[ctk.CTkEntry] = None
        self._api_key_entry: Optional[ctk.CTkEntry] = None
        self._model_entry: Optional[ctk.CTkEntry] = None

    @staticmethod
    def _set_entry_text(
        entry: ctk.CTkEntry, value: str, *, readonly: bool = False
    ) -> None:
        """Update an entry's contents (even when read-only)."""
        if readonly:
            entry.configure(state="normal")
        entry.delete(0, "end")
        if value:
            entry.insert(0, value)
        if readonly:
            entry.configure(state="readonly")

    def show(self) -> bool:
        """Show the onboarding wizard. Returns True if completed."""
        if self._is_complete:
            return True

        self._create_window()
        self._setup_steps()
        self._show_step(0)

        if self._root:
            self._root.mainloop()
            return self._is_complete
        return False

    def _create_window(self) -> None:
        """Create the main wizard window."""
        # Detect DPI scale factor
        dpi_scale = get_windows_dpi_scale()
        LOGGER.info("Detected DPI scale factor: %.2f", dpi_scale)

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Reset customtkinter scaling to 1.0 to prevent double-scaling
        ctk.set_widget_scaling(1.0)
        ctk.set_window_scaling(1.0)

        self._root = ctk.CTk()
        self._root.title("Hoppy Whisper Setup")

        # Set window icon (use after() to ensure it overrides customtkinter default)
        def _set_icon():
            icon_path = _get_icon_path()
            if icon_path:
                try:
                    self._root.iconbitmap(str(icon_path))
                except Exception:
                    pass

        self._root.after(10, _set_icon)

        # Target dimensions we want on screen (at any DPI)
        # Divide by DPI scale to compensate for system scaling
        target_width = 680
        target_height = 580
        actual_width = int(target_width / dpi_scale)
        actual_height = int(target_height / dpi_scale)
        self._root.geometry(f"{actual_width}x{actual_height}")
        self._root.resizable(False, False)

        try:
            self._root.attributes("-topmost", True)
        except Exception:
            pass

        # Bind keyboard shortcuts
        self._root.bind("<Return>", lambda e: self._on_next())
        self._root.bind("<BackSpace>", lambda e: self._on_back())
        self._root.bind("<Escape>", lambda e: self._on_cancel())

        # Main container using grid for better layout control
        self._root.grid_rowconfigure(0, weight=1)
        self._root.grid_columnconfigure(0, weight=1)

        self._main_frame = ctk.CTkFrame(self._root, fg_color="transparent")
        self._main_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        self._main_frame.grid_rowconfigure(2, weight=1)  # Content frame expands
        self._main_frame.grid_columnconfigure(0, weight=1)

        # Header
        header_frame = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15))

        title_label = ctk.CTkLabel(
            header_frame,
            text="🎙️ Hoppy Whisper",
            font=ctk.CTkFont(size=28, weight="bold"),
        )
        title_label.pack(anchor="w")

        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="Let's get you started with speech transcription",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        )
        subtitle_label.pack(anchor="w", pady=(5, 0))

        # Step indicator
        self._step_indicator_frame = ctk.CTkFrame(
            self._main_frame, fg_color="transparent"
        )
        self._step_indicator_frame.grid(row=1, column=0, sticky="ew", pady=(0, 15))

        # Content area - constrained height
        self._content_frame = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        self._content_frame.grid(row=2, column=0, sticky="nsew", pady=(0, 15))

        # Button frame - stays at bottom
        button_frame = ctk.CTkFrame(self._main_frame, fg_color="transparent")
        button_frame.grid(row=3, column=0, sticky="ew", pady=(10, 0))

        self._cancel_button = ctk.CTkButton(
            button_frame,
            text="Cancel",
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._on_cancel,
        )
        self._cancel_button.pack(side="left")

        self._finish_button = ctk.CTkButton(
            button_frame,
            text="Finish",
            width=100,
            fg_color=self.SUCCESS_COLOR,
            hover_color="#16a34a",
            command=self._on_finish,
        )
        self._finish_button.pack(side="right")
        self._finish_button.pack_forget()

        self._next_button = ctk.CTkButton(
            button_frame,
            text="Next →",
            width=100,
            command=self._on_next,
        )
        self._next_button.pack(side="right", padx=(0, 10))

        self._back_button = ctk.CTkButton(
            button_frame,
            text="← Back",
            width=100,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._on_back,
            state="disabled",
        )
        self._back_button.pack(side="right", padx=(0, 10))

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

    def _setup_steps(self) -> None:
        """Setup all onboarding steps."""
        self._steps = [
            OnboardingStep(
                title="Welcome",
                description="Get started with Hoppy Whisper",
                can_skip=False,
            ),
            OnboardingStep(
                title="Hotkey",
                description="Configure your recording shortcut",
                validation_func=self._validate_hotkey,
            ),
            OnboardingStep(
                title="Transcription",
                description="Choose transcription method",
            ),
            OnboardingStep(
                title="Test",
                description="Verify your setup",
                can_skip=True,
            ),
            OnboardingStep(
                title="Complete",
                description="You're all set!",
                can_skip=False,
            ),
        ]
        self._update_step_indicator()

    def _update_step_indicator(self) -> None:
        """Update the step indicator."""
        for widget in self._step_indicator_frame.winfo_children():
            widget.destroy()

        for i, step in enumerate(self._steps):
            step_frame = ctk.CTkFrame(
                self._step_indicator_frame, fg_color="transparent"
            )
            step_frame.pack(side="left", expand=True, fill="x", padx=5)

            # Determine colors
            if i < self._current_step:
                color = self.SUCCESS_COLOR
                text_color = "white"
            elif i == self._current_step:
                color = self.ACCENT_COLOR
                text_color = "white"
            else:
                color = "#374151"
                text_color = "gray"

            # Step circle
            circle = ctk.CTkLabel(
                step_frame,
                text=str(i + 1) if i >= self._current_step else "✓",
                width=32,
                height=32,
                corner_radius=16,
                fg_color=color,
                text_color=text_color,
                font=ctk.CTkFont(size=12, weight="bold"),
            )
            circle.pack()

            # Step title
            title = ctk.CTkLabel(
                step_frame,
                text=step.title,
                font=ctk.CTkFont(size=11),
                text_color="gray" if i != self._current_step else "white",
            )
            title.pack(pady=(5, 0))

    def _show_step(self, step_index: int) -> None:
        """Show the specified step."""
        if not 0 <= step_index < len(self._steps):
            return

        self._current_step = step_index

        for widget in self._content_frame.winfo_children():
            widget.destroy()

        step_creators = [
            self._create_welcome_content,
            self._create_hotkey_content,
            self._create_transcription_mode_content,
            self._create_test_content,
            self._create_complete_content,
        ]
        step_creators[step_index]()

        # Update navigation
        self._back_button.configure(state="normal" if step_index > 0 else "disabled")

        if step_index == len(self._steps) - 1:
            self._next_button.pack_forget()
            self._back_button.pack_forget()
            self._back_button.pack(side="left", padx=(10, 0))
            self._finish_button.pack(side="right")
        else:
            self._finish_button.pack_forget()
            self._back_button.pack_forget()
            self._back_button.pack(side="right", padx=(0, 10))
            self._next_button.pack(side="right", padx=(0, 10))

        self._update_step_indicator()

    def _create_welcome_content(self) -> None:
        """Create the welcome step content."""
        frame = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        welcome_text = (
            "Welcome to Hoppy Whisper! 🎉\n\n"
            "This guide will help you set up speech transcription in a few steps.\n"
            "We'll configure your hotkey, choose the best transcription method,\n"
            "and test everything to make sure it works perfectly."
        )

        welcome_label = ctk.CTkLabel(
            frame,
            text=welcome_text,
            font=ctk.CTkFont(size=14),
            justify="left",
        )
        welcome_label.pack(pady=20, anchor="w")

        # Features
        features_frame = ctk.CTkFrame(frame, corner_radius=12)
        features_frame.pack(fill="x", pady=10)

        features_title = ctk.CTkLabel(
            features_frame,
            text="What you'll be able to do:",
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        features_title.pack(anchor="w", padx=20, pady=(15, 10))

        features = [
            ("🎤", "Press a hotkey to start recording your speech"),
            ("📝", "Transcribe speech to text instantly"),
            ("📋", "Automatically copy text to your clipboard"),
            ("🔄", "Paste text directly into any application"),
            ("📚", "Search through your transcription history"),
        ]

        for icon, text in features:
            feature_frame = ctk.CTkFrame(features_frame, fg_color="transparent")
            feature_frame.pack(fill="x", padx=20, pady=3)

            ctk.CTkLabel(
                feature_frame, text=icon, font=ctk.CTkFont(size=14), width=30
            ).pack(side="left")

            ctk.CTkLabel(
                feature_frame, text=text, font=ctk.CTkFont(size=13), anchor="w"
            ).pack(side="left", fill="x", expand=True)

        ctk.CTkLabel(features_frame, text="").pack(pady=5)

    def _create_hotkey_content(self) -> None:
        """Create the hotkey configuration step."""
        frame = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="Choose a hotkey that doesn't conflict with other programs.",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        ).pack(anchor="w", pady=(0, 20))

        # Hotkey frame
        hotkey_frame = ctk.CTkFrame(frame, corner_radius=12)
        hotkey_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            hotkey_frame,
            text="Current Hotkey",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 10))

        self._hotkey_var = ctk.StringVar(value=self._settings.hotkey_chord)

        hotkey_display = ctk.CTkEntry(
            hotkey_frame,
            textvariable=self._hotkey_var,
            state="readonly",
            font=ctk.CTkFont(family="Consolas", size=16),
            height=45,
            justify="center",
        )
        hotkey_display.pack(fill="x", padx=20, pady=(0, 15))
        self._hotkey_entry = hotkey_display
        self._set_entry_text(hotkey_display, self._hotkey_var.get(), readonly=True)

        buttons_frame = ctk.CTkFrame(hotkey_frame, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=20, pady=(0, 15))

        ctk.CTkButton(
            buttons_frame,
            text="Change Hotkey",
            width=140,
            command=self._change_hotkey,
        ).pack(side="left", padx=(0, 10))

        ctk.CTkButton(
            buttons_frame,
            text="Reset to Default",
            width=140,
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            command=self._reset_hotkey,
        ).pack(side="left")

        # Tips
        tips_frame = ctk.CTkFrame(frame, corner_radius=12)
        tips_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            tips_frame,
            text="💡 Tips",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 10))

        tips = [
            "Choose a combination that's easy to remember",
            "Avoid hotkeys used by other programs (Ctrl+C, Ctrl+V)",
            "Try combinations like Ctrl+Shift+H or Alt+Space",
        ]

        for tip in tips:
            ctk.CTkLabel(
                tips_frame,
                text=f"• {tip}",
                font=ctk.CTkFont(size=12),
                text_color="gray",
            ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkLabel(tips_frame, text="").pack(pady=5)

    def _create_transcription_mode_content(self) -> None:
        """Create the transcription mode selection step."""
        # Use scrollable frame since remote settings can overflow on small screens
        frame = ctk.CTkScrollableFrame(self._content_frame, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="Choose how you want to transcribe speech.",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        ).pack(anchor="w", pady=(0, 20))

        is_remote = self._settings.remote_transcription_enabled
        self._transcription_mode = ctk.StringVar(
            value="remote" if is_remote else "local"
        )

        # Local option
        local_frame = ctk.CTkFrame(frame, corner_radius=12)
        local_frame.pack(fill="x", pady=5)

        local_radio = ctk.CTkRadioButton(
            local_frame,
            variable=self._transcription_mode,
            value="local",
            text="Local Transcription",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_mode_change,
        )
        local_radio.pack(anchor="w", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            local_frame,
            text="Speech is processed locally. Better privacy, works offline.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
            justify="left",
        ).pack(anchor="w", padx=45, pady=(0, 15))

        # Remote option
        remote_frame = ctk.CTkFrame(frame, corner_radius=12)
        remote_frame.pack(fill="x", pady=5)

        remote_radio = ctk.CTkRadioButton(
            remote_frame,
            variable=self._transcription_mode,
            value="remote",
            text="Remote Transcription (Recommended)",
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self._on_mode_change,
        )
        remote_radio.pack(anchor="w", padx=20, pady=(15, 5))

        ctk.CTkLabel(
            remote_frame,
            text="Speech is sent to a remote service. Requires internet and API setup.",
            font=ctk.CTkFont(size=12),
            text_color="gray",
        ).pack(anchor="w", padx=45, pady=(0, 15))

        # Remote settings
        self._remote_settings_frame = ctk.CTkFrame(frame, corner_radius=12)

        self._endpoint_var = ctk.StringVar(
            value=self._settings.remote_transcription_endpoint
        )
        self._api_key_var = ctk.StringVar(
            value=self._settings.remote_transcription_api_key
        )
        self._model_var = ctk.StringVar(value=self._settings.remote_transcription_model)

        ctk.CTkLabel(
            self._remote_settings_frame,
            text="Remote Settings",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 10))

        # Endpoint
        ctk.CTkLabel(
            self._remote_settings_frame,
            text="Endpoint URL:",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=20, pady=(5, 2))

        self._endpoint_entry = ctk.CTkEntry(
            self._remote_settings_frame,
            textvariable=self._endpoint_var,
            placeholder_text="https://api.example.com/transcribe",
        )
        self._endpoint_entry.pack(fill="x", padx=20, pady=(0, 10))
        if self._endpoint_var.get():
            self._set_entry_text(self._endpoint_entry, self._endpoint_var.get())

        # API Key
        ctk.CTkLabel(
            self._remote_settings_frame,
            text="API Key (optional):",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=20, pady=(5, 2))

        self._api_key_entry = ctk.CTkEntry(
            self._remote_settings_frame,
            textvariable=self._api_key_var,
            show="•",
            placeholder_text="Your API key",
        )
        self._api_key_entry.pack(fill="x", padx=20, pady=(0, 10))
        if self._api_key_var.get():
            self._set_entry_text(self._api_key_entry, self._api_key_var.get())

        # Model
        ctk.CTkLabel(
            self._remote_settings_frame,
            text="Model:",
            font=ctk.CTkFont(size=12),
        ).pack(anchor="w", padx=20, pady=(5, 2))

        self._model_entry = ctk.CTkEntry(
            self._remote_settings_frame,
            textvariable=self._model_var,
            placeholder_text="whisper-1",
        )
        self._model_entry.pack(fill="x", padx=20, pady=(0, 15))
        if self._model_var.get():
            self._set_entry_text(self._model_entry, self._model_var.get())

        self._on_mode_change()

    def _on_mode_change(self) -> None:
        """Handle transcription mode change."""
        mode_var = self._transcription_mode
        if mode_var is None:
            return

        if mode_var.get() == "remote":
            self._remote_settings_frame.pack(fill="x", pady=10)
        else:
            self._remote_settings_frame.pack_forget()

    def _create_test_content(self) -> None:
        """Create the testing step content."""
        frame = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        ctk.CTkLabel(
            frame,
            text="Let's verify everything is working correctly.",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        ).pack(anchor="w", pady=(0, 20))

        # Test results
        test_frame = ctk.CTkFrame(frame, corner_radius=12)
        test_frame.pack(fill="both", expand=True, pady=10)

        self._test_status_var = ctk.StringVar(value="Ready to test")

        ctk.CTkLabel(
            test_frame,
            textvariable=self._test_status_var,
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 10))

        self._test_textbox = ctk.CTkTextbox(
            test_frame,
            height=150,
            font=ctk.CTkFont(family="Consolas", size=12),
            state="disabled",
        )
        self._test_textbox.pack(fill="both", expand=True, padx=20, pady=(0, 15))

        self._test_button = ctk.CTkButton(
            test_frame,
            text="Run Test",
            width=120,
            command=self._run_test,
        )
        self._test_button.pack(pady=(0, 15))

    def _create_complete_content(self) -> None:
        """Create the completion step content."""
        frame = ctk.CTkFrame(self._content_frame, fg_color="transparent")
        frame.pack(fill="both", expand=True)

        # Success icon
        ctk.CTkLabel(
            frame,
            text="🎉",
            font=ctk.CTkFont(size=48),
        ).pack(pady=(20, 10))

        ctk.CTkLabel(
            frame,
            text="You're all set!",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).pack()

        ctk.CTkLabel(
            frame,
            text="Your configuration has been saved.",
            font=ctk.CTkFont(size=14),
            text_color="gray",
        ).pack(pady=(5, 20))

        # Summary
        summary_frame = ctk.CTkFrame(frame, corner_radius=12)
        summary_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            summary_frame,
            text="Your Configuration",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 10))

        hotkey_var = self._hotkey_var
        transcription_mode = self._transcription_mode

        hotkey_text = self._settings.hotkey_chord
        if hotkey_var is not None and hotkey_var.get().strip():
            hotkey_text = hotkey_var.get().strip().upper()

        mode_text = "Remote" if self._settings.remote_transcription_enabled else "Local"
        if transcription_mode is not None:
            mode_text = "Remote" if transcription_mode.get() == "remote" else "Local"
        summary_items = [
            ("Hotkey", hotkey_text),
            ("Transcription Mode", mode_text),
            ("Auto-paste", "Enabled" if self._settings.auto_paste else "Disabled"),
        ]

        for label, value in summary_items:
            row = ctk.CTkFrame(summary_frame, fg_color="transparent")
            row.pack(fill="x", padx=20, pady=3)

            ctk.CTkLabel(
                row, text=f"{label}:", font=ctk.CTkFont(size=12), width=140, anchor="w"
            ).pack(side="left")

            ctk.CTkLabel(
                row,
                text=value,
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=self.ACCENT_COLOR,
            ).pack(side="left")

        ctk.CTkLabel(summary_frame, text="").pack(pady=5)

        # Quick start
        quickstart_frame = ctk.CTkFrame(frame, corner_radius=12)
        quickstart_frame.pack(fill="x", pady=10)

        ctk.CTkLabel(
            quickstart_frame,
            text="Quick Start",
            font=ctk.CTkFont(size=14, weight="bold"),
        ).pack(anchor="w", padx=20, pady=(15, 10))

        steps = [
            "1. Press your hotkey to start recording",
            "2. Speak clearly into your microphone",
            "3. Release the hotkey to transcribe",
            "4. Text is automatically copied to clipboard!",
        ]

        for step in steps:
            ctk.CTkLabel(
                quickstart_frame,
                text=step,
                font=ctk.CTkFont(size=12),
                text_color="gray",
            ).pack(anchor="w", padx=20, pady=2)

        ctk.CTkLabel(quickstart_frame, text="").pack(pady=5)

    def _change_hotkey(self) -> None:
        """Capture a new hotkey chord from the keyboard."""
        root = self._root
        hotkey_var = self._hotkey_var
        hotkey_entry = self._hotkey_entry
        if not root or hotkey_var is None or hotkey_entry is None:
            return

        hotkey = capture_hotkey(root, title="Change Hotkey")
        if not hotkey:
            return

        hotkey_var.set(hotkey.strip().upper())
        self._set_entry_text(hotkey_entry, hotkey_var.get(), readonly=True)

    def _reset_hotkey(self) -> None:
        """Reset hotkey to default."""
        hotkey_var = self._hotkey_var
        hotkey_entry = self._hotkey_entry
        if hotkey_var is None or hotkey_entry is None:
            return
        hotkey_var.set(AppSettings().hotkey_chord)
        self._set_entry_text(hotkey_entry, hotkey_var.get(), readonly=True)

    def _validate_hotkey(self) -> bool:
        """Validate the hotkey configuration."""
        from tkinter import messagebox

        hotkey_var = self._hotkey_var
        if hotkey_var is None:
            return False

        try:
            hotkey = hotkey_var.get().strip().upper()
            chord = parse_hotkey(hotkey)
            if chord.modifier_mask == 0:
                raise HotkeyParseError(
                    "Hotkey must include at least one modifier (Ctrl/Shift/Alt/Win)"
                )
            ensure_hotkey_available(chord)
        except HotkeyInUseError as exc:
            messagebox.showerror("Hotkey Unavailable", str(exc))
            return False
        except HotkeyParseError as exc:
            messagebox.showerror("Invalid Hotkey", str(exc))
            return False
        except HotkeyRegistrationError as exc:
            messagebox.showerror("Hotkey Error", str(exc))
            return False
        return True

    def _run_test(self) -> None:
        """Run a test of the transcription setup."""
        root = self._root
        transcription_mode = self._transcription_mode
        endpoint_var = self._endpoint_var
        api_key_var = self._api_key_var
        model_var = self._model_var
        if (
            root is None
            or transcription_mode is None
            or endpoint_var is None
            or api_key_var is None
            or model_var is None
        ):
            return

        self._test_button.configure(state="disabled", text="Testing...")
        self._test_status_var.set("Running tests...")

        self._test_textbox.configure(state="normal")
        self._test_textbox.delete("1.0", "end")
        self._test_textbox.configure(state="disabled")

        def update_details(message: str):
            def update():
                self._test_textbox.configure(state="normal")
                self._test_textbox.insert("end", message + "\n")
                self._test_textbox.see("end")
                self._test_textbox.configure(state="disabled")

            root.after(0, update)

        def run_test_thread():
            try:
                update_details("Testing transcription setup...")
                mode = transcription_mode.get()
                update_details(f"Mode: {mode} transcription")

                if mode == "remote":
                    endpoint = endpoint_var.get()
                    if not endpoint:
                        update_details("❌ Remote mode requires endpoint URL")
                        root.after(
                            0,
                            lambda: self._test_button.configure(
                                state="normal", text="Run Test"
                            ),
                        )
                        root.after(0, lambda: self._test_status_var.set("Test failed"))
                        return

                    update_details(f"Endpoint: {endpoint}")
                    try:
                        load_transcriber(
                            remote_enabled=True,
                            remote_endpoint=endpoint,
                            remote_api_key=api_key_var.get(),
                            remote_model=model_var.get(),
                        )
                        update_details("✅ Remote transcriber initialized")
                    except Exception as e:
                        update_details(f"❌ Failed: {e}")
                        root.after(
                            0,
                            lambda: self._test_button.configure(
                                state="normal", text="Run Test"
                            ),
                        )
                        root.after(0, lambda: self._test_status_var.set("Test failed"))
                        return
                else:
                    try:
                        transcriber = load_transcriber(remote_enabled=False)
                        update_details("✅ Local transcriber initialized")
                        update_details(f"Provider: {transcriber.provider}")
                    except Exception as e:
                        update_details(f"❌ Failed: {e}")
                        root.after(
                            0,
                            lambda: self._test_button.configure(
                                state="normal", text="Run Test"
                            ),
                        )
                        root.after(0, lambda: self._test_status_var.set("Test failed"))
                        return

                update_details("✅ All tests passed!")
                root.after(0, lambda: self._test_status_var.set("All tests passed"))

            except Exception as e:
                update_details(f"❌ Test failed: {e}")
                root.after(0, lambda: self._test_status_var.set("Test failed"))
            finally:
                root.after(
                    0,
                    lambda: self._test_button.configure(
                        state="normal", text="Run Test"
                    ),
                )

        threading.Thread(target=run_test_thread, daemon=True).start()

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        from tkinter import messagebox

        if messagebox.askyesno(
            "Cancel Setup",
            "Are you sure you want to cancel?\n\n"
            "You can run setup again from the Settings menu.",
        ):
            self._cleanup()

    def _on_back(self) -> None:
        """Handle back button click."""
        if self._current_step > 0:
            self._show_step(self._current_step - 1)

    def _on_next(self) -> None:
        """Handle next button click."""
        step = self._steps[self._current_step]

        if step.validation_func and not step.validation_func():
            return

        if self._current_step < len(self._steps) - 1:
            self._show_step(self._current_step + 1)

    def _on_finish(self) -> None:
        """Handle finish button click."""
        hotkey_var = self._hotkey_var
        transcription_mode = self._transcription_mode
        if hotkey_var is None or transcription_mode is None:
            return

        try:
            self._settings.hotkey_chord = hotkey_var.get().strip().upper()

            mode = transcription_mode.get()
            self._settings.remote_transcription_enabled = mode == "remote"
            if mode == "remote":
                endpoint_var = self._endpoint_var
                api_key_var = self._api_key_var
                model_var = self._model_var
                if endpoint_var is None or api_key_var is None or model_var is None:
                    raise RuntimeError("Remote settings controls were not initialized")

                self._settings.remote_transcription_endpoint = (
                    endpoint_var.get().strip()
                )
                self._settings.remote_transcription_api_key = api_key_var.get().strip()
                self._settings.remote_transcription_model = model_var.get().strip()

            self._settings.first_run_complete = True
            self._settings.save()

            LOGGER.info("Onboarding completed successfully")

        except Exception as exc:
            LOGGER.error("Failed to save onboarding settings: %s", exc)
            from tkinter import messagebox

            messagebox.showerror("Save Error", "Failed to save settings.")
            return

        self._is_complete = True
        self._cleanup()

        if self._on_complete:
            self._on_complete()

    def _cleanup(self) -> None:
        """Cleanup the wizard window."""
        if self._root:
            try:
                self._root.quit()
                self._root.destroy()
            except Exception:
                pass
            self._root = None
