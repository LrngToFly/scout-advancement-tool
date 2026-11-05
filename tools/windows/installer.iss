; Inno Setup script for the Windows installer. Built by .github/workflows/windows.yml after
; PyInstaller has produced dist\Scout Advancement Tool\. Installs for the current user only,
; so no administrator rights are needed. Scout data in Documents is left alone on uninstall.

#ifndef AppVersion
  #define AppVersion "dev"
#endif
#ifndef AppVersionNum
  #define AppVersionNum "0.0.0"
#endif
#define AppName "Scout Advancement Tool"
#define AppExe "Scout Advancement Tool.exe"

[Setup]
AppId={{5B7D2C3E-8F41-4A6B-9C2D-1E3F4A5B6C7D}
AppName={#AppName}
AppVersion={#AppVersion}
VersionInfoVersion={#AppVersionNum}
AppPublisher={#AppName}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\..\dist
OutputBaseFilename=ScoutAdvancementTool-{#AppVersion}-Windows-Setup
SetupIconFile=icon.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; Flags: unchecked

[Files]
Source: "..\..\dist\{#AppName}\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExe}"; Description: "Open {#AppName} now"; Flags: nowait postinstall skipifsilent
