"""Registre de commandes + recherche intelligente, dans la langue choisie.

On peut chercher une commande par son nom (« grep ») ou décrire ce qu'on veut faire
(« supprimer un dossier », « voir les fichiers cachés »). Aucune IA externe :
synonymes + racines de mots + score de correspondance, 100 % hors ligne.

Les descriptions et les mots-clés sont des clés des fichiers de langue (reg.xxx et reg.xxx.kw) :
on cherche à la fois dans le français (toujours) et dans la langue choisie. Pour le chinois et
le japonais (pas d'espaces entre les mots), on compare les caractères et les paires de caractères.
"""
import re
import unicodedata

from . import core, langue, lexique
from .langue import t
from .plateforme import BOLD, DIM, GEST, INSTALL, IS_WIN, OSK, RESET, C, fg, installer, piege

# ================================================================ registre

def E(unix, win, desc, kw="", danger=False, note=None, mac=None, android=None):
    return {"type": "cmd", "cmd": C(unix, win, mac, android), "desc": desc, "kw": kw,
            "danger": danger, "note": note,
            "noms": {x.split()[0].lower() for x in (unix, win, mac, android) if x}}


def R(titre, kw, steps):
    return {"type": "recette", "titre": titre, "kw": kw,
            "steps": [(C(*s[:2]) if len(s) == 3 else C(*s[:-1]), s[-1]) for s in steps]}


LAUNCHER = "am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER"
NOTE_ANDROID = None if OSK == "android" else ("reg.note.android", {})


def A(cmd, desc, kw, danger=False):
    """Commande propre à Android/Termux."""
    e = E(cmd, cmd, desc, kw, danger=danger, note=NOTE_ANDROID)
    e["android"] = True
    return e


def RA(titre, kw, steps):
    r = {"type": "recette", "titre": titre, "kw": kw, "steps": steps, "android": True}
    return r


