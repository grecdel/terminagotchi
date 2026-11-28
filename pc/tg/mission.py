"""La ligne 🎯 « ce que je dois taper maintenant » (allègement du 9 novembre, variante B « terminal + mission »).

Une seule ligne, toujours au même endroit : juste au-dessus de la saisie (téléphone, `tg espace`), sous la créature
(fenêtre `tg`), et « ➜ à toi : » dans le terminal de l'enfant. Le détail (le texte de la leçon, « Pour les grands »,
« Dans un vrai terminal », les options expliquées…) reste derrière le + (téléphone), la touche [+] (fenêtre `tg`) ou
`tg detail`.

Ordre (le même que Mission.kt, vecteurs communs donnees/mission/vecteurs.json) : le défi éclair, le terrain effacé,
la leçon (ou le niveau qu'il manque), le bandeau de l'histoire (choisir une aile), la quête suivie.
"""
from .langue import t


def formater(genre, **v):
    """La ligne (texte avec les commandes entre `…`) d'une mission. Pure : testée par les vecteurs communs."""
    if genre == "defi":
        if v.get("calme"):
            return t("conf.defi", cmd=v["cmd"])
        return t("app.defi", cmd=v["cmd"], s=v["s"])
    if genre == "terrain":
        return t("app.terrain.titre") + " · " + t("mis.tape", cmd="`" + v["cmd"] + "`")
    if genre == "lecon":
        tete = f"🎯 {v['titre']} ({v['k']}/{v['n']}) · "
        cmd = v["cmd"]
        return tete + (cmd if cmd.startswith("🧩") else t("mis.tape", cmd=cmd))
    if genre == "niveau":
        return "🎯 " + t("mis.niveau", n=v["n"], xp=v["xp"])
    if genre == "bandeau":
        return "🗺 " + v["titre"]
    if genre == "quete":
        return v["ligne"]
    return ""


def choisir(state, cwd=None):
    """(genre, valeurs) de la mission du moment, ou None (rien à taper de précis)."""
    from . import core
    from .plateforme import piege
    d = state.get("defi")
    if d:
        import time
        reste = max(0, core.defi_duree(state) - (time.time() - d["start"]))
        return "defi", {"cmd": piege(d["cmd"]), "s": f"{reste:.0f}", "calme": core._calme(state)}
    perdu = state.get("terrain_perdu")
    if perdu:
        return "terrain", {"cmd": piege(perdu["cmd"])}
    from . import compagnon, histoire, lecons
    les, _e = lecons.lecon_courante(state)
    if les:
        lvl = core.level(state["xp"])
        if lvl < les["niveau"]:
            return "niveau", {"n": les["niveau"], "xp": max(0, 10 * (les["niveau"] - 1) ** 2 - state["xp"])}
        step = les["steps"][state["step"]]
        return "lecon", {"titre": lecons.tx(les["titre"]), "k": state["step"] + 1, "n": len(les["steps"]),
                         "cmd": compagnon.commande_montree(state, step, cwd)}
    b = histoire.bandeau(state)
    if b:
        return "bandeau", {"titre": b[0]}
    from . import intro, quetes
    if intro.ouvert(state, "quetes"):
        q = quetes.ligne_suivie(state)
        if q:
            return "quete", {"ligne": q}
    return None


def ligne(state, cwd=None):
    """La ligne 🎯 du moment (avec ses `commandes`), ou "" ."""
    try:
        m = choisir(state, cwd)
    except Exception:                                # noqa: BLE001 (l'écran ne plante jamais pour la mission)
        return ""
    return formater(m[0], **m[1]) if m else ""


def detail(state, cwd=None):
    """Tout ce qui est derrière le + : la leçon complète (chapitre, texte, commande, pour les grands, vrai terminal,
    options expliquées, d'où la taper, astuce, indice), le terrain effacé, le défi, la quête suivie."""
    from . import app
    return app.lignes_lecon(state)
