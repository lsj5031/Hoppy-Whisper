# MSIX Package Build Guide

This guide explains how to build and test the MSIX package for Microsoft Store submission.

## Prerequisites

### 1. Windows 10 SDK

Download and install from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/

Required tools:
- `makeappx.exe` - Creates MSIX packages
- `signtool.exe` - Signs packages (for local testing)
- `makepri.exe` - Creates resource indexes

Typical installation path:
```
C:\Program Files (x86)\Windows Kits\10\bin\{version}\x64\
```

### 2. PyInstaller Executable

Build the executable first:
```powershell
poetry install --with dev
poetry run pyinstaller --noconfirm --clean HoppyWhisper_onefile.spec
```

Output: `dist\Hoppy Whisper-CPU.exe`

### 3. MSIX Assets

Create and place all required PNG assets in `msix\Assets\` directory.

See [ASSETS_REQUIREMENTS.md](ASSETS_REQUIREMENTS.md) for complete list.

Minimum required assets:
- Square44x44Logo.png (44x44)
- Square150x150Logo.png (150x150)
- StoreLogo.png (50x50)
- SplashScreen.png (620x300)

## Building the MSIX Package

### Quick Build (Default)

Build everything from scratch:

```powershell
.\msix\build_msix.ps1
```

This will:
1. Build PyInstaller executable
2. Prepare packaging directory
3. Generate resource index
4. Create unsigned MSIX package
5. Validate package structure

Output: `dist_msix\HoppyWhisper_0.1.0.0.msix`

### Custom Version

Specify a different version:

```powershell
.\msix\build_msix.ps1 -Version "1.2.3.0"
```

Version format: `Major.Minor.Build.Revision` (e.g., `1.0.0.0`)

### Skip PyInstaller Build

If executable already exists:

```powershell
.\msix\build_msix.ps1 -NoBuild
```

### Sign Package (for Local Testing)

To test the package locally, you need to sign it:

```powershell
# Create a test certificate (one-time setup)
New-SelfSignedCertificate -Type CodeSigningCert -Subject "CN=Hoppy Whisper Test" -CertStoreLocation Cert:\CurrentUser\My

# Export certificate (replace thumbprint)
$cert = Get-ChildItem Cert:\CurrentUser\My\{THUMBPRINT}
Export-PfxCertificate -Cert $cert -FilePath "TestCert.pfx" -Password (ConvertTo-SecureString -String "testpassword" -Force -AsPlainText)

# Build and sign
.\msix\build_msix.ps1 -Sign -CertPath "TestCert.pfx" -CertPassword "testpassword"
```

**Note:** For Microsoft Store submission, DO NOT sign the package. Microsoft will sign it after approval.

## Testing the Package

### 1. Local Installation

Install the package locally (requires signing):

```powershell
Add-AppxPackage -Path "dist_msix\HoppyWhisper_0.1.0.0.msix"
```

If unsigned, you'll get an error. Sign first or enable Developer Mode:
- Settings → Update & Security → For developers → Developer mode (ON)

### 2. Launch the App

After installation:
- Open Start Menu
- Search for "Hoppy Whisper"
- Launch the app
- Verify tray icon appears
- Test hotkey functionality

### 3. Check Installation Location

Apps are installed to:
```
C:\Program Files\WindowsApps\HoppyWhisper.HoppyWhisper_0.1.0.0_x64__{PublisherID}\
```

### 4. Uninstall

```powershell
Remove-AppxPackage -Package HoppyWhisper.HoppyWhisper_0.1.0.0_x64__{PublisherID}
```

Or via Settings → Apps → Hoppy Whisper → Uninstall

## Windows App Certification Kit (WACK)

**CRITICAL:** Run WACK before Store submission to catch issues early.

### Run WACK

```powershell
& "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" test -appxpackagepath "dist_msix\HoppyWhisper_0.1.0.0.msix"
```

Or use GUI:
1. Open "Windows App Cert Kit" from Start Menu
2. Select "Validate App Package"
3. Browse to your MSIX file
4. Click "Next" and wait for tests to complete

### WACK Tests

The kit runs multiple tests:
- **App manifest compliance** - Validates AppxManifest.xml
- **Platform compatibility** - Checks Windows version requirements
- **Supported APIs** - Verifies no restricted APIs are used
- **Package sanity** - Validates package structure
- **Security tests** - Checks for vulnerabilities
- **Performance tests** - Launch time, memory usage, etc.

### Expected Results

For Hoppy Whisper, you should see:
- ✅ App manifest compliance
- ✅ Supported API test
- ✅ Package sanity test
- ⚠️ **Signing test may fail** (OK if submitting unsigned to Store)
- ✅ Performance tests (app should launch < 5 seconds)

### Common Issues and Fixes

#### Issue: "Package is not signed"
**Fix:** This is OK for Store submission. Microsoft signs packages after approval.

For local testing, sign the package (see above).

#### Issue: "App manifest uses restricted capabilities"
**Fix:** Review `AppxManifest.xml` capabilities section. Remove any that aren't needed.

Current capabilities:
- `internetClient` - For model downloads
- `runFullTrust` - For Win32 app execution
- `microphone` - For audio capture

All are justified and should pass.

#### Issue: "Performance: App launch time exceeded"
**Fix:** 
- Optimize PyInstaller bundle (remove unnecessary dependencies)
- Reduce model file sizes if bundled
- Implement lazy loading for heavy modules

#### Issue: "Resource.pri missing or invalid"
**Fix:** Ensure `makepri.exe` ran successfully. Check build script output.

If missing, rebuild with:
```powershell
.\msix\build_msix.ps1 -NoBuild
```

## Troubleshooting

### Build Errors

#### "makeappx.exe not found"
Install Windows 10 SDK. Verify installation path:
```powershell
Get-ChildItem "C:\Program Files (x86)\Windows Kits\10\bin" -Recurse -Filter makeappx.exe
```

#### "AppxManifest.xml is invalid"
Validate XML syntax. Common issues:
- Missing namespace declarations
- Invalid characters in identity name
- Incorrect version format (must be X.X.X.X)

#### "Executable not found"
Build PyInstaller executable first:
```powershell
poetry run pyinstaller --noconfirm --clean HoppyWhisper_onefile.spec
```

### Runtime Errors

#### "App fails to launch after installation"
Check Event Viewer:
1. Windows Logs → Application
2. Look for errors from "Hoppy Whisper" source
3. Common issues:
   - Missing DLLs (onnxruntime, vcruntime140.dll)
   - Incorrect file permissions
   - Conflicting hotkey registration

#### "Microphone access denied"
The app needs microphone capability declared in manifest. Verify:
```xml
<DeviceCapability Name="microphone" />
```

User must also grant permission in Windows Settings → Privacy → Microphone.

#### "App crashes on startup"
Enable console mode for debugging:
1. Edit `HoppyWhisper_onefile.spec`
2. Change `console=False` to `console=True`
3. Rebuild executable
4. Rebuild MSIX
5. Check console output for error messages

### Package Validation Errors

#### "Signature verification failed"
Expected if unsigned. Sign package or submit unsigned to Store.

#### "Asset file missing"
Ensure all referenced assets in `AppxManifest.xml` exist in `msix\Assets\`.

Required assets checklist:
- [ ] Square44x44Logo.png
- [ ] Square150x150Logo.png
- [ ] Wide310x150Logo.png
- [ ] SmallTile.png
- [ ] StoreLogo.png
- [ ] SplashScreen.png

## Advanced Configuration

### Publisher Identity

Before Store submission, update `AppxManifest.xml`:

```xml
<Identity Name="HoppyWhisper.HoppyWhisper"
          Publisher="CN=YOUR_ACTUAL_PUBLISHER_CN"
          Version="0.1.0.0" />
