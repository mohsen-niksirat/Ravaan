; Inno Setup 6 Script for Ravaan (روان)
; Produces a per-user, non-admin installer with optional startup, desktop icon, and ravan:// protocol handler.
; Leaves %APPDATA%\Ravan intact upon uninstall to preserve user dictionaries and settings.

#ifndef MyAppVersion
#define MyAppVersion "1.0.0"
#endif

#define MyAppName "Ravaan"
#define MyAppPublisher "Mohsen Niksirat"
#define MyAppURL "https://github.com/mohsen-niksirat/Ravaan"
#define MyAppExeName "Ravaan.exe"

[Setup]
AppId={{C4E9C0A7-62F1-4F2B-933B-8C477614AA51}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}/releases
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Ravaan-Setup-{#MyAppVersion}
SetupIconFile=..\ravan\data\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
CloseApplications=force

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "Launch Ravaan at Windows startup"; GroupDescription: "Windows Integration:"
Name: "registerprotocol"; Description: "Register ravan:// URL protocol handler"; GroupDescription: "Windows Integration:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: startup

[Registry]
Root: HKCU; Subkey: "Software\Classes\ravan"; ValueType: string; ValueName: ""; ValueData: "URL:Ravaan Protocol"; Flags: uninsdeletekey; Tasks: registerprotocol
Root: HKCU; Subkey: "Software\Classes\ravan"; ValueType: string; ValueName: "URL Protocol"; ValueData: ""; Flags: uninsdeletekey; Tasks: registerprotocol
Root: HKCU; Subkey: "Software\Classes\ravan\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"; Flags: uninsdeletekey; Tasks: registerprotocol
Root: HKCU; Subkey: "Software\Classes\ravan\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey; Tasks: registerprotocol

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
