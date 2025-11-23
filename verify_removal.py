#!/usr/bin/env python3
"""Quick verification script to ensure Smart Cleanup removal is complete."""

import sys
from pathlib import Path

# Add src to path
SRC = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC))


def verify_no_cleanup_imports():
    """Verify cleanup module is not imported anywhere."""
    try:
        # This should fail if cleanup is still in __all__ or actively imported
        from app import cleanup  # noqa: F401

        print("❌ FAIL: app.cleanup is still importable")
        return False
    except ImportError:
        print("✅ PASS: app.cleanup import fails as expected")
        return True


def verify_settings_cleaned():
    """Verify cleanup fields removed from settings."""
    from app.settings import AppSettings

    # Check annotations don't contain cleanup fields
    if "cleanup_mode" in AppSettings.__annotations__:
        print("❌ FAIL: cleanup_mode still in AppSettings")
        return False

    if "cleanup_enabled" in AppSettings.__annotations__:
        print("❌ FAIL: cleanup_enabled still in AppSettings")
        return False

    print("✅ PASS: Cleanup fields removed from AppSettings")
    return True


def verify_old_settings_load():
    """Verify backward compatibility with old settings."""
    from app.settings import AppSettings

    old_settings = {
        "hotkey_chord": "CTRL+SHIFT+;",
        "cleanup_mode": "standard",  # Old field
        "cleanup_enabled": True,  # Old field
        "auto_paste": True,
    }

    try:
        settings = AppSettings.from_dict(old_settings)
        if hasattr(settings, "cleanup_mode") or hasattr(settings, "cleanup_enabled"):
            print("❌ FAIL: Old cleanup fields loaded into settings")
            return False
        print("✅ PASS: Old settings load without cleanup fields")
        return True
    except Exception as e:
        print(f"❌ FAIL: Error loading old settings: {e}")
        return False


def verify_tray_actions_cleaned():
    """Verify TrayMenuActions doesn't have cleanup callback."""
    from app.tray import TrayMenuActions

    if "set_cleanup_enabled" in TrayMenuActions.__annotations__:
        print("❌ FAIL: set_cleanup_enabled still in TrayMenuActions")
        return False

    print("✅ PASS: set_cleanup_enabled removed from TrayMenuActions")
    return True


def verify_history_stores_raw():
    """Verify history can store raw mode."""
    import tempfile

    from app.history import HistoryDAO

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        dao = HistoryDAO(db_path)
        dao.open()

        try:
            # Insert with raw mode
            utterance_id = dao.insert(
                text="test utterance",
                mode="raw",
                duration_ms=1000,
            )

            # Retrieve and verify
            utterance = dao.get_by_id(utterance_id)
            if utterance and utterance.mode == "raw":
                print("✅ PASS: History stores and retrieves mode='raw' correctly")
                return True
            else:
                print("❌ FAIL: History did not store mode='raw' correctly")
                return False
        finally:
            dao.close()


def main():
    """Run all verifications."""
    print("\n" + "=" * 60)
    print("Smart Cleanup Removal Verification")
    print("=" * 60 + "\n")

    checks = [
        ("No Cleanup Imports", verify_no_cleanup_imports),
        ("Settings Cleaned", verify_settings_cleaned),
        ("Old Settings Compatible", verify_old_settings_load),
        ("Tray Actions Cleaned", verify_tray_actions_cleaned),
        ("History Raw Mode", verify_history_stores_raw),
    ]

    results = []
    for name, check_func in checks:
        print(f"\nChecking {name}...")
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ EXCEPTION: {name} - {e}")
            results.append(False)

    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} checks passed")
    print("=" * 60 + "\n")

    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
