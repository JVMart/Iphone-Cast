; Iphone-Cast installer — Inno Setup 6 script.
;
; Per-user install to %LocalAppData%\Iphone-Cast\. Three wizard languages
; (English / Spanish / French); the choice is seeded into settings.json so
; the app launches in the same language on first run.
;
; Built by installer\build.ps1, which stages the bundle into installer\staging\
; first.

#define AppName       "Iphone-Cast"
#define AppVersion    "1.0.0"
#define AppPublisher  "JVMart"
#define AppRepoUrl    "https://github.com/JVMart/Iphone-Cast"

[Setup]
AppId={{B4F8A1D7-3C92-4E5A-9B6F-1A8C5D2E7F4A}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppRepoUrl}
AppSupportURL={#AppRepoUrl}/issues
AppUpdatesURL={#AppRepoUrl}/releases
DefaultDirName={localappdata}\{#AppName}
DefaultGroupName={#AppName}
DisableDirPage=auto
DisableProgramGroupPage=auto
PrivilegesRequired=lowest
LicenseFile=..\LICENSE
OutputDir=output
OutputBaseFilename=Iphone-Cast-Setup-{#AppVersion}
SetupIconFile=..\Iphone-Cast.ico
UninstallDisplayIcon={app}\Iphone-Cast.exe
WizardStyle=modern
Compression=lzma2/ultra
SolidCompression=yes
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "staging\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\Iphone-Cast.exe"; WorkingDir: "{app}"; IconFilename: "{app}\Iphone-Cast.exe"
Name: "{group}\{cm:UninstallProgram,{#AppName}}"; Filename: "{uninstallexe}"
Name: "{userdesktop}\{#AppName}";     Filename: "{app}\Iphone-Cast.exe"; WorkingDir: "{app}"; IconFilename: "{app}\Iphone-Cast.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\Iphone-Cast.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; Wipe the per-user settings dir on uninstall (the install dir IS that dir
; in the default case, so this is mostly redundant; covers the case where
; the user picked a non-default install dir).
Type: filesandordirs; Name: "{localappdata}\{#AppName}"

[CustomMessages]
; ----- Bonjour-missing notice on the Finished page -----
en.BonjourMissing=Note: Iphone-Cast needs Apple's Bonjour service to advertise on your network. If 'PC-Cast' does not appear on your iPhone, install Bonjour Print Services for Windows from Apple:%n%nhttps://support.apple.com/downloads
es.BonjourMissing=Nota: Iphone-Cast necesita el servicio Bonjour de Apple para anunciarse en la red. Si 'PC-Cast' no aparece en el iPhone, instala Bonjour Print Services para Windows desde Apple:%n%nhttps://support.apple.com/downloads
fr.BonjourMissing=Note : Iphone-Cast a besoin du service Bonjour d'Apple pour s'annoncer sur le reseau. Si 'PC-Cast' n'apparait pas sur l'iPhone, installez Bonjour Print Services pour Windows depuis Apple :%n%nhttps://support.apple.com/downloads

[Code]
procedure WriteLanguageSeed();
var
  SettingsDir, SettingsPath, LangCode, Content: String;
begin
  LangCode := ActiveLanguage();
  SettingsDir := ExpandConstant('{localappdata}\{#AppName}');
  SettingsPath := SettingsDir + '\settings.json';
  ForceDirectories(SettingsDir);
  Content := '{' + #13#10 + '  "language": "' + LangCode + '"' + #13#10 + '}' + #13#10;
  if not SaveStringToFile(SettingsPath, Content, False) then
    MsgBox('Could not write settings.json to ' + SettingsPath, mbError, MB_OK);
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
    WriteLanguageSeed();
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then begin
    if not FileExists('C:\Program Files\Bonjour\mDNSResponder.exe') then
      WizardForm.FinishedLabel.Caption :=
        WizardForm.FinishedLabel.Caption + #13#10#13#10 +
        ExpandConstant('{cm:BonjourMissing}');
  end;
end;
