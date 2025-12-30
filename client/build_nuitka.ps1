# build_nuitka.ps1
# Script build dự án bằng Nuitka (Biên dịch ra mã máy C++)
# Yêu cầu: Đã cài đặt Python và pip. Nuitka sẽ tự động tải C compiler nếu thiếu.

param(
    [string]$NewVersion = "",
    [switch]$Clean = $false  # Add -Clean flag to force clean build
)

# ------------------------------------------------------------------
# Force PowerShell dùng UTF-8
[console]::OutputEncoding = [System.Text.Encoding]::UTF8
# ------------------------------------------------------------------

# ------------------------------------------------------------------
# Activate venv if exists (important when running from Admin UI)
# Venv is in the root directory (parent of client)
$venvPath = Join-Path (Split-Path $PSScriptRoot -Parent) ".venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "[0/5] Activating virtual environment..." -ForegroundColor Yellow
    . $venvPath
}
# ------------------------------------------------------------------

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FourT Suite - Nuitka Build Script" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Hàm ghi file UTF-8 không BOM
function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    $utf8 = New-Object System.Text.UTF8Encoding $false
    [IO.File]::WriteAllText($Path, $Content, $utf8)
}

# Step 1: Version
if ($NewVersion) {
    Write-Host "[1/4] Dang cap nhat version thanh $NewVersion..." -ForegroundColor Yellow
    $Version = $NewVersion.Trim()
    Write-Utf8NoBom -Path "version.ini" -Content $Version
    Write-Host "      Da cap nhat version.ini" -ForegroundColor Green
}
else {
    if (Test-Path "version.ini") {
        $Version = (Get-Content "version.ini" -Raw -Encoding UTF8).Trim()
        Write-Host "[1/4] Su dung version hien tai: $Version" -ForegroundColor Yellow
    }
    else {
        $Version = "1.0.0"
        Write-Utf8NoBom -Path "version.ini" -Content $Version
        Write-Host "[1/4] Tao version mac dinh: $Version" -ForegroundColor Yellow
    }
}

Write-Host ""

# Step 2: Clean up old build (only if -Clean flag is set, otherwise keep cache)
if ($Clean) {
    Write-Host "[2/4] Don dep thu muc build cu..." -ForegroundColor Yellow
    if (Test-Path "launcher.build") { Remove-Item "launcher.build" -Recurse -Force }
    if (Test-Path "launcher.dist") { Remove-Item "launcher.dist" -Recurse -Force }
    if (Test-Path "launcher.onefile-build") { Remove-Item "launcher.onefile-build" -Recurse -Force }
    Write-Host "      Da don dep xong." -ForegroundColor Green
}
else {
    Write-Host "[2/4] Giu lai cache de build nhanh hon..." -ForegroundColor Yellow
}

# Always clean dist/FourT to avoid conflicts
if (Test-Path "dist\FourT") { Remove-Item "dist\FourT" -Recurse -Force }
Write-Host ""

# Step 3: Run Nuitka
Write-Host "[3/4] Dang bien dich bang Nuitka..." -ForegroundColor Yellow

