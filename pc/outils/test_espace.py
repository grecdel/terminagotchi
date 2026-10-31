"""Tests de l'espace de travail, de la vue déployée et du cerveau de la créature (PC).

    python3 pc/outils/test_espace.py            les tests
    python3 pc/outils/test_espace.py --generer  réécrit donnees/espace/vecteurs.json (après un changement voulu)

Les vecteurs (découpage des commandes, chaînes de tuyaux, tours du cerveau) sont les mêmes pour Android
(tests/jvm/Espace.kt) : les deux versions doivent donner exactement les mêmes blocs et les mêmes lignes surlignées.
"""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_test_espace_")

from tg import cerveau as CV  # noqa: E402
from tg import deploie as D  # noqa: E402
from tg import langue  # noqa: E402

VECTEURS = RACINE / "donnees" / "espace" / "vecteurs.json"
LIGNES = [
    "cat lianes.txt | grep -i gland", "ls | grep a > liste.txt", "cd grenier && ls -la", "ls -a",
    'grep "a | b" f.txt 2>/dev/null', "head -n 3 repas.txt", "chmod +x miam.sh", 'find . -name "*.txt" | wc -l',
    "echo bonjour >> journal.txt", "sort -n notes.csv|uniq -c", "cat a.txt|sort|uniq -c|sort -rn|head -3",
    "mkdir -p nid/coin ; touch nid/coin/oeuf.txt", "rm -r vieux_carton || echo rate", "wc -l < liste.txt",
    "tr a-z A-Z < cri.txt > CRI.txt", "VAR=1 echo $VAR", "ping -c 3 exemple.org &", "ls ~/terrain_terminagotchi/grenier",
    "cp grenier/lianes.txt .", "mv fouillis rangement", "rev parchemin", "tree", "tail -n 2 journal.txt | rev",
    "grep -rn gland .", "cd ..", "echo 'un | deux' | wc -w", "cat lianes.txt | grep gland | wc -l > total.txt",
]
EXISTANTS = ["grenier", "fouillis", "parchemin", "vieux_carton"]
REUSSIS = []
RATES = []


def ok(cond, nom):
    (REUSSIS if cond else RATES).append(nom)
    if not cond:
        print("  ✗", nom)


def existe(m):
    return m in EXISTANTS


def vecteurs():
    dep = []
    for l in LIGNES:
        bl = D.blocs(l, existe)
        ch = D.chaines(bl)
        dep.append({"ligne": l, "blocs": [[b["t"], b["g"], b["i"], b["seg"], b["role"], b["cmd"]] for b in bl],
                    "chaines": [{"etapes": [[e["cmd"], e["debut"], e["fin"], e["texte"]] for e in c["etapes"]],
                                 "redir": list(c["redir"]) if c["redir"] else None} for c in ch],
                    "sure": [D.sure(c["etapes"]) for c in ch]})
    seqs = []
    for depart, var, tours in [
        ("content", {"faim": 25, "jeu": 50, "sommeil": 70, "repas": 0},
         [({}, None), ({"commande_tapee": True}, None), ({}, None), ({}, None)]),
        ("content", {"faim": 60, "jeu": 20, "sommeil": 70, "repas": 8},
         [({}, None), ({}, None), ({"commande_tapee": True, "commande_ratee": True}, None), ({}, None)]),
        ("content", {"faim": 60, "jeu": 60, "sommeil": 10, "repas": 0},
         [({}, None)] + [({}, None)] * 9 + [({"commande_tapee": True}, None)]),
        ("content", {"faim": 95, "jeu": 60, "sommeil": 60, "repas": 8},
         [({"commande_tapee": True}, None), ({}, None), ({}, "dort"), ({}, "dort"), ({}, "confus"), ({}, None)]),
        ("faim", {"faim": 10, "jeu": 80, "sommeil": 80, "repas": 4}, [({}, None), ({"commande_tapee": True}, None),
                                                                      ({}, None), ({}, "joue"), ({}, "mange")]),
    ]:
        cv = CV.Cerveau(depart)
        cv.var = dict(var)
        sortie = []
        for sig, force in tours:
            cv.forcer(force) if force or cv.force else None
            if force is None and cv.force:
                cv.forcer(None)
            tr = cv.tour(sig, 0.0)
            sortie.append({"signaux": sig, "force": force, "de": tr.de, "vers": tr.vers, "etat": cv.etat,
                           "var": dict(cv.var), "lignes": [[i, g] for i, g in tr.lignes], "dit": tr.dit})
        seqs.append({"depart": depart, "var": var, "tours": sortie})
    return {"deploie": dep, "cerveau": {"programme": CV.PROGRAMME, "transitions": [list(x) for x in CV.transitions()],
                                        "sequences": seqs}}


