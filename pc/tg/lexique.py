"""Le lexique, devenu le « carnet d'aventure » : toutes les commandes, rangées par chapitres et par
univers, chacune avec le moment de l'histoire où on l'a apprise (histoire.noter : « La forêt du
Grenier », « avant l'histoire », « en liberté »…), puis les souvenirs (chapitres réveillés,
quêtes, titres, objets).

  blanc     = déjà goûtée (sur n'importe lequel de tes appareils)
  gris      = à découvrir ici
  🔒 sombre = existe dans un autre univers (l'appli Android) : pas ici

Fil rouge : l'ordinateur est un monde à explorer, le Terminaworld, que la créature parcourt avec l'enfant.
Chaque commande a une IMAGE (le monde) et une explication TECHNIQUE ; l'affichage
suit le palier de vocabulaire (voir mots.py) : l'image seule, puis l'image et la
technique côte à côte, puis la technique avec l'image en petit rappel.
Les mêmes phrases existent dans l'appli Android (Regles.LEXIQUE dans Jeu.kt).
Sous chaque commande qui a besoin de quelque chose après elle : un exemple prêt à taper depuis le
Terminaworld (« ↳ exemple : mkdir cabane », voir exemples.py).
"""
from . import core, exemples, explique
from .langue import t
from .mots import palier
from .plateforme import BOLD, DIM, RESET, C, OS_NAMES, OSK, fg, installer

ICI = "ici"
TEL = "telephone"


