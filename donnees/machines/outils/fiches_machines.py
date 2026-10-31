"""Les fiches notions de la Salle des Machines (charte de rigueur, docs/programme.md § 7.1) et sa place dans
donnees/programme.json : le monde (prérequis = niveaux 0 à 3 du tronc commun, paliers, ponts, attirance, exploit,
variantes réservées des types Machine et Roche), les maths des étapes (Ponts des Nombres) et les étapes rejouées dans bash.

    python3 donnees/machines/outils/fiches_machines.py      écrit donnees/programme.json et ses deux copies

Chaque cas « vrai_terminal » est rejoué dans un bash neuf par pc/outils/rejeu_bash.py, dans un terrain jetable. Les
sorties qui dépendent de la machine (nombre de cœurs, mémoire, version du noyau) ne sont jamais écrites telles
quelles : le cas vérifie leur FORME (motif), ou les compare à ce que le jeu calcule sur la même machine (« egal_jeu »,
étapes de l'histoire). Les cas qui téléchargent (podman) ne se rejouent pas (« rejeu »: « reseau ») ; ceux du
téléphone non plus (« telephone »). Rien ne sort du terrain, jamais de sudo.
"""
import json
import shutil
from pathlib import Path

D = Path(__file__).resolve().parents[3]


def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"ma.f.{nid}.enfant", "grands": f"ma.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"ma.f.{nid}.limite", "idees_fausses": [f"ma.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


