"""Les fiches notions du Port (charte de rigueur, docs/programme.md § 7.1) et sa place dans donnees/programme.json :
le monde (prérequis = niveaux du tronc commun, paliers, ponts, attirance, variantes réservées), la correspondance
niveaux du tronc → chapitres de l'histoire (« tronc »), les maths des étapes et les étapes rejouées dans bash.

    python3 donnees/port/outils/fiches_port.py      écrit donnees/programme.json et ses deux copies

Chaque cas « vrai_terminal » est rejoué dans un bash neuf par pc/outils/rejeu_bash.py, sur la boucle locale
seulement : un petit serveur python3 -m http.server --bind 127.0.0.1 (ou https avec un certificat auto-signé fait par
openssl) est lancé dans « prepare » et arrêté à la fin de « cmd ». Rien ne sort de la machine.
"""
import json
import shutil
from pathlib import Path

D = Path(__file__).resolve().parents[3]


def attendre(port, https=False):
    s = "s" if https else ""
    k = " -k" if https else ""
    return (f"for i in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do curl -s{k} -o /dev/null http{s}://127.0.0.1:{port}/ "
            f"&& break; sleep 0.3; done")


def serveur(port, dossier="."):
    return (f"python3 -m http.server {port} --bind 127.0.0.1 --directory {dossier} >/dev/null 2>&1 & echo $! > pid; "
            + attendre(port))


HTTPS = ("openssl req -x509 -newkey rsa:2048 -nodes -days 2 -keyout k.pem -out c.pem -subj /CN=localhost "
         "-addext subjectAltName=DNS:localhost,IP:127.0.0.1 >/dev/null 2>&1; "
         "python3 -c \"import http.server,ssl;s=http.server.HTTPServer(('127.0.0.1',8769),http.server.SimpleHTTPRequestHandler);"
         "c=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);c.load_cert_chain('c.pem','k.pem');"
         "s.socket=c.wrap_socket(s.socket,server_side=True);s.serve_forever()\" >/dev/null 2>&1 & echo $! > pid; "
         + attendre(8769, https=True))
FIN = "; kill $(cat pid)"


def fiche(nid, motif, vrai, sources):
    return nid, {"motif": motif, "enfant": f"port.f.{nid}.enfant", "grands": f"port.f.{nid}.grands",
                 "vrai_terminal": vrai, "limite_image": f"port.f.{nid}.limite", "idees_fausses": [f"port.f.{nid}.idee"],
                 "sources": sources, "relu_par": None}


