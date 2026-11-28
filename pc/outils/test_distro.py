"""La distribution pratiquée (pc/tg/distro.py) : détection par /etc/os-release, choix dans les réglages, conseils."""
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
os.environ["HOME"] = tempfile.mkdtemp(prefix="tgd")
from tg import distro as D  # noqa: E402

ok = ko = 0


def verifier(c, msg):
    global ok, ko
    print(("  ✔ " if c else "  ✖ ") + msg)
    ok, ko = ok + bool(c), ko + (not c)


print("1. Reconnaître la distribution (/etc/os-release)")
cas = {'ID=ubuntu\nID_LIKE=debian': "ubuntu", 'ID=debian': "debian", 'ID=linuxmint\nID_LIKE="ubuntu debian"': "mint",
       'ID=fedora': "fedora", 'ID="rocky"\nID_LIKE="rhel centos fedora"': "fedora", 'ID=arch': "arch",
       'ID=manjaro\nID_LIKE=arch': "arch", 'ID="opensuse-tumbleweed"\nID_LIKE="opensuse suse"': "opensuse",
       'ID=pop\nID_LIKE="ubuntu debian"': "ubuntu", 'ID=zzz\nID_LIKE=fedora': "fedora", 'ID=gentoo': None}
for texte, attendu in cas.items():
    verifier(D.reconnaitre(D.os_release_de(texte)) == attendu, f"{texte.splitlines()[0]} → {attendu}")
print("2. Le magasin et la commande d'installation de chaque distribution")
verifier(D.installer("ubuntu", "compiler") == "sudo apt install build-essential", "Ubuntu : build-essential")
verifier(D.installer("fedora", "compiler") == "sudo dnf install gcc make", "Fedora : gcc make")
verifier(D.installer("arch", "compiler") == "sudo pacman -S base-devel", "Arch : base-devel")
verifier(D.installer("opensuse", "git") == "sudo zypper install git", "openSUSE : zypper")
verifier(D.magasin("arch")["compte"] == "pacman -Q | wc -l", "Arch : compter les paquets avec pacman -Q")
verifier(D.installer(None, "git") is None, "aucune distribution : pas de conseil")
print("3. Le réglage : auto ou choisie")
st = {}
verifier(D.courante(st)[1] == "auto", "par défaut : automatique")
D.changer(st, "Fedora")
verifier(D.courante(st) == ("fedora", "choisie"), "tg distro Fedora → fedora")
D.changer(st, "manjaro")
verifier(D.courante(st)[0] == "arch", "un dérivé (manjaro) → sa famille (arch)")
verifier("ubuntu" in D.changer(st, "gentoo"), "une distribution inconnue : la liste des choix")
verifier(D.courante(st)[0] == "arch", "… et le choix d'avant est gardé")
D.changer(st, "auto")
verifier(D.choix(st) == "auto", "tg distro auto : retour à la détection")
print(f"\n{ok} réussis, {ko} ratés")
sys.exit(1 if ko else 0)
