"""Toast notification system for user feedback."""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass
from typing import Callable, Optional

import customtkinter as ctk

LOGGER = logging.getLogger("hoppy_whisper.toast")


@dataclass
class ToastConfig:
    """Configuration for toast notifications."""

    duration_ms: int = 4000
    max_width: int = 380
    fade_duration_ms: int = 300
    padding: int = 20
    corner_radius: int = 12


class Toast:
    """Individual toast notification with modern styling."""

    # Color schemes for different toast types
    TYPE_COLORS = {
        "info": {"bg": "#1e3a5f", "fg": "#ffffff", "accent": "#3b82f6"},
        "success": {"bg": "#14532d", "fg": "#ffffff", "accent": "#22c55e"},
        "warning": {"bg": "#713f12", "fg": "#ffffff", "accent": "#eab308"},
        "error": {"bg": "#7f1d1d", "fg": "#ffffff", "accent": "#ef4444"},
    }

    def __init__(
        self,
        parent: ctk.CTk,
        message: str,
        title: str = "",
        toast_type: str = "info",
        config: Optional[ToastConfig] = None,
        on_click: Optional[Callable[[], None]] = None,
    ):
        self._parent = parent
        self._message = message
        self._title = title
        self._toast_type = toast_type
        self._config = config or ToastConfig()
        self._on_click = on_click
        self._root: Optional[ctk.CTkToplevel] = None
        self._auto_destroy_after_id: Optional[str] = None
        self._is_visible = False

    def show(self) -> None:
        """Display the toast notification."""
        if self._root and self._root.winfo_exists():
            self._root.lift()
            return

        self._create_window()
        self._position_window()
        self._show_with_fade()
        self._schedule_auto_destroy()

    def hide(self) -> None:
        """Hide the toast with fade effect."""
        if not self._root or not self._is_visible:
            return
        self._fade_out()

    def _create_window(self) -> None:
        """Create the toast window with modern styling."""
        colors = self.TYPE_COLORS.get(self._toast_type, self.TYPE_COLORS["info"])

        self._root = ctk.CTkToplevel(self._parent)
        self._root.withdraw()
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)

        # Set transparency
        try:
            self._root.attributes("-alpha", 0.0)
        except Exception:
            pass

        # Main frame with rounded corners
        main_frame = ctk.CTkFrame(
            self._root,
            fg_color=colors["bg"],
            corner_radius=self._config.corner_radius,
            border_width=2,
            border_color=colors["accent"],
        )
        main_frame.pack(
            fill="both",
            expand=True,
            padx=2,
            pady=2,
        )

        # Content frame
        content_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        content_frame.pack(
            fill="both",
            expand=True,
            padx=self._config.padding,
            pady=self._config.padding,
        )

        # Icon based on type
        icons = {"info": "ℹ️", "success": "✓", "warning": "⚠", "error": "✕"}
        icon = icons.get(self._toast_type, "ℹ️")

        # Header with icon and title
        if self._title:
            header_frame = ctk.CTkFrame(content_frame, fg_color="transparent")
            header_frame.pack(fill="x", pady=(0, 8))

            icon_label = ctk.CTkLabel(
                header_frame,
                text=icon,
                font=ctk.CTkFont(size=16, weight="bold"),
                text_color=colors["accent"],
            )
            icon_label.pack(side="left", padx=(0, 8))

            title_label = ctk.CTkLabel(
                header_frame,
                text=self._title,
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=colors["fg"],
                anchor="w",
            )
            title_label.pack(side="left", fill="x", expand=True)

        # Message
        message_label = ctk.CTkLabel(
            content_frame,
            text=self._message,
            font=ctk.CTkFont(size=13),
            text_color=colors["fg"],
            anchor="w",
            justify="left",
            wraplength=self._config.max_width - 2 * self._config.padding - 20,
        )
        message_label.pack(fill="x")

        # Bind click events
        if self._on_click:

            def on_click_handler(event=None):
                if self._on_click:
                    self._on_click()
                self.hide()

            for widget in [main_frame, content_frame, message_label]:
                widget.bind("<Button-1>", on_click_handler)
            if self._title:
                header_frame.bind("<Button-1>", on_click_handler)

        # Hover effect
        def on_enter(event):
            try:
                self._root.attributes("-alpha", 0.98)
            except Exception:
                pass

        def on_leave(event):
            try:
                self._root.attributes("-alpha", 0.95)
            except Exception:
                pass

        main_frame.bind("<Enter>", on_enter)
        main_frame.bind("<Leave>", on_leave)

    def _position_window(self) -> None:
        """Position the toast in the bottom-right corner."""
        if not self._root:
            return

        self._root.update_idletasks()

        width = min(self._config.max_width, max(250, self._root.winfo_reqwidth()))
        height = self._root.winfo_reqheight()

        screen_width = self._root.winfo_screenwidth()
        screen_height = self._root.winfo_screenheight()

        margin = 24
        x = screen_width - width - margin
        y = screen_height - height - margin - 48  # Account for taskbar

        self._root.geometry(f"{width}x{height}+{x}+{y}")

    def _show_with_fade(self) -> None:
        """Show the toast with fade-in effect."""
        if not self._root:
            return

        self._is_visible = True
        self._root.deiconify()
        self._fade_in()

    def _fade_in(self) -> None:
        """Fade in the toast window."""

        def fade_step(alpha: float):
            if not self._root or not self._root.winfo_exists():
                return

            if alpha < 0.95:
                try:
                    self._root.attributes("-alpha", alpha)
                except Exception:
                    pass
                self._root.after(20, lambda: fade_step(alpha + 0.1))
            else:
                try:
                    self._root.attributes("-alpha", 0.95)
                except Exception:
                    pass

        fade_step(0.0)

    def _fade_out(self) -> None:
        """Fade out the toast window."""
        if not self._root:
            return

        def fade_step(alpha: float):
            if not self._root or not self._root.winfo_exists():
                return

            if alpha > 0.0:
                try:
                    self._root.attributes("-alpha", alpha)
                except Exception:
                    pass
                self._root.after(20, lambda: fade_step(alpha - 0.15))
            else:
                self._destroy()

        fade_step(0.95)

    def _schedule_auto_destroy(self) -> None:
        """Schedule automatic destruction of the toast."""
        if not self._root:
            return

        total_duration = self._config.duration_ms
        self._auto_destroy_after_id = self._root.after(total_duration, self._fade_out)

    def _destroy(self) -> None:
        """Destroy the toast window."""
        self._is_visible = False

        if self._auto_destroy_after_id:
            after_id = self._auto_destroy_after_id
            self._auto_destroy_after_id = None
            root = self._root
            if root:
                try:
                    root.after_cancel(after_id)
                except Exception:
                    pass

        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None


