# Microsoft Store Submission Package

This directory contains all files and documentation needed to prepare Hoppy Whisper for Microsoft Store submission.

## 📁 Directory Structure

```
msix/
├── AppxManifest.xml              # MSIX package manifest (update Publisher ID)
├── priconfig.xml                 # Resource index configuration
├── build_msix.ps1                # Automated MSIX build script
├── generate_assets.py            # Helper script to create assets from ICO files
├── Assets/                       # Visual assets (PNGs) - CREATE THESE FIRST
│   ├── Square44x44Logo.png
│   ├── Square150x150Logo.png
│   ├── StoreLogo.png
│   ├── SplashScreen.png
│   └── ... (see ASSETS_REQUIREMENTS.md)
├── Screenshots/                  # App screenshots for Store listing - CREATE THESE
│   ├── screenshot1.png
│   ├── screenshot2.png
│   └── ...
└── [Documentation files]
```

## 🚀 Quick Start

### Step 1: Generate Assets (5 minutes)

Run the asset generator to create all required PNG files:

```powershell
# Install Pillow if not already installed
poetry run pip install Pillow

# Generate all assets from existing ICO files
poetry run python msix\generate_assets.py
```

This creates all required PNG assets in `msix/Assets/` directory.

### Step 2: Take Screenshots (15 minutes)

Capture 3-5 screenshots of the app in action:
- Resolution: 1920x1080 (or higher)
- Format: PNG or JPEG
- Save to: `msix/Screenshots/`

See [HUMAN_REQUIRED_STEPS.md](HUMAN_REQUIRED_STEPS.md) for screenshot guidelines.

### Step 3: Register Partner Center Account (10 minutes + wait)

1. Go to https://partner.microsoft.com/dashboard/registration
2. Register as Individual ($19) or Company ($99)
3. Wait for verification (24-48 hours)
4. Get your Publisher ID from Account Settings → Identity Details

### Step 4: Update Publisher ID (1 minute)

Edit `msix/AppxManifest.xml` line 11:

```xml
<!-- Change this: -->
Publisher="CN=YOUR_PUBLISHER_CN"

<!-- To your actual ID: -->
Publisher="CN=A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
```

### Step 5: Build MSIX Package (10 minutes)

Run the build script:

```powershell
.\msix\build_msix.ps1 -Version "0.1.0.0"
```

Output: `dist_msix\HoppyWhisper_0.1.0.0.msix`

### Step 6: Run WACK Test (15 minutes)

Validate the package:

```powershell
& "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" test -appxpackagepath "dist_msix\HoppyWhisper_0.1.0.0.msix"
```

All tests should pass except signing (Microsoft will sign it).

### Step 7: Submit to Store (60-90 minutes)

Follow the detailed guide: [STORE_SUBMISSION_GUIDE.md](STORE_SUBMISSION_GUIDE.md)

## 📚 Documentation Files

### Essential Reading (Start Here)
- **[HUMAN_REQUIRED_STEPS.md](HUMAN_REQUIRED_STEPS.md)** - Complete checklist of human tasks
  - What's automated vs. what you need to do
  - Step-by-step instructions with time estimates
  - Priority ranking and critical path

### Technical Guides
- **[MSIX_BUILD_GUIDE.md](MSIX_BUILD_GUIDE.md)** - Building and testing MSIX packages
  - Prerequisites and setup
  - Build script usage
  - Troubleshooting common issues
  
- **[ASSETS_REQUIREMENTS.md](ASSETS_REQUIREMENTS.md)** - Visual asset specifications
  - Complete list of required images
  - Size and format requirements
  - Design guidelines

### Store Submission
- **[STORE_SUBMISSION_GUIDE.md](STORE_SUBMISSION_GUIDE.md)** - Complete submission process
  - Partner Center setup
  - Store listing creation
  - Age rating (IARC) questionnaire
  - Package upload and certification

- **[STORE_LISTING_CONTENT.md](STORE_LISTING_CONTENT.md)** - English store content
  - App description (ready to copy/paste)
  - Keywords and categories
  - Release notes

- **[STORE_LISTING_CONTENT_ZH_CN.md](STORE_LISTING_CONTENT_ZH_CN.md)** - Chinese store content
  - Localized descriptions
  - Translated keywords

### Legal
- **[../PRIVACY_POLICY.md](../PRIVACY_POLICY.md)** - Privacy policy (ready to host)
  - Complete privacy disclosure
  - GDPR/CCPA compliant
  - Must be hosted at public URL

## 🔴 Critical Requirements

Before submission, you MUST have:

- [ ] All PNG assets in `msix/Assets/` (run `generate_assets.py`)
- [ ] 3-5 screenshots in `msix/Screenshots/` (1920x1080)
- [ ] Privacy policy hosted at public URL (e.g., GitHub Pages)
- [ ] Microsoft Partner Center account registered
- [ ] Publisher ID updated in `AppxManifest.xml`
- [ ] MSIX package built and tested with WACK
- [ ] All WACK tests passed (except signing)

## ⏱️ Time Estimates

| Task | Time Required |
|------|---------------|
| Generate assets | 5 minutes |
| Take screenshots | 15-30 minutes |
| Register Partner Center | 10 minutes + 24-48hr wait |
| Update Publisher ID | 1 minute |
| Build MSIX | 5-10 minutes |
| Run WACK test | 15-20 minutes |
| Create Store submission | 60-90 minutes |
| **Total (excluding wait)** | **2-3 hours** |
| Certification review | 24-48 hours (Microsoft) |

## 🛠️ Helper Scripts

### Generate Assets
```powershell
poetry run python msix\generate_assets.py
```
Creates all required PNG assets from existing ICO files.

### Build MSIX
```powershell
.\msix\build_msix.ps1 -Version "0.1.0.0"
```
Builds complete MSIX package ready for submission.

### Validate Assets
```powershell
# Check if all required assets exist
$required = @(
    'Square44x44Logo.png', 'Square150x150Logo.png',
    'Wide310x150Logo.png', 'SmallTile.png',
    'StoreLogo.png', 'SplashScreen.png'
)

$missing = $required | Where-Object { -not (Test-Path "msix\Assets\$_") }

if ($missing.Count -eq 0) {
    Write-Host "✅ All required assets present!"
} else {
    Write-Host "❌ Missing: $($missing -join ', ')"
}
```

## 📞 Getting Help

### Questions About This Package?
Read the documentation files in this directory:
1. Start with `HUMAN_REQUIRED_STEPS.md` for overview
2. Refer to specific guides for detailed instructions
3. Check troubleshooting sections in each guide

### Microsoft Store Issues?
- [Partner Center Support](https://partner.microsoft.com/support)
- [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/topics/windows-store.html)
- [Official Documentation](https://learn.microsoft.com/en-us/windows/apps/publish/)

### Technical Issues?
- Check `MSIX_BUILD_GUIDE.md` troubleshooting section
- Review WACK test results for specific errors
- Verify Windows 10 SDK is installed correctly

## ✅ Success Checklist

Use this quick checklist to track your progress:

```
Pre-Submission:
☐ Assets generated (run generate_assets.py)
☐ Screenshots taken and saved
☐ Privacy policy hosted at public URL
☐ Partner Center account registered and verified
☐ Publisher ID copied from Partner Center
☐ AppxManifest.xml updated with Publisher ID
☐ MSIX package built successfully
☐ WACK test passed (all except signing)

Submission:
☐ Partner Center submission created
☐ App name reserved
☐ Properties section completed
☐ IARC age rating completed
☐ English store listing filled out
☐ (Optional) Chinese listing added
☐ Screenshots uploaded
☐ Store icon uploaded (1024x1024)
☐ Privacy policy URL added
☐ MSIX package uploaded
☐ Availability settings configured
☐ Submission reviewed and submitted

Post-Submission:
☐ Certification status monitored
☐ If rejected: issues fixed and re-submitted
☐ If approved: README updated with Store link
☐ Release announcement created
```

## 🎉 What's Automated?

All of these have been created for you:
- ✅ MSIX package manifest (AppxManifest.xml)
- ✅ Build automation script (build_msix.ps1)
- ✅ Asset generation script (generate_assets.py)
- ✅ Privacy policy document (PRIVACY_POLICY.md)
- ✅ Store listing content (English and Chinese)
- ✅ Complete documentation and guides
- ✅ Troubleshooting guides
- ✅ Validation scripts

You only need to:
1. Generate assets (run script)
2. Take screenshots (manual)
3. Register Partner Center (one-time)
4. Update Publisher ID (copy/paste)
5. Build and submit (follow guides)

**Total human work: 2-3 hours** (excluding Partner Center verification wait)

## 📖 Further Reading

- [Microsoft Store Policies](https://learn.microsoft.com/en-us/windows/apps/publish/store-policies)
- [MSIX Packaging](https://learn.microsoft.com/en-us/windows/msix/)
- [Windows App Certification Kit](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-app-certification-kit)
- [Age Rating (IARC)](https://www.globalratings.com/)

---

**Ready to submit?** Start with [HUMAN_REQUIRED_STEPS.md](HUMAN_REQUIRED_STEPS.md) for your complete checklist!