FICHES = dict([
    fiche("localhost", r"\b(localhost|127\.0\.0\.1)\b", [
        {"cmd": "getent hosts localhost", "motif": r"^(127\.0\.0\.1|::1)\s+.*\blocalhost\b", "outil": "getent"},
        {"cmd": "ping -c 1 -W 2 127.42.0.2 | grep -o '1 received'", "sortie": "1 received", "si": "ping -c 1 -W 2 127.42.0.2"}],
        ["RFC 1122, § 3.2.1.3 (127.0.0.0/8, la boucle locale)", "RFC 6761, § 6.3 (le nom localhost)",
         "man 5 hosts : https://man7.org/linux/man-pages/man5/hosts.5.html"]),
    fiche("hosts", r"(\bhosts\b|annuaire|^getent\b|^resolve-dnsname\b|^dscacheutil\b)", [
        {"prepare": "printf '127.0.0.1\\tlocalhost camp\\n127.42.0.2\\tfeu.terminaworld feu\\n' > annuaire.txt",
         "cmd": "grep feu annuaire.txt", "sortie": "127.42.0.2\tfeu.terminaworld feu"},
        {"cmd": "grep -c localhost /etc/hosts", "motif": r"^[1-9]\d*$"}],
        ["man 5 hosts : https://man7.org/linux/man-pages/man5/hosts.5.html", "man 1 getent",
         "RFC 1034 et RFC 1035 (DNS)"]),
    fiche("http", r"^(curl|curl\.exe)\b.*(\s-\w*[Io]\b|https?://)", [
        {"prepare": serveur(8765), "cmd": "curl -sI http://127.0.0.1:8765/ | head -n 1" + FIN, "motif": r"^HTTP/1\.0 200 OK"},
        {"prepare": serveur(8766), "cmd": "curl -s -o /dev/null -w '%{http_code}\\n' http://127.0.0.1:8766/absent" + FIN,
         "sortie": "404"}],
        ["RFC 9110 (HTTP : méthodes, codes 200 et 404, en-têtes)", "RFC 9112 (HTTP/1.1)",
         "curl(1) : https://curl.se/docs/manpage.html"]),
    fiche("ssh_cles", r"(^ssh-keygen\b|cle_du_port|^(tg\s+)?port\s+t[eé]l[eé]porteur|teleporteur)", [
        {"cmd": "ssh-keygen -q -t ed25519 -N '' -C explorateur -f cle && cut -d ' ' -f 1,3 cle.pub",
         "sortie": "ssh-ed25519 explorateur", "outil": "ssh-keygen"},
        {"cmd": "ssh-keygen -q -t ed25519 -N '' -C explorateur -f cle && stat -c %a cle", "sortie": "600",
         "outil": "ssh-keygen"}],
        ["OpenSSH, ssh-keygen(1) : https://man.openbsd.org/ssh-keygen", "RFC 8709 (Ed25519 dans SSH)",
         "RFC 4251 (architecture de SSH)"]),
    fiche("serveur", r"(http\.server|^serveur\b|:8000\b)", [
        {"prepare": "mkdir quai; echo 'Bienvenue sur mon quai' > quai/index.html; " + serveur(8770, "quai"),
         "cmd": "curl -s http://127.0.0.1:8770/" + FIN, "sortie": "Bienvenue sur mon quai"},
        {"prepare": serveur(8771), "cmd": "curl -sI http://127.0.0.1:8771/ | grep -c '^Server: SimpleHTTP'" + FIN,
         "sortie": "1"}],
        ["Python, http.server : https://docs.python.org/3/library/http.server.html (« not recommended for production »)",
         "man 7 ip (adresse d'écoute 127.0.0.1 ou 0.0.0.0)"]),
    fiche("couches", r"(^(curl|curl\.exe)\b.*\s-\w*v\b|^(tg\s+)?port\s+couches|couches\.txt)", [
        {"prepare": serveur(8767), "cmd": "curl -sv -o /dev/null http://127.0.0.1:8767/ 2>&1 | grep -c '^> GET / HTTP/1.1'" + FIN,
         "sortie": "1"},
        {"prepare": serveur(8772), "cmd": "curl -sv -o /dev/null http://127.0.0.1:8772/ 2>&1 | grep -E 'Connected to'" + FIN,
         "motif": r"Connected to 127\.0\.0\.1 \(127\.0\.0\.1\) port 8772"}],
        ["RFC 1122 (les couches de l'Internet : application, transport, Internet, lien)",
         "ISO/IEC 7498-1 (le modèle OSI en 7 couches)", "RFC 9293 (TCP)", "RFC 791 (IP)"]),
    fiche("ports", r"(^(ss|netstat)\b|^(tg\s+)?port\s+carte\b)", [
        {"prepare": serveur(8768), "cmd": "ss -tln | grep -c '127.0.0.1:8768'" + FIN, "sortie": "1", "outil": "ss"},
        {"cmd": "ss -tln | head -n 1", "motif": r"^State\s+Recv-Q\s+Send-Q\s+Local Address:Port", "outil": "ss"}],
        ["man 8 ss : https://man7.org/linux/man-pages/man8/ss.8.html", "RFC 6335 (numéros de port)",
         "IANA, Service Name and Transport Protocol Port Number Registry"]),
    fiche("tcp_udp", r"(^ss\s+-\w*[tu]|^netstat\b.*\b(tcp|udp)\b|^(tg\s+)?port\s+course\b)", [
        {"cmd": "ss -t | head -n 1", "motif": r"Recv-Q\s+Send-Q", "outil": "ss"},
        {"cmd": "ss -u -a | head -n 1", "motif": r"Recv-Q\s+Send-Q", "outil": "ss"}],
        ["RFC 9293 (TCP)", "RFC 768 (UDP)", "man 7 tcp, man 7 udp"]),
    fiche("routage", r"(^ip\s+(-\d\s+)?r(oute)?\b|^route\s+print|^netstat\s+-\w*r|^(tracepath|traceroute|tracert)\b|"
                     r"^(tg\s+)?port\s+(messager|guide|[eé]teins|rallume|route)\b)", [
        {"cmd": "tracepath -n 127.0.0.1", "motif": r"reached", "outil": "tracepath"},
        {"cmd": "ping -c 1 -W 2 127.0.0.1 | grep -o 'ttl=[0-9]*'", "sortie": "ttl=64", "si": "ping -c 1 -W 2 127.0.0.1"},
        {"cmd": "ip route show table local | grep -c '127.0.0.0/8'", "motif": r"^[1-9]$", "outil": "ip"}],
        ["man 8 ip-route : https://man7.org/linux/man-pages/man8/ip-route.8.html", "man 8 tracepath",
         "RFC 791 (IP, durée de vie TTL)", "RFC 1812 (routeurs)"]),
    fiche("box_nat", r"(\|\s*grep\s+default\b|^ip\s+(-\d\s+)?n(eigh(bour)?)?\b|^arp\b|^ipconfig\b.*passerelle|"
                     r"^(tg\s+)?port\s+gardien\b)", [
        {"cmd": "ip -4 route show default", "motif": r"^default via \S+", "si": "ip -4 route show default | grep -q default"},
        {"cmd": "ip neigh > /dev/null; echo $?", "sortie": "0", "outil": "ip"}],
        ["RFC 2131 (DHCP)", "RFC 1918 (adresses privées)", "RFC 3022 (NAT)", "RFC 5737 (adresses de documentation)",
         "man 8 ip-neighbour"]),
    fiche("tls", r"(https://|--cacert\b|^(tg\s+)?port\s+sceau\b)", [
        {"prepare": HTTPS, "cmd": "curl -sS https://localhost:8769/ 2>&1; echo \"code $?\"" + FIN,
         "motif": r"self.signed certificate", "outil": "openssl"},
        {"prepare": HTTPS, "cmd": "curl -sS --cacert c.pem -o /dev/null -w '%{http_code}\\n' https://localhost:8769/" + FIN,
         "sortie": "200", "outil": "openssl"}],
        ["RFC 8446 (TLS 1.3)", "RFC 5280 (certificats X.509)", "RFC 9110, § 4.2.2 (https)",
         "curl(1), --cacert : https://curl.se/docs/manpage.html#--cacert", "man 1 openssl-req"]),
])

