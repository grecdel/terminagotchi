"""« Dans un vrai terminal… » (G-10) : à chaque étape, à côté des explications pour l'enfant et pour les grands, une
ligne qui dit si la commande marche pareil dans un vrai terminal (Linux, macOS), ou ce qu'il faut taper à la place.

Les données sont ici (et les mêmes dans app/…/Vrai.kt) ; les phrases sont des clés « vrai.* » des 14 langues.
"""
import re

from .langue import t
from .plateforme import IS_WIN

# la commande à taper sur macOS quand celle de Linux n'y est pas (motif sur la commande → commande macOS)
MAC = [
    (r"^free\b", "top -l 1 | head -n 10"),
    (r"^ip\b", "ifconfig"),
    (r"/etc/hostname", "hostname"),
    (r"^ps aux\b", None),
]
# pas installés sur tous les ordinateurs (un adulte peut les ajouter)
ABSENTS = {"tree", "nslookup", "traceroute", "dig", "tracepath"}
# propres au téléphone (Termux, Android) : pas de « vrai terminal » d'ordinateur
TELEPHONE = ("termux-", "am ", "pm ", "ouvre ")


def _mac(cmd):
    for motif, mac in MAC:
        if re.search(motif, cmd):
            return mac
    return None


def cle(cmd):
    """(clé, paramètres) de la ligne « vrai terminal » d'une commande, ou None."""
    cmd = (cmd or "").strip()
    if not cmd or cmd.startswith(TELEPHONE) or cmd in ("miam",) or cmd.startswith("ouvre"):
        return None
    if IS_WIN:
        return "vrai.win", {"cmd": cmd}
    premier = cmd.split()[0]
    if premier in ("port", "tg"):             # les commandes du jeu (le réseau simulé du Port) : pas d'équivalent tel quel
        return None
    if premier in ABSENTS:
        return "vrai.absent", {"cmd": premier}
    mac = _mac(cmd)
    if mac:
        return "vrai.mac", {"mac": mac}
    return "vrai.pareil", {"cmd": cmd}


def ligne(step):
    """La ligne « 💻 Dans un vrai terminal… » de l'étape (ou None)."""
    c = cle(step.get("cmd"))
    return t(c[0], **c[1]) if c else None
