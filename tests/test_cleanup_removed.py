"""Test that Smart Cleanup has been removed and raw output is used."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.settings import AppSettings


def test_cleanup_settings_removed():
    """Test that cleanup_mode and cleanup_enabled are not in AppSettings."""
    settings = AppSettings()
    
    # These fields should not exist in annotations
    assert "cleanup_mode" not in AppSettings.__annotations__
    assert "cleanup_enabled" not in AppSettings.__annotations__


def test_old_settings_with_cleanup_still_load():
    """Test that old settings.json files with cleanup fields still load."""
    old_settings_dict = {
        "hotkey_chord": "CTRL+SHIFT+;",
        "paste_window_seconds": 2.0,
        "start_with_windows": False,
        "first_run_complete": True,
        "cleanup_mode": "standard",  # Old field
        "cleanup_enabled": True,  # Old field
        "auto_paste": True,
        "history_retention_days": 90,
        "telemetry_enabled": False,
    }
    
    # Should load without error, ignoring the cleanup fields
    settings = AppSettings.from_dict(old_settings_dict)
    assert settings.hotkey_chord == "CTRL+SHIFT+;"
    assert settings.auto_paste is True
    # Old fields are simply ignored
    assert not hasattr(settings, "cleanup_mode")
    assert not hasattr(settings, "cleanup_enabled")


def test_settings_save_excludes_cleanup():
    """Test that saved settings.json does not contain cleanup fields."""
    settings = AppSettings()
    settings_dict = settings.to_dict()
    
    # Cleanup fields should not be in the saved dict
    assert "cleanup_mode" not in settings_dict
    assert "cleanup_enabled" not in settings_dict
    
    # But other fields should be present
    assert "hotkey_chord" in settings_dict
    assert "auto_paste" in settings_dict


def test_tray_menu_actions_without_cleanup():
    """Test that TrayMenuActions doesn't have set_cleanup_enabled."""
    from app.tray import TrayMenuActions
    
    # Check annotations
    assert "set_cleanup_enabled" not in TrayMenuActions.__annotations__


def test_no_cleanup_imports_in_main():
    """Test that __main__ doesn't import cleanup module."""
    import app.__main__ as main_module
    
    # Verify that the cleanup imports have been removed
    # by checking that certain references don't exist
    assert not hasattr(main_module, "CleanupEngine")
    assert not hasattr(main_module, "CleanupMode")


def test_cleanup_not_in_app_exports():
    """Test that cleanup is not in app.__all__."""
    import app
    
    assert "cleanup" not in app.__all__
