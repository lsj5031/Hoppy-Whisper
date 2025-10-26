# Build MSIX package for Microsoft Store submission
# This script creates an MSIX package from the PyInstaller executable
#
# Prerequisites:
# 1. Windows 10 SDK installed (for makeappx.exe and signtool.exe)
# 2. PyInstaller executable already built
# 3. All required assets in msix/Assets/ directory
# 4. Code signing certificate (for testing/sideloading)
#
# Usage:
#   .\msix\build_msix.ps1 [-Version "0.1.0.0"] [-NoBuild] [-Sign] [-CertPath "cert.pfx"] [-CertPassword "password"]

param(
    [string]$Version = "0.1.0.0",
    [switch]$NoBuild,
    [switch]$Sign,
    [string]$CertPath = "",
    [string]$CertPassword = ""
)

$ErrorActionPreference = "Stop"

# Configuration
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSCommandPath)
$MsixDir = Join-Path $ProjectRoot "msix"
$DistDir = Join-Path $ProjectRoot "dist"
$PackagingDir = Join-Path $MsixDir "packaging"
$OutputDir = Join-Path $ProjectRoot "dist_msix"
$ExeName = "Hoppy Whisper-CPU.exe"
$PackageName = "HoppyWhisper"

# Find Windows SDK tools
$WinSDKPath = "C:\Program Files (x86)\Windows Kits\10\bin"
$LatestSDKVersion = Get-ChildItem $WinSDKPath | Where-Object { $_.Name -match '^\d+\.\d+\.\d+\.\d+$' } | Sort-Object Name -Descending | Select-Object -First 1
$SDKBinPath = Join-Path (Join-Path $WinSDKPath $LatestSDKVersion.Name) "x64"

$MakeAppx = Join-Path $SDKBinPath "makeappx.exe"
$SignTool = Join-Path $SDKBinPath "signtool.exe"
$MakePri = Join-Path $SDKBinPath "makepri.exe"

# Validate SDK tools
if (-not (Test-Path $MakeAppx)) {
    Write-Error "makeappx.exe not found. Please install Windows 10 SDK."
    Write-Host "Download from: https://developer.microsoft.com/en-us/windows/downloads/windows-sdk/"
    exit 1
}

Write-Host "=== Hoppy Whisper MSIX Build Script ===" -ForegroundColor Cyan
Write-Host "Version: $Version" -ForegroundColor Green
Write-Host "Project Root: $ProjectRoot" -ForegroundColor Gray
Write-Host "SDK Path: $SDKBinPath" -ForegroundColor Gray
Write-Host ""

# Step 1: Build PyInstaller executable (if not skipped)
if (-not $NoBuild) {
    Write-Host "[1/6] Building PyInstaller executable..." -ForegroundColor Yellow
    
    Push-Location $ProjectRoot
    try {
        & poetry run pyinstaller --noconfirm --clean HoppyWhisper_onefile.spec
        if ($LASTEXITCODE -ne 0) {
            throw "PyInstaller build failed"
        }
    } finally {
        Pop-Location
    }
    
    Write-Host "✓ PyInstaller build complete" -ForegroundColor Green
} else {
    Write-Host "[1/6] Skipping PyInstaller build (using existing)" -ForegroundColor Yellow
}

# Verify executable exists
$ExePath = Join-Path $DistDir $ExeName
if (-not (Test-Path $ExePath)) {
    Write-Error "Executable not found: $ExePath"
    Write-Host "Run without -NoBuild flag to build the executable first."
    exit 1
}

# Step 2: Prepare packaging directory
Write-Host "[2/6] Preparing packaging directory..." -ForegroundColor Yellow

if (Test-Path $PackagingDir) {
    Remove-Item $PackagingDir -Recurse -Force
}
New-Item -ItemType Directory -Path $PackagingDir -Force | Out-Null

# Copy executable
Copy-Item $ExePath $PackagingDir
Write-Host "✓ Copied executable: $ExeName" -ForegroundColor Gray

# Copy AppxManifest and update version
$ManifestSource = Join-Path $MsixDir "AppxManifest.xml"
$ManifestDest = Join-Path $PackagingDir "AppxManifest.xml"

if (-not (Test-Path $ManifestSource)) {
    Write-Error "AppxManifest.xml not found: $ManifestSource"
    exit 1
}

