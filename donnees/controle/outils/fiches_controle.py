"""Les données du Poste de Contrôle (donnees/controle.json), ses fiches notions (charte de rigueur, docs/programme.md
§ 7.1) et sa place dans donnees/programme.json : le monde (prérequis = niveaux 0 à 6 du tronc, paliers, ponts vers la
Salle des Rouages, la Citadelle, la Forge, l'Observatoire et la Guilde, attirance, exploit « la vague » : tous les
suspects d'une vague arrêtés, le veilleur épargné ; variantes EXISTANTES favorisées), les maths des étapes et les étapes
rejouées dans bash.

    python3 donnees/controle/outils/fiches_controle.py    écrit donnees/controle.json, donnees/programme.json et leurs copies

Le contenu existant n'est pas changé (§ 2.19) : machines0, systeme1 (free, df, du), dortoir0, systeme2 (sleep &, jobs,
kill %1), dortoir1 (ps | wc -l, le téléphone) et scripts2 (le .bashrc) restent dans le tronc et les ailes ; le monde les
cite (« reutilise ») et ses étapes vont plus loin. Chaque cas « vrai_terminal » est rejoué dans un bash neuf par
pc/outils/rejeu_bash.py, dans un terrain jetable. Lecture seule sur le vrai système, jamais de sudo.
"""
import json
import shutil
from pathlib import Path

D = Path(__file__).resolve().parents[3]


