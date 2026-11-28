; Installeur Windows de Terminagotchi (idée 71, 3 novembre 2026), fabriqué par la CI (.github/workflows/apk-essai.yml,
; tâche « installeur-windows ») à partir du code du dépôt :
;   - le jeu PC (terminagotchi.pyz, fabriqué avec python -m zipapp pc, comme pour Linux) ;
;   - Python officiel (python.org, celui que la CI utilise déjà pour tester le jeu sous Windows), recopié tel quel dans
;     le dossier du jeu : rien d'autre à installer, rien n'est téléchargé à l'installation ni pendant le jeu.
; Installation pour la personne connectée seulement (pas besoin d'être administrateur, pas de fenêtre « Autoriser cette
; application à apporter des modifications ? »), dans %LOCALAPPDATA%\Programs\Terminagotchi ; un raccourci dans le menu
; Démarrer (et, si on coche, sur le bureau). Désinstaller enlève le jeu mais JAMAIS la créature : la sauvegarde est
; dans %USERPROFILE%\.terminagotchi et le terrain dans %USERPROFILE%\terrain_terminagotchi, que l'installeur ne touche pas.
; Réinstaller par-dessus répare les fichiers du jeu (voir pc/tg/sante.py : « un adulte peut réinstaller le jeu »).
; Pas de signature payante : Windows SmartScreen affichera « Windows a protégé votre ordinateur » au premier lancement
; (voir README, « Sous Windows »).
;
; Compiler : iscc /DVersion=0.1.N /DSource=<dossier préparé> terminagotchi.iss

#ifndef Version
  #define Version "0.0.0"
#endif
#ifndef Source
  #define Source "build"
#endif

[Setup]
AppId={{6F1D4C9A-7B2E-4E57-9C3A-2D8B5F0E1A43}
AppName=Terminagotchi
AppVersion={#Version}
AppVerName=Terminagotchi {#Version}
AppPublisher=Terminagotchi (projet libre)
AppPublisherURL=https://github.com/grecdel/terminagotchi
AppSupportURL=https://github.com/grecdel/terminagotchi/issues
DefaultDirName={autopf}\Terminagotchi
DefaultGroupName=Terminagotchi
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=
OutputDir=sortie
OutputBaseFilename=terminagotchi-installeur
SetupIconFile={#Source}\terminagotchi.ico
UninstallDisplayIcon={app}\terminagotchi.ico
UninstallDisplayName=Terminagotchi
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ShowLanguageDialog=auto
LicenseFile={#Source}\LICENSE.txt
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "fr"; MessagesFile: "compiler:Languages\French.isl"
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "de"; MessagesFile: "compiler:Languages\German.isl"
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"
Name: "it"; MessagesFile: "compiler:Languages\Italian.isl"
Name: "pt"; MessagesFile: "compiler:Languages\Portuguese.isl"
Name: "ru"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "ja"; MessagesFile: "compiler:Languages\Japanese.isl"

[Tasks]
Name: "bureau"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"

[Files]
Source: "{#Source}\terminagotchi.pyz"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Source}\terminagotchi.ico"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Source}\LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion
Source: "{#Source}\LISEZMOI.txt"; DestDir: "{app}"; Flags: ignoreversion isreadme
Source: "{#Source}\python\*"; DestDir: "{app}\python"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\Terminagotchi"; Filename: "{app}\python\python.exe"; Parameters: """{app}\terminagotchi.pyz"""; WorkingDir: "{%USERPROFILE}"; IconFilename: "{app}\terminagotchi.ico"
Name: "{group}\{cm:UninstallProgram,Terminagotchi}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\Terminagotchi"; Filename: "{app}\python\python.exe"; Parameters: """{app}\terminagotchi.pyz"""; WorkingDir: "{%USERPROFILE}"; IconFilename: "{app}\terminagotchi.ico"; Tasks: bureau

[Run]
Filename: "{app}\python\python.exe"; Parameters: """{app}\terminagotchi.pyz"""; WorkingDir: "{%USERPROFILE}"; Description: "{cm:LaunchProgram,Terminagotchi}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
; seulement ce que Python a pu ranger dans le dossier du jeu (fichiers .pyc) : jamais la sauvegarde ni le terrain
Type: filesandordirs; Name: "{app}\python\Lib\__pycache__"
