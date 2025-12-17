"""Command-line entry point for the Hoppy Whisper tray application."""

from __future__ import annotations

import logging
import os
import queue
import signal
import sys
import threading
from typing import Callable, Optional

import numpy as np
import pyperclip
from pynput.keyboard import Controller, Key

from app import startup
from app.audio import AudioDeviceError, AudioRecorder, VoiceActivityDetector, create_vad
from app.audio.buffer import TempWavFile
from app.history import HistoryDAO, HistoryPalette
from app.hotkey import HotkeyCallbacks, HotkeyInUseError, HotkeyManager
from app.metrics import (
    TRANSCRIBE_BUDGET_CPU_MS,
    TRANSCRIBE_BUDGET_GPU_MS,
    get_metrics,
    initialize_metrics,
)
from app.settings import (
    AppSettings,
    default_history_db_path,
    default_metrics_log_path,
)
from app.transcriber import (
    HoppyTranscriber,
    RemoteTranscriber,
    RemoteTranscriptionError,
    load_transcriber,
)
from app.tray import TrayController, TrayMenuActions, TrayState
from app.ui import OnboardingWizard, SettingsWindow, ToastManager

LOGGER = logging.getLogger("hoppy_whisper")


class AppRuntime:
    """High-level coordinator that wires the tray and hotkey subsystems."""

    def __init__(
        self, settings: AppSettings, transcriber: HoppyTranscriber | RemoteTranscriber
    ) -> None:
        self._settings = settings
        self._transcriber = transcriber
        self._stop_event = threading.Event()
        self._recording_active = False
        self._transcribe_timer: Optional[threading.Timer] = None
        self._idle_timer: Optional[threading.Timer] = None
        self._app_name = "Hoppy Whisper"
        self._startup_command = startup.resolve_startup_command()
        # VAD state
        self._vad: VoiceActivityDetector | None = None
        self._vad_carry = np.array([], dtype=np.float32)
        self._vad_stop_requested = False

        self._audio_recorder = AudioRecorder()
        self._audio_buffer: Optional[np.ndarray] = None
        self._keyboard_controller = Controller()
        self._history = HistoryDAO(
            default_history_db_path(),
            retention_days=settings.history_retention_days,
        )
        self._history.open()
        registry_startup = self._probe_startup_state()
        self._toggle_mode = True

        # Initialize UI components
        self._toast_manager = ToastManager()

        # UI request queue for thread-safe window creation
        self._ui_queue: queue.Queue[Callable[[], None]] = queue.Queue()

        self._tray = TrayController(
            app_name=self._app_name,
            menu_actions=TrayMenuActions(
                toggle_recording=self._menu_toggle_recording,
                show_settings=self._show_settings_window,
                show_history=self._show_history_tip,
                restart_app=self._restart,
                set_start_with_windows=self._set_start_with_windows,
                quit_app=self.stop,
            ),
            start_with_windows=registry_startup,
            show_first_run_tip=not settings.first_run_complete,
            first_run_hotkey_chord=settings.hotkey_chord,
        )
        callbacks = HotkeyCallbacks(
            on_record_start=self._handle_record_start,
            on_record_stop=self._handle_record_stop,
            on_request_paste=self._handle_request_paste,
            on_error=self._log_callback_error,
        )
        self._hotkey = HotkeyManager(
            settings.hotkey_chord,
            callbacks,
            paste_window_seconds=settings.paste_window_seconds,
            toggle_mode=True,
        )

    def start(self) -> None:
        """Start the tray icon and hotkey listener."""
        LOGGER.info("Starting Hoppy Whisper runtime")

        transcriber_config_before: tuple[bool, str, str, str] | None = None
        onboarding_completed = False

        # Show onboarding wizard for first-time users
        if not self._settings.first_run_complete:
            transcriber_config_before = (
                self._settings.remote_transcription_enabled,
                self._settings.remote_transcription_endpoint,
                self._settings.remote_transcription_api_key,
                self._settings.remote_transcription_model,
            )

            onboarding_completed = self._show_onboarding_wizard()
            if onboarding_completed:
                self._toast_manager.success(
                    "Setup completed! Press your hotkey to start transcribing."
                )
            else:
                LOGGER.info("Onboarding cancelled by user")
                self._toast_manager.info(
                    "You can run setup again from the Settings menu."
                )

        # Ensure first-run messaging reflects the current settings state.
        self._tray.configure_first_run_tip(
            show_first_run_tip=not self._settings.first_run_complete,
            hotkey_chord=self._settings.hotkey_chord,
        )

        # Apply any onboarding changes before starting background services.
        if onboarding_completed:
            try:
                self._hotkey.set_paste_window_seconds(
                    self._settings.paste_window_seconds
                )
                self._hotkey.update_chord(self._settings.hotkey_chord)
            except Exception as exc:
                LOGGER.exception(
                    "Failed to apply hotkey settings after onboarding", exc_info=exc
                )
                self._toast_manager.error(
                    "Setup saved but hotkey update failed. Please restart the app.",
                    "Hotkey Error",
                )

            if transcriber_config_before is not None:
                transcriber_config_after = (
                    self._settings.remote_transcription_enabled,
                    self._settings.remote_transcription_endpoint,
                    self._settings.remote_transcription_api_key,
                    self._settings.remote_transcription_model,
                )
                if transcriber_config_after != transcriber_config_before:
                    try:
                        self._transcriber = load_transcriber(
                            remote_enabled=self._settings.remote_transcription_enabled,
                            remote_endpoint=self._settings.remote_transcription_endpoint,
                            remote_api_key=self._settings.remote_transcription_api_key,
                            remote_model=self._settings.remote_transcription_model,
                        )
                    except Exception as exc:
                        LOGGER.exception(
                            "Failed to reload transcriber after onboarding",
                            exc_info=exc,
                        )
                        self._toast_manager.error(
                            "Setup saved but transcription reload failed. "
                            "Please restart the app.",
                            "Setup Error",
                        )

        self._tray.start()
        self._hotkey.start()
        if self._settings.start_with_windows:
            self._apply_startup_setting(True)

    def stop(self) -> None:
        """Shut down background services and signal termination."""
        if self._stop_event.is_set():
            return
        LOGGER.info("Stopping Hoppy Whisper runtime")
        self._stop_event.set()
        self._cancel_timer(self._transcribe_timer)
        self._cancel_timer(self._idle_timer)
        self._hotkey.stop()
        self._tray.stop()
        self._history.close()

        # Cleanup toast manager
        if hasattr(self, "_toast_manager"):
            self._toast_manager.cleanup()

    def wait(self) -> None:
        """Block the main thread until a quit signal arrives, processing UI requests."""
        while not self._stop_event.is_set():
            try:
                # Check for UI requests with timeout to allow stop event checking
                ui_task = self._ui_queue.get(timeout=0.1)
                try:
                    ui_task()
                except Exception:
                    LOGGER.exception("Error executing UI task")
            except queue.Empty:
                pass

    def _schedule_ui(self, task: Callable[[], None]) -> None:
        """Schedule a UI task to run on the main thread."""
        self._ui_queue.put(task)

    # Tray menu callbacks -------------------------------------------------

    def _menu_toggle_recording(self) -> None:
        if self._recording_active:
            self._handle_record_stop()
        else:
            self._handle_record_start()

    def _show_settings_window(self) -> None:
        """Show the settings window for configuration management."""

        def show():
            try:
                settings_window = SettingsWindow(
                    settings=self._settings,
                    on_apply=self._on_settings_applied,
                )
                settings_window.show()
            except Exception as exc:
                LOGGER.exception("Failed to open settings window", exc_info=exc)
                self._toast_manager.error(
                    "Failed to open settings window.", "Settings Error"
                )

        self._schedule_ui(show)

    def _show_onboarding_wizard(self) -> bool:
        """Show the onboarding wizard for first-time setup."""
        try:
            onboarding = OnboardingWizard(
                settings=self._settings,
                on_complete=self._on_onboarding_complete,
            )
            return onboarding.show()
        except Exception as exc:
            LOGGER.exception("Failed to show onboarding wizard", exc_info=exc)
            self._toast_manager.error(
                "Failed to open setup wizard. You can configure settings manually.",
                "Setup Error",
            )
            return False

    def _on_settings_applied(self) -> None:
        """Handle settings changes applied through the settings window."""
        self._toast_manager.success("Settings saved successfully.", "Configuration")

        # Update startup registry if setting changed
        registry_state = self._probe_startup_state()
        if registry_state != self._settings.start_with_windows:
            self._apply_startup_setting(self._settings.start_with_windows)

        # Restart hotkey with new settings
        previous_chord = self._hotkey.chord
        previous_paste_window = self._hotkey.paste_window_seconds

        def restore_previous_hotkey() -> None:
            try:
                self._hotkey.set_paste_window_seconds(previous_paste_window)
                self._hotkey.update_chord(previous_chord)
                self._hotkey.start()
            except Exception:
                LOGGER.exception(
                    "Failed to restore previous hotkey after settings update error"
                )

        try:
            self._hotkey.stop()
            self._hotkey.set_paste_window_seconds(self._settings.paste_window_seconds)
            self._hotkey.update_chord(self._settings.hotkey_chord)
            self._hotkey.start()
        except HotkeyInUseError as exc:
            LOGGER.error("Requested hotkey is already registered: %s", exc)
            self._toast_manager.error(str(exc), "Hotkey Error")
            restore_previous_hotkey()
        except Exception as exc:
            LOGGER.error("Failed to restart hotkey after settings change: %s", exc)
            self._toast_manager.error(
                "Settings saved but hotkey restart failed. Please restart app.",
                "Hotkey Error",
            )
            restore_previous_hotkey()

    def _on_onboarding_complete(self) -> None:
        """Handle onboarding completion."""
        self._settings.first_run_complete = True
        self._settings.save()
        LOGGER.info("Onboarding completed and settings saved")

    def _show_history_tip(self) -> None:
        """Open the history search palette."""

        def show():
            LOGGER.debug("Opening history palette")
            try:
                palette = HistoryPalette(
                    dao=self._history,
                    on_copy=self._palette_copy,
                    on_paste=self._palette_paste,
                )
                palette.show()
            except Exception as exc:
                LOGGER.exception("Failed to open history palette", exc_info=exc)
                self._toast_manager.error(
                    "Could not open history palette", "History Error"
                )

        self._schedule_ui(show)

    def _set_start_with_windows(self, enabled: bool) -> None:
        if self._settings.start_with_windows == enabled:
            return
        success = self._apply_startup_setting(enabled)
        if not success:
            return
        self._settings.start_with_windows = enabled
        self._settings.save()
        state = "enabled" if enabled else "disabled"
        self._toast_manager.success(f"Launch at login {state}.", "Startup")

    # Hotkey callbacks ----------------------------------------------------

    def _handle_record_start(self) -> None:
        if self._recording_active:
            return
        LOGGER.debug("Hotkey pressed: start recording")
        self._recording_active = True
        self._cancel_timer(self._transcribe_timer)
        self._cancel_timer(self._idle_timer)

        try:
            # Initialize VAD and wire audio chunk callback
            try:
                self._vad = create_vad(sample_rate=self._audio_recorder.sample_rate)
                self._vad_carry = np.array([], dtype=np.float32)
                self._vad_stop_requested = False
                self._audio_recorder.set_on_frames(self._on_audio_chunk)
            except Exception:
                # VAD is best-effort; continue without auto-stop if initialization fails
                LOGGER.debug(
                    "VAD initialization failed; continuing without auto-stop",
                    exc_info=True,
                )
                self._vad = None
                self._audio_recorder.set_on_frames(None)

            self._audio_recorder.start()
            self._tray.set_state(TrayState.LISTENING)
        except AudioDeviceError as exc:
            LOGGER.error("Audio device error: %s", exc)
            self._toast_manager.error(str(exc), "Microphone Error")
            self._recording_active = False
            self._tray.set_state(TrayState.ERROR)
            self._schedule_idle_reset()
        except Exception as exc:
            LOGGER.exception("Failed to start audio capture", exc_info=exc)
            self._toast_manager.error(
                "Could not start audio capture. Check your microphone.",
                "Recording Error",
            )
            self._recording_active = False
            self._tray.set_state(TrayState.ERROR)
            self._schedule_idle_reset()

    def _handle_record_stop(self) -> None:
        if not self._recording_active:
            return
        LOGGER.debug("Hotkey released: stop recording")
        self._recording_active = False

        # Detach VAD processing and reset state
        try:
            self._audio_recorder.set_on_frames(None)
        except Exception:
            LOGGER.debug("Failed to detach audio chunk callback", exc_info=True)
        self._vad = None
        self._vad_carry = np.array([], dtype=np.float32)
        self._vad_stop_requested = False

        # Start performance tracking for transcription pipeline
        metrics = get_metrics()
        metrics.start("ptt_release_to_paste")

        try:
            self._audio_buffer = self._audio_recorder.stop()
            # Calculate duration from returned buffer
            buffer_samples = (
                len(self._audio_buffer) if self._audio_buffer is not None else 0
            )
            duration = buffer_samples / self._audio_recorder.sample_rate
            LOGGER.info(
                "Captured %.2f seconds of audio (%d samples)", duration, buffer_samples
            )

            if duration < 0.1:
                LOGGER.warning(
                    "Audio buffer too short (%.2f s), skipping transcription", duration
                )
                self._toast_manager.warning(
                    "Please hold the hotkey longer to record audio.",
                    "Recording Too Short",
                )
                self._tray.set_state(TrayState.ERROR)
                self._schedule_idle_reset()
                return

            self._tray.set_state(TrayState.TRANSCRIBING)
            delay = self._settings.transcribe_start_delay_ms / 1000.0
            self._transcribe_timer = threading.Timer(
                delay, self._complete_transcription
            )
            self._transcribe_timer.start()
        except Exception as exc:
            LOGGER.exception("Failed to stop audio capture", exc_info=exc)
            self._toast_manager.error(
                "Could not complete audio capture.",
                "Recording Error",
            )
            self._tray.set_state(TrayState.ERROR)
            self._schedule_idle_reset()

    def _complete_transcription(self) -> None:
        """Transcribe the audio buffer and copy to clipboard."""
        if self._audio_buffer is None:
            LOGGER.error("No audio buffer to transcribe")
            self._toast_manager.error(
                "No audio recorded. Please try recording again.",
                "Transcription Error",
            )
            self._tray.set_state(TrayState.ERROR)
            self._schedule_idle_reset()
            return

        try:
            # Use TempWavFile to create a temporary WAV for transcription
            with TempWavFile(
                self._audio_buffer,
                self._audio_recorder.sample_rate,
                cleanup=True,
            ) as wav_path:
                result = self._transcriber.transcribe_file(wav_path)

            LOGGER.info(
                "Transcription completed in %.0f ms: '%s'",
                result.duration_ms,
                result.text[:100],
            )

            # Use raw model output (no Smart Cleanup)
            cleaned_text = result.text
            cleanup_mode = "raw"

            # Save to history
            try:
                self._history.insert(
                    text=cleaned_text,
                    mode=cleanup_mode,
                    duration_ms=int(result.duration_ms),
                    raw_text=result.text,
                )
                LOGGER.debug("Utterance saved to history")
            except Exception as exc:
                LOGGER.warning("Failed to save to history: %s", exc)

            # Copy to clipboard
            try:
                pyperclip.copy(cleaned_text)
                LOGGER.debug("Text copied to clipboard")
            except Exception as exc:
                LOGGER.error("Failed to copy to clipboard: %s", exc)
                self._toast_manager.error(
                    "Could not copy text to clipboard.", "Clipboard Error"
                )
                self._tray.set_state(TrayState.ERROR)
                self._schedule_idle_reset()
                return

            # Success!
            self._tray.set_state(TrayState.COPIED)

            # Auto-paste first to avoid focus issues from notifications
            if self._settings.auto_paste:
                LOGGER.debug("Auto-paste enabled, performing paste")
                self._perform_paste()
                self._tray.set_state(TrayState.PASTED)

            self._toast_manager.success(
                f"Transcribed: {cleaned_text[:60]}...", "Transcription Complete"
            )

            # Record performance metrics
            metrics = get_metrics()
            event = metrics.stop(
                "ptt_release_to_paste",
                provider_detected=self._transcriber.provider,
                provider_requested=getattr(self._transcriber, "provider_requested", ""),
            )
            if event:
                # Check against budget (GPU vs CPU)
                detected = self._transcriber.provider
                budget = (
                    TRANSCRIBE_BUDGET_GPU_MS
                    if any(k in detected.lower() for k in ("directml", "dml"))
                    else TRANSCRIBE_BUDGET_CPU_MS
                )
                metrics.check_budget(
                    "transcribe_pipeline",
                    result.duration_ms,
                    budget,
                    provider_detected=detected,
                    provider_requested=getattr(
                        self._transcriber, "provider_requested", ""
                    ),
                )

            self._schedule_idle_reset()

        except RemoteTranscriptionError as exc:
            # Log with structured context for debugging
            LOGGER.error(
                "Remote transcription failed",
                extra={
                    "error_type": exc.error_type.value,
                    "context": exc.context,
                    "status_code": exc.status_code,
                    "retryable": exc.is_retryable(),
                },
                exc_info=exc,
            )

            # User-facing message based on error category
            if exc.error_type.name == "NETWORK_TIMEOUT":
                message = (
                    "Remote transcription timed out. Check network/endpoint latency."
                )
            elif exc.error_type.name == "CONNECTION_FAILED":
                message = (
                    "Cannot connect to remote API. Check endpoint URL and network."
                )
            elif exc.error_type.name == "HTTP_ERROR":
                message = (
                    f"Remote API error (HTTP {exc.status_code}). Check API status."
                )
            elif exc.error_type.name == "PARSE_ERROR":
                message = (
                    "Remote API returned unexpected format. Check API configuration."
                )
            else:
                message = "Remote transcription failed. Check endpoint and network."

            self._toast_manager.error(message, "Remote Transcription Failed")
            self._tray.set_state(TrayState.ERROR)
            self._schedule_idle_reset()
        except Exception as exc:
            LOGGER.exception("Transcription failed", exc_info=exc)
            self._toast_manager.error(
                "Could not transcribe audio. Try again.", "Transcription Failed"
            )
            self._tray.set_state(TrayState.ERROR)
            self._schedule_idle_reset()

    def _handle_request_paste(self) -> None:
        LOGGER.debug("Hotkey tapped within paste window: paste")
        self._tray.set_state(TrayState.PASTED)
        self._perform_paste()
        self._schedule_idle_reset()

    def _perform_paste(self) -> None:
        """Simulate paste into the focused window.

        On Windows, use Shift+Insert (the standard Windows paste command).
        On other platforms, use Ctrl+V.
        """
        try:
            # Small delay to ensure context switch
            import sys
            import time

            predelay = self._settings.paste_predelay_ms / 1000.0
            time.sleep(predelay)

            if sys.platform == "win32":
                # Use Shift+Insert as the standard Windows paste command.
                # Do not send both Shift+Insert and Ctrl+V, as many apps respond
                # to both and will paste twice. Shift+Insert is the most reliable.
                with self._keyboard_controller.pressed(Key.shift):
                    self._keyboard_controller.press(Key.insert)
                    self._keyboard_controller.release(Key.insert)
                LOGGER.info("Paste command sent (Shift+Insert)")
            else:
                with self._keyboard_controller.pressed(Key.ctrl):
                    self._keyboard_controller.press("v")
                    self._keyboard_controller.release("v")
                LOGGER.info("Paste command sent (Ctrl+V)")
        except Exception as exc:
            LOGGER.error("Failed to perform paste: %s", exc)
            self._toast_manager.error("Could not paste text.", "Paste Error")

    # --- VAD integration -------------------------------------------------

    def _on_audio_chunk(self, chunk: np.ndarray) -> None:
        """Incrementally feed captured audio to VAD and auto-stop on trailing silence.

        Runs on the PortAudio callback thread; keep work minimal.
        """
        if self._vad is None or not self._recording_active:
            return
        try:
            data = chunk.flatten()
            if self._vad_carry.size:
                data = np.concatenate((self._vad_carry, data))
            frame_size = self._vad.frame_size  # 30ms @ 16kHz = 480 samples
            idx = 0
            n = len(data)
            while idx + frame_size <= n:
                frame = data[idx : idx + frame_size]
                _, should_stop = self._vad.process_frame(frame)
                if should_stop and not self._vad_stop_requested:
                    if self._toggle_mode:
                        # In toggle mode, do not auto-stop on VAD; user controls stop
                        break
                    self._vad_stop_requested = True
                    # Stop recording on a separate thread to avoid blocking callback
                    threading.Thread(
                        target=self._handle_record_stop,
                        daemon=True,
                    ).start()
                    break
                idx += frame_size
            # Keep leftover for next callback
            self._vad_carry = data[idx:]
        except Exception:
            # Never let VAD errors impact recording
            LOGGER.debug("VAD processing error", exc_info=True)

    def _log_callback_error(self, exc: Exception) -> None:
        LOGGER.exception("Unhandled exception in hotkey callback", exc_info=exc)

    # History palette callbacks -------------------------------------------

    def _palette_copy(self, text: str) -> None:
        """Copy text from history palette to clipboard."""
        try:
            pyperclip.copy(text)
            LOGGER.debug("Copied from history palette to clipboard")
        except Exception as exc:
            LOGGER.error("Failed to copy from palette: %s", exc)

    def _palette_paste(self, text: str) -> None:
        """Copy text from history palette and paste it."""
        try:
            pyperclip.copy(text)
            self._perform_paste()
            LOGGER.debug("Pasted from history palette")
        except Exception as exc:
            LOGGER.error("Failed to paste from palette: %s", exc)

    # Helpers -------------------------------------------------------------

    def _schedule_idle_reset(self, delay: float | None = None) -> None:
        """Schedule a return to idle state after a delay.

        If delay is None, uses the value from settings (idle_reset_delay_ms).
        """
        self._cancel_timer(self._idle_timer)
        if delay is None:
            delay = self._settings.idle_reset_delay_ms / 1000.0
        self._idle_timer = threading.Timer(delay, self._reset_to_idle)
        self._idle_timer.start()

    def _reset_to_idle(self) -> None:
        LOGGER.debug("Resetting tray state to idle")
        self._tray.set_state(TrayState.IDLE)

    def _cancel_timer(self, timer: Optional[threading.Timer]) -> None:
        if timer and timer.is_alive():
            timer.cancel()

    def _apply_startup_setting(self, enabled: bool) -> bool:
        try:
            if enabled:
                startup.enable_startup(self._app_name, self._startup_command)
            else:
                startup.disable_startup(self._app_name)
        except startup.StartupError as exc:
            self._toast_manager.error(f"Could not update auto-start: {exc}", "Startup")
            LOGGER.debug("Startup toggle failed", exc_info=True)
            return False
        return True

    def _probe_startup_state(self) -> bool:
        try:
            registry_enabled = startup.is_startup_enabled(
                self._app_name, self._startup_command
            )
        except startup.StartupError:
            LOGGER.debug("Startup probe unavailable on this platform", exc_info=True)
            return self._settings.start_with_windows
        if registry_enabled != self._settings.start_with_windows:
            self._settings.start_with_windows = registry_enabled
            self._settings.save()
        return registry_enabled

    def _restart(self) -> None:
        """Restart the application by spawning a new instance and exiting."""
        try:
            import subprocess

            subprocess.Popen(self._startup_command, shell=True)
            self._toast_manager.info("Restarting Hoppy Whisper...", "Restart")
        except Exception as exc:
            LOGGER.exception("Failed to restart application", exc_info=exc)
            self._toast_manager.error("Could not restart the application.", "Restart")
            return
        # Stop current runtime; main() will exit afterward
        self.stop()