REGISTRE = [
    # --- navigation
    E("pwd", "pwd", "reg.afficher_dossier_ou_tu", "reg.afficher_dossier_ou_tu.kw"),
    E("ls", "dir", "reg.lister_contenu_dossier", "reg.lister_contenu_dossier.kw"),
    E("ls -a", "dir -Force", "reg.voir_aussi_fichiers_caches", "reg.voir_aussi_fichiers_caches.kw"),
    E("ls -l", "dir", "reg.lister_avec_details_taille", "reg.lister_avec_details_taille.kw"),
    E("cd dossier", "cd dossier", "reg.aller_dossier", "reg.aller_dossier.kw"),
    E("cd ..", "cd ..", "reg.remonter_dossier_parent", "reg.remonter_dossier_parent.kw"),
    E("cd ~", "cd ~", "reg.revenir_dossier_perso", "reg.revenir_dossier_perso.kw"),
    E("tree", "tree /f", "reg.voir_plan_tous_dossiers", "reg.voir_plan_tous_dossiers.kw",
      note=None if IS_WIN else ("reg.note.absent", {"cmd": installer("tree")})),
    # --- fichiers et dossiers
    E("mkdir nom", "mkdir nom", "reg.creer_dossier", "reg.creer_dossier.kw"),
    E("mkdir -p a/b/c", "mkdir a\\b\\c", "reg.creer_plusieurs_dossiers_imbriques", "reg.creer_plusieurs_dossiers_imbriques.kw"),
    E("touch fichier.txt", "New-Item fichier.txt", "reg.creer_fichier_vide", "reg.creer_fichier_vide.kw"),
    E('echo "texte" > fichier.txt', 'echo "texte" > fichier.txt', "reg.ecrire_texte_fichier_ecrase",
      "reg.ecrire_texte_fichier_ecrase.kw", danger=True),
    E('echo "texte" >> fichier.txt', 'echo "texte" >> fichier.txt', "reg.ajouter_texte_fin_fichier",
      "reg.ajouter_texte_fin_fichier.kw"),
    E("cat fichier.txt", "cat fichier.txt", "reg.afficher_contenu_fichier", "reg.afficher_contenu_fichier.kw"),
    E("less fichier.txt", "more fichier.txt", "reg.lire_long_fichier_page", "reg.lire_long_fichier_page.kw"),
    E("head -n 5 fichier.txt", "Get-Content fichier.txt -Head 5", "reg.voir_premieres_lignes_fichier",
      "reg.voir_premieres_lignes_fichier.kw"),
    E("tail -n 5 fichier.txt", "Get-Content fichier.txt -Tail 5", "reg.voir_dernieres_lignes_fichier",
      "reg.voir_dernieres_lignes_fichier.kw"),
    E("cp source copie", "cp source copie", "reg.copier_fichier", "reg.copier_fichier.kw"),
    E("cp -r dossier copie", "cp -r dossier copie", "reg.copier_dossier_entier", "reg.copier_dossier_entier.kw"),
    E("mv ancien nouveau", "mv ancien nouveau", "reg.renommer_fichier_ou_dossier", "reg.renommer_fichier_ou_dossier.kw"),
    E("mv fichier dossier/", "mv fichier dossier\\", "reg.deplacer_fichier_dossier", "reg.deplacer_fichier_dossier.kw"),
    E("rm fichier", "rm fichier", "reg.supprimer_fichier_sans_corbeille", "reg.supprimer_fichier_sans_corbeille.kw", danger=True),
    E("rm -r dossier", "rm -r dossier", "reg.supprimer_dossier_tout_contenu", "reg.supprimer_dossier_tout_contenu.kw", danger=True),
    E("rmdir dossier", "rmdir dossier", "reg.supprimer_dossier_vide", "reg.supprimer_dossier_vide.kw"),
    # --- recherche
    E('grep "mot" fichier.txt', 'Select-String "mot" fichier.txt', "reg.chercher_mot_fichier",
      "reg.chercher_mot_fichier.kw"),
    E('grep -r "mot" .', 'Get-ChildItem -Recurse | Select-String "mot"', "reg.chercher_mot_tous_fichiers",
      "reg.chercher_mot_tous_fichiers.kw"),
    E('find . -name "*.txt"', "Get-ChildItem -Recurse -Filter *.txt", "reg.trouver_fichiers_par_leur",
      "reg.trouver_fichiers_par_leur.kw"),
    # --- protections
    E("ls -l fichier", "attrib fichier", "reg.voir_droits_fichier", "reg.voir_droits_fichier.kw"),
    E("chmod 444 fichier", "attrib +r fichier", "reg.proteger_fichier_lecture_seule", "reg.proteger_fichier_lecture_seule.kw"),
    E("chmod 644 fichier", "attrib -r fichier", "reg.enlever_protection_fichier", "reg.enlever_protection_fichier.kw"),
    E("chmod +x script.sh", "Unblock-File script.ps1", "reg.autoriser_recette_script_se",
      "reg.autoriser_recette_script_se.kw"),
    # --- système
    E("whoami", "whoami", "reg.afficher_nom_utilisateur", "reg.afficher_nom_utilisateur.kw"),
    E("date", "Get-Date", "reg.afficher_date_heure", "reg.afficher_date_heure.kw"),
    E("ps aux", "Get-Process", "reg.voir_programmes_qui_tournent", "reg.voir_programmes_qui_tournent.kw", android="ps"),
    E("top", "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10",
      "reg.voir_qui_consomme_plus", "reg.voir_qui_consomme_plus.kw"),
    E("kill PID", "Stop-Process -Id PID", "reg.arreter_programme_par_numero", "reg.arreter_programme_par_numero.kw", danger=True),
    E("pkill nom", "Stop-Process -Name nom", "reg.arreter_programme_par_nom", "reg.arreter_programme_par_nom.kw", danger=True),
    E("df -h", "Get-PSDrive", "reg.voir_espace_libre_disque", "reg.voir_espace_libre_disque.kw"),
    E("du -sh dossier", "(Get-ChildItem dossier -Recurse | Measure-Object Length -Sum).Sum",
      "reg.connaitre_taille_dossier", "reg.connaitre_taille_dossier.kw"),
    E("free -h", "Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory",
      "reg.voir_memoire_libre_maison", "reg.voir_memoire_libre_maison.kw", mac="vm_stat"),
    E("uname -a", "systeminfo", "reg.informations_systeme", "reg.informations_systeme.kw"),
    E("clear", "cls", "reg.nettoyer_ecran_terminal", "reg.nettoyer_ecran_terminal.kw"),
    E("history", "history", "reg.voir_commandes_tapees_avant", "reg.voir_commandes_tapees_avant.kw"),
    E("man commande", "Get-Help commande", "reg.lire_manuel_commande", "reg.lire_manuel_commande.kw"),
    E(installer("nom"), "winget install nom", "reg.installer_logiciel", "reg.installer_logiciel.kw"),
    E(f"{INSTALL.get(GEST, 'sudo apt install').replace('install', 'remove').replace('-S', '-R').replace(' add', ' del')} nom",
      "winget uninstall nom", "reg.desinstaller_logiciel", "reg.desinstaller_logiciel.kw", danger=True,
      mac="brew uninstall nom", android="pkg uninstall nom"),
    E({"dnf": "sudo dnf upgrade", "pacman": "sudo pacman -Syu", "zypper": "sudo zypper update",
       "apk": "sudo apk upgrade"}.get(GEST, "sudo apt update && sudo apt upgrade"),
      "winget upgrade --all", "reg.mettre_jour_tous_logiciels", "reg.mettre_jour_tous_logiciels.kw",
      mac="brew upgrade", android="pkg upgrade"),
    E(f"{'dnf search' if GEST == 'dnf' else 'pacman -Ss' if GEST == 'pacman' else 'apt search'} nom",
      "winget search nom", "reg.chercher_logiciel_installer", "reg.chercher_logiciel_installer.kw",
      mac="brew search nom", android="pkg search nom"),
    # --- réseau
    E("ping -c 3 example.com", "ping -n 3 example.com", "reg.tester_si_internet_marche", "reg.tester_si_internet_marche.kw"),
    E("ip a", "ipconfig", "reg.voir_adresse_ip", "reg.voir_adresse_ip.kw", mac="ifconfig", android="ifconfig"),
    E("curl -I https://site.com", "curl.exe -I https://site.com", "reg.verifier_si_site_repond", "reg.verifier_si_site_repond.kw"),
    E("curl -o fichier https://site.com/fichier", "curl.exe -o fichier https://site.com/fichier",
      "reg.telecharger_fichier", "reg.telecharger_fichier.kw"),
    E("nslookup site.com", "nslookup site.com", "reg.trouver_adresse_site_annuaire", "reg.trouver_adresse_site_annuaire.kw"),
    E("ssh utilisateur@machine", "ssh utilisateur@machine", "reg.se_connecter_autre_machine",
      "reg.se_connecter_autre_machine.kw"),
    # --- git
    E("git init", "git init", "reg.fabriquer_album_photo_git", "reg.fabriquer_album_photo_git.kw"),
    E("git status", "git status", "reg.voir_etat_fichiers_suivis", "reg.voir_etat_fichiers_suivis.kw"),
    E("git add fichier", "git add fichier", "reg.preparer_fichier_pour_prochain", "reg.preparer_fichier_pour_prochain.kw"),
    E('git commit -m "message"', 'git commit -m "message"', "reg.prendre_photo_fichiers_souvenir", "reg.prendre_photo_fichiers_souvenir.kw"),
    E("git log", "git log", "reg.voir_historique_versions", "reg.voir_historique_versions.kw"),
    E("git diff", "git diff", "reg.voir_qui_change", "reg.voir_qui_change.kw"),
    E("git clone https://...", "git clone https://...", "reg.recuperer_projet_existant", "reg.recuperer_projet_existant.kw"),
    # --- scripts / commandes perso
    E("alias nom='commande'", "function nom { commande }", "reg.creer_propre_commande_raccourci", "reg.creer_propre_commande_raccourci.kw"),
    E("sh script.sh", "powershell -ExecutionPolicy Bypass -File script.ps1", "reg.lancer_script", "reg.lancer_script.kw"),
    # --- Android (Termux) : piloter le téléphone
    A("termux-open-url https://site.com", "reg.ouvrir_site_ou_lien",
      "reg.ouvrir_site_ou_lien.kw"),
    A(f"{LAUNCHER} nom.du.paquet", "reg.lancer_application_avec_nom", "reg.lancer_application_avec_nom.kw"),
    A("pm list packages | grep nom", "reg.trouver_nom_secret_application",
      "reg.trouver_nom_secret_application.kw"),
    A('am start -a android.intent.action.VIEW -d "geo:0,0?q=lieu"', "reg.chercher_lieu_cartes",
      "reg.chercher_lieu_cartes.kw"),
    A("am start -a android.intent.action.DIAL -d tel:0612345678", "reg.preparer_appel_sans_appeler",
      "reg.preparer_appel_sans_appeler.kw"),
    A('am start -a android.intent.action.SENDTO -d sms:0612345678 --es sms_body "Salut"', "reg.preparer_sms",
      "reg.preparer_sms.kw"),
    A("am start -a android.intent.action.SENDTO -d mailto:ami@exemple.fr", "reg.ecrire_e_mail", "reg.ecrire_e_mail.kw"),
    A("am start -a android.settings.SETTINGS", "reg.ouvrir_reglages_telephone", "reg.ouvrir_reglages_telephone.kw"),
    A("am start -a android.settings.WIFI_SETTINGS", "reg.ouvrir_reglages_wi_fi", "reg.ouvrir_reglages_wi_fi.kw"),
    A("am start -a android.settings.BLUETOOTH_SETTINGS", "reg.ouvrir_reglages_bluetooth", "reg.ouvrir_reglages_bluetooth.kw"),
    A("termux-torch on", "reg.allumer_lampe_torche_off", "reg.allumer_lampe_torche_off.kw"),
    A("termux-battery-status", "reg.voir_etat_batterie", "reg.voir_etat_batterie.kw"),
    A("termux-volume music 10", "reg.regler_volume_0_15", "reg.regler_volume_0_15.kw"),
    A("termux-brightness 128", "reg.regler_luminosite_0_255", "reg.regler_luminosite_0_255.kw"),
    A('termux-tts-speak "Bonjour"', "reg.faire_parler_telephone", "reg.faire_parler_telephone.kw"),
    A("termux-vibrate -d 500", "reg.faire_vibrer_vibreur", "reg.faire_vibrer_vibreur.kw"),
    A('termux-toast "Coucou"', "reg.afficher_petit_message_ecran", "reg.afficher_petit_message_ecran.kw"),
    A("termux-clipboard-get", "reg.voir_contenu_presse_papier", "reg.voir_contenu_presse_papier.kw"),
    A('termux-clipboard-set "texte"', "reg.mettre_texte_presse_papier", "reg.mettre_texte_presse_papier.kw"),
    A("termux-share fichier", "reg.partager_fichier_whatsapp_mail", "reg.partager_fichier_whatsapp_mail.kw"),
    A("termux-open fichier", "reg.ouvrir_fichier_avec_appli", "reg.ouvrir_fichier_avec_appli.kw"),
    A("termux-camera-photo photo.jpg", "reg.prendre_photo", "reg.prendre_photo.kw"),
    A("termux-wifi-connectioninfo", "reg.infos_wi_fi_connecte", "reg.infos_wi_fi_connecte.kw"),
    A("termux-setup-storage", "reg.donner_termux_acces_fichiers",
      "reg.donner_termux_acces_fichiers.kw"),
    # --- recettes : suites de commandes
    R("reg.r.creer_dossier_entrer", "reg.r.creer_dossier_entrer.kw", [
        ("mkdir projet", "mkdir projet", "reg.r.creer_dossier_entrer.0"),
        ("cd projet", "cd projet", "reg.r.creer_dossier_entrer.1")]),
    R("reg.r.renommer_fichier_securite", "reg.r.renommer_fichier_securite.kw", [
        ("ls", "dir", "reg.r.renommer_fichier_securite.0"),
        ("mv ancien.txt nouveau.txt", "mv ancien.txt nouveau.txt", "reg.r.renommer_fichier_securite.1"),
        ("ls", "dir", "reg.r.renommer_fichier_securite.2")]),
    R("reg.r.faire_sauvegarde_avant", "reg.r.faire_sauvegarde_avant.kw", [
        ("cp fichier.txt fichier.txt.bak", "cp fichier.txt fichier.txt.bak", "reg.r.faire_sauvegarde_avant.0"),
        ("nano fichier.txt", "notepad fichier.txt", "reg.r.faire_sauvegarde_avant.1")]),
    R("reg.r.supprimer_dossier_sans", "reg.r.supprimer_dossier_sans.kw", [
        ("ls dossier", "dir dossier", "reg.r.supprimer_dossier_sans.0"),
        ("rm -r dossier", "rm -r dossier", "reg.r.supprimer_dossier_sans.1"),
        ("ls", "dir", "reg.r.supprimer_dossier_sans.2")]),
    R("reg.r.retrouver_fichier_perdu", "reg.r.retrouver_fichier_perdu.kw", [
        ('find ~ -name "*nom*"', "Get-ChildItem ~ -Recurse -Filter *nom*", "reg.r.retrouver_fichier_perdu.0"),
        ("cat chemin/trouvé", "cat chemin\\trouvé", "reg.r.retrouver_fichier_perdu.1")]),
    R("reg.r.proteger_fichier_important", "reg.r.proteger_fichier_important.kw", [
        ("chmod 444 fichier", "attrib +r fichier", "reg.r.proteger_fichier_important.0"),
        ("ls -l fichier", "attrib fichier", "reg.r.proteger_fichier_important.1")]),
    R("reg.r.verifier_que_internet", "reg.r.verifier_que_internet.kw", [
        ("ping -c 3 example.com", "ping -n 3 example.com", "reg.r.verifier_que_internet.0"),
        ("curl -I https://example.com", "curl.exe -I https://example.com", "reg.r.verifier_que_internet.1")]),
    R("reg.r.liberer_espace_disque", "reg.r.liberer_espace_disque.kw", [
        ("df -h", "Get-PSDrive", "reg.r.liberer_espace_disque.0"),
        ("du -sh * | sort -h", "Get-ChildItem | Sort-Object Length", "reg.r.liberer_espace_disque.1"),
        ("rm gros_fichier", "rm gros_fichier", "reg.r.liberer_espace_disque.2")]),
    R("reg.r.arreter_programme_bloque", "reg.r.arreter_programme_bloque.kw", [
        ("ps aux | grep nom", "Get-Process nom", "reg.r.arreter_programme_bloque.0"),
        ("kill PID", "Stop-Process -Name nom", "reg.r.arreter_programme_bloque.1")]),
    R("reg.r.commencer_projet_avec", "reg.r.commencer_projet_avec.kw", [
        ("mkdir projet", "mkdir projet", "reg.r.commencer_projet_avec.0"),
        ("cd projet", "cd projet", "reg.r.commencer_projet_avec.1"),
        ("git init", "git init", "reg.r.commencer_projet_avec.2"),
        ("git add .", "git add .", "reg.r.commencer_projet_avec.3"),
        ('git commit -m "début"', 'git commit -m "début"', "reg.r.commencer_projet_avec.4")]),
    R("reg.r.telecharger_fichier_dossier", "reg.r.telecharger_fichier_dossier.kw", [
        ("cd dossier", "cd dossier", "reg.r.telecharger_fichier_dossier.0"),
        ("curl -o fichier https://site.com/fichier", "curl.exe -o fichier https://site.com/fichier", "reg.r.telecharger_fichier_dossier.1")]),
    R("reg.r.creer_lancer_script", "reg.r.creer_lancer_script.kw", [
        ("echo 'echo Bonjour' > script.sh", "echo 'Write-Output Bonjour' > script.ps1", "reg.r.creer_lancer_script.0"),
        ("chmod +x script.sh", "Unblock-File script.ps1", "reg.r.creer_lancer_script.1"),
        ("./script.sh", "powershell -ExecutionPolicy Bypass -File script.ps1", "reg.r.creer_lancer_script.2")]),
    RA("reg.r.lancer_appli_dont", "reg.r.lancer_appli_dont.kw", [
        ("pm list packages | grep -i youtube", "reg.r.lancer_appli_dont.0"),
        (f"{LAUNCHER} com.google.android.youtube", "reg.r.lancer_appli_dont.1")]),
    RA("reg.r.creer_ma_commande", "reg.r.creer_ma_commande.kw", [
        (f"echo 'ouvre() {{ {LAUNCHER} \"$1\"; }}' >> ~/.bashrc", "reg.r.creer_ma_commande.0"),
        ("source ~/.bashrc", "reg.r.creer_ma_commande.1"),
        ("ouvre com.android.settings", "reg.r.creer_ma_commande.2")]),
    RA("reg.r.recuperer_fichier_telecharge", "reg.r.recuperer_fichier_telecharge.kw", [
        ("termux-setup-storage", "reg.r.recuperer_fichier_telecharge.0"),
        ("ls ~/storage/downloads", "reg.r.recuperer_fichier_telecharge.1"),
        ("cp ~/storage/downloads/fichier ~/", "reg.r.recuperer_fichier_telecharge.2")]),
    R("reg.r.creer_propre_commande", "reg.r.creer_propre_commande.kw", [
        ("alias salut='echo Salut !'", "function salut { 'Salut !' }", "reg.r.creer_propre_commande.0"),
        (f"echo \"alias salut='echo Salut !'\" >> ~/.bashrc", "Add-Content $PROFILE \"function salut { 'Salut !' }\"",
         "reg.r.creer_propre_commande.1")]),
]