# Update version in manifest
(Get-Content $ManifestSource) -replace 'Version="[\d\.]+"', "Version=`"$Version`"" | Set-Content $ManifestDest
Write-Host "✓ Updated AppxManifest.xml (Version: $Version)" -ForegroundColor Gray

# Copy Assets
$AssetsSource = Join-Path $MsixDir "Assets"
$AssetsDest = Join-Path $PackagingDir "Assets"

if (Test-Path $AssetsSource) {
    Copy-Item $AssetsSource $PackagingDir -Recurse -Force
    $AssetCount = (Get-ChildItem $AssetsDest -File).Count
    Write-Host "✓ Copied $AssetCount asset files" -ForegroundColor Gray
} else {
    Write-Warning "Assets directory not found: $AssetsSource"
    Write-Host "  Creating placeholder Assets directory..."
    New-Item -ItemType Directory -Path $AssetsDest -Force | Out-Null
    Write-Warning "  You must add required PNG assets before Store submission!"
}

Write-Host "✓ Packaging directory prepared" -ForegroundColor Green

# Step 3: Generate PRI (Package Resource Index)
Write-Host "[3/6] Generating resource index..." -ForegroundColor Yellow

$PriConfigPath = Join-Path $MsixDir "priconfig.xml"
$ResourcesFile = Join-Path $PackagingDir "resources.pri"

if (Test-Path $MakePri) {
    try {
        # Create default priconfig if not exists
        if (-not (Test-Path $PriConfigPath)) {
            & $MakePri createconfig /cf $PriConfigPath /dq en-US /pv 10.0.0 2>&1 | Out-Null
        }
        
        # Generate PRI file
        & $MakePri new /pr $PackagingDir /cf $PriConfigPath /of $ResourcesFile /o 2>&1 | Out-Null
        
        if (Test-Path $ResourcesFile) {
            Write-Host "✓ Generated resources.pri" -ForegroundColor Gray
        } else {
            Write-Warning "resources.pri not generated (non-critical, continuing)"
        }
    } catch {
        Write-Warning "Failed to generate PRI file: $_"
        Write-Host "  This is non-critical, continuing build..."
    }
} else {
    Write-Warning "makepri.exe not found, skipping resource indexing"
}

Write-Host "✓ Resource index step complete" -ForegroundColor Green

# Step 4: Create MSIX package
Write-Host "[4/6] Creating MSIX package..." -ForegroundColor Yellow

if (-not (Test-Path $OutputDir)) {
    New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
}

$MsixPath = Join-Path $OutputDir "${PackageName}_${Version}.msix"

# Remove existing package
if (Test-Path $MsixPath) {
    Remove-Item $MsixPath -Force
}

# Create MSIX using makeappx
Write-Host "Running: makeappx pack /d `"$PackagingDir`" /p `"$MsixPath`"" -ForegroundColor Gray
& $MakeAppx pack /d $PackagingDir /p $MsixPath /l /o

if ($LASTEXITCODE -ne 0) {
    Write-Error "makeappx pack failed with exit code $LASTEXITCODE"
    exit 1
}

if (-not (Test-Path $MsixPath)) {
    Write-Error "MSIX package not created: $MsixPath"
    exit 1
}

$MsixSize = [math]::Round((Get-Item $MsixPath).Length / 1MB, 2)
Write-Host "✓ MSIX package created: ${MsixSize}MB" -ForegroundColor Green

# Step 5: Sign package (if requested)
if ($Sign) {
    Write-Host "[5/6] Signing MSIX package..." -ForegroundColor Yellow
    
    if (-not (Test-Path $SignTool)) {
        Write-Error "signtool.exe not found: $SignTool"
        exit 1
    }
    
    if (-not $CertPath -or -not (Test-Path $CertPath)) {
        Write-Error "Certificate file not found: $CertPath"
        Write-Host "Usage: -Sign -CertPath 'path\to\cert.pfx' -CertPassword 'password'"
        exit 1
    }
    
    $SignArgs = @(
        "sign",
        "/fd", "SHA256",
        "/a",
        "/f", $CertPath
    )
    
    if ($CertPassword) {
        $SignArgs += "/p", $CertPassword
    }
    
    # Add timestamp server
    $SignArgs += "/tr", "http://timestamp.digicert.com"
    $SignArgs += "/td", "SHA256"
    $SignArgs += $MsixPath
    
    Write-Host "Signing with certificate: $CertPath" -ForegroundColor Gray
    & $SignTool @SignArgs
    
    if ($LASTEXITCODE -ne 0) {
        Write-Warning "Package signing failed. This is OK for Store submission (Microsoft will sign it)."
        Write-Host "For local testing, you need a valid code signing certificate."
    } else {
        Write-Host "✓ Package signed successfully" -ForegroundColor Green
    }
} else {
    Write-Host "[5/6] Skipping signing (not required for Store submission)" -ForegroundColor Yellow
    Write-Host "  Microsoft Store will sign the package after approval." -ForegroundColor Gray
}

# Step 6: Validate package
Write-Host "[6/6] Validating MSIX package..." -ForegroundColor Yellow

# Check package integrity
Write-Host "Running: makeappx verify /p `"$MsixPath`"" -ForegroundColor Gray
& $MakeAppx verify /p $MsixPath

if ($LASTEXITCODE -ne 0) {
    Write-Warning "Package verification reported issues (this may be OK if unsigned)"
} else {
    Write-Host "✓ Package structure validated" -ForegroundColor Green
}

# Display package info
Write-Host ""
Write-Host "=== Build Complete ===" -ForegroundColor Cyan
Write-Host "Package: $MsixPath" -ForegroundColor Green
Write-Host "Size: ${MsixSize}MB" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "1. Test package locally: Add-AppxPackage -Path `"$MsixPath`"" -ForegroundColor Gray
Write-Host "2. Run WACK test: & 'C:\Program Files (x86)\Windows Kits\10\App Certification Kit\appcert.exe' test -appxpackagepath `"$MsixPath`"" -ForegroundColor Gray
Write-Host "3. Upload to Partner Center: https://partner.microsoft.com/en-us/dashboard/apps-and-games/overview" -ForegroundColor Gray
Write-Host ""
Write-Host "For troubleshooting, see: msix\MSIX_BUILD_GUIDE.md" -ForegroundColor Gray