FICHES = dict([
    fiche("organes", r"(^nproc\b|^lscpu\b|^free\b|^lsblk\b|machines\s+(coeurs|memoire|ouvre))", [
        {"cmd": "nproc | grep -cE '^[1-9][0-9]*$'", "sortie": "1"},
        {"cmd": "test \"$(nproc)\" -le \"$(grep -c ^processor /proc/cpuinfo)\" && echo ok", "sortie": "ok"},
        {"cmd": "free -h | head -n 1 | awk '{print $1}'", "sortie": "total"},
        {"cmd": "lsblk -d -o TYPE | head -n 1", "sortie": "TYPE", "outil": "lsblk"},
        {"cmd": "nproc", "rejeu": "telephone", "motif": r"^[1-9][0-9]*$"}],
        ["man 1 nproc (GNU coreutils) : https://www.gnu.org/software/coreutils/manual/html_node/nproc-invocation.html",
         "man 1 free (procps-ng), man 1 lscpu et man 8 lsblk (util-linux)",
         "Documentation du noyau Linux, The /proc Filesystem (meminfo) : https://docs.kernel.org/filesystems/proc.html",
         "Programme de NSI (première) : architecture matérielle, modèle de von Neumann"]),
    fiche("peripheriques", r"(/proc/cpuinfo|^lspci\b|^lsusb\b|^getprop\b|machines\s+monte\s+1\b)", [
        {"cmd": "grep -c ^processor /proc/cpuinfo | grep -cE '^[1-9]'", "sortie": "1"},
        {"cmd": "head -n 1 /proc/cpuinfo | cut -d: -f1 | tr -d ' \\t'", "sortie": "processor"},
        {"cmd": "lspci | head -n 1 | grep -cE '^[0-9a-f]{2}:[0-9a-f]{2}\\.[0-7] '", "sortie": "1", "outil": "lspci"},
        {"cmd": "getprop ro.product.model", "rejeu": "telephone", "motif": r"\S"}],
        ["man 8 lspci (pciutils) : https://man7.org/linux/man-pages/man8/lspci.8.html", "man 8 lsusb (usbutils)",
         "man 5 proc, /proc/cpuinfo : https://man7.org/linux/man-pages/man5/proc_cpuinfo.5.html",
         "Android, propriétés système (getprop) : https://source.android.com/docs/core/architecture/configuration/add-system-properties"]),
    fiche("binaire", r"(printf\s+['\"]?%x|xxd\s+-\w*b|\bod\b|machines\s+(interrupteurs|allume))", [
        {"cmd": "printf '%x\\n' 65", "sortie": "41"},
        {"cmd": "printf A | od -An -tx1", "sortie": " 41"},
        {"cmd": "printf '\\303\\251' | od -An -tx1", "sortie": " c3 a9"},
        {"cmd": "echo $((2#01000001))", "sortie": "65"},
        {"cmd": "echo -n A | xxd -b", "motif": r"^00000000: 01000001 +A$", "outil": "xxd"}],
        ["ANSI X3.4-1986 (ASCII), ISO/IEC 646", "RFC 3629 (UTF-8) : https://www.rfc-editor.org/rfc/rfc3629",
         "The Unicode Standard, chap. 3 (UTF-8)", "man 1 xxd, man 1 od ; POSIX.1-2024, printf"]),
    fiche("unites", r"(stat\b.*%s|wc\s+-c|photo\.bin|machines\s+unit)", [
        {"cmd": "head -c 1048576 /dev/zero > f && stat -c %s f", "sortie": "1048576"},
        {"prepare": "head -c 1048576 /dev/zero > photo.bin", "cmd": "wc -c photo.bin", "sortie": "1048576 photo.bin"},
        {"cmd": "echo $((1024*1024)) $((1000*1000))", "sortie": "1048576 1000000"},
        {"cmd": "numfmt --to=iec 1048576", "sortie": "1.0M"},
        {"cmd": "numfmt --to=si 1048576", "sortie": "1.1M"}],
        ["CEI 80000-13:2008 (préfixes binaires Ki, Mi, Gi)", "BIPM, Le Système international d'unités, 9e édition (2019) : préfixes k, M, G",
         "man 1 numfmt, man 1 stat (GNU coreutils)"]),
    fiche("demarrage", r"(^uname\s+-\w*r|^uptime\b|/proc/uptime|^dmesg\b|systemd-analyze|machines\s+r[eé]veil)", [
        {"cmd": "uname -s", "sortie": "Linux"},
        {"cmd": "awk '{print ($1 > 0)}' /proc/uptime", "sortie": "1"},
        {"cmd": "uptime | grep -c 'load average'", "sortie": "1"}],
        ["UEFI Specification 2.10 (UEFI Forum, 2022) : https://uefi.org/specifications",
         "man 7 bootup (systemd) : https://www.freedesktop.org/software/systemd/man/latest/bootup.html",
         "man 1 systemd-analyze ; man 1 dmesg ; Documentation du noyau, sysctl kernel.dmesg_restrict",
         "The Linux kernel user's and administrator's guide, boot : https://docs.kernel.org/admin-guide/"]),
    fiche("systeme_exploitation", r"(^uname\b|os-release|^ps\b|^which\s+ls|^command\s+-v\s+ls|^lsmod\b|/proc/modules|"
                                  r"machines\s+(orchestre|licences?))", [
        {"cmd": "uname -s", "sortie": "Linux"},
        {"cmd": ". /etc/os-release && test -n \"$ID\" && echo ok", "sortie": "ok"},
        {"cmd": "command -v ls", "motif": r"^/(usr/)?bin/ls$"},
        {"cmd": "ps -p 1 -o pid= | tr -d ' '", "sortie": "1"},
        {"cmd": "getprop ro.build.version.release", "rejeu": "telephone", "motif": r"^[0-9]+"}],
        ["man 5 os-release : https://www.freedesktop.org/software/systemd/man/latest/os-release.html", "man 1 uname, man 1 ps, man 8 lsmod",
         "Free Software Foundation, Qu'est-ce que le logiciel libre ? https://www.gnu.org/philosophy/free-sw.fr.html",
         "Linux, fichier COPYING (GPL version 2) ; Open Source Initiative, licence MIT"]),
    fiche("virtualisation", r"(/proc/(1|self)/cgroup|machines\s+(bo[iî]te|range))", [
        {"cmd": "test -r /proc/1/cgroup && echo lisible", "sortie": "lisible"},
        {"cmd": "grep -c ':' /proc/self/cgroup | grep -cE '^[1-9]'", "sortie": "1"}],
        ["man 7 cgroups, man 7 namespaces : https://man7.org/linux/man-pages/man7/cgroups.7.html",
         "G. Popek et R. Goldberg, Formal requirements for virtualizable third generation architectures (1974)",
         "Open Container Initiative, Image et Runtime Specifications : https://opencontainers.org/",
         "KVM : https://www.linux-kvm.org/"]),
    fiche("machine_virtuelle", r"(podman|qemu-img|virsh|conteneur_jetable|machines\s+(adulte|conteneur|vm)|^command\s+-v\s+podman)", [
        {"cmd": "qemu-img create -f qcow2 d.qcow2 1G", "motif": r"^Formatting 'd\.qcow2', fmt=qcow2 .*size=1073741824",
         "outil": "qemu-img"},
        {"prepare": "qemu-img create -f qcow2 d.qcow2 1G >/dev/null", "cmd": "qemu-img info d.qcow2 | grep '^virtual size'",
         "sortie": "virtual size: 1 GiB (1073741824 bytes)", "outil": "qemu-img"},
        {"cmd": "podman run --rm --network=none docker.io/library/alpine:3.20 echo bonjour", "sortie": "bonjour", "rejeu": "reseau"}],
        ["Podman, podman-run(1) (--rm, --root, --runroot) : https://docs.podman.io/en/latest/markdown/podman-run.1.html",
         "QEMU, qemu-img : https://www.qemu.org/docs/master/tools/qemu-img.html",
         "libvirt, virsh(1) (lecture seule -r, snapshot-create-as) : https://libvirt.org/manpages/virsh.html",
         "Image officielle Alpine Linux : https://hub.docker.com/_/alpine"]),
    fiche("datacenter", r"(^df\b|^du\b|machines\s+(ferme|[eé]nergie))", [
        {"cmd": "df -h . | head -n 1 | awk '{print $1}'", "sortie": "Filesystem"},
        {"cmd": "echo $((300 * 8760)) $((300 * 8760 / 1000))", "sortie": "2628000 2628"}],
        ["NIST SP 800-145, The NIST Definition of Cloud Computing (2011)",
         "ADEME et Arcep, Évaluation de l'impact environnemental du numérique en France (2022)",
         "The Green Grid, PUE : A Comprehensive Examination of the Metric (2012)", "man 1 df, man 1 du (GNU coreutils)"]),
    fiche("sauvegarde_321", r"(sauvegarde\.(tar\.gz|sha256)|ferme/|machines\s+panne|^tar\s+-?x)", [
        {"prepare": "echo creatures > c", "cmd": "tar czf s.tgz c && tar tzf s.tgz", "sortie": "c"},
        {"prepare": "echo creatures > c; tar czf s.tgz c; sha256sum s.tgz > s.sha256", "cmd": "sha256sum -c s.sha256",
         "sortie": "s.tgz: OK"},
        {"prepare": "echo creatures > c; tar czf s.tgz c; rm c; mkdir l; cp s.tgz l/", "cmd": "tar xzf l/s.tgz && cat c",
         "sortie": "creatures"}],
        ["US-CERT (CISA), Data Backup Options (2012) : la règle 3-2-1",
         "ANSSI, Guide d'hygiène informatique (2017), mesure 37 : définir et appliquer une politique de sauvegarde",
         "man 1 tar (GNU tar), man 1 sha256sum (GNU coreutils)"]),
    fiche("assemblage", r"machines\s+(monte|demarre|drapeau)", [
        {"cmd": "echo $((65 + 20 + 5 + 4 + 120))", "sortie": "214"}],
        ["JEDEC JESD79-4 (DDR4) et JESD79-5 (DDR5) : deux types de mémoire qui ne se remplacent pas",
         "Intel, ATX12V Power Supply Design Guide : l'alimentation doit couvrir la consommation",
         "Décision du propriétaire (§ 7.3) : pièces génériques, sans marque ni prix réel ; budget en points fictifs"]),
])

