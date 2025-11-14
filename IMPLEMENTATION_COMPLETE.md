# Smart Cleanup Removal – Implementation Complete

## Summary

Smart Cleanup has been removed from Hoppy Whisper. All transcriptions now go directly from the ONNX model to history and clipboard without any text post‑processing.

---

## What Was Changed

### 1. Core Application

1. **`src/app/settings.py`**
   - Removed `cleanup_mode` and `cleanup_enabled` fields from the `AppSettings` dataclass.
   - Updated settings loading so unknown keys are ignored, preserving backward compatibility with existing `settings.json` files.

2. **`src/app/__main__.py`**
   - Removed imports of `CleanupEngine` / `CleanupMode` from `app.cleanup`.
   - Removed `self._cleanup_engine` and the `_create_cleanup_engine()` helper.
   - Removed `_set_cleanup_enabled()` tray callback.
   - Updated `_complete_transcription()` to:
     - Use raw model output directly (`cleaned_text = result.text`).
     - Use a fixed mode string: `cleanup_mode = "raw"`.
     - Stop recording any cleanup‑specific metrics.

3. **`src/app/tray/controller.py`**
   - Removed `set_cleanup_enabled` from the `TrayMenuActions` dataclass.
   - Removed `cleanup_enabled` parameter from `TrayController.__init__()`.
   - Removed `toggle_cleanup_enabled()` and the “Smart Cleanup” tray menu item.
   - Updated first‑run messaging to remove Smart Cleanup references.

4. **`src/app/__init__.py`**
   - Removed `"cleanup"` from `__all__`.

### 2. Cleanup Module

5. **`src/app/cleanup/`**
   - Deleted the entire cleanup package (both `__init__.py` and `engine.py`).

### 3. Tests

6. **Deleted tests**
   - `tests/test_cleanup_engine.py` – Cleanup engine unit tests.
   - `tests/test_shift_bypass.py` – Shift‑to‑bypass cleanup behavior tests.

7. **Modified tests**
   - `tests/test_error_recovery.py` – Removed `test_cleanup_handles_invalid_mode_gracefully`.

8. **New tests**
   - `tests/test_cleanup_removed.py` – Verifies that no cleanup code paths remain.
   - `tests/test_raw_transcription.py` – Verifies raw transcription output is stored with `mode="raw"` and exported correctly.

### 4. Documentation

9. **`SMOKE_TEST.md`**
   - Removed the “Smart Cleanup” section and renumbered later sections.
   - Removed `cleanup_mode` from the example `settings.json`.
   - Updated success criteria to focus on raw transcription behavior.

10. **`README.md`**
    - Removed “smart cleanup” from the high‑level description and feature list.
    - Removed cleanup references from the package layout.
    - Updated the example `settings.json` to match the new settings schema (including `auto_paste`).

11. **`SMART_CLEANUP_REMOVAL.md`**
    - Added as a dedicated document summarizing the rationale and the code changes.

---

## Current Behavior

Before:

```text
Audio → Transcriber → CleanupEngine → History/Clipboard
```

After:

```text
Audio → Transcriber → History/Clipboard
```

All output is now raw model text; no punctuation, capitalization, or filler removal is performed by Hoppy Whisper.

---

## Backward Compatibility

- **Settings:** Existing `settings.json` files that include `cleanup_mode` or `cleanup_enabled` still load successfully. Unknown keys are ignored.
- **History:** The `mode` column in the history database is preserved. Existing rows with legacy cleanup modes remain intact; new rows use `mode="raw"`.
- **Imports:** All references to `app.cleanup` have been removed from active code, so import‑time errors are avoided.

---

## Verification Checklist

Use this to confirm that Smart Cleanup is fully removed:

- [ ] No imports of `app.cleanup` remain in the source tree.
- [ ] No references to `CleanupEngine` or `CleanupMode` remain.
- [ ] `TrayMenuActions` no longer exposes `set_cleanup_enabled`.
- [ ] `TrayController` has no `cleanup_enabled` state or “Smart Cleanup” menu items.
- [ ] `_complete_transcription()` uses `result.text` directly and sets `cleanup_mode = "raw"`.
- [ ] History rows for new transcriptions use `mode="raw"`.
- [ ] All cleanup‑specific tests have been removed or replaced.
- [ ] New tests (`test_cleanup_removed.py`, `test_raw_transcription.py`) pass.
- [ ] README and SMOKE_TEST documentation no longer claim Smart Cleanup exists.

---

## Files Touched (Summary)

- `src/app/settings.py`
- `src/app/__main__.py`
- `src/app/tray/controller.py`
- `src/app/__init__.py`
- `src/app/cleanup/` (deleted)
- `tests/test_cleanup_engine.py` (deleted)
- `tests/test_shift_bypass.py` (deleted)
- `tests/test_error_recovery.py`
- `tests/test_cleanup_removed.py`
- `tests/test_raw_transcription.py`
- `README.md`
- `SMOKE_TEST.md`
- `SMART_CLEANUP_REMOVAL.md`

---

## Next Steps

1. Run the full test suite: `poetry run pytest`.
2. Perform a manual smoke test on a clean Windows VM using `SMOKE_TEST.md`.
3. Update release notes to call out the removal of Smart Cleanup and the new “raw only” behavior.
4. If demand arises, consider re‑introducing cleanup as an optional plugin or external tool rather than a core feature.