for _e in REGISTRE:
    if _e["type"] == "cmd":
        core.NOMS_CONNUS.update(_e["noms"])

# ================================================================ moteur de recherche

SYNONYMES = {
    "dossier": "dossier repertoire folder directory rep",
    "fichier": "fichier file document doc texte txt",
    "creer": "creer cree creation fabriquer nouveau nouvelle generer construire init",
    "supprimer": "supprimer supprime effacer efface enlever detruire delete virer jeter",
    "voir": "voir afficher affiche lister liste montrer regarder visualiser",
    "copier": "copier copie dupliquer duplique",
    "sauvegarde": "sauvegarde sauvegarder backup bak",
    "deplacer": "deplacer deplace bouger ranger move",
    "renommer": "renommer renomme rename",
    "chercher": "chercher cherche trouver trouve rechercher recherche localiser retrouver",
    "lire": "lire ouvrir lecture read",
    "proteger": "proteger protege verrouiller bloquer securiser",
    "droit": "droit droits permission permissions acces",
    "internet": "internet reseau connexion connecte web wifi ligne",
    "site": "site url page",
    "ip": "ip adresse",
    "telecharger": "telecharger download recuperer rapatrier",
    "processus": "processus programme application appli tache logiciel",
    "arreter": "arreter tuer fermer kill stopper stop quitter",
    "espace": "espace disque place stockage",
    "taille": "taille poids gros lourd volume",
    "installer": "installer installe paquet",
    "aller": "aller entrer changer naviguer deplacer",
    "remonter": "remonter revenir retour arriere parent",
    "ou": "ou position emplacement actuel courant",
    "historique": "historique precedent anciennes",
    "qui": "qui utilisateur user compte",
    "heure": "heure date jour",
    "memoire": "memoire ram",
    "git": "git version depot commit",
    "script": "script automatiser automatique batch",
    "commande": "commande raccourci alias fonction",
    "nettoyer": "nettoyer clear ecran effacer-ecran",
    "aide": "aide manuel help documentation",
    "cache": "cache caches cachee invisible masque secret",
    "lancer": "lancer executer demarrer run",
    "ecrire": "ecrire ecris inserer mettre",
    "ajouter": "ajouter rajouter append",
    "telephone": "telephone appeler appel numero tel",
    "sms": "sms texto",
    "mail": "mail email courriel",
    "carte": "carte cartes map maps itineraire gps",
    "lampe": "lampe torche flash lumiere",
    "allumer": "allumer eteindre activer",
    "batterie": "batterie charge",
    "volume": "volume son",
    "luminosite": "luminosite",
    "photo": "photo camera appareil selfie",
    "parler": "parler voix",
    "vibrer": "vibrer vibration vibreur",
    "reglage": "reglage reglages parametre parametres",
    "partager": "partager share",
    "presse": "presse-papier presse",
    "envoyer": "envoyer",
    "regler": "regler ajuster",
    "youtube": "youtube whatsapp instagram spotify netflix",
    "modifier": "modifier editer changer",
    "tout": "tout tous toutes entier complet",
}
STOP = set("""le la les l un une des de du d pour comment je j veux voudrais aimerais faire fais
mon ma mes ton ta tes son sa ses a au aux et en sur dans quel quelle quels quelles est ce c que qu
il y on me m te t se s avec par plus peux peut puis dois faut sont etre avoir ca cela ceci
the an of to in on my me i want how do can is it""".split())