def tests_deploie():
    bl = D.blocs("cat lianes.txt | grep -i gland")
    ok([b["g"] for b in bl] == ["commande", "chemin", "tuyau", "commande", "option", "argument"], "maquette : 6 blocs")
    ok([b["i"] for b in bl] == [1, 2, 3, 4, 5, 6], "numéros d'allumage")
    ok(bl[5]["role"] == "motif", "gland est le mot cherché")
    bl = D.blocs("ls | grep a > liste.txt")
    ok([b["g"] for b in bl] == ["commande", "tuyau", "commande", "argument", "redirection", "chemin"], "redirection")
    ok(bl[5]["role"] == "cible", "liste.txt reçoit la sortie")
    ch = D.chaines(bl)
    ok(len(ch) == 1 and ch[0]["redir"][1] == "liste.txt" and [e["texte"] for e in ch[0]["etapes"]] == ["ls", "grep a"],
       "chaîne : ls | grep a, puis le fichier")
    ok(D.blocs('grep "a | b" f.txt')[1]["t"] == '"a | b"', "les guillemets protègent le tuyau")
    ok(D.blocs("ls|wc")[1]["g"] == "tuyau", "tuyau collé")
    ok(D.blocs("cd grenier")[1]["g"] == "chemin", "cd : son argument est un lieu")
    ok(D.blocs("head -n 3 f.txt")[2]["role"] == "valeur", "head -n 3 : 3 est une valeur")
    ok(D.blocs("chmod +x miam.sh")[1]["g"] == "option", "chmod +x : une option")
    ok(not D.sure(D.chaines(D.blocs("find . -delete"))[0]["etapes"]), "find -delete n'est jamais lancé")
    ok(not D.sure(D.chaines(D.blocs("rm x"))[0]["etapes"]), "rm n'est jamais lancé")
    ok(not D.sure(D.chaines(D.blocs("cat $(rm x)"))[0]["etapes"]), "pas de $( ) lancé")
    ok(D.composee("a | b") and not D.composee("ls -la"), "commande composée")
    # le flux : on lance seulement des commandes sûres, sans redirection, dans un dossier
    d = tempfile.mkdtemp()
    Path(d, "lianes.txt").write_text("une liane\nun gland\nla ronce\nun Gland doré\n", encoding="utf-8")
    lances = []

    def lancer(texte):
        lances.append(texte)
        return D.lanceur(d)(texte)
    s = D.flux("cat lianes.txt | grep -i gland > sortie.txt", lancer)
    ok(lances == ["cat lianes.txt", "cat lianes.txt | grep -i gland"], "flux : préfixes sans redirection")
    ok(s == [[["une liane", "un gland", "la ronce", "un Gland doré"], ["un gland", "un Gland doré"]]], "flux : lignes")
    ok(not Path(d, "sortie.txt").exists(), "deploie n'écrit jamais le fichier de la redirection")
    lances.clear()
    ok(D.flux("rm -r * | cat", lancer) == [None] and not lances, "rien de dangereux n'est lancé")
    # les textes, dans toutes les langues
    for code in langue.LANGUES:
        langue.definir(code)
        for l in LIGNES:
            bl = D.blocs(l, existe)
            for b in bl:
                x = D.longue(b, bl)
                ok(x and "{" not in x and "dep." not in x, f"texte {code} {b['t']}")
        lignes = D.ecran("cat lianes.txt | grep -i gland", D.blocs("cat lianes.txt | grep -i gland"), 3,
                         [[["a", "b"], ["b"]]], 0.4, 100, d)
        ok(len(lignes) > 6, f"écran {code}")
    langue.definir("fr")
    # la récap des leçons
    r = D.recap_lecon("cat lianes.txt | grep gland")
    ok(len(r) == 2 and "deploie cat lianes.txt | grep gland" in r[1], "récap de leçon + astuce")
    ok(D.recap_lecon("ls") == [], "pas de récap pour une commande simple")