def _entrees():
    inst = installer("nom")
    return [
        (t("lex.ch.fichiers"), ICI, [
            ("pwd", t("lex.pwd.i"), t("lex.pwd.t")),
            (C("ls", "dir"), t("lex.ls.i", opt=C("ls -a", "dir -Force")), t("lex.ls.t", opt=C("ls -a", "dir -Force"))),
            ("cd", t("lex.cd.i"), t("lex.cd.t")),
            ("mkdir", t("lex.mkdir.i"), t("lex.mkdir.t")),
            (C("touch", "New-Item"), t("lex.touch.i"), t("lex.touch.t")),
            (C("cp", "copy"), t("lex.cp.i"), t("lex.cp.t")),
            (C("mv", "move"), t("lex.mv.i"), t("lex.mv.t")),
            (C("rm", "del"), t("lex.rm.i"), t("lex.rm.t")),
            (C("chmod", "attrib"), t("lex.chmod.i"), t("lex.chmod.t")),
            ("tree", t("lex.tree.i"), t("lex.tree.t")),
            ("rev", t("lex.rev.i"), t("lex.rev.t")),
        ]),
        (t("lex.ch.lire"), ICI, [
            (C("cat", "type"), t("lex.cat.i"), t("lex.cat.t")),
            (C("less", "more"), t("lex.less.i"), t("lex.less.t")),
            (C("head", "Get-Content"), t("lex.head.i"), t("lex.head.t")),
            (C("grep", "Select-String"), t("lex.grep.i"), t("lex.grep.t")),
            (C("find", "Get-ChildItem"), t("lex.find.i"), t("lex.find.t")),
            (C("wc", "Measure-Object"), t("lex.wc.i"), t("lex.wc.t")),
            (C("sort", "Sort-Object"), t("lex.sort.i"), t("lex.sort.t")),
        ]),
        (t("lex.ch.systeme"), ICI, [
            ("whoami", t("lex.whoami.i"), t("lex.whoami.t")),
            (C("date", "Get-Date"), t("lex.date.i"), t("lex.date.t")),
            (C("ps", "Get-Process"), t("lex.ps.i"), t("lex.ps.t")),
            (C("htop", "tasklist", mac="top"), t("lex.htop.i"), t("lex.htop.t")),
            (C("kill", "Stop-Process"), t("lex.kill.i"), t("lex.kill.t")),
            (C("df", "Get-PSDrive"), t("lex.df.i"), t("lex.df.t")),
            (C("du", "Measure-Object"), t("lex.du.i"), t("lex.du.t")),
            ("free", t("lex.free.i"), t("lex.free.t")),
            ("uptime", t("lex.uptime.i"), t("lex.uptime.t")),
            (C("sudo", "winget"), t("lex.sudo.i", cmd=inst), t("lex.sudo.t", cmd=inst)),
        ]),
        (t("lex.ch.reseau"), ICI, [
            ("ping", t("lex.ping.i"), t("lex.ping.t")),
            (C("curl", "curl.exe"), t("lex.curl.i"), t("lex.curl.t")),
            (C("ip", "ipconfig", mac="ifconfig"), t("lex.ip.i"), t("lex.ip.t")),
            ("nslookup", t("lex.nslookup.i"), t("lex.nslookup.t")),
            ("ssh", t("lex.ssh.i"), t("lex.ssh.t")),
        ]),
        (t("lex.ch.git"), ICI, [
            ("git", t("lex.git.i"), t("lex.git.t")),
            (C("bash", "powershell"), t("lex.bash.i"), t("lex.bash.t")),
            (C("alias", "function"), t("lex.alias.i"), t("lex.alias.t")),
            (C("python3", "python"), t("lex.python3.i"), t("lex.python3.t")),
            (C("nano", "notepad"), t("lex.nano.i"), t("lex.nano.t")),
        ]),
        (t("lex.ch.maison"), ICI, [
            ("tg carte", t("lex.tg_carte.i"), t("lex.tg_carte.t")),
            ("tg quetes", t("lex.tg_quetes.i"), t("lex.tg_quetes.t")),
            ("tg aile", t("lex.tg_aile.i"), t("lex.tg_aile.t")),
            ("tg explique", t("lex.explique.i"), t("lex.explique.t")),
            ("tg envies", t("lex.tg_envies.i"), t("lex.tg_envies.t")),
        ]),
        (t("lex.ch.recensement"), ICI, [
            ("tg", t("lex.tg.i"), t("lex.tg.t")),
            ("tg site", t("lex.tg_site.i"), t("lex.tg_site.t")),
            ("tg collection", t("lex.tg_collection.i"), t("lex.tg_collection.t")),
            ("tg bestiaire", t("lex.tg_bestiaire.i"), t("lex.tg_bestiaire.t")),
            ("tg langue", t("lex.tg_langue.i"), t("lex.tg_langue.t")),
        ]),
        (t("lex.ch.telephone"), TEL, [
            ("ouvre", t("lex.ouvre.i"), t("lex.ouvre.t")),
            ("applis", t("lex.applis.i"), t("lex.applis.t")),
            ("sms", t("lex.sms.i"), t("lex.sms.t")),
            ("lampe", t("lex.lampe.i"), t("lex.lampe.t")),
            ("dis", t("lex.dis.i"), t("lex.dis.t")),
            ("web", t("lex.web.i"), t("lex.web.t")),
            ("carte", t("lex.carte.i"), t("lex.carte.t")),
        ]),
        (t("lex.ch.jeux"), TEL, [
            ("donjon", t("lex.donjon.i"), t("lex.donjon.t")),
            ("ctf", t("lex.ctf.i"), t("lex.ctf.t")),
            ("doom", t("lex.doom.i"), t("lex.doom.t")),
            ("edite", t("lex.edite.i"), t("lex.edite.t")),
            ("caresse", t("lex.caresse.i"), t("lex.caresse.t")),
            ("joue", t("lex.joue.i"), t("lex.joue.t")),
        ]),
    ]


def explication(image, technique, p):
    """Palier 0 : l'image · palier 1 : l'image — la technique · palier 2 : la technique (l'image)."""
    if p <= 0 or image == technique:
        return image
    if p == 1:
        return f"{image} {DIM}— {technique}{RESET}"
    return f"{technique} {DIM}({image}){RESET}"