```

Get your Publisher CN from Partner Center:
1. Go to https://partner.microsoft.com/dashboard
2. Account settings → Identity details
3. Copy "Publisher ID"

### Multi-Architecture Support

Currently builds for x64 only. To add ARM64:

1. Build ARM64 executable (requires ARM64 Python environment)
2. Create separate MSIX for each architecture
3. Upload both to Store as a "package flight"

Or create an MSIX bundle:
```powershell
makeappx bundle /d "bundle_dir" /p "HoppyWhisper.msixbundle"
```

### Localization

Add language support:

1. Update `AppxManifest.xml`:
```xml
<Resources>
  <Resource Language="en-us" />
  <Resource Language="zh-cn" />
  <Resource Language="es-es" />
</Resources>
```

2. Create localized assets (optional):
```
msix/Assets/
  en-us/
    StoreLogo.png
  zh-cn/
    StoreLogo.png
```

3. Provide Store listings in each language via Partner Center

## CI/CD Integration

### GitHub Actions Workflow

Add MSIX build to CI:

```yaml
- name: Build MSIX
  run: |
    .\msix\build_msix.ps1 -Version "${{ github.ref_name }}"
  
- name: Run WACK
  run: |
    & "C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe" test -appxpackagepath "dist_msix\*.msix"
  
- name: Upload MSIX
  uses: actions/upload-artifact@v3
  with:
    name: msix-package
    path: dist_msix/*.msix
```

### Automated Store Submission

Use Store Submission API for automated uploads:
- https://learn.microsoft.com/en-us/windows/uwp/monetize/create-and-manage-submissions-using-windows-store-services

## Next Steps

After successful WACK testing:

1. **Create Store listing** - See [STORE_SUBMISSION_GUIDE.md](STORE_SUBMISSION_GUIDE.md)
2. **Upload package** - Partner Center → New submission → Packages
3. **Fill out IARC questionnaire** - Age rating
4. **Submit for review** - Takes 24-48 hours typically

## References

- [MSIX Packaging Documentation](https://learn.microsoft.com/en-us/windows/msix/)
- [Windows App Certification Kit](https://learn.microsoft.com/en-us/windows/uwp/debug-test-perf/windows-app-certification-kit)
- [Partner Center Guide](https://learn.microsoft.com/en-us/windows/apps/publish/)
- [Desktop Bridge (Win32 to MSIX)](https://learn.microsoft.com/en-us/windows/apps/desktop/modernize/desktop-to-uwp-root)