def _install_global_exception_handlers() -> None:
    """Log uncaught exceptions from the main thread and background threads."""

    def _handle_uncaught(exc_type, exc_value, exc_traceback) -> None:
        LOGGER.critical(
            "Uncaught exception in main thread",
            exc_info=(exc_type, exc_value, exc_traceback),
        )
        try:
            show_error_dialog(
                "Hoppy Whisper hit an unexpected error and needs to close. "
                "Details were written to the log file."
            )
        except Exception:
            # Avoid recursion if dialog/logging fails
            pass

    sys.excepthook = _handle_uncaught

    # Python 3.11+: capture uncaught exceptions in background threads
    if hasattr(threading, "excepthook"):
        original_excepthook = threading.excepthook  # noqa: F841

        def _thread_excepthook(args) -> None:  # type: ignore[no-redef]
            LOGGER.critical(
                "Uncaught exception in thread %s", getattr(args, "thread", None)
            )
            LOGGER.critical(
                "Thread exception details",
                exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
            )
            try:
                if callable(original_excepthook):
                    original_excepthook(args)
            except Exception:
                # Best-effort only; never let this crash the process
                pass

        threading.excepthook = _thread_excepthook  # type: ignore[assignment]


def configure_logging() -> None:
    """Set up logging for console and a rolling log file.

    - Console level can be overridden via HOPPY_WHISPER_LOG_LEVEL (e.g., DEBUG/INFO).
    - Detailed DEBUG logs are always written to Hoppy Whisper dir/hoppy_whisper.log.
    """
    level_name = os.getenv("HOPPY_WHISPER_LOG_LEVEL", "INFO").upper()
    console_level = getattr(logging, level_name, logging.INFO)

    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    handlers: list[logging.Handler] = []

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(console_level)
    ch.setFormatter(fmt)
    handlers.append(ch)

    # File handler (rolling)
    try:
        from logging.handlers import RotatingFileHandler

        log_path = default_metrics_log_path().with_name("hoppy_whisper.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(
            str(log_path), maxBytes=1_000_000, backupCount=2, encoding="utf-8"
        )
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(fmt)
        handlers.append(fh)
    except Exception:
        # If file logging fails, continue with console-only
        pass

    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    for h in list(root.handlers):
        root.removeHandler(h)
    for h in handlers:
        root.addHandler(h)