def tests_cerveau():
    # le programme est du vrai shell : bash le lit sans erreur
    import shutil
    import subprocess
    if shutil.which("bash"):
        src = "\n".join(l.replace("{commentaire}", "cerveau").replace("{phrase}", "?") for l in CV.PROGRAMME)
        script = ("commande_tapee() { return 1; }; commande_ratee() { return 1; }; dire() { echo \"$1\"; }\n"
                  "faim=20; jeu=50; sommeil=60; repas=3; etat=content\n" + src + "\necho $etat\n")
        r = subprocess.run(["bash", "-n", "-c", script], capture_output=True, text=True)
        ok(r.returncode == 0, "bash -n : le cerveau est du vrai shell")
        # et bash donne le même résultat que notre interpréteur, état par état
        for etat in CV.ETATS:
            for faim, tape in ((20, 1), (50, 0), (95, 1)):
                var = {"faim": faim, "jeu": 50, "sommeil": 60, "repas": 3}
                sc = script.replace("etat=content\n", f"etat={etat}\n").replace("faim=20", f"faim={faim}")
                if tape:
                    sc = sc.replace("commande_tapee() { return 1; }", "commande_tapee() { return 0; }")
                r = subprocess.run(["bash", "-c", sc + "echo $faim $jeu $sommeil"], capture_output=True, text=True)
                attendu = CV.executer(etat, var, {"commande_tapee": bool(tape)})
                fin = r.stdout.strip().split("\n")
                ok(fin[-2] == attendu[0], f"bash = interpréteur ({etat}, faim {faim}, tapée {tape})")
                v = attendu[1]
                ok(fin[-1] == f"{v['faim']} {v['jeu']} {v['sommeil']}", f"variables bash = interpréteur ({etat})")
    tr = CV.transitions()
    ok(("faim", "mange") in tr and ("mange", "content") in tr and ("content", "confus") in tr, "flèches lues")
    cv = CV.Cerveau()
    cv.var.update(faim=20)
    t1 = cv.tour({})
    ok(t1.vers == "faim", "faim < 30 : elle a faim")
    t2 = cv.tour({"commande_tapee": True})
    ok(t2.vers == "mange", "une commande tapée : elle mange")
    cv.forcer("dort")
    t3 = cv.tour({})
    ok(cv.etat == "dort" and t3.de == "dort", "forcer : l'état reste")
    ok(any(CV.PROGRAMME[i].strip().startswith("sommeil=") for i, _g in t3.lignes), "forcer : sa branche s'exécute")
    cv.forcer(None)
    ok(cv.force is None, "la laisser vivre")
    # les noms du code dans les 14 langues : des identifiants valides, le même nombre de lignes
    for code in langue.LANGUES:
        langue.definir(code)
        txt = CV.texte_programme("Noisette")
        ok(len(txt) == len(CV.PROGRAMME), f"programme {code}")
        for x in CV.IDS:
            ok(re.match(r"^[a-z_]+$", CV.ident(x)) is not None, f"identifiant {code} {x}")
        ok(len({CV.ident(e) for e in CV.ETATS}) == len(CV.ETATS), f"états distincts {code}")
    langue.definir("fr")


