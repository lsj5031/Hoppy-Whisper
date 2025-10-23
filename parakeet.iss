; Inno Setup installer script for Parakeet
; This installer bundles the PyInstaller output and handles VC++ Redistributable silently

#define MyAppName "Parakeet"
#define MyAppVersion "0.1.0"
#define MyAppPublisher "Parakeet Contributors"
#define MyAppURL "https://github.com/parakeet-app/parakeet"
#define MyAppExeName "Parakeet.exe"
#define VCRedistUrl "https://aka.ms/vs/17/release/vc_redist.x64.exe"

[Setup]
AppId={{A1B2C3D4-E5F6-7890-ABCD-EF1234567890}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=LICENSE
OutputDir=installer
OutputBaseFilename=Parakeet-Setup-{#MyAppVersion}
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
SetupIconFile=src\app\tray\icon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\Parakeet\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
; Download and include VC++ Redistributable
Source: "{#VCRedistUrl}"; DestDir: "{tmp}"; Flags: deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Installing Visual C++ Redistributable..."; Flags: waituntilterminated runhidden
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName,'&','&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"

[Code]
function VCRedistNeedsInstall: Boolean;
var
    ErrorCode: Integer;
    bVCRedistNeeded: Boolean;
    sInstalledVersion: string;
begin
    // Check if VC++ 14.0 runtime is already installed
    sInstalledVersion := '';
    bVCRedistNeeded := RegQueryMultiStringValue(HKEY_LOCAL_MACHINE,
        'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64',
        'Version', sInstalledVersion);
    
    // If the registry key doesn't exist or version is too old, we need to install
    Result := not bVCRedistNeeded or (sInstalledVersion = '');
end;

function InitializeSetup: Boolean;
begin
    Result := True;
    // Always return True to continue installation
end;

function PrepareToInstall(Var NeedsRestart: Boolean): String;
begin
    Result := '';
    // Prepare VC++ redistributable installation check
    if VCRedistNeedsInstall then
    begin
        // We'll install it during the [Run] section
        // This is just a placeholder to indicate we need it
    end;
end;
