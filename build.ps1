#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Build Parakeet executable with PyInstaller

.DESCRIPTION
    This script builds the Parakeet Windows executable using PyInstaller.
    It can perform clean builds, incremental builds, and run basic sanity checks.

.PARAMETER Clean
    Remove build artifacts before building (clean build)

.PARAMETER Test
    Run the built executable to verify it launches

.PARAMETER Console
    Build with console window enabled (for debugging)

.PARAMETER SkipTests
    Skip running pytest before building

.EXAMPLE
    .\build.ps1
    Build the executable (incremental)

.EXAMPLE
    .\build.ps1 -Clean
    Clean build from scratch

.EXAMPLE
    .\build.ps1 -Clean -Test
    Clean build and test the executable

.EXAMPLE
    .\build.ps1 -Console
    Build with console window for debugging
#>

param(
    [switch]$Clean,
    [switch]$Test,
    [switch]$Console,
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"

# Colors for output
function Write-Step {
    param([string]$Message)
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] $Message" -ForegroundColor Green
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERR] $Message" -ForegroundColor Red
}

# Check Poetry is available
Write-Step "Checking environment..."
try {
    $poetryVersion = poetry --version
    Write-Success "Poetry found: $poetryVersion"
} catch {
    Write-Error "Poetry not found. Please install Poetry first:"
    Write-Host "  py -3.11 -m pip install poetry"
    exit 1
}

# Check Python version
try {
    $pythonVersion = poetry run python --version
    Write-Success "Python: $pythonVersion"
} catch {
    Write-Error "Poetry environment not set up correctly"
    Write-Host "Run: poetry install --with dev"
    exit 1
}

# Clean build artifacts if requested
if ($Clean) {
    Write-Step "Cleaning build artifacts..."
    if (Test-Path build) {
        Remove-Item -Recurse -Force build
        Write-Success "Removed build/ directory"
    }
    if (Test-Path dist) {
        Remove-Item -Recurse -Force dist
        Write-Success "Removed dist/ directory"
    }
    if (Test-Path Parakeet.spec) {
        Remove-Item -Force "*.spec.backup" -ErrorAction SilentlyContinue
    }
}

# Modify spec file for console mode if requested
$specModified = $false
if ($Console) {
    Write-Step "Enabling console mode..."
    $specContent = Get-Content Parakeet.spec -Raw
    if ($specContent -match "console_mode = False") {
        Copy-Item Parakeet.spec Parakeet.spec.backup
        $specContent = $specContent -replace "console_mode = False", "console_mode = True"
        Set-Content Parakeet.spec -Value $specContent
        $specModified = $true
        Write-Success "Console mode enabled"
    }
}

try {
    # Run tests unless skipped
    if (-not $SkipTests) {
        Write-Step "Running tests..."
        poetry run pytest --tb=short
        Write-Success "Tests passed"
    }

    # Build with PyInstaller
    Write-Step "Building executable with PyInstaller..."
    $buildArgs = @("run", "pyinstaller", "--noconfirm")
    if ($Clean) {
        $buildArgs += "--clean"
    }
    $buildArgs += "Parakeet.spec"

    $buildStart = Get-Date
    & poetry @buildArgs
    $buildDuration = (Get-Date) - $buildStart

    if (-not (Test-Path dist\Parakeet.exe)) {
        Write-Error "Build failed: dist\Parakeet.exe not found"
        exit 1
    }

    $exeSize = (Get-Item dist\Parakeet.exe).Length / 1MB
    Write-Success "Build completed in $($buildDuration.TotalSeconds.ToString('0.0'))s"
    Write-Host "Executable size: $($exeSize.ToString('0.0')) MB"

    # Test the executable if requested
    if ($Test) {
        Write-Step "Testing executable..."
        Write-Host "Launching Parakeet.exe (press Ctrl+C to stop after verifying it works)"
        
        $testProcess = Start-Process -FilePath "dist\Parakeet.exe" -PassThru -NoNewWindow
        
        # Give it a few seconds to start
        Start-Sleep -Seconds 3
        
        if ($testProcess.HasExited) {
            Write-Error "Executable crashed on startup"
            Write-Host "Exit code: $($testProcess.ExitCode)"
            exit 1
        } else {
            Write-Success "Executable launched successfully"
            Write-Host "Check the system tray for the Parakeet icon"
            Write-Host "Press Enter to stop the test..."
            Read-Host
            
            # Stop the test process
            Stop-Process -Id $testProcess.Id -Force -ErrorAction SilentlyContinue
            Write-Success "Test completed"
        }
    }

    Write-Success "Build complete: dist\Parakeet.exe"

} finally {
    # Restore spec file if modified
    if ($specModified -and (Test-Path Parakeet.spec.backup)) {
        Write-Step "Restoring original spec file..."
        Move-Item Parakeet.spec.backup Parakeet.spec -Force
        Write-Success "Spec file restored"
    }
}

Write-Host ""
Write-Host 'Next steps:' -ForegroundColor Yellow
Write-Host '  - Test the executable: .\dist\Parakeet.exe'
Write-Host '  - Create zip for distribution: Compress-Archive dist\Parakeet.exe Parakeet-windows-x86_64.zip'
Write-Host '  - Run smoke tests: See SMOKE_TEST.md'