TRONC = {"note": "niveau du tronc commun → chapitres de l'histoire qui l'enseignent (§ 2.19) ; un monde s'ouvre quand "
                 "tous les chapitres de ses niveaux requis sont finis (arbre du Carrefour, § 2.9)",
         "n0": ["reveil"], "n1": ["reveil"], "n2": ["nid"], "n3": ["bibliotheque"], "n4": ["nid", "bibliotheque"],
         "n5": [], "n6": ["cave"]}

PORT = {"requis": ["n4"], "paliers": [f"port{i}" for i in range(12)],
        "attirance": {"cmds": ["ping", "curl", "ip", "ssh", "ss", "hostname"], "familles": ["Célestes"]},
        "ponts": {"ssh": ["atelier", "controle"], "curl": ["observatoire", "citadelle"],
                  "ports_ouverts": ["citadelle.hangar_ouvert", "ondes", "machines.m6"]},
        "variantes_reservees": ["plumange:orage", "tortunivers:lagon", "empyria:nuage"]}

ETAPES = {"port1.2": {"maths": ["pourcentages"]}, "port8.2": {"maths": ["comptage"]}, "port9.4": {"maths": ["comptage"]}}

REJEU = {
    "port0.1": {"contient": ["panneau.txt", "annuaire.txt", "carnet_de_bord.txt", "quai"],
                "pourquoi": "hist.port0.1.bravo : le panneau, l'annuaire, le carnet de bord et le quai"},
    "port1.2": {"motif": r"3 packets transmitted, 3 received, 0% packet loss", "outil": "ping",
                "pourquoi": "hist.port1.2.bravo : 3 échos, 0 % perdu"},
    "port2.2": {"sortie": "127.42.0.2\tfeu.terminaworld feu", "pourquoi": "hist.port2.2.bravo : feu → 127.42.0.2"},
    "port3.0": {"motif": r"^HTTP/1\.1 200 OK", "pourquoi": "hist.port3.0.bravo : 200 OK"},
    "port3.1": {"lignes": 3, "motif": r"eau\.terminaworld \(127\.42\.0\.3\)", "pourquoi": "hist.port3.1.bravo : les 3 premières lignes"},
    "port3.3": {"motif": r"^HTTP/1\.1 404 Not Found", "pourquoi": "hist.port3.3.bravo : 404"},
    "port4.2": {"motif": r"^ssh-ed25519 \S+ explorateur$", "outil": "ssh-keygen", "pourquoi": "hist.port4.2.bravo : ssh-ed25519 … explorateur"},
    "port5.2": {"motif": r"^Bienvenue sur mon quai$", "pourquoi": "hist.port5.2.bravo : ta page"},
    "port6.0": {"motif": r"^> GET / HTTP/1\.1", "pourquoi": "hist.port6.0.bravo : > GET / HTTP/1.1 (l'application)"},
    "port7.1": {"motif": r"127\.0\.0\.1:8042\b", "outil": "ss", "pourquoi": "hist.port7.1.bravo : 127.0.0.1:8042, la porte du phare"},
    "port9.1": {"motif": r"reached", "outil": "tracepath", "pourquoi": "hist.port9.1.bravo : un seul saut"},
    "port11.0": {"code": "non0", "motif": r"self.signed certificate", "outil": "openssl", "pourquoi": "hist.port11.0.bravo : curl refuse le sceau"},
    "port11.1": {"motif": r"/feu\s", "outil": "openssl", "pourquoi": "hist.port11.1.bravo : la page du phare, scellée"},
}


