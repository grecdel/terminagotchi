"""Vecteurs communs Python / Kotlin des sons du jeu (pc/tg/sons.py, Sons.kt).

    python3 pc/outils/vecteurs_sons.py             réécrit donnees/sons/vecteurs.json
    python3 pc/outils/vecteurs_sons.py --verifier  code de sortie 1 s'il n'est plus à jour

Chaque son du catalogue (6 réussites / erreurs, 9 musiques, le thème et les 9 motifs des gardiens, le cri des 151
espèces, plus des cris de bébé, d'ado, shiny et glitch) : sa longueur et l'empreinte sha256 de ses échantillons 16 bits
(petit-boutiste). Plus les briques de calcul (expo, 2^x, la table du sinus), la règle « quel son après un tour », les
permissions (nuit de 20 h 30 à 7 h 30, « ce soir seulement », mode classe, créature qui dort).
"""
import json
import struct
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import sons as S  # noqa: E402

SORTIE = RACINE / "donnees/sons/vecteurs.json"


def noms():
    out = list(S.RETOURS) + ["biome_" + b for b in S.BIOMES] + ["gardiens_theme"] + \
        ["gardien_" + g[1] for g in S.GARDIENS] + ["gardien_glitch"]
    ids = sorted(S.especes())
    out += ["cri:" + e for e in ids]
    for e in ids[::10]:
        out += [S.nom_cri(e, "bebe"), S.nom_cri(e, "ado", shiny=True), S.nom_cri(e, "adulte", glitch=True)]
    return out


def resume(lecon=0, etape=0, niveau=1, stade=1, exploits=0, collection=0, total=0):
    return {"lecon": lecon, "etape": etape, "niveau": niveau, "stade": stade, "exploits": exploits,
            "collection": collection, "total": total}


def cas_choisir():
    a = resume()
    cas = [(a, resume(stade=2, niveau=4), "", 0), (resume(stade=0, niveau=1), resume(stade=1, niveau=2), "", 2),
           (a, resume(exploits=1), "erreur_douce", 1), (a, resume(collection=1), "", 0), (a, resume(niveau=2), "", 0),
           (a, resume(etape=1, total=1), "erreur_douce", 2), (a, resume(lecon=1, etape=0), "", 0),
           (a, a, "erreur_douce", 0), (a, a, "erreur_presque", 2), (a, a, "refus_doux", 1), (a, a, "autre", 1),
           (a, resume(total=1), "", 0), (a, resume(total=1), "", 1), (a, resume(total=1), "", 2),
           (a, resume(total=3), "", 2), (a, a, "", 2), (None, a, "", 0)]
    return [{"avant": av, "apres": ap, "marque": m, "n": n, "attendu": list(S.choisir(av, ap, m, n))}
            for av, ap, m, n in cas]


def cas_apparitions():
    cas = [("braisillon", {}, True), ("braisillon", {}, False), ("braisillon", {"shiny": True}, True),
           ("braisillon", {"glitch": True, "shiny": True}, True), ("heaumbre", {"gardien": "droits"}, False),
           ("heaumbre", {"gardien": "droits", "glitch": True}, True), ("x", {"gardien": "inconnue"}, True), ("", {}, True)]
    return [{"id": e, "ind": i, "nouvelle": n, "attendu": S.nom_apparition(e, i, n)} for e, i, n in cas]


def cas_permis():
    out = []
    base = dict(S.DEFAUTS)
    regs = [dict(base), dict(base, on=True), dict(base, on=True, musique=True), dict(base, on=True, v_cris=0),
            dict(base, on=True, musique=True, soir="2026-11-03"), dict(base, on=True, soir="2026-11-02")]
    heures = [(2026, 11, 3, 12 * 60), (2026, 11, 3, 20 * 60 + 29), (2026, 11, 3, 20 * 60 + 30), (2026, 11, 3, 23 * 60),
              (2026, 11, 4, 3 * 60), (2026, 11, 4, 7 * 60 + 29), (2026, 11, 4, 7 * 60 + 30), (2026, 3, 1, 1 * 60),
              (2028, 1, 1, 0)]
    for r in regs:
        for h in heures:
            for cat in ("musique", "cris", "retours"):
                for classe, dort in ((False, False), (True, False), (False, True)):
                    out.append({"r": r, "cat": cat, "quand": list(h), "classe": classe, "dort": dort,
                                "attendu": S.permis(r, cat, *h, classe=classe, dort=dort)})
    soirees = [{"quand": list(h), "attendu": S.soiree(*h)} for h in heures]
    return out, soirees


def vecteurs():
    sons = []
    for nom in noms():
        e = S.pcm(S.fabriquer(nom))
        sons.append({"nom": nom, "n": len(e), "empreinte": S.empreinte(e)})
    exemple = S.pcm(S.fabriquer("reussite_petite"))
    permis, soirees = cas_permis()
    return {"note": "Généré par pc/outils/vecteurs_sons.py ; spécification dans pc/tg/sons.py",
            "version": S.VERSION, "sr": S.SR,
            "calcul": {"expo": [[x, repr(S.expo(x))] for x in (-800.0, -3.3, -1.0, -0.001, 0.0, 0.5, 1.0, 2.0, 10.0, 700.5)],
                       "pow2": [[x, repr(S.pow2(x))] for x in (-1.0, -0.25, 0.0, 1 / 12, 0.5, 3.0)],
                       "note": [[n, repr(S.note(n))] for n in (21, 48, 60, 69, 96, 108)],
                       "sin": [[i, repr(S.SIN[i])] for i in (0, 1, 100, 255, 256, 257, 511, 512, 700, 1023, 1024)],
                       "alea": [S.Alea(g).suivant() for g in (0, 1, 7, 123456, 4294967295)],
                       "md5": S.md5("braisillon")},
            "exemple": {"nom": "reussite_petite", "debut": exemple[:200]},
            "sons": sons, "choisir": cas_choisir(), "apparitions": cas_apparitions(), "permis": permis, "soirees": soirees,
            "categories": {n: S.categorie(n) for n in ("evolution", "cri:braisillon", "gardien_heaumbre", "biome_feu",
                                                      "gardiens_theme", "erreur_douce", "refus")}}


def main():
    v = vecteurs()
    texte = json.dumps(v, ensure_ascii=False, indent=0) + "\n"
    if "--verifier" in sys.argv:
        ok = SORTIE.exists() and SORTIE.read_text(encoding="utf-8") == texte
        print("à jour" if ok else "PAS à jour : relancer python3 pc/outils/vecteurs_sons.py")
        sys.exit(0 if ok else 1)
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text(texte, encoding="utf-8")
    print(len(v["sons"]), "sons,", len(v["choisir"]), "cas de choix,", len(v["permis"]), "cas de permission ->", SORTIE)


if __name__ == "__main__":
    main()