def donnees_controle():
    return {
        "note": "Généré par donnees/controle/outils/fiches_controle.py ; lu par pc/tg/controle.py et Controle.kt",
        "entrepot": {"caisses": ["cartes_du_ciel", "journaux_anciens", "pieces_de_rechange", "sons_du_moteur"],
                     "tailles_kio": [8, 32, 128, 512]},
        "journal": {"jour": "2026-11-01", "total": 24, "alertes": [3, 4, 5, 6],
                    "infos": ["moteur=ok temp=41", "ventilation=ok", "boucliers=100%", "radar=ok cibles=0",
                              "eau=ok niveau=87%", "porte_nord=fermee", "ronde=ok", "batterie=ok charge=93%"],
                    "textes_alerte": ["moteur=chaud temp=88", "porte_sud=ouverte", "radar=perdu", "eau=fuite niveau=12%",
                                      "batterie=faible charge=8%", "boucliers=12%"]},
        "sac": {"lignes": ["export POSTE=controle", "export EQUIPAGE=4", "alias rondes='ls entrepot'"]},
        "cron": {"exemples": ["0 7 * * 1-5 echo REVEIL >> reveil.log", "*/30 * * * * echo RONDE >> ronde.log"],
                 "situations": [{"id": "matin_semaine", "rep": "30 7 * * 1-5"}, {"id": "midi", "rep": "0 12 * * *"},
                                {"id": "quart_heure", "rep": "*/15 * * * *"}, {"id": "dimanche_soir", "rep": "0 20 * * 0"},
                                {"id": "premier_du_mois", "rep": "0 9 1 * *"}, {"id": "lundi_8h", "rep": "0 8 * * 1"}]},
        "familles": {"lettres": "dap",
                     "distributions": [{"id": "fedora", "nom": "Fedora", "rep": "d"},
                                       {"id": "almalinux", "nom": "AlmaLinux", "rep": "d"},
                                       {"id": "debian", "nom": "Debian", "rep": "a"},
                                       {"id": "ubuntu", "nom": "Ubuntu", "rep": "a"},
                                       {"id": "arch", "nom": "Arch Linux", "rep": "p"}]},
        # le magasin de paquets : le premier dont la base existe ; on LIT seulement (installer : avec un adulte)
        "magasins": [{"id": "zypper", "base": "/etc/zypp", "compte": "rpm -qa | wc -l",
                      "installer": "sudo zypper install cowsay", "maj": "sudo zypper update"},
                     {"id": "dnf", "base": "/usr/lib/sysimage/rpm", "compte": "rpm -qa | wc -l",
                      "installer": "sudo dnf install cowsay", "maj": "sudo dnf upgrade"},
                     {"id": "apt", "base": "/var/lib/dpkg/status", "compte": "dpkg -l | grep -c '^ii'",
                      "installer": "sudo apt install cowsay", "maj": "sudo apt update && sudo apt upgrade"},
                     {"id": "pacman", "base": "/var/lib/pacman/local", "compte": "pacman -Q | wc -l",
                      "installer": "sudo pacman -S cowsay", "maj": "sudo pacman -Syu"},
                     {"id": "apk", "base": "/lib/apk/db/installed", "compte": "apk info | wc -l",
                      "installer": "sudo apk add cowsay", "maj": "sudo apk upgrade"}],
        "equipage": {"base": ["root:x:0:0:root:/root:/bin/bash", "daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin",
                              "capitaine:x:1000:1000:La capitaine:/home/capitaine:/bin/bash"], "uid_depart": 1001},
        "vague": {"suspects": ["bavard_fictif", "bruyant_fictif", "copieur_fictif", "fouineur_fictif", "glouton_fictif"],
                  "par_vague": 3, "veilleur": "veilleur_fictif", "secondes": 900},
        # le tableau de bord de la vue déployée : la première règle qui correspond (lit / arrete / change)
        "tableau": {"regles": [
            {"motif": r"^(sudo\s+)?(dnf|yum|apt|apt-get|zypper|pacman|brew)\s+(install|remove|upgrade|update|-S)",
             "jauge": "magasin", "sens": "change"},
            {"motif": r"^(rpm\s+-q|dpkg(-query)?\s+-l|apt\s+(list|search|show)|dnf\s+(list|search|info)|pacman\s+-Q)",
             "jauge": "magasin", "sens": "lit"},
            {"motif": r"^(sudo\s+)?systemctl\s+(--user\s+)?(start|stop|restart|reload|enable|disable)\b",
             "jauge": "services", "sens": "change"},
            {"motif": r"^(systemctl|get-service|gsv)\b", "jauge": "services", "sens": "lit"},
            {"motif": r"^(kill|pkill|killall|stop-process|spps)\b", "jauge": "habitants", "sens": "arrete"},
            {"motif": r"^(ps|top|htop|pgrep|jobs|get-process|gps)\b", "jauge": "habitants", "sens": "lit"},
            {"motif": r"^(free|vmstat)\b", "jauge": "memoire", "sens": "lit"},
            {"motif": r"^(df|du|get-psdrive)\b", "jauge": "entrepot", "sens": "lit"},
            {"motif": r"^(uptime|nproc)\b", "jauge": "charge", "sens": "lit"},
            {"motif": r"^(export|alias|source|unset)\s|^\.\s+\S", "jauge": "sac", "sens": "change"},
            {"motif": r"^(env|printenv|which)\b|^echo\s+.*\$(HOME|PATH|USER|SHELL|PWD|LANG|POSTE|COULEUR)\b",
             "jauge": "sac", "sens": "lit"},
            {"motif": r"^(journalctl|dmesg)\b|^tail\s+(-\w+\s+)*-\w*f", "jauge": "carnet", "sens": "lit"},
            {"motif": r"^crontab\s+-l\b", "jauge": "reveil", "sens": "lit"},
            {"motif": r"^crontab\b", "jauge": "reveil", "sens": "change"},
            {"motif": r"^(sudo\s+)?(useradd|userdel|usermod|adduser|passwd)\b", "jauge": "equipage", "sens": "change"},
            {"motif": r"^(id|whoami|groups)\b|/etc/passwd", "jauge": "equipage", "sens": "lit"}]},
        "couleurs": {"habitants": 141, "memoire": 78, "entrepot": 179, "charge": 203, "sac": 215, "carnet": 229,
                     "reveil": 215, "magasin": 117, "services": 141, "equipage": 117},
    }


def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"ct.f.{nid}.enfant", "grands": f"ct.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"ct.f.{nid}.limite", "idees_fausses": [f"ct.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