_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff]")


def mots(texte):
    """Mots en minuscules sans accents ; pour le chinois/japonais : caractères et paires de caractères."""
    t_ = unicodedata.normalize("NFD", texte.lower())
    # Accents retirés seulement sur l'alphabet latin, grec ou cyrillique : en hindi,
    # bengali, ourdou ou arabe, les signes combinants font partie des lettres.
    garde, prec = [], ""
    for c in t_:
        cat = unicodedata.category(c)
        if cat == "Mn" and prec and ord(prec) < 0x530:
            continue
        if cat[0] == "M" or c.isalnum() or c == "_":
            garde.append(c)
        else:
            garde.append(" ")
        if cat[0] != "M":
            prec = c
    out = []
    for m in "".join(garde).split():
        if _CJK.search(m):
            car = [c for c in m if _CJK.match(c)]
            out += car + [a + b for a, b in zip(car, car[1:])]
            reste = _CJK.sub(" ", m).split()
            out += reste
        else:
            out.append(m)
    return out


def racine(m):
    if len(m) > 3 and m.endswith(("s", "x")):
        m = m[:-1]
    return m[:6]


RACINE_CONCEPT = {}
for _canon, _variantes in SYNONYMES.items():
    for _v in _variantes.split():
        for _m in mots(_v):
            RACINE_CONCEPT.setdefault(racine(_m), _canon)