def _configure_ssl_certs() -> None:
    """Ensure HTTPS works in frozen builds by pointing to certifi CA bundle."""
    try:
        import certifi

        os.environ.setdefault("SSL_CERT_FILE", certifi.where())
    except Exception:
        # Best-effort; if certifi is unavailable, urllib/requests may still work
        LOGGER.debug("SSL cert configuration skipped", exc_info=True)


def show_error_dialog(message: str, title: str = "Hoppy Whisper") -> None:
    """Display an error dialog, falling back to stderr when necessary."""
    LOGGER.error("%s", message)
    if sys.platform == "win32":
        try:
            ctypes = __import__("ctypes")
            ctypes.windll.user32.MessageBoxW(None, message, title, 0x00000010)  # type: ignore[attr-defined]
            return
        except Exception:  # pragma: no cover - fall back to stderr
            LOGGER.debug("Failed to display Windows message box", exc_info=True)
    print(f"{title}: {message}", file=sys.stderr)


def main() -> int:
    """Launch the Hoppy Whisper tray app."""
    if sys.platform != "win32":
        print(
            "Hoppy Whisper is optimized for Windows "
            "and may not function correctly elsewhere.",
            file=sys.stderr,
        )
    configure_logging()
    _install_global_exception_handlers()
    LOGGER.info(
        "Process starting (python=%s, platform=%s, argv=%s)",
        sys.version.split()[0],
        sys.platform,
        " ".join(sys.argv),
    )
    # Configure SSL certificates early for any upcoming downloads
    _configure_ssl_certs()
    settings = AppSettings.load()

    # Initialize performance metrics (opt-in via telemetry_enabled)
    initialize_metrics(
        enabled=settings.telemetry_enabled,
        log_path=default_metrics_log_path() if settings.telemetry_enabled else None,
    )
    metrics = get_metrics()

    # Track startup time
    metrics.start("startup")

    # Optional: prefetch model assets in the background for offline readiness
    # (skip if using remote transcription)
    if not settings.remote_transcription_enabled:

        def _prefetch_models() -> None:
            try:
                from app.transcriber import get_model_manager

                manager = get_model_manager()
                manager.ensure_models()
            except Exception:
                # Prefetch is best-effort; ignore failures
                LOGGER.debug("Model prefetch failed", exc_info=True)

        try:
            threading.Thread(target=_prefetch_models, daemon=True).start()
        except Exception:
            LOGGER.debug("Failed to start model prefetch thread", exc_info=True)

    # Load and warm up the transcriber
    if settings.remote_transcription_enabled:
        LOGGER.info("Loading remote transcriber...")
    else:
        LOGGER.info("Loading local transcriber...")
    try:
        transcriber = load_transcriber(
            remote_enabled=settings.remote_transcription_enabled,
            remote_endpoint=settings.remote_transcription_endpoint,
            remote_api_key=settings.remote_transcription_api_key,
            remote_model=settings.remote_transcription_model,
        )
        try:
            requested = getattr(transcriber, "provider_requested", "")
            LOGGER.info(
                "Transcriber ready (detected: %s; requested: %s)",
                transcriber.provider,
                requested,
            )
        except Exception:
            LOGGER.info("Transcriber ready (provider: %s)", transcriber.provider)
    except Exception as exc:
        LOGGER.exception("Failed to load transcriber", exc_info=exc)

        # If remote transcription failed, show onboarding wizard to let them reconfigure
        # (regardless of first_run_complete status if config is invalid)
        is_remote_config_invalid = (
            settings.remote_transcription_enabled
            and not settings.remote_transcription_endpoint
        )
        if is_remote_config_invalid or (
            settings.remote_transcription_enabled and not settings.first_run_complete
        ):
            LOGGER.info(
                "Remote transcription failed and first_run incomplete; "
                "showing onboarding"
            )
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    onboarding = OnboardingWizard(settings)
                    if onboarding.show():
                        # Onboarding completed; retry loading transcriber.
                        try:
                            transcriber = load_transcriber(
                                remote_enabled=settings.remote_transcription_enabled,
                                remote_endpoint=settings.remote_transcription_endpoint,
                                remote_api_key=settings.remote_transcription_api_key,
                                remote_model=settings.remote_transcription_model,
                            )
                            LOGGER.info(
                                "Transcriber loaded successfully after onboarding"
                            )
                            break  # Success!
                        except Exception as retry_exc:
                            LOGGER.warning(
                                "Transcriber failed after onboarding "
                                "(attempt %d/%d): %s",
                                attempt + 1,
                                max_retries,
                                retry_exc,
                            )
                            if attempt < max_retries - 1:
                                # Show onboarding again to let user fix config
                                LOGGER.info(
                                    "Bringing user back to onboarding to fix config"
                                )
                                continue
                            else:
                                # Final attempt failed
                                show_error_dialog(
                                    "Remote transcription setup failed. "
                                    "Please check your endpoint and try again."
                                )
                                return 1
                    else:
                        # User cancelled onboarding
                        LOGGER.info("User cancelled onboarding")
                        return 1
                except Exception as onboard_exc:
                    LOGGER.exception(
                        "Failed to show onboarding wizard", exc_info=onboard_exc
                    )
                    show_error_dialog(
                        "Setup wizard failed. "
                        "Please check your configuration and try again."
                    )
                    return 1
        else:
            # Show error for local transcription or if user already completed onboarding
            if settings.remote_transcription_enabled:
                show_error_dialog(
                    "Failed to connect to remote transcription service. "
                    "Please check your endpoint configuration and try again."
                )
            else:
                show_error_dialog(
                    "Failed to load speech recognition model. "
                    "Please check your internet connection and try again."
                )
            return 1

    try:
        runtime = AppRuntime(settings, transcriber)
    except HotkeyInUseError as exc:
        show_error_dialog(str(exc))
        return 1

    def handle_signal(signum: int, frame: object) -> None:
        LOGGER.info("Received signal %s, shutting down", signum)
        runtime.stop()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, handle_signal)
        except ValueError:
            pass

    runtime.start()

    # Complete startup timing
    from app.metrics import STARTUP_BUDGET_MS

    startup_event = metrics.stop(
        "startup",
        provider_detected=transcriber.provider,
        provider_requested=getattr(transcriber, "provider_requested", ""),
    )
    if startup_event:
        metrics.check_budget(
            "startup_to_ready", startup_event.duration_ms, STARTUP_BUDGET_MS
        )

    try:
        runtime.wait()
    finally:
        runtime.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
