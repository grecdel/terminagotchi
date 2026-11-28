#!/bin/sh
# Cyberdeck Terminagotchi (idée 80) : le petit Linux portable démarre directement sur le jeu.
# Voir docs/oeuf/cyberdeck.md, § « Démarrer sur le jeu ». Le matériel viendra plus tard : ce script marche déjà sur
# n'importe quel Linux (essai sur un vieux portable, une machine virtuelle…).
#
#   sh installer.sh terminagotchi.pyz           installe le jeu pour CE compte et le lance à l'ouverture de session
#   sh installer.sh terminagotchi.pyz --bureau  en plus : au démarrage d'un bureau graphique, un terminal plein écran
#   sh installer.sh --retirer                   enlève tout ce que ce script a ajouté (la créature reste)
#
# À lancer DANS LE COMPTE DE L'ENFANT, sans sudo : le script n'écrit que dans son dossier personnel
#   ~/.local/share/terminagotchi/   le jeu (terminagotchi.pyz) et le petit lanceur plein écran
#   ~/.local/bin/terminagotchi      la commande « terminagotchi »
#   ~/.bash_profile ou ~/.profile   un bloc entre deux repères (# >>> terminagotchi cyberdeck >>>) : à la connexion
#                                   sur la console tty1 (celle où le cyberdeck s'ouvre), le jeu se lance ; quand on le
#                                   quitte, on reste dans le vrai shell (`terminagotchi` ou `tg` pour y revenir)
#   ~/.config/autostart/terminagotchi.desktop   seulement avec --bureau
# La sauvegarde de la créature (~/.terminagotchi) et le terrain (~/terrain_terminagotchi) ne sont jamais touchés.
# Ce qui demande un adulte et sudo (connexion automatique, compte sans droits, police plus grosse, clapet) est expliqué
# dans docs/oeuf/cyberdeck.md : ce script ne le fait pas.
set -eu

DEBUT="# >>> terminagotchi cyberdeck >>>"
FIN="# <<< terminagotchi cyberdeck <<<"
JEU="$HOME/.local/share/terminagotchi"
BIN="$HOME/.local/bin"
AUTO="$HOME/.config/autostart/terminagotchi.desktop"

dit() { printf '%s\n' "$*"; }

profil() {   # le fichier lu par le shell de connexion
  if [ -f "$HOME/.bash_profile" ]; then echo "$HOME/.bash_profile"
  elif [ -f "$HOME/.bash_login" ]; then echo "$HOME/.bash_login"
  else echo "$HOME/.profile"; fi
}

retirer_bloc() {
  f="$1"
  [ -f "$f" ] || return 0
  if grep -qF "$DEBUT" "$f"; then
    awk -v d="$DEBUT" -v f="$FIN" '$0 == d {saute = 1; next} $0 == f {saute = 0; next} !saute' "$f" > "$f.tg-tmp"
    cat "$f.tg-tmp" > "$f" && rm -f "$f.tg-tmp"
  fi
}

if [ "${1:-}" = "--retirer" ]; then
  for f in "$HOME/.bash_profile" "$HOME/.bash_login" "$HOME/.profile"; do retirer_bloc "$f"; done
  rm -f "$AUTO" "$BIN/terminagotchi" "$JEU/terminagotchi.pyz" "$JEU/plein-ecran.sh"
  rmdir "$JEU" 2>/dev/null || true
  dit "Retiré : le jeu ne se lance plus au démarrage. La créature (~/.terminagotchi) est toujours là."
  exit 0
fi

PYZ="${1:-}"
if [ -z "$PYZ" ] || [ ! -f "$PYZ" ]; then
  dit "Utilisation : sh installer.sh terminagotchi.pyz [--bureau]   (ou --retirer)"
  exit 2
fi
if [ "$(id -u)" = 0 ]; then
  dit "Lance ce script dans le compte de l'enfant, pas en administrateur (pas de sudo) : il n'écrit que chez lui."
  exit 2