def concepts(texte):
    return {RACINE_CONCEPT.get(racine(m), racine(m)) for m in mots(texte) if m not in STOP}


def tx(v):
    """Traduit une clé (ou (clé, paramètres))."""
    if isinstance(v, (tuple, list)):
        return t(v[0], **v[1])
    return t(v) if v else ""


def titre(e):
    """Le titre d'une recette (« … (Android) » hors Android)."""
    s_ = t(e["titre"])
    return s_ if not e.get("android") or OSK == "android" else t("reg.titre_android", titre=s_)


_INDEX = {}


def _concepts_de(e):
    """Concepts d'une entrée : le français toujours, plus la langue choisie."""
    code = langue.courante()
    cle = (id(e), code)
    if cle not in _INDEX:
        base = e["desc"] if e["type"] == "cmd" else e["titre"]
        textes = [langue.brut(base, "fr") or "", langue.brut(e["kw"], "fr") or ""]
        if code != "fr":
            textes += [langue.brut(base, code) or "", langue.brut(e["kw"], code) or ""]
        if e["type"] == "recette":
            textes += [t(x) for _c, x in e["steps"]]
        _INDEX[cle] = concepts(" ".join(x if isinstance(x, str) else " ".join(x) for x in textes))
    return _INDEX[cle]


