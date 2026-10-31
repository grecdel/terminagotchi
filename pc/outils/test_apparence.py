"""Test de l'apparence (pc/tg/apparence.py) : les thèmes (contraste lisible pour le texte et les blocs de la vue
déployée, recoloration, sprites jamais touchés, couleurs du terminal), l'interface évolutive (le calendrier
d'apparition des panneaux, l'annonce, un panneau mérité le reste, « Tout afficher » et sa question), la migration des
anciennes parties, la disposition (grille, aimantation, dispositions toutes prêtes, cacher / remettre, « ma
disposition »), l'espace de travail (rangement, options, places endormies), le premier tuyau du chapitre 5, la
synchronisation du thème, et les vecteurs communs avec Android (donnees/apparence/vecteurs.json).

    python3 pc/outils/test_apparence.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_apparence_")
os.environ.pop("HISTFILE", None)
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import apparence as A, core, histoire, intro, langue, plateforme  # noqa: E402
from tg import espace_scene as S  # noqa: E402

langue.definir("fr")
ok = ko = 0


def verif(c, msg, silencieux=False):
    global ok, ko
    if c:
        ok += 1
    else:
        ko += 1
    if not c or not silencieux:
        print(("  ✔ " if c else "  ✖ ") + msg)


# ---------------------------------------------------------------- les données
print("Les données")
D = A.donnees()
for f in ("donnees/apparence.json", "app/src/main/assets/apparence.json"):
    verif((RACINE / f).read_text(encoding="utf-8") == (RACINE / "pc/tg/apparence.json").read_text(encoding="utf-8"),
          f"{f} : copie exacte de pc/tg/apparence.json")
verif(len(D["ordre"]) == 9 and set(D["ordre"]) == set(D["themes"]), "9 thèmes, tous dans l'ordre")
verif(D["themes"]["gameboy"]["fond"].upper() == "#0F380F", "Game Boy inversé : fond très foncé #0F380F")
verif(json.loads((RACINE / "donnees/apparence/vecteurs.json").read_text(encoding="utf-8")) == json.loads(
    json.dumps(A.vecteurs())), "les vecteurs communs (donnees/apparence/vecteurs.json) sont à jour")

# ---------------------------------------------------------------- les thèmes : contraste
print("Le contraste de chaque thème (WCAG : texte ≥ 4,5 ; texte doux et blocs ≥ 3)")
for cle in A.ordre():
    th = A.Theme(cle)
    for fond in ("panneau", "terminal", "panneau2"):
        F = th.r[fond]
        verif(A.contraste(th.r["texte"], F) >= 4.5, f"{cle} : texte sur {fond} ({A.contraste(th.r['texte'], F):.1f})",
              True)
        verif(A.contraste(th.r["doux"], F) >= 3.0, f"{cle} : texte doux sur {fond} ({A.contraste(th.r['doux'], F):.1f})",
              True)
        for k, c in th.acc.items():
            verif(A.contraste(c, F) >= 3.0, f"{cle} : bloc {k} sur {fond} ({A.contraste(c, F):.1f})", True)
    # les blocs de la vue déployée : texte de l'accent sur son fond teinté (alpha 40 sur le panneau)
    for g, (r, gg, b) in __import__("tg.deploie", fromlist=["x"]).COULEURS.items():
        c = th.couleur((r, gg, b, 255))[:3]
        teinte = tuple(int(c[i] * 40 / 255 + th.r["panneau"][i] * (1 - 40 / 255)) for i in range(3))
        verif(A.contraste(c, teinte) >= 3.0, f"{cle} : bloc « {g} » lisible ({A.contraste(c, teinte):.1f})", True)
    verif(True, f"{cle} : contrastes vérifiés")
verif(A.Theme("gameboy").clair is False, "Game Boy est maintenant un thème sombre")

print("La recoloration")
L = [("rect", 0, 0, 10, 10, S.FOND), ("texte", 1, 1, "x", 12, S.TEXTE, False, "g", False),
     ("imgt", "cadre", 1, 1, 1.0, False, False, 1, 1, 0, 1.0), ("rrect", 0, 0, 5, 5, 3, S.PANNEAU, S.BORD, 1)]
verif(A.recolorer(L, A.Theme("sombre")) == L, "sombre : la liste est inchangée")
for cle in A.ordre():
    R = A.recolorer(L, A.Theme(cle))
    verif(R[2] == L[2], f"{cle} : les images (sprites) ne changent jamais", True)
    verif(R[0][5][:3] == A.Theme(cle).r["fond"], f"{cle} : le fond devient le fond du thème", True)
verif(A.Theme("clair").couleur(S.TEXTE)[:3] == A.Theme("clair").neutre(0.93), "clair : le texte devient foncé")
verif(A.Theme("matrix").couleur(S.VERT)[:3] == A.hexa("#00FF41"), "Matrix : le vert devient le vert Matrix")
verif(A.Theme("clair").couleur((0, 0, 0, 90)) == (0, 0, 0, 90), "les ombres restent des ombres")

print("Les couleurs du terminal")
st = core.new_state("Pixel")
core.migrate(st)
A.choisir_theme(st, "matrix")
verif(plateforme.THEME_ANSI is not None and "38;2;0;255;65" in plateforme.fg(78), "Matrix : fg(78) (vert) → le vert du thème")
verif(plateforme.fg(245) == "\033[38;5;245m", "les gris restent ceux du terminal")
A.choisir_theme(st, "clair")
verif(plateforme.THEME_ANSI is None, "thème clair : le terminal garde ses couleurs (fond sombre du terminal)")
A.choisir_theme(st, "sombre")
verif(plateforme.fg(78) == "\033[38;5;78m", "sombre : les couleurs d'origine")
verif(st["config"]["theme_date"] > 0 and not A.choisir_theme(st, "inconnu"), "le thème est daté (synchronisation)")

# ---------------------------------------------------------------- la migration
print("La migration des anciennes parties")
vieille = core.new_state("Ancien")
core.migrate(vieille)
vieille.pop("apparence", None)
verif(A.cle_theme(vieille) == "sombre", "une ancienne partie : thème Sombre")
verif(A.disposition(vieille)[1] == "classique", "une ancienne partie : disposition Classique")
verif(A.visibles(vieille) >= set(A.ids()), "une ancienne partie (sans déblocage progressif) : tous ses panneaux visibles")
verif(A.a_(vieille)["annonces"] == [], "… sans annonce (rien de « nouveau » pour un joueur qui connaît déjà)")
milieu = intro.nouvelle_partie(core.new_state("Milieu"))
core.migrate(milieu)
intro.finir(milieu)
h = histoire.h_(milieu)
h["faits"] += ["t0", "reveil1", "racine"]
h["ailes"].append("reveil")
milieu.pop("apparence", None)
v = A.visibles(milieu)
verif({"ile", "explorateur", "envies", "carte"} <= v and "deploie" not in v,
      "une partie en cours : ses panneaux déjà mérités sont visibles, pas les autres")
verif(A.a_(milieu)["annonces"] == [], "… sans annonce à la migration")

# ---------------------------------------------------------------- le calendrier
print("Le calendrier d'apparition (interface évolutive)")
st = intro.nouvelle_partie(core.new_state("Nouveau"))
core.migrate(st)
verif(A.visibles(st) == {"terminal", "direct"}, "au tout début : l'œuf (créature en direct) et l'invite seulement")
verif(A.onglets(st) == [] and A.onglets_telephone([]) == ["terminal"], "pas d'onglets du panneau du moment")
etapes = [
    ("éclosion", lambda s: intro.finir(s), {"ile"}),
    ("leçon t0 « Où suis-je ? »", lambda s: histoire.h_(s)["faits"].append("t0"), {"explorateur", "envies"}),
    ("fin du chapitre 1", lambda s: histoire.h_(s)["ailes"].append("reveil"), {"carte"}),
    ("leçon « Le garde-manger » (nid1)", lambda s: histoire.h_(s)["faits"].append("nid1"), {"deploie", "assiette"}),
    ("première créature dressée", lambda s: s.setdefault("captures", []).append({"id": "c1", "espece": "Gouttelin"}),
     {"equipe"}),
    ("chapitre 5 « La loupe du détective » (le tuyau)", lambda s: histoire.h_(s)["faits"].append("biblio1"), {"tuyaux"}),
    ("chapitre 8 « Ma première recette »", lambda s: histoire.h_(s)["faits"].append("scripts0"), {"cerveau"}),
]
for nom, f, attendus in etapes:
    avant = A.visibles(st)
    f(st)
    intro.verifier(st)
    apres = A.visibles(st)
    verif(apres - avant == attendus, f"{nom} : apparaissent {sorted(attendus)} (vu : {sorted(apres - avant)})")
    verif(set(A.a_(st)["annonces"]) >= attendus, f"{nom} : annoncés (animation et phrase)", True)
    for p in attendus:
        verif(not langue.t(f"app.pan.{p}.dit").startswith("app."), f"la phrase de « {p} »", True)
verif(A.onglets(st) == ["carte", "cerveau", "tuyaux", "lecon"], "l'espace est complet : Carte, Cerveau, Tuyaux, Leçon")
histoire.h_(st)["faits"].remove("biblio1")
verif("tuyaux" in A.visibles(st), "un panneau mérité le reste")

print("« Tout afficher » (pour les grands)")
st2 = intro.nouvelle_partie(core.new_state("Classe"))
core.migrate(st2)
q, rep = A.question_adulte(3)
verif(" × " in q and rep == str(eval(q.replace("×", "*"))), f"la question des grands : {q} = {rep}")
A.tout_afficher(st2, True)
verif(A.visibles(st2) >= set(A.ids()), "Tout afficher : tous les panneaux")
verif(not intro.eclos(st2) and histoire.h_(st2)["faits"] == [], "… sans rien changer à la progression")
A.tout_afficher(st2, False)
verif(A.visibles(st2) == {"terminal", "direct"}, "réversible")

# ---------------------------------------------------------------- la disposition
print("La disposition (grille, dispositions toutes prêtes)")
g = A.grille()
for nom in D["dispositions"]:
    cases = A.preset(nom)
    verif(all(A.borner(c) == c for c in cases.values()), f"{nom} : toutes les dalles dans la grille", True)
    ks = list(cases)
    verif(not any(A.chevauche(cases[a], cases[b]) for i, a in enumerate(ks) for b in ks[i + 1:]),
          f"{nom} : aucune dalle ne chevauche une autre")
    verif("terminal" in cases, f"{nom} : le terminal est là", True)
verif(A.rect_de([0, 0, 24, 20]) == (16, 96, 1888, 968), "la grille couvre 16-1904 × 96-1064")
verif(A.case_de(*A.rect_de([5, 7, 2, 2])[:2]) == [5, 7], "aimantation : un point retombe sur sa case")
verif(A.borner([30, -2, 1, 99]) == [21, 0, 3, 20], "borner : taille minimale, dans la grille")
st3 = core.new_state("Range")
core.migrate(st3)
A.modifier(st3, "envies", case=[5, 11, 4, 5])
verif(A.disposition(st3) == ({**A.preset("classique"), "envies": [5, 11, 4, 5]}, "perso"), "déplacer une dalle")
A.modifier(st3, "equipe", cacher=True)
verif("equipe" not in A.disposition(st3)[0] and A.caches(st3) == ["equipe"], "cacher une dalle (le tiroir)")
A.enregistrer_mienne(st3)
A.choisir_disposition(st3, "terminal_geant")
verif(A.disposition(st3)[1] == "terminal_geant", "choisir « Terminal géant »")
A.choisir_disposition(st3, "mienne")
verif(A.disposition(st3)[0]["envies"] == [5, 11, 4, 5] and "equipe" not in A.disposition(st3)[0], "« Ma disposition » revient")
A.modifier(st3, "equipe", cacher=False)
verif("equipe" in A.disposition(st3)[0], "remettre une dalle")
A.origine(st3)
verif(A.disposition(st3) == (A.preset("classique"), "classique"), "Disposition d'origine")
A.choisir_theme(st3, "ocean")
A.choisir_disposition(st3, "creature_centre")
verif(A.cle_theme(st3) == "ocean" and A.disposition(st3)[1] == "creature_centre", "thème et disposition indépendants")
verif(A.choisir_disposition(st3, "classe") and A.disposition(st3) == ({}, "classe"), "Classe / grand écran")

# ---------------------------------------------------------------- l'espace de travail
print("L'espace de travail (dessin)")


def modele(**k):
    m = {"chapitre": "", "nom": "Noisette", "espece_stade": "", "etat_nom": "content", "equipe": [], "envies": [],
         "assiette": [], "arbre": [], "lieux": {}, "lignes": [], "invite": [], "saisie": "", "cerveau": None,
         "deploie": None, "onglet": "carte", "t": 1.0}
    m.update(k)
    return m


L, Z, _ = S.scene(modele(visibles={"terminal", "direct"}, onglets=[]))
verif(not any(z[4] == "reglages" for z in Z) and any(op[0] == "texte" and op[3] == "Terminagotchi" for op in L),
      "avant l'éclosion : l'œuf et l'invite seuls, sans barre")
vis = {"terminal", "direct", "ile", "explorateur", "envies"}
L, Z, _ = S.scene(modele(visibles=vis, onglets=[], cases=A.preset("classique")))
verif(sum(1 for op in L if op[0] == "ligne" and op[7] == (6, 8, 0)) >= 12, "les places encore endormies : des pointillés")
verif(any(z[4] == "ranger" for z in Z), "le bouton crayon « Ranger mon espace » dans la barre")
L, Z, _ = S.scene(modele(visibles=vis, onglets=[], cases=A.preset("classique"), rangement=True, caches=["equipe"]))
acts = {z[4] for z in Z}
verif({"rg:dalle:explorateur", "rg:coin:terminal", "rg:cacher:envies", "rg:fini", "rg:origine", "rg:mienne"} <= acts,
      "rangement : poignées, coins, ✕, Terminé, Disposition d'origine, Ma disposition")
verif("rg:dalle:deploie" not in acts and "rg:remettre:equipe" not in acts and "rg:cacher:terminal" not in acts,
      "rangement : les dalles pas encore découvertes n'apparaissent pas ; le terminal ne se cache pas")
verif(not any(op[0] == "ligne" and op[7] == (6, 8, 0) for op in L), "rangement : pas de pointillés « à découvrir »")
L, Z, _ = S.scene(modele(visibles=vis, onglets=[], cases=A.preset("classique"), theme=A.Theme("pastel"),
                         options={"theme": "pastel", "dispo": "classique", "tout": False, "notifs": True, "langue": "Français",
                                  "question": None}))
acts = {z[4] for z in Z}
verif({"opt:theme:" + c for c in A.ordre()} <= acts and {"opt:tout", "opt:ranger", "opt:dispo:terminal_geant"} <= acts,
      "les options : 9 thèmes, dispositions, ranger, Tout afficher")
verif(L[0][5][:3] == A.Theme("pastel").r["fond"], "le thème s'applique à tout l'espace")
L, Z, _ = S.scene(modele(visibles=vis | {"carte"}, onglets=["carte", "lecon"], cases=A.preset("classique"),
                         arrivees={"carte": 0.5}))
verif(any(op[0] == "texte" and "nouveau" in op[3] for op in L), "l'arrivée d'un panneau : la pastille « nouveau »")

# ---------------------------------------------------------------- le chapitre 5
print("Le premier tuyau (chapitre 5, « La loupe du détective »)")
import re  # noqa: E402
steps = histoire.LECONS["biblio1"]["steps"] if hasattr(histoire, "LECONS") else None
src = (RACINE / "pc/tg/histoire.py").read_text(encoding="utf-8")
verif('_n("biblio1", 4' in src and "| grep Abyssor" in src, "l'étape du tuyau : cat … | grep Abyssor")
rx = re.compile(r"\|\s*(grep|select-string|sls|findstr)\b.*abyssor", re.I)
verif(bool(rx.search("cat etagere_c/coin_poussiereux/livre_des_abysses.txt | grep Abyssor")), "la vérification accepte le tuyau")
verif(not rx.search("grep Abyssor etagere_c/coin_poussiereux/livre_des_abysses.txt"), "… et demande vraiment un tuyau")
kt = (RACINE / "app/src/main/java/fr/terminagotchi/Histoire.kt").read_text(encoding="utf-8")
verif('n("biblio1", 4, "cat etagere_c/coin_poussiereux/livre_des_abysses.txt | grep Abyssor"' in kt,
      "la même étape sur Android")
for code in langue.LANGUES:
    d = json.loads((RACINE / f"pc/tg/langues/{code}.json").read_text(encoding="utf-8"))
    da = json.loads((RACINE / f"app/src/main/assets/langues/{code}.json").read_text(encoding="utf-8"))
    cles = [k for k in d if k.startswith(("app.pan.", "app.theme.", "esp.rg.", "app.opt.", "app.dispo.", "hist.biblio1.4"))]
    verif(len(cles) >= 50 and all(da.get(k) == d[k] for k in cles), f"{code} : {len(cles)} textes, identiques PC / Android",
          True)
verif(True, "les textes de l'apparence dans les 14 langues")

# ---------------------------------------------------------------- la synchronisation
print("Le thème suit le recensement (le plus récent gagne)")
from tg import recense  # noqa: E402
s = core.new_state("Sync")
core.migrate(s)
A.choisir_theme(s, "ambre")
charge, snap = recense._charge(s)
verif(charge["valeurs"]["theme"] == "ambre" and charge["valeurs"]["themeDate"] > 0, "envoyé au site avec sa date")
srv = {"themeDate": s["config"]["theme_date"] + 1000, "theme": "ocean", "stats": {}}
recense._appliquer(s, srv, snap)
verif(A.cle_theme(s) == "ocean", "un thème plus récent (l'autre appareil) gagne")
recense._appliquer(s, {"themeDate": 5, "theme": "matrix", "stats": {}}, snap)
verif(A.cle_theme(s) == "ocean", "un thème plus ancien ne change rien")

print(f"{ok} réussis, {ko} échoués")
sys.exit(1 if ko else 0)
