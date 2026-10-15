# 🐰 Cozy Disk Diary

A cute, pastel, **look-only** disk space explorer for Windows. See what each folder contains,
how much space it takes, and a diary of what changed between scans. Light and dark mode included.

> Nothing is ever deleted or modified. Your scan history stays on your own computer.

## Install (easiest)

1. Download `CozyDiskDiary-Setup.exe` from the [Releases](../../releases) page.
2. Run it. Windows may show a blue "protected your PC" screen because the app isn't code-signed:
   click **More info → Run anyway**.
3. Open **Cozy Disk Diary** from your desktop or Start menu. Right-click its taskbar icon to pin it.

Windows 10/11 only (needs the Edge WebView2 runtime, already included in Windows 11).

## Run from source

```
pip install -r requirements.txt
python app.py
```

## Build the installer

```
winget install JRSoftware.InnoSetup
powershell -ExecutionPolicy Bypass -File build.ps1
```

Produces `installer_output\CozyDiskDiary-Setup.exe`.

## How it works

- `app.py`: Python scanner + tiny local web server (standard library) + `pywebview` desktop window
- `index.html`: the whole UI (HTML/CSS/vanilla JS)
- `make_icon.py`: draws the bunny icon
- `build.ps1` + `installer.iss`: PyInstaller exe + Inno Setup installer
