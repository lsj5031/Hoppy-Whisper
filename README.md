<div align="center">

# 🐰 Hoppy Whisper

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="icos/BunnyTranscribing1.ico">
  <img alt="Hoppy Whisper - Cute bunny transcription app" src="icos/BunnyStandby.ico" width="128" height="128">
</picture>

Hoppy Whisper is a Windows-native tray application for fast speech transcription and clipboard automation. Built with ONNX Runtime and WebRTC VAD for on-device processing, it captures audio via a global hotkey, transcribes locally, and pastes results into any application—no cloud services, no telemetry.

</div>

## Features

- 🎤 **Record with a hotkey** - Press & hold `Ctrl+Shift+;` to start recording
- ✨ **Instant transcription** - ONNX-powered speech-to-text in seconds
- 📋 **Auto-paste** - Transcription automatically pastes into your active window
- 🔐 **100% private** - All processing happens on your machine, no cloud services
- 🔇 **Smart noise filtering** - WebRTC VAD eliminates background noise
- 💾 **Local history** - Search past transcriptions (90-day retention)
- ⚡ **GPU accelerated** - Optional DirectML support for compatible hardware

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
5. **Run tests and verify setup:**
    ```powershell
    poetry run pytest
    poetry run ruff check src/
    ```

## Building from Source

### For End Users

**Download and install the latest release:**

