#!/bin/bash
# Les captures de la fiche F-Droid (fastlane/metadata/android/<langue>/images/phoneScreenshots), UNE LANGUE À LA FOIS,
# sur le téléphone virtuel (workflow .github/workflows/vitrine.yml), puis quelques captures des nouveautés.
#   MODE=telephone LANGUES="fr en" bash tests/vitrine.sh   → captures/vitrine_<langue>/*.png
#   MODE=nouveautes bash tests/vitrine.sh                   → captures/nouveautes/*.png (idées 74 et 76)
#   MODE=carte bash tests/vitrine.sh                       → captures/carte/*.png (idée 76 seule : la carte ouverte)
#   MODE=tablette bash tests/vitrine.sh                     → captures/tablette/*.png (idée 75 : deux colonnes en paysage)
# On choisit ensuite les 4 meilleures de chaque langue (les mêmes écrans dans chaque langue) : voir docs/fdroid.md.
set -u
MODE=${MODE:-telephone}
LANGUES=${LANGUES:-fr en}
APK=app/build/outputs/apk/release/app-release.apk
PAQ=fr.terminagotchi
NON=non
mkdir -p captures
node --no-warnings site/test/serveur.mjs > captures/serveur.log 2>&1 &
sleep 3
adb install -r "$APK"
adb shell pm grant $PAQ android.permission.POST_NOTIFICATIONS || true
adb shell settings put global window_animation_scale 0 || true
D=captures
capture() { sleep "${2:-2}"; adb exec-out screencap -p > "$D/$1.png"; }
saisie() {
  adb shell uiautomator dump /sdcard/tg_ui.xml >/dev/null 2>&1
  adb exec-out cat /sdcard/tg_ui.xml 2>/dev/null | python3 -c '
import re, sys
x = sys.stdin.read()
m = re.search(r"<node [^>]*resource-id=\"fr.terminagotchi:id/saisie\"[^>]*>", x)
if not m:
    print("absent"); sys.exit()
n = m.group(0)
def g(k):
    r = re.search(k + r"=\"([^\"]*)\"", n)
    return r.group(1) if r else ""
t, h = g("text"), g("hint")
vide = t == "" or t == h or t.endswith("…")
print("pret" if g("focused") == "true" and vide else "occupe")'
}
# (au plus quelques secondes : le téléphone virtuel ne dit pas toujours « prêt », et attendre 25 s à chaque commande
#  faisait durer la vitrine des heures ; la première fois, on garde l'écran lu pour comprendre)
attendre_pret() {
  for i in $(seq 1 "${1:-6}"); do [ "$(saisie)" = pret ] && return 0; sleep 1; done
  [ -f "$D/pas_pret.xml" ] || adb exec-out cat /sdcard/tg_ui.xml > "$D/pas_pret.xml" 2>/dev/null
  echo "(saisie pas prête)"
}
tape() {
  local t="${1// /%s}"
  attendre_pret
  [ -n "$t" ] && adb shell "input text '$t'"
  sleep 1
  adb shell input keyevent 66
  sleep "${2:-3}"
}
sans_clavier() {   # Retour range le clavier de l'écran (seulement s'il est ouvert : sinon Retour fermerait le jeu)
  adb shell dumpsys input_method | grep -q "mInputShown=true" && adb shell input keyevent 4
  sleep 2
}
avec_clavier() { adb shell input tap 540 2200 >/dev/null 2>&1; sleep 1; }
# Le jeu, du début, dans la langue L (la langue de l'appli, comme si le téléphone était dans cette langue)
debut() {   # $1 : langue (fr, en…), $2 : « oui » dans cette langue
  adb shell am force-stop $PAQ
  adb shell pm clear $PAQ
  adb shell pm grant $PAQ android.permission.POST_NOTIFICATIONS || true
  adb shell cmd locale set-app-locales $PAQ --user 0 --locales "$1" || true
  adb shell am start -n $PAQ/.TerminalActivity
  capture ecran_0 12
  for i in 1 2 3 4 5 6; do tape "" 3; capture "ecran_$i" 1; done
  for essai in 1 2 3; do
    tape "Pixel" 6
    [ "$essai" = 1 ] && capture bapteme 1
    tape "$2" 8
    attendre_pret 10
    adb shell uiautomator dump /sdcard/tg_ui.xml >/dev/null 2>&1
    adb exec-out cat /sdcard/tg_ui.xml | grep -o 'text="Pixel[^"]*" resource-id="fr.terminagotchi:id/titre"' | grep -q Pixel && break
    for i in 1 2 3; do tape "" 3; done
  done
  tape "langue $1" 2
}

