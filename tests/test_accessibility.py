"""Tests for accessibility and theming features."""


from app.tray import TrayTheme
from app.tray.icons import TrayIconFactory, _palette_for_theme
from app.tray.state import TrayState


def test_high_contrast_theme_palette():
    """Test that high-contrast theme uses accessible colors."""
    background, border, accents = _palette_for_theme(TrayTheme.HIGH_CONTRAST)

    # High-contrast should use pure white border
    assert border == (255, 255, 255, 255)

    # Accents should be bright and distinct
    assert accents["idle"] == (0, 255, 255, 255)  # Cyan
    assert accents["listening"] == (255, 255, 0, 255)  # Yellow
    assert accents["copied"] == (0, 255, 0, 255)  # Green
    assert accents["error"] == (255, 0, 0, 255)  # Red


def test_light_theme_palette():
    """Test light theme palette."""
    background, border, accents = _palette_for_theme(TrayTheme.LIGHT)

    # Light theme should have dark border for contrast
    assert border == (50, 50, 50, 255)

    # Check all accent colors are defined
    assert "idle" in accents
    assert "listening" in accents
    assert "copied" in accents
    assert "pasted" in accents
    assert "error" in accents


def test_dark_theme_palette():
    """Test dark theme palette."""
    background, border, accents = _palette_for_theme(TrayTheme.DARK)

    # Dark theme should have light border for contrast
    assert border == (230, 230, 230, 255)

    # Check all accent colors are defined
    assert "idle" in accents
    assert "listening" in accents
    assert "copied" in accents
    assert "pasted" in accents
    assert "error" in accents


def test_icon_factory_supports_all_themes():
    """Test that icon factory can generate icons for all themes."""
    factory = TrayIconFactory()

    for theme in [TrayTheme.LIGHT, TrayTheme.DARK, TrayTheme.HIGH_CONTRAST]:
        for state in [
            TrayState.IDLE,
            TrayState.LISTENING,
            TrayState.TRANSCRIBING,
            TrayState.COPIED,
            TrayState.PASTED,
            TrayState.ERROR,
        ]:
            icon = factory.frame(state, theme, size=32)
            assert icon is not None
            assert icon.size == (32, 32)
            assert icon.mode == "RGBA"


def test_icon_sizes_for_dpi_scaling():
    """Test that multiple icon sizes are supported for DPI scaling."""
    factory = TrayIconFactory()

    # Should support common icon sizes
    assert 16 in factory.sizes  # Standard
    assert 20 in factory.sizes  # 125% scaling
    assert 24 in factory.sizes  # 150% scaling
    assert 32 in factory.sizes  # 200% scaling
    assert 48 in factory.sizes  # 300% scaling


def test_animated_states_have_multiple_frames():
    """Test that animated states generate multiple frames."""
    factory = TrayIconFactory()

    # Listening state is animated
    frames = factory.state_frames(TrayState.LISTENING, TrayTheme.LIGHT)

    # Should have frames for each size
    assert 32 in frames

    # Should have multiple frames for animation
    assert len(frames[32]) > 1


def test_static_states_have_single_frame():
    """Test that static states have only one frame."""
    factory = TrayIconFactory()

    # IDLE state is static
    frames = factory.state_frames(TrayState.IDLE, TrayTheme.LIGHT)

    # Should have frames for each size
    assert 32 in frames

    # Should have exactly one frame (no animation)
    assert len(frames[32]) == 1


def test_high_contrast_colors_are_distinct():
    """Test that high-contrast theme colors are maximally distinct."""
    _, _, accents = _palette_for_theme(TrayTheme.HIGH_CONTRAST)

    colors = [
        accents["idle"],
        accents["listening"],
        accents["copied"],
        accents["pasted"],
        accents["error"],
    ]

    # All colors should be unique
    assert len(colors) == len(set(colors))

    # All colors should use max brightness in at least one channel
    for color in colors:
        max_channel = max(color[:3])  # Ignore alpha
        assert max_channel == 255, f"Color {color} not bright enough for high contrast"


def test_theme_detection_falls_back_gracefully():
    """Test that theme detection handles missing registry keys gracefully."""
    from app.tray.controller import detect_tray_theme

    # Should not crash and should return a valid theme
    theme = detect_tray_theme()
    assert theme in [TrayTheme.LIGHT, TrayTheme.DARK, TrayTheme.HIGH_CONTRAST]


def test_icon_cache_efficiency():
    """Test that icon factory caches generated icons."""
    factory = TrayIconFactory()

    # Generate same icon twice
    icon1 = factory.frame(TrayState.IDLE, TrayTheme.LIGHT, 32)
    icon2 = factory.frame(TrayState.IDLE, TrayTheme.LIGHT, 32)

    # Should return same cached instance (lru_cache)
    assert icon1 is icon2
