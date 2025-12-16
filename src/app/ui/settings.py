"""Settings management window for Hoppy Whisper."""

from __future__ import annotations

import logging
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Optional

from app.settings import AppSettings

LOGGER = logging.getLogger("hoppy_whisper.settings")


class SettingsWindow:
    """Settings window for managing application configuration."""

    def __init__(self, settings: AppSettings, on_apply: Optional[callable] = None):
        self._settings = settings
        self._on_apply = on_apply
        self._root: Optional[tk.Tk] = None
        self._original_settings = settings.to_dict()  # Backup for cancellation
        self._modified = False

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
        self._root = tk.Tk()
        self._root.title("Hoppy Whisper Settings")
        self._root.geometry("700x600")
        self._root.resizable(True, True)

        # Configure grid
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(0, weight=1)

        # Create notebook for tabs
        self._notebook = ttk.Notebook(self._root)
        self._notebook.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        # Button frame
        button_frame = ttk.Frame(self._root)
        button_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))

        # Cancel button
        ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
        ).pack(side="right", padx=(10, 0))

        # Apply button
        self._apply_button = ttk.Button(
            button_frame,
            text="Apply",
            command=self._on_apply_click,
            state="disabled",
        )
        self._apply_button.pack(side="right")

        # OK button
        ttk.Button(
            button_frame,
            text="OK",
            command=self._on_ok,
        ).pack(side="right")

        # Help text
        help_label = ttk.Label(
            button_frame,
            text="Settings are automatically saved when you click OK or Apply",
            foreground="gray",
        )
        help_label.pack(side="left")

        # Handle window close
        self._root.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Center window on screen
        self._center_window()

        # Track modifications
        self._root.bind("<<Modified>>", self._on_modified)

    def _center_window(self) -> None:
        """Center the window on the screen."""
        if not self._root:
            return
        self._root.update_idletasks()
        width = self._root.winfo_width()
        height = self._root.winfo_height()
        x = (self._root.winfo_screenwidth() // 2) - (width // 2)
        y = (self._root.winfo_screenheight() // 2) - (height // 2)
        self._root.geometry(f"{width}x{height}+{x}+{y}")

    def _setup_tabs(self) -> None:
        """Setup all settings tabs."""
        # General tab
        general_frame = ttk.Frame(self._notebook)
        self._notebook.add(general_frame, text="General")
        self._create_general_tab(general_frame)

        # Hotkey tab
        hotkey_frame = ttk.Frame(self._notebook)
        self._notebook.add(hotkey_frame, text="Hotkey")
        self._create_hotkey_tab(hotkey_frame)

        # Transcription tab
        transcription_frame = ttk.Frame(self._notebook)
        self._notebook.add(transcription_frame, text="Transcription")
        self._create_transcription_tab(transcription_frame)

        # History tab
        history_frame = ttk.Frame(self._notebook)
        self._notebook.add(history_frame, text="History")
        self._create_history_tab(history_frame)

        # Advanced tab
        advanced_frame = ttk.Frame(self._notebook)
        self._notebook.add(advanced_frame, text="Advanced")
        self._create_advanced_tab(advanced_frame)

    def _create_general_tab(self, parent: ttk.Frame) -> None:
        """Create the general settings tab."""
        parent.columnconfigure(0, weight=1)

        # Startup settings
        startup_frame = ttk.LabelFrame(parent, text="Startup", padding=15)
        startup_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        startup_frame.columnconfigure(1, weight=1)

        # Start with Windows
        self._start_with_windows_var = tk.BooleanVar(value=self._settings.start_with_windows)
        ttk.Checkbutton(
            startup_frame,
            text="Start Hoppy Whisper with Windows",
            variable=self._start_with_windows_var,
        ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # Telemetry
        self._telemetry_var = tk.BooleanVar(value=self._settings.telemetry_enabled)
        ttk.Checkbutton(
            startup_frame,
            text="Enable performance telemetry (helps improve the app)",
            variable=self._telemetry_var,
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(0, 10))

        # About section
        about_frame = ttk.LabelFrame(parent, text="About", padding=15)
        about_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        about_text = """
Hoppy Whisper - Speech Transcription Tool
Version: 1.0.0

Transform your speech into text with privacy-first local transcription
or flexible remote transcription options.

Features:
• Local AI-powered transcription
• Global hotkey support
• Automatic clipboard integration
• Comprehensive history search
• Windows integration

© 2024 Hoppy Whisper
        """

        about_label = ttk.Label(
            about_frame,
            text=about_text.strip(),
            font=("Segoe UI", 9),
            justify="left",
        )
        about_label.pack()

    def _create_hotkey_tab(self, parent: ttk.Frame) -> None:
        """Create the hotkey settings tab."""
        parent.columnconfigure(0, weight=1)

        # Hotkey configuration
        hotkey_frame = ttk.LabelFrame(parent, text="Hotkey Configuration", padding=15)
        hotkey_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        hotkey_frame.columnconfigure(1, weight=1)

        # Current hotkey
        ttk.Label(hotkey_frame, text="Current hotkey:").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        self._hotkey_var = tk.StringVar(value=self._settings.hotkey_chord)
        hotkey_display = ttk.Entry(
            hotkey_frame,
            textvariable=self._hotkey_var,
            state="readonly",
            font=("Consolas", 10),
        )
        hotkey_display.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))

        # Change hotkey button
        ttk.Button(
            hotkey_frame,
            text="Change Hotkey",
            command=self._change_hotkey,
        ).grid(row=2, column=0, sticky="w", pady=(0, 10))

        # Reset to default
        ttk.Button(
            hotkey_frame,
            text="Reset to Default (Ctrl+Shift+;)",
            command=self._reset_hotkey,
        ).grid(row=2, column=1, sticky="w", padx=(10, 0), pady=(0, 10))

        # Advanced hotkey settings
        advanced_frame = ttk.LabelFrame(parent, text="Advanced", padding=15)
        advanced_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        advanced_frame.columnconfigure(0, weight=1)

        # Paste window timing
        ttk.Label(advanced_frame, text="Paste window (seconds):").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        self._paste_window_var = tk.DoubleVar(value=self._settings.paste_window_seconds)
        paste_window_spinbox = ttk.Spinbox(
            advanced_frame,
            from_=0.5,
            to=10.0,
            increment=0.5,
            textvariable=self._paste_window_var,
            width=10,
        )
        paste_window_spinbox.grid(row=1, column=0, sticky="w", pady=(0, 15))

        # Auto-paste
        self._auto_paste_var = tk.BooleanVar(value=self._settings.auto_paste)
        ttk.Checkbutton(
            advanced_frame,
            text="Automatically paste transcribed text",
            variable=self._auto_paste_var,
        ).grid(row=2, column=0, sticky="w", pady=(0, 10))

        # Timing settings
        timing_frame = ttk.LabelFrame(parent, text="Timing (milliseconds)", padding=15)
        timing_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        timing_frame.columnconfigure(1, weight=1)

        # Transcribe start delay
        ttk.Label(timing_frame, text="Transcribe start delay:").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        self._transcribe_start_delay_var = tk.IntVar(value=int(self._settings.transcribe_start_delay_ms))
        transcribe_delay_spinbox = ttk.Spinbox(
            timing_frame,
            from_=100,
            to=5000,
            increment=100,
            textvariable=self._transcribe_start_delay_var,
            width=10,
        )
        transcribe_delay_spinbox.grid(row=1, column=0, sticky="w", pady=(0, 15))

        # Paste predelay
        ttk.Label(timing_frame, text="Paste predelay:").grid(
            row=2, column=0, sticky="w", pady=(0, 5)
        )

        self._paste_predelay_var = tk.IntVar(value=int(self._settings.paste_predelay_ms))
        paste_predelay_spinbox = ttk.Spinbox(
            timing_frame,
            from_=50,
            to=1000,
            increment=50,
            textvariable=self._paste_predelay_var,
            width=10,
        )
        paste_predelay_spinbox.grid(row=3, column=0, sticky="w", pady=(0, 15))

        # Idle reset delay
        ttk.Label(timing_frame, text="Idle reset delay:").grid(
            row=4, column=0, sticky="w", pady=(0, 5)
        )

        self._idle_reset_delay_var = tk.IntVar(value=int(self._settings.idle_reset_delay_ms))
        idle_reset_spinbox = ttk.Spinbox(
            timing_frame,
            from_=500,
            to=10000,
            increment=100,
            textvariable=self._idle_reset_delay_var,
            width=10,
        )
        idle_reset_spinbox.grid(row=5, column=0, sticky="w", pady=(0, 15))

    def _create_transcription_tab(self, parent: ttk.Frame) -> None:
        """Create the transcription settings tab."""
        parent.columnconfigure(0, weight=1)

        # Transcription mode selection
        mode_frame = ttk.LabelFrame(parent, text="Transcription Method", padding=15)
        mode_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self._remote_transcription_enabled_var = tk.BooleanVar(
            value=self._settings.remote_transcription_enabled
        )

        # Local transcription option
        local_frame = ttk.Frame(mode_frame)
        local_frame.grid(row=0, column=0, sticky="ew", pady=10)
        local_frame.columnconfigure(1, weight=1)

        local_radio = ttk.Radiobutton(
            local_frame,
            variable=self._remote_transcription_enabled_var,
            value=False,
            text="Local Transcription (Recommended)",
            font=("Segoe UI", 11, "bold"),
        )
        local_radio.grid(row=0, column=0, sticky="w", pady=(0, 5))

        local_desc = ttk.Label(
            local_frame,
            text="Speech is transcribed locally on your computer using AI models. "
                 "This provides better privacy and works offline after initial setup.",
            font=("Segoe UI", 9),
            foreground="gray",
            wraplength=500,
            justify="left",
        )
        local_desc.grid(row=1, column=0, sticky="w")

        # Remote transcription option
        remote_frame = ttk.Frame(mode_frame)
        remote_frame.grid(row=1, column=0, sticky="ew", pady=10)
        remote_frame.columnconfigure(1, weight=1)

        remote_radio = ttk.Radiobutton(
            remote_frame,
            variable=self._remote_transcription_enabled_var,
            value=True,
            text="Remote Transcription",
            font=("Segoe UI", 11, "bold"),
        )
        remote_radio.grid(row=0, column=0, sticky="w", pady=(0, 5))

        remote_desc = ttk.Label(
            remote_frame,
            text="Speech is sent to a remote service for transcription. "
                 "Requires internet connection and API configuration.",
            font=("Segoe UI", 9),
            foreground="gray",
            wraplength=500,
            justify="left",
        )
        remote_desc.grid(row=1, column=0, sticky="w")

        # Remote settings frame
        self._remote_settings_frame = ttk.LabelFrame(
            mode_frame,
            text="Remote Transcription Settings",
            padding=15,
        )
        self._remote_settings_frame.grid(
            row=2, column=0, sticky="ew",
            pady=(15, 0)
        )
        self._remote_settings_frame.columnconfigure(1, weight=1)

        # Endpoint URL
        ttk.Label(self._remote_settings_frame, text="Endpoint URL:").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        self._remote_endpoint_var = tk.StringVar(
            value=self._settings.remote_transcription_endpoint
        )
        endpoint_entry = ttk.Entry(
            self._remote_settings_frame,
            textvariable=self._remote_endpoint_var,
        )
        endpoint_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=(0, 5))

        # API Key
        ttk.Label(self._remote_settings_frame, text="API Key:").grid(
            row=1, column=0, sticky="w", pady=(0, 5)
        )

        self._remote_api_key_var = tk.StringVar(
            value=self._settings.remote_transcription_api_key
        )
        api_key_entry = ttk.Entry(
            self._remote_settings_frame,
            textvariable=self._remote_api_key_var,
            show="*",
        )
        api_key_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 5))

        # Model
        ttk.Label(self._remote_settings_frame, text="Model:").grid(
            row=2, column=0, sticky="w", pady=(0, 5)
        )

        self._remote_model_var = tk.StringVar(
            value=self._settings.remote_transcription_model
        )
        model_entry = ttk.Entry(
            self._remote_settings_frame,
            textvariable=self._remote_model_var,
        )
        model_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=(0, 15))

        # Test connection button
        ttk.Button(
            self._remote_settings_frame,
            text="Test Connection",
            command=self._test_remote_connection,
        ).grid(row=3, column=0, columnspan=2)

        # Bind to show/hide remote settings
        def on_mode_change(*args):
            if self._remote_transcription_enabled_var.get():
                self._remote_settings_frame.grid()
            else:
                self._remote_settings_frame.grid_remove()

        self._remote_transcription_enabled_var.trace_add("write", on_mode_change)
        on_mode_change()  # Initial call

    def _create_history_tab(self, parent: ttk.Frame) -> None:
        """Create the history settings tab."""
        parent.columnconfigure(0, weight=1)

        # History retention
        retention_frame = ttk.LabelFrame(parent, text="History Retention", padding=15)
        retention_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        retention_frame.columnconfigure(1, weight=1)

        ttk.Label(retention_frame, text="Keep history for (days):").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        self._history_retention_var = tk.IntVar(
            value=self._settings.history_retention_days
        )
        retention_spinbox = ttk.Spinbox(
            retention_frame,
            from_=7,
            to=365,
            increment=1,
            textvariable=self._history_retention_var,
            width=10,
        )
        retention_spinbox.grid(row=1, column=0, sticky="w", pady=(0, 15))

        # History actions
        actions_frame = ttk.LabelFrame(parent, text="History Actions", padding=15)
        actions_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        # Export history
        ttk.Button(
            actions_frame,
            text="Export History",
            command=self._export_history,
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Clear history
        ttk.Button(
            actions_frame,
            text="Clear All History",
            command=self._clear_history,
        ).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 10))

        # History info
        info_label = ttk.Label(
            actions_frame,
            text="History is stored locally on your computer and never leaves "
            "your device.",
            font=("Segoe UI", 9),
            foreground="gray",
        )
        info_label.grid(row=1, column=0, columnspan=2, sticky="w", pady=(10, 0))

    def _create_advanced_tab(self, parent: ttk.Frame) -> None:
        """Create the advanced settings tab."""
        parent.columnconfigure(0, weight=1)

        # Configuration management
        config_frame = ttk.LabelFrame(
            parent, text="Configuration Management", padding=15
        )
        config_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        # Export settings
        ttk.Button(
            config_frame,
            text="Export Settings",
            command=self._export_settings,
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Import settings
        ttk.Button(
            config_frame,
            text="Import Settings",
            command=self._import_settings,
        ).grid(row=0, column=1, sticky="w", padx=(10, 0), pady=(0, 10))

        # Reset to defaults
        ttk.Button(
            config_frame,
            text="Reset to Defaults",
            command=self._reset_to_defaults,
        ).grid(row=1, column=0, columnspan=2, pady=(10, 0))

        # Diagnostics
        diag_frame = ttk.LabelFrame(parent, text="Diagnostics", padding=15)
        diag_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)

        # View logs
        ttk.Button(
            diag_frame,
            text="View Log File",
            command=self._view_logs,
        ).grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Reset onboarding
        onboarding_frame = ttk.LabelFrame(parent, text="Onboarding", padding=15)
        onboarding_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        # Reset first run
        ttk.Button(
            onboarding_frame,
            text="Reset First-Run Setup",
            command=self._reset_first_run,
        ).grid(row=0, column=0, sticky="w")

    def _change_hotkey(self) -> None:
        """Change the hotkey through a simple dialog."""
        current_hotkey = self._hotkey_var.get()

        new_hotkey = tk.simpledialog.askstring(
            "Change Hotkey",
            f"Enter new hotkey combination:\n\nCurrent: {current_hotkey}"
            "\n\nExample: CTRL+SHIFT+H",
            parent=self._root,
        )

        if new_hotkey and new_hotkey.strip():
            # Basic validation
            hotkey = new_hotkey.strip().upper()
            if "+" in hotkey and len(hotkey) > 3:
                self._hotkey_var.set(hotkey)

    def _reset_hotkey(self) -> None:
        """Reset hotkey to default."""
        self._hotkey_var.set("CTRL+SHIFT+;")

    def _test_remote_connection(self) -> None:
        """Test the remote transcription connection."""
        endpoint = self._remote_endpoint_var.get()
        if not endpoint:
            messagebox.showerror("Test Failed", "Please enter an endpoint URL first.")
            return

        # This is a simplified test - in a real implementation,
        # you'd want to actually test the connection
        messagebox.showinfo(
            "Test Result",
            "Connection test placeholder. In a full implementation, "
            "this would test the actual remote transcription endpoint.",
        )

    def _export_history(self) -> None:
        """Export history to a file."""
        from app.history.dao import HistoryDAO
        from app.settings import default_history_db_path

        try:
            dao = HistoryDAO(
                default_history_db_path(),
                retention_days=self._settings.history_retention_days,
            )
            dao.open()

            # Use the existing history export functionality
            # Note: This would open a modal dialog, so in a real implementation
            # you'd want to extract the export logic
            messagebox.showinfo(
                "Export History",
                "Use the History window from the tray menu to export your history.",
            )

            dao.close()
        except Exception as exc:
            messagebox.showerror("Export Failed", f"Failed to export history: {exc}")

    def _clear_history(self) -> None:
        """Clear all history with confirmation."""
        result = messagebox.askyesno(
            "Clear History",
            "Are you sure you want to delete all transcription history?"
            "\n\nThis action cannot be undone.",
            icon="warning",
        )

        if not result:
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

            messagebox.showinfo(
                "Clear History", f"Successfully deleted {deleted} records."
            )
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
            import json
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
            import json
            with open(file_path, "r", encoding="utf-8") as f:
                settings_data = json.load(f)

            # Validate and create new settings
            new_settings = AppSettings.from_dict(settings_data)

            result = messagebox.askyesno(
                "Import Settings",
                "This will replace your current settings. Continue?",
            )

            if result:
                self._settings = new_settings
                messagebox.showinfo(
                    "Import Settings", "Settings imported successfully."
                )
                self._root.destroy()  # Close settings window
                # In a real implementation, you'd refresh the UI
        except Exception as exc:
            messagebox.showerror("Import Failed", f"Failed to import settings: {exc}")

    def _reset_to_defaults(self) -> None:
        """Reset all settings to defaults."""
        result = messagebox.askyesno(
            "Reset Settings",
            "This will reset all settings to their default values. Continue?",
        )

        if not result:
            return

        try:
            self._settings = AppSettings()  # Creates default settings
            messagebox.showinfo("Reset Settings", "Settings reset to defaults.")
            self._root.destroy()  # Close settings window
            # In a real implementation, you'd refresh the UI
        except Exception as exc:
            messagebox.showerror("Reset Failed", f"Failed to reset settings: {exc}")

    def _view_logs(self) -> None:
        """Open the log file in the default text editor."""
        try:
            import subprocess
            import sys

            # Find the most recent log file
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
        result = messagebox.askyesno(
            "Reset Onboarding",
            "This will reset the first-run setup, and the onboarding wizard "
            "will appear next time you start the app. Continue?",
        )

        if result:
            self._settings.first_run_complete = False
            messagebox.showinfo(
                "Reset Onboarding", "First-run setup will appear on next startup."
            )

    def _on_modified(self, event) -> None:
        """Handle window modification to track changes."""
        if self._root and self._root.tk.call("winfo", "exists", str(event.widget)):
            self._modified = True
            self._apply_button.config(state="normal")
            self._root.tk.call("wm", "attributes", str(self._root), "-modified", "0")

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if self._modified:
            result = messagebox.askyesno(
                "Discard Changes",
                "You have unsaved changes. Are you sure you want to cancel?",
            )
            if not result:
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
            # Update settings from UI variables
            self._settings.start_with_windows = self._start_with_windows_var.get()
            self._settings.telemetry_enabled = self._telemetry_var.get()
            self._settings.hotkey_chord = self._hotkey_var.get()
            self._settings.paste_window_seconds = self._paste_window_var.get()
            self._settings.auto_paste = self._auto_paste_var.get()
            self._settings.transcribe_start_delay_ms = float(
                self._transcribe_start_delay_var.get()
            )
            self._settings.paste_predelay_ms = float(
                self._paste_predelay_var.get()
            )
            self._settings.idle_reset_delay_ms = float(
                self._idle_reset_delay_var.get()
            )
            self._settings.history_retention_days = self._history_retention_var.get()

            # Transcription settings
            self._settings.remote_transcription_enabled = (
                self._remote_transcription_enabled_var.get()
            )
            if self._remote_transcription_enabled_var.get():
                self._settings.remote_transcription_endpoint = (
                    self._remote_endpoint_var.get()
                )
                self._settings.remote_transcription_api_key = (
                    self._remote_api_key_var.get()
                )
                self._settings.remote_transcription_model = (
                    self._remote_model_var.get()
                )

            # Save to disk
            self._settings.save()

            self._modified = False
            self._apply_button.config(state="disabled")

            # Call on_apply callback if provided
            if self._on_apply:
                self._on_apply()

            return True

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