def quand(state, mot):
    """Le moment de l'histoire où la commande a été apprise (carnet d'aventure), ou « »."""
    ou = ((state.get("histoire") or {}).get("carnet") or {}).get(mot)
    if not ou:
        return ""
    if ou in ("avant", "libre"):
        return t("hist.carnet." + ou)
    return t(f"hist.{ou}.court")


def souvenirs(state):
    """Les souvenirs du carnet : chapitres réveillés, quêtes finies, titres, objets."""
    from . import histoire, quetes
    q = quetes.q_(state)
    h = histoire.h_(state)
    out = ["", f"{fg(147)}{BOLD}" + t("lex.souvenirs") + RESET]
    for cid in h["ailes"]:
        out.append(f"  {fg(78)}✓{RESET} " + histoire.nom_chapitre(cid))
    if not h["ailes"]:
        out.append(f"  {DIM}" + t("lex.souvenirs.aucun") + RESET)
    out.append("  " + t("lex.souvenirs.quetes", n=len(q["finies"])))
    if q["titres"]:
        out.append("  " + t("lex.souvenirs.titres", liste=", ".join(t("qu.titre." + x) for x in q["titres"])))
    if q["objets"]:
        out.append("  " + t("lex.souvenirs.objets", liste=", ".join(t("qu.objet." + x) for x in q["objets"][-12:])))
    return out


def lignes(state):
    vus = {c.lower() for c in state.get("seen", [])}
    ici = OS_NAMES.get(OSK, "PC")
    p = palier(state)
    sortie = []
    total = 0
    goutees = 0
    for titre, univers, commandes in _entrees():
        autre = univers == TEL and OSK != "android"
        sortie.append("")
        sortie.append(f"{fg(147)}{BOLD}{titre}{RESET}" + (f" {DIM}" + t("lex.pas_ici", ici=ici) + RESET if autre else ""))
        for cmd, image, technique in commandes:
            mot = cmd.split()[0].lower()
            gout = mot in vus
            if autre:
                sortie.append(f"  {fg(238)}🔒 {cmd:<15} {image}{RESET}")
                continue
            total += 1
            goutees += gout
            desc = explication(image, technique, p)
            if gout:
                moment = quand(state, mot)
                moment = f" {fg(213)}· 📖 {moment}{RESET}" if moment else ""
                sortie.append(f"  {fg(255)}● {BOLD}{cmd:<15}{RESET}{fg(255)} {desc}{RESET}{moment}")
            else:
                sortie.append(f"  {fg(244)}○ {cmd:<15} {desc}{RESET}")
            ex = exemples.lexique(cmd)
            if ex:
                sortie.append(f"  {' ' * 18}{fg(110)}↳ " + t("lex.exemple", ex=ex) + RESET)
            g = explique.grand_commande(cmd.split()[0].lower(), technique)        # pour les grands
            if g:
                sortie.append(f"  {' ' * 18}{DIM}{g}{RESET}")
            for k, o in enumerate(explique.lignes_options(cmd.split()[0])):   # -r = « récursif »…
                debut = t("lex.options") + " " if k == 0 else ""
                sortie.append(f"  {' ' * 18}{DIM}{debut}{o}{RESET}")
    entete = [f" {fg(213)}── 📖 " + t("lex.carnet.titre", nom=state.get("name", "")) + RESET,
              f" {DIM}" + t("lex.titre", ici=ici, n=goutees, total=total) + RESET,
              f" {DIM}" + t("lex.legende") + RESET,
              f" {fg(110)}↳ " + t("lex.exemples.ou", cmd=f"cd ~/{core.TERRAIN.name}") + RESET,
              f" {fg(110)}📖 " + t("lex.explique", ex="tg explique rm") + RESET]
    return entete + sortie + souvenirs(state)


def images():
    """{commande : image} pour la recherche « / » (commandes Linux/Mac et Windows)."""
    out = {}
    for _t, _u, commandes in _entrees():
        for cmd, image, _tech in commandes:
            out.setdefault(cmd.split()[0].lower(), image)
    return out
