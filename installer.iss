; Inno Setup script for Tasker (Планнер).
; Requires Inno Setup 6+: https://jrsoftware.org/isdl.php
; NOTE: this file must be saved as UTF-8 with BOM for Cyrillic.
; build.bat handles the BOM conversion automatically.

#define MyAppName "Планнер"
#define MyAppVersion "0.1.0"
#define MyAppExeName "Tasker.exe"

[Setup]
AppId={{B8A5D3E1-7C4F-4A92-8E6B-2F1D9C5A3B7E}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\Tasker
DefaultGroupName={#MyAppName}
OutputDir=installer_output
OutputBaseFilename=Tasker_Setup
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "dist\Tasker\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#MyAppName}}"; Flags: nowait postinstall skipifsilent

[Code]
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  DataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    DataDir := ExpandConstant('{userappdata}\Tasker');
    if DirExists(DataDir) then
    begin
      if MsgBox('Удалить данные приложения (задачи и настройки)?',
                mbConfirmation, MB_YESNO or MB_DEFBUTTON2) = IDYES then
      begin
        DelTree(DataDir, True, True, True);
      end;
    end;
  end;
end;
