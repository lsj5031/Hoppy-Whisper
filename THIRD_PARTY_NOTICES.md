# Third-Party Notices and Licenses

Hoppy Whisper includes or depends upon third-party open source software components. The following is a list of these components with their respective licenses and copyright notices.

---

## Runtime Dependencies

### ONNX Runtime (DirectML)
- **Copyright:** Microsoft Corporation
- **License:** MIT License
- **Repository:** https://github.com/microsoft/onnxruntime
- **Usage:** Local machine learning inference for speech recognition
- **License URL:** https://github.com/microsoft/onnxruntime/blob/main/LICENSE

### onnx-asr
- **License:** Apache License 2.0
- **Repository:** https://github.com/k2-fsa/onnx-asr
- **Usage:** Speech recognition model interface and utilities
- **License URL:** https://github.com/k2-fsa/onnx-asr/blob/main/LICENSE

### Hugging Face Hub
- **License:** Apache License 2.0
- **Repository:** https://github.com/huggingface/huggingface_hub
- **Usage:** Model downloads from Hugging Face
- **License URL:** https://github.com/huggingface/huggingface_hub/blob/main/LICENSE

### sounddevice
- **License:** MIT License
- **Repository:** https://github.com/spatialaudio/python-sounddevice
- **Usage:** Audio capture via PortAudio
- **License URL:** https://github.com/spatialaudio/python-sounddevice/blob/master/LICENSE

### PortAudio (bundled via sounddevice)
- **License:** MIT License
- **Website:** http://www.portaudio.com/
- **Usage:** Cross-platform audio I/O
- **License URL:** http://www.portaudio.com/license.html

### NumPy
- **License:** BSD 3-Clause License
- **Repository:** https://github.com/numpy/numpy
- **Usage:** Numerical array operations for audio processing
- **License URL:** https://github.com/numpy/numpy/blob/main/LICENSE.txt

### WebRTC VAD
- **License:** BSD 3-Clause License
- **Repository:** https://github.com/wiseman/py-webrtcvad
- **Usage:** Voice activity detection
- **License URL:** https://github.com/wiseman/py-webrtcvad/blob/master/LICENSE

### Pillow
- **License:** Historical Permission Notice and Disclaimer (HPND)
- **Repository:** https://github.com/python-pillow/Pillow
- **Usage:** Image processing for tray icons
- **License URL:** https://github.com/python-pillow/Pillow/blob/main/LICENSE

### pystray
- **License:** GNU Lesser General Public License v3.0 (LGPL-3.0)
- **Repository:** https://github.com/moses-palmer/pystray
- **Usage:** System tray icon integration
- **License URL:** https://github.com/moses-palmer/pystray/blob/master/COPYING.LGPL

### pynput
- **License:** GNU Lesser General Public License v3.0 (LGPL-3.0)
- **Repository:** https://github.com/moses-palmer/pynput
- **Usage:** Global hotkey registration and keyboard automation
- **License URL:** https://github.com/moses-palmer/pynput/blob/master/COPYING.LGPL

### pyperclip
- **License:** BSD 3-Clause License
- **Repository:** https://github.com/asweigart/pyperclip
- **Usage:** Clipboard operations
- **License URL:** https://github.com/asweigart/pyperclip/blob/master/LICENSE.txt

---

## Development Dependencies

### PyInstaller
- **License:** GPL with exception
- **Repository:** https://github.com/pyinstaller/pyinstaller
- **Usage:** Packaging application into standalone executable
- **License URL:** https://github.com/pyinstaller/pyinstaller/blob/develop/COPYING.txt

### Ruff
- **License:** MIT License
- **Repository:** https://github.com/astral-sh/ruff
- **Usage:** Linting and code formatting
- **License URL:** https://github.com/astral-sh/ruff/blob/main/LICENSE

### mypy
- **License:** MIT License
- **Repository:** https://github.com/python/mypy
- **Usage:** Static type checking
- **License URL:** https://github.com/python/mypy/blob/master/LICENSE

### pytest
- **License:** MIT License
- **Repository:** https://github.com/pytest-dev/pytest
- **Usage:** Testing framework
- **License URL:** https://github.com/pytest-dev/pytest/blob/main/LICENSE

### pre-commit
- **License:** MIT License
- **Repository:** https://github.com/pre-commit/pre-commit
- **Usage:** Git hook management
- **License URL:** https://github.com/pre-commit/pre-commit/blob/main/LICENSE

---

## Speech Models

### Whisper ONNX Models
- **Source:** Hugging Face Model Hub
- **Original Model:** OpenAI Whisper (MIT License)
- **Usage:** Offline speech-to-text transcription
- **License URL:** https://github.com/openai/whisper/blob/main/LICENSE
- **Note:** Models are downloaded at runtime from Hugging Face, not bundled in the executable.

---

## LGPL Compliance Notes

Hoppy Whisper depends on **pystray** and **pynput**, both licensed under LGPL-3.0. Compliance highlights:

1. The application dynamically links to these libraries (standard Python imports).
2. Full source code for Hoppy Whisper, pystray, and pynput is available via their respective repositories.
3. Contributors and users may replace or modify these libraries by editing `pyproject.toml` and rebuilding the application.
4. No additional restrictions are imposed beyond those in LGPL-3.0.

---

## Reporting License Issues

If you believe any third-party component is not properly attributed or there is a licensing concern, please open an issue in the repository issue tracker. We take compliance seriously and will address issues promptly.

---

**Last Updated:** January 2025

For the most up-to-date dependency list, see `pyproject.toml` and `poetry.lock`.