def chercher(requete, n=3):
    req = requete.strip().lower()
    if not req:
        return []
    premier = req.split()[0]
    qc = concepts(requete)
    scores = []
    for idx, e in enumerate(REGISTRE):
        s = 0.0
        if e["type"] == "cmd" and premier in e["noms"]:
            s = 100 + (5 if e["cmd"].lower() == req else 0) - idx * 0.01
        elif qc:
            ec = _concepts_de(e)
            commun = len(qc & ec)
            if commun:
                s = commun * 10 - len(ec - qc) * 0.5
                if qc <= ec:
                    s += 5
                if e["type"] == "recette" and commun >= 2:
                    s += 4
        if s > 0:
            if e.get("android") and OSK != "android":
                s -= 3
            scores.append((s, e))
    scores.sort(key=lambda x: -x[0])
    if not scores:
        return []
    seuil = scores[0][0] * 0.5
    return [e for s, e in scores[:n] if s >= seuil]


# images des commandes qui ne sont pas dans le lexique (les autres viennent de lexique.py)
IMAGES_EN_PLUS = {
    "rmdir": "reg.img.rmdir", "tail": "reg.img.tail",
    "echo": "reg.img.echo",
    "clear": "reg.img.clear", "cls": "reg.img.clear",
    "history": "reg.img.history", "man": "reg.img.man",
    "get-help": "reg.img.man", "uname": "reg.img.uname",
    "systeminfo": "reg.img.uname", "free": "reg.img.free",
    "top": "reg.img.top", "pkill": "reg.img.pkill",
    "rm": "reg.img.rm",
    "termux-open-url": "reg.img.termux-open-url", "am": "reg.img.am",
    "pm": "reg.img.pm", "termux-torch": "reg.img.termux-torch",
    "termux-battery-status": "reg.img.termux-battery-status",
    "termux-tts-speak": "reg.img.termux-tts-speak", "termux-vibrate": "reg.img.termux-vibrate",
    "termux-toast": "reg.img.termux-toast", "termux-clipboard-get": "reg.img.termux-clipboard-get",
    "termux-clipboard-set": "reg.img.termux-clipboard-get", "termux-volume": "reg.img.termux-volume",
    "termux-brightness": "reg.img.termux-brightness", "termux-share": "reg.img.termux-share",
    "termux-open": "reg.img.termux-open", "termux-camera-photo": "reg.img.termux-camera-photo",
    "termux-wifi-connectioninfo": "reg.img.termux-wifi-connectioninfo",
    "termux-setup-storage": "reg.img.termux-setup-storage",
}


