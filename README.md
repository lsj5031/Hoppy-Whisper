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

## Download & Installation

### For End Users

1. **Download the latest release:**
   - Go to [Releases](https://github.com/YOUR_USERNAME/Parakeet/releases/latest)
   - Download `Parakeet-windows-x86_64.zip`

2. **Extract and run:**
   - Extract the zip file to a folder of your choice
   - Double-click `Parakeet.exe` to launch
   - The app will appear in your system tray

3. **First-run setup:**
   - A notification will explain the default hotkey (`Ctrl+Shift+;`)
   - On first transcription, models (~500MB) will download automatically from Hugging Face
   - Models are cached locally in `%LOCALAPPDATA%\Parakeet\models\`

**System Requirements:**
- Windows 10 (64-bit) or Windows 11
- 2GB RAM minimum, 4GB recommended
- 1GB free disk space for models
- Microphone access
- Internet connection for first-run model download

**Optional:** GPU acceleration requires DirectX 12 compatible GPU (NVIDIA, AMD, or Intel)

### For Developers

See [Development Setup](#quick-start) below.

## CI and Releases

- **Windows CI** runs on pull requests targeting `main`, pushes to `main`, and tags matching `v*`
- The workflow installs Poetry, runs Ruff linting, executes pytest, and builds a single-file PyInstaller executable using `Parakeet.spec`
- The executable is zipped as `Parakeet-windows-x86_64.zip` and uploaded as a workflow artifact
- **Tag pushes** that match `v*` automatically create a GitHub Release with the zip attached and auto-generated release notes

### Creating a Release

To publish a new release:

1. **Update version in `pyproject.toml`:**
   ```toml
   version = "0.2.0"
   ```

2. **Commit and tag:**
   ```bash
   git add pyproject.toml
   git commit -m "Bump version to 0.2.0"
   git tag v0.2.0
   git push origin master --tags
   ```

3. **GitHub Actions** will automatically:
   - Build the PyInstaller executable
   - Run all tests
   - Create a GitHub Release
   - Attach `Parakeet-windows-x86_64.zip`

4. **Smoke test** the release build on a clean Windows VM using [SMOKE_TEST.md](SMOKE_TEST.md)

## Usage

### Hotkey Workflow

The default hotkey is <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>;</kbd>:

- **Press & hold** - start audio capture and show "Listening" tray state
- **Release** - stop capture and begin transcription
- **Press again within 2 seconds** - paste the transcript into the active window

### Configuration

Settings are stored in `%LOCALAPPDATA%\Parakeet\settings.json` and can be edited manually or via the tray menu (Settings → opens file location).

**Available Settings:**

```json
{
  "first_run_complete": false,
  "hotkey_chord": "CTRL+SHIFT+;",
  "paste_window_seconds": 2.0,
  "start_with_windows": false
}
```

- `hotkey_chord`: Global hotkey combination (e.g., "CTRL+ALT+V")
- `paste_window_seconds`: Time window for same-hotkey paste (0-5 seconds)
- `start_with_windows`: Launch at Windows login
- `first_run_complete`: Internal flag for first-run notification

**Environment Override:**
Set `PARAKEET_SETTINGS_PATH` to use a custom settings file location.

## Privacy & Data

**Parakeet processes all audio and transcription data on your local device:**

- **No cloud services**: Audio capture, speech recognition, and text processing happen entirely on your machine using local ONNX Runtime models.
- **No telemetry**: The application does not collect, transmit, or share usage data, analytics, or personal information.
- **Performance metrics**: Opt-in local performance logging can be enabled by setting `telemetry_enabled: true` in settings. Metrics are logged locally only (no PII, no network transmission).

## Error Handling & Recovery

Parakeet is designed to handle errors gracefully:

- **Microphone missing or disconnected**: Shows clear notification with instructions to connect a microphone
- **Hotkey conflicts**: Displays specific error if the chosen hotkey is already registered by another application
- **Model download failures**: Automatically retries up to 3 times with exponential backoff (2s, 4s, 8s delays)
- **Device hot-unplug during recording**: Logs warning and completes transcription with available audio buffer
- **Clipboard access issues**: Shows actionable error message if Windows privacy settings block clipboard access

**Startup errors** are shown in a Windows message dialog with guidance on resolution.

## Accessibility Features

Parakeet is designed to be accessible:

- **High-contrast icons**: Automatically switches to high-contrast icon variants when Windows high-contrast mode is enabled
- **Theme awareness**: Respects system light/dark theme preferences for icon appearance
- **Keyboard navigation**: All tray menu items are keyboard-accessible (navigate with arrow keys, activate with Enter)
- **Screen reader friendly**: Menu items have descriptive labels for assistive technologies
- **Multiple icon sizes**: Supports various DPI scaling levels (16px to 64px)
- **Local storage**: Transcription history is stored in a local SQLite database at `%LOCALAPPDATA%\Parakeet\history.db` with a default 90-day retention period.
- **Export & deletion**: You can export your history to `.txt` or `.json` files via the History palette, or clear all stored utterances at any time with a confirmation dialog.

**Required permissions:**
- **Microphone access**: To capture audio for transcription.
- **Clipboard access**: To copy and paste transcribed text.
- **Registry access**: To enable "Start with Windows" functionality.

All data remains under your control on your device.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+;` | **Record & Transcribe** (default hotkey)<br>- Press & hold to start recording<br>- Release to stop and transcribe<br>- Press again within 2s to paste |
| `Shift` (hold during release) | **Bypass Smart Cleanup** - outputs raw transcription without cleanup |
| `Win+Shift+Y` | **Open History Palette** - search and reuse past transcriptions |
| `Enter` (in History) | Copy selected item to clipboard |
| `Shift+Enter` (in History) | Copy and paste selected item |
| `Esc` (in History) | Close History Palette |

**Note:** The main hotkey can be customized in `settings.json` (e.g., `"hotkey_chord": "CTRL+ALT+V"`).

## Known Limitations

- **Windows only:** Parakeet is optimized for Windows 10/11 and uses Windows-specific APIs (WASAPI, winreg, pystray). It will not run on macOS or Linux without significant modifications.

- **English only (v1):** The current model supports English transcription. Multilingual models may be added in future releases.

- **Model size:** Initial download is ~500MB and requires internet connection. Models are cached locally after first download.

- **GPU compatibility:** DirectML acceleration requires a DirectX 12 compatible GPU. The app will fall back to CPU if no compatible GPU is detected (slower but functional).

- **Hotkey conflicts:** If another application has already registered the chosen hotkey, Parakeet will fail to start with an error. You must resolve the conflict by changing either app's hotkey.

- **Background noise:** Very noisy environments may affect transcription quality. The WebRTC VAD gate helps filter background noise but is not perfect.

- **Clipboard-only:** Transcribed text is delivered via clipboard and paste simulation (`Ctrl+V`). Applications that block clipboard access or intercept paste events may not work correctly.

- **No undo:** Once transcription is pasted, there's no built-in undo. Use your application's undo feature (`Ctrl+Z`).

- **History retention:** Default 90-day retention for transcription history. Older entries are automatically purged. Export important transcriptions if needed.

## Troubleshooting

- **"Hotkey already in use"** - Another application is using the same hotkey. Change Parakeet's hotkey in settings or disable the conflicting app's hotkey.

- **"Microphone Error: No audio input device"** - Ensure a microphone is connected and enabled in Windows Sound settings. Check Privacy settings to allow microphone access.

- **"Failed to download model"** - Check internet connection and firewall settings. Ensure HTTPS access to huggingface.co is not blocked. The app will retry up to 3 times with backoff.

- **Transcription is slow (>2 seconds)** - Your system may be using CPU instead of GPU. Check if your GPU supports DirectX 12. Install latest graphics drivers if needed.

- **"Recording Too Short"** - Hold the hotkey for at least 0.2 seconds. Very brief presses are ignored to prevent accidental triggers.

- **Paste doesn't work in some apps** - Some applications (e.g., elevated/admin windows) may block simulated keystrokes. Try running Parakeet as administrator, or manually paste with `Ctrl+V`.

- **Poetry reports an unsupported Python version** - Ensure Python 3.11 is installed and run `py -3.11 -m poetry env use 3.11` to point Poetry at the correct interpreter.

- **Virtual environment creation fails** - Confirm that Visual C++ Build Tools are available (required for some optional dependencies) and re-run `poetry install`.

- **Clipboard automation blocked** - Windows privacy settings may prevent clipboard access; enable clipboard history and app access under *Settings > System > Clipboard*.

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE).
