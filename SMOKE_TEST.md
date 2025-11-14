# Hoppy Whisper Smoke Test Checklist

This document provides a smoke test checklist for verifying a Hoppy Whisper release build on a clean Windows machine.

---

## Prerequisites

- Clean Windows 11 (or Windows 10) machine/VM with no development tools installed
- No system-wide Python required
- Microphone available (or virtual audio device)
- Internet connection for first-run model download

---

## Pre-Test Setup

1. Download the latest `Hoppy Whisper-CPU.exe` from GitHub Releases.
2. Place the executable in a test directory (for example, `C:\Test\Hoppy Whisper`).
3. Ensure Windows Defender / antivirus does not block the executable.
4. Enable microphone access in Windows privacy settings:
   - Settings → Privacy & Security → Microphone
   - Enable “Let apps access your microphone”.

---

## 1. First Launch

**Expected:** Application starts without errors and shows the first‑run notification.

- [ ] Double‑click `Hoppy Whisper-CPU.exe`.
- [ ] Application launches and tray icon appears (idle state).
- [ ] First‑run notification appears explaining the default hotkey.
- [ ] No console window appears.
- [ ] No error dialogs are shown.

On failure:

- Check Event Viewer for application errors.
- Look for missing DLL errors.
- Verify antivirus is not blocking execution.

---

## 2. Model Download

**Expected:** Models download automatically on the first transcription attempt.

