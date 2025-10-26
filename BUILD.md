# Building Hoppy Whisper

This guide covers building the Hoppy Whisper executable locally for development and testing.

## Prerequisites

- **Python 3.11 (64-bit)** - Required for all builds
- **Poetry** - Dependency management and virtual environment
- **Git** - Version control
- **Visual C++ Build Tools** - Optional, for building native dependencies from source (most are pre-built wheels)

## Quick Build

To build the executable locally:

```powershell
# Install dependencies
poetry install --with dev

# Build with PyInstaller
poetry run pyinstaller --noconfirm --clean HoppyWhisper.spec
```

The output will be in `dist/Hoppy Whisper.exe`.

## Build Configuration

### PyInstaller Spec File

The build is configured in `HoppyWhisper.spec`:

- **Entry point:** `src/app/__main__.py`
- **Mode:** Single-file executable (`--onefile` equivalent)
- **Console:** Windowed mode (no console window) by default
- **Icon:** Generated dynamically by the app (no static .ico required)
- **Hidden imports:** All required packages are explicitly listed
- **Excludes:** Unnecessary packages (matplotlib, pandas, etc.) to reduce size

### Console vs Windowed Mode

To enable console mode for debugging:

1. Edit `HoppyWhisper.spec`
2. Change `console_mode = False` to `console_mode = True`
3. Rebuild

Console mode will show stdout/stderr in a terminal window, useful for debugging.

## Testing the Build

### Local Testing

1. **Build the executable:**
   ```powershell
   poetry run pyinstaller --noconfirm --clean HoppyWhisper.spec
   ```

2. **Run from dist directory:**
   ```powershell
   .\dist\Hoppy Whisper.exe
   ```

3. **Test basic functionality:**
   - Tray icon appears
   - Hotkey works
   - Audio capture starts/stops
   - Transcription completes (models download on first run)
   - Cleanup and paste work

4. **Check logs:**
   - Console output (if console mode enabled)
   - Windows Event Viewer for crashes
   - `%LOCALAPPDATA%\Hoppy Whisper\` for settings/history

### Clean VM Testing

For production releases, test on a clean Windows VM:

1. **Prepare VM:**
   - Fresh Windows 10 or 11 installation
   - No Python or development tools
   - Enable microphone (or virtual audio device)

2. **Copy executable:**
   - Transfer `dist/Hoppy Whisper.exe` to VM
   - No other files needed (self-contained)

3. **Run smoke tests:**
   - Follow [SMOKE_TEST.md](SMOKE_TEST.md) checklist
   - Verify all acceptance criteria pass

## Build Optimization

### Reducing Executable Size

The current build is optimized for compatibility. To reduce size:

1. **Enable UPX compression:** Already enabled in spec (`upx=True`)
2. **Exclude more packages:** Add to `excludes` list in spec
3. **Remove debug info:** PyInstaller strips by default

Typical sizes:
- **Uncompressed:** ~150-200 MB
- **UPX compressed:** ~80-120 MB

### Build Performance

Build times:
- **Clean build:** 2-5 minutes (depending on CPU)
- **Incremental build:** 30-60 seconds (if only app code changed)

To speed up builds:
- Use `--noconfirm` flag (skips prompts)
- Don't use `--clean` for incremental builds
- Keep build artifacts in `build/` directory

## Troubleshooting Builds

### "Module not found" at runtime

The executable runs but crashes with "No module named X":

1. **Add to hiddenimports:**
   ```python
   hiddenimports=[
       'missing_module',
       # ...
   ]
   ```

2. **Check for dynamic imports:**
   - Search codebase for `__import__()` or `importlib.import_module()`
   - Add these modules to `hiddenimports`

3. **Rebuild:**
   ```powershell
   poetry run pyinstaller --noconfirm --clean HoppyWhisper.spec
   ```

### "DLL not found" at runtime

Missing DirectML or ONNX Runtime DLLs:

1. **Check package installation:**
   ```powershell
   poetry run python -c "import onnxruntime; print(onnxruntime.__version__)"
   ```

2. **Verify DML provider:**
   ```powershell
   poetry run python -c "import onnxruntime; print(onnxruntime.get_available_providers())"
   ```

3. **Add to binaries if needed:**
   ```python
   binaries=[
       ('path/to/dll', '.'),
   ]
   ```

### "File not found" for data files

Missing vocab.json or other assets at runtime:

1. **Add to datas:**
   ```python
   datas=[
       ('path/to/asset', 'destination/folder'),
   ]
   ```

2. **Note:** Models are downloaded at runtime from Hugging Face, not bundled in the executable.

### Build hangs or crashes

PyInstaller fails during build:

1. **Clear build cache:**
   ```powershell
Remove-Item -Recurse -Force build, dist
poetry run pyinstaller --noconfirm --clean HoppyWhisper.spec
   ```

2. **Check Poetry environment:**
   ```powershell
   poetry env info
   poetry install --sync --with dev
   ```

3. **Update PyInstaller:**
   ```powershell
   poetry add --group dev pyinstaller@latest
   ```

## CI/CD Integration

The build is automated in `.github/workflows/windows-ci.yml`:

1. **On push to main:** Build and upload artifact
2. **On tag (v*):** Build, create release, attach zip

To trigger a release:
```bash
git tag v0.2.0
git push origin master --tags
```

GitHub Actions will:
- Run tests (pytest, ruff)
- Build with PyInstaller
- Create GitHub Release
- Upload `Hoppy Whisper-CPU.exe`

## Advanced Configuration

### Custom Icon

To add a static application icon:

1. Create/obtain a `.ico` file (multi-resolution recommended)
2. Place in root directory as `hoppy_whisper.ico`
3. Uncomment in `HoppyWhisper.spec`:
   ```python
   icon='hoppy_whisper.ico',
   ```

Note: Icons are currently generated dynamically by the app, so this is optional.

### Version Info

To embed version metadata in the executable:

1. Create `version_info.txt`:
   ```
   VSVersionInfo(
     ffi=FixedFileInfo(
       filevers=(0, 1, 0, 0),
       prodvers=(0, 1, 0, 0),
       # ...
     )
   )
   ```

2. Reference in spec:
   ```python
   version='version_info.txt',
   ```

### Code Signing

For distribution via Microsoft Store or enterprise:

1. Obtain code signing certificate
2. Sign the executable:
   ```powershell
   signtool sign /f certificate.pfx /p password /tr http://timestamp.digicert.com /td sha256 /fd sha256 "dist\Hoppy Whisper.exe"
   ```

3. Verify signature:
   ```powershell
   signtool verify /pa "dist\Hoppy Whisper.exe"
   ```

## Further Reading

- [PyInstaller Documentation](https://pyinstaller.org/en/stable/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [ONNX Runtime Deployment](https://onnxruntime.ai/docs/deployment/)
- [DirectML Provider](https://onnxruntime.ai/docs/execution-providers/DirectML-ExecutionProvider.html)
