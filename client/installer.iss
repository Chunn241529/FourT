; FourT Helper Installer Script for Inno Setup
; Download Inno Setup from: https://jrsoftware.org/isdl.php

#define MyAppName "FourT"
#define MyAppVersion "0.0.2"
#define MyAppPublisher "FourT Studio"
#define MyAppURL "https://fourt.io.vn"
#define MyAppExeName "FourT.exe"

[Setup]
; NOTE: AppId should be unique for your app
AppId={{B8F73E91-4D2C-4F7A-9C3E-1A2B3C4D5E6F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={localappdata}\{#MyAppName}
DisableDirPage=no
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Output settings - use simple filename for auto-update
OutputDir=dist
OutputBaseFilename=FourT_Setup
SetupIconFile=favicon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
; Allow install without admin - app will request UAC when running
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
; Architecture
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
; Close running app during install (for auto-update)
CloseApplications=force
CloseApplicationsFilter=*.exe
RestartApplications=yes
; Prevent multiple installer instances
AppMutex=FourTHelperSetupMutex

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Copy all files from dist\FourT folder
Source: "dist\FourT\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
; Run app after install without elevation requirement
; Use shellexec to avoid "requires elevation" error
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent shellexec
Filename: "{app}\{#MyAppExeName}"; Flags: nowait skipifnotsilent shellexec

[UninstallDelete]
; Clean up user data on uninstall (optional - comment out to keep user data)
; Type: filesandordirs; Name: "{localappdata}\FourT"

[Code]
// Custom Pascal code for installer

// Note: CloseApplications=force handles closing running apps automatically
// No need for manual process detection - it was causing false positives

// Run on install complete  
procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    // Any post-install tasks
  end;
end;






























































