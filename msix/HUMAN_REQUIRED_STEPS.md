# Human-Required Steps for Microsoft Store Submission

## ✅ What's Already Done (Automated Preparation)

The following files and configurations have been created for you:

### 📦 MSIX Packaging
- ✅ `msix/AppxManifest.xml` - MSIX package manifest
- ✅ `msix/priconfig.xml` - Resource index configuration
- ✅ `msix/build_msix.ps1` - Automated build script
- ✅ `msix/MSIX_BUILD_GUIDE.md` - Comprehensive build documentation

### 📄 Documentation
- ✅ `PRIVACY_POLICY.md` - Complete privacy policy
- ✅ `msix/ASSETS_REQUIREMENTS.md` - Detailed asset specifications
- ✅ `msix/STORE_SUBMISSION_GUIDE.md` - Step-by-step submission guide
- ✅ `msix/STORE_LISTING_CONTENT.md` - English store listing
- ✅ `msix/STORE_LISTING_CONTENT_ZH_CN.md` - Chinese store listing

---

## 🔴 CRITICAL: Human Actions Required

These tasks **MUST** be completed by a human before submission:

### 1. 🎨 Create Visual Assets (HIGH PRIORITY)

**Status:** ❌ Not Done

**What you need:**
Create PNG image assets from your existing .ico files in the `icos/` directory.

**Required assets** (place in `msix/Assets/`):

#### Minimum Required Set
- `Square44x44Logo.png` - 44x44 pixels
- `Square44x44Logo.scale-200.png` - 88x88 pixels
- `Square150x150Logo.png` - 150x150 pixels
- `Square150x150Logo.scale-200.png` - 300x300 pixels
- `Wide310x150Logo.png` - 310x150 pixels
- `Wide310x150Logo.scale-200.png` - 620x300 pixels
- `SmallTile.png` - 71x71 pixels
- `SmallTile.scale-200.png` - 142x142 pixels
- `StoreLogo.png` - 50x50 pixels
- `StoreLogo.scale-200.png` - 100x100 pixels
- `SplashScreen.png` - 620x300 pixels
- `SplashScreen.scale-200.png` - 1240x600 pixels
- `Square310x310Logo.png` - 310x310 pixels (optional but recommended)
- `Square310x310Logo.scale-200.png` - 620x620 pixels (optional but recommended)

**How to create:**

Option A: Use Python script (quick method)
```powershell
# Install Pillow if not already installed
poetry run pip install Pillow

# Run this Python script to convert icons
poetry run python -c "
from PIL import Image
import os

ico_path = 'icos/BunnyStandby.ico'
assets_dir = 'msix/Assets'
os.makedirs(assets_dir, exist_ok=True)

img = Image.open(ico_path)

sizes = {
    'Square44x44Logo.png': (44, 44),
    'Square44x44Logo.scale-200.png': (88, 88),
    'Square150x150Logo.png': (150, 150),
    'Square150x150Logo.scale-200.png': (300, 300),
    'Wide310x150Logo.png': (310, 150),
    'Wide310x150Logo.scale-200.png': (620, 300),
    'SmallTile.png': (71, 71),
    'SmallTile.scale-200.png': (142, 142),
    'StoreLogo.png': (50, 50),
    'StoreLogo.scale-200.png': (100, 100),
    'SplashScreen.png': (620, 300),
    'SplashScreen.scale-200.png': (1240, 600),
    'Square310x310Logo.png': (310, 310),
    'Square310x310Logo.scale-200.png': (620, 620),
}

for filename, size in sizes.items():
    resized = img.resize(size, Image.Resampling.LANCZOS)
    output_path = os.path.join(assets_dir, filename)
    resized.save(output_path, 'PNG')
    print(f'Created: {output_path}')

print('All assets created successfully!')
"
```

Option B: Use online tool
1. Go to https://www.pwabuilder.com/imageGenerator
2. Upload `icos/BunnyStandby.ico` (convert to PNG first if needed)
3. Select "Windows" platform
4. Download generated assets
5. Copy to `msix/Assets/` directory

