#!/bin/bash
# Partie automatique sur un téléphone virtuel : on tape de vraies commandes et on prend des captures.
set -u
mkdir -p captures
APK=app/build/outputs/apk/release/app-release.apk
adb install -r "$APK"
adb shell pm grant fr.terminagotchi android.permission.POST_NOTIFICATIONS || true
adb logcat -c
n=0
capture() { n=$((n+1)); sleep "${2:-2}"; adb exec-out screencap -p > "captures/$(printf %02d $n)_$1.png"; }
tape() {   # tape une commande lettre par lettre puis Entrée
  local t="${1// /%s}"
  adb shell "input text '$t'"
  sleep 0.5
  adb shell input keyevent 66
  sleep "${2:-1.5}"
}
adb shell am start -n fr.terminagotchi/.TerminalActivity
capture debut 5
tape "Pixel" 2
capture bapteme
for c in "pwd" "ls" "cd" "mkdir terrain_terminagotchi" "cd terrain_terminagotchi" "mkdir nid"; do tape "$c"; done
capture nid
tape "echo pomme > nid/repas.txt"; tape "cat nid/repas.txt"; tape "grep pomme nid/repas.txt"
tape "ls -l nid"; tape "chmod 444 nid/repas.txt"; tape "echo poire >> nid/repas.txt"
tape "cp nid/repas.txt nid/secours.txt"; tape "mv nid/secours.txt reserve.txt"; tape "rm reserve.txt" 3
capture tronc_fini
tape "arbre"
capture arbre
tape "cherche supprimer un dossier"
capture recherche
tape "fichier_inexistant"
capture erreur_expliquee
tape "joue pierre"; tape "devine 10"
capture jeux_creature
tape "collection"
capture collection
tape "donjon" 3
capture donjon
tape "plan"
capture plan
tape "ctf" 3
tape "cd 01_cache"; tape "ls -a"
capture ctf
tape "doom" 6
capture doom 3
adb shell input keyevent 4
sleep 2
capture retour
adb shell am force-stop fr.terminagotchi
sleep 1
adb logcat -d > captures/logcat.txt
if grep -q "FATAL EXCEPTION" captures/logcat.txt; then
  grep -A 25 "FATAL EXCEPTION" captures/logcat.txt > captures/PLANTAGE.txt
  echo "PLANTAGE DÉTECTÉ"; cat captures/PLANTAGE.txt
fi
ls -la captures