MACHINES = {"requis": ["n0", "n1", "n2", "n3"], "paliers": [f"sm{i}" for i in range(11)], "chapitre": "machinerie",
            "attirance": {"cmds": ["nproc", "lscpu", "free", "lsblk", "lspci", "uname"], "familles": ["Constructs"]},
            "ponts": {"ressources": ["controle"], "ports": ["port"], "sha256sum": ["citadelle", "crypte"],
                      "tar": ["citadelle", "controle"], "binaire": ["crypte"]},
            "exploits": [{"id": "machines.premier_demarrage", "nom": "recomp.machines.premier_demarrage", "recompense": "variante"}],
            "maths": ["binaire", "hexadecimal", "puissances", "multiplication", "addition"],
            "variantes_reservees": ["chaudrogre:mecanique", "homardeur:mecanique", "golemmur:desert", "magmastodonte:canyon"]}

ETAPES = {"sm3.0": {"maths": ["hexadecimal"]}, "sm3.3": {"maths": ["binaire"]}, "sm3.5": {"maths": ["puissances"]},
          "sm8.3": {"maths": ["multiplication"]}, "sm10.1": {"maths": ["addition"]}}

REJEU = {
    "sm1.0": {"motif": r"^[1-9][0-9]*$", "egal_jeu": "coeurs", "pourquoi": "hist.sm1.0.bravo : le nombre de cœurs (le jeu compte aussi)"},
    "sm1.2": {"motif": r"^Mem:\s+\S+", "pourquoi": "hist.sm1.2.bravo : la ligne « Mem », colonne « total »"},
    "sm2.1": {"motif": r"^[1-9][0-9]*$", "egal_jeu": "cpuinfo", "pourquoi": "hist.sm2.1.bravo : une fiche par unité de calcul"},
    "sm3.0": {"sortie": "41", "pourquoi": "hist.sm3.0.bravo : 41"},
    "sm3.1": {"motif": r"^00000000: 01000001 +A$", "outil": "xxd", "pourquoi": "hist.sm3.1.bravo : 01000001"},
    "sm3.4": {"sortie": "1048576 photo.bin", "pourquoi": "hist.sm3.4.bravo : 1 048 576 octets"},
    "sm4.0": {"egal_jeu": "noyau", "pourquoi": "hist.sm4.0.bravo : la version du noyau (le jeu la lit aussi)"},
    "sm4.1": {"motif": r"load average", "pourquoi": "hist.sm4.1.adulte : la charge moyenne"},
    "sm5.0": {"motif": r"^Linux \S+ \S+", "pourquoi": "hist.sm5.0.bravo : le nom du noyau, sa version, le processeur"},
    "sm5.3": {"motif": r"^/(usr/)?bin/ls$", "pourquoi": "hist.sm5.3.bravo : souvent /usr/bin"},
    "sm7.6": {"motif": r"^Formatting 'disque_virtuel\.qcow2', fmt=qcow2 .*size=1073741824", "outil": "qemu-img",
              "pourquoi": "hist.sm7.6.bravo : 1 Gio annoncé"},
    "sm7.7": {"motif": r"^virtual size: 1 GiB \(1073741824 bytes\)$", "outil": "qemu-img", "pourquoi": "hist.sm7.7.bravo : virtual size"},
    "sm8.0": {"motif": r"^Filesystem\s+Size\s+Used\s+Avail\s+Use%\s+Mounted on$", "pourquoi": "hist.sm8.0.bravo : taille, utilisé, disponible"},
    "sm9.0": {"contient": ["disque_2", "loin"], "pourquoi": "hist.sm9.0.bravo : disque_2 et loin"},
    "sm9.7": {"sortie": "sauvegarde.tar.gz: OK", "pourquoi": "hist.sm9.7.bravo : OK"},
}


def main():
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {k: v for k, v in P["notions"].items() if k not in FICHES}
    notions.update(FICHES)
    P["notions"] = notions
    for m in P["mondes"]:
        if m["id"] == "machines":
            m.update(MACHINES)
    for cle in ("etapes", "rejeu"):                   # les étapes de la Salle : exactement celles d'ici
        P[cle] = {k: v for k, v in P[cle].items() if not (k.startswith("sm") and k.split(".")[0][2:].isdigit())}
    P["etapes"].update(ETAPES)
    P["rejeu"].update(REJEU)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    for c in ("pc/tg/machines.json", "app/src/main/assets/machines.json"):
        shutil.copyfile(D / "donnees/machines.json", D / c)
    print(f"{len(FICHES)} fiches de la Salle des Machines, {len(REJEU)} étapes rejouées")


if __name__ == "__main__":
    main()
