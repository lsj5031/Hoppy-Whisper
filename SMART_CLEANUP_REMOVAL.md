# Smart Cleanup Removal Summary

This document summarizes the removal of Smart Cleanup from Hoppy Whisper and the resulting behavior changes.

---

## Overview

Smart Cleanup (punctuation, capitalization, and filler‑word removal) has been removed from the application. Transcriptions now go directly from the ONNX transcriber to the clipboard and history with raw model output.

---

## Code Changes

### 1. Settings (`src/app/settings.py`)

- Removed configuration fields:
  - `cleanup_mode: str = "standard"`
  - `cleanup_enabled: bool = True`
- Updated `AppSettings` loading to ignore unknown keys so that existing `settings.json` files containing these keys still load without errors.

### 2. Runtime (`src/app/__main__.py`)

- Removed imports:
  - `from app.cleanup import CleanupEngine, CleanupMode`
- Removed:
  - `self._cleanup_engine` initialization and `_create_cleanup_engine()` helper.
  - `_set_cleanup_enabled()` callback used by the tray.
  - `set_cleanup_enabled` and `cleanup_enabled` wiring into `TrayMenuActions` / `TrayController`.
  - Cleanup logic inside `_complete_transcription()` (no more calls into a cleanup engine).
- Updated `_complete_transcription()`:
  - `cleaned_text = result.text` (raw model output).
  - `cleanup_mode = "raw"` as a fixed mode string recorded in history.
  - Removed cleanup‑specific metrics from telemetry.

### 3. Tray Menu (`src/app/tray/controller.py`)

- Removed from `TrayMenuActions`:
  - `set_cleanup_enabled: Callable[[bool], None]`
- Updated `TrayController`:
  - Removed `cleanup_enabled` parameter and state.
  - Removed `toggle_cleanup_enabled()` method.
  - Removed “Smart Cleanup” menu item from `_build_menu()`.
- Updated the first‑run message:
  - Removed references to toggling Smart Cleanup from the tray menu.

### 4. Package Exports (`src/app/__init__.py`)

- Removed `"cleanup"` from `__all__`.

### 5. Tests

- Deleted:
  - `tests/test_cleanup_engine.py`
  - `tests/test_shift_bypass.py`
- Modified:
  - `tests/test_error_recovery.py` – removed cleanup‑specific test case.
- Added:
  - `tests/test_cleanup_removed.py` – asserts there are no remaining cleanup paths.
  - `tests/test_raw_transcription.py` – asserts raw model text is stored with `mode="raw"` and can be queried.

### 6. Documentation

- **`SMOKE_TEST.md`**
  - Removed the dedicated “Smart Cleanup” section.
  - Renumbered subsequent sections (former section 5 is now section 4, etc.).
  - Removed `cleanup_mode` from the example settings JSON.
  - Updated success criteria to reference raw transcription rather than Smart Cleanup behavior.

- **`README.md`**
  - Removed “smart cleanup” from the introduction and feature list.
  - Removed cleanup from the package layout description.
  - Updated the example `settings.json` to match the new schema (no cleanup fields, includes `auto_paste`).

---

## Behavior Before vs After

Before:

```text
ONNX Model Output → CleanupEngine.clean() → History / Clipboard
```

After:

```text
ONNX Model Output → History / Clipboard (raw)
```

Users now receive the raw model output. Any downstream cleanup is the responsibility of external tools or workflows.

---

## Backward Compatibility

1. **Settings**
   - Old `settings.json` files that contain `cleanup_mode` or `cleanup_enabled` still load.
   - These keys are ignored rather than causing errors.

2. **History Database**
   - The `mode` column remains in the schema.
   - Existing rows with values such as `"standard"`, `"conservative"`, or `"rewrite"` are preserved.
   - New rows are stored with `mode="raw"`.

3. **Imports and Public API**
   - No public imports of `app.cleanup` remain.
   - Applications embedding Hoppy Whisper should not see import errors related to cleanup removal.

---

## Breaking Changes

- Users who relied on Smart Cleanup now receive raw model output instead of cleaned text.
- There is no built‑in way to toggle cleanup behavior from the tray.

These changes are intentional to simplify maintenance and reduce surprises in transcription output.

---

## Future Considerations

1. The `mode` column in the history table could be repurposed or removed in a future schema migration if it is no longer needed.
2. If strong user demand for cleanup returns, consider:
   - Implementing cleanup as an optional plugin or extension.
   - Exposing a simple post‑processing hook that runs outside the core application.
3. Documentation and release notes should clearly communicate that all output is now raw model text by design.

