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
# L'état de la ligne de saisie, lu à l'écran (uiautomator) : « pret » quand elle a le focus et qu'elle est vide
# (ou montre son indice gris « tape une commande… »), sinon « occupe » ou « absent ».
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
vide = t == "" or t == h or t.endswith("\u2026")
print("pret" if g("focused") == "true" and vide else "occupe")'
}
# attend que la ligne de saisie soit prête (au plus N secondes) : le téléphone virtuel est lent, et taper trop tôt
# perdait des lettres ou collait deux lignes (« cdmkdir », le nom « pwddebloquer tout », `langue fr` perdu)
attendre_pret() {
  for i in $(seq 1 "${1:-25}"); do [ "$(saisie)" = pret ] && return 0; sleep 1; done
  echo "(la ligne de saisie n'est pas prête après ${1:-25} s)"
}
tape() {   # tape une commande lettre par lettre puis Entrée
  local t="${1// /%s}"
  attendre_pret
  [ -n "$t" ] && adb shell "input text '$t'"
  sleep 1
  adb shell input keyevent 66
  sleep "${2:-3}"
}
adb shell am start -n fr.terminagotchi/.TerminalActivity
capture debut 12
# les écrans du début (intro.json) : Entrée jusqu'au dernier (Entrée de trop : rien), puis le nom et « oui »
tape "" 4
capture intro_1
# Entrée de trop sur le dernier écran : rien. On en tape assez pour être sûr d'y être, puis le nom, et l'on vérifie
# à l'écran (le titre) que la créature s'appelle bien Pixel ; sinon on recommence (le téléphone virtuel perd parfois
# une Entrée pendant le changement d'écran).
for i in 1 2 3 4 5; do tape "" 3; done
for essai in 1 2 3; do
  tape "Pixel" 6
  [ "$essai" = 1 ] && capture bapteme
  tape "oui" 8
  attendre_pret 40
  adb shell uiautomator dump /sdcard/tg_ui.xml >/dev/null 2>&1
  adb exec-out cat /sdcard/tg_ui.xml 2>/dev/null | grep -q 'resource-id="fr.terminagotchi:id/titre"[^>]*' && \
    adb exec-out cat /sdcard/tg_ui.xml | grep -o 'text="Pixel[^"]*" resource-id="fr.terminagotchi:id/titre"' | grep -q Pixel && break
  echo "nom pas encore pris (essai $essai) : on recommence"
  for i in 1 2 3; do tape "" 3; done
done
# le jeu en français (le téléphone virtuel est en anglais)
tape "langue fr" 2
# l'œuf et sa liste (Intro.kt) : 4 commandes, il éclot ; puis tout est ouvert pour la suite du scénario
tape "ls" 2
capture oeuf_fele
for c in "pwd" "echo bonjour" "whoami"; do tape "$c" 2; done
capture eclosion_merci
tape "debloquer tout"; tape "oui"
for c in "pwd" "ls" "cd" "mkdir terrain_terminagotchi" "cd terrain_terminagotchi" "mkdir nid"; do tape "$c"; done
capture nid
tape "echo pomme > nid/repas.txt"; tape "cat nid/repas.txt"; tape "grep pomme nid/repas.txt"
tape "ls -l nid"; tape "chmod 444 nid/repas.txt"; tape "echo poire >> nid/repas.txt"
tape "cp nid/repas.txt nid/secours.txt"; tape "mv nid/secours.txt reserve.txt"; tape "rm reserve.txt" 3
capture tronc_fini
tape "terminal" 3          # un deuxième onglet de terminal
capture onglet_2_ouvert
tape "cd terrain_terminagotchi/nid"; tape "pwd"; tape "ls" 2   # le Terminal 2 part du camp (~)
capture onglet_2_dossier
# le téléphone tourne (paysage) puis revient (portrait) : les deux onglets restent, Terminal 2 toujours dans nid
# (manifeste : configChanges ; Onglets.etat / reprendre si Android recrée quand même l'écran)
onglets_vus() {
  adb shell uiautomator dump /sdcard/tg_ui.xml >/dev/null 2>&1
  adb exec-out cat /sdcard/tg_ui.xml 2>/dev/null | python3 -c '
import re, sys
x = sys.stdin.read()
t = re.findall(r"text=\"([^\"]*)\"", x)
print("onglets:", sorted(set(v for v in t if "Terminal " in v and len(v) < 20)))'
}
onglets_vus > captures/rotation_resultat.txt
adb shell settings put system accelerometer_rotation 0
adb shell settings put system user_rotation 1
capture rotation_paysage 5
onglets_vus >> captures/rotation_resultat.txt
tape "pwd" 2
capture rotation_paysage_pwd
adb shell settings put system user_rotation 0
capture rotation_portrait 5
onglets_vus >> captures/rotation_resultat.txt
tape "pwd" 2
capture rotation_portrait_pwd
adb exec-out cat /sdcard/tg_ui.xml 2>/dev/null | grep -o 'terrain_terminagotchi/nid' | head -1 >> captures/rotation_resultat.txt
adb shell uiautomator dump /sdcard/tg_ui.xml >/dev/null 2>&1
adb exec-out cat /sdcard/tg_ui.xml 2>/dev/null | grep -c 'terrain_terminagotchi/nid' >> captures/rotation_resultat.txt
cat captures/rotation_resultat.txt
tape "exit" 3              # on ferme l'onglet 2, retour au Terminal 1
capture onglet_1_retour
# une commande tapée pendant qu'une autre tourne : mise en attente (grisée), puis lancée juste après
tape "sleep 6" 0.5; tape "ls" 0.5
capture attente 0.5
sleep 8
capture attente_lancee 1
# Ctrl+C (clavier branché : Ctrl gauche + C) arrête la commande ET vide l'attente
tape "sleep 15" 0.5; tape "pwd" 0.5
adb shell input keycombination 113 31 || true
capture ctrl_c 2
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
adb shell dumpsys window | grep -E "mCurrentFocus|mFocusedApp" > captures/focus.txt
adb shell dumpsys input_method | grep -E "mServedView|mCurFocusedWindow|mInputShown" >> captures/focus.txt
tape "cat ~/terrain_terminagotchi/monstre_abyssor.txt" 2
capture dressage_examine
tape "find ~/terrain_terminagotchi -name repaire_abyssor" 2
capture dressage_repaire
tape "dressage abandon"
adb shell am start -n fr.terminagotchi/.TerminalActivity --es essai_equipe abyssor:adulte
sleep 5
tape "troupe" 2
capture troupe
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
adb logcat -d -s TG:V > captures/tg.log
if grep -q "FATAL EXCEPTION" captures/logcat.txt; then
  grep -A 25 "FATAL EXCEPTION" captures/logcat.txt > captures/PLANTAGE.txt
  echo "PLANTAGE DÉTECTÉ"; cat captures/PLANTAGE.txt
fi
ls -la captures
