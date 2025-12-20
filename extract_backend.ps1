# ============================================
# FourT Helper - Backend Extraction Script
# Tách backend thành project riêng biệt
# ============================================

param(
    [string]$TargetDir = "..\fourthelper-server"
)

$SourceDir = $PSScriptRoot
$TargetDir = Join-Path $SourceDir $TargetDir

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  FourT Backend Extraction Script" -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Source: $SourceDir" -ForegroundColor Yellow
Write-Host "Target: $TargetDir" -ForegroundColor Yellow
Write-Host ""

# Auto-confirm (no prompt)
Write-Host "Starting extraction..." -ForegroundColor Green

# Create target directory structure
Write-Host "`n[1/7] Creating directory structure..." -ForegroundColor Green

$directories = @(
    "$TargetDir",
    "$TargetDir\app",
    "$TargetDir\app\routers",
    "$TargetDir\app\middleware",
    "$TargetDir\app\security",
    "$TargetDir\admin",
    "$TargetDir\admin\tabs",
    "$TargetDir\cloudflare",
    "$TargetDir\data",
    "$TargetDir\config"
)

foreach ($dir in $directories) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
        Write-Host "  Created: $dir" -ForegroundColor Gray
    }
}

# Copy backend core files
Write-Host "`n[2/7] Copying backend core files..." -ForegroundColor Green

$coreFiles = @{
    "backend\main.py"           = "app\main.py"
    "backend\database.py"       = "app\database.py"
    "backend\db.py"             = "app\db.py"
    "backend\schemas.py"        = "app\schemas.py"
    "backend\package_config.py" = "app\package_config.py"
    "backend\__init__.py"       = "app\__init__.py"
}

foreach ($src in $coreFiles.Keys) {
    $srcPath = Join-Path $SourceDir $src
    $dstPath = Join-Path $TargetDir $coreFiles[$src]
    if (Test-Path $srcPath) {
        Copy-Item $srcPath $dstPath -Force
        Write-Host "  Copied: $src -> $($coreFiles[$src])" -ForegroundColor Gray
    }
}

# Copy routers
Write-Host "`n[3/7] Copying routers..." -ForegroundColor Green

$routerFiles = Get-ChildItem -Path "$SourceDir\backend\routers" -Filter "*.py" -ErrorAction SilentlyContinue
foreach ($file in $routerFiles) {
    Copy-Item $file.FullName "$TargetDir\app\routers\$($file.Name)" -Force
    Write-Host "  Copied: routers\$($file.Name)" -ForegroundColor Gray
}

# Copy middleware
Write-Host "`n[4/7] Copying middleware..." -ForegroundColor Green

$middlewareFiles = Get-ChildItem -Path "$SourceDir\backend\middleware" -Filter "*.py" -ErrorAction SilentlyContinue
foreach ($file in $middlewareFiles) {
    Copy-Item $file.FullName "$TargetDir\app\middleware\$($file.Name)" -Force
    Write-Host "  Copied: middleware\$($file.Name)" -ForegroundColor Gray
}

# Copy security
Write-Host "`n[5/7] Copying security modules..." -ForegroundColor Green

$securityFiles = Get-ChildItem -Path "$SourceDir\backend\security" -Filter "*.py" -ErrorAction SilentlyContinue
foreach ($file in $securityFiles) {
    Copy-Item $file.FullName "$TargetDir\app\security\$($file.Name)" -Force
    Write-Host "  Copied: security\$($file.Name)" -ForegroundColor Gray
}

# Copy admin (optional)
Write-Host "`n[5.5/7] Copying admin panel..." -ForegroundColor Green