class ToastManager:
    """Manager for toast notifications."""

    def __init__(
        self,
        parent: Optional[ctk.CTk] = None,
        config: Optional[ToastConfig] = None,
    ):
        self._parent = parent or self._get_root_window()
        self._config = config or ToastConfig()
        self._toasts: list[Toast] = []
        self._lock = threading.Lock()

    def _get_root_window(self) -> ctk.CTk:
        """Get or create a root window for the toast manager."""
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        root = ctk.CTk()
        root.withdraw()
        root.title("Hoppy Whisper Toast Manager")
        return root

    def show_toast(
        self,
        message: str,
        title: str = "",
        toast_type: str = "info",
        duration_ms: Optional[int] = None,
        on_click: Optional[Callable[[], None]] = None,
    ) -> Toast:
        """Show a toast notification."""
        config = ToastConfig(**{**self._config.__dict__})
        if duration_ms is not None:
            config.duration_ms = duration_ms

        toast = Toast(
            parent=self._parent,
            message=message,
            title=title,
            toast_type=toast_type,
            config=config,
            on_click=on_click,
        )

        with self._lock:
            self._toasts.append(toast)

        def show_on_main_thread():
            toast.show()

            def check_and_cleanup():
                if not toast._root or not toast._root.winfo_exists():
                    with self._lock:
                        if toast in self._toasts:
                            self._toasts.remove(toast)
                else:
                    toast._root.after(1000, check_and_cleanup)

            if toast._root:
                toast._root.after(1000, check_and_cleanup)

        try:
            self._parent.after(0, show_on_main_thread)
        except Exception:
            threading.Thread(target=show_on_main_thread, daemon=True).start()

        return toast

    def info(self, message: str, title: str = "", **kwargs) -> Toast:
        """Show info toast."""
        return self.show_toast(message, title, "info", **kwargs)

    def success(self, message: str, title: str = "", **kwargs) -> Toast:
        """Show success toast."""
        return self.show_toast(message, title, "success", **kwargs)

    def warning(self, message: str, title: str = "", **kwargs) -> Toast:
        """Show warning toast."""
        return self.show_toast(message, title, "warning", **kwargs)

    def error(self, message: str, title: str = "", **kwargs) -> Toast:
        """Show error toast."""
        return self.show_toast(message, title, "error", **kwargs)

    def hide_all(self) -> None:
        """Hide all visible toasts."""
        with self._lock:
            for toast in self._toasts[:]:
                toast.hide()

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.hide_all()

        try:
            if self._parent and self._parent.winfo_exists():
                if (
                    hasattr(self._parent, "title")
                    and self._parent.title() == "Hoppy Whisper Toast Manager"
                ):
                    self._parent.destroy()
        except Exception:
            pass