def tests_scene():
    """La scène se dessine (toutes les langues, le mode classe), sans fenêtre."""
    from tg import espace_scene as S
    for classe in (False, True):
        mise = S.Mise(classe)
        for r in (mise.deploie, mise.terminal, mise.direct, mise.contexte):
            ok(r[0] >= 0 and r[1] >= 0 and r[0] + r[2] <= mise.W and r[1] + r[3] <= mise.H, f"panneau dans l'écran {classe}")
    m = {"nom": "Noisette", "chapitre": "Chapitre 3", "deploie": None, "lignes": [], "invite": [], "saisie": "",
         "envies": [], "assiette": [], "arbre": [], "lieux": {}, "equipe": [], "equipe_lignes": []}
    bl = D.blocs("cat lianes.txt | grep -i gland")
    m["deploie"] = {"ligne": "x", "blocs": bl, "chaines": D.chaines(bl), "sorties": [[["a", "gland"], ["gland"]]],
                    "actif": 3, "phase": 0.3, "auto": True, "lieu": ("lianes.txt", "grenier/"), "lieu_piece": "grenier"}
    m["cerveau"] = {"code": CV.texte_programme("N"), "ligne": (3, "vrai"), "faites": {1, 2, 3}, "etat": "faim",
                    "de": "content", "vers": "faim", "force": None, "vars": [("faim", 20)]}
    for code in langue.LANGUES:
        langue.definir(code)
        for onglet in S.ONGLETS:
            m["onglet"] = onglet
            L, Z, (W, H) = S.scene(m, 1.0)
            ok(len(L) > 50 and all(isinstance(op, tuple) for op in L), f"scène {code} {onglet}")
            textes = [op[3] for op in L if op[0] == "texte"]
            ok(not any(("esp." in x or "dep." in x or "cerv." in x) and " " not in x for x in textes),
               f"pas de clé brute {code} {onglet}")
    langue.definir("fr")
    img = S.vers_pil(S.scene(m, 1.0)[0], (1920, 1080))
    ok(img.size == (1920, 1080), "capture PIL")


def tests_espace():
    """Le contrôleur : une vraie partie, de vraies commandes dans le terminal de l'espace."""
    sys.path.insert(0, str(RACINE / "pc" / "outils"))
    import capture_espace as C
    C.preparer()
    from tg import app, core
    from tg import espace as E
    esp = E.Espace(app.etape)
    esp.mini.dossier = str(core.TERRAIN / "grenier")
    total = (esp.state or {}).get("total", 0)
    C.taper(esp, "cat lianes.txt | grep -i gland")
    ok(esp.dep and [b["t"] for b in esp.dep["blocs"]] == ["cat", "lianes.txt", "|", "grep", "-i", "gland"],
       "espace : la dernière commande se déploie")
    ok(esp.dep["sorties"] and len(esp.dep["sorties"][0][-1]) == 2, "espace : ce qui passe dans le tuyau")
    ok(esp.dep["lieu"] and esp.dep["lieu"][1].startswith("grenier"), "espace : le chemin relié au lieu")
    ok((esp.state or {}).get("total", 0) > total, "espace : le jeu a compté la commande")
    ok(any("Gland" in "".join(s for s, _c, _g in l) for l in esp.lignes), "espace : la sortie est dans le terminal")
    C.taper(esp, "cerveau")
    ok(esp.onglet == "cerveau", "espace : `cerveau` ouvre le panneau")
    C.taper(esp, "deploie --pas ls | grep a > liste.txt")
    ok(esp.dep["auto"] is False and esp.dep["blocs"][-1]["t"] == "liste.txt", "espace : deploie --pas")
    ok(not (core.TERRAIN / "grenier" / "liste.txt").exists(), "espace : deploie ne lance pas la commande")
    esp.mini.saisie = ""
    esp.entree()
    ok(esp.dep["actif"] == 2, "espace : Entrée sur une ligne vide = bloc suivant (pas à pas)")
    esp.clic(0, 0, [(0, 0, 10, 10, "forcer:dort")])
    ok(esp.cv.force == "dort", "espace : forcer un état d'un clic")
    for _ in range(3):
        esp.cv_dernier = -1e9
        esp.tick()
    ok(esp.c.etat == "dort", "espace : la créature prend la pose de son état")
    lignes = E.ecran_texte(esp, 170, 48)
    ok(len(lignes) == 48, "mode texte : la taille du terminal")
    m = esp.modele()
    ok(m["nom"] == "Noisette" and m["arbre"] and m["envies"], "espace : le modèle complet")


def main():
    if "--generer" in sys.argv:
        VECTEURS.parent.mkdir(parents=True, exist_ok=True)
        VECTEURS.write_text(json.dumps(vecteurs(), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print("vecteurs écrits :", VECTEURS)
        return
    attendu = json.loads(VECTEURS.read_text(encoding="utf-8"))
    ok(vecteurs() == attendu, "vecteurs communs (donnees/espace/vecteurs.json)")
    tests_deploie()
    tests_cerveau()
    tests_scene()
    tests_espace()
    print(f"{len(REUSSIS)} réussis, {len(RATES)} échoués")
    sys.exit(1 if RATES else 0)


if __name__ == "__main__":
    main()
