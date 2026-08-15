; ===========================================================================
;  Inno Setup script for "YT Downloader" – installer version
; ===========================================================================
;  The portable .exe already contains everything needed:
;    - Python runtime + yt-dlp
;    - ffmpeg.exe (for MP3 conversion)
;  The installer simply packages that .exe with shortcuts + uninstaller.
;
;  Prerequisites:
;    1. Install Inno Setup (free): https://jrsoftware.org/isdl.php
;    2. Build the portable exe first:
;         .\build\build_portable.bat   (or build_all.bat for both)
;    3. Compile this script:
;         iscc build\installer.iss
; ===========================================================================

#define MyAppName        "YT Downloader"
#define MyAppVersion     "2.2.0"
#define MyAppPublisher   "YT Downloader"
#define MyAppExeName     "YT_Downloader.exe"
#define MyAppURL         "https://github.com/yt-dlp/yt-dlp"

; Project root = one level up from this .iss file (which lives in build/).
; Inno Setup resolves relative paths from the .iss location, so we build
; absolute paths from SourcePath to reach the dist/ and assets/ folders.
#define ProjectRoot      SourcePath + "\.."

[Setup]
; Unique app ID – do NOT change after publishing updates
AppId={{8F2A7B3C-4D5E-6F70-8192-3A4B5C6D7E8F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir={#ProjectRoot}\dist
OutputBaseFilename=YT_Downloader_Installer
Compression=lzma2/ultra
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64os
ArchitecturesAllowed=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

; Optional: include an icon for the installer/uninstaller
; Uncomment the next line if you have assets\app_icon.ico
;SetupIconFile={#ProjectRoot}\assets\app_icon.ico

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
; The portable exe built by PyInstaller — already contains ffmpeg.exe,
; Python runtime, and yt-dlp bundled inside. No additional files needed.
Source: "{#ProjectRoot}\dist\YT_Downloader.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\dist\native_host.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#ProjectRoot}\tools\native_messaging\com.yt_downloader.host.json"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
; Start Menu shortcut
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
; Start Menu uninstall shortcut
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"

; Optional Desktop shortcut (only if user checks the box)
Name: "{commondesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
; Offer to launch the app after install
Filename: "{app}\{#MyAppExeName}"; Description: "Launch {#MyAppName}"; Flags: nowait postinstall skipifsilent
; Native Messaging host registration for Chrome and Edge.
; The manifest file is installed in the app folder and both browser registries
; point to it. This requires administrator privileges.

[UninstallDelete]
; Clean up the Downloads folder created by the app (only if empty)
Type: dirifempty; Name: "{app}\Downloads"

[UninstallRun]
; Unregister custom protocol when uninstalling
; Remove native messaging host registry key when uninstalling
; (HKLM) - requires admin during uninstall
; We can't delete the manifest file until after the registry key is removed, so leave file deletion to UninstallDelete/Files
;

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
end;

[Registry]
; Register native messaging host manifest path for Chrome (system-wide)
Root: HKLM; Subkey: "Software\Google\Chrome\NativeMessagingHosts\com.yt_downloader.host"; ValueType: string; ValueName: ""; ValueData: "{app}\\com.yt_downloader.host.json"; Flags: uninsdeletevalue
; Register native messaging host manifest path for Microsoft Edge (system-wide)
Root: HKLM; Subkey: "Software\Microsoft\Edge\NativeMessagingHosts\com.yt_downloader.host"; ValueType: string; ValueName: ""; ValueData: "{app}\\com.yt_downloader.host.json"; Flags: uninsdeletevalue

[UninstallRun]
; Remove the registry entries on uninstall
Filename: "reg"; Parameters: "delete ""HKLM\Software\Google\Chrome\NativeMessagingHosts\com.yt_downloader.host"" /f"; Flags: runhidden
Filename: "reg"; Parameters: "delete ""HKLM\Software\Microsoft\Edge\NativeMessagingHosts\com.yt_downloader.host"" /f"; Flags: runhidden