if (Test-Path "$SourceDir\backend\admin\admin_window.py") {
    Copy-Item "$SourceDir\backend\admin\admin_window.py" "$TargetDir\admin\admin_window.py" -Force
    Copy-Item "$SourceDir\backend\admin\__init__.py" "$TargetDir\admin\__init__.py" -Force -ErrorAction SilentlyContinue
    
    $tabFiles = Get-ChildItem -Path "$SourceDir\backend\admin\tabs" -Filter "*.py" -ErrorAction SilentlyContinue
    foreach ($file in $tabFiles) {
        Copy-Item $file.FullName "$TargetDir\admin\tabs\$($file.Name)" -Force
        Write-Host "  Copied: admin\tabs\$($file.Name)" -ForegroundColor Gray
    }
}

# Copy data files
Write-Host "`n[6/7] Copying data and config files..." -ForegroundColor Green

$dataFiles = @(
    "data\fourthelper.db",
    "data\packages.json",
    "data\skills.json"
)

foreach ($file in $dataFiles) {
    $srcPath = Join-Path $SourceDir $file
    $dstPath = Join-Path $TargetDir $file
    if (Test-Path $srcPath) {
        Copy-Item $srcPath $dstPath -Force
        Write-Host "  Copied: $file" -ForegroundColor Gray
    }
}

# Copy config files
$configFiles = @(
    ".env",
    "server_config.json",
    "run_server.py"
)

foreach ($file in $configFiles) {
    $srcPath = Join-Path $SourceDir $file
    if (Test-Path $srcPath) {
        Copy-Item $srcPath "$TargetDir\$file" -Force
        Write-Host "  Copied: $file" -ForegroundColor Gray
    }
}

# Copy cloudflare worker
if (Test-Path "$SourceDir\cloudflare\sepay-webhook-proxy.js") {
    Copy-Item "$SourceDir\cloudflare\sepay-webhook-proxy.js" "$TargetDir\cloudflare\sepay-webhook-proxy.js" -Force
    Write-Host "  Copied: cloudflare\sepay-webhook-proxy.js" -ForegroundColor Gray
}

# Create server-only requirements.txt
Write-Host "`n[7/7] Creating requirements.txt..." -ForegroundColor Green

$requirements = @"
# FourT Helper Backend - Dependencies
# ====================================

# Core Framework
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
pydantic>=2.0.0

# Database
aiosqlite>=0.19.0

# Environment & Config
python-dotenv>=1.0.0
python-multipart>=0.0.6

# HTTP Client
requests>=2.31.0

# Tunnel Integration
pyngrok>=7.0.0

# System Monitoring
psutil>=5.9.0

# Security (optional)
cryptography>=41.0.0
"@

Set-Content -Path "$TargetDir\requirements.txt" -Value $requirements
Write-Host "  Created: requirements.txt" -ForegroundColor Gray

# Create .env.example
$envExample = @"
# ============================================
# FourT Helper Backend - Environment Variables
# ============================================

# Server URL (for local development)
LICENSE_SERVER_URL=http://127.0.0.1:8000

# Sepay Configuration (auto payment verification)
# Get from: https://my.sepay.vn
SEPAY_ACCOUNT_NUMBER=your_account_number
SEPAY_API_KEY=your_api_key

# VietQR Bank Configuration
BANK_ID=MB
BANK_ACCOUNT=your_bank_account
BANK_NAME=YOUR NAME

# Package Prices (VND)
BASIC_PRICE=20000
PLUS_PRICE=35000
PRO_PRICE=55000
PREMIUM_PRICE=89000

# Tunnel Configuration
# Options: cloudflare, ngrok, bore, localhost.run, none
TUNNEL_TYPE=cloudflare

# ngrok (if using ngrok)
NGROK_AUTHTOKEN=your_ngrok_token

# Cloudflare Named Tunnel (if using cloudflare)
CLOUDFLARE_TUNNEL_NAME=your_tunnel_name
CLOUDFLARE_TUNNEL_URL=https://your-domain.com
"@

Set-Content -Path "$TargetDir\.env.example" -Value $envExample
Write-Host "  Created: .env.example" -ForegroundColor Gray

