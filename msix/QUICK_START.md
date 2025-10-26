# Microsoft Store Submission - Quick Start Guide

**⏱️ Estimated Time: 2-3 hours (excluding Partner Center verification wait)**

## 🎯 Goal

Get Hoppy Whisper published on Microsoft Store.

## ✅ What's Already Done

All technical preparation is complete:
- MSIX package configuration ✅
- Build automation scripts ✅
- Privacy policy document ✅
- Store listing content (English + Chinese) ✅
- Comprehensive documentation (100+ pages) ✅

## 🚀 5-Step Quick Start

### Step 1: Generate Assets (5 minutes)

```powershell
# Install Pillow library
poetry run pip install Pillow

# Generate all PNG assets from ICO files
poetry run python msix\generate_assets.py
```

**Output:** 14+ PNG files in `msix/Assets/`

---

### Step 2: Take Screenshots (15 minutes)

Capture 3-5 screenshots at 1920x1080:

1. **Tray icon and menu** - Right-click tray icon
2. **Recording state** - Show "Listening" state
3. **Transcription result** - Show text in an app
4. **History palette** - Win+Shift+Y window
5. **Settings** - settings.json or settings UI

Save to: `msix/Screenshots/`

**Tool:** Windows Snip & Sketch (Win+Shift+S)

---

### Step 3: Setup Partner Center (10 min + 24-48hr wait)

1. Go to: https://partner.microsoft.com/dashboard/registration
2. Sign in with Microsoft account
3. Choose: **Individual** ($19) or **Company** ($99)
4. Pay registration fee
5. Wait for verification email (24-48 hours)
6. Log in → Account Settings → Identity Details
7. Copy **Publisher ID**: `CN=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`

---

### Step 4: Build MSIX Package (15 minutes)

```powershell
# 1. Update Publisher ID in AppxManifest.xml (line 11)
# Replace: Publisher="CN=YOUR_PUBLISHER_CN"
# With: Publisher="CN=YOUR_ACTUAL_ID_FROM_STEP_3"

# 2. Build MSIX
.\msix\build_msix.ps1 -Version "0.1.0.0"

# 3. Run WACK test
& "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" test -appxpackagepath "dist_msix\HoppyWhisper_0.1.0.0.msix"
```