Option C: Manual design
1. Open `icos/BunnyStandby.ico` in image editor (Photoshop, GIMP, etc.)
2. Export each required size as PNG
3. Ensure transparency is preserved
4. Save to `msix/Assets/` directory

**Validation:**
```powershell
# Check if all required assets exist
$required = @(
    'Square44x44Logo.png', 'Square44x44Logo.scale-200.png',
    'Square150x150Logo.png', 'Square150x150Logo.scale-200.png',
    'Wide310x150Logo.png', 'Wide310x150Logo.scale-200.png',
    'SmallTile.png', 'SmallTile.scale-200.png',
    'StoreLogo.png', 'StoreLogo.scale-200.png',
    'SplashScreen.png', 'SplashScreen.scale-200.png'
)

$missing = @()
foreach ($asset in $required) {
    if (-not (Test-Path "msix\Assets\$asset")) {
        $missing += $asset
    }
}

if ($missing.Count -eq 0) {
    Write-Host "✅ All required assets present!" -ForegroundColor Green
} else {
    Write-Host "❌ Missing assets:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "  - $_" -ForegroundColor Yellow }
}
```

**Time estimate:** 30-60 minutes

---

### 2. 📸 Take Application Screenshots (HIGH PRIORITY)

**Status:** ❌ Not Done

**What you need:**
Capture 3-5 high-quality screenshots of the app in action.

**Requirements:**
- Resolution: 1920x1080 pixels (or higher)
- Format: PNG or JPEG
- No sensitive/personal information visible
- Show actual app functionality

**Recommended screenshots:**

1. **Tray Icon and Menu**
   - Show Hoppy Whisper icon in system tray
   - Right-click menu expanded
   - Caption: "Hoppy Whisper lives in your system tray - always ready, never intrusive"

2. **Recording State**
   - Show notification or tray icon in "Listening" state
   - Caption: "Press and hold your hotkey to start recording - simple and intuitive"

3. **Transcription Result**
   - Show transcribed text in an application (e.g., Notepad, Word)
   - Caption: "Release to transcribe in under 1 second - lightning fast results"

4. **History Palette** (Win+Shift+Y)
   - Show history search window with sample transcriptions
   - Caption: "Search and reuse past transcriptions with Win+Shift+Y"

5. **Settings File** (optional)
   - Show settings.json or settings location
   - Caption: "Customize hotkeys, paste delay, and startup behavior - make it yours"

**How to capture:**
1. Build and install the app locally
2. Use Windows Snipping Tool or Snip & Sketch (Win+Shift+S)
3. Capture screenshots at 1920x1080 resolution
4. Save as PNG files: `screenshot1.png`, `screenshot2.png`, etc.
5. Store in `msix/Screenshots/` directory for later upload

**Time estimate:** 15-30 minutes

---

### 3. 🌐 Host Privacy Policy (HIGH PRIORITY)

**Status:** ❌ Not Done

**What you need:**
Upload `PRIVACY_POLICY.md` to a publicly accessible URL.

**Options:**

#### Option A: GitHub Pages (Recommended - Free)
1. Go to your repository settings
2. Enable GitHub Pages:
   - Settings → Pages
   - Source: Deploy from a branch
   - Branch: `master` (or `main`)
   - Folder: `/` (root)
3. Convert Markdown to HTML or just commit as-is (GitHub auto-converts)
4. Access at: `https://YOUR_USERNAME.github.io/Hoppy-Whisper/PRIVACY_POLICY.html`
5. Wait 2-5 minutes for deployment