def main():
    f = D / "donnees/programme.json"
    P = json.loads(f.read_text(encoding="utf-8"))
    notions = {}
    for k, v in P["notions"].items():
        notions[k] = v
        if k == "traceroute":                      # les fiches du Port juste après celles du réseau d'avant
            notions.update(FICHES)
    notions.update({k: v for k, v in FICHES.items() if k not in notions})
    P["notions"] = notions
    # le curl d'avant visait example.com (rejoué seulement avec le réseau) : un cas local en plus, toujours rejoué
    cas = P["notions"]["curl"]["vrai_terminal"]
    local = {"prepare": serveur(8773), "cmd": "curl -s http://127.0.0.1:8773/ | grep -c '<h1>Directory listing'" + FIN,
             "sortie": "1"}
    P["notions"]["curl"]["vrai_terminal"] = [c for c in cas if "8773" not in c.get("cmd", "")] + [local]
    P["tronc"] = TRONC
    for m in P["mondes"]:
        if m["id"] == "port":
            m.update(PORT)
    P["etapes"].update(ETAPES)
    P["rejeu"].update(REJEU)
    texte = json.dumps(P, ensure_ascii=False, indent=1) + "\n"
    f.write_text(texte, encoding="utf-8")
    for c in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        shutil.copyfile(f, D / c)
    print(f"{len(FICHES)} fiches du Port, {len(REJEU)} étapes rejouées")


if __name__ == "__main__":
    main()
