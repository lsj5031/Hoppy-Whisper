# Microsoft Store Submission Guide

This comprehensive guide walks you through the entire Microsoft Store submission process for Hoppy Whisper.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Partner Center Account Setup](#partner-center-account-setup)
3. [Application Preparation](#application-preparation)
4. [Creating Store Listing](#creating-store-listing)
5. [Age Rating (IARC)](#age-rating-iarc)
6. [Package Upload](#package-upload)
7. [Submission and Review](#submission-and-review)
8. [Post-Publication](#post-publication)
9. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### 1. Microsoft Partner Center Account

**Required:** Developer account with Microsoft Partner Center

- **Individual Account:** $19 USD (one-time fee)
- **Company Account:** $99 USD (one-time fee)

**Registration:** https://partner.microsoft.com/dashboard/registration

**Verification Time:** 24-48 hours for individual, 1-2 weeks for company

### 2. Prepared MSIX Package

Build and test your MSIX package:

```powershell
.\msix\build_msix.ps1 -Version "0.1.0.0"
```

**Verify with WACK:**
```powershell
& "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" test -appxpackagepath "dist_msix\HoppyWhisper_0.1.0.0.msix"
```

### 3. Required Assets

All visual assets must be prepared (see [ASSETS_REQUIREMENTS.md](ASSETS_REQUIREMENTS.md)):

- [ ] App screenshots (at least 1, recommend 3-5)
- [ ] 1024x1024 app icon (PNG)
- [ ] MSIX package assets (all tile sizes)

### 4. Privacy Policy

Host your privacy policy at a publicly accessible URL:

- **Option 1:** GitHub Pages (free, recommended for open-source)
  - Upload `PRIVACY_POLICY.md` to repository
  - Enable GitHub Pages in repository settings
  - URL: `https://username.github.io/hoppy-whisper/PRIVACY_POLICY.html`

- **Option 2:** Your own website
  - Upload privacy policy to your domain
  - URL: `https://yourdomain.com/privacy-policy`

- **Option 3:** Free hosting services
  - Netlify, Vercel, or similar
  - Upload as static HTML

**CRITICAL:** Privacy policy URL is REQUIRED for Store submission.

### 5. Support Contact

Provide a support contact:
- **Email:** maintainers@hoppy.app (or your support email)
- **GitHub Issues:** https://github.com/YOUR_USERNAME/Hoppy-Whisper/issues
- **Website:** (optional)

---

## Partner Center Account Setup

### Step 1: Create Developer Account

1. Go to https://partner.microsoft.com/dashboard/registration
2. Sign in with Microsoft account (or create one)
3. Choose account type:
   - **Individual:** For solo developers or small projects
   - **Company:** For organizations (requires business verification)
4. Complete registration form:
   - Publisher display name (e.g., "Hoppy Whisper Contributors")
   - Contact information
   - Payment method for registration fee
5. Submit and wait for verification

### Step 2: Reserve App Name

1. Log in to Partner Center
2. Go to **Apps and games** → **New product** → **MSIX or PWA app**
3. Reserve name: **"Hoppy Whisper"**
4. If unavailable, try:
   - "Hoppy Whisper - Speech to Text"
   - "Hoppy Transcribe"
   - Check availability first

**Note:** Name reservation is free and lasts 3 months.

### Step 3: Verify Publisher Identity

In `AppxManifest.xml`, update the Publisher field:

1. Go to Partner Center → Account settings → Identity details
2. Copy your **Publisher ID** (format: `CN=XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX`)
3. Update `msix/AppxManifest.xml`:

```xml
<Identity Name="HoppyWhisper.HoppyWhisper"
          Publisher="CN=YOUR_ACTUAL_PUBLISHER_ID_HERE"
          Version="0.1.0.0" />
```

4. Rebuild MSIX package with correct Publisher ID

---

## Application Preparation

### Update Version Number

Ensure version in all files is consistent:

1. **pyproject.toml:**
```toml
version = "0.1.0"
```

2. **version_info.txt:**
```python
filevers=(0, 1, 0, 0),
prodvers=(0, 1, 0, 0),
```

3. **AppxManifest.xml:**
```xml
Version="0.1.0.0"
```

### Test MSIX Package Thoroughly

1. **Install locally:**
```powershell
Add-AppxPackage -Path "dist_msix\HoppyWhisper_0.1.0.0.msix"
```

2. **Launch and test:**
   - Tray icon appears
   - Hotkey works (Ctrl+Shift+;)
   - Audio capture functions
   - Transcription completes
   - History palette opens (Win+Shift+Y)
   - Settings persist across restarts

3. **Run WACK:**
```powershell
& "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" test -appxpackagepath "dist_msix\HoppyWhisper_0.1.0.0.msix"
```

**All tests must pass** (except signing, which is OK for Store submission).

4. **Clean uninstall:**
```powershell
Remove-AppxPackage -Package HoppyWhisper.HoppyWhisper_0.1.0.0_x64__{PublisherID}
```

Verify no leftover files or registry entries.

---

## Creating Store Listing

### Step 1: Start New Submission

1. Go to Partner Center → Apps and games → Hoppy Whisper
2. Click **Start your submission**

### Step 2: Properties

#### Category
- **Primary:** Productivity
- **Secondary:** Utilities & tools (optional)

#### System Requirements
- **Minimum OS:** Windows 10, version 1903 (Build 18362)
- **Recommended OS:** Windows 11
- **Processor:** x64 (64-bit)
- **Memory:** 2 GB RAM (minimum), 4 GB recommended
- **Graphics:** DirectX 12 compatible GPU (optional, for acceleration)
- **Storage:** 1 GB free space
- **Sound card:** Microphone required

#### Product Declarations
- [ ] This product accesses, collects, or transmits personal information
  - **Select:** No (all processing is local)
- [ ] This product has been tested to meet accessibility guidelines
  - **Select:** Yes (keyboard accessible, screen reader friendly)
- [ ] This product supports pen and ink input
  - **Select:** No

#### App capabilities (auto-filled from manifest)
- Internet client
- Microphone

### Step 3: Age Ratings (IARC)

**CRITICAL:** Complete IARC questionnaire. Cannot submit without this.

1. Click **Get rating**
2. Answer questionnaire honestly:

**Sample answers for Hoppy Whisper:**

- **Does your product contain violent content?** No
- **Does your product contain sexual content?** No
- **Does your product contain nudity?** No
- **Does your product contain content that depicts or encourages the use of drugs, alcohol, or tobacco?** No
- **Does your product contain content that depicts or encourages extreme or realistic violence?** No
- **Does your product contain profanity or crude humor?** No
- **Does your product allow users to communicate with each other?** No
- **Does your product allow users to share information?** Yes
  - *(Transcribed text via clipboard)*
  - **Is this sharing restricted?** Yes, user-initiated only
- **Does your product collect, disclose, or share location information?** No
- **Does your product contain user-generated content that is accessible to others?** No
- **Does your product allow users to purchase digital goods?** No
- **Does your product include advertisements?** No
- **Does your product access the internet?** Yes
  - **For what purpose?** Download AI models (one-time, initial setup)

**Expected Rating:** ESRB: Everyone, PEGI: 3+, USK: 0+

### Step 4: Store Listings

Create store listing content for each language (minimum: English).

#### English (United States)

**App Name:**
```
Hoppy Whisper
```

**Description:** (Maximum 10,000 characters)

See [STORE_LISTING_CONTENT.md](STORE_LISTING_CONTENT.md) for full description.

**Short Description:** (Maximum 255 characters)
```
Fast, offline speech-to-text transcription for Windows. Press a hotkey, speak, and get instant text in any app. Privacy-first, no cloud required.
```

**Keywords:** (Maximum 7, comma-separated)
```
speech to text, transcription, voice typing, dictation, accessibility, offline, productivity
```

**Screenshots:** (Upload 1-10, at least 1 required)
- Recommended: 1920x1080 PNG or JPEG
- Show actual app functionality
- Include captions if helpful

**Store Logos:**
- 1:1 Square icon: 300x300 minimum (upload 1024x1024 for best quality)

**Additional Information:**

**Publisher website:**
```
https://github.com/YOUR_USERNAME/Hoppy-Whisper
```

**Support contact:**
```
https://github.com/YOUR_USERNAME/Hoppy-Whisper/issues
```

**Privacy policy:**
```
https://your-hosted-url.com/PRIVACY_POLICY.html
```
*(REQUIRED - must be publicly accessible URL)*

**Copyright and trademark info:**
```
Copyright © 2025 Hoppy Whisper Contributors. Licensed under MIT License.
```

**Additional license terms:** (Optional)
```
This software is provided under the MIT License. See https://opensource.org/licenses/MIT for details.
```

**Features:**
- [ ] Accessible (meets accessibility guidelines)
- [ ] Desktop application
- [ ] Keyboard-focused
- [ ] Offline capable

#### Additional Languages (Recommended)

**Chinese (Simplified):**
- See [STORE_LISTING_CONTENT_ZH_CN.md](STORE_LISTING_CONTENT_ZH_CN.md)

Add translations for:
- App description
- Short description
- Keywords
- Screenshots with Chinese UI (if localized)

---

## Package Upload

### Step 1: Packages

1. Click **Packages** section in submission
2. Upload your MSIX file:
   - **File:** `dist_msix\HoppyWhisper_0.1.0.0.msix`
   - **Size:** Should be 80-150 MB (depending on bundled models)
3. Wait for validation (2-5 minutes)

**Common Validation Errors:**

- **Publisher mismatch:** Ensure Publisher in AppxManifest matches your Partner Center Publisher ID
- **Version conflict:** If you've submitted before, new version must be higher
- **Missing capabilities:** Ensure manifest declares all required capabilities

### Step 2: Availability

**Markets:**
- Select all markets (or specific regions)
- Recommended: Worldwide distribution

**Pricing:**
- **Free** (recommended for open-source)
- Or set a price (minimum $1.49)

**Release Date:**
- **As soon as possible** (after passing certification)
- Or schedule a specific date

### Step 3: Visibility

**Discoverability:**
- ✅ **Make this product available and discoverable in the Store**
  - Users can search and find your app
- Or: **Not discoverable** (direct link only, for limited releases)

**Acquisition:**
- ✅ **Allow acquisition**

---

## Submission and Review

### Step 1: Review Submission

1. Go through checklist:
   - [ ] Properties complete
   - [ ] Age rating complete (IARC)
   - [ ] Store listing filled out (all required fields)
   - [ ] Screenshots uploaded
   - [ ] Privacy policy URL provided
   - [ ] Package uploaded and validated
   - [ ] Availability set
   - [ ] Pricing set

2. Click **Review your submission**

3. Check for any warnings or errors

### Step 2: Submit for Certification

1. Click **Submit to the Store**
2. Confirmation message appears
3. Status changes to **In certification**

**Review Timeline:**
- **Automated checks:** 1-2 hours
- **Manual review:** 24-48 hours (typical)
- **Total time:** Usually 1-3 days

### Step 3: Monitor Certification Status

Check status in Partner Center:
- **In certification** - Review in progress
- **Certification failed** - Review rejection report
- **Pending publication** - Approved, waiting to go live
- **In the Store** - Live and available

**Email Notifications:**
- You'll receive emails at key stages
- Enable notifications in Partner Center settings

---

## Certification Failure (If It Happens)

### Common Rejection Reasons

#### 1. Missing Privacy Policy
**Error:** "Privacy policy URL is invalid or inaccessible"

**Fix:**
- Verify URL is publicly accessible
- Ensure it's not localhost or private IP
- Test URL in incognito browser
- Re-submit with corrected URL

#### 2. App Crashes on Launch
**Error:** "Application failed to launch during testing"

**Fix:**
- Test MSIX on clean Windows 10/11 VM
- Check WACK test results
- Review Event Viewer logs
- Ensure all dependencies are bundled
- Re-build with console mode for debugging

#### 3. Missing Required Assets
**Error:** "App icons are missing or incorrect size"

**Fix:**
- Verify all assets in `msix/Assets/` directory
- Check AppxManifest references match actual files
- Re-build MSIX package
- Re-run WACK test

#### 4. Inappropriate Content
**Error:** "App content violates Store policies"

**Fix:**
- Review Store policy: https://learn.microsoft.com/en-us/windows/apps/publish/store-policies
- Remove any inappropriate content
- Update screenshots if needed
- Adjust age rating if necessary

### Re-submission Process

1. Fix issues identified in rejection report
2. Create new submission (previous one is saved as draft)
3. Upload updated package if needed
4. Click **Submit to the Store** again
5. Average re-review time: 12-24 hours

---

## Post-Publication

### Step 1: Verify Live Listing

1. Search Microsoft Store for "Hoppy Whisper"
2. Verify:
   - App name correct
   - Screenshots display properly
   - Description readable
   - Download button works

**Store URL:** `https://www.microsoft.com/store/apps/{AppID}`
- Find AppID in Partner Center

### Step 2: Update README

Add Store badge to README.md:

```markdown
## Download

<a href="https://www.microsoft.com/store/apps/{AppID}">
  <img src="https://get.microsoft.com/images/en-us%20dark.svg" width="200"/>
</a>
```

### Step 3: Monitor Reviews

- Check Partner Center → Reviews and ratings
- Respond to user feedback
- Address bugs and feature requests
- Plan updates based on feedback

### Step 4: Update Process

For future updates:

1. Increment version in all files
2. Build new MSIX package
3. Test thoroughly with WACK
4. Create new submission in Partner Center
5. Upload new package
6. Submit for certification

**Update Review:** Usually faster than initial submission (12-24 hours).

---

## Troubleshooting

### Package Upload Fails

**Issue:** "Package validation failed"

**Solutions:**
- Run WACK locally first
- Check Publisher ID matches Partner Center
- Verify version is higher than previous submissions
- Ensure package is MSIX format (not EXE or ZIP)
- Check file size < 2 GB

### Privacy Policy URL Rejected

**Issue:** "Privacy policy URL cannot be accessed"

**Solutions:**
- Test URL in incognito browser window
- Ensure it's HTTPS (HTTP may be rejected)
- Host on reliable service (GitHub Pages, Netlify, etc.)
- Verify no login/authentication required
- Check page loads in < 5 seconds

### Age Rating Issues

**Issue:** "IARC rating incomplete"

**Solutions:**
- Complete entire questionnaire (all questions)
- Wait 5-10 minutes for rating to process
- Refresh Partner Center page
- Contact IARC support if persistent: https://www.globalratings.com/contact.aspx

### Store Listing Not Displaying Correctly

**Issue:** Screenshots or icons appear pixelated/wrong

**Solutions:**
- Re-upload assets in correct format (PNG preferred)
- Ensure minimum resolutions met (see ASSETS_REQUIREMENTS.md)
- Clear browser cache and check again
- Wait 24 hours for CDN propagation

### App Not Appearing in Search

**Issue:** Can't find app in Store search

**Solutions:**
- Wait 24-48 hours after publication (indexing delay)
- Search exact app name
- Check availability settings (not set to "Not discoverable")
- Verify market includes your region

---

## Checklist for Submission

Before clicking **Submit to the Store**, verify:

### Technical
- [ ] MSIX package built and tested locally
- [ ] WACK test passed (all except signing)
- [ ] Publisher ID in AppxManifest matches Partner Center
- [ ] Version number is unique and incremented
- [ ] All required assets included in package
- [ ] App tested on clean Windows 10 and 11 VMs

### Content
- [ ] App name reserved in Partner Center
- [ ] Store listing description written (English + translations)
- [ ] Short description under 255 characters
- [ ] Keywords selected (max 7)
- [ ] 3-5 screenshots uploaded (1920x1080 recommended)
- [ ] 1024x1024 app icon uploaded
- [ ] Privacy policy hosted at public URL
- [ ] Support contact information provided
- [ ] IARC age rating completed

### Legal
- [ ] Developer account verified
- [ ] Copyright information accurate
- [ ] License terms specified (MIT)
- [ ] No trademark infringement
- [ ] App complies with Store policies

### Testing
- [ ] App launches successfully
- [ ] All features work as described
- [ ] No crashes or errors
- [ ] Microphone permission granted correctly
- [ ] Clean uninstall leaves no artifacts

---

## Resources

### Official Microsoft Documentation
- [Partner Center Dashboard](https://partner.microsoft.com/dashboard)
- [App submission process](https://learn.microsoft.com/en-us/windows/apps/publish/publish-your-app/msix/create-app-submission)
- [Store policies](https://learn.microsoft.com/en-us/windows/apps/publish/store-policies)
- [Age ratings (IARC)](https://www.globalratings.com/)

### Tools
- [Windows App Certification Kit (WACK)](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-app-certification-kit)
- [MSIX Packaging Tool](https://learn.microsoft.com/en-us/windows/msix/packaging-tool/tool-overview)
- [Asset Generator](https://www.pwabuilder.com/imageGenerator)

### Support
- [Partner Center Support](https://partner.microsoft.com/support)
- [Microsoft Q&A](https://learn.microsoft.com/en-us/answers/topics/windows-store.html)
- [Windows Dev Community Discord](https://discord.gg/windowsdev)

---

## Summary

**The submission process at a glance:**

1. ✅ **Prepare** - Build MSIX, test with WACK, create assets
2. ✅ **Account** - Register Partner Center, reserve name
3. ✅ **List** - Fill out store listing, upload screenshots
4. ✅ **Rate** - Complete IARC age rating questionnaire
5. ✅ **Upload** - Upload MSIX package
6. ✅ **Submit** - Review and submit for certification
7. ✅ **Wait** - 1-3 days for review
8. ✅ **Publish** - Go live in Microsoft Store!

**Average time from start to publication:** 3-7 days (including account setup).

**Good luck with your submission!** 🚀
