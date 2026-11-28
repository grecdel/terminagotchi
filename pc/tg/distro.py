"""La distribution Linux pratiquée : détectée toute seule (/etc/os-release) ou choisie dans les réglages.

    tg distro              la distribution pratiquée, celle détectée, et la liste
    tg distro fedora       la choisir (ubuntu, debian, mint, fedora, arch, opensuse)
    tg distro auto         revenir à la détection

Sur un vrai ordinateur, les commandes RÉELLES des leçons suivent ce qui est installé (une étape dont l'outil manque
est cachée) ; le choix change les conseils montrés (installer, mettre à jour, compter les paquets : apt, dnf, pacman,
zypper) et le Linux virtuel du jeu (Windows). Mêmes règles dans l'appli : Distro.kt. Données : distros.json.
"""
import json
import os
from pathlib import Path

from .langue import t

_D = None


def donnees():
    global _D
    if _D is None:
        _D = json.loads((Path(__file__).with_name("distros.json")).read_text(encoding="utf-8"))
    return _D


def os_release_de(texte):
    r = {}
    for l in (texte or "").splitlines():
        if "=" in l and not l.lstrip().startswith("#"):
            k, _, v = l.partition("=")
            r[k.strip()] = v.strip().strip('"').strip("'")
    return r


def reconnaitre(osr):
    """La clé de la distribution (« fedora »…) d'après /etc/os-release, ou None."""
    d = donnees()
    ident = (osr.get("ID") or "").lower()
    for cle, x in d["distros"].items():
        if ident == cle or ident in x["ids"]:
            return cle
    for mot in (osr.get("ID_LIKE") or "").lower().split():
        if mot in d["like"]:
            return d["like"][mot]
    return None


def detecter():
    for f in ("/etc/os-release", "/usr/lib/os-release"):
        try:
            return reconnaitre(os_release_de(Path(f).read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return None


def choix(state):
    return (state or {}).get("distro", "auto") or "auto"


def courante(state):
    """(clé ou None, 'choisie' | 'auto')"""
    c = choix(state)
    if c != "auto" and c in donnees()["distros"]:
        return c, "choisie"
    return detecter(), "auto"


def nom(cle):
    return donnees()["distros"][cle]["nom"] if cle in donnees()["distros"] else "?"


def magasin(cle):
    """Le magasin de paquets de la distribution : dict avec id, installer, maj, compte (ou None)."""
    if cle not in donnees()["distros"]:
        return None
    mid = donnees()["distros"][cle]["magasin"]
    return dict(donnees()["magasins"][mid], id=mid)


def installer(cle, paquet):
    """« sudo pacman -S base-devel » pour un paquet logique (compiler) ou un vrai nom (git)."""
    m = magasin(cle)
    if not m:
        return None
    return m["installer"].format(p=m["paquets"].get(paquet, paquet))


def ligne_installer(state, paquet):
    """La ligne de conseil pour installer un outil sur la distribution pratiquée (ou None)."""
    cle, _ = courante(state)
    cmd = installer(cle, paquet)
    return t("dist.installer", distro=nom(cle), cmd=cmd) if cmd else None


def ecran(state):
    cle, mode = courante(state)
    det = detecter()
    lignes = ["🐧 " + t("dist.titre", nom=nom(cle) if cle else t("dist.aucune"))]
    if mode == "auto":
        lignes.append("   " + t("dist.auto"))
    if det:
        lignes.append("   " + t("dist.detectee", nom=nom(det)))
    if cle:
        m = magasin(cle)
        lignes.append("   " + t("dist.magasin", magasin=m["id"], cmd=m["installer"].format(p="cowsay")))
    lignes.append("   " + t("dist.aide", cmd="`tg distro fedora`", cmd2="`tg distro auto`",
                               liste=", ".join(donnees()["ordre"])))
    return lignes


def changer(state, valeur):
    v = (valeur or "").strip().lower()
    d = donnees()
    if v == "auto":
        state["distro"] = "auto"
        cle = detecter()
        return "🐧 " + t("dist.choisie", nom=t("dist.auto_nom", nom=nom(cle) if cle else t("dist.aucune")))
    trouve = next((c for c, x in d["distros"].items() if v == c or v in x["ids"] or v == x["nom"].lower()), None)
    if not trouve:
        return t("dist.inconnue", nom=valeur, liste=", ".join(d["ordre"] + ["auto"]))
    state["distro"] = trouve
    return "🐧 " + t("dist.choisie", nom=nom(trouve))