1. Go to [Releases](https://github.com/lsj5031/Hoppy-Whisper/releases/latest)
2. Download **`Hoppy Whisper-CPU.exe`** (CPU-based inference, works on all systems)
3. Extract and run the `.exe` file - the app will appear in your system tray

**System Requirements:**
- Windows 10 (64-bit) or Windows 11
- 2GB RAM minimum, 4GB recommended
- 1GB free disk space for models
- Microphone access
- Internet connection for first-run model download

**GPU Acceleration (Optional):**
- The CPU executable automatically detects and uses DirectML GPU acceleration if available
- Requires DirectX 12 compatible GPU (NVIDIA, AMD, Intel, or Qualcomm)
- If no GPU is detected, falls back seamlessly to CPU inference
- No separate GPU executable needed; one build works for all hardware

**First-run setup:**
- A notification will explain the default hotkey (`Ctrl+Shift+;`)
- On first transcription, models (~500MB) will download automatically from Hugging Face
- Models are cached locally in `%LOCALAPPDATA%\Hoppy Whisper\models\`

### For Developers

**Build from source locally:**

1. **Install dependencies:**
   ```powershell
   py -3.11 -m poetry install --with dev
   ```

2. **Run tests and linting:**
   ```powershell
   poetry run pytest
   poetry run ruff check src/
   ```

3. **Build the executable:**
    ```powershell
    poetry run pyinstaller --noconfirm --clean HoppyWhisper_onefile.spec
    ```
    Output: `dist\Hoppy Whisper-CPU.exe` (~20 MB without bundled models)

4. **Test the build:**
    ```powershell
    .\dist\Hoppy Whisper-CPU.exe
    ```

**Build Notes:**
- The single executable automatically detects and uses DirectML GPU acceleration if available
- Models (~500 MB) download automatically on first launch from Hugging Face
- To pre-bundle models into the executable, place them in `%LOCALAPPDATA%\Hoppy Whisper\models\` before building
- With bundled models, the executable is ~57 MB; without them, it's ~20 MB

## CI and Releases

- **Windows CI** runs on push events to `master`, and tags matching `v*`
- The workflow installs Poetry, runs Ruff linting, executes pytest, and builds a single-file PyInstaller executable
- The release attaches `Hoppy Whisper-CPU.exe` as an artifact
- **Tag pushes** that match `v*` automatically create a GitHub Release with the zip attached and auto-generated release notes

### Creating a Release

To publish a new release:

1. **Update version in `pyproject.toml`:**
   ```toml
   version = "0.2.0"
   ```

2. **Commit and tag:**
    ```powershell
    git add pyproject.toml
    git commit -m "Bump version to 0.2.0"
    git tag v0.2.0
    git push origin master
    git push origin v0.2.0
    ```

3. **GitHub Actions** will automatically:
   - Build the PyInstaller executable
   - Run all tests
   - Create a GitHub Release
   - Attach `Hoppy Whisper-CPU.exe`

4. **Smoke test** the release build on a clean Windows VM using [SMOKE_TEST.md](SMOKE_TEST.md)

## Usage

### Hotkey Workflow

The default hotkey is <kbd>Ctrl</kbd> + <kbd>Shift</kbd> + <kbd>;</kbd>:

- **Press & hold** - start audio capture and show "Listening" tray state
- **Release** - stop capture and begin transcription
- **Press again within 2 seconds** - paste the transcript into the active window

### Configuration

Settings are stored in `%LOCALAPPDATA%\Hoppy Whisper\settings.json` and can be edited manually or via the tray menu (Settings → opens file location).

**Available Settings:**

```json
{
  "auto_paste": true,
  "first_run_complete": false,
  "history_retention_days": 90,
  "hotkey_chord": "CTRL+SHIFT+;",
  "idle_reset_delay_ms": 1600.0,
  "paste_predelay_ms": 180.0,
  "paste_window_seconds": 2.0,
  "remote_transcription_api_key": "",
  "remote_transcription_enabled": false,
  "remote_transcription_endpoint": "",
  "start_with_windows": false,
  "telemetry_enabled": false,
  "transcribe_start_delay_ms": 800.0
}
```

- `hotkey_chord`: Global hotkey combination (e.g., "CTRL+ALT+V")
- `paste_window_seconds`: Time window for same-hotkey paste (0-5 seconds)
- `start_with_windows`: Launch at Windows login
- `auto_paste`: Automatically paste transcription after recording stops
- `history_retention_days`: Days to retain transcription history (0 = no limit, must manually clear)
- `telemetry_enabled`: Enable local-only performance metrics logging
- `remote_transcription_enabled`: Use remote API instead of local ONNX models (default: false)
- `remote_transcription_endpoint`: URL of remote transcription API endpoint (required if remote enabled)
- `remote_transcription_api_key`: Optional API key for authentication (e.g., Bearer token)
- `transcribe_start_delay_ms`: Delay before transcription starts (milliseconds)
- `paste_predelay_ms`: Delay before paste simulation (milliseconds)
- `idle_reset_delay_ms`: Delay before tray icon returns to idle state (milliseconds)
- `first_run_complete`: Internal flag for first-run notification

**Environment Override:**
Set `HOPPY_WHISPER_SETTINGS_PATH` to use a custom settings file location.

### Remote Transcription

Hoppy Whisper can be configured to use a remote transcription API instead of local ONNX models. This is useful if you want to:

- Use a more powerful cloud-based model
- Offload transcription to a remote server (e.g., GLM-ASR, Whisper API, custom endpoints)
- Reduce local resource usage

**To enable remote transcription:**

1. Edit `settings.json` (`%LOCALAPPDATA%\Hoppy Whisper\settings.json`)
2. Set `remote_transcription_enabled` to `true`
3. Set `remote_transcription_endpoint` to your API endpoint URL
4. (Optional) Set `remote_transcription_api_key` if your API requires authentication

**Configuration Details:**

Edit `settings.json` directly or use the Settings menu:

| Setting | Type | Required | Description |
|---------|------|----------|-------------|
| `remote_transcription_enabled` | boolean | Yes | Enable/disable remote transcription |
| `remote_transcription_endpoint` | string | Yes (if enabled) | Full URL to your transcription API endpoint |
| `remote_transcription_api_key` | string | No | Bearer token for authentication (sent as `Authorization: Bearer {token}`) |
| `remote_transcription_model` | string | No | Optional model identifier to pass to the remote API |

**Example configuration:**

```json
{
  "remote_transcription_enabled": true,
  "remote_transcription_endpoint": "http://localhost:8000/transcribe",
  "remote_transcription_api_key": "your-api-key-here",
  "remote_transcription_model": ""
}
```

**API Requirements:**

The remote endpoint should:
- Accept `POST` requests with audio file as `multipart/form-data` with field name `file`
- Return JSON with transcription text in one of these formats:
  - `{"text": "transcribed text"}`
  - `{"transcription": "transcribed text"}`
  - `{"result": "transcribed text"}`
  - `{"results": [{"text": "transcribed text"}]}`
  - `{"data": {"text": "transcribed text"}}`
- Support WAV audio format (16kHz, mono recommended)
- Optionally support Bearer token authentication via `Authorization` header

**Compatible APIs:**
- [GLM-ASR](https://github.com/lsj5031/glm-asr-docker) - Docker-based ASR service
- OpenAI Whisper API
- Custom ASR endpoints following the format above

**Testing API Compatibility:**

To verify your endpoint accepts the correct request format, you can test with `curl`:

```powershell
# Test with a sample WAV file
curl -X POST `
  -F "file=@path/to/audio.wav" `
  -H "Authorization: Bearer your-api-key" `
  http://your-endpoint/path
```

Your API should return 200 OK with JSON containing one of the supported text fields shown above.

**Notes:**
- When remote transcription is enabled, local ONNX models are not loaded (faster startup, less RAM usage)
- Network latency and API response time will affect transcription speed
- Audio data is sent to the remote endpoint - ensure you trust the service provider if privacy is a concern
- If authentication fails, check that your API key format matches (some APIs use different header formats)

## Privacy & Data

**Hoppy Whisper processes all audio and transcription data on your local device (by default):**

- **No cloud services**: Audio capture, speech recognition, and text processing happen entirely on your machine using local ONNX Runtime models.
- **No telemetry**: The application does not collect, transmit, or share usage data, analytics, or personal information.
- **Performance metrics**: Opt-in local performance logging can be enabled by setting `telemetry_enabled: true` in settings. Metrics are logged locally only (no PII, no network transmission).
- **Remote transcription**: If you enable remote transcription, audio recordings will be sent to your configured endpoint. Ensure you trust the service provider if privacy is a concern.

## Error Handling & Recovery

Hoppy Whisper is designed to handle errors gracefully:

- **Microphone missing or disconnected**: Shows clear notification with instructions to connect a microphone
- **Hotkey conflicts**: Displays specific error if the chosen hotkey is already registered by another application
- **Model download failures**: Automatically retries up to 3 times with exponential backoff (2s, 4s, 8s delays)
- **Device hot-unplug during recording**: Logs warning and completes transcription with available audio buffer
- **Clipboard access issues**: Shows actionable error message if Windows privacy settings block clipboard access

**Startup errors** are shown in a Windows message dialog with guidance on resolution.

## Accessibility Features

Hoppy Whisper is designed to be accessible:

- **High-contrast icons**: Automatically switches to high-contrast icon variants when Windows high-contrast mode is enabled
- **Theme awareness**: Respects system light/dark theme preferences for icon appearance
- **Keyboard navigation**: All tray menu items are keyboard-accessible (navigate with arrow keys, activate with Enter)
- **Screen reader friendly**: Menu items have descriptive labels for assistive technologies
- **Multiple icon sizes**: Supports various DPI scaling levels (16px to 64px)
- **Local storage**: Transcription history is stored in a local SQLite database at `%LOCALAPPDATA%\Hoppy Whisper\history.db`. Retention is configurable (default 90 days).
- **Export & deletion**: You can export your history to `.txt` or `.json` files via the History palette, or clear all stored utterances at any time with a confirmation dialog.

**Required permissions:**
- **Microphone access**: To capture audio for transcription.
- **Clipboard access**: To copy and paste transcribed text.
- **Registry access**: To enable "Start with Windows" functionality.

All data remains under your control on your device.

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+;` | **Record & Transcribe** (default hotkey, customizable)<br>- Press & hold to start recording<br>- Release to stop and transcribe<br>- Press again within 2s to paste |
| **Tray menu** | Click **History** to open the History Palette |
| `Enter` (in History) | Copy selected item to clipboard |
| `Shift+Enter` (in History) | Copy and paste selected item |
| `Esc` (in History) | Close History Palette |
| `↑/↓` (in History) | Navigate through search results |

**Customizing the hotkey:**
Edit `settings.json` to change the hotkey:
- Location: `%LOCALAPPDATA%\Hoppy Whisper\settings.json`
- Examples: `"CTRL+ALT+V"`, `"WIN+SHIFT+C"`, `"F12"`, etc.
- Supported modifiers: CTRL, SHIFT, ALT, WIN
- Supported keys: A-Z, 0-9, F1-F24, and punctuation keys (`;`, `,`, `.`, etc.).

## Known Limitations

- **Windows only:** Hoppy Whisper is optimized for Windows 10/11 and uses Windows-specific APIs (WASAPI, winreg, pystray). It will not run on macOS or Linux without significant modifications.

- **English only (v1):** The current model supports English transcription. Multilingual models may be added in future releases.

- **Model size:** Initial download is ~500MB and requires internet connection. Models are cached locally after first download.

- **GPU compatibility:** DirectML acceleration requires a DirectX 12 compatible GPU. The app will fall back to CPU if no compatible GPU is detected (slower but functional).

- **Hotkey conflicts:** If another application has already registered the chosen hotkey, Hoppy Whisper will fail to start with an error. You must resolve the conflict by changing either app's hotkey.

- **Background noise:** Very noisy environments may affect transcription quality. The WebRTC VAD gate helps filter background noise but is not perfect.

- **Clipboard-only:** Transcribed text is delivered via clipboard and paste simulation (`Ctrl+V`). Applications that block clipboard access or intercept paste events may not work correctly.

- **No undo:** Once transcription is pasted, there's no built-in undo. Use your application's undo feature (`Ctrl+Z`).

- **History retention:** Transcription history retention is configurable in `settings.json` (default 90 days). To delete old entries manually, use the "Clear History" button in the History palette. Export important transcriptions if needed.

## Troubleshooting

- **"Hotkey already in use"** - Another application is using the same hotkey. Change Hoppy Whisper's hotkey in settings or disable the conflicting app's hotkey.

- **"Microphone Error: No audio input device"** - Ensure a microphone is connected and enabled in Windows Sound settings. Check Privacy settings to allow microphone access.

- **"Failed to download model"** - Check internet connection and firewall settings. Ensure HTTPS access to huggingface.co is not blocked. The app will retry up to 3 times with backoff.

- **Transcription is slow (>2 seconds)** - Your system may be using CPU instead of GPU. Check if your GPU supports DirectX 12. Install latest graphics drivers if needed.

- **"Recording Too Short"** - Hold the hotkey for at least 0.2 seconds. Very brief presses are ignored to prevent accidental triggers.

- **Paste doesn't work in some apps** - Some applications (e.g., elevated/admin windows) may block simulated keystrokes. Try running Hoppy Whisper as administrator, or manually paste with `Ctrl+V`.

- **Poetry reports an unsupported Python version** - Ensure Python 3.11 is installed and run `py -3.11 -m poetry env use 3.11` to point Poetry at the correct interpreter.

- **Virtual environment creation fails** - Confirm that Visual C++ Build Tools are available (required for some optional dependencies) and re-run `poetry install`.

- **Clipboard automation blocked** - Windows privacy settings may prevent clipboard access; enable clipboard history and app access under *Settings > System > Clipboard*.

## License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE).