#### Option B: Netlify/Vercel (Free)
1. Create account on Netlify (https://netlify.com) or Vercel (https://vercel.com)
2. Create new site from Git repository
3. Deploy automatically
4. Custom domain optional
5. URL: `https://your-site.netlify.app/PRIVACY_POLICY.html`

#### Option C: Your Own Website
1. Convert `PRIVACY_POLICY.md` to HTML
2. Upload to your web server
3. Ensure HTTPS enabled
4. URL: `https://yourdomain.com/privacy-policy`

**Validation:**
```powershell
# Test URL accessibility (replace with your actual URL)
$url = "https://YOUR_USERNAME.github.io/Hoppy-Whisper/PRIVACY_POLICY.html"
try {
    $response = Invoke-WebRequest -Uri $url -UseBasicParsing
    if ($response.StatusCode -eq 200) {
        Write-Host "✅ Privacy policy accessible!" -ForegroundColor Green
    }
} catch {
    Write-Host "❌ Privacy policy URL not accessible" -ForegroundColor Red
}
```

**Update AppxManifest.xml and submission:**
Once hosted, you'll provide this URL during Store submission (not in AppxManifest).

**Time estimate:** 10-20 minutes

---

### 4. 🏢 Register Microsoft Partner Center Account (HIGH PRIORITY)

**Status:** ❌ Not Done

**What you need:**
Create a developer account to submit apps to Microsoft Store.

**Steps:**
1. Go to https://partner.microsoft.com/dashboard/registration
2. Sign in with Microsoft account (or create one)
3. Choose account type:
   - **Individual** ($19 USD, faster verification)
   - **Company** ($99 USD, requires business documents)
4. Complete registration form
5. Pay registration fee
6. Wait for verification:
   - Individual: 24-48 hours
   - Company: 1-2 weeks

**After verification:**
1. Go to Partner Center Dashboard
2. Navigate to Account Settings → Identity Details
3. Copy your **Publisher ID**: `CN=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`
4. This will be used in the next step

**Time estimate:** 10-15 minutes (plus verification wait time)

---

### 5. 📝 Update AppxManifest with Publisher ID (HIGH PRIORITY)

**Status:** ⚠️ Partially Done (needs your Publisher ID)

**What you need:**
Replace the placeholder Publisher ID in `msix/AppxManifest.xml`.

**Current line (line 11):**
```xml
Publisher="CN=YOUR_PUBLISHER_CN"
```

**What to do:**
1. Get your Publisher ID from Partner Center (see step 4)
2. Open `msix/AppxManifest.xml`
3. Replace `CN=YOUR_PUBLISHER_CN` with your actual Publisher ID
4. Example:
```xml
Publisher="CN=A1B2C3D4-E5F6-7890-ABCD-EF1234567890"
```

**File location:** `D:\a\parakeet\parakeet\msix\AppxManifest.xml`

**Time estimate:** 2 minutes

---

### 6. 🏗️ Build MSIX Package (MEDIUM PRIORITY)

**Status:** ⚠️ Ready to run (requires steps 1 and 5 first)

**What you need:**
Run the build script to create the MSIX package.

**Prerequisites:**
- ✅ Assets created (step 1)
- ✅ Publisher ID updated (step 5)
- ✅ Windows 10 SDK installed

**Command:**
```powershell
.\msix\build_msix.ps1 -Version "0.1.0.0"
```

**What it does:**
1. Builds PyInstaller executable
2. Copies assets and manifest
3. Creates MSIX package
4. Validates package structure

**Output:** `dist_msix\HoppyWhisper_0.1.0.0.msix`

**Time estimate:** 5-10 minutes

---

### 7. 🧪 Run Windows App Certification Kit (MEDIUM PRIORITY)

**Status:** ❌ Not Done (requires step 6 first)

**What you need:**
Test the MSIX package with Microsoft's official certification tool.

**Prerequisites:**
- ✅ MSIX package built (step 6)
- ✅ Windows 10 SDK installed

**Command:**
```powershell
& "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" test -appxpackagepath "dist_msix\HoppyWhisper_0.1.0.0.msix"
```

**Or use GUI:**
1. Search "Windows App Cert Kit" in Start Menu
2. Select "Validate App Package"
3. Browse to MSIX file
4. Run tests (takes 10-15 minutes)

**Expected results:**
- ✅ Manifest compliance: PASS
- ✅ Supported APIs: PASS
- ✅ Package sanity: PASS
- ⚠️ Signing: FAIL (OK for Store submission, Microsoft will sign it)
- ✅ Performance: PASS

**If any tests fail (except signing):**
- Review error report
- Fix issues in code/manifest
- Rebuild MSIX
- Re-run WACK

**Time estimate:** 15-20 minutes

---

### 8. 📤 Create Partner Center Submission (HIGH PRIORITY)

**Status:** ❌ Not Done (requires Partner Center account)

**What you need:**
Create a new app submission in Partner Center.

**Steps:**

#### A. Reserve App Name
1. Log in to Partner Center
2. Go to **Apps and games** → **New product** → **MSIX or PWA app**
3. Reserve name: **"Hoppy Whisper"**
4. If taken, try: "Hoppy Whisper - Speech to Text" or similar

#### B. Start Submission
1. Click on your reserved app name
2. Click **Start your submission**

#### C. Fill Out Properties
1. **Category:** Productivity (primary), Utilities & tools (secondary)
2. **System Requirements:** Copy from `STORE_SUBMISSION_GUIDE.md`
3. **Product Declarations:** 
   - No personal data collection
   - Yes to accessibility
4. **Capabilities:** Auto-filled from manifest

#### D. Complete Age Rating (IARC)
1. Click **Get rating**
2. Answer questionnaire (see `STORE_SUBMISSION_GUIDE.md` for answers)
3. Expected rating: Everyone / PEGI 3
4. **CRITICAL:** Cannot submit without completing this

#### E. Create Store Listing (English)
1. **App name:** Hoppy Whisper
2. **Description:** Copy from `STORE_LISTING_CONTENT.md`
3. **Short description:** (255 chars max)
4. **Keywords:** (7 max) - Copy from listing file
5. **Screenshots:** Upload 3-5 PNG/JPEG files from step 2
6. **App icon:** Upload 1024x1024 PNG (create from BunnyStandby.ico)
7. **Privacy policy URL:** URL from step 3
8. **Support contact:** GitHub issues URL or email
9. **Website:** GitHub repository URL

#### F. Add Chinese Listing (Optional but Recommended)
1. Click **Add language** → Chinese (Simplified)
2. Copy content from `STORE_LISTING_CONTENT_ZH_CN.md`
3. Upload Chinese screenshots if available

#### G. Upload Package
1. Click **Packages** section
2. Upload `dist_msix\HoppyWhisper_0.1.0.0.msix`
3. Wait for validation (2-5 minutes)
4. Fix any errors and re-upload if needed

#### H. Set Availability
1. **Markets:** Select all (worldwide) or specific regions
2. **Pricing:** Free (recommended)
3. **Release date:** As soon as possible after approval

#### I. Review and Submit
1. Click **Review your submission**
2. Check all sections have green checkmarks
3. Click **Submit to the Store**
4. Wait for certification (24-48 hours typical)

**Time estimate:** 60-90 minutes (first time)

---

### 9. 📊 Monitor Certification Status (LOW PRIORITY)

**Status:** ❌ Not Done (after step 8)

**What you need:**
Check Partner Center for certification status.

**Steps:**
1. Log in to Partner Center
2. Go to your app submission
3. Check status:
   - "In certification" - Review in progress
   - "Certification failed" - Check rejection report
   - "Pending publication" - Approved, going live soon
   - "In the Store" - Live!

**If certification fails:**
1. Read rejection report carefully
2. Fix identified issues
3. Create new submission
4. Upload updated package if needed
5. Re-submit

**Time estimate:** 5 minutes (checking status)

---

### 10. 🎉 Post-Publication Tasks (LOW PRIORITY)

**Status:** ❌ Not Done (after app is live)

**What you need:**
Update documentation and promote the app.

**Tasks:**

#### A. Update README.md
Add Microsoft Store badge:
```markdown
<a href="https://www.microsoft.com/store/apps/{AppID}">
  <img src="https://get.microsoft.com/images/en-us%20dark.svg" width="200"/>
</a>
```

#### B. Announce Release
- Create GitHub release with Store link
- Update repository description
- Post on social media (if applicable)
- Notify users/community

#### C. Monitor Feedback
- Check Partner Center → Reviews and ratings
- Respond to user reviews
- Address bugs and feature requests
- Plan future updates

#### D. Plan Updates
- Increment version number
- Build new MSIX
- Create update submission in Partner Center
- Submit for certification (faster than initial: 12-24 hours)

**Time estimate:** 30-60 minutes

---

## 📋 Priority Summary

### 🔴 MUST DO BEFORE SUBMISSION (Critical Path)

1. ✅ **Create Visual Assets** (step 1) - 30-60 min
2. ✅ **Register Partner Center Account** (step 4) - 10-15 min + wait
3. ✅ **Update Publisher ID** (step 5) - 2 min
4. ✅ **Host Privacy Policy** (step 3) - 10-20 min
5. ✅ **Take Screenshots** (step 2) - 15-30 min
6. ✅ **Build MSIX Package** (step 6) - 5-10 min
7. ✅ **Run WACK Test** (step 7) - 15-20 min
8. ✅ **Create Store Submission** (step 8) - 60-90 min

**Total estimated time:** 2.5-4 hours (excluding Partner Center verification wait time)

### 🟢 NICE TO HAVE (Optional)

- Add Chinese store listing (included in step 8)
- Create hero image for Store feature (optional)
- Set up GitHub Pages for documentation
- Prepare promotional materials

---

## 🚀 Quick Start Checklist

Use this checklist to track your progress:

```
☐ 1. Create all required PNG assets in msix/Assets/
☐ 2. Take 3-5 app screenshots
☐ 3. Host privacy policy at public URL
☐ 4. Register Microsoft Partner Center account
☐ 5. Get Publisher ID from Partner Center
☐ 6. Update msix/AppxManifest.xml with Publisher ID
☐ 7. Run: .\msix\build_msix.ps1 -Version "0.1.0.0"
☐ 8. Run WACK test on MSIX package
☐ 9. Fix any WACK failures (except signing)
☐ 10. Log in to Partner Center
☐ 11. Reserve app name "Hoppy Whisper"
☐ 12. Start new submission
☐ 13. Fill out Properties section
☐ 14. Complete IARC age rating questionnaire
☐ 15. Create English store listing
☐ 16. (Optional) Create Chinese store listing
☐ 17. Upload screenshots
☐ 18. Upload 1024x1024 app icon
☐ 19. Add privacy policy URL
☐ 20. Upload MSIX package
☐ 21. Set availability (worldwide, free)
☐ 22. Review submission
☐ 23. Submit to Store
☐ 24. Wait for certification (24-48 hours)
☐ 25. Check for certification results
☐ 26. If approved: Update README with Store link
☐ 27. If rejected: Fix issues and re-submit
```

---

## 📞 Need Help?

### Resources Created for You
- 📖 `msix/MSIX_BUILD_GUIDE.md` - Detailed build instructions
- 📖 `msix/STORE_SUBMISSION_GUIDE.md` - Step-by-step submission guide
- 📖 `msix/ASSETS_REQUIREMENTS.md` - Asset specifications
- 📖 `PRIVACY_POLICY.md` - Ready-to-host privacy policy
- 📖 `msix/STORE_LISTING_CONTENT.md` - English store content
- 📖 `msix/STORE_LISTING_CONTENT_ZH_CN.md` - Chinese store content

### Official Documentation
- [Microsoft Partner Center](https://partner.microsoft.com/dashboard)
- [App Submission Process](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/create-app-submission)
- [Windows App Certification Kit](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-app-certification-kit)

### Support Channels
- [Partner Center Support](https://partner.microsoft.com/support)
- [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/topics/windows-store.html)
- [Windows Dev Discord](https://discord.gg/windowsdev)

---

## ✨ Final Notes

All automated preparation work is complete. The files created follow Microsoft's best practices and Store policies. The remaining tasks require human judgment (design, screenshots, account setup) or official registration (Partner Center account).

**Estimated time to complete all required steps:** 2.5-4 hours (plus Partner Center account verification wait time of 24-48 hours).

**Good luck with your Microsoft Store submission!** 🚀