$nuitkaArgs = @(
    "--standalone",
    "--windows-console-mode=attach",
    "--enable-plugin=tk-inter",
    # Tcl/Tk data files (fix init.tcl not found error)
    "--include-data-dir=$env:LOCALAPPDATA\Programs\Python\Python311\tcl\tcl8.6=tcl/tcl8.6",
    "--include-data-dir=$env:LOCALAPPDATA\Programs\Python\Python311\tcl\tk8.6=tcl/tk8.6",
    # Exclude heavy modules not needed for core functionality
    "--nofollow-import-to=torch",
    # MIDI processing modules
    "--include-module=pretty_midi",
    "--include-module=mido",
    "--windows-icon-from-ico=favicon.ico",
    # Windows Metadata (helps reduce antivirus false positives)
    # Windows Metadata (helps reduce antivirus false positives)
    "--windows-company-name=System Runtime",
    "--windows-product-name=Runtime Broker",
    "--windows-file-version=$Version.0",
    "--windows-product-version=$Version.0",
    "--windows-file-description=System Runtime Broker",
    # Include data files
    "--include-data-file=favicon.ico=favicon.ico",
    # "--include-data-file=version.txt=version.txt",
    "--include-data-file=version.ini=version.ini",
    "--include-data-dir=midi_files=midi_files",
    "--include-data-dir=wwm_resources=wwm_resources",
    "--include-data-file=wwm_combos/templates.json=wwm_combos/templates.json",
    "--include-data-file=data/skills.json=data/skills.json",
    "--include-data-file=data/quest_helper_config.json=data/quest_helper_config.json",
    # "--include-data-file=data/wwm_user_settings.json=data/wwm_user_settings.json",
    # UI modules
    "--include-module=ui.animations",
    "--include-module=ui.theme",

    "--include-module=ui.menu_launcher",
    "--include-module=ui.splash_screen",
    # "--include-module=ui.wwm_combo",
    # Midi
    "--include-module=ui.midi_player_frame",
    "--include-module=ui.playlist_frame",
    "--include-module=ui.script_viewer",

    # upgrade
    "--include-module=ui.upgrade_window",
    "--include-module=ui.payment_window",

    # macro
    # "--include-module=ui.macro_window",
    
    # Dialog UI modules
    "--include-module=ui.bug_report_dialog",
    "--include-module=ui.exit_confirm_dialog",
    "--include-module=ui.sync_progress_dialog",
    "--include-module=ui.update_complete_dialog",
    # Ping Optimizer UI
    "--include-module=ui.ping_optimizer_frame",
    # Quest Video Helper UI modules
    "--include-module=ui.quest_video_helper_window",
    "--include-module=ui.region_selector",
    "--include-module=ui.video_overlay_window",
    "--include-module=ui.video_overlay_launcher",
    "--include-module=ui.ocr_setup_window",
    # Screen Translator UI
    "--include-module=ui.screen_translator_window",
    "--include-module=services.translation_service",
    # Services modules (offline-first)
    "--include-module=services.connection_manager",
    "--include-module=services.secure_license_cache",
    "--include-module=services.license_key_utils",
    "--include-module=services.offline_payment_service",
    # Quest Video Helper services
    "--include-module=services.ocr_addon_manager",
    "--include-module=services.video_popup_service",
    "--include-module=services.quest_helper_settings",
    # Ping Optimizer service
    "--include-module=services.ping_optimizer_service",
    # WWM Combo runtime
    "--include-module=services.wwm_combo_runtime",
    # Sync service
    "--include-module=services.sync_service",
    # Quest Video Helper dependencies
    # winocr is a single .py file, need to copy it directly and include winrt packages
    "--include-data-file=../.venv/Lib/site-packages/winocr.py=winocr.py",
    "--include-package=winrt",
    # OCR dependencies (pytesseract downloaded at runtime, but PIL/numpy needed)
    "--include-module=PIL",
    "--include-module=PIL.Image",
    "--include-module=PIL.ImageEnhance",
    "--include-module=PIL.ImageOps",
    "--include-module=PIL.ImageGrab",
    "--include-module=numpy",
    # Screen capture for OCR
    "--include-module=dxcam",
    # Note: youtube_search_service removed - now opens YouTube search URL directly in browser
    # Exclude webview platforms not needed on Windows
    "--nofollow-import-to=webview.platforms.android",
    "--nofollow-import-to=webview.platforms.cocoa",
    "--nofollow-import-to=webview.platforms.gtk",
    "--nofollow-import-to=webview.platforms.qt",
    # Build options
    "--mingw64",
    "--windows-uac-admin",
    "--assume-yes-for-downloads",
    "--output-dir=dist",
    "--output-filename=FourT.exe", # Recommendation: Rename this to something safe like 'calc_host.exe' after build
    "launcher.py"
)

# Chạy lệnh
python -m nuitka $nuitkaArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "      Build that bai!" -ForegroundColor Red
    exit 1
}

# Đổi tên thư mục output
if (Test-Path "dist\launcher.dist") {
    if (Test-Path "dist\FourT") { Remove-Item "dist\FourT" -Recurse -Force }
    Move-Item "dist\launcher.dist" "dist\FourT"
}

Write-Host "      Build thanh cong!" -ForegroundColor Green
Write-Host ""

# Step 4: Update update_info.json
Write-Host "[4/4] Dang cap nhat update_info.json..." -ForegroundColor Yellow

$jsonPath = "update_info.json"
if (Test-Path $jsonPath) {
    $json = Get-Content $jsonPath -Raw -Encoding UTF8 | ConvertFrom-Json
    $json.version = $Version
    $json.min_version = $Version
    $json.release_date = (Get-Date).ToString("yyyy-MM-dd")
    $jsonText = $json | ConvertTo-Json -Depth 10
    
    if ($PSVersionTable.PSVersion.Major -ge 7) {
        $jsonText | Set-Content -Path $jsonPath -Encoding utf8NoBOM
    }
    else {
        Write-Utf8NoBom -Path $jsonPath -Content $jsonText
    }
    Write-Host "      update_info.json da cap nhat." -ForegroundColor Green
}
else {
    Write-Host "      Khong tim thay update_info.json, bo qua." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "NUITKA BUILD HOAN TAT!" -ForegroundColor Green
Write-Host "Output: dist\FourT\FourT.exe" -ForegroundColor White
Write-Host ""
Write-Host "Next: Run .\build_installer.ps1 to create FourT_Setup.exe" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
