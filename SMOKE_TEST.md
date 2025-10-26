# Hoppy Whisper Smoke Test Checklist

This document provides a comprehensive smoke test checklist for verifying the Hoppy Whisper build on a clean Windows VM.

## Prerequisites

- **Clean Windows 11 VM** with no development tools installed
- **No Python** installed on the system
- **Microphone** available (or virtual audio device for testing)
- **Internet connection** for first-run model download

## Pre-Test Setup

1. Download the latest `Hoppy Whisper-CPU.exe` from GitHub Releases
2. Place the executable in a test directory (e.g., `C:\Test\Hoppy Whisper`)
3. Ensure Windows Defender or antivirus doesn't block the executable
4. Enable microphone access in Windows Privacy Settings:
   - Go to **Settings > Privacy & Security > Microphone**
   - Enable "Let apps access your microphone"

## Test Plan

### 1. First Launch

**Expected:** Application starts without errors and shows first-run notification.

- [ ] Double-click `Hoppy Whisper-CPU.exe`
- [ ] Application launches and tray icon appears (should show idle state)
- [ ] First-run notification appears explaining the default hotkey
- [ ] No console window appears (windowed mode)
- [ ] No error dialogs

**On failure:**
- Check Event Viewer for application errors
- Look for missing DLL errors
- Verify antivirus isn't blocking execution

---

### 2. Model Download

**Expected:** Models download automatically from Hugging Face on first transcription attempt.

- [ ] Press the default hotkey `Ctrl+Shift+;`
- [ ] Icon changes to "Listening" state (animated microphone)
- [ ] Speak a short phrase: "Testing one two three"
- [ ] Release the hotkey
- [ ] Icon changes to "Transcribing" state (spinner animation)
- [ ] Application downloads models (may take 30-60 seconds on first run)
- [ ] Models are cached to `%LOCALAPPDATA%\Hoppy Whisper\models\`
- [ ] After transcription completes, text is copied to clipboard
- [ ] Success notification appears with transcribed text preview

**On failure:**
- Check internet connection
- Verify firewall isn't blocking HTTPS requests to huggingface.co
- Check `%LOCALAPPDATA%\Hoppy Whisper\models\` for partial downloads
- Look for error notifications

---

### 3. Hotkey Recording Workflow

**Expected:** Press-and-hold to record, release to transcribe, press again to paste.

#### 3a. Basic Recording

- [ ] Open Notepad
- [ ] Press and hold `Ctrl+Shift+;`
- [ ] Speak: "This is a test of the Hoppy Whisper transcription system"
- [ ] Release the hotkey
- [ ] Wait for transcription to complete
- [ ] Verify text is copied to clipboard (paste manually with `Ctrl+V`)
- [ ] Transcribed text appears in Notepad with proper capitalization and punctuation

#### 3b. Same-Hotkey Paste

- [ ] Open a new Notepad window
- [ ] Press and hold `Ctrl+Shift+;`
- [ ] Speak: "Testing automatic paste feature"
- [ ] Release the hotkey
- [ ] Immediately press `Ctrl+Shift+;` again within 2 seconds
- [ ] Text automatically pastes into Notepad (Ctrl+V simulated)
- [ ] Icon shows "Pasted" state (arrow icon)

#### 3c. Auto-Paste Mode

- [ ] Right-click tray icon → Settings
- [ ] Edit `settings.json` and set `"auto_paste": true`
- [ ] Save and restart Hoppy Whisper
- [ ] Press and hold `Ctrl+Shift+;`
- [ ] Speak: "Auto paste enabled"
- [ ] Release the hotkey
- [ ] Text automatically pastes without pressing hotkey again

---

### 4. Smart Cleanup

**Expected:** Transcribed text is cleaned with punctuation, capitalization, and filler removal.

#### 4a. Standard Cleanup

- [ ] Press and hold hotkey, speak: "um so like this is you know a test"
- [ ] Release hotkey
- [ ] Verify clipboard contains: "This is a test" (fillers removed)
- [ ] Verify proper capitalization

<!-- Shift-to-bypass behavior has been removed; all transcriptions follow the configured cleanup setting. -->

---

### 5. History & Search

**Expected:** All transcriptions are saved to local SQLite database with FTS5 search.

- [ ] Right-click tray icon → History
- [ ] History palette window opens
- [ ] Previous transcriptions are listed
- [ ] Type search query (e.g., "test")
- [ ] Results update in real-time (FTS5 search)
- [ ] Press `Enter` to copy selected item to clipboard
- [ ] Press `Esc` to close palette
- [ ] Verify history database exists at `%LOCALAPPDATA%\Hoppy Whisper\history.db`

---

### 6. Settings & Configuration

**Expected:** Settings are persisted and applied correctly.

- [ ] Right-click tray icon → Settings
- [ ] File explorer opens to `%LOCALAPPDATA%\Hoppy Whisper\settings.json`
- [ ] Edit settings:
  ```json
  {
    "hotkey_chord": "CTRL+ALT+V",
    "paste_window_seconds": 3.0,
    "cleanup_mode": "conservative",
    "start_with_windows": true,
    "auto_paste": false
  }
  ```
- [ ] Save and restart Hoppy Whisper
- [ ] Verify new hotkey works (`Ctrl+Alt+V`)
- [ ] Verify paste window is 3 seconds
- [ ] Check registry key: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Hoppy Whisper`