**Expected:** All tests pass except signing (that's OK).

---

### Step 5: Submit to Store (60 minutes)

#### A. Host Privacy Policy (5 minutes)
- Go to your GitHub repo settings
- Enable GitHub Pages: Settings → Pages → Deploy from branch: `master`
- Access at: `https://YOUR_USERNAME.github.io/Hoppy-Whisper/PRIVACY_POLICY.html`
- Wait 2 minutes for deployment

#### B. Create Submission in Partner Center (55 minutes)

1. **Reserve App Name**
   - Partner Center → Apps and games → New product → MSIX app
   - Name: "Hoppy Whisper"

2. **Start Submission**
   - Click app name → Start your submission

3. **Properties**
   - Category: Productivity
   - System Requirements: Copy from STORE_SUBMISSION_GUIDE.md
   - No personal data collection: ✓

4. **Age Rating (IARC)** - **CRITICAL**
   - Click "Get rating"
   - Answer questionnaire (see STORE_SUBMISSION_GUIDE.md for answers)
   - Expected: Everyone / PEGI 3

5. **Store Listing (English)**
   - App name: Hoppy Whisper
   - Description: Copy from `msix/STORE_LISTING_CONTENT.md`
   - Short description: Copy from same file
   - Keywords: `speech to text, transcription, voice typing, dictation, accessibility, offline, productivity`
   - Screenshots: Upload 3-5 from `msix/Screenshots/`
   - App icon: Upload `msix/Assets/StoreIcon_1024x1024.png`
   - Privacy policy URL: Your GitHub Pages URL
   - Support: https://github.com/YOUR_USERNAME/Hoppy-Whisper/issues
   - Website: https://github.com/YOUR_USERNAME/Hoppy-Whisper

6. **Store Listing (Chinese)** - Optional
   - Add language → Chinese (Simplified)
   - Copy from `msix/STORE_LISTING_CONTENT_ZH_CN.md`

7. **Packages**
   - Upload: `dist_msix\HoppyWhisper_0.1.0.0.msix`
   - Wait for validation (2-5 minutes)

8. **Availability**
   - Markets: Select all (worldwide)
   - Pricing: Free
   - Release: As soon as possible

9. **Review & Submit**
   - Click "Review your submission"
   - Verify all sections have green checkmarks
   - Click "Submit to the Store"

---

## ⏰ Timeline

| Task | Time |
|------|------|
| Generate assets | 5 min |
| Take screenshots | 15 min |
| Register Partner Center | 10 min |
| **Wait for verification** | **24-48 hours** |
| Host privacy policy | 5 min |
| Update Publisher ID | 2 min |
| Build MSIX | 10 min |
| Run WACK test | 15 min |
| Create submission | 60 min |
| **Total active time** | **~2 hours** |
| **Wait for certification** | **24-48 hours** |
| **Total calendar time** | **2-4 days** |

---

## 📋 Checklist

Print this and check off as you go:

```
☐ 1. Run: poetry run pip install Pillow
☐ 2. Run: poetry run python msix\generate_assets.py
☐ 3. Verify: msix/Assets/ has 14+ PNG files
☐ 4. Take 3-5 app screenshots (1920x1080)
☐ 5. Save screenshots to: msix/Screenshots/
☐ 6. Register Partner Center account ($19 or $99)
☐ 7. Wait for verification email (24-48 hours)
☐ 8. Log in and copy Publisher ID from Identity Details
☐ 9. Update msix/AppxManifest.xml line 11 with Publisher ID
☐ 10. Enable GitHub Pages in repository settings
☐ 11. Verify privacy policy accessible at GitHub Pages URL
☐ 12. Run: .\msix\build_msix.ps1 -Version "0.1.0.0"
☐ 13. Run WACK test on MSIX package
☐ 14. Fix any WACK failures (signing failure is OK)
☐ 15. Log in to Partner Center
☐ 16. Reserve app name "Hoppy Whisper"
☐ 17. Start new submission
☐ 18. Fill Properties section
☐ 19. Complete IARC age rating (CRITICAL)
☐ 20. Create English store listing (copy from docs)
☐ 21. (Optional) Add Chinese listing
☐ 22. Upload screenshots
☐ 23. Upload 1024x1024 app icon
☐ 24. Add privacy policy URL
☐ 25. Upload MSIX package
☐ 26. Set availability (worldwide, free)
☐ 27. Review submission for errors
☐ 28. Submit to Store
☐ 29. Wait for certification (24-48 hours)
☐ 30. Check email for approval/rejection
```

---

## 🆘 Troubleshooting

### Assets Won't Generate
```powershell
# Install Pillow if missing
poetry run pip install Pillow

# Check ICO file exists
Test-Path "icos\BunnyStandby.ico"
```

### WACK Test Fails
- **Manifest errors:** Check AppxManifest.xml syntax
- **Missing assets:** Run generate_assets.py again
- **Signing fails:** OK for Store submission (Microsoft signs it)
- **Other failures:** See MSIX_BUILD_GUIDE.md troubleshooting

### Privacy Policy Not Accessible
- Wait 2-5 minutes after enabling GitHub Pages
- Check URL in incognito browser
- Ensure repository is public
- Verify Pages enabled: Settings → Pages

### Partner Center Submission Errors
- **IARC incomplete:** Must complete entire questionnaire
- **Privacy URL invalid:** Test in browser, must be HTTPS
- **Package validation fails:** Check Publisher ID matches
- **Screenshots wrong size:** Minimum 1366x768, recommended 1920x1080

---

## 📞 Need More Help?

### Detailed Guides
- **Complete checklist:** [HUMAN_REQUIRED_STEPS.md](HUMAN_REQUIRED_STEPS.md)
- **Build instructions:** [MSIX_BUILD_GUIDE.md](MSIX_BUILD_GUIDE.md)
- **Submission walkthrough:** [STORE_SUBMISSION_GUIDE.md](STORE_SUBMISSION_GUIDE.md)
- **Asset specs:** [ASSETS_REQUIREMENTS.md](ASSETS_REQUIREMENTS.md)

### Support
- [Partner Center Support](https://partner.microsoft.com/support)
- [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/topics/windows-store.html)
- [GitHub Issues](https://github.com/YOUR_USERNAME/Hoppy-Whisper/issues)

---

## ✨ Tips for Success

1. ✅ **Run asset generator first** - See if output looks good before submission
2. ✅ **Test MSIX locally** - Install with `Add-AppxPackage` to catch issues
3. ✅ **Complete IARC carefully** - Cannot submit without this
4. ✅ **Use GitHub Pages** - Free, reliable privacy policy hosting
5. ✅ **Save WACK report** - Evidence of pre-submission testing
6. ✅ **Double-check Publisher ID** - Most common submission error
7. ✅ **Schedule buffer time** - Allow 3-4 days total before deadlines

---

## 🎉 After Approval

When your app is approved (usually 24-48 hours):

1. **Update README** with Store badge:
```markdown
<a href="https://www.microsoft.com/store/apps/{AppID}">
  <img src="https://get.microsoft.com/images/en-us%20dark.svg" width="200"/>
</a>
```

2. **Announce release** on GitHub

3. **Monitor reviews** in Partner Center

4. **Plan updates** - Increment version, rebuild MSIX, create new submission

---

**Ready? Start with Step 1: Generate Assets! 🚀**