JOURNAL_TEST = "printf 'INFO a\\nALERTE b\\nINFO c\\nALERTE d\\n' > j.log"
FICHES = dict([
    fiche("processus", r"(/proc\b|\$\$|\$pid\b|^(top|htop)\b|^(tg\s+)?controle\s+habitants?\b|^(sleep|start-sleep)\s+\d+\s*$)", [
        {"cmd": "echo $$ | grep -c '^[0-9][0-9]*$'", "sortie": "1"},
        {"cmd": "head -1 /proc/self/status", "motif": r"^Name:\s+head$", "outil": "/proc/self/status"},
        {"cmd": "ls /proc/$$ | grep -c '^status$'", "sortie": "1", "outil": "/proc/self"},
        {"cmd": "top -bn1 | head -1", "motif": "load average", "outil": "top"}],
        ["proc(5), le système de fichiers /proc : https://man7.org/linux/man-pages/man5/proc.5.html",
         "Bash, Special Parameters ($$) et Job Control : https://www.gnu.org/software/bash/manual/html_node/Special-Parameters.html",
         "POSIX.1-2024, ps : https://pubs.opengroup.org/onlinepubs/9799919799/utilities/ps.html",
         "procps, top(1) : https://man7.org/linux/man-pages/man1/top.1.html"]),
    fiche("jauges", r"(^(tg\s+)?controle\s+(jauges?|entrepot)\b|^nproc\b|entrepot)", [
        {"cmd": "df -h . | head -1", "motif": r"^Filesystem\s+Size\s+Used\s+Avail\s+Use%\s+Mounted on$"},
        {"prepare": "printf '%32768s' '' > a.bin", "cmd": "du -k a.bin",
         "motif": r"^\d+\s+a\.bin$"},
        {"cmd": "echo $(( 3 * 100 / 4 ))%", "sortie": "75%"},
        {"cmd": "nproc | grep -c '^[0-9][0-9]*$'", "sortie": "1", "outil": "nproc"}],
        ["procps, free(1) et uptime(1) : https://man7.org/linux/man-pages/man1/free.1.html",
         "GNU coreutils, df, du et nproc : https://www.gnu.org/software/coreutils/manual/",
         "proc(5), /proc/meminfo (MemAvailable) et /proc/loadavg : https://man7.org/linux/man-pages/man5/proc.5.html"]),
    fiche("environnement", r"(\$HOME\b|\$PATH\b|\$POSTE\b|\$env:|^export\b|^env\b|^printenv\b|^which\b|^get-command\b|"
                           r"^(bash|sh|zsh)\s+-c\b|^(tg\s+)?controle\s+(path|sac)\b|sac_a_dos)", [
        {"cmd": "export COULEUR=bleu; bash -c 'echo $COULEUR'", "sortie": "bleu"},
        {"cmd": "COULEUR=bleu; bash -c 'echo \"[$COULEUR]\"'", "sortie": "[]"},
        {"cmd": "echo $PATH | tr ':' '\\n' | head -1", "motif": "^/"},
        {"prepare": "printf 'export POSTE=controle\\n' > sac.sh", "cmd": "source ./sac.sh; echo $POSTE", "sortie": "controle"},
        {"cmd": "which ls", "motif": "/ls$"}],
        ["POSIX.1-2024, Environment Variables (chapitre 8) : https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap08.html",
         "Bash, Bourne Shell Builtins (export, source) : https://www.gnu.org/software/bash/manual/html_node/Bourne-Shell-Builtins.html",
         "environ(7) : https://man7.org/linux/man-pages/man7/environ.7.html"]),
    fiche("journaux_systeme", r"(carnet_de_bord|^journalctl\b|^logcat\b|^dmesg\b|^tail\s+(-\w+\s+)*-\w*[fF]|"
                              r"^(tg\s+)?controle\s+(journal|alertes)\b|alerte)", [
        {"prepare": JOURNAL_TEST, "cmd": "grep -c ALERTE j.log", "sortie": "2"},
        {"prepare": JOURNAL_TEST, "cmd": "tail -n 1 j.log", "sortie": "ALERTE d"},
        {"prepare": JOURNAL_TEST, "cmd": "timeout 1 tail -f j.log >/dev/null; echo code $?", "sortie": "code 124"},
        {"cmd": "journalctl --user -n 1 --no-pager >/dev/null 2>&1; echo lu", "sortie": "lu", "outil": "journalctl"}],
        ["journalctl(1), systemd : https://www.freedesktop.org/software/systemd/man/latest/journalctl.html",
         "dmesg(1), util-linux : https://man7.org/linux/man-pages/man1/dmesg.1.html",
         "GNU coreutils, tail (-n, -f) : https://www.gnu.org/software/coreutils/manual/html_node/tail-invocation.html",
         "Filesystem Hierarchy Standard 3.0, /var/log : https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch05s10.html"]),
    fiche("cron", r"(crontab|^(tg\s+)?controle\s+(cron|r[eé]veils?)\b)", [
        {"cmd": "crontab -l >/dev/null 2>&1; echo lu", "sortie": "lu", "outil": "crontab"},
        {"prepare": "printf '30 7 * * * echo DRING\\n' > r.crontab", "cmd": "cut -d' ' -f1-5 r.crontab", "sortie": "30 7 * * *"},
        {"cmd": "echo $((45 % 15))", "sortie": "0"}],
        ["POSIX.1-2024, crontab : https://pubs.opengroup.org/onlinepubs/9799919799/utilities/crontab.html",
         "crontab(5), cronie / Vixie cron (les 5 champs, */n, jour du mois OU de la semaine) : https://man7.org/linux/man-pages/man5/crontab.5.html",
         "systemd.timer(5), l'autre réveil des systèmes récents : https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html"]),
    fiche("distributions", r"(/etc/(os|lsb)-release|^(tg\s+)?controle\s+(distribution|familles?|installer)\b|win32_operatingsystem)", [
        {"cmd": "grep -c '^ID=' /etc/os-release", "sortie": "1", "outil": "/etc/os-release"},
        {"cmd": ". /etc/os-release; echo \"$ID\" | grep -c '^[a-z0-9._-]*$'", "sortie": "1", "outil": "/etc/os-release"}],
        ["os-release(5), freedesktop.org : https://www.freedesktop.org/software/systemd/man/latest/os-release.html",
         "DistroWatch, les familles de distributions : https://distrowatch.com/dwres.php?resource=major",
         "Fedora, essayer et installer (support live, machine virtuelle) : https://docs.fedoraproject.org/en-US/fedora/latest/",
         "Debian, Manuel d'installation : https://www.debian.org/releases/stable/installmanual"]),
    fiche("paquets", r"(^rpm\s+-q|^dpkg(-query)?\s+-l|^(apt|dnf|pacman|zypper)\b|^(tg\s+)?controle\s+magasin\b)", [
        {"cmd": "rpm -qa | wc -l", "motif": r"^\d+$", "outil": "rpm", "si": "test -d /usr/lib/sysimage/rpm"},
        {"cmd": "dpkg -l | grep -c '^ii'", "motif": r"^\d+$", "outil": "dpkg", "si": "test -f /var/lib/dpkg/status"}],
        ["DNF, Command Reference : https://dnf.readthedocs.io/en/latest/command_ref.html ; rpm(8) : https://rpm.org/",
         "Debian, APT et dpkg (Debian Reference, chapitre 2) : https://www.debian.org/doc/manuals/debian-reference/ch02.fr.html",
         "Arch Wiki, pacman : https://wiki.archlinux.org/title/Pacman"]),
    fiche("services", r"(^systemctl\b|get-service|^(tg\s+)?controle\s+services?\b)", [
        {"cmd": "systemctl --version | head -1", "motif": r"^systemd \d+", "outil": "systemctl"}],
        ["systemctl(1), systemd : https://www.freedesktop.org/software/systemd/man/latest/systemctl.html",
         "systemd.service(5) : https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html",
         "Microsoft, Get-Service (PowerShell) : https://learn.microsoft.com/powershell/module/microsoft.powershell.management/get-service"]),
    fiche("utilisateurs_systeme", r"(/etc/passwd|equipage|^(tg\s+)?controle\s+(useradd|equipage)\b|get-localuser)", [
        {"cmd": "cut -d: -f1 /etc/passwd | head -1", "sortie": "root"},
        {"prepare": "printf 'root:x:0:0::/root:/bin/bash\\nmousse:x:1001:1001::/home/mousse:/bin/bash\\n' > e.txt",
         "cmd": "grep mousse e.txt | cut -d: -f3", "sortie": "1001"}],
        ["passwd(5) : https://man7.org/linux/man-pages/man5/passwd.5.html",
         "useradd(8), shadow-utils : https://man7.org/linux/man-pages/man8/useradd.8.html",
         "Linux Standard Base, Users & Groups (UID 0 root, UID système, UID ≥ 1000)"]),
    fiche("poste_alerte", r"^(tg\s+)?controle\s+(alerte|tableau|arrete|ps)\b", [
        {"cmd": "bash -c 'exec -a glouton_fictif sleep 30' & sleep 0.3; ps -o args= -p $! ; kill $!",
         "sortie": "glouton_fictif 30"},
        {"cmd": "bash -c 'exec -a veilleur_fictif sleep 30' & p=$!; sleep 0.3; kill $p; wait $p 2>/dev/null; "
                "ps -p $p > /dev/null; echo \"vivant $?\"", "sortie": "vivant 1"}],
        ["kill(1) et signal(7) (SIGTERM) : https://man7.org/linux/man-pages/man7/signal.7.html",
         "Bash, exec -a (le nom donné au processus) : https://www.gnu.org/software/bash/manual/html_node/Bourne-Shell-Builtins.html",
         "ANSSI, Recommandations de sécurité relatives à un système GNU/Linux (surveiller, moindre privilège)"]),
])