def image(e):
    """L'image (la maison) d'une commande trouvée, ou None."""
    cle = e["cmd"].split()[0].lower()
    return lexique.images().get(cle) or (t(IMAGES_EN_PLUS[cle]) if cle in IMAGES_EN_PLUS else None)


def afficher(resultats, nom):
    """Lignes à afficher, commandes piégées contre le copier-coller."""
    if not resultats:
        return [" " + t("reg.rien", nom=nom), f" {DIM}" + t("reg.rien.essaie") + RESET]
    out = []
    for e in resultats:
        if e["type"] == "cmd":
            out.append(f" {BOLD}{t(e['desc'])}{RESET}")
            out.append(f"   {fg(226)}➜ `{piege(e['cmd'])}`{RESET}")
            if image(e):
                out.append(f"   {fg(147)}🏠 {image(e)}{RESET}")
            if e["danger"]:
                out.append(f"   {fg(203)}" + t("reg.danger") + RESET)
            if e["note"]:
                out.append(f"   {DIM}{tx(e['note'])}{RESET}")
        else:
            out.append(f" {BOLD}" + t("reg.recette", titre=titre(e)) + RESET)
            for i, (cmd, expl) in enumerate(e["steps"], 1):
                out.append(f"   {i}. {fg(226)}`{piege(cmd)}`{RESET}  {DIM}{t(expl)}{RESET}")
        out.append("")
    return out


def memoriser(state, resultats):
    """Les commandes consultées rapportent un bonus si on les tape dans les 15 min."""
    import time
    now = time.time()
    for e in resultats:
        cmds = [e["cmd"]] if e["type"] == "cmd" else [c for c, _ in e["steps"]]
        for c in cmds:
            w = core.first_word(c)
            if w:
                state["cherche"][w] = now
