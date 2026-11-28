"""Les vecteurs communs de la Salle des Rouages (Python ↔ Kotlin) : donnees/machines/vecteurs.json.

    python3 pc/outils/vecteurs_machines.py              écrit les vecteurs (depuis pc/tg/machines.py et pc/tg/deploie.py)
    python3 pc/outils/vecteurs_machines.py --verifier   code de sortie 1 si le fichier n'est plus à jour (CI)

Les pièces qu'une commande interroge (l'ordinateur ouvert, la vue déployée), les interrupteurs (octets UTF-8), la
lettre du défi, les unités, la mémoire lue dans free -h, les cartes du réveil, l'orchestre et les boîtes mélangés pour
chaque partie, le besoin et le drapeau de l'épreuve, la vérification d'une machine montée, l'énergie, la maison dans la
maison : tests/jvm/Machines.kt vérifie que l'appli Android donne EXACTEMENT les mêmes résultats.
"""
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import deploie, langue, machines as M  # noqa: E402

FICHIER = RACINE / "donnees" / "machines" / "vecteurs.json"


def vecteurs():
    langue.definir("fr")
    graines = ["1:0", "2:1730000000", "7:42", "partie:3", "9:1761900000", "4:1700000123"]
    lignes = ["nproc", "lscpu | head -20", "free -h", "cat /proc/meminfo | head -3", "lsblk", "df -h .", "du -sh .",
              "lspci", "lspci | grep -i vga", "lsusb", "uptime", "cat /proc/uptime", "cat /proc/cpuinfo | head -5",
              "grep -c ^processor /proc/cpuinfo", "getprop ro.product.model", "machines coeurs 4", "machines memoire 7.8",
              "nproc && free -h; lsblk || df -h", "ls", "echo nproc", "stat -c %s photo.bin", "lsmod | head -5",
              "Nproc", "uname -r"]
    pieces = [{"ligne": l, "pieces": M.pieces_de(l)} for l in lignes]
    dep = [{"ligne": l, "pieces": [{"seg": x["seg"], "cmd": x["cmd"], "pieces": x["pieces"]} for x in deploie.pieces(l)]}
           for l in lignes]
    mots = ["A", "Zoé", "Léa", "Hugo", "Ñandú", "字", "🐉", "Pixel"]
    inter = [{"mot": m, "octets": [[c, b] for c, b in M.interrupteurs(m)]} for m in mots]
    noms = ["Pixel", "élodie", "Œuf", "123", "", "zébulon", "Ñ"]
    lettres = [{"nom": n, "lettre": M.lettre_defi(n), "bits": M.bits(ord(M.lettre_defi(n)))} for n in noms]
    unites = [{"n": n, **M.unites(n)} for n in (1048576, 1000, 1024, 1000000000, 1099511627776)]
    mem = [{"reponse": r, "kio": k, "ok": M.memoire_ok(r, k)} for r, k in
           (("7.8", 8148544), ("7,8", 8148544), ("8", 8148544), ("7.8Gi", 8148544), ("8.3 Go", 8148544), ("16", 8148544),
            ("512", 524288), ("512Mi", 524288), ("0.5", 524288), ("15", 16314880), ("15Gi", 16314880), ("16", 16314880),
            ("31", 32611072), ("abc", 8148544), ("", 8148544), ("7800 Mi", 8148544), ("7.8", 0), ("8148544", 8148544),
            ("8148544 kB", 8148544), ("9000000", 8148544), ("60000", 8148544))]
    parties = [{"graine": g, "reveil": [[l, e] for l, e in M.reveil_cartes(g)], "reponse": M.reveil_reponse(g),
                "orchestre": [[n, i, l] for n, i, l in M.orchestre(g)], "range": [[n, i, r] for n, i, r in M.range_boites(g)],
                "besoin": M.besoin_epreuve(g), "drapeau": M.drapeau(g)} for g in graines]
    choix = [(["P1", "C1", "M1", "S1", "G0", "A1"], "ecole"), (["P2", "C2", "M3", "S1", "G0", "A1"], "ecole"),
             (["P1", "C1", "M3", "S1", "G0", "A1"], "ecole"), (["P3", "C2", "M3", "S1", "G2", "A1"], "ecole"),
             (["P2", "C1", "M2", "S1", "G1", "A2"], "jouer"), (["P2", "C1", "M1", "S1", "G0", "A2"], "jouer"),
             (["P3", "C2", "M4", "S2", "G2", "A3"], "jouer"), (["P2", "C1", "M2", "S2", "G0", "A1"], "dessiner"),
             (["P1", "C1", "M2", "S1", "G0", "A1"], "dessiner"), (["P3", "C2", "M3", "S3", "G0", "A2"], "serveur"),
             (["P3", "C2", "M3", "S3", "G1", "A2"], "serveur"), (["P4", "C3", "M3", "S1", "G0", "A1"], "robot"),
             (["P4", "C2", "M3", "S1", "G0", "A1"], "robot"), (["P2", "C1", "M2", "S1", "G1", "A2"], "robot"),
             (["p2", "c1", "m2"], "ecole"), (["P2", "P1", "C1", "M2", "S1", "G0", "A1"], "ecole"), (["X9"], "ecole"), ([], "jouer")]
    montages = [{"choix": c, "besoin": b, **M.montage(c, b)} for c, b in choix]
    boites = [{"cpuinfo": c, "cgroup": g, "dockerenv": d, "containerenv": e, **M.boite_de(c, g, d, e)} for c, g, d, e in
              (("flags\t\t: fpu vme hypervisor sse", "0::/", False, False), ("flags\t\t: fpu vme sse", "0::/init.scope", False, False),
               ("", "12:pids:/docker/0123abc", False, False), ("", "0::/", True, False), ("", "0::/", False, True),
               ("flags : hypervisor", "0::/kubepods/x", False, False), ("Features : fp asimd", "0::/", False, False))]
    energie = [{"watts": w, "heures": h, **M.energie(w, h)} for w, h in ((300, 8760), (65, 24), (5, 8760))]
    return {"note": "généré par pc/outils/vecteurs_machines.py ; vérifié par tests/jvm/Machines.kt",
            "pieces": pieces, "deploie": dep, "interrupteurs": inter, "lettres": lettres, "unites": unites,
            "memoire": mem, "parties": parties, "montages": montages, "boites": boites, "energie": energie}


def main():
    texte = json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n"
    if "--verifier" in sys.argv:
        if not FICHIER.is_file() or FICHIER.read_text(encoding="utf-8") != texte:
            print("donnees/machines/vecteurs.json n'est plus à jour : python3 pc/outils/vecteurs_machines.py")
            sys.exit(1)
        print("vecteurs de la Salle des Rouages à jour")
        return
    FICHIER.parent.mkdir(parents=True, exist_ok=True)
    FICHIER.write_text(texte, encoding="utf-8")
    print(f"{FICHIER.relative_to(RACINE)} : écrit")


if __name__ == "__main__":
    main()