# idée 76 : `bug`, puis la réponse des grands LUE à l'écran et calculée (pas devinée), puis la carte du rapport.
# Le texte du terminal (id/sortie) est un TextView ordinaire, mais quand le clavier de l'écran est ouvert, la leçon
# et le clavier lui prennent toute la place : il est alors invisible et uiautomator ne le donne pas. On range donc
# le clavier avant de lire la question, puis on le rouvre pour taper la réponse.
lire_question() {   # $1 : fichier où garder l'écran lu ; écrit le résultat de la multiplication (ou rien)
  adb shell rm -f /sdcard/tg_ui.xml
  adb shell uiautomator dump /sdcard/tg_ui.xml >/dev/null 2>&1
  adb exec-out cat /sdcard/tg_ui.xml > "$1" 2>/dev/null
  python3 - "$1" <<'PY'
import re, sys
import xml.etree.ElementTree as ET
try:
    noeuds = [n.get("text", "") for n in ET.parse(sys.argv[1]).iter("node")
              if n.get("resource-id") == "fr.terminagotchi:id/sortie"]
except Exception:
    noeuds = []
q = re.findall(r"(\d+)\s*×\s*(\d+)", noeuds[-1] if noeuds else "")
print(int(q[-1][0]) * int(q[-1][1]) if q else "")
PY
}
carte_ouverte() {
  adb shell rm -f /sdcard/tg_ui.xml; adb shell uiautomator dump /sdcard/tg_ui.xml >/dev/null 2>&1
  adb exec-out cat /sdcard/tg_ui.xml 2>/dev/null > "$D/76_apres.xml"
  grep -q "Ouvrir la page" "$D/76_apres.xml"
}
ouvrir_carte() {
  carte=non
  for essai in 1 2 3 4 5; do
    tape "bug" 3
    [ "$essai" = 1 ] && capture 76_question 1
    Q=$(lire_question "$D/76_ecran_${essai}_clavier.xml")
    if [ -z "$Q" ]; then
      sans_clavier
      [ "$essai" = 1 ] && capture 76_question_sans_clavier 1
      Q=$(lire_question "$D/76_ecran_${essai}.xml")
      avec_clavier
    fi
    echo "essai $essai : réponse des grands lue à l'écran : « $Q »"
    tape "${Q:-0}" 4                 # (rien lu : « 0 », pour que la question suivante reparte de zéro)
    if [ -n "$Q" ] && carte_ouverte; then carte=oui; break; fi
    sans_clavier; capture "76_rate_$essai" 1; avec_clavier
  done
  echo "carte du rapport : $carte"
  echo "$carte" > "$D/76_carte_ouverte.txt"
}

if [ "$MODE" = telephone ]; then
  for L in $LANGUES; do
    D=captures/vitrine_$L; mkdir -p $D
    OUI=$([ "$L" = fr ] && echo oui || echo yes); NON=$([ "$L" = fr ] && echo non || echo no)
    debut "$L" "$OUI"
    tape "ls" 4
    for c in "pwd" "echo bonjour" "whoami"; do tape "$c" 2; done
  tape "$NON" 3                                 # « Tu veux m'entendre ? » (le son, à l'éclosion) : non
    capture eclosion 2
    tape "debloquer tout"; tape "$OUI"
    for c in "cd" "mkdir terrain_terminagotchi" "cd terrain_terminagotchi" "mkdir nid" "echo pomme > nid/repas.txt" "cat nid/repas.txt"; do tape "$c"; done
    capture nid 2
    sans_clavier; capture nid_sans_clavier 1; avec_clavier
    tape "joue pierre" 3; capture jeux 1
    tape "collection" 3; capture collection 1
    adb shell am start -n $PAQ/.TerminalActivity --es essai_dressage abyssor
    capture rencontre 6
    sans_clavier; capture rencontre_sans_clavier 1; avec_clavier
    tape "dressage abandon"
    adb shell am start -n $PAQ/.TerminalActivity --es essai_equipe abyssor:adulte
    sleep 5
    tape "troupe" 3; capture troupe 1
    tape "espace" 6; capture espace 2
    sans_clavier; capture espace_sans_clavier 1; avec_clavier
    tape "espace" 4
    tape "donjon" 4; capture donjon 1
    tape "plan" 3; capture plan 1
  done
