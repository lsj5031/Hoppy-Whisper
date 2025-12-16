"""Toast notification system for user feedback."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from dataclasses import dataclass
from typing import Callable, Optional

LOGGER = logging.getLogger("hoppy_whisper.toast")


@dataclass
class ToastConfig:
    """Configuration for toast notifications."""
    duration_ms: int = 4000
    max_width: int = 350
    fade_duration_ms: int = 300
    padding: int = 15
    background: str = "#2d3748"
    foreground: str = "#ffffff"
    border_color: str = "#4a5568"
    border_width: int = 1
    corner_radius: int = 8


class Toast:
    """Individual toast notification."""

    def __init__(
        self,
        parent: tk.Toplevel,
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
        self._root: Optional[tk.Toplevel] = None
        self._fade_after_id: Optional[str] = None
        self._auto_destroy_after_id: Optional[str] = None
        self._is_visible = False

        # Color scheme for different toast types
        self._type_colors = {
            "info": ("#3182ce", "#ffffff"),      # blue
            "success": ("#38a169", "#ffffff"),    # green
            "warning": ("#d69e2e", "#000000"),    # yellow
            "error": ("#e53e3e", "#ffffff"),      # red
        }

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
        """Create the toast window."""
        self._root = tk.Toplevel(self._parent)
        self._root.withdraw()  # Start hidden for fade-in effect
        self._root.overrideredirect(True)  # Remove window decorations
        self._root.configure(bg=self._config.background)

        # Configure window attributes for better appearance
        try:
            # Try to make it transparent for rounded corners effect
            if hasattr(self._root, "attributes"):
                self._root.attributes("-alpha", 0.0)  # Start transparent
        except Exception:
            pass  # Fallback if transparency not supported

        # Create main frame
        main_frame = tk.Frame(
            self._root,
            bg=self._config.background,
            highlightthickness=self._config.border_width,
            highlightbackground=self._config.border_color,
            relief="flat",
            bd=0,
        )
        main_frame.pack(
            fill="both",
            expand=True,
            padx=self._config.padding,
            pady=self._config.padding,
        )

        # Add content
        if self._title:
            title_label = tk.Label(
                main_frame,
                text=self._title,
                font=("Segoe UI", 9, "bold"),
                bg=self._config.background,
                fg=self._get_type_colors()[1],
                anchor="w",
            )
            title_label.pack(fill="x", pady=(0, 2))

        message_label = tk.Label(
            main_frame,
            text=self._message,
            font=("Segoe UI", 9),
            bg=self._config.background,
            fg=self._get_type_colors()[1],
            anchor="w",
            wraplength=self._config.max_width - 2 * self._config.padding,
            justify="left",
        )
        message_label.pack(fill="x")

        # Bind click events
        if self._on_click:
            def on_click_handler(event=None):
                if self._on_click:
                    self._on_click()
                    self.hide()

            main_frame.bind("<Button-1>", on_click_handler)
            title_label.bind("<Button-1>", on_click_handler)
            message_label.bind("<Button-1>", on_click_handler)

        # Add hover effects
        def on_enter(event):
            try:
                if hasattr(self._root, "attributes"):
                    self._root.attributes("-alpha", 0.95)
            except Exception:
                pass

        def on_leave(event):
            try:
                if hasattr(self._root, "attributes"):
                    self._root.attributes("-alpha", 0.9)
            except Exception:
                pass

        main_frame.bind("<Enter>", on_enter)
        main_frame.bind("<Leave>", on_leave)

    def _get_type_colors(self) -> tuple[str, str]:
        """Get colors for the current toast type."""
        return self._type_colors.get(self._toast_type, self._type_colors["info"])

    def _position_window(self) -> None:
        """Position the toast in the bottom-right corner."""
        if not self._root:
            return

        # Update geometry to get proper dimensions
        self._root.update_idletasks()

        width = min(self._config.max_width, max(200, self._root.winfo_reqwidth()))
        height = self._root.winfo_reqheight()

        # Get screen dimensions
        screen_width = self._root.winfo_screenwidth()
        screen_height = self._root.winfo_screenheight()

        # Position in bottom-right corner with margin
        margin = 20
        x = screen_width - width - margin
        y = screen_height - height - margin

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

            if alpha < 0.9:
                try:
                    if hasattr(self._root, "attributes"):
                        self._root.attributes("-alpha", alpha)
                except Exception:
                    pass
                # Schedule next step
                self._root.after(20, lambda: fade_step(alpha + 0.1))
            else:
                try:
                    if hasattr(self._root, "attributes"):
                        self._root.attributes("-alpha", 0.9)
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
                    if hasattr(self._root, "attributes"):
                        self._root.attributes("-alpha", alpha)
                except Exception:
                    pass
                # Schedule next step
                self._root.after(20, lambda: fade_step(alpha - 0.1))
            else:
                self._destroy()

        try:
            if hasattr(self._root, "attributes"):
                self._root.attributes("-alpha", 0.9)
        except Exception:
            pass

        fade_step(0.9)

    def _schedule_auto_destroy(self) -> None:
        """Schedule automatic destruction of the toast."""
        if not self._root:
            return

        # Calculate total duration including fade
        total_duration = self._config.duration_ms + self._config.fade_duration_ms
        self._auto_destroy_after_id = self._root.after(
            total_duration, self._fade_out
        )

    def _destroy(self) -> None:
        """Destroy the toast window."""
        self._is_visible = False

        if self._fade_after_id:
            try:
                self._root.after_cancel(self._fade_after_id)  # type: ignore[union-attr]
            except Exception:
                pass
            self._fade_after_id = None

        if self._auto_destroy_after_id:
            try:
                self._root.after_cancel(self._auto_destroy_after_id)  # type: ignore[union-attr]
            except Exception:
                pass
            self._auto_destroy_after_id = None

        if self._root:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None


class ToastManager:
    """Manager for toast notifications."""

    def __init__(
        self, parent: Optional[tk.Tk] = None, config: Optional[ToastConfig] = None
    ):
        self._parent = parent or self._get_root_window()
        self._config = config or ToastConfig()
        self._toasts: list[Toast] = []
        self._lock = threading.Lock()

    def _get_root_window(self) -> tk.Tk:
        """Get or create a root window for the toast manager."""
        root = tk.Tk()
        root.withdraw()  # Hide the window
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

        # Show on main thread
        def show_on_main_thread():
            toast.show()

            # Remove from list when destroyed
            def on_destroy():
                with self._lock:
                    if toast in self._toasts:
                        self._toasts.remove(toast)

            # This is a bit of a hack, but we can poll for destruction
            def check_and_cleanup():
                if not toast._root or not toast._root.winfo_exists():
                    on_destroy()
                else:
                    toast._root.after(1000, check_and_cleanup)  # Check every second

            toast._root.after(1000, check_and_cleanup)  # type: ignore[union-attr]

        # Schedule on main thread if we're not already on it
        try:
            self._parent.after(0, show_on_main_thread)
        except Exception:
            # Fallback if parent is not available
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
            # Copy list to avoid modification during iteration
            for toast in self._toasts[:]:
                toast.hide()

    def cleanup(self) -> None:
        """Cleanup resources."""
        self.hide_all()

        # Destroy the parent window if we created it
        try:
            if self._parent and self._parent.winfo_exists():
                # Only destroy if it's our managed window
                if (hasattr(self._parent, 'title') and
                    self._parent.title() == "Hoppy Whisper Toast Manager"):
                    self._parent.destroy()
        except Exception:
            pass
