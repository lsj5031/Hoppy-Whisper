#!/usr/bin/env python3
"""
Generate all required Microsoft Store assets from existing ICO files.

This script converts the existing .ico files in the icos/ directory to PNG
assets required for MSIX packaging and Microsoft Store submission.

Usage:
    poetry run python msix/generate_assets.py

Requirements:
    - Pillow library (install with: poetry run pip install Pillow)
"""

import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("❌ Pillow library not found.")
    print("Please install it with: poetry run pip install Pillow")
    sys.exit(1)


def ensure_directory(directory: Path) -> None:
    """Create directory if it doesn't exist."""
    directory.mkdir(parents=True, exist_ok=True)
    print(f"📁 Created/verified directory: {directory}")


def convert_icon_to_png(
    ico_path: Path, sizes: dict[str, tuple[int, int]], output_dir: Path
) -> None:
    """
    Convert ICO file to multiple PNG sizes.

    Args:
        ico_path: Path to source ICO file
        sizes: Dictionary mapping output filename to (width, height) tuple
        output_dir: Directory to save PNG files
    """
    print(f"\n🖼️  Processing: {ico_path.name}")

    if not ico_path.exists():
        print(f"❌ Source icon not found: {ico_path}")
        return

    try:
        img = Image.open(ico_path)

        # If ICO has multiple sizes, use the largest one
        if hasattr(img, "n_frames") and img.n_frames > 1:
            # Get all available sizes
            available_sizes = []
            for i in range(img.n_frames):
                img.seek(i)
                available_sizes.append((img.width, img.height))

            # Use the largest size
            largest_idx = max(
                range(len(available_sizes)),
                key=lambda i: available_sizes[i][0] * available_sizes[i][1],
            )
            img.seek(largest_idx)
            w, h = available_sizes[largest_idx]
            print(f"   Using frame {largest_idx} ({w}x{h})")

        # Convert to RGBA if not already
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Generate each required size
        for filename, size in sizes.items():
            output_path = output_dir / filename

            # Resize with high-quality resampling
            resized = img.resize(size, Image.Resampling.LANCZOS)

            # Save as PNG
            resized.save(output_path, "PNG")

            print(f"   ✅ Created: {filename} ({size[0]}x{size[1]})")

    except Exception as e:
        print(f"   ❌ Error processing {ico_path.name}: {e}")


def generate_store_icon(ico_path: Path, output_dir: Path) -> None:
    """
    Generate high-resolution store icon (1024x1024).

    Args:
        ico_path: Path to source ICO file
        output_dir: Directory to save the icon
    """
    print("\n🏪 Generating Store Icon (1024x1024)")

    if not ico_path.exists():
        print(f"❌ Source icon not found: {ico_path}")
        return

    try:
        img = Image.open(ico_path)

        # Use largest frame if multiple sizes
        if hasattr(img, "n_frames") and img.n_frames > 1:
            sizes = []
            for i in range(img.n_frames):
                img.seek(i)
                sizes.append((img.width, img.height))
            largest_idx = max(
                range(len(sizes)), key=lambda i: sizes[i][0] * sizes[i][1]
            )
            img.seek(largest_idx)

        # Convert to RGBA
        if img.mode != "RGBA":
            img = img.convert("RGBA")

        # Resize to 1024x1024 (Store requirement)
        store_icon = img.resize((1024, 1024), Image.Resampling.LANCZOS)

        output_path = output_dir / "StoreIcon_1024x1024.png"
        store_icon.save(output_path, "PNG")

        print("   ✅ Created: StoreIcon_1024x1024.png")
        print("   📤 Upload this to Partner Center for Store listing")

    except Exception as e:
        print(f"   ❌ Error generating store icon: {e}")


def main():
    """Main execution function."""
    print("=" * 60)
    print("🐰 Hoppy Whisper - Microsoft Store Asset Generator")
    print("=" * 60)

    # Define paths
    project_root = Path(__file__).parent.parent
    icos_dir = project_root / "icos"
    assets_dir = project_root / "msix" / "Assets"
    screenshots_dir = project_root / "msix" / "Screenshots"

    # Ensure output directories exist
    ensure_directory(assets_dir)
    ensure_directory(screenshots_dir)

    # Define source icon
    source_icon = icos_dir / "BunnyPauseRounded.ico"

    # Define required MSIX package assets
    msix_assets = {
        # Square tiles
        "Square44x44Logo.png": (44, 44),
        "Square44x44Logo.scale-200.png": (88, 88),
        "Square150x150Logo.png": (150, 150),
        "Square150x150Logo.scale-200.png": (300, 300),
        "Square310x310Logo.png": (310, 310),
        "Square310x310Logo.scale-200.png": (620, 620),
        # Wide tile
        "Wide310x150Logo.png": (310, 150),
        "Wide310x150Logo.scale-200.png": (620, 300),
        # Small tile
        "SmallTile.png": (71, 71),
        "SmallTile.scale-200.png": (142, 142),
        # Store logo
        "StoreLogo.png": (50, 50),
        "StoreLogo.scale-200.png": (100, 100),
        # Splash screen
        "SplashScreen.png": (620, 300),
        "SplashScreen.scale-200.png": (1240, 600),
    }

    # Define alternative icons for different states (optional)
    alternative_icons = {
        "BunnyPause.ico": "Pause",
        "BunnyTranscribe1.ico": "Transcribe",
    }

    print("\n" + "=" * 60)
    print("📦 Generating MSIX Package Assets")
    print("=" * 60)

    # Generate main MSIX assets
    convert_icon_to_png(source_icon, msix_assets, assets_dir)

    # Generate high-res store icon
    generate_store_icon(source_icon, assets_dir)

    print("\n" + "=" * 60)
    print("🎨 Optional: Alternative Icon States")
    print("=" * 60)

    print("\nYou can also generate alternative versions from other icons:")
    for icon_file, state_name in alternative_icons.items():
        icon_path = icos_dir / icon_file
        if icon_path.exists():
            print(f"   • {icon_file} (for {state_name} state)")
        else:
            print(f"   ⚠️  {icon_file} not found")

    print("\nTo use alternative icons, manually replace generated PNGs in msix/Assets/")

    # Validation
    print("\n" + "=" * 60)
    print("✅ Validation")
    print("=" * 60)

    missing = []
    for filename in msix_assets.keys():
        asset_path = assets_dir / filename
        if not asset_path.exists():
            missing.append(filename)

    if missing:
        print(f"\n❌ Missing {len(missing)} required assets:")
        for filename in missing:
            print(f"   - {filename}")
    else:
        print("\n✅ All required MSIX package assets generated successfully!")

    # Check store icon
    store_icon_path = assets_dir / "StoreIcon_1024x1024.png"
    if store_icon_path.exists():
        print("✅ Store icon (1024x1024) generated successfully!")
    else:
        print("❌ Store icon missing")

    # Summary
    print("\n" + "=" * 60)
    print("📋 Next Steps")
    print("=" * 60)

    print("\n1. Review generated assets in: msix/Assets/")
    print("2. Upload StoreIcon_1024x1024.png to Partner Center")
    print("3. Take 3-5 screenshots of the app (1920x1080)")
    print("   Save them in: msix/Screenshots/")
    print("4. Update msix/AppxManifest.xml with your Publisher ID")
    print('5. Run: .\\msix\\build_msix.ps1 -Version "0.1.0.0"')
    print("\n📖 See msix/HUMAN_REQUIRED_STEPS.md for detailed instructions")

    print("\n" + "=" * 60)
    print("✨ Asset Generation Complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
