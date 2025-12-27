@echo off
REM Run Admin Panel directly (no build required)
cd /d "%~dp0"

REM Activate virtual environment from parent directory (FourT/.venv)
if exist "..\\.venv\\Scripts\\activate.bat" (
    call ..\.venv\Scripts\activate.bat
) else if exist ".venv\\Scripts\\activate.bat" (
    call .venv\Scripts\activate.bat
)

python admin.py