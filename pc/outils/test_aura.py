"""Test des auras de rareté (PC) : l'échelle des couleurs, la lueur qui suit la silhouette (dehors seulement),
la respiration, le rendu terminal, la collection, tg anime, et le réglage `tg aura on|off` rangé par partie.

    python3 pc/outils/test_aura.py          (crée son propre HOME temporaire)

Le même calcul est testé sur Android par tests/jvm/Aura.kt.
"""
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ["HOME"] = tempfile.mkdtemp(prefix="tg_aura_")
os.environ["LANG"] = "fr_FR.UTF-8"
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import app, aura as A, bestiaire as B, core, equipe, explo, langue, parties, sprites  # noqa: E402

ok = ko = 0
ANSI = re.compile(r"\x1b\[[0-9;]*m")


def verifier(cond, msg):
    global ok, ko
    ok, ko = (ok + 1, ko) if cond else (ok, ko + 1)
    print(("  ✔ " if cond else "  ✖ ") + msg)


def teinte_de(lignes, rgb):
    """Une case du terminal a-t-elle la couleur rgb, assombrie (aura sur fond sombre) ?"""
    for x in lignes:
        for m in re.finditer(r"[34]8;2;(\d+);(\d+);(\d+)m", x):
            c = [int(v) for v in m.groups()]
            f = c[0] / rgb[0] if rgb[0] else c[2] / rgb[2]
            if 0.1 < f < 1 and all(abs(c[i] - rgb[i] * f) <= 2 for i in range(3)):
                return True
    return False


def tg(*args):
    r = subprocess.run([sys.executable, str(RACINE / "pc"), *args], capture_output=True, text=True)
    return langue.sans_marques(ANSI.sub("", r.stdout))


print("L'échelle des auras")
verifier(A.ORDRE == ["commune", "peu commune", "rare", "épique", "légendaire", "mythique", "shiny"],
         "7 paliers : les 6 raretés, puis shiny")
verifier(all(A.PALIERS[r].couleur == B.COULEUR_RARETE[r] for r in A.ORDRE[:-1]),
         "les couleurs sont celles des raretés (bestiaire.COULEUR_RARETE)")
rayons = [A.PALIERS[r].rayon for r in A.ORDRE]
forces = [A.PALIERS[r].force for r in A.ORDRE[:-1]]
verifier(rayons == sorted(rayons) and forces == sorted(forces) and rayons[-2] == 3,
         "plus c'est rare, plus l'aura est large et forte (1 à 3 pixels)")
verifier(A.palier_de("rare", True) == "shiny" and A.palier_de("épique") == "épique" and A.palier_de("??") == "commune",
         "shiny passe avant la rareté ; rareté inconnue = commune")
verifier(not A.visible("commune", terminal=True) and A.visible("peu commune", terminal=True),
         "commune : rien dans le terminal")

print("La lueur suit la silhouette")
# un anneau 7×7 avec un trou fermé au milieu
w = h = 7
plein = [1 <= x <= 5 and 1 <= y <= 5 and not (x == 3 and y == 3) for y in range(h) for x in range(w)]
W, H, r, px = A.calque(w, h, plein, "légendaire")
verifier((W, H, r) == (w + 6, h + 6, 3), "toile agrandie du rayon de chaque côté")
verifier(all(px[(y + r) * W + x + r] is None for y in range(h) for x in range(w) if plein[y * w + x]),
         "jamais d'aura SUR la bestiole")
verifier(px[(3 + r) * W + 3 + r] is None, "un trou fermé à l'intérieur reste vide (aura dehors seulement)")
verifier(px[(3 + r) * W + 0 + r] is not None and px[(3 + r) * W + 0 + r][3] > 150, "le bord extérieur brille fort")
loin = [p for k, p in enumerate(px) if p and abs(k % W - (3 + r)) >= 6]
verifier(px[0] is None and all(p[3] < px[(3 + r) * W + r][3] for p in loin), "la lueur s'éteint en s'éloignant")
nb = {n: sum(1 for p in A.calque(w, h, plein, n)[3] if p) for n in A.ORDRE}
verifier(nb["peu commune"] < nb["rare"] < nb["légendaire"], "les auras rares couvrent plus de pixels")
alphas = {sum(p[3] for p in A.calque(w, h, plein, "rare", ph)[3] if p) for ph in range(A.PHASES)}
verifier(len(alphas) > 4, "l'aura respire : elle change d'une image à l'autre")
couleurs = {p[:3] for p in A.calque(w, h, plein, "shiny", 3)[3] if p}
verifier(len(couleurs) > 6, "shiny : une lueur arc-en-ciel (beaucoup de couleurs)")

print("Dans le terminal")
e = B.espece("Braisillon")
sans = B.dessin(e, stade="adulte")
verifier(B.dessin(e, stade="adulte", aura="commune") == sans, "commune : le dessin est inchangé")
avec = B.dessin(e, stade="adulte", aura="rare")
lg = lambda ls: max(len(ANSI.sub("", x)) for x in ls)
verifier(lg(avec) == lg(sans) + 4 and len(avec) > len(sans), "rare : 2 cases de lueur de chaque côté")
verifier(teinte_de(avec, (95, 175, 255)) and not teinte_de(sans, (95, 175, 255)), "des demi-blocs bleus (rare) autour")
verifier(B.dessin(e, True, stade="adulte", aura="shiny", phase=1) != B.dessin(e, True, stade="adulte", aura="shiny", phase=9),
         "l'aura animée change avec la phase")

print("Collection, troupe, tg anime")
core.save(core.migrate(core.new_state("Pixel")))
st = core.load()
for nom, rar, sh in (("Braisillon", "légendaire", False), ("Pyrodrac", "commune", False), ("Ombrachne", "rare", True)):
    ind = B.individu(B.espece(nom), sh)
    ind["rarete"], ind["stade"], ind["teinte"] = rar, "adulte", 0.3
    st["captures"].append(ind)
core.save(st)
col = explo.ecran_collection(core.load())
brut = "\n".join(col)
verifier(teinte_de(col, (255, 175, 0)),
         "tg collection : la légendaire a son aura dorée")
verifier("montre sa rareté" in langue.sans_marques(ANSI.sub("", brut)), "tg collection : la légende des auras")
r = equipe.animation(st["captures"][0], "content", aura=True)
r0 = equipe.animation(st["captures"][0], "content")
verifier(r and r0 and len(r[0]) == len(r0[0]) and lg(r[0][0]) > lg(r0[0][0]), "tg anime : l'aura respire autour d'elle")

print("La créature de l'écran principal et le réglage")
verifier(A.palier_compagnon({"shiny": True}) == "shiny" and A.palier_compagnon({}) == "commune",
         "le compagnon : shiny (1 sur 64) ou commune")
verifier(A.active(core.load()), "l'aura est affichée par défaut")
core.modifier(lambda s: s.update(shiny=True))
ecran_on = app.render(core.load(), 2, False)
verifier(lg(sprites.creature(core.load(), "shiny", 1)[0]) > lg(sprites.creature(core.load())[0]),
         "compagnon shiny : la lueur arc-en-ciel l'entoure")
sortie = tg("aura", "off")
verifier("OFF" in sortie and not A.active(core.load()), "tg aura off : coupée et rangée dans la partie")
ecran_off = app.render(core.load(), 2, False)
verifier(ecran_on != ecran_off, "l'écran principal change quand on coupe l'aura")
verifier(app.aura_ecran(core.load()) is None, "plus d'aura autour de la créature")
verifier("ON" in tg("aura", "on") and A.active(core.load()), "tg aura on : de retour")
verifier("tg aura" in tg("aide"), "tg aide mentionne tg aura")
tg("aura", "off")
i1 = parties.active()
i2 = parties.nouvelle("Zou", "fr", lambda s: "œuf")
verifier(i2 and A.active(core.load()), "nouvelle partie : l'aura est réglée à neuf (affichée)")
parties.charger(i1)
verifier(not A.active(core.load()) and core.load()["name"] == "Pixel", "retour à la partie 1 : son aura reste coupée")

print(f"\n{ok} réussis, {ko} échoués   (HOME={Path.home()})")
sys.exit(1 if ko else 0)
