# AGENTS.md - Coding Guidelines for Hoppy Whisper

## Build, Lint & Test Commands

```powershell
# Install dependencies
poetry install --with dev

# Run all tests
poetry run pytest

# Run a single test
poetry run pytest tests/test_hoppy.py::test_some_test -xvs

# Lint & format with Ruff
poetry run ruff check src/ tests/ --fix
poetry run ruff format src/ tests/

# Type check with mypy
poetry run mypy src/app

# Build executable
poetry run pyinstaller --noconfirm --clean HoppyWhisper.spec
```

## Codebase Structure

**Hoppy Whisper** is a Windows-native tray transcription app (Python 3.11+) using ONNX Runtime (CPU/GPU via DirectML).

- `src/app/` - Main application package
  - `__main__.py` - Entry point; `AppRuntime` orchestrates tray, hotkey, audio, transcriber
  - `audio/` - Audio capture (PortAudio via sounddevice) and VAD (WebRTC)
  - `hotkey/` - Global hotkey listener (Windows pynput)
  - `transcriber/` - ONNX speech recognition + model manager (Hugging Face hub)
  - `tray/` - Tray icon, menu, state management (pystray)
  - `history/` - SQLite persistence and search UI (90-day retention)
  - `settings.py` - JSON config + paths (`%LOCALAPPDATA%\Hoppy Whisper\`)
  - `metrics.py` - Optional telemetry (opt-in, local-only)
  - `startup.py` - Windows registry startup integration

- `tests/` - Pytest suite; conftest adds `src/` to path
- `HoppyWhisper.spec` - PyInstaller config (single-file, onefile, no console)

## Code Style & Conventions

- **Language**: Python 3.11+ with type hints (`from __future__ import annotations`)
- **Import Order**: Ruff isort (stdlib, third-party, `app` first-party)
- **Formatting**: Ruff formatter; 88-char line length; double quotes
- **Linting**: Ruff rules E, F, W, B, I (no unused imports, PEP 8, etc.)
- **Types**: Mypy with `ignore_missing_imports=true`; annotate all function signatures
- **Naming**: snake_case functions/variables, PascalCase classes
- **Errors**: Use custom exceptions (e.g., `AudioDeviceError`, `HotkeyInUseError`); log via `LOGGER` before raising; always include context in error messages
- **Docstrings**: Module + public method docstrings required; use `"""Format."""` for one-liners, multi-line for complex logic
- **Threading**: Use `threading.Event`, `Timer`; keep callbacks minimal; VAD processing is event-driven
