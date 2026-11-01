"""Les vecteurs communs du Poste de Contrôle (Python ↔ Kotlin) : donnees/controle/vecteurs.json.

    python3 pc/outils/vecteurs_controle.py              écrit les vecteurs (depuis pc/tg/controle.py et pc/tg/deploie.py)
    python3 pc/outils/vecteurs_controle.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

Les caisses de l'entrepôt (tailles mélangées, la plus lourde, l'empreinte de leur contenu), les pourcentages et les
jauges, le compte du PATH, le carnet de bord de chaque partie et ses alertes, les réveils cron (champs, équivalences,
prochaine sonnerie, la situation de la partie), les familles de distributions mélangées et la correction des réponses,
la distribution reconnue dans /etc/os-release, le registre de l'équipage, la vague (suspects tirés, numéros simulés,
bilan), le tableau de bord (vue déployée) : tests/jvm/Controle.kt vérifie que l'appli Android donne EXACTEMENT les
mêmes résultats.
"""
import datetime
import hashlib
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import deploie, langue, controle as K  # noqa: E402

FICHIER = RACINE / "donnees" / "controle" / "vecteurs.json"


def vecteurs():
    langue.definir("fr")
    graines = ["1:0", "2:1730000000", "7:42", "partie:3", "9:1761900000", "4:1700000123", "5:5", "8:1762000000"]
    parties = []
    for g in graines:
        parties.append({"graine": g, "caisses": [[n, k] for n, k in K.caisses(g)], "lourde": K.caisse_lourde(g),
                        "sha_lourde": hashlib.sha256(K.caisse_octets(g, K.caisse_lourde(g))).hexdigest(),
                        "journal": K.journal_lignes(g), "alertes": K.nb_alertes(g),
                        "cron": K.cron_situation(g)["id"], "familles": [[n, i, r] for n, i, r in K.familles_cartes(g)],
                        "vagues": [{"n": n, "suspects": K.vague_suspects(g, n), "pids": K.pids_simules(g, n)} for n in (1, 2, 3)]})
    caisse_rep = []
    for g in graines[:3]:
        for r in (K.caisse_lourde(g), K.caisse_lourde(g).upper(), K.caisse_lourde(g) + ".bin", "entrepot/" + K.caisse_lourde(g),
                  "cartes_du_ciel", "", "  " + K.caisse_lourde(g) + "  "):
            caisse_rep.append({"graine": g, "reponse": r, "ok": K.caisse_ok(r, g)})
    pourcents = [{"u": u, "t": t_, "p": K.pourcentage(u, t_), "jauge": K.jauge(K.pourcentage(u, t_))}
                 for u, t_ in ((0, 10), (1, 3), (2, 3), (5, 10), (999, 1000), (1, 200), (3, 0), (7, 7), (123456, 8000000))]
    paths = []
    for p in ("/usr/bin:/bin", "/usr/local/bin:/usr/bin:/bin:/usr/bin", "/a::/b", "", "C:\\x;C:\\y"):
        for r in ("1", "2", "3", "4", "5", "x", ""):
            paths.append({"path": p, "win": ";" in p, "reponse": r, "ok": K.path_ok(r, p, ";" in p)})
    lignes = ["30 7 * * 1-5 echo REVEIL", "*/15 * * * * echo R", "0 20 * * 7 x", "0 20 * * 0 x", "0,15,30,45 * * * * a",
              "0 9 1 * * a", "0 12 * * *", "60 * * * * a", "* 24 * * * a", "# 0 7 * * *", "", "1-5/2 8-18/5 * * * a",
              "5 4 1,15 * 3 a", "0 0 29 2 * a", "* * * * a", "*/0 * * * * a", "3-1 * * * * a", "0 7 * 13 * a",
              "@daily x", "7 7 7 7 7 x"]
    crons = []
    for l in lignes:
        c = K.cron(l)
        crons.append({"ligne": l, "champs": [sorted(x) for x in c] if c else None})
    depuis = [datetime.datetime(2026, 11, 1, 6, 0), datetime.datetime(2026, 12, 31, 23, 59), datetime.datetime(2027, 2, 27, 12, 30),
              datetime.datetime(2026, 11, 6, 7, 30)]
    prochaines = []
    for l in lignes:
        for d in depuis:
            p = K.prochaine(l, d)
            prochaines.append({"ligne": l, "depuis": d.strftime("%Y-%m-%d %H:%M"), "prochaine": p.strftime("%Y-%m-%d %H:%M") if p else None})
    pareils = [{"a": a, "b": b, "pareil": K.cron_pareil(a, b)} for a, b in
               (("*/15 * * * *", "0,15,30,45 * * * *"), ("0 20 * * 0", "0 20 * * 7"), ("30 7 * * 1-5", "30 7 * * 1,2,3,4,5"),
                ("0 12 * * *", "0 0 * * *"), ("0 9 1 * *", "00 09 01 * *"), ("x", "x"), ("0 8 * * 1", "0 8 * * MON"))]
    cron_rep = []
    for g in graines[:4]:
        s = K.cron_situation(g)
        for r in (s["rep"], f'"{s["rep"]}"', " ".join(s["rep"].split()) + "  ", "0 0 * * *", "? ? ? ? ?", "*/15 * * * *"):
            cron_rep.append({"graine": g, "reponse": r, "ok": K.cron_ok(r, g)})
    quiz = []
    for g in graines[:3]:
        c = K.familles_cartes(g)
        bon = [r for _n, _i, r in c]
        for rep in (bon, list(reversed(bon)), ["d"] * 5, ["DNF", "apt", "Pacman", "a", "a"], ["x"] * 5, bon[:4], []):
            ok, justes = K.quiz_justes(c, rep, "dap")
            quiz.append({"graine": g, "rep": rep, "ok": ok, "justes": [[n, i] for n, i in justes]})
    osr_textes = ['NAME="Fedora Linux"\nVERSION="43 (Workstation Edition)"\nID=fedora\nVERSION_ID=43\n',
                  'PRETTY_NAME="Ubuntu 24.04.1 LTS"\nNAME="Ubuntu"\nID=ubuntu\nID_LIKE=debian\n',
                  'NAME="Linux Mint"\nID=linuxmint\nID_LIKE="ubuntu debian"\n', "# rien\n", "",
                  'NAME="Arch Linux"\nID=arch\n', "NAME='openSUSE Tumbleweed'\nID=\"opensuse-tumbleweed\"\nID_LIKE=\"opensuse suse\"\n"]
    distrib = []
    for txt in osr_textes:
        osr = K.os_release_de(txt)
        for r in ("fedora", "Fedora", "ubuntu", "debian", "linuxmint", "linux", "arch", "opensuse-tumbleweed", "suse", "", "Ubuntu "):
            distrib.append({"texte": txt, "osr": osr, "reponse": r, "ok": K.distribution_ok(r, osr)})
    base = K.equipage_texte()
    equipage = []
    for nom in ("mousse", "Mousse", "capitaine", "1abc", "_robot", "a" * 17, "cuistot-2", "", "élève"):
        txt, uid = K.equipage_ajoute(base, nom)
        equipage.append({"nom": nom, "valide": K.nom_valide(nom), "texte": txt, "uid": uid, "nouveaux": K.nouveaux_membres(txt)})
    txt2, _u = K.equipage_ajoute(base, "mousse")
    txt3, uid3 = K.equipage_ajoute(txt2, "vigie")
    equipage.append({"nom": "vigie", "valide": True, "texte": txt3, "uid": uid3, "nouveaux": K.nouveaux_membres(txt3)})
    bilans = [{"suspects": s, "veilleur": v, "bilan": K.bilan_vague(s, v)} for s in ([], [[1, "a"]]) for v in (True, False)]
    crontab = ["# x\n0 7 * * 1-5 echo A\n\n*/15 * * * * echo B >> r.log\n60 * * * * x\n0 7 * * *\n", "", "# seul\n"]
    crontabs = [{"texte": x, "lignes": [[l, ok] for l, ok in K.lignes_crontab(x)]} for x in crontab]
    cmds = ["ps aux | grep fictif", "kill 1234 5678", "free -h && df -h .", "export COULEUR=bleu; bash -c 'echo $COULEUR'",
            "sudo dnf install cowsay", "rpm -qa | wc -l", "systemctl list-units --type=service", "sudo systemctl restart cups",
            "journalctl --user -n 20", "tail -f carnet_de_bord.log", "crontab -l", "crontab -e", "useradd mousse",
            "cut -d: -f1 /etc/passwd | head -3", "echo $HOME", "echo bonjour", "nproc", "uptime", "du -sh *", "jobs; fg",
            "source sac_a_dos.sh", ". ./sac.sh", "whoami", "ls -l", "Get-Service | Select-Object -First 5", "top"]
    tableau = [{"ligne": c, "tableaux": [list(x) for x in K.tableaux_de(c)],
                "deploie": [[x["seg"], x["cmd"], x["jauge"], x["sens"]] for x in deploie.tableaux(c)]} for c in cmds]
    return {"note": "Généré par pc/outils/vecteurs_controle.py ; vérifié par tests/jvm/Controle.kt",
            "parties": parties, "caisse_rep": caisse_rep, "pourcents": pourcents, "paths": paths, "crons": crons,
            "prochaines": prochaines, "pareils": pareils, "cron_rep": cron_rep, "quiz": quiz, "distrib": distrib,
            "equipage": equipage, "bilans": bilans, "crontabs": crontabs, "tableau": tableau}


def main():
    texte = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        ok = FICHIER.exists() and FICHIER.read_text(encoding="utf-8") == texte
        print("vecteurs du Poste de Contrôle à jour" if ok else "vecteurs du Poste de Contrôle PAS à jour : relancer pc/outils/vecteurs_controle.py")
        sys.exit(0 if ok else 1)
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"écrit {FICHIER.relative_to(RACINE)}")


if __name__ == "__main__":
    main()