fi
command -v python3 >/dev/null 2>&1 || { dit "python3 manque : un adulte l'installe une fois (sudo apt install python3)."; exit 2; }

mkdir -p "$JEU" "$BIN"
cp "$PYZ" "$JEU/terminagotchi.pyz.tmp" && mv "$JEU/terminagotchi.pyz.tmp" "$JEU/terminagotchi.pyz"
cat > "$BIN/terminagotchi" <<'LANCEUR'
#!/bin/sh
exec python3 "$HOME/.local/share/terminagotchi/terminagotchi.pyz" "$@"
LANCEUR
chmod 755 "$BIN/terminagotchi"

P=$(profil)
retirer_bloc "$P"
cat >> "$P" <<BLOC
$DEBUT
# Le cyberdeck démarre sur le jeu (installeur/cyberdeck/installer.sh ; pour l'enlever : sh installer.sh --retirer).
case ":\$PATH:" in *":\$HOME/.local/bin:"*) ;; *) PATH="\$HOME/.local/bin:\$PATH"; export PATH ;; esac
if [ -z "\${TG_DANS_LE_JEU:-}" ] && [ "\$(tty 2>/dev/null)" = "\${TG_CYBERDECK_TTY:-/dev/tty1}" ] && [ -f "\$HOME/.local/share/terminagotchi/terminagotchi.pyz" ]; then
  TG_DANS_LE_JEU=1; export TG_DANS_LE_JEU
  python3 "\$HOME/.local/share/terminagotchi/terminagotchi.pyz"
  echo "Tu es dans le vrai terminal de ton cyberdeck. Pour revenir au jeu : terminagotchi"
fi
$FIN
BLOC

if [ "${2:-}" = "--bureau" ]; then
  cat > "$JEU/plein-ecran.sh" <<'PLEIN'
#!/bin/sh
# Un terminal plein écran avec le jeu (le premier terminal trouvé sur la machine).
J="python3 $HOME/.local/share/terminagotchi/terminagotchi.pyz"
TG_DANS_LE_JEU=1; export TG_DANS_LE_JEU
for t in foot kitty xfce4-terminal gnome-terminal konsole lxterminal xterm; do
  command -v "$t" >/dev/null 2>&1 || continue
  case "$t" in
    foot) exec foot --fullscreen sh -c "$J; exec \$SHELL" ;;
    kitty) exec kitty --start-as=fullscreen sh -c "$J; exec \$SHELL" ;;
    xfce4-terminal) exec xfce4-terminal --fullscreen -x sh -c "$J; exec \$SHELL" ;;
    gnome-terminal) exec gnome-terminal --full-screen -- sh -c "$J; exec \$SHELL" ;;
    konsole) exec konsole --fullscreen -e sh -c "$J; exec \$SHELL" ;;
    lxterminal) exec lxterminal -e sh -c "$J; exec \$SHELL" ;;
    xterm) exec xterm -fullscreen -fa Monospace -fs 14 -e sh -c "$J; exec \$SHELL" ;;
  esac
done
PLEIN
  chmod 755 "$JEU/plein-ecran.sh"
  mkdir -p "$(dirname "$AUTO")"
  cat > "$AUTO" <<DESK
[Desktop Entry]
Type=Application
Name=Terminagotchi
Comment=Le jeu au démarrage du cyberdeck
Exec=$JEU/plein-ecran.sh
Terminal=false
X-GNOME-Autostart-enabled=true
DESK
fi

dit "C'est prêt : à la prochaine connexion sur la console (tty1), le jeu se lance tout seul."
dit "  le jeu : $JEU/terminagotchi.pyz   la commande : terminagotchi   le réglage : $P"
[ "${2:-}" = "--bureau" ] && dit "  bureau graphique : $AUTO"
dit "Pour tout enlever : sh installer.sh --retirer   (la créature reste)"
