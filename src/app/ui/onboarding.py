"""First-run onboarding wizard for new users."""

from __future__ import annotations

import logging
import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Callable, Optional

from app.settings import AppSettings
from app.transcriber import load_transcriber

LOGGER = logging.getLogger("hoppy_whisper.onboarding")


@dataclass
class OnboardingStep:
    """Represents a step in the onboarding process."""
    title: str
    description: str
    content_widget: ttk.Frame
    can_skip: bool = True
    validation_func: Optional[Callable[[], bool]] = None


class OnboardingWizard:
    """First-run onboarding wizard with step-by-step setup guidance."""

    def __init__(self, settings: AppSettings, on_complete: Optional[Callable[[], None]] = None):
        self._settings = settings
        self._on_complete = on_complete
        self._root: Optional[tk.Tk] = None
        self._current_step = 0
        self._steps: list[OnboardingStep] = []
        self._step_labels: list[ttk.Label] = []
        self._is_complete = False

    def show(self) -> bool:
        """Show the onboarding wizard. Returns True if completed, False if cancelled."""
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
        self._root = tk.Tk()
        self._root.title("Hoppy Whisper Setup")
        self._root.geometry("600x500")
        self._root.resizable(False, False)

        # Configure window to stay on top
        try:
            if hasattr(self._root, "attributes"):
                self._root.attributes("-topmost", True)
        except Exception:
            pass

        # Configure grid
        self._root.columnconfigure(0, weight=1)
        self._root.rowconfigure(1, weight=1)

        # Header with app branding
        header_frame = ttk.Frame(self._root)
        header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header_frame.columnconfigure(1, weight=1)

        # App icon/title
        title_label = ttk.Label(
            header_frame,
            text="🦘 Hoppy Whisper",
            font=("Segoe UI", 16, "bold"),
        )
        title_label.grid(row=0, column=0, sticky="w")

        subtitle_label = ttk.Label(
            header_frame,
            text="Let's get you started with speech transcription",
            font=("Segoe UI", 10),
            foreground="gray",
        )
        subtitle_label.grid(row=1, column=0, sticky="w", pady=(5, 0))

        # Step indicator
        step_frame = ttk.Frame(self._root)
        step_frame.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 10))
        step_frame.columnconfigure(0, weight=1)

        self._step_indicator = ttk.Frame(step_frame)
        self._step_indicator.pack(fill="x", pady=(0, 20))

        # Content area
        self._content_frame = ttk.Frame(self._root)
        self._content_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self._content_frame.columnconfigure(0, weight=1)
        self._content_frame.rowconfigure(0, weight=1)

        # Button frame
        button_frame = ttk.Frame(self._root)
        button_frame.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))

        # Cancel button (left side)
        self._cancel_button = ttk.Button(
            button_frame,
            text="Cancel",
            command=self._on_cancel,
        )
        self._cancel_button.pack(side="left")

        # Spacer
        spacer = ttk.Frame(button_frame)
        spacer.pack(side="left", expand=True, fill="x")

        # Navigation buttons (right side)
        self._back_button = ttk.Button(
            button_frame,
            text="← Back",
            command=self._on_back,
            state="disabled",
        )
        self._back_button.pack(side="right", padx=(0, 10))

        self._next_button = ttk.Button(
            button_frame,
            text="Next →",
            command=self._on_next,
        )
        self._next_button.pack(side="right", padx=(0, 10))

        self._finish_button = ttk.Button(
            button_frame,
            text="Finish",
            command=self._on_finish,
            state="hidden",
        )
        self._finish_button.pack(side="right")

        # Handle window close
        self._root.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Center window on screen
        self._center_window()

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

    def _setup_steps(self) -> None:
        """Setup all onboarding steps."""
        # Step 1: Welcome
        welcome_frame = ttk.Frame(self._content_frame)
        welcome_content = self._create_welcome_content(welcome_frame)
        self._steps.append(OnboardingStep(
            title="Welcome to Hoppy Whisper",
            description="Let's set up your speech transcription experience",
            content_widget=welcome_content,
            can_skip=False,
        ))

        # Step 2: Hotkey Configuration
        hotkey_frame = ttk.Frame(self._content_frame)
        hotkey_content = self._create_hotkey_content(hotkey_frame)
        self._steps.append(OnboardingStep(
            title="Configure Hotkey",
            description="Choose the keyboard shortcut for starting transcription",
            content_widget=hotkey_content,
            validation_func=self._validate_hotkey,
        ))

        # Step 3: Transcription Mode
        mode_frame = ttk.Frame(self._content_frame)
        mode_content = self._create_transcription_mode_content(mode_frame)
        self._steps.append(OnboardingStep(
            title="Transcription Mode",
            description="Choose between local or remote transcription",
            content_widget=mode_content,
        ))

        # Step 4: Testing
        test_frame = ttk.Frame(self._content_frame)
        test_content = self._create_test_content(test_frame)
        self._steps.append(OnboardingStep(
            title="Test Your Setup",
            description="Let's verify everything is working correctly",
            content_widget=test_content,
            can_skip=True,
        ))

        # Step 5: Complete
        complete_frame = ttk.Frame(self._content_frame)
        complete_content = self._create_complete_content(complete_frame)
        self._steps.append(OnboardingStep(
            title="You're All Set!",
            description="Ready to start transcribing",
            content_widget=complete_content,
            can_skip=False,
        ))

        self._update_step_indicator()

    def _update_step_indicator(self) -> None:
        """Update the step indicator."""
        # Clear existing step indicators
        for widget in self._step_indicator.winfo_children():
            widget.destroy()

        # Create step indicators
        for i, step in enumerate(self._steps):
            step_frame = ttk.Frame(self._step_indicator)
            step_frame.pack(side="left", expand=True, fill="x", padx=5)

            # Step circle
            circle_color = "#0078d4" if i < self._current_step else (
                "#107c10" if i == self._current_step else "#666666"
            )

            step_label = ttk.Label(
                step_frame,
                text=str(i + 1),
                font=("Segoe UI", 10, "bold"),
                foreground="white",
                background=circle_color,
                width=3,
            )
            step_label.pack()

            # Step title
            title_label = ttk.Label(
                step_frame,
                text=step.title,
                font=("Segoe UI", 8),
                wraplength=100,
            )
            title_label.pack(pady=(5, 0))

            self._step_labels.append(step_label)

    def _show_step(self, step_index: int) -> None:
        """Show the specified step."""
        if not 0 <= step_index < len(self._steps):
            return

        self._current_step = step_index
        step = self._steps[step_index]

        # Clear content
        for widget in self._content_frame.winfo_children():
            widget.destroy()

        # Show step content
        step.content_widget.pack(fill="both", expand=True, pady=10)

        # Update navigation buttons
        self._back_button.config(state="normal" if step_index > 0 else "disabled")

        if step_index == len(self._steps) - 1:
            # Last step - show Finish button
            self._next_button.pack_forget()
            self._finish_button.pack(side="right")
        else:
            # Middle steps - show Next button
            self._finish_button.pack_forget()
            self._next_button.pack(side="right")

        self._update_step_indicator()

    def _create_welcome_content(self, parent: ttk.Frame) -> ttk.Frame:
        """Create the welcome step content."""
        content = ttk.Frame(parent)
        content.columnconfigure(0, weight=1)

        # Welcome message
        welcome_text = """
Welcome to Hoppy Whisper! 🎉

This guide will help you set up speech transcription in just a few steps.
We'll configure your hotkey, choose the best transcription method for your needs,
and test everything to make sure it works perfectly.

Your audio is processed locally for privacy, and all settings are saved to your computer.
        """

        welcome_label = ttk.Label(
            content,
            text=welcome_text.strip(),
            font=("Segoe UI", 11),
            justify="left",
            wraplength=500,
        )
        welcome_label.grid(row=0, column=0, sticky="ew", pady=20)

        # Feature highlights
        features_frame = ttk.LabelFrame(content, text="What you'll be able to do:", padding=15)
        features_frame.grid(row=1, column=0, sticky="ew", pady=10)

        features = [
            "🎤 Press a hotkey to start recording your speech",
            "📝 Transcribe speech to text instantly",
            "📋 Automatically copy text to your clipboard",
            "🔄 Paste text directly into any application",
            "📚 Search through your transcription history",
        ]

        for i, feature in enumerate(features):
            label = ttk.Label(
                features_frame,
                text=feature,
                font=("Segoe UI", 10),
            )
            label.grid(row=i, column=0, sticky="w", pady=2)

        return content

    def _create_hotkey_content(self, parent: ttk.Frame) -> ttk.Frame:
        """Create the hotkey configuration step content."""
        content = ttk.Frame(parent)
        content.columnconfigure(0, weight=1)

        # Instructions
        instruction_label = ttk.Label(
            content,
            text="Choose a hotkey combination that doesn't conflict with other programs.",
            font=("Segoe UI", 10),
            justify="left",
        )
        instruction_label.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        # Hotkey selection frame
        hotkey_frame = ttk.LabelFrame(content, text="Hotkey Configuration", padding=15)
        hotkey_frame.grid(row=1, column=0, sticky="ew", pady=10)
        hotkey_frame.columnconfigure(1, weight=1)

        # Current hotkey display
        ttk.Label(hotkey_frame, text="Current hotkey:").grid(row=0, column=0, sticky="w", pady=(0, 5))

        self._hotkey_var = tk.StringVar(value=self._settings.hotkey_chord)
        hotkey_display = ttk.Entry(
            hotkey_frame,
            textvariable=self._hotkey_var,
            state="readonly",
            font=("Consolas", 10),
        )
        hotkey_display.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 15))

        # Hotkey buttons
        buttons_frame = ttk.Frame(hotkey_frame)
        buttons_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))

        ttk.Button(
            buttons_frame,
            text="Change Hotkey",
            command=self._change_hotkey,
        ).pack(side="left", padx=(0, 10))

        ttk.Button(
            buttons_frame,
            text="Reset to Default",
            command=self._reset_hotkey,
        ).pack(side="left")

        # Tips
        tips_frame = ttk.LabelFrame(content, text="Tips", padding=10)
        tips_frame.grid(row=2, column=0, sticky="ew", pady=20)

        tips = [
            "• Choose a combination that's easy to remember and use",
            "• Avoid hotkeys used by other programs (like Ctrl+C, Ctrl+V)",
            "• Consider combinations like Ctrl+Shift+H or Alt+Space",
            "• You can change this later in Settings",
        ]

        for tip in tips:
            label = ttk.Label(
                tips_frame,
                text=tip,
                font=("Segoe UI", 9),
                foreground="gray",
            )
            label.pack(anchor="w", pady=2)

        return content

    def _create_transcription_mode_content(self, parent: ttk.Frame) -> ttk.Frame:
        """Create the transcription mode selection step content."""
        content = ttk.Frame(parent)
        content.columnconfigure(0, weight=1)

        # Instructions
        instruction_label = ttk.Label(
            content,
            text="Choose how you want to transcribe speech. You can change this later.",
            font=("Segoe UI", 10),
            justify="left",
        )
        instruction_label.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        # Mode selection
        modes_frame = ttk.LabelFrame(content, text="Transcription Method", padding=15)
        modes_frame.grid(row=1, column=0, sticky="ew", pady=10)

        self._transcription_mode = tk.StringVar(value="local" if not self._settings.remote_transcription_enabled else "remote")

        # Local transcription option
        local_frame = ttk.Frame(modes_frame)
        local_frame.grid(row=0, column=0, sticky="ew", pady=10)
        local_frame.columnconfigure(1, weight=1)

        local_radio = ttk.Radiobutton(
            local_frame,
            variable=self._transcription_mode,
            value="local",
            text="Local Transcription (Recommended)",
            font=("Segoe UI", 11, "bold"),
        )
        local_radio.grid(row=0, column=0, sticky="w", pady=(0, 5))

        local_desc = ttk.Label(
            local_frame,
            text="Speech is transcribed locally on your computer using AI models. "
                 "This provides better privacy and works offline after the initial setup.",
            font=("Segoe UI", 9),
            foreground="gray",
            wraplength=400,
            justify="left",
        )
        local_desc.grid(row=1, column=0, sticky="w")

        # Remote transcription option
        remote_frame = ttk.Frame(modes_frame)
        remote_frame.grid(row=1, column=0, sticky="ew", pady=10)
        remote_frame.columnconfigure(1, weight=1)

        remote_radio = ttk.Radiobutton(
            remote_frame,
            variable=self._transcription_mode,
            value="remote",
            text="Remote Transcription",
            font=("Segoe UI", 11, "bold"),
        )
        remote_radio.grid(row=0, column=0, sticky="w", pady=(0, 5))

        remote_desc = ttk.Label(
            remote_frame,
            text="Speech is sent to a remote service for transcription. "
                 "This may require internet connection and API configuration.",
            font=("Segoe UI", 9),
            foreground="gray",
            wraplength=400,
            justify="left",
        )
        remote_desc.grid(row=1, column=0, sticky="w")

        # Remote settings (initially hidden)
        self._remote_settings_frame = ttk.LabelFrame(
            modes_frame,
            text="Remote Settings",
            padding=10,
        )
        self._remote_settings_frame.grid(
            row=2, column=0, sticky="ew",
            pady=(10, 0)
        )
        self._remote_settings_frame.columnconfigure(1, weight=1)
        self._remote_settings_frame.grid_remove()  # Initially hidden

        # Endpoint URL
        ttk.Label(self._remote_settings_frame, text="Endpoint URL:").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )
        self._endpoint_var = tk.StringVar(value=self._settings.remote_transcription_endpoint)
        endpoint_entry = ttk.Entry(
            self._remote_settings_frame,
            textvariable=self._endpoint_var,
        )
        endpoint_entry.grid(row=0, column=1, sticky="ew", padx=(10, 0), pady=(0, 5))

        # API Key
        ttk.Label(self._remote_settings_frame, text="API Key (optional):").grid(
            row=1, column=0, sticky="w", pady=(0, 5)
        )
        self._api_key_var = tk.StringVar(value=self._settings.remote_transcription_api_key)
        api_key_entry = ttk.Entry(
            self._remote_settings_frame,
            textvariable=self._api_key_var,
            show="*",
        )
        api_key_entry.grid(row=1, column=1, sticky="ew", padx=(10, 0), pady=(0, 5))

        # Model
        ttk.Label(self._remote_settings_frame, text="Model:").grid(
            row=2, column=0, sticky="w", pady=(0, 5)
        )
        self._model_var = tk.StringVar(value=self._settings.remote_transcription_model)
        model_entry = ttk.Entry(
            self._remote_settings_frame,
            textvariable=self._model_var,
        )
        model_entry.grid(row=2, column=1, sticky="ew", padx=(10, 0), pady=(0, 5))

        # Bind to show/hide remote settings
        def on_mode_change(*args):
            if self._transcription_mode.get() == "remote":
                self._remote_settings_frame.grid()
            else:
                self._remote_settings_frame.grid_remove()

        self._transcription_mode.trace_add("write", on_mode_change)
        on_mode_change()  # Initial call

        return content

    def _create_test_content(self, parent: ttk.Frame) -> ttk.Frame:
        """Create the testing step content."""
        content = ttk.Frame(parent)
        content.columnconfigure(0, weight=1)

        # Instructions
        instruction_label = ttk.Label(
            content,
            text="Let's test your setup to make sure everything works correctly.",
            font=("Segoe UI", 10),
            justify="left",
        )
        instruction_label.grid(row=0, column=0, sticky="ew", pady=(0, 20))

        # Test results frame
        self._test_results_frame = ttk.LabelFrame(content, text="Test Results", padding=15)
        self._test_results_frame.grid(row=1, column=0, sticky="ew", pady=10)
        self._test_results_frame.columnconfigure(0, weight=1)

        # Test status
        self._test_status_var = tk.StringVar(value="Ready to test")
        status_label = ttk.Label(
            self._test_results_frame,
            textvariable=self._test_status_var,
            font=("Segoe UI", 11, "bold"),
        )
        status_label.grid(row=0, column=0, sticky="w", pady=(0, 10))

        # Test details
        self._test_details_text = tk.Text(
            self._test_results_frame,
            height=8,
            wrap="word",
            font=("Consolas", 9),
            state="disabled",
        )
        self._test_details_text.grid(row=1, column=0, sticky="ew", pady=(0, 10))

        # Test button
        self._test_button = ttk.Button(
            self._test_results_frame,
            text="Run Test",
            command=self._run_test,
        )
        self._test_button.grid(row=2, column=0)

        return content

    def _create_complete_content(self, parent: ttk.Frame) -> ttk.Frame:
        """Create the completion step content."""
        content = ttk.Frame(parent)
        content.columnconfigure(0, weight=1)

        # Success message
        success_text = """
🎉 You're all set up and ready to use Hoppy Whisper!

Your configuration has been saved. You can always change these settings later
through the Settings menu in the tray icon.

Quick Start:
1. Click the tray icon to access the menu
2. Press your hotkey to start recording
3. Speak clearly into your microphone
4. Release the hotkey to transcribe

Your transcriptions will be automatically copied to the clipboard
and you can paste them anywhere!
        """

        success_label = ttk.Label(
            content,
            text=success_text.strip(),
            font=("Segoe UI", 11),
            justify="left",
        )
        success_label.grid(row=0, column=0, sticky="ew", pady=20)

        # Final settings summary
        summary_frame = ttk.LabelFrame(content, text="Your Configuration", padding=15)
        summary_frame.grid(row=1, column=0, sticky="ew", pady=10)

        # Display current settings
        mode_text = "Local" if not self._settings.remote_transcription_enabled else "Remote"

        summary_items = [
            ("Hotkey", self._settings.hotkey_chord),
            ("Transcription Mode", mode_text),
            ("Auto-paste", "Enabled" if self._settings.auto_paste else "Disabled"),
            ("Start with Windows", "Yes" if self._settings.start_with_windows else "No"),
        ]

        for i, (label, value) in enumerate(summary_items):
            ttk.Label(
                summary_frame,
                text=f"{label}:",
                font=("Segoe UI", 9, "bold"),
            ).grid(row=i, column=0, sticky="w", pady=2)

            ttk.Label(
                summary_frame,
                text=value,
                font=("Segoe UI", 9),
            ).grid(row=i, column=1, sticky="w", padx=(10, 0), pady=2)

        return content

    def _change_hotkey(self) -> None:
        """Change the hotkey through a simple dialog."""
        current_hotkey = self._hotkey_var.get()

        # Simple input dialog for now
        new_hotkey = tk.simpledialog.askstring(
            "Change Hotkey",
            f"Enter new hotkey combination:\n\nCurrent: {current_hotkey}\n\nExample: CTRL+SHIFT+H",
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

    def _validate_hotkey(self) -> bool:
        """Validate the hotkey configuration."""
        hotkey = self._hotkey_var.get()
        if not hotkey or "+" not in hotkey:
            messagebox.showerror("Invalid Hotkey", "Please enter a valid hotkey combination.")
            return False
        return True

    def _run_test(self) -> None:
        """Run a test of the transcription setup."""
        self._test_button.config(state="disabled", text="Testing...")
        self._test_status_var.set("Running tests...")

        # Clear test details
        self._test_details_text.config(state="normal")
        self._test_details_text.delete(1.0, tk.END)
        self._test_details_text.config(state="disabled")

        def update_test_details(message: str):
            """Update test details text."""
            def update():
                self._test_details_text.config(state="normal")
                self._test_details_text.insert(tk.END, message + "\n")
                self._test_details_text.see(tk.END)
                self._test_details_text.config(state="disabled")
            self._root.after(0, update)

        def run_test_thread():
            """Run test in background thread."""
            try:
                update_test_details("Testing transcription setup...")

                # Test transcription mode
                mode = self._transcription_mode.get()
                update_test_details(f"Mode: {mode} transcription")

                if mode == "remote":
                    endpoint = self._endpoint_var.get()
                    if not endpoint:
                        update_test_details("❌ Remote mode requires endpoint URL")
                        self._root.after(0, lambda: self._test_button.config(state="normal", text="Run Test"))
                        self._root.after(0, lambda: self._test_status_var.set("Test failed"))
                        return

                    update_test_details(f"Endpoint: {endpoint}")

                    try:
                        transcriber = load_transcriber(
                            remote_enabled=True,
                            remote_endpoint=endpoint,
                            remote_api_key=self._api_key_var.get(),
                            remote_model=self._model_var.get(),
                        )
                        update_test_details("✅ Remote transcriber initialized successfully")
                    except Exception as e:
                        update_test_details(f"❌ Failed to initialize remote transcriber: {e}")
                        self._root.after(0, lambda: self._test_button.config(state="normal", text="Run Test"))
                        self._root.after(0, lambda: self._test_status_var.set("Test failed"))
                        return
                else:
                    try:
                        transcriber = load_transcriber(remote_enabled=False)
                        update_test_details("✅ Local transcriber initialized successfully")
                        update_test_details(f"Provider: {transcriber.provider}")
                    except Exception as e:
                        update_test_details(f"❌ Failed to initialize local transcriber: {e}")
                        self._root.after(0, lambda: self._test_button.config(state="normal", text="Run Test"))
                        self._root.after(0, lambda: self._test_status_var.set("Test failed"))
                        return

                update_test_details("✅ All tests passed!")
                self._root.after(0, lambda: self._test_status_var.set("All tests passed"))

            except Exception as e:
                update_test_details(f"❌ Test failed: {e}")
                self._root.after(0, lambda: self._test_status_var.set("Test failed"))

            finally:
                self._root.after(0, lambda: self._test_button.config(state="normal", text="Run Test"))

        import threading
        threading.Thread(target=run_test_thread, daemon=True).start()

    def _on_cancel(self) -> None:
        """Handle cancel button click."""
        if messagebox.askyesno(
            "Cancel Setup",
            "Are you sure you want to cancel the setup?\n\nYou can run this setup again from the Settings menu.",
        ):
            self._cleanup()

    def _on_back(self) -> None:
        """Handle back button click."""
        if self._current_step > 0:
            self._show_step(self._current_step - 1)

    def _on_next(self) -> None:
        """Handle next button click."""
        current_step = self._steps[self._current_step]

        # Validate if required
        if current_step.validation_func and not current_step.validation_func():
            return

        if self._current_step < len(self._steps) - 1:
            self._show_step(self._current_step + 1)

    def _on_finish(self) -> None:
        """Handle finish button click."""
        # Save settings
        try:
            # Update settings from wizard
            self._settings.hotkey_chord = self._hotkey_var.get()

            mode = self._transcription_mode.get()
            self._settings.remote_transcription_enabled = (mode == "remote")
            if mode == "remote":
                self._settings.remote_transcription_endpoint = self._endpoint_var.get()
                self._settings.remote_transcription_api_key = self._api_key_var.get()
                self._settings.remote_transcription_model = self._model_var.get()

            self._settings.first_run_complete = True
            self._settings.save()

            LOGGER.info("Onboarding completed successfully")

        except Exception as exc:
            LOGGER.error("Failed to save onboarding settings: %s", exc)
            messagebox.showerror(
                "Save Error",
                "Failed to save your settings. Please try again.",
            )
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
