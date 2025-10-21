# Parakeet Tray App Foundation

Parakeet is a Windows-native tray application for fast transcription and clipboard automation. This repository currently provides the scaffolding for future development, including a Poetry-managed environment and a modular `src/app` package layout covering tray integration, hotkey handling, audio capture, speech transcription, smart cleanup, and history persistence.

## Quick start

1. **Install Python 3.11 (64-bit)** and ensure it is available as `py -3.11` or `python3.11`.
2. **Install Poetry** (if not already present):
   ```powershell
   py -3.11 -m pip install poetry
   ```
3. **Create the virtual environment and install dependencies**:
   ```powershell
   py -3.11 -m poetry install --with dev
   ```
4. **Verify the environment** with Poetry's built-in checks:
   ```powershell
   py -3.11 -m poetry check
   ```
5. **Explore the package layout** under `src/app/` to begin implementing tray, hotkey, audio, transcriber, cleanup, and history features.

## CI and releases

- Windows CI runs on pull requests targeting `main`, pushes to `main`, and tags matching `v*`.
- The workflow installs Poetry, runs Ruff linting, executes pytest, and on pushes to `main` or tags builds a single-file PyInstaller executable.
- The executable is zipped as `Parakeet-windows-x86_64.zip` and uploaded as a workflow artifact.
- Tag pushes that match `v*` create a GitHub Release and attach the generated zip.

## Hotkey flow (planned)

The default experience targets a single press-and-hold hotkey (tentatively <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>Space</kbd>):

- **Press & hold** - start audio capture and indicate the "Listening" tray state.
- **Release** - stop capture, trigger speech-to-text transcription, and run smart cleanup.
- **Press again within a short window** - paste the cleaned transcript into the active window.

## Troubleshooting

- **Poetry reports an unsupported Python version** - ensure Python 3.11 is installed and run `py -3.11 -m poetry env use 3.11` to point Poetry at the correct interpreter.
- **Virtual environment creation fails** - confirm that Visual C++ Build Tools are available (required for some optional dependencies) and re-run `poetry install`.
- **Hotkey conflicts once implemented** - disable or remap conflicting shortcuts in other applications, then update the Parakeet hotkey configuration (future work) under `app.hotkey`.
- **Clipboard automation blocked** - Windows privacy settings may prevent clipboard access; enable clipboard history and app access under *Settings > System > Clipboard*.

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE).
