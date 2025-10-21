Perfect—here’s the **re‑thought “easy path” plan**: a **single‑binary Windows tray app in Python** (no local/remote HTTP server), with **in‑process ONNX Runtime (DirectML)**, global hotkey, VAD auto‑stop, **same‑hotkey paste window**, rule‑based **Smart Cleanup**, and **SQLite+FTS history**. This lines up with your current repo’s strengths (onnxruntime‑directml, `onnx_asr`, pystray/pynput, rule cleanup), just streamlined for the simplest ship path. 

Below are **ready‑to‑import GitHub issues** (acceptance criteria + dependencies), plus a script to create them in your new repo.

---

## Download your backlog + importer

* **Issues CSV (easy path):** [issues_easy_path.csv](sandbox:/mnt/data/issues_easy_path.csv)
* **Create issues in GitHub (PowerShell):** [create_issues_easy_path.ps1](sandbox:/mnt/data/create_issues_easy_path.ps1)

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
* **Kept/Simplified:** In‑process ASR via `onnxruntime-directml` and `onnx_asr`, first‑run model download & cache, tray/Hotkey/Auto‑paste, rule‑based cleanup with tests, local history, PyInstaller packaging. 
* **Result:** Fewer moving parts, faster to build, easier to test/release.

---

## Dependency flow (high level)

```
[E0.*] foundation
   ├─ [E1.*] tray + hotkey + settings
   ├─ [E2.*] audio + VAD → [E2.3] buffers
   ├─ [E3.1] DirectML → [E3.2] model assets → [E3.3] transcriber → [E3.4] end‑to‑end
   ├─ [E4.*] cleanup + same‑hotkey paste
   ├─ [E5.*] SQLite history + palette
   └─ [E6.*] perf/resilience → [E7.*] PyInstaller → (later) [E8.*] Store
```

---

## Backlog overview (you’ll get each as a GitHub issue)

### EPIC 0 — Project foundation (Python, no HTTP)

* **[E0.1] Initialize Python tray app repo (Poetry + src layout)**
* **[E0.2] Code quality & tooling (Ruff, Mypy, Pre-commit)**
* **[E0.3] Windows CI (GitHub Actions): test + PyInstaller artifact)**
* **[E0.4] Versioning & release workflow**

### EPIC 1 — Tray & Settings

* **[E1.1] System tray icon & context menu (pystray)**
* **[E1.2] Global hotkey (reliable) with paste‑window timer** — press/hold=record; release=stop; press again within N seconds=paste.
* **[E1.3] Icon state engine (Idle/Listening/Transcribing/Copied/Pasted/Error)**
* **[E1.4] Settings JSON + minimal UI hook**
* **[E1.5] Start with Windows (HKCU\…\Run)**

### EPIC 2 — Audio capture & VAD

* **[E2.1] WASAPI capture @16 kHz mono (sounddevice)**
* **[E2.2] WebRTC VAD gate (auto‑stop on trailing silence)**
* **[E2.3] Temp WAV writer + PCM16 buffer utility**

### EPIC 3 — In‑process ASR (ONNX Runtime + DirectML)

* **[E3.1] DirectML provider detection & session init** (prefer DML; fallback CPU).
* **[E3.2] Model asset manager (download/cache/validate)** — encoder/decoder/vocab in `%LOCALAPPDATA%/<App>/models`.
* **[E3.3] Parakeet ONNX transcriber (embedded)** — via `onnx_asr.load_model`.
* **[E3.4] End‑to‑end pipeline: release → transcribe → copy**

### EPIC 4 — Smart Cleanup & paste

* **[E4.1] Smart Cleanup (rule engine) with modes** (Conservative/Standard/Rewrite + tests).
* **[E4.2] Shift‑to‑bypass cleanup** (document in first‑run tip).
* **[E4.3] Same‑hotkey paste window (+ auto‑paste toggle)** (works in Notepad, Word, Teams, Slack).

### EPIC 5 — Local history (SQLite + FTS5)

* **[E5.1] SQLite store with FTS5 (utterances)** — retention 90d.
* **[E5.2] History palette (search/copy/paste)** — type‑ahead FTS, low‑latency.
* **[E5.3] Export & privacy controls** — export .txt/.json, Clear with confirm; telemetry off.

### EPIC 6 — Performance & resilience

* **[E6.1] Performance budgets & local metrics (opt‑in)** — release→paste ≤600ms (DML) / ≤1.2s (CPU) for ~5–7s utterances.
* **[E6.2] Error handling & recovery** — model download/backoff, missing mic, hot‑unplug, hotkey conflicts.
* **[E6.3] Accessibility & theming** — high‑contrast icons, keyboardable menu.

### EPIC 7 — Packaging & release (PyInstaller → zip)

* **[E7.1] PyInstaller spec (single‑exe with resources)**
* **[E7.2] Smoke tests on clean Windows VM**
* **[E7.3] Release packaging & README updates**

### EPIC 8 — (Later) Microsoft Store readiness (MSIX wrap)

* **[E8.1] MSIX packaging around PyInstaller EXE (later)**
* **[E8.2] WACK pre‑check (later)**
* **[E8.3] Store metadata & submission draft (later)**

> The CSV embeds all acceptance criteria and the dependency graph so you can start at **[E0.1]** and work straight through.

---

## Why this is the “easy path”

* **One process, one binary**: No HTTP server to start/monitor; fewer failure modes.
* **GPU when available**: ONNX Runtime w/ **DirectML** auto‑accelerates on NVIDIA/AMD/Intel DX12; CPU fallback just works. 
* **Leverages your current code paths**: `onnx_asr.load_model`, `onnxruntime-directml`, `sounddevice` recorder, `pystray`/`pynput`, **rule‑based cleanup** (already tested), clipboard paste, etc. 

---

## Minimal prep (because you’re new to Windows dev)

* **Python 3.11 (64‑bit)** and **Poetry**.
* **Git & GitHub CLI** (`winget install Git.Git` and `winget install GitHub.cli`).
* **Visual C++ Build Tools** (only if any wheel falls back to source; most are prebuilt).
* **Optional**: a clean **Windows 11 VM** for smoke testing the PyInstaller build (no dev tools installed).

---

If you want, I can also generate a tiny starter layout (Python) that wires: tray icon, a working hotkey, minimal recorder, DirectML provider check, and a dummy “cleanup” so you can commit **[E1.1]–[E2.1]** immediately.
