# Builds the app into a slim .exe (clean venv) and wraps it in a one-file installer.
# Usage:  powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path .venv)) { python -m venv .venv }
$py = ".\.venv\Scripts\python.exe"
& $py -m pip install -q -r requirements.txt pyinstaller

Remove-Item build_out -Recurse -Force -ErrorAction SilentlyContinue
& $py -m PyInstaller --noconfirm --windowed --name "Cozy Disk Diary" --icon "$PWD\icon.ico" `
    --add-data "$PWD\index.html;." --add-data "$PWD\icon.ico;." `
    --distpath "$PWD\build_out\dist" --workpath "$PWD\build_out\work" --specpath "$PWD\build_out" app.py

$iscc = @("$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "C:\Program Files (x86)\Inno Setup 6\ISCC.exe") |
    Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { Write-Warning "Inno Setup not found (winget install JRSoftware.InnoSetup) - skipping installer."; exit }
& $iscc installer.iss
Write-Host "Done! Installer: installer_output\CozyDiskDiary-Setup.exe"
