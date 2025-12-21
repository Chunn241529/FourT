# Build Installer Script
# Requires: Inno Setup installed (https://jrsoftware.org/isdl.php)

param(
    [string]$Version = ""
)

# Force UTF-8
[console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FourT Helper - Create Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Get version
if (-not $Version) {
    if (Test-Path "version.ini") {
        $Version = (Get-Content "version.ini" -Raw -Encoding UTF8).Trim()
    }
    else {
        $Version = "1.0.0"
    }
}

Write-Host "Version: $Version" -ForegroundColor Yellow
Write-Host ""

# Check if Inno Setup is installed
$InnoPath = "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if (-not (Test-Path $InnoPath)) {
    $InnoPath = "C:\Program Files\Inno Setup 6\ISCC.exe"
}

if (-not (Test-Path $InnoPath)) {
    Write-Host "ERROR: Inno Setup not found!" -ForegroundColor Red
    Write-Host "Please install Inno Setup from: https://jrsoftware.org/isdl.php" -ForegroundColor Yellow
    exit 1
}

# Check if dist\FourT exists
if (-not (Test-Path "dist\FourT\FourT.exe")) {
    Write-Host "ERROR: dist\FourT\FourT.exe not found!" -ForegroundColor Red
    Write-Host "Please run build_nuitka.ps1 first to build the application." -ForegroundColor Yellow
    exit 1
}

# Update version in .iss file
Write-Host "Updating installer script version..." -ForegroundColor Yellow
$issContent = Get-Content "installer.iss" -Raw -Encoding UTF8
$issContent = $issContent -replace '#define MyAppVersion ".*"', "#define MyAppVersion `"$Version`""
$issContent | Set-Content "installer.iss" -Encoding UTF8

# Create releases folder for this version
$releasesDir = "$PSScriptRoot\releases\$Version"
if (-not (Test-Path $releasesDir)) {
    New-Item -ItemType Directory -Path $releasesDir -Force | Out-Null
    Write-Host "Created release folder: $releasesDir" -ForegroundColor Yellow
}

# Run Inno Setup Compiler
Write-Host "Building installer..." -ForegroundColor Yellow
$OutputName = "FourT_Setup_v$Version"
& $InnoPath "installer.iss" "/DOutputBaseFilename=$OutputName" "/O$releasesDir"

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Cyan
    Write-Host "INSTALLER BUILD COMPLETE!" -ForegroundColor Green
    Write-Host "Output: $releasesDir\$OutputName.exe" -ForegroundColor White
    Write-Host "========================================" -ForegroundColor Cyan
}
else {
    Write-Host "Installer build failed!" -ForegroundColor Red
    exit 1
}
