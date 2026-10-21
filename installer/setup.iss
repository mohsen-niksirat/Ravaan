; Inno Setup 6 Script for Ravaan (روان)
; Produces a per-user, non-admin installer with optional startup, desktop icon, and ravan:// protocol handler.
; Preserves %APPDATA%\Ravaan upon upgrade.
; Prompts the user upon uninstall with an optional clean data removal choice.

#ifndef MyAppVersion
#define MyAppVersion "2.0.0"
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

[CustomMessages]
english.LaunchStartup=Launch Ravaan at Windows startup
english.RegisterProtocol=Register ravan:// URL protocol handler
english.DeleteDataPrompt=Do you also want to permanently delete your personal settings, custom snippets, and learned vocabulary?%n%nآیا می‌خواهید تمام تنظیمات، کلمات اختصاری و واژگان یادگرفته‌شده نیز از سیستم حذف شوند؟

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "startup"; Description: "{cm:LaunchStartup}"; GroupDescription: "Windows Integration:"
Name: "registerprotocol"; Description: "{cm:RegisterProtocol}"; GroupDescription: "Windows Integration:"

[Files]
Source: "..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
Source: "..\README.fa.md"; DestDir: "{app}"; Flags: ignoreversion skipifsourcedoesntexist
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

[Code]
// Clean uninstall option: prompt user if they also wish to delete %APPDATA%\Ravaan
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: string;
begin
  if CurUninstallStep = usUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\Ravaan');
    if DirExists(DataDir) then
    begin
      if MsgBox(CustomMessage('DeleteDataPrompt'), mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      begin
        DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;
