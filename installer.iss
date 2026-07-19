; Установщик ChatList.
; Номер версии НЕ хардкодится здесь — он подставляется из version.py
; через скрипт build.ps1 (файл version.iss).

#include "version.iss"

#ifndef MyAppVersion
  #error version.iss не содержит MyAppVersion. Запустите build.ps1
#endif

#define MyAppName "ChatList"
#define MyAppPublisher "ChatList"
#define MyAppExeName "ChatList.exe"

[Setup]
AppId={{A7E3C1B0-4D2F-4A91-9E6C-8B2F5D1A0C44}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=no
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=ChatList-Setup-{#MyAppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
UninstallDisplayName={#MyAppName} {#MyAppVersion}
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallFilesDir={app}
CreateUninstallRegKey=yes
Uninstallable=yes

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Удалить {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: files; Name: "{app}\*.log"
Type: files; Name: "{app}\*.db"
Type: files; Name: "{app}\.env"
Type: files; Name: "{app}\.env.local"
Type: dirifempty; Name: "{app}"