CONTROLE = {"id": "controle", "types": ["machine", "roche"], "requis": ["n0", "n1", "n2", "n3", "n4", "n5", "n6"],
            "paliers": [f"ct{i}" for i in range(8)], "chapitre": "controle",
            "attirance": {"cmds": ["ps", "kill", "free", "df", "jobs", "crontab", "systemctl", "journalctl"],
                          "familles": ["Constructs"]},
            "ponts": {"os_release": ["machines"], "ps_kill": ["citadelle"], "bashrc": ["forge"], "export": ["observatoire"],
                      "paquets": ["guilde"], "ressources": ["machines"]},
            "reutilise": {"lecons": ["machines0", "systeme1", "dortoir0", "systeme2", "dortoir1", "scripts2"]},
            "exploits": [{"id": "controle.vague", "nom": "recomp.controle.vague", "recompense": "variante"}],
            "maths": ["pourcentages", "division", "modulo"],
            "variantes_reservees": ["ressortine:mecanique", "parasouris:neon", "pavegarde:montagne"]}

ETAPES = {"ct2.6": {"maths": ["pourcentages", "division"]}, "ct5.3": {"maths": ["modulo"]}}


def rejeu():
    return {
        "ct0.1": {"contient": ["consignes_du_poste.txt", "entrepot", "sac_a_dos.sh", "reveils.crontab", "equipage.txt"],
                  "pourquoi": "hist.ct0.1.bravo : des consignes, un entrepôt, un sac à dos, des réveils, l'équipage"},
        "ct1.1": {"motif": r"^\d+$", "pourquoi": "hist.ct1.1.bravo : le numéro (PID) de ton terminal"},
        "ct1.2": {"contient": ["status", "cmdline"], "outil": "/proc/self", "pourquoi": "hist.ct1.2.bravo : le miroir"},
        "ct1.3": {"motif": r"^Name:\s+bash$", "outil": "/proc/self/status", "pourquoi": "hist.ct1.3.bravo : Name: bash"},
        "ct1.7": {"motif": r"^\[1\]\+\s+Running\s+sleep 60 &$", "pourquoi": "hist.ct1.7.bravo : [1]+ Running"},
        "ct1.8": {"code": 0, "pourquoi": "hist.ct1.8.bravo : la tâche n° 1 est arrêtée"},
        "ct1.9": {"motif": "load average", "outil": "top", "pourquoi": "hist.ct1.9.bravo : la première ligne de top"},
        "ct2.0": {"motif": r"^\s+total\s+used\s+free", "outil": "free", "pourquoi": "hist.ct2.0.bravo : total, used, free"},
        "ct2.1": {"motif": r"^Filesystem\s+Size\s+Used\s+Avail", "pourquoi": "hist.ct2.1.bravo : Size, Used, Avail, Use%"},
        "ct2.2": {"egal_jeu": "entrepot", "pourquoi": "hist.ct2.2.bravo : la caisse la plus lourde"},
        "ct2.4": {"motif": "load average", "outil": "uptime", "pourquoi": "hist.ct2.4.bravo : load average"},
        "ct2.5": {"egal_jeu": "coeurs", "outil": "nproc", "pourquoi": "hist.ct2.5.bravo : les cœurs (comme la Salle des Rouages)"},
        "ct3.0": {"sortie": "{HOME}", "pourquoi": "hist.ct3.0.bravo : ta maison"},
        "ct3.1": {"egal_jeu": "path", "pourquoi": "hist.ct3.1.bravo : un dossier par ligne"},
        "ct3.3": {"motif": r"/ls$", "pourquoi": "hist.ct3.3.bravo : le chemin de ls"},
        "ct3.5": {"sortie": "bleu", "pourquoi": "hist.ct3.5.bravo : l'habitant a emporté la variable"},
        "ct3.7": {"motif": r"^export POSTE=controle$", "pourquoi": "hist.ct3.7.bravo : export et alias"},
        "ct3.9": {"sortie": "controle", "pourquoi": "hist.ct3.9.bravo : le sac à dos est chargé"},
        "ct4.1": {"lignes": 5, "pourquoi": "hist.ct4.1.bravo : les 5 dernières lignes"},
        "ct4.2": {"egal_jeu": "alertes", "pourquoi": "hist.ct4.2.bravo : le nombre de lignes ALERTE"},
        "ct5.2": {"motif": r"^\S+ \S+ \S+ \S+ \S+ echo ", "pourquoi": "hist.ct5.2.bravo : 5 champs, puis la commande"},
        "ct6.0": {"motif": r"^ID=", "outil": "/etc/os-release", "pourquoi": "hist.ct6.0.bravo : ID= le nom court"},
        "ct6.5": {"motif": r"^\d+$", "outil": "/usr/lib/sysimage/rpm", "pourquoi": "hist.ct6.5.bravo : un nombre de paquets"},
        "ct6.6": {"egal_jeu": "paquets", "outil": "/var/lib/dpkg/status", "pourquoi": "hist.ct6.6.bravo : le jeu compte pareil"},
        "ct6.10": {"motif": r"^root$", "outil": "/etc/passwd", "pourquoi": "hist.ct6.10.bravo : root, le premier"},
        "ct6.12": {"motif": r":1001:1001::/home/", "pourquoi": "hist.ct6.12.bravo : le nouveau membre, UID 1001"},
        "ct7.1": {"egal_jeu": "suspects", "pourquoi": "hist.ct7.1.bravo : les suspects et le veilleur"},
    }


def main():
    G = donnees_controle()
    texte_g = json.dumps(G, ensure_ascii=False, indent=1) + "\n"
    (D / "donnees/controle.json").write_text(texte_g, encoding="utf-8")
    for c in ("pc/tg/controle.json", "app/src/main/assets/controle.json"):
        (D / c).write_text(texte_g, encoding="utf-8")
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    P["mondes"] = [CONTROLE if m["id"] == "controle" else m for m in P["mondes"]]
    if not any(m["id"] == "controle" for m in P["mondes"]):
        P["mondes"].append(CONTROLE)
    for cle in ("etapes", "rejeu"):                   # les étapes du Poste : exactement celles d'ici
        P[cle] = {k: v for k, v in P[cle].items() if not (k.startswith("ct") and k.split(".")[0][2:].isdigit())}
    P["etapes"].update(ETAPES)
    R = rejeu()
    P["rejeu"].update(R)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    print(f"{len(FICHES)} fiches du Poste de Contrôle, {len(R)} étapes rejouées ; controle.json écrit")


if __name__ == "__main__":
    main()