# Create server config module
$serverConfig = @"
"""
Server Configuration - Extracted from core/config.py
Only contains server-side configurations
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ------------------- License Configuration -------------------
LICENSE_DURATION_DAYS = 30  # Monthly subscription

# ------------------- Payment Configuration (VietQR) -------------------
BANK_INFO = {
    "BANK_ID": os.getenv("BANK_ID"),
    "ACCOUNT_NO": os.getenv("BANK_ACCOUNT"),
    "ACCOUNT_NAME": os.getenv("BANK_NAME"),
    "TEMPLATE": "compact2"
}

def get_int_env(key, default=0):
    try:
        return int(os.getenv(key, default))
    except:
        return default

PACKAGE_PRICES = {
    "basic": get_int_env("BASIC_PRICE", 20000),
    "plus": get_int_env("PLUS_PRICE", 35000),
    "pro": get_int_env("PRO_PRICE", 55000),
    "premium": get_int_env("PREMIUM_PRICE", 89000),
}

# ------------------- Sepay Configuration -------------------
SEPAY_ACCOUNT_NUMBER = os.getenv("SEPAY_ACCOUNT_NUMBER", "")
SEPAY_API_KEY = os.getenv("SEPAY_API_KEY", "")
SEPAY_ENABLED = bool(SEPAY_ACCOUNT_NUMBER and SEPAY_API_KEY)

# ------------------- Server URL Discovery -------------------
SERVER_CONFIG_URL = "https://api.npoint.io/c6878ec0e82ad63a767f"

# ------------------- Demo License -------------------
DEMO_LICENSE_KEY = "DEMO-FOURTHELPER-2024"
"@

Set-Content -Path "$TargetDir\config\settings.py" -Value $serverConfig
New-Item -ItemType File -Path "$TargetDir\config\__init__.py" -Force | Out-Null
Write-Host "  Created: config\settings.py" -ForegroundColor Gray

# Create README
$readme = @"
# FourT Helper Backend

Backend server cho ứng dụng FourT Helper.

## Cấu trúc

```
fourthelper-server/
├── app/                    # FastAPI application
│   ├── main.py             # Entry point
│   ├── database.py         # SQLite database
│   ├── routers/            # API endpoints
│   ├── middleware/         # Rate limiter, validators
│   └── security/           # Security modules
├── admin/                  # Admin panel (Tkinter)
├── cloudflare/             # Cloudflare Worker
├── config/                 # Server configuration
├── data/                   # Database files
├── run_server.py           # Start server
├── .env                    # Environment variables
└── requirements.txt        # Dependencies
```

## Cài đặt

```bash
# Tạo virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Cài dependencies
pip install -r requirements.txt

# Copy .env
cp .env.example .env
# Edit .env với thông tin của bạn
```

## Chạy server

```bash
python run_server.py
```

## API Endpoints

- ``POST /license/verify`` - Xác thực license
- ``POST /license/activate`` - Kích hoạt license
- ``POST /payment/create`` - Tạo đơn thanh toán
- ``POST /sepay/webhook`` - Webhook nhận thông báo từ Sepay
- ``GET /health`` - Health check

## Database

SQLite database lưu tại ``data/fourthelper.db``
"@

Set-Content -Path "$TargetDir\README.md" -Value $readme
Write-Host "  Created: README.md" -ForegroundColor Gray

# Summary
Write-Host "`n============================================" -ForegroundColor Cyan
Write-Host "  Extraction Complete!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Backend extracted to: $TargetDir" -ForegroundColor Yellow
Write-Host ""
Write-Host "Next steps:" -ForegroundColor White
Write-Host "  1. cd $TargetDir" -ForegroundColor Gray
Write-Host "  2. python -m venv venv" -ForegroundColor Gray
Write-Host "  3. venv\Scripts\activate" -ForegroundColor Gray
Write-Host "  4. pip install -r requirements.txt" -ForegroundColor Gray
Write-Host "  5. Update imports in app/*.py (backend -> app)" -ForegroundColor Gray
Write-Host "  6. python run_server.py" -ForegroundColor Gray
Write-Host ""
