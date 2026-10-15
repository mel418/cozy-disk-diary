; Inno Setup script - builds a one-file installer (no admin rights needed).
#define AppName "Cozy Disk Diary"
#define AppVersion "1.0.0"

[Setup]
AppId={{7B3E2A64-5C1D-4F8A-9E2B-C01D1D150001}
AppName={#AppName}
AppVersion={#AppVersion}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
PrivilegesRequired=lowest
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppName}.exe
OutputDir=installer_output
OutputBaseFilename=CozyDiskDiary-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes

[Tasks]
Name: "desktopicon"; Description: "Put a bunny shortcut on my desktop"; Flags: checkedonce

[Files]
Source: "build_out\dist\{#AppName}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppName}.exe"; IconFilename: "{app}\{#AppName}.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppName}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppName}.exe"; Description: "Open Cozy Disk Diary now"; Flags: nowait postinstall skipifsilent