---

### 7. Start with Windows

**Expected:** Application starts automatically on login when enabled.

- [ ] Right-click tray icon → Start with Windows (check)
- [ ] Verify registry key exists: `HKCU\Software\Microsoft\Windows\CurrentVersion\Run\Hoppy Whisper`
- [ ] Log out and log back in (or reboot)
- [ ] Verify Hoppy Whisper starts automatically
- [ ] Tray icon appears within 5 seconds of login

---

### 8. Error Handling

**Expected:** Application handles errors gracefully with clear messages.

#### 8a. Microphone Missing

- [ ] Disable all audio input devices
- [ ] Press hotkey
- [ ] Verify error notification: "Microphone Error: No audio input device available"
- [ ] Icon shows error state (red X)
- [ ] Application does not crash

#### 8b. Hotkey Conflict

- [ ] Use another application to register `Ctrl+Shift+;` (e.g., AutoHotkey)
- [ ] Launch Hoppy Whisper
- [ ] Verify error dialog: "Hotkey already in use by another application"
- [ ] Application does not start (exits gracefully)

#### 8c. Short Recording

- [ ] Press and immediately release hotkey (<0.1 seconds)
- [ ] Verify notification: "Recording Too Short: Please hold the hotkey longer"
- [ ] Icon shows error state
- [ ] Application recovers to idle state

---

### 9. Multi-Application Paste Test

**Expected:** Paste works correctly in various applications.

Test paste functionality in:

- [ ] Notepad
- [ ] Microsoft Word
- [ ] Microsoft Teams (chat window)
- [ ] Slack desktop app
- [ ] Outlook email composer
- [ ] VS Code
- [ ] Web browser (Chrome/Edge) text field

---

### 10. Performance & Resource Usage

**Expected:** Low CPU when idle, fast transcription on GPU.

- [ ] Open Task Manager
- [ ] Monitor Hoppy CPU usage when idle: **<1%**
- [ ] Record a 5-7 second utterance
- [ ] Note transcription time from release to clipboard:
  - **GPU (DirectML):** ≤600 ms
  - **CPU fallback:** ≤1.2 seconds
- [ ] Verify no memory leaks after 10+ transcriptions
- [ ] Check final memory usage: **<200 MB idle**

---

### 11. Accessibility Features

**Expected:** High-contrast icons, keyboard navigation work correctly.

- [ ] Enable Windows High Contrast mode
- [ ] Verify tray icon switches to high-contrast variants
- [ ] Right-click tray icon
- [ ] Navigate menu using arrow keys
- [ ] Press Enter to activate menu items
- [ ] Verify all menu items are keyboard-accessible

---

### 12. Cleanup & Uninstall

**Expected:** Application can be cleanly removed.

- [ ] Right-click tray icon → Quit
- [ ] Application exits completely
- [ ] Delete `Hoppy Whisper-CPU.exe`
- [ ] Verify registry key removed: `HKCU\...\Run\Hoppy Whisper` (if Start with Windows was enabled)
- [ ] Optionally delete user data:
  - `%LOCALAPPDATA%\Hoppy Whisper\settings.json`
  - `%LOCALAPPDATA%\Hoppy Whisper\models\`
  - `%LOCALAPPDATA%\Hoppy Whisper\history.db`

---

## Success Criteria

All checklist items must pass for the build to be considered production-ready:

- ✅ Application launches without errors on clean Windows 11 VM
- ✅ Models download and cache correctly
- ✅ Hotkey recording and paste workflow works end-to-end
- ✅ Smart Cleanup functions correctly (no Shift-bypass)
- ✅ History and search work with FTS5 queries
- ✅ Settings persist across restarts
- ✅ Start with Windows toggle works correctly
- ✅ Error handling is graceful with clear notifications
- ✅ Performance meets budgets (GPU: ≤600ms, CPU: ≤1.2s)
- ✅ Paste works in all tested applications
- ✅ Accessibility features function as expected
- ✅ Application can be cleanly removed

---

## Failure Reporting

If any test fails, document:

1. **Test Step:** Which checklist item failed
2. **Expected Behavior:** What should have happened
3. **Actual Behavior:** What actually happened
4. **Error Messages:** Any dialogs, logs, or console output
5. **System Info:** Windows version, hardware specs
6. **Reproduction:** Steps to reproduce the failure

Submit failure reports as GitHub issues with the `bug` and `smoke-test` labels.
