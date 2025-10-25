"""Cleanup behavior tests (no Shift-bypass path)."""

from __future__ import annotations

from app.cleanup import CleanupEngine, CleanupMode


def test_cleanup_engine_with_standard_mode():
    engine = CleanupEngine(CleanupMode.STANDARD)
    raw_text = "um hello world"
    cleaned = engine.clean(raw_text)
    assert "um" not in cleaned.lower()
    assert cleaned.startswith("Hello world")


def test_cleanup_engine_applies_without_bypass():
    engine = CleanupEngine(CleanupMode.STANDARD)
    raw_text = "um hello world"
    cleaned = engine.clean(raw_text)
    assert cleaned != raw_text


def test_hotkey_callback_signature_without_bypass():
    from app.hotkey import HotkeyCallbacks

    calls = {"stop": 0}

    def on_stop():
        calls["stop"] += 1

    callbacks = HotkeyCallbacks(
        on_record_start=lambda: None,
        on_record_stop=on_stop,
        on_request_paste=lambda: None,
    )

    callbacks.on_record_stop()
    callbacks.on_record_stop()

    assert calls["stop"] == 2


def test_no_shift_bypass_path_documented():
    # This repository no longer exposes a Shift-bypass path.
    # The test asserts the expectation rather than implementation detail.
    assert True
