#!/bin/bash
# Partie automatique sur un téléphone virtuel : on tape de vraies commandes et on prend des captures.
set -u
mkdir -p captures
APK=app/build/outputs/apk/release/app-release.apk
# serveur du recensement en local (le téléphone virtuel le voit à l'adresse 10.0.2.2)
node --no-warnings site/test/serveur.mjs > captures/serveur.log 2>&1 &
sleep 3
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
# ---- dressage d'un monstre (on force l'apparition d'Abyssor) puis animations de l'équipe
adb shell am start -n fr.terminagotchi/.TerminalActivity --es essai_dressage abyssor
capture dressage_rencontre 5
tape "cat ~/terrain_terminagotchi/monstre_abyssor.txt" 2
capture dressage_examine
tape "find ~/terrain_terminagotchi -name repaire_abyssor" 2
capture dressage_repaire
tape "dressage abandon"
adb shell am start -n fr.terminagotchi/.TerminalActivity --es essai_equipe abyssor:adulte
sleep 5
tape "equipe" 2
capture equipe
tape "bestiaire abyssor" 2
capture fiche_abyssor
tape "anime abyssor attaque" 1
capture anime_attaque 0.6
adb shell input keyevent 4
tape "anime abyssor confus" 1
capture anime_confus 0.8
adb shell input keyevent 4
adb shell am start -n fr.terminagotchi/.TerminalActivity --es essai_equipe abyssor:finale
sleep 5
tape "anime abyssor statique" 1
capture anime_finale 0.6
adb shell input keyevent 4
adb shell am start -n fr.terminagotchi/.TerminalActivity --es essai_equipe abyssor:enfant
sleep 5
tape "anime abyssor content" 1
capture anime_enfant 0.6
adb shell input keyevent 4
tape "donjon" 3
capture donjon
tape "plan"
capture plan
tape "ctf" 3
tape "cd 01_cache"; tape "ls -a"
capture ctf
# ---- recensement : inscription, puis liaison à un compte « PC » et synchro
tape "compte serveur http://10.0.2.2:8787"
tape "compte creer TelCI" 6
capture compte_cree
J='content-type: application/json'
CLE=$(curl -s -X POST localhost:8787/api/inscription -H "$J" -d '{"pseudo":"PcCI","appareil":"pc"}' | python3 -c "import json,sys;print(json.load(sys.stdin)['cle'])")
curl -s -X POST localhost:8787/api/sync -H "authorization: Bearer $CLE" -H "$J" -d '{"appareil":"pc","deltas":{"xp":500},"vus":["git"],"valeurs":{"nom":"CreaturePC"}}' > /dev/null
CODE=$(curl -s -X POST localhost:8787/api/code -H "authorization: Bearer $CLE" -H "$J" -d '{}' | python3 -c "import json,sys;print(json.load(sys.stdin)['code'])")
echo "code de liaison : $CODE"
tape "compte oublier"
tape "compte lier $CODE" 8
capture compte_lie
tape "compte" 2
capture compte_etat
curl -s localhost:8787/api/profil/TelCI > captures/profil_TelCI.json
curl -s localhost:8787/api/profil/PcCI > captures/profil_PcCI.json
python3 - <<'PY' > captures/sync_resultat.txt
import json
t = json.load(open("captures/profil_TelCI.json"))
p = json.load(open("captures/profil_PcCI.json"))
ok1 = t.get("xp", 0) > 0 and "android" in t.get("appareils", [])
ok2 = "android" in p.get("appareils", []) and "pc" in p.get("appareils", []) and p.get("xp", 0) > 500
print("inscription depuis le téléphone :", "OK" if ok1 else "ÉCHEC", t.get("xp"), t.get("appareils"))
print("liaison + synchro PC <-> téléphone :", "OK" if ok2 else "ÉCHEC", p.get("xp"), p.get("appareils"), p.get("nom"))
PY
cat captures/sync_resultat.txt
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