elif [ "$MODE" = nouveautes ]; then
  # ---- les nouveautés (idées 74 et 76), en français
  D=captures/nouveautes; mkdir -p $D
  debut fr oui
  tape "ls" 4
  for c in "pwd" "echo bonjour" "whoami"; do tape "$c" 2; done
  tape "$NON" 3                                 # « Tu veux m'entendre ? » (le son, à l'éclosion) : non
  tape "debloquer tout"; tape "oui"
  tape "compte serveur http://10.0.2.2:8787"
  tape "compte creer VitrineCI" 8
  capture compte_cree 1
  tape "compte serveur http://10.0.2.2:9"       # plus de site : comme sans Internet
  tape "pwd"; tape "ls"; tape "sync" 12
  capture 74_hors_ligne 1
  adb shell uiautomator dump /sdcard/tg_ui.xml >/dev/null 2>&1
  adb exec-out cat /sdcard/tg_ui.xml | grep -o 'resource-id="fr.terminagotchi:id/chemin"[^>]*bounds="[^"]*"' > $D/chemin.txt
  B=$(grep -o 'bounds="\[[0-9]*,[0-9]*\]\[[0-9]*,[0-9]*\]"' $D/chemin.txt | grep -o '[0-9]\+' | tr '\n' ' ')
  set -- $B
  [ $# -ge 4 ] && adb shell input tap $(( $3 - 60 )) $(( ($2 + $4) / 2 ))     # toucher le nuage : il s'explique
  capture 74_explique 2
  tape "compte" 3; capture 74_compte 1
  ouvrir_carte
  capture 76_carte 1
  sans_clavier; capture 76_carte_sans_clavier 1
  adb shell am force-stop $PAQ
elif [ "$MODE" = carte ]; then
  # ---- seulement la carte « Signaler un souci » (idée 76) : la question des grands lue, la bonne réponse, la carte
  D=captures/carte; mkdir -p $D
  debut fr oui
  tape "ls" 4
  for c in "pwd" "echo bonjour" "whoami"; do tape "$c" 2; done
  tape "$NON" 3                                 # « Tu veux m'entendre ? » (le son, à l'éclosion) : non
  tape "debloquer tout"; tape "oui"
  ouvrir_carte
  capture 76_carte 1
  sans_clavier; capture 76_carte_sans_clavier 1
  adb shell am force-stop $PAQ
else
  # ---- tablette (idée 75) : portrait (une colonne, comme un téléphone), puis paysage (deux colonnes)
  D=captures/tablette; mkdir -p $D
  adb shell settings put system accelerometer_rotation 0
  adb shell settings put system user_rotation 0
  debut fr oui
  tape "ls" 4
  for c in "pwd" "echo bonjour" "whoami"; do tape "$c" 2; done
  tape "$NON" 3                                 # « Tu veux m'entendre ? » (le son, à l'éclosion) : non
  tape "debloquer tout"; tape "oui"
  for c in "cd" "mkdir terrain_terminagotchi" "cd terrain_terminagotchi" "mkdir nid" "cd nid" "echo pomme > repas.txt" "ls -l" "cat repas.txt"; do tape "$c"; done
  capture tablette_0 3
  adb shell settings put system user_rotation 1
  capture tablette_1 6
  tape "grep pomme repas.txt"; tape "ls"
  capture tablette_1_commandes 2
  adb shell settings put system user_rotation 0
  capture tablette_2 6
  adb shell settings put system user_rotation 1
  capture tablette_3 6
  adb shell wm size > $D/taille.txt; adb shell wm density >> $D/taille.txt
fi
adb logcat -d > captures/logcat_$MODE.txt
if grep -q "FATAL EXCEPTION" captures/logcat_$MODE.txt; then
  grep -A 25 "FATAL EXCEPTION" captures/logcat_$MODE.txt > captures/PLANTAGE_$MODE.txt
  echo "PLANTAGE DÉTECTÉ"; cat captures/PLANTAGE_$MODE.txt
fi
find captures -name "*.png" | sort