- [ ] Press the default hotkey `Ctrl+Shift+;`.
- [ ] Icon changes to “Listening” state (microphone).
- [ ] Speak a short phrase: “Testing one two three”.
- [ ] Release the hotkey.
- [ ] Icon changes to “Transcribing” state (spinner).
- [ ] Application downloads models (may take 30–60 seconds on first run).
- [ ] Models are cached to `%LOCALAPPDATA%\Hoppy Whisper\models\`.
- [ ] After transcription completes, text is copied to the clipboard.
- [ ] Success notification appears with a preview of the transcription.

On failure:

- Check internet connection.
- Verify firewall is not blocking HTTPS requests to `huggingface.co`.
- Check `%LOCALAPPDATA%\Hoppy Whisper\models\` for partial downloads.
- Look for error notifications.

---

## 3. Hotkey Recording Workflow

**Expected:** Press‑and‑hold to record, release to transcribe, optional paste.

### 3a. Basic Recording

- [ ] Open Notepad.
- [ ] Press and hold `Ctrl+Shift+;`.
- [ ] Speak: “This is a test of the Hoppy Whisper transcription system”.
- [ ] Release the hotkey.
- [ ] Wait for transcription to complete.
- [ ] Paste manually with `Ctrl+V`.
- [ ] Transcribed text appears in Notepad with reasonable capitalization and punctuation.

### 3b. Same‑Hotkey Paste

- [ ] Open a new Notepad window.
- [ ] Press and hold `Ctrl+Shift+;`.
- [ ] Speak: “Testing automatic paste feature”.
- [ ] Release the hotkey.
- [ ] Press `Ctrl+Shift+;` again within the paste window (default 2 seconds).
- [ ] Text is automatically pasted into Notepad.
- [ ] Icon shows “Pasted” state.

### 3c. Auto‑Paste Mode

- [ ] Right‑click tray icon → Settings.
- [ ] Edit `settings.json` and set `"auto_paste": true`.
- [ ] Save and restart Hoppy Whisper.
- [ ] Press and hold `Ctrl+Shift+;`, say “Auto paste enabled”, then release.
- [ ] Text automatically pastes without pressing the hotkey a second time.

---

## 4. History & Search

**Expected:** Transcriptions are saved to local SQLite history with FTS5 search.

- [ ] Right‑click tray icon → History.
- [ ] History palette window opens.
- [ ] Previous transcriptions are listed.
- [ ] Type a search query (for example, “test”).
- [ ] Results update as you type.
- [ ] Press Enter to copy selected item to the clipboard.
- [ ] Press Esc to close the palette.
- [ ] Verify history database exists at `%LOCALAPPDATA%\Hoppy Whisper\history.db`.

---

## 5. Settings & Configuration

**Expected:** Settings are persisted and applied correctly.

- [ ] Right‑click tray icon → Settings.
- [ ] File Explorer opens to `%LOCALAPPDATA%\Hoppy Whisper\settings.json`.
- [ ] Edit settings to:

  ```json
  {
    "hotkey_chord": "CTRL+ALT+V",
    "paste_window_seconds": 3.0,
    "start_with_windows": true,
    "auto_paste": false
  }
  ```

- [ ] Save and restart Hoppy Whisper.
- [ ] Verify the new hotkey (`Ctrl+Alt+V`) starts recording.
- [ ] Verify paste window is approximately 3 seconds.

---

## 6. Start with Windows

**Expected:** Application starts automatically on login when enabled.

- [ ] Right‑click tray icon → Start with Windows (check to enable).
- [ ] Verify registry key exists:
  - `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Hoppy Whisper`
- [ ] Log out and back in (or reboot).
- [ ] Verify Hoppy Whisper starts automatically and tray icon appears within ~5 seconds.

---

## 7. Error Handling

**Expected:** Application handles common errors gracefully with clear messages.

### 7a. Microphone Missing

- [ ] Disable all audio input devices.
- [ ] Press the hotkey.
- [ ] Verify error notification: “Microphone Error: No audio input device available”.
- [ ] Icon shows error state (for example, red X).
- [ ] Application does not crash.

### 7b. Hotkey Conflict

- [ ] Use another application (for example, AutoHotkey) to register `Ctrl+Shift+;`.
- [ ] Launch Hoppy Whisper.
- [ ] Verify error dialog: “Hotkey already in use by another application”.
- [ ] Application exits gracefully (does not remain running without a hotkey).

### 7c. Short Recording

- [ ] Press and immediately release the hotkey (<0.1 seconds).
- [ ] Verify notification: “Recording Too Short: Please hold the hotkey longer”.
- [ ] Icon shows error state then returns to idle.

---

## 8. Multi‑Application Paste

**Expected:** Paste works correctly in multiple applications.

Test paste in:

- [ ] Notepad
- [ ] Microsoft Word
- [ ] Microsoft Teams (chat)
- [ ] Slack desktop app
- [ ] Outlook email composer
- [ ] VS Code
- [ ] Web browser (Chrome/Edge) text field

---

## 9. Performance & Resource Usage

**Expected:** Low CPU when idle and acceptable end‑to‑end latency.

- [ ] Open Task Manager.
- [ ] Monitor CPU usage when idle: target <1%.
- [ ] Record a 5–7 second utterance.
- [ ] Measure time from hotkey release to clipboard ready:
  - **GPU (DirectML):** target ≲ 600 ms.
  - **CPU fallback:** target ≲ 1.2 seconds.
- [ ] Verify there are no obvious memory leaks after 10+ transcriptions.
- [ ] Check idle memory usage after tests (target <200 MB).

---

## 10. Accessibility

**Expected:** High‑contrast support and keyboard navigation work.

- [ ] Enable Windows High Contrast mode.
- [ ] Verify tray icon remains visible against high‑contrast theme.
- [ ] Right‑click tray icon.
- [ ] Navigate the menu using arrow keys.
- [ ] Press Enter to activate menu items.
- [ ] Verify all menu items are keyboard accessible.

---

## 11. Cleanup & Uninstall

**Expected:** Application can be removed cleanly.

- [ ] Right‑click tray icon → Quit.
- [ ] Application exits completely (no lingering processes).
- [ ] Delete `Hoppy Whisper-CPU.exe`.
- [ ] If Start with Windows was enabled, verify registry key was removed:
  - `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Hoppy Whisper`
- [ ] Optionally delete user data:
  - `%LOCALAPPDATA%\Hoppy Whisper\settings.json`
  - `%LOCALAPPDATA%\Hoppy Whisper\models\`
  - `%LOCALAPPDATA%\Hoppy Whisper\history.db`

---

## Success Criteria

All of the following must be true for the build to be considered production‑ready:

- [ ] Application launches without errors on a clean Windows VM.
- [ ] Models download and cache correctly.
- [ ] Hotkey recording and paste workflow works end‑to‑end.
- [ ] Raw transcriptions are captured without Smart Cleanup.
- [ ] History and search work with FTS5 queries.
- [ ] Settings persist across restarts.
- [ ] Start with Windows toggle works correctly.
- [ ] Error handling is clear and non‑crashing.
- [ ] Performance meets targets (GPU ≲ 600 ms, CPU ≲ 1.2 s).
- [ ] Paste works in all tested applications.
- [ ] Accessibility features (high contrast, keyboard navigation) function as expected.
- [ ] Application can be cleanly uninstalled.

If any item fails, record:

1. The checklist item that failed.
2. Expected behavior.
3. Actual behavior.
4. Any error dialogs, logs, or crash dumps.

