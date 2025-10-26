# Microsoft Store Asset Requirements

This document specifies all required visual assets for Microsoft Store submission.

## Required Image Assets

All images must be PNG format with transparency support where applicable.

### 1. Application Icons (Required)

Place these in `msix/Assets/` directory:

#### Square Tiles
- **Square44x44Logo.png** - 44x44 pixels (App list icon)
- **Square44x44Logo.scale-200.png** - 88x88 pixels (High DPI)
- **Square150x150Logo.png** - 150x150 pixels (Medium tile)
- **Square150x150Logo.scale-200.png** - 300x300 pixels (High DPI)
- **Square310x310Logo.png** - 310x310 pixels (Large tile)
- **Square310x310Logo.scale-200.png** - 620x620 pixels (High DPI)

#### Wide Tile
- **Wide310x150Logo.png** - 310x150 pixels (Wide tile)
- **Wide310x150Logo.scale-200.png** - 620x300 pixels (High DPI)

#### Small Tile
- **SmallTile.png** - 71x71 pixels (Small tile)
- **SmallTile.scale-200.png** - 142x142 pixels (High DPI)

#### Store Logo
- **StoreLogo.png** - 50x50 pixels (Package display logo)
- **StoreLogo.scale-200.png** - 100x100 pixels (High DPI)

#### Splash Screen
- **SplashScreen.png** - 620x300 pixels (Launch splash screen)
- **SplashScreen.scale-200.png** - 1240x600 pixels (High DPI)

### 2. Store Listing Images (Required for Submission)

Upload these in Partner Center during submission:

#### Screenshots (At least 1, up to 10 required)
- **Minimum resolution:** 1366x768 pixels
- **Recommended resolution:** 1920x1080 pixels or higher
- **Aspect ratio:** 16:9 or 16:10 preferred
- **Format:** PNG or JPEG
- **Content:** Show actual app functionality, not marketing materials

Recommended screenshots to include:
1. Main tray icon and menu
2. Settings configuration screen
3. Transcription in progress (with "Listening" state)
4. History palette with search functionality
5. Notification showing transcription complete
6. Example of transcription being pasted into an app

#### Store Logos
- **1:1 App icon (Required):**
  - 300x300 pixels minimum
  - 1024x1024 pixels recommended
  - PNG with transparency
  - Should match your app's brand identity

- **Optional additional sizes:**
  - 150x150 pixels
  - 71x71 pixels
  - 50x50 pixels

#### Hero Image (Optional but Recommended)
- **1920x1080 pixels**
- PNG or JPEG
- Used in Store search results and featured listings
- Should be eye-catching and represent the app's purpose

#### Promotional Images (Optional)
- **2400x1200 pixels** - For featured promotions
- **1000x800 pixels** - For Store collections
- PNG or JPEG

### 3. Design Guidelines

#### Color & Branding
- **Primary color:** Use consistent branding colors
- **Background:** Transparent where appropriate for tiles
- **Contrast:** Ensure icons work on both light and dark themes
- **Style:** Modern, clean, professional appearance

#### Icon Design Tips
- Use the bunny character from your existing icons (BunnyStandby.ico)
- Keep icons simple and recognizable at small sizes
- Avoid text in icons (except for 310x310 large tile if necessary)
- Use solid colors or subtle gradients
- Maintain consistency across all sizes

#### Screenshot Guidelines
- Use clean, professional-looking captures
- Annotate screenshots with arrows/labels if needed
- Show diverse use cases
- Ensure UI text is readable
- Remove any sensitive/personal information
- Use high-contrast, accessible designs

## Asset Creation Workflow

### Option 1: Convert Existing ICO Files

Your existing icons in `icos/` can be converted:

```powershell
# Extract PNG from ICO using ImageMagick or online converter
convert BunnyStandby.ico[0] Square150x150Logo.png

# Or use Python with Pillow
python -c "from PIL import Image; img = Image.open('icos/BunnyStandby.ico'); img.save('msix/Assets/Square150x150Logo.png')"
```

### Option 2: Use Design Tools

Recommended tools:
- **Adobe Photoshop/Illustrator** - Professional design
- **Figma** - Free, web-based design tool
- **Inkscape** - Free vector graphics editor
- **GIMP** - Free raster graphics editor
- **Canva** - Simple online design tool

### Option 3: Hire a Designer

If you need professional assets, consider:
- Upwork or Fiverr graphic designers
- Microsoft Store asset design services
- Local design agencies

## Asset Validation

Before submission, validate your assets:

1. **Use the Asset Generator Tool:**
   - [PWA Builder Image Generator](https://www.pwabuilder.com/imageGenerator)
   - Upload your base 1024x1024 icon
   - Generate all required sizes

2. **Check with Windows App Certification Kit:**
   ```powershell
   & "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" test -appxpackagepath "path\to\package.msix"
   ```

3. **Manual Validation Checklist:**
   - [ ] All required sizes present
   - [ ] PNG format with correct dimensions
   - [ ] Transparency works correctly
   - [ ] Icons visible on both light/dark backgrounds
   - [ ] No pixelation or artifacts
   - [ ] Consistent branding across sizes
   - [ ] Screenshots show actual app functionality
   - [ ] No sensitive information in screenshots

## Asset File Structure

Your final `msix/Assets/` directory should look like:

```
msix/
├── Assets/
│   ├── Square44x44Logo.png
│   ├── Square44x44Logo.scale-200.png
│   ├── Square150x150Logo.png
│   ├── Square150x150Logo.scale-200.png
│   ├── Square310x310Logo.png
│   ├── Square310x310Logo.scale-200.png
│   ├── Wide310x150Logo.png
│   ├── Wide310x150Logo.scale-200.png
│   ├── SmallTile.png
│   ├── SmallTile.scale-200.png
│   ├── StoreLogo.png
│   ├── StoreLogo.scale-200.png
│   ├── SplashScreen.png
│   └── SplashScreen.scale-200.png
└── AppxManifest.xml
```

## Next Steps

1. **Create or convert all required assets** using the existing bunny icons
2. **Place assets in `msix/Assets/` directory**
3. **Take 3-5 high-quality screenshots** of the app in action
4. **Prepare Store listing images** (1024x1024 icon minimum)
5. **Validate all assets** using the checklist above
6. **Test MSIX package** with Windows App Certification Kit

## References

- [Microsoft Store App Screenshots](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/screenshots-and-images)
- [MSIX Asset Guidelines](https://learn.microsoft.com/en-us/windows/apps/design/style/iconography/app-icon-design)
- [Visual Assets for Windows Apps](https://learn.microsoft.com/en-us/windows/apps/design/style/app-icons-and-logos)
