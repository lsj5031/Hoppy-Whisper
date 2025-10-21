Perfect! Here is the refreshed easy-path plan: ship a single-binary Windows tray app in Python (no local or remote HTTP server) with in-process ONNX Runtime (DirectML), a global hotkey, VAD auto-stop, the same-hotkey paste window, rule-based Smart Cleanup, and SQLite + FTS history. This stays aligned with the strengths already in this repo (`onnxruntime-directml`, `onnx_asr`, `pystray`/`pynput`, cleanup rules) while keeping the release path simple.

---

## Why Python remains the stack

* The existing transcription pipeline (`onnx_asr.load_model`, DirectML session helpers, rule-based cleanup tests) is already written in Python, so we can reuse proven code instead of rewriting it.
* ONNX Runtime with DirectML and the Parakeet models ship ready-to-use Python wheels, which keeps install and packaging time low compared with rebuilding native bindings in another language.
* The repo already contains Python-specific tooling (PyInstaller spec drafts, Ruff/Mypy configs, Poetry metadata), so sticking with Python avoids retooling and keeps the CI and release scripts relevant.

---

## Download your backlog + importer

* **Issues CSV (easy path):** [issues_easy_path.csv](issues_easy_path.csv)
* **Create issues in GitHub (PowerShell):** [create_issues_easy_path.ps1](create_issues_easy_path.ps1)

**How to import into a fresh repo:**

```powershell
# authenticate once
gh auth login

# from the folder containing the two files
.\create_issues_easy_path.ps1 -Repo yourname/yourrepo -CsvPath .\issues_easy_path.csv
```

---

## What changed vs. the previous plan

* **Removed:** HTTP inference server, process manager, health checks, retries.
* **Kept/Simplified:** In-process ASR via `onnxruntime-directml` and `onnx_asr`, first-run model download and cache, tray/hotkey/auto-paste, rule-based cleanup with tests, local history, PyInstaller packaging.
* **Result:** Fewer moving parts, faster to build, easier to test and release.

---

## Dependency flow (high level)

```
[E0.*] foundation
   -> [E1.*] tray + hotkey + settings
   -> [E2.*] audio + VAD + [E2.3] buffers
   -> [E3.1] DirectML + [E3.2] model assets + [E3.3] transcriber + [E3.4] end-to-end
   -> [E4.*] cleanup + same-hotkey paste
   -> [E5.*] SQLite history + palette
   -> [E6.*] perf/resilience + [E7.*] PyInstaller + (later) [E8.*] Store
```

---

## Backlog overview (you will get each item as a GitHub issue)

### EPIC 0 - Project foundation (Python, no HTTP)

* **[E0.1] Initialize Python tray app repo (Poetry + src layout)**
* **[E0.2] Code quality and tooling (Ruff, Mypy, pre-commit)**
* **[E0.3] Windows CI (GitHub Actions): test + PyInstaller artifact)**
* **[E0.4] Versioning and release workflow**

### EPIC 1 - Tray and settings

* **[E1.1] System tray icon and context menu (pystray)**
* **[E1.2] Global hotkey (reliable) with paste-window timer** - press/hold = record; release = stop; press again within N seconds = paste.
* **[E1.3] Icon state engine (Idle/Listening/Transcribing/Copied/Pasted/Error)**
* **[E1.4] Settings JSON + minimal UI hook**
* **[E1.5] Start with Windows (HKCU\...\Run)**

### EPIC 2 - Audio capture and VAD

* **[E2.1] WASAPI capture @16 kHz mono (sounddevice)**
* **[E2.2] WebRTC VAD gate (auto-stop on trailing silence)**
* **[E2.3] Temp WAV writer + PCM16 buffer utility**

### EPIC 3 - In-process ASR (ONNX Runtime + DirectML)

* **[E3.1] DirectML provider detection and session init** (prefer DML; fallback CPU)
* **[E3.2] Model asset manager (download/cache/validate)** - encoder/decoder/vocab in `%LOCALAPPDATA%/<App>/models`
* **[E3.3] Parakeet ONNX transcriber (embedded)** - via `onnx_asr.load_model`
* **[E3.4] End-to-end pipeline: release + transcribe + copy**

### EPIC 4 - Smart Cleanup and paste

* **[E4.1] Smart Cleanup (rule engine) with modes** (Conservative/Standard/Rewrite + tests)
* **[E4.2] Shift-to-bypass cleanup** (document in first-run tip)
* **[E4.3] Same-hotkey paste window (+ auto-paste toggle)** (works in Notepad, Word, Teams, Slack)

### EPIC 5 - Local history (SQLite + FTS5)

* **[E5.1] SQLite store with FTS5 (utterances)** - retention 90d
* **[E5.2] History palette (search/copy/paste)** - type-ahead FTS, low-latency
* **[E5.3] Export and privacy controls** - export .txt/.json, Clear with confirm; telemetry off

### EPIC 6 - Performance and resilience

* **[E6.1] Performance budgets and local metrics (opt-in)** - release+paste <=600 ms (DML) / <=1.2 s (CPU) for ~5-7 s utterances
* **[E6.2] Error handling and recovery** - model download/backoff, missing mic, hot-unplug, hotkey conflicts
* **[E6.3] Accessibility and theming** - high-contrast icons, keyboardable menu

### EPIC 7 - Packaging and release (PyInstaller + zip)

* **[E7.1] PyInstaller spec (single exe with resources)**
* **[E7.2] Smoke tests on clean Windows VM**
* **[E7.3] Release packaging and README updates**

### EPIC 8 - (later) Microsoft Store readiness (MSIX wrap)

* **[E8.1] MSIX packaging around PyInstaller EXE (later)**
* **[E8.2] WACK pre-check (later)**
* **[E8.3] Store metadata and submission draft (later)**

> The CSV embeds all acceptance criteria and the dependency graph so you can start at **[E0.1]** and work straight through.

---

## Why this is the easy path

* **One process, one binary:** no HTTP server to start or monitor; fewer failure modes.
* **GPU when available:** ONNX Runtime with DirectML accelerates on NVIDIA/AMD/Intel DX12; CPU fallback just works.
* **Leverages current code paths:** reuse the existing sound capture, hotkey handling, cleanup rules, and clipboard helpers.

---

## Minimal prep (because you are new to Windows dev)

* **Python 3.11 (64-bit)** and **Poetry** - required for the existing modules and packaging flow.
* **Git and GitHub CLI** (`winget install Git.Git` and `winget install GitHub.cli`).
* **Visual C++ Build Tools** (only if any wheel falls back to source; most are prebuilt).
* **Optional:** a clean **Windows 11 VM** for smoke testing the PyInstaller build (no dev tools installed).

---

If you want, I can also generate a tiny starter layout (Python) that wires: tray icon, a working hotkey, minimal recorder, DirectML provider check, and a dummy cleanup so you can commit **[E1.1]**-**[E2.1]** immediately.


