#!/bin/bash
# Passages sur le téléphone virtuel, écran par écran (workflow .github/workflows/audit-ecrans.yml).
#   PASSAGE=complet|conditions|langues|gestes  CLAVIER=oui|non  bash tests/audit_ecrans.sh   → captures/*.png
# Mêmes outils que tests/vitrine.sh et tests/scenario.sh (tape, capture, toucher) ; les mots à toucher sont lus à
# l'écran (tests/audit_lire.py). Chaque capture note dans captures/journal.txt si le clavier de l'écran est ouvert.
set -u
PASSAGE=${PASSAGE:-complet}
CLAVIER=${CLAVIER:-non}
L=${LANGUE:-fr}
APK=app/build/outputs/apk/release/app-release.apk
PAQ=fr.terminagotchi
D=captures
J=$D/journal.txt
N=0
if [ "${1:-}" = avd ]; then   # avant le démarrage du téléphone virtuel : son réglage « pas de clavier physique »
  for f in "${ANDROID_AVD_HOME:-$HOME/.android/avd}"/*.avd/config.ini; do
    [ -f "$f" ] || continue
    sed -i '/^hw.keyboard *=/d' "$f"; echo "hw.keyboard=no" >> "$f"
    echo "$f :"; grep -E "hw.keyboard|hw.mainKeys|hw.dPad" "$f"
  done
  exit 0
fi
mkdir -p $D

journal() { echo "$(date +%H:%M:%S) $*" >> $J; }
ime() { adb shell dumpsys input_method 2>/dev/null | grep -o "mInputShown=[a-z]*" | head -1 | cut -d= -f2; }
vivant() { adb shell dumpsys window 2>/dev/null | grep "mCurrentFocus" | grep -q "$PAQ"; }
activite() { adb shell dumpsys activity activities 2>/dev/null | grep -E "topResumedActivity|mResumedActivity" | head -1 | grep -o "[A-Za-z]*Activity" | tail -1; }
capture() {   # capture nom [délai] [ui] : l'image, et (ui) la liste des éléments de l'écran si Android la donne
  sleep "${2:-2}"
  N=$((N + 1))
  local f; f=$(printf "%03d_%s" $N "$1")
  adb exec-out screencap -p > "$D/$f.png"
  journal "capture $f clavier=$(ime) devant=$(activite)"
  if [ "${3:-}" = ui ]; then
    timeout 12 adb shell uiautomator dump /sdcard/tg_ui.xml >/dev/null 2>&1 && adb exec-out cat /sdcard/tg_ui.xml > "$D/$f.xml" 2>/dev/null
    adb shell rm -f /sdcard/tg_ui.xml >/dev/null 2>&1
  fi
}
tape() {   # tape une commande lettre par lettre puis Entrée
  local t="${1// /%s}"
  [ -n "$t" ] && adb shell "input text '$t'"
  sleep 0.7
  adb shell input keyevent 66
  sleep "${2:-2.5}"
}
ecris() { local t="${1// /%s}"; adb shell "input text '$t'"; sleep "${2:-1}"; }
sans_clavier() {   # Retour range le clavier de l'écran (seulement s'il est ouvert : sinon Retour fermerait le jeu)
  [ "$(ime)" = true ] && adb shell input keyevent 4
  sleep 1.5
}
pos() {
  local r; r=$(adb logcat -d -s TG_POS:I 2>/dev/null | grep " $1 [0-9]" | tail -1 | grep -o '[0-9]\+ [0-9]\+ *$')
  [ -z "$r" ] && r=$(grep " $1 [0-9]" $D/tg_pos.log 2>/dev/null | tail -1 | grep -o '[0-9]\+ [0-9]\+ *$')
  echo $r
}
toucher() { local xy; xy=$(pos "$1"); if [ -n "$xy" ]; then adb shell input tap $xy; else journal "PAS TROUVÉ : $1"; fi; sleep "${2:-2}"; }
avec_clavier() { local xy; xy=$(pos saisie); [ -n "$xy" ] && adb shell input tap $xy >/dev/null 2>&1; sleep 1.5; }
ecran() { adb exec-out screencap -p > $D/_ecran.png; }
dims() { python3 -c "from PIL import Image; im=Image.open('$D/_ecran.png'); print(im.width, im.height)"; }
tapf() {   # touche un point donné en fractions de l'écran (0 à 1)
  ecran; local wh; wh=($(dims))
  local x y; x=$(python3 -c "print(int(${wh[0]} * $1))"); y=$(python3 -c "print(int(${wh[1]} * $2))")
  adb shell input tap $x $y; journal "touche $x $y ($1, $2)"; sleep "${3:-1.5}"
}
glisser() {   # glisser x1 y1 x2 y2 (fractions de l'écran)
  ecran; local wh; wh=($(dims))
  adb shell input swipe $(python3 -c "w,h=${wh[0]},${wh[1]}; print(int(w*$1), int(h*$2), int(w*$3), int(h*$4))") 300; sleep 1
}
deux_appuis() { adb shell "input tap $1 $2 & sleep 0.12; input tap $1 $2; wait"; }   # deux appuis très rapprochés
ou_est() { ecran; python3 tests/audit_lire.py mot $D/_ecran.png "$1" "${2:-1}" 2>/dev/null; }
toucher_mot() {   # toucher_mot Mot [délai] [n] : touche le n-ième mot lu à l'écran qui contient Mot ; 1 si introuvable
  local xy; xy=$(ou_est "$1" "${3:-1}")
  if [ -n "$xy" ]; then adb shell input tap $xy; journal "touche « $1 » en $xy"; sleep "${2:-2}"; return 0; fi
  journal "MOT PAS LU : « $1 »"; return 1
}
retour() {   # le bouton Retour sur l'écran $1 (clavier rangé d'abord) : le jeu reste-t-il ouvert ? (rouvert sinon)
  if [ "$(ime)" = true ]; then adb shell input keyevent 4; sleep 1.2; fi
  adb shell input keyevent 4; sleep 1.5
  if vivant; then journal "RETOUR sur « $1 » : le jeu reste ouvert"; return 0; fi
  journal "RETOUR sur « $1 » : LE JEU SE FERME"; lancer; sleep 4; return 1
}
lancer() { adb shell am start -n $PAQ/.TerminalActivity >/dev/null 2>&1; }
icone() { adb shell am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER -n $PAQ/.TerminalActivity >/dev/null 2>&1; }
neuf() {   # l'appli comme juste installée, dans la langue $1 (Android 13 et plus : la langue de l'appli)
  adb shell am force-stop $PAQ
  adb shell pm clear $PAQ >/dev/null
  adb shell pm grant $PAQ android.permission.POST_NOTIFICATIONS >/dev/null 2>&1 || true
  adb shell cmd locale set-app-locales $PAQ --user 0 --locales "$1" >/dev/null 2>&1 || true
}
tourner() {   # $1 : 1 = paysage, 0 = portrait. Le jeu suit l'écran d'accueil (fenêtre transparente) : on laisse tourner tout le téléphone
  adb shell cmd window set-ignore-orientation-request $([ "$1" = 1 ] && echo true || echo false) >/dev/null 2>&1
  adb shell settings put system accelerometer_rotation 0; adb shell settings put system user_rotation "$1"; sleep "${2:-4}"
}
config() { adb shell am get-config 2>/dev/null | head -2 | tr -d '\r'; }

# Le téléphone virtuel annonce un clavier physique (le jeu passe alors en « tout au clavier », idée 69) ; un vrai
# téléphone n'en a pas. On retire les claviers du téléphone virtuel (les touches envoyées par adb marchent toujours).
enlever_clavier() {
  adb root >/dev/null 2>&1; sleep 4; adb wait-for-device; sleep 2
  adb shell 'for d in /sys/class/input/input*; do echo "$d : $(cat $d/name 2>/dev/null)"; done' > $D/entrees.txt 2>&1
  adb shell 'for d in /sys/class/input/input*; do n=$(cat $d/name 2>/dev/null); case "$n" in *eyboard*|*qwerty*|*keys*) p=$(readlink -f $d/device); b=$(basename $p); echo "retire : $n ($b)"; echo -n $b > $d/device/driver/unbind;; esac; done' >> $D/entrees.txt 2>&1
  sleep 3
  adb shell dumpsys input 2>/dev/null | grep -E "^ +[0-9-]+: |KeyboardType|Sources" | head -60 >> $D/entrees.txt
}

# ------------------------------------------------------------------------------------------------ préparation
node --no-warnings site/test/serveur.mjs > $D/serveur.log 2>&1 &
sleep 2
adb install -r "$APK" > /dev/null
adb logcat -G 16M >/dev/null 2>&1 || true
echo "avant : $(config)" > $D/config.txt
[ "$CLAVIER" = non ] && enlever_clavier
echo "après : $(config)" >> $D/config.txt
RESTE=non; [ "$CLAVIER" = non ] && config | grep -q qwerty && RESTE=oui
echo "clavier physique encore annoncé : $RESTE" >> $D/config.txt
sans_mode_clavier() { [ "$RESTE" = oui ] && tape "clavier off" 2; }   # le réglage du jeu, une fois la créature née
adb shell getprop ro.build.version.release >> $D/config.txt
# TAILLE=720x1280:320 : un écran plus petit (taille en pixels : densité), comme un téléphone de 360 × 640 dp
if [ -n "${TAILLE:-}" ]; then adb shell wm size "${TAILLE%%:*}"; adb shell wm density "${TAILLE##*:}"; sleep 5; fi
adb shell wm size >> $D/config.txt; adb shell wm density >> $D/config.txt
adb shell settings put global window_animation_scale 0 || true
adb shell settings put global transition_animation_scale 0 || true
adb shell settings put global animator_duration_scale 1 || true      # comme un vrai téléphone (0 : le jeu coupe ses animations)
adb shell settings put secure show_ime_with_hard_keyboard $([ "$CLAVIER" = non ] && echo 0 || echo 1) || true
adb shell appops set $PAQ SYSTEM_ALERT_WINDOW allow >/dev/null 2>&1 || true
for essai in 1 2 3 4; do
  adb shell input keyevent 3; sleep 4
  if adb shell dumpsys window 2>/dev/null | grep "mCurrentFocus" | grep -qi "not responding"; then
    echo "boîte « ne répond pas » du téléphone virtuel : Wait (essai $essai)" >> $D/config.txt
    ecran; xy=$(python3 tests/audit_lire.py mot $D/_ecran.png Wait 1); [ -n "$xy" ] && adb shell input tap $xy
    sleep 6
  else break; fi
done
adb logcat -c
adb logcat -v brief -s TG_POS:I > $D/tg_pos.log 2>/dev/null &
journal "passage $PASSAGE clavier=$CLAVIER langue=$L"

# ------------------------------------------------------------------------------------------------ morceaux communs
# du premier lancement à la créature née, sans captures (Entrée : « Je joue seul », puis les 3 écrans du début)
intro_rapide() {
  lancer; sleep 10
  tape "" 2; tape "" 2; tape "" 2; tape "" 4
  tape "langue $L" 2
  tape "pwd" 3; tape "ls" 6; tape "echo Pixel" 3; tape "whoami" 5
  tape "non" 3                                   # « Tu veux m'entendre ? » : le bouton Non (au clavier)
  tape "" 2; tape "" 2; tape "" 2
  sans_mode_clavier
}
# la question des grands de `bug`, lue à l'écran (comme tests/vitrine.sh), puis la carte « Signaler un souci »
carte_bug() {
  local essai Q
  for essai in 1 2 3; do
    tape "bug" 3; sans_clavier
    ecran
    Q=$(python3 tests/lire_ecran.py question $D/_ecran.png 2>/dev/null)
    avec_clavier
    journal "bug : réponse lue « $Q »"
    tape "${Q:-0}" 4
    [ -n "$Q" ] && break
  done
}
# les écrans importants, dans la condition $1 (le jeu est ouvert, créature née, tout débloqué)
ecrans_cles() {
  local c=$1
  avec_clavier
  capture ${c}_jeu_clavier_ouvert 1 ui
  sans_clavier; capture ${c}_jeu_clavier_range 1
  avec_clavier
  toucher menu 2; capture ${c}_menu 1 ui
  toucher "gros:🐾" 2; capture ${c}_fiche_creature 1
  glisser 0.5 0.45 0.5 0.12; capture ${c}_fiche_creature_bas 1
  retour "fiche créature ($c)"
  toucher plus 2; capture ${c}_lecon_detail 1
  retour "leçon en détail ($c)"
  toucher menu 2; toucher "gros:⚙" 2; capture ${c}_reglages 1
  retour "réglages ($c)"
  tape "carte" 3; capture ${c}_carte 1
  sans_clavier; capture ${c}_carte_clavier_range 1; avec_clavier
  tape "lexique" 3; capture ${c}_lexique 1
  tape "perdu" 3; capture ${c}_perdu 1
  tape "" 2
  tape "espace" 5; capture ${c}_espace 2
  sans_clavier; capture ${c}_espace_clavier_range 1; avec_clavier
  tape "espace" 3
  adb shell am start -n $PAQ/.TerminalActivity --es essai_dressage abyssor >/dev/null 2>&1
  sleep 5; avec_clavier
  capture ${c}_monstre 1
  tape "dressage abandon" 3
  icone; capture ${c}_menu_du_jeu 5
  tape "" 3
}

# ------------------------------------------------------------------------------------------------ passage complet
if [ "$PASSAGE" = complet ]; then
  neuf "$L"; lancer
  capture a01_qui_est_avec_toi 12 ui
  sans_clavier; capture a01_qui_clavier_range 1; avec_clavier
  tape "2" 2; capture a02_conseils_adulte 1 ui
  sans_clavier; capture a02_conseils_clavier_range 1; avec_clavier
  tape "" 2; capture a03_ecran_1 1 ui
  sans_clavier; capture a03_ecran_1_clavier_range 1; avec_clavier
  tape "" 2; capture a04_ecran_2 1
  tape "" 2; capture a05_ecran_3 1
  tape "" 4; capture a06_camp_endormi 1 ui
  sans_clavier; capture a06_camp_clavier_range 1; avec_clavier
  tape "langue $L" 2
  tape "pwd" 4; capture a07_camp_rallume 1
  tape "ls" 0.3; capture a08_premier_ls 0.3; capture a09_oeuf_arrive 5
  tape "echo" 3; capture a10_et_mon_nom 1
  tape "echo Pixel" 3; capture a11_oeuf_nomme 1
  sans_clavier; capture a11_oeuf_nomme_clavier_range 1; avec_clavier
  tape "whoami" 0.5; capture a12_eclosion 0.2; capture a13_question_son 3 ui
  tape "non" 3; capture a14_pixel_est_ne 1 ui
  sans_clavier; capture a14_pixel_est_ne_clavier_range 1; avec_clavier
  for i in 1 2 3; do tape "" 2; capture a15_presentation_$i 1; done
  sans_mode_clavier
  # la première leçon, le +, le menu ☰ avant « debloquer tout »
  tape "date" 3; capture b01_premiere_lecon 1 ui
  sans_clavier; capture b01_premiere_lecon_clavier_range 1 ui; avec_clavier
  toucher plus 2; capture b02_lecon_en_detail 1 ui
  retour "leçon en détail"
  toucher menu 2; capture b03_menu_debut 1 ui
  toucher "gros:🐾" 2; capture b04_fiche_creature_debut 1 ui
  retour "fiche de la créature"
  toucher creature 2; capture b05_fiche_en_touchant_la_creature 1
  retour "fiche (créature touchée)"
  tape "pwd" 3; tape "ls" 3; capture b06_lecon_suivante 1
  tape "debloquer tout" 2; tape "oui" 3; capture c01_tout_debloque 1
  for c in "cd" "mkdir terrain_terminagotchi" "cd terrain_terminagotchi" "mkdir nid" "echo pomme > nid/repas.txt" "cat nid/repas.txt"; do tape "$c" 2; done
  capture c02_lecon_nid 1 ui
  # ---- le menu ☰ et ses 7 entrées
  toucher menu 2; capture c03_menu 1 ui
  toucher "gros:🐾" 2; capture c04_fiche_creature 1 ui
  glisser 0.5 0.45 0.5 0.12; capture c04_fiche_creature_bas 1
  toucher_mot Album 3 && { capture c05_album 1; retour "album"; capture c05_apres_retour_album 1; }
  toucher menu 2; toucher "gros:🐾" 2
  toucher_mot Aura 3 && capture c06_aura_changee 1
  retour "fiche (aura)"
  toucher menu 2; toucher "gros:🗺" 3; capture c07_carte 1
  sans_clavier; capture c07_carte_clavier_range 1
  glisser 0.5 0.25 0.25 0.18; capture c07_carte_glissee 1
  retour "carte"; capture c07_apres_retour_carte 1
  avec_clavier
  toucher menu 2; toucher "gros:📖" 2; capture c08_lecon_depuis_menu 1
  retour "leçon (menu)"
  toucher menu 2; toucher "gros:📚" 3; capture c09_lexique 1 ui
  sans_clavier; capture c09_lexique_clavier_range 1
  glisser 0.5 0.5 0.5 0.2; capture c09_lexique_defile 1
  retour "lexique"; capture c09_apres_retour_lexique 1
  avec_clavier
  tape "lexique" 2; tape "ls" 3
  toucher menu 2; toucher "gros:🧭" 3; capture c10_perdu 1
  sans_clavier; capture c10_perdu_clavier_range 1
  retour "je suis perdu"; capture c10_apres_retour_perdu 1
  avec_clavier; tape "" 2
  toucher menu 2; toucher "gros:🗂" 3; capture c11_deux_terminaux 1 ui
  toucher menu 2; toucher "gros:🗂" 2; toucher menu 2; toucher "gros:🗂" 2; toucher menu 2; toucher "gros:🗂" 2
  capture c11_beaucoup_de_terminaux 1
  for i in 1 2 3; do tape "exit" 1.5; done
  capture c11_apres_exit 1
  vivant || { journal "exit a fermé le jeu"; lancer; sleep 4; }
  toucher menu 2; toucher "gros:⚙" 2; capture c12_reglages 1 ui
  toucher "gros:🔊" 3; capture c13_reglages_son 1 ui
  toucher_mot OK 2 || retour "réglages du son"
  toucher menu 2; toucher "gros:⚙" 2; toucher "gros:🔤" 3; capture c14_lecture_confort 1
  toucher menu 2; toucher "gros:⚙" 2; toucher "gros:🌍" 3; capture c15_langue 1
  toucher menu 2; toucher "gros:⚙" 2; toucher "gros:⌨" 3; avec_clavier; tape "pwd" 3; capture c16_terminal_pur 1 ui
  sans_clavier; capture c16_terminal_pur_clavier_range 1; avec_clavier
  toucher menu 2; capture c16_menu_en_terminal_pur 1; toucher "gros:⚙" 2; toucher "gros:⌨" 3; avec_clavier
  # ---- les commandes qui ouvrent un écran
  tape "aide" 3; capture d01_aide 1
  tape "aide tout" 3; capture d02_aide_tout 1
  tape "etat" 3; capture d03_etat 1
  tape "envies" 3; capture d04_envies 1
  tape "album" 4; capture d05_album_commande 1
  retour "album (commande)"
  tape "joue pierre" 3; tape "devine 5" 3; capture d06_mini_jeux 1
  tape "collection" 3; capture d07_collection 1
  tape "son" 3; capture d08_son_commande 1
  toucher_mot OK 2 || retour "son (commande)"
  tape "confort" 3; tape "confort taille 150" 3; capture d09_confort_grand 1
  toucher menu 2; capture d09_menu_texte_grand 1; retour "menu (texte 150 %)"
  tape "confort taille 100" 2
  tape "theme" 3; capture d10_themes 1
  adb shell am start -n $PAQ/.TerminalActivity --es essai_dressage abyssor >/dev/null 2>&1
  sleep 5; avec_clavier; capture e01_monstre 1 ui
  sans_clavier; capture e01_monstre_clavier_range 1; avec_clavier
  tape "cat ~/terrain_terminagotchi/monstre_abyssor.txt" 3; capture e02_dressage_examine 1
  toucher menu 2; capture e03_menu_pendant_dressage 1; retour "menu (dressage)"
  tape "dressage abandon" 3
  adb shell am start -n $PAQ/.TerminalActivity --es essai_equipe abyssor:adulte >/dev/null 2>&1
  sleep 5
  tape "troupe" 3; capture e04_troupe 1
  tape "bestiaire abyssor" 3; capture e05_fiche_abyssor 1
  tape "anime abyssor attaque" 1; capture e06_anime 0.5
  toucher menu 2; toucher "gros:🐾" 2; capture e07_fiche_avec_equipe 1
  glisser 0.5 0.45 0.5 0.12; capture e07_fiche_avec_equipe_bas 1
  retour "fiche (équipe)"
  tape "donjon" 4; capture e08_donjon 1
  tape "plan" 3; capture e09_plan 1
  tape "attaque" 3; capture e10_combat 1
  tape "cd" 2
  # ---- l'espace et ses onglets, le monde
  tape "espace" 6; capture f01_espace 2
  sans_clavier; capture f01_espace_clavier_range 1
  retour "espace"; capture f01_apres_retour_espace 1
  avec_clavier
  tape "monde" 5; capture f02_monde 2
  sans_clavier; capture f02_monde_clavier_range 1; avec_clavier
  tape "cerveau" 4; capture f03_cerveau 1
  tape "carte" 4; capture f04_carte_dans_espace 1
  tape "options" 4; capture f05_options 1
  tape "ranger" 4; capture f06_ranger 1
  tape "deploie ls -l | grep nid" 4; capture f07_deploie 1
  tape "espace classe" 4; capture f08_espace_classe 1
  tape "espace classe" 3; tape "espace" 4; capture f09_espace_ferme 1
  # ---- le mode classe, la carte de visite, l'éditeur, Doom, signaler un souci, le compte, la notification, la bulle
  tape "carte visite" 4; capture g01_carte_de_visite 1
  retour "carte de visite"; tape "" 1
  tape "classe tableau" 4; capture g02_classe_tableau 1
  retour "tableau de la classe"; tape "" 1
  tape "classe" 3; capture g03_classe_aide 1
  tape "edite notes.txt" 4; capture g04_editeur 1 ui
  ecris "bonjour le monde" 1; capture g04_editeur_texte 1
  adb shell input keyevent 4; sleep 1; capture g04_editeur_un_retour 1
  vivant && [ "$(activite)" = "EditeurActivity" ] && { adb shell input keyevent 4; sleep 1; }
  capture g04_apres_editeur 1
  vivant || { journal "après l'éditeur : le jeu est fermé"; lancer; sleep 4; }
  tape "cat notes.txt" 3; capture g04_texte_garde 1
  carte_bug; capture g05_signaler_un_souci 1 ui
  sans_clavier; capture g05_signaler_clavier_range 1
  retour "signaler un souci"; capture g05_apres_retour_signaler 1
  avec_clavier
  tape "compte" 3; capture g06_compte 1
  tape "compte serveur http://10.0.2.2:8787" 3; tape "compte creer AuditCI" 8; capture g06_compte_cree 1
  tape "sync" 8; capture g06_synchro 1
  tape "compte serveur http://10.0.2.2:9" 3; tape "pwd" 3; tape "sync" 10; capture g06_hors_ligne 1
  toucher nuage 2; capture g06_nuage_explique 1
  tape "notif on" 4; capture g07_notif 1
  adb shell cmd statusbar expand-notifications; capture g07_volet_notifications 3
  adb shell cmd statusbar collapse; sleep 2
  vivant || { lancer; sleep 4; }
  tape "bulle" 4; capture g08_bulle 1
  adb shell input keyevent 3; capture g08_bulle_sur_accueil 4
  icone; capture g09_menu_du_jeu 5 ui
  for m in 5 4 3; do tape "$m" 3; capture g09_menu_choix_$m 1; icone; sleep 3; done
  tape "2" 3; capture g09_nouvelle_partie_question 1
  tape "non" 3; capture g09_nouvelle_partie_non 1
  tape "1" 3; capture g09_jouer 1
  tape "doom" 6; capture g10_doom 3
  retour "doom"; capture g10_apres_doom 2
  # le jeu fermé puis rouvert depuis l'icône (comme sur un vrai téléphone)
  adb shell am force-stop $PAQ; sleep 2
  icone; capture h01_rouvert_depuis_icone 8 ui
  sans_clavier; capture h01_rouvert_clavier_range 1
  tape "" 3; capture h02_jouer 1
fi

# ------------------------------------------------------------------------------------------------ conditions
if [ "$PASSAGE" = conditions ]; then
  une_condition() {   # $1 : nom ; le jeu depuis le premier lancement, puis les écrans importants
    local c=$1
    neuf "$L"; lancer
    capture ${c}_qui_est_avec_toi 12
    tape "2" 2; capture ${c}_conseils_adulte 1
    tape "" 2; capture ${c}_ecran_1 1
    tape "" 2; capture ${c}_ecran_2 1
    tape "" 2; capture ${c}_ecran_3 1
    tape "" 4; capture ${c}_camp 1
    tape "langue $L" 2
    tape "pwd" 3; tape "ls" 6; capture ${c}_oeuf 1
    tape "echo Pixel" 3; tape "whoami" 4; capture ${c}_question_son 1
    tape "non" 3; capture ${c}_pixel_est_ne 1
    tape "" 2; tape "" 2; tape "" 2
    sans_mode_clavier
    tape "debloquer tout" 2; tape "oui" 3
    for cmd in "cd" "mkdir terrain_terminagotchi" "cd terrain_terminagotchi" "mkdir nid"; do tape "$cmd" 2; done
    ecrans_cles $c
  }
  tourner 1; une_condition paysage
  tape "edite notes.txt" 4; capture paysage_editeur 1; adb shell input keyevent 4; sleep 1; adb shell input keyevent 4; sleep 1
  vivant || { lancer; sleep 3; }
  tourner 0
  adb shell settings put system font_scale 1.3; sleep 2
  une_condition police13
  tape "edite notes.txt" 4; capture police13_editeur 1; adb shell input keyevent 4; sleep 1; adb shell input keyevent 4; sleep 1
  vivant || { lancer; sleep 3; }
  tape "son" 3; capture police13_reglages_son 1; toucher_mot OK 2 || retour "son (police 1,3)"
  adb shell settings put system font_scale 1.0; sleep 2
  adb shell wm size 720x1280; adb shell wm density 320; sleep 4
  une_condition petit720
  adb shell wm size 480x800; adb shell wm density 240; sleep 4
  une_condition petit480
  adb shell settings put system font_scale 1.3; sleep 2
  adb shell am force-stop $PAQ; lancer; sleep 6
  capture petit480_police13_jeu 1
  toucher menu 2; capture petit480_police13_menu 1; retour "menu (petit écran, grande police)"
  toucher creature 2; capture petit480_police13_fiche 1; retour "fiche (petit écran, grande police)"
  adb shell settings put system font_scale 1.0
  adb shell wm size reset; adb shell wm density reset; sleep 4
  # le thème du téléphone : sombre puis clair (les boîtes de dialogue et l'éditeur suivent le téléphone)
  for th in yes no; do
    adb shell cmd uimode night $th; sleep 3
    adb shell am force-stop $PAQ; lancer; sleep 6
    capture theme_${th}_jeu 1
    tape "son" 3; capture theme_${th}_reglages_son 1; toucher_mot OK 2 || retour "réglages du son (thème $th)"
    tape "edite notes.txt" 4; capture theme_${th}_editeur 1; adb shell input keyevent 4; sleep 1
    [ "$(activite)" = "EditeurActivity" ] && { adb shell input keyevent 4; sleep 1; }
    vivant || { lancer; sleep 3; }
    icone; capture theme_${th}_menu_du_jeu 4; tape "" 2
  done
fi

# ------------------------------------------------------------------------------------------------ langues
if [ "$PASSAGE" = langues ]; then
  for L in ${LANGUES:-en de ja ar}; do
    neuf "$L"; lancer
    capture ${L}_qui_est_avec_toi 12
    tape "2" 2; capture ${L}_conseils_adulte 1
    tape "" 2; capture ${L}_ecran_1 1
    tape "" 2; capture ${L}_ecran_2 1
    tape "" 2; capture ${L}_ecran_3 1
    tape "" 4; capture ${L}_camp 1
    tape "langue $L" 2
    tape "pwd" 3; capture ${L}_camp_rallume 1
    tape "ls" 6; capture ${L}_oeuf 1
    tape "echo Pixel" 3; tape "whoami" 4; capture ${L}_question_son 1
    tape "non" 3; capture ${L}_ne 1
    tape "" 2; capture ${L}_presentation_1 1; tape "" 2; capture ${L}_presentation_2 1; tape "" 2
    sans_mode_clavier
    tape "date" 3; capture ${L}_lecon 1
    sans_clavier; capture ${L}_lecon_clavier_range 1; avec_clavier
    toucher plus 2; capture ${L}_lecon_detail 1; retour "leçon ($L)"
    tape "debloquer tout" 2; tape "oui" 3
    for cmd in "cd" "mkdir terrain_terminagotchi" "cd terrain_terminagotchi" "mkdir nid"; do tape "$cmd" 2; done
    capture ${L}_lecon_nid 1
    toucher menu 2; capture ${L}_menu 1
    toucher "gros:🐾" 2; capture ${L}_fiche 1
    glisser 0.5 0.45 0.5 0.12; capture ${L}_fiche_bas 1
    retour "fiche ($L)"
    toucher menu 2; toucher "gros:⚙" 2; capture ${L}_reglages 1
    toucher "gros:🔊" 3; capture ${L}_reglages_son 1; toucher_mot OK 2 || retour "son ($L)"
    toucher menu 2; toucher "gros:📚" 3; capture ${L}_lexique 1
    tape "ls" 3
    toucher menu 2; toucher "gros:🧭" 3; capture ${L}_perdu 1
    tape "" 2
    tape "carte" 3; capture ${L}_carte 1
    tape "aide" 3; capture ${L}_aide 1
    tape "fichier_inexistant" 3; capture ${L}_erreur 1
    adb shell am start -n $PAQ/.TerminalActivity --es essai_dressage abyssor >/dev/null 2>&1
    sleep 5; avec_clavier; capture ${L}_monstre 1
    tape "dressage abandon" 3
    tape "espace" 5; capture ${L}_espace 2; tape "monde" 4; capture ${L}_monde 2; tape "espace" 3
    tape "album" 4; capture ${L}_album 1; retour "album ($L)"
    tape "edite notes.txt" 4; capture ${L}_editeur 1; adb shell input keyevent 4; sleep 1
    [ "$(activite)" = "EditeurActivity" ] && { adb shell input keyevent 4; sleep 1; }
    vivant || { lancer; sleep 3; }
    icone; capture ${L}_menu_du_jeu 5
    tape "" 2
  done
fi

# ------------------------------------------------------------------------------------------------ gestes
if [ "$PASSAGE" = gestes ]; then
  neuf "$L"; lancer
  capture g01_qui_est_avec_toi 12
  # Retour : d'abord le clavier, puis l'écran lui-même
  sans_clavier
  retour "Qui est avec toi ?"; capture g02_apres_retour_qui 1
  # l'appli tuée sur « Qui est avec toi ? » puis relancée
  adb shell am force-stop $PAQ; sleep 1; lancer; capture g03_tuee_sur_qui_relancee 8
  # toucher le bouton « Un adulte est à côté de moi »
  toucher_mot adulte 2 2 || tape "2" 2
  capture g04_apres_toucher_adulte 1
  adb shell am force-stop $PAQ; sleep 1; lancer; capture g05_tuee_sur_conseils_relancee 8
  tape "" 2; capture g06_ecran_1 1
  # rotation pendant l'intro
  tourner 1; capture g07_ecran_1_paysage 1
  sans_clavier; capture g07_ecran_1_paysage_clavier_range 1
  tourner 0; capture g08_ecran_1_retour_portrait 1
  avec_clavier
  # double appui rapide sur « Suivant » (lu à l'écran ; sinon le symétrique de « Passer »)
  xy=$(ou_est Suivant 1)
  if [ -z "$xy" ]; then p=($(ou_est Passer 1)); wh=($(dims)); [ ${#p[@]} = 2 ] && xy="$((wh[0] - p[0])) ${p[1]}"; fi
  journal "Suivant en « $xy »"
  if [ -n "$xy" ]; then deux_appuis $xy; else tape "" 1; fi
  capture g09_apres_double_appui_suivant 2
  retour "écran du début"; capture g10_apres_retour_ecran 1
  adb shell am force-stop $PAQ; sleep 1; lancer; capture g11_tuee_sur_ecran_relancee 8
  tape "" 2; tape "" 2; tape "" 2; tape "" 4
  tape "langue $L" 2
  capture g12_camp 1
  adb shell am force-stop $PAQ; sleep 1; lancer; capture g13_tuee_au_camp_relancee 8
  tape "pwd" 4
  adb shell input keyevent 3; sleep 2; capture g14_accueil_du_telephone 1
  icone; capture g15_retour_par_icone_au_camp 5
  sans_clavier; capture g15_retour_par_icone_clavier_range 1
  tape "" 3; capture g16_apres_jouer 1
  tape "" 2; tape "" 2; tape "" 2; tape "pwd" 3      # (si les écrans du début sont revenus : on les repasse)
  # appui pendant la cinématique du premier ls
  tape "ls" 0.2; tapf 0.5 0.3 0.3; capture g17_appui_pendant_ls 0.2; capture g18_apres_ls 5
  adb shell am force-stop $PAQ; sleep 1; lancer; capture g19_tuee_apres_ls_relancee 8
  tape "" 2; tape "" 2; tape "" 2
  tape "echo Pixel" 3
  adb shell am force-stop $PAQ; sleep 1; lancer; capture g20_tuee_apres_le_nom_relancee 8
  tape "whoami" 0.3; tapf 0.5 0.3 0.2; tapf 0.5 0.3 0.2; capture g21_appuis_pendant_eclosion 0.2
  capture g22_question_son 3
  adb shell am force-stop $PAQ; sleep 1; lancer; capture g23_tuee_sur_question_son_relancee 8
  tape "" 2; tape "" 2; tape "" 2
  sans_mode_clavier
  tape "pwd" 3; capture g24_milieu_de_lecon 1
  adb shell am force-stop $PAQ; sleep 1; lancer; capture g25_tuee_en_lecon_relancee 8
  # ---- Retour sur chaque écran
  sans_clavier; capture g26_jeu_clavier_range 1
  retour "le jeu, clavier rangé"; capture g27_apres_retour_jeu 1
  tape "debloquer tout" 2; tape "oui" 3
  for cmd in "cd" "mkdir terrain_terminagotchi" "cd terrain_terminagotchi" "mkdir nid"; do tape "$cmd" 2; done
  toucher menu 2; retour "menu ☰"; capture g28_apres_retour_menu 1
  # double appui rapide sur ☰ puis sur +
  deux_appuis $(pos menu); capture g29_double_appui_menu 2
  retour "menu ☰ (double appui)"; vivant && retour "menu ☰ (2e fiche ?)"
  deux_appuis $(pos plus); capture g30_double_appui_plus 2
  retour "leçon (double appui)"
  # le menu ☰ ouvert, puis le volet des notifications ouvert et refermé : le clavier revient-il par-dessus ?
  avec_clavier
  toucher menu 2; capture g31_menu_ouvert 1
  adb shell cmd statusbar expand-notifications; sleep 2; adb shell cmd statusbar collapse; sleep 3
  capture g31_menu_apres_volet_notifications 1
  retour "menu ☰ après le volet"
  vivant || { lancer; sleep 4; }
  # le menu ☰ ouvert, puis l'écran éteint et rallumé
  avec_clavier
  toucher menu 2
  adb shell input keyevent 26; sleep 3; adb shell input keyevent 26; sleep 2; adb shell input keyevent 82; sleep 3
  capture g32_menu_apres_ecran_eteint 1
  retour "menu ☰ après écran éteint"
  vivant || { lancer; sleep 4; }
  # la fiche de la créature ouverte, bouton Accueil, puis retour par l'icône
  avec_clavier
  toucher creature 2; adb shell input keyevent 3; sleep 2; icone; sleep 4
  capture g33_fiche_puis_accueil_puis_icone 1
  tape "" 3; capture g33_apres_jouer 1
  vivant || { lancer; sleep 4; }
  # rotation pendant qu'une fiche est ouverte
  toucher menu 2; toucher "gros:🐾" 2; tourner 1; capture g34_fiche_paysage 1
  glisser 0.5 0.6 0.5 0.15; capture g34_fiche_paysage_defilee 1
  tourner 0; capture g35_fiche_retour_portrait 1
  retour "fiche après rotation"
  # le jeu tourné : le terminal, le menu, le clavier
  tourner 1; avec_clavier; capture g36_jeu_paysage_clavier 1
  toucher menu 2; capture g36_menu_paysage 1; retour "menu (paysage)"
  tourner 0; capture g37_jeu_retour_portrait 1
  # défilement du terminal, puis une commande : revient-on en bas ?
  for i in 1 2 3 4; do tape "aide tout" 1.5; done
  sans_clavier
  glisser 0.5 0.3 0.5 0.7; capture g38_terminal_remonte 1
  glisser 0.5 0.3 0.5 0.7; glisser 0.5 0.3 0.5 0.7; capture g38_terminal_remonte_plus 1
  avec_clavier; tape "pwd" 3; capture g39_apres_commande 1
  # appui long : sur le texte du terminal, puis dans la ligne de saisie
  ecran; wh=($(dims))
  adb shell input swipe $((wh[0] / 3)) $((wh[1] / 4)) $((wh[0] / 3)) $((wh[1] / 4)) 1200; capture g40_appui_long_terminal 1
  retour "appui long (terminal)"
  ecris "echo copie" 1
  xy=$(pos saisie); adb shell input swipe $xy $xy 1200; capture g41_appui_long_saisie 1
  toucher_mot "Coller" 2 || toucher_mot "Paste" 2; capture g41_apres_coller 1
  adb shell input keyevent 66; sleep 2
  # la croix du haut, puis un toucher dans la marge du panneau : le jeu se ferme-t-il sans prévenir ?
  ecran; wh=($(dims)); mx=$(pos menu); set -- $mx
  cx=$(( $1 + (wh[0] - $1) * 5 / 10 )); adb shell input tap $cx $2; sleep 2
  capture g42_apres_la_croix 1
  vivant && journal "CROIX : le jeu reste ouvert" || { journal "CROIX : le jeu se ferme sans rien demander"; lancer; sleep 4; }
  adb shell input tap 3 $((wh[1] / 2)); sleep 2
  capture g43_apres_toucher_la_marge 1
  vivant && journal "MARGE : le jeu reste ouvert" || { journal "MARGE : le jeu se ferme sans rien demander"; lancer; sleep 4; }
  # un toucher dans la petite bande entre le bas du panneau et le haut du clavier (là où l'on vise la 1re rangée de touches)
  avec_clavier
  timeout 12 adb shell uiautomator dump /sdcard/tg_ui.xml >/dev/null 2>&1
  bande=$(adb exec-out cat /sdcard/tg_ui.xml 2>/dev/null | python3 -c "
import re, sys
x = sys.stdin.read()
m = re.search(r'resource-id=\"fr.terminagotchi:id/fond\"[^>]*bounds=\"\[(\d+),(\d+)\]\[(\d+),(\d+)\]\"', x)
print((int(m.group(1)) + int(m.group(3))) // 2, int(m.group(4)) - 8) if m else print('')")
  journal "bande au-dessus du clavier : « $bande »"
  capture g43_avant_toucher_la_bande 1
  if [ -n "$bande" ]; then
    adb shell input tap $bande; sleep 2
    capture g43_apres_toucher_la_bande 1
    vivant && journal "BANDE AU-DESSUS DU CLAVIER : le jeu reste ouvert" || { journal "BANDE AU-DESSUS DU CLAVIER : le jeu se ferme sans rien demander"; lancer; sleep 4; }
  fi
  # Retour sur les autres écrans
  tape "album" 4; retour "album"
  tape "carte" 3; sans_clavier; retour "carte"; avec_clavier
  tape "lexique" 3; sans_clavier; retour "lexique"; avec_clavier
  tape "perdu" 3; sans_clavier; retour "pas de panique"; avec_clavier; tape "" 2
  tape "espace" 5; sans_clavier; retour "espace de travail"; capture g44_apres_retour_espace 1; avec_clavier
  tape "espace" 3; tape "espace" 3
  icone; sleep 4; retour "menu du jeu"; capture g45_apres_retour_menu_du_jeu 1
  tape "" 2
  tape "son" 3; capture g45_reglages_son 1; sans_clavier; retour "réglages du son"; capture g45_apres_retour_son 1
  # l'éditeur : du texte tapé puis Retour
  tape "edite brouillon.txt" 4; ecris "texte pas enregistre" 1; capture g46_editeur 1
  adb shell input keyevent 4; sleep 1; capture g46_editeur_retour_1 1
  [ "$(activite)" = "EditeurActivity" ] && { adb shell input keyevent 4; sleep 1; capture g46_editeur_retour_2 1; }
  vivant || { journal "après l'éditeur : le jeu est fermé"; lancer; sleep 4; }
  tape "cat brouillon.txt" 3; capture g47_brouillon_perdu 1
  # bouton Accueil au milieu d'une commande longue, puis retour
  tape "sleep 8" 0.5; adb shell input keyevent 3; sleep 3; lancer; capture g48_retour_pendant_commande 2
  capture g48_commande_finie 8
  # Récents : le jeu y est-il ?
  adb shell input keyevent 3; sleep 2; adb shell input keyevent 187; capture g49_recents 3
  adb shell input keyevent 3; sleep 1; lancer; sleep 3
  # double appui sur Entrée, deux commandes très vite
  ecris "pwd" 0.2; adb shell "input keyevent 66; input keyevent 66"; ecris "ls" 0.2; adb shell input keyevent 66
  capture g50_commandes_rapides 3
fi

# ------------------------------------------------------------------------------------------------ le tout début
# Le premier lancement comme sur un téléphone neuf (la permission des notifications n'est pas donnée d'avance), puis
# les premières leçons une à une, clavier ouvert : ce que voit l'enfant pendant ses 20 premières commandes.
if [ "$PASSAGE" = debut ]; then
  adb shell am force-stop $PAQ; adb shell pm clear $PAQ >/dev/null
  adb shell pm revoke $PAQ android.permission.POST_NOTIFICATIONS >/dev/null 2>&1 || true
  adb shell cmd locale set-app-locales $PAQ --user 0 --locales "$L" >/dev/null 2>&1 || true
  lancer
  capture p01_tout_premier_lancement 10 ui
  journal "devant au premier lancement : $(adb shell dumpsys window 2>/dev/null | grep -m1 mCurrentFocus | tr -d '\r')"
  vivant || { adb shell input keyevent 4; sleep 2; capture p02_apres_refus_permission 1; }
  capture p03_qui_est_avec_toi 2 ui
  # toucher les boutons eux-mêmes (pas la touche Entrée)
  toucher_mot seul 2 || tape "" 2
  capture p04_ecran_1 1 ui
  for i in 2 3; do
    xy=$(ou_est Suivant 1)
    if [ -z "$xy" ]; then pp=($(ou_est Passer 1)); wh=($(dims)); [ ${#pp[@]} = 2 ] && xy="$((wh[0] - pp[0])) ${pp[1]}"; fi
    journal "Suivant (écran $((i - 1))) en « $xy »"
    if [ -n "$xy" ]; then adb shell input tap $xy; sleep 2; else tape "" 2; fi
    capture p04_ecran_$i 1
  done
  tape "" 4; capture p05_camp 1 ui
  sans_clavier; capture p05_camp_clavier_range 1; avec_clavier
  tape "langue $L" 2
  capture p05_camp_avant_pwd 1
  ecris "pw" 1; capture p05_camp_en_tapant 1 ui
  ecris "d" 0.5; adb shell input keyevent 66; sleep 4; capture p06_apres_pwd 1 ui
  tape "ls" 6; capture p07_apres_ls 1
  tape "echo Pixel" 4; capture p08_apres_echo 1
  tape "whoami" 5; capture p09_apres_whoami 1
  tape "non" 3
  for i in 1 2 3; do capture p10_presentation_$i 1; tape "" 2; done
  sans_mode_clavier
  k=0
  for c in "pwd" "ls" "cd ~" "cd terrain_terminagotchi" "ls" "cd vestibule" "ls" "cd /" "ls" "pwd" "cd ~"; do
    k=$((k + 1)); tape "$c" 3; capture "p11_lecon_$(printf %02d $k)" 1
  done
  capture p12_ligne_longue 1 ui
  sans_clavier; capture p12_ligne_longue_clavier_range 1 ui
  toucher plus 2; capture p12_lecon_en_detail 1
  retour "leçon en détail (ligne longue)"
  avec_clavier
  tape "cd /home/explorateur/terrain_terminagotchi/vestibule" 3; capture p13_lecon_suivante 1
  for c in "cd .." "mkdir nid" "cd nid" "echo pomme > repas.txt" "ls" "cat repas.txt"; do
    k=$((k + 1)); tape "$c" 3; capture "p14_suite_$(printf %02d $k)" 1
  done
  # les touches de la rangée : ⋯ (les autres symboles), ↑, ⇥
  toucher_mot Indice 2 && capture p15_indice 1
  ecran; wh=($(dims)); sy=$(pos saisie | cut -d' ' -f2)
  journal "saisie en y=$sy sur ${wh[1]}"
  capture p16_rangee_de_touches 1 ui
fi

# ------------------------------------------------------------------------------------------------ compléments
# Ce que le passage complet n'a pas pu toucher : la carte du monde de l'espace (zoom, lieu, livre des gardiens),
# « Ranger mon espace » et les options clavier rangé, la taille du texte avant et après l'espace, le tableau de la
# classe, le monstre pas à pas, le lexique (« Mettre dans la ligne »).
if [ "$PASSAGE" = complements ]; then
  neuf "$L"; intro_rapide
  tape "debloquer tout" 2; tape "oui" 3
  for c in "cd" "mkdir terrain_terminagotchi" "cd terrain_terminagotchi" "mkdir nid" "cd"; do tape "$c" 2; done
  # ---- la taille du texte : avant, « très grand », puis après un passage par l'espace
  capture k01_texte_normal 1 ui
  tape "confort taille 150" 3; capture k01_texte_150 1 ui
  toucher menu 2; capture k01_menu_150 1; retour "menu (150 %)"
  toucher plus 2; capture k01_lecon_150 1; retour "leçon (150 %)"
  tape "espace" 5; tape "espace" 4; capture k01_texte_150_apres_espace 1 ui
  adb shell am force-stop $PAQ; lancer; sleep 6; capture k01_texte_150_apres_relance 1 ui
  tape "confort taille 100" 3; tape "espace" 5; tape "espace" 4
  # ---- la carte du monde de l'espace (positions relevées sur un Pixel 6)
  tape "espace" 5; tape "carte" 4
  sans_clavier; capture k02_carte_espace_clavier_range 2
  tapf 0.925 0.272 1; tapf 0.925 0.272 1; capture k02_carte_zoom_plus 1
  glisser 0.5 0.30 0.3 0.26; capture k02_carte_glissee 1
  tapf 0.925 0.32 1; tapf 0.925 0.32 1; capture k02_carte_zoom_moins 1
  tapf 0.40 0.262 2; capture k02_carte_lieu_touche 1
  tapf 0.50 0.289 2; capture k02_carte_lieu_2 1
  toucher_mot aller 2; capture k02_carte_apres_y_aller 1
  toucher_mot livre 3 && { capture k02_livre_des_gardiens 1; glisser 0.5 0.6 0.5 0.3; capture k02_livre_defile 1; }
  toucher_mot carnet 3 && capture k02_carnet 1
  retour "carte de l'espace"; vivant || true
  avec_clavier
  # ---- ranger et options, clavier rangé, jusqu'en bas
  tape "ranger" 4; sans_clavier; capture k03_ranger_clavier_range 1
  glisser 0.5 0.6 0.5 0.2; capture k03_ranger_bas 1
  toucher_mot Termin 2 || toucher_mot OK 2 || toucher_mot Fermer 2; capture k03_ranger_apres 1
  avec_clavier; tape "options" 4; sans_clavier; capture k04_options_clavier_range 1
  glisser 0.5 0.6 0.5 0.2; capture k04_options_bas 1
  glisser 0.5 0.6 0.5 0.2; capture k04_options_bas_2 1
  avec_clavier; tape "espace" 4
  vivant || { lancer; sleep 4; }
  # ---- le tableau de la classe sur un téléphone, clavier rangé ; comment en sortir ?
  tape "classe tableau" 4; sans_clavier; capture k05_tableau_clavier_range 1
  tapf 0.94 0.06 2; capture k05_tableau_apres_toucher_coin 1
  vivant || { journal "tableau : le jeu s'est fermé"; lancer; sleep 4; }
  avec_clavier; tape "" 2; tape "pwd" 3; capture k05_apres_tableau 1
  # ---- le monstre pas à pas
  adb shell am start -n $PAQ/.TerminalActivity --es essai_dressage abyssor >/dev/null 2>&1
  sleep 5; avec_clavier; capture k06_monstre 1 ui
  toucher_mot Indice 3; capture k06_monstre_indice 1
  tape "cat ~/terrain_terminagotchi/monstre_abyssor.txt" 4; capture k06_monstre_etape_2 1
  sans_clavier; capture k06_monstre_etape_2_clavier_range 1; avec_clavier
  tape "find ~/terrain_terminagotchi -name repaire_abyssor" 4; capture k06_monstre_repaire 1
  tape "indice" 3; capture k06_monstre_indice_commande 1
  tape "dressage abandon" 3
  # ---- le lexique : « Mettre dans la ligne »
  tape "lexique" 3; sans_clavier
  toucher_mot Mettre 2; capture k07_lexique_mettre 1
  tape "" 2
  # ---- l'album : toucher un stade, puis dehors
  tape "album" 4; sans_clavier; capture k08_album_clavier_range 1
  tapf 0.8 0.42 1; capture k08_album_stade_touche 1
  tapf 0.5 0.95 1; capture k08_album_touche_dehors 1
  vivant || { journal "album : le jeu s'est fermé"; lancer; sleep 4; }
  # ---- le thème clair du jeu (commande theme)
  avec_clavier; tape "theme clair" 3; capture k09_theme_clair 1
  tape "espace" 5; capture k09_theme_clair_espace 1; tape "espace" 4
  toucher menu 2; capture k09_theme_clair_menu 1; retour "menu (thème clair)"
  tape "theme sombre" 3
fi

# ------------------------------------------------------------------------------------------------ fin
adb shell am force-stop $PAQ
adb logcat -d > $D/_logcat.txt 2>/dev/null
grep -E "TG_POS|TG  |I/TG|E/TG|W/TG" $D/_logcat.txt | tail -400 > $D/tg.log
if grep -q "FATAL EXCEPTION" $D/_logcat.txt; then
  grep -B 2 -A 30 "FATAL EXCEPTION" $D/_logcat.txt > $D/PLANTAGE.txt
  echo "PLANTAGE DÉTECTÉ"; head -80 $D/PLANTAGE.txt
fi
grep -E "ANR in|Not responding" $D/_logcat.txt | head -20 > $D/anr.txt
rm -f $D/_ecran.png
kill $(jobs -p) 2>/dev/null
cat $J
ls $D | wc -l
