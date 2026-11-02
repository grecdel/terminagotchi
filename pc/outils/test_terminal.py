"""Le terminal du jeu (Windows) comparé au VRAI bash + coreutils (décision du 2 novembre).

    python3 pc/outils/test_terminal.py [--fiches] [--syntaxe] [--windows] [--git] [--python-curl] [--garde] [-v]   (tout par défaut)

1. Les fiches : chaque cas « vrai_terminal » de donnees/programme.json est préparé par le vrai bash dans deux dossiers
   jetables identiques, puis la commande est lancée dans le vrai bash (bash -c) et dans le terminal du jeu ; la sortie
   et le code de sortie doivent être les MÊMES (les chemins des deux dossiers et « bash: line 1: » ramenés à la même
   écriture). Une commande que le terminal du jeu n'a pas est « racontée » (comptée, avec la liste) ; une différence
   est un échec.
2. La syntaxe : des lignes de shell (guillemets, $( ), $(( )), jokers, redirections, tuyaux, if/for/while/case,
   fonctions, alias, read, export, ${x%…}, here-doc…) comparées au vrai bash de la même façon.
3. Le Linux virtuel de Windows (simulé ici) : / montre bin, etc, home, tmp… ; ~ ne montre que le terrain ; on ne peut
   pas écrire hors du terrain ; chmod est gardé et respecté ; les vrais fichiers sont bien modifiés.
4. Le petit git contre le vrai git. 5. python3 (le Python du jeu) contre le vrai python3, et curl contre le vrai curl
   sur le même phare du Port (127.0.0.1:8042 ; la date et les vitesses mises de côté). 6. Les garde-fous : python3
   n'écrit, ne lit, ne lance rien hors du terrain et ne va pas sur le réseau ; curl ne parle qu'au phare.
Utilisé par tout.sh (pc) et en CI (.github/workflows/rejeu.yml, sur une vraie machine Linux).
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))
os.environ.setdefault("LANG", "C.UTF-8")
from tg import langue  # noqa: E402

langue.definir("fr")
from tg.vsh import CoquilleVirtuelle, Vfs, outils  # noqa: E402

BAVARD = "-v" in sys.argv
ok = ko = 0
racontes = {}
ecarts = []


def verifier(c, m):
    global ok, ko
    ok, ko = ok + bool(c), ko + (not c)
    if not c or BAVARD:
        print(("  ✔ " if c else "  ✖ ") + m)
    if not c:
        ecarts.append(m)


def _moi():
    import getpass
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001
        return "eleve"


ENV = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "LC_ALL": "C", "USER": os.environ.get("USER") or _moi(),
       "TERM": "dumb", "GIT_CONFIG_NOSYSTEM": "1"}
if os.environ.get("TZ"):
    ENV["TZ"] = os.environ["TZ"]


def normaliser(s, dossier, home):
    s = s.replace(str(dossier), "@ICI").replace(str(home), "@HOME")
    s = re.sub(r"bash: -c: line \d+: `.*'\n", "", s)
    s = re.sub(r"^bash: line \d+: `.*'\n", "", s, flags=re.M)
    s = re.sub(r"bash: (-c: )?line \d+: ", "bash: ", s)
    s = re.sub(r"^/bin/sh: \d+: ", "bash: ", s, flags=re.M)
    return s


def deux_terrains():
    out = []
    for _ in range(2):
        home = Path(tempfile.mkdtemp(prefix="tg_vsh_"))
        (home / "terrain").mkdir()
        out.append(home)
    return out


def bash(cmd, terrain, home, entree=None):
    env = dict(ENV, HOME=str(home))
    r = subprocess.run(["bash", "--norc", "-c", cmd], cwd=terrain, env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, input=entree, timeout=40)
    return r.stdout.decode("utf-8", "replace"), r.returncode


def virtuel(cmd, terrain, home):
    vfs = Vfs(mode="transparent", home=home, terrain=terrain, jeu=home / ".terminagotchi", zones=[home],
              utilisateur=ENV["USER"])
    c = CoquilleVirtuelle(cwd=terrain, vfs=vfs, env=ENV)     # (LC_ALL=C, comme le vrai bash à côté)
    c.sh.vars["HOME"] = str(home)
    c.sh.vars["USER"] = ENV["USER"]
    s, code, _d = c.lancer(cmd, delai=40)
    c.fermer()
    return s, code


def commandes_de(ligne):
    """Les commandes d'une ligne (pour savoir si une est racontée)."""
    out = []
    for morceau in re.split(r"\|\||&&|[|;&()]|\$\(|`|\bthen\b|\bdo\b|\belse\b", ligne):
        mots = morceau.strip().split()
        while mots and re.match(r"^[A-Za-z_]\w*=", mots[0]):
            mots = mots[1:]
        if mots and mots[0] not in ("if", "fi", "for", "while", "done", "!", "{", "}", "in", "time"):
            out.append(mots[0].strip("'\""))
    return out


# ce que le terminal du jeu montre de SA machine virtuelle (ses tâches, son disque, son heure) : ces commandes
# existent, mais leur sortie ne peut pas être celle d'une autre machine
PROPRES = {"ps", "uptime", "df", "free", "date", "hostname", "uname", "nproc", "id", "pgrep", "pidof", "killall", "pkill",
           "stat", "tty", "env", "printenv"}


def racontee(ligne):
    u = outils.usage_raconte(ligne)
    if u:                       # python3 -m http.server, curl vers une autre adresse que le phare : racontés ici
        return u + " (usage raconté : -m, ou une autre adresse que le phare)"
    for c in commandes_de(ligne):
        if c in outils.RACONTEES and outils.TOUS.get(c) is None:
            return c
        if c in PROPRES:
            return c + " (propre à la machine)"
        if c in outils.TOUS and not shutil.which(c) and c not in ("pwd", "echo", "printf", "test", "["):
            return c + " (absent de cet ordinateur)"
    return None


def comparer(nom, cmd, prepare=None, entree=None, trie=False, norm=None):
    absente = racontee(cmd) or (racontee(prepare) if prepare and racontee(prepare) and
                                not racontee(prepare).endswith("machine)") else None)
    if absente is None and re.search(r"/proc/|\$PATH\b", cmd):
        absente = "/proc, PATH (propres à la machine)"
    if absente:
        racontes.setdefault(absente, []).append(nom)
        return
    (ha, hb) = deux_terrains()
    ta, tb = ha / "terrain", hb / "terrain"
    try:
        if prepare:
            subprocess.run(["bash", "--norc", "-c", prepare], cwd=ta, env=dict(ENV, HOME=str(ha)),
                           capture_output=True, timeout=20)
            if racontee(prepare) is None and re.search(r"\bgit\b", prepare):
                coq = None                            # (les dépôts du terminal du jeu : préparés par son petit git)
                sb0, _cb0 = virtuel(prepare, tb, hb)
            else:
                subprocess.run(["bash", "--norc", "-c", prepare], cwd=tb, env=dict(ENV, HOME=str(hb)),
                               capture_output=True, timeout=20)
        sa, ca = bash(cmd, ta, ha)
        sb, cb = virtuel(cmd, tb, hb)
        na, nb = normaliser(sa, ta, ha), normaliser(sb, tb, hb)
        if norm:
            na, nb = norm(na), norm(nb)
        if trie:
            na, nb = "\n".join(sorted(na.split("\n"))), "\n".join(sorted(nb.split("\n")))
        egal = na == nb and ca == cb
        msg = f"{nom} : `{cmd}`"
        if not egal:
            msg += f"\n      bash  ({ca}) : {na[:400]!r}\n      jeu   ({cb}) : {nb[:400]!r}"
        verifier(egal, msg)
    finally:
        shutil.rmtree(ha, ignore_errors=True)
        shutil.rmtree(hb, ignore_errors=True)


def fiches():
    print("1. Les fiches (vrai_terminal) : le vrai bash et le terminal du jeu, côte à côte")
    P = json.loads((RACINE / "donnees" / "programme.json").read_text(encoding="utf-8"))
    for nid, n in P["notions"].items():
        for k, cas in enumerate(n["vrai_terminal"]):
            if cas.get("rejeu"):
                continue
            if cas.get("si"):
                (h,) = deux_terrains()[:1]
                r = subprocess.run(["bash", "--norc", "-c", cas["si"]], cwd=h / "terrain", env=dict(ENV, HOME=str(h)),
                                   capture_output=True, timeout=20)
                shutil.rmtree(h, ignore_errors=True)
                if r.returncode != 0:
                    continue
            outil = cas.get("outil")
            if outil and not (os.path.exists(outil) if outil.startswith("/") else shutil.which(outil)):
                continue
            trie = bool(re.match(r"^(find|grep -r|grep -rl|grep -rn)\b", cas["cmd"]))
            comparer(f"{nid}#{k}", cas["cmd"], cas.get("prepare"), trie=trie)


SYNTAXE = [
    ("echo 'a  b'  \"c  d\"  e\\ f", None),
    ("x='un deux'; echo $x; echo \"$x\"; printf '[%s]\\n' $x", None),
    ("echo ${HOME:+oui} ${NOPE:-defaut} ${#HOME} x${NOPE}y", None),
    ("f=archive.tar.gz; echo ${f%.gz} ${f%%.*} ${f#*.} ${f##*.} ${f/tar/zip}", None),
    ("echo $((3 + 4 * 2)) $(( (3+4)*2 )) $((17 / 5)) $((-17 / 5)) $((17 % 5)) $((2**10)) $((1<2 && 3>2))", None),
    ("i=5; i=$((i+1)); echo $i; echo $((i++)) $i $((++i))", None),
    ("echo $(echo un; echo deux) \"$(echo un; echo deux)\"", None),
    ("echo `echo vieux style`", None),
    ("mkdir d; touch d/a.txt d/b.txt d/c.log; echo d/*.txt; echo d/*.zip; echo 'd/*.txt'", None),
    ("touch b a c; ls; ls | sort -r | head -n 2", None),
    ("echo un > f; echo deux >> f; cat f; cat < f | wc -l", None),
    ("ls nope 2> err; cat err; ls nope > tout 2>&1; cat tout; ls nope 2>/dev/null; echo $?", None),
    ("true && echo oui || echo non; false && echo oui || echo non; false; echo $?; ! false; echo $?", None),
    ("if [ 5 -lt 10 ]; then echo petit; elif [ 5 -eq 10 ]; then echo egal; else echo grand; fi", None),
    ("[ -f nope ] || echo absent; touch t; [ -f t ] && echo fichier; [ -d . ] && echo dossier", None),
    ("for f in 1 2 3; do for g in a b; do echo $f$g; done; done", None),
    ("for i in $(seq 1 5); do [ $i -eq 3 ] && continue; [ $i -eq 5 ] && break; echo $i; done", None),
    ("n=0; until [ $n -ge 3 ]; do n=$((n+1)); echo tour $n; done", None),
    ("for x in pomme poire kiwi; do case $x in p*) echo \"$x commence par p\";; *) echo \"$x autre\";; esac; done", None),
    ("salut() { echo \"Salut $1, tu as $# arguments\"; return 3; }; salut Lea x y; echo code $?", None),
    ("compte() { local n=$1; echo $n; }; n=9; compte 4; echo $n", None),
    ("shopt -s expand_aliases\nalias miam='echo Miam !'\nmiam", None),
    ("echo 'echo \"script $1\"' > s.sh; sh s.sh arg; bash s.sh deux; chmod +x s.sh; ./s.sh trois", None),
    ("echo 'echo dedans' > s.sh; ./s.sh; echo $?", None),
    ("export COULEUR=bleu; sh -c 'echo $COULEUR'; PAS=la; sh -c 'echo x$PAS'", None),
    ("echo 'read prenom; echo \"Salut $prenom !\"' > q.sh; echo Léa | sh q.sh", None),
    ("printf '%s-%d-%05.2f-%x\\n' mot 42 3.14159 255; printf '%s\\n' a b c", None),
    ("echo -n sans; echo; echo -e 'a\\tb\\nc'", None),
    ("cat <<FIN\nligne $HOME\nautre\nFIN", None),
    ("cat <<'FIN'\nbrut $HOME\nFIN", None),
    ("(cd /; pwd); pwd", None),
    ("{ echo a; echo b; } > g; cat g", None),
    ("x=1; (x=2; echo $x); echo $x", None),
    ("echo début; exit 3; echo jamais", None),
    ("set -- un deux trois; echo $# $2 \"$@\"; shift; echo $1", None),
    ("cd /tmp && cd - && cd -", None),
    ("cd nope; echo $?", None),
    ("echo $(( 10 / 0 ))", None),
    ("type cd echo ls; command -v ls", None),
    ("v=\"a b c\"; for m in $v; do echo \"[$m]\"; done; for m in \"$v\"; do echo \"[$m]\"; done", None),
    ("IFS=,; ligne='a,b,,c'; for m in $ligne; do echo \"<$m>\"; done", None),
    ("echo ~ ~/x \"~\"", None),
    ("umask 077; touch secret; ls -l secret | cut -c1-10", None),
    ("echo abc | tr a-z A-Z; echo 'Hello World' | tr -d o; echo aaabbb | tr -s ab", None),
    ("printf 'b\\na\\nc\\na\\n' | sort | uniq -c", None),
    ("printf '10\\n9\\n100\\n' | sort -n; printf '10\\n9\\n100\\n' | sort", None),
    ("printf 'x,3\\ny,1\\nz,2\\n' | sort -t, -k2 -n", None),
    ("printf 'a:b:c\\nd:e:f\\n' | cut -d: -f2,3", None),
    ("seq 3; seq 2 4; seq 0 5 20; seq -s, 5", None),
    ("echo bonjour | rev; echo un deux trois | wc -w", None),
    ("printf 'l1\\nl2\\nl3\\nl4\\nl5\\n' > f; head -n 2 f; tail -n 2 f; tail -n +4 f; head -c 4 f; echo", None),
    ("printf 'pomme\\nPoire\\nkiwi\\n' > f; grep -i p f; grep -c i f; grep -v kiwi f; grep -n o f", None),
    ("printf 'a1\\nb22\\nc333\\n' | grep -E '[0-9]{2,}'; printf 'a1\\nb22\\n' | grep -o '[0-9]'", None),
    ("printf 'un\\ndeux\\n' > a; printf 'un\\ntrois\\n' > b; diff a b; echo $?", None),
    ("printf 'x\\ny\\nz\\n' > a; printf 'x\\nz\\nw\\n' > b; diff a b; diff -u a b | tail -n +3", None),
    ("printf 'chat chien\\n' | sed 's/ch/CH/'; printf 'chat chien\\n' | sed 's/ch/CH/g'; printf '1\\n2\\n3\\n' | sed -n '2p'", None),
    ("printf 'a\\nb\\nc\\n' > f; sed -i '2d' f; cat f; sed -i '1i titre' f; cat f", None),
    ("printf '2024-01-05 x\\n' | sed -E 's/^([0-9]{4})-([0-9]{2})-([0-9]{2})/\\3\\/\\2\\/\\1/'", None),
    ("printf 'n,t,a\\npix,eau,5\\nbou,feu,7\\n' > c.csv; awk -F, 'NR>1 {s+=$3; n++} END {print s/n}' c.csv", None),
    ("printf 'a b c\\nd e f\\n' | awk '{print $2, NF}'; printf '3\\n4\\n' | awk '{s+=$1} END {print s}'", None),
    ("awk 'BEGIN {printf \"%5.2f|%-4s|%d\\n\", 3.14159, \"ab\", 7}'", None),
    ("printf 'pix eau\\nbou feu\\npat eau\\n' | awk '{c[$2]++} END {for (k in c) print k, c[k]}' | sort", None),
    ("echo 'a b' | xargs echo x; printf 'f1\\nf2\\n' | xargs touch; ls", None),
    ("printf 'un\\ndeux\\n' | tee t.txt | wc -l; cat t.txt", None),
    ("printf 'a\\nb\\n' > a; printf '1\\n2\\n' > b; paste a b; paste -d: a b", None),
    ("echo -n a | sha256sum; echo bonjour | base64; echo Ym9uam91cgo= | base64 -d", None),
    ("echo -n A | xxd -b; echo -n bonjour | xxd", None),
    ("printf 'bonjour' > b; od -An -tx1 -N4 b", None),
    ("echo '2^12 / 125000' | bc -l; echo '3600 * 1 / 100' | bc; echo '300000000 / 2400000000' | bc -l", None),
    ("echo 'scale=3; 10/3' | bc; echo '7 % 3' | bc", None),
    ("mkdir -p x/y; touch x/y/z x/a; find x | sort; find x -type f | sort; find x -name 'z'", None),
    ("mkdir -p s; touch s/a.glitch s/b.txt; find . -name '*.glitch' -delete; find . | sort", None),
    ("touch f; chmod 444 f; ls -l f | cut -c1-10; echo x >> f; echo $?", None),
    ("touch f; chmod 755 f; ls -l f | cut -c1-10; chmod u-x,go-rx f; ls -l f | cut -c1-10; chmod a+r f; stat -c %a f", None),
    ("mkdir a; cp -r a b; ls; mv b c; ls; rmdir c; ls; rm -r a; ls", None),
    ("mkdir d; touch d/f; rmdir d; echo $?; rm d; echo $?", None),
    ("cp nope x; mv nope x; rm nope; echo fin", None),
    ("echo pomme > r.txt; cp r.txt s.txt; mv s.txt t.txt; ls; cat t.txt", None),
    ("mkdir boite; touch b.txt a.txt; ls; ls -a; ls -1", None),
    ("mkdir -p a/b; touch a/b/c; ls -R a", None),
    ("printf 'abc' > f; ls -l f | cut -d' ' -f1,2,5,9", None),
    ("printf '%s\\n' ligne1 ligne2 > l.txt; wc l.txt; wc -c l.txt; wc -l < l.txt", None),
    ("printf 'x\\n' > a; printf 'yy\\n' > b; wc -l a b", None),
    ("du -sh . >/dev/null; echo ok", None),
    ("echo \"il dit \\\"bonjour\\\"\" 'l'\\''eau'", None),
    ("a=1; b=2; echo \"$a$b\" '$a' \\$a", None),
    ("echo début; for i in 1 2; do echo $i; done > boucle.txt; cat boucle.txt", None),
    ("echo $0 | grep -c bash", None),
    ("tar czf s.tar.gz . 2>/dev/null; mkdir r; echo coucou > m.txt; tar czf a.tar.gz m.txt; tar xzf a.tar.gz -C r; cat r/m.txt", None),
    ("printf 'b\\na\\n' > x; sort x | diff - x; echo $?", None),
    ("mkdir -p e/n e/s; touch e/n/1 e/n/2 e/s/2; diff <(ls e/n) <(ls e/s)", None),
    ("echo 'un deux' | { read a b; echo \"$b $a\"; }", None),
    ("echo a; sleep 0.1; echo b", None),
    ("x=5; [ \"$x\" -lt 10 ] && echo vrai || echo faux; [ abc = abc ] && echo egal", None),
    ("printf 'z\\ny\\nx\\n' | sort | head -1; echo $PWD | grep -c terrain", None),
    ("echo $((0x1F)) $((010)) $((7/2)) $((-7%3))", None),
    ("printf 'a,b\\n' | awk -F, '{print $2 $1}'; awk 'BEGIN { x = 1; x += 2; print x * 2, x / 4 }'", None),
    ("printf 'l1\\nl2\\nl3\\n' | sed -n '1p;$p'; printf 'l1\\nl2\\nl3\\n' | sed -n '2,3p'", None),
    ("printf 'cle=1\\nCLE_API=x\\nfin\\n' > c; sed -i '/CLE_API/d' c; cat c", None),
    ("echo \"pierres : $(printf 'a\\nb\\n' | wc -l)\"", None),
    ("printf 'b 2\\na 10\\nc 1\\n' | sort -k2 -nr | head -2", None),
    ("printf 'x\\n' > f; cat f f f | uniq -c; cat -n f", None),
    ("echo $(( 1 + )) ; echo apres", None),
    ("if true; then; fi", None),
    ("echo 'non fini", None),
    ("for i in 1 2 3\ndo\n  echo $i\ndone", None),
    ("case abc in a*) echo A ;; esac; case x in y) echo y ;; *) echo defaut ;; esac", None),
    ("f() { echo \"f:$*\"; }; f a b; unset -f f; f 2>/dev/null || echo plus_de_f", None),
    ("echo $HOME | grep -c tg_vsh", None),
]


def syntaxe():
    print("2. La syntaxe du shell : le vrai bash et le terminal du jeu, côte à côte")
    for k, (cmd, prep) in enumerate(SYNTAXE):
        comparer(f"syntaxe#{k}", cmd, prep)


def windows():
    print("3. Le Linux virtuel de Windows (simulé) : les lieux du système, le terrain, les droits gardés")
    home = Path(tempfile.mkdtemp(prefix="tg_vsh_win_"))
    terrain = home / "terrain_terminagotchi"
    jeu = home / ".terminagotchi"
    (terrain / "vestibule").mkdir(parents=True)
    jeu.mkdir()
    (home / "Documents").mkdir()
    (home / "Documents" / "prive.txt").write_text("ne pas lire")
    vfs = Vfs(mode="windows", home=home, terrain=terrain, jeu=jeu, utilisateur="lea")
    c = CoquilleVirtuelle(vfs=vfs)
    s, code, d = c.lancer("pwd")
    verifier(s == "/home/lea\n" and d == str(home), f"pwd au démarrage : /home/lea (le jeu voit {d})")
    s, _c, _d = c.lancer("ls")
    verifier(s == "terrain_terminagotchi\n", f"ls dans ~ : seulement le terrain ({s.strip()!r}, pas Documents)")
    s, _c, _d = c.lancer("ls -a")
    verifier(".terminagotchi" in s and "Documents" not in s, "ls -a : ~/.terminagotchi, jamais les dossiers de Windows")
    s, _c, d = c.lancer("cd / && ls && pwd")
    verifier(s == "bin\ndev\netc\nhome\nproc\nroot\ntmp\nusr\nvar\n/\n", f"cd / ; ls ; pwd : les lieux du système ({s!r})")
    verifier(d == str(jeu / "systeme"), f"le jeu voit les lieux du système en vrais petits fichiers ({d})")
    s, _c, _d = c.lancer("ls /bin | grep -c -x ls; cat /etc/hostname | wc -l; ls -l /etc/hostname | cut -c1-10")
    verifier(s == "1\n1\n-rw-r--r--\n", f"/bin contient ls, /etc/hostname se lit, root en est le propriétaire ({s!r})")
    s, code, _d = c.lancer("echo x > /etc/hostname")
    verifier(code != 0 and "Permission denied" in s, f"écrire dans /etc : Permission denied ({s.strip()})")
    s, code, _d = c.lancer("touch ~/hors.txt; mkdir /tmp/ok && echo tmp_ok")
    verifier(not (home / "hors.txt").exists() and "Permission denied" in s and "tmp_ok" in s,
             "rien d'écrit dans ~ hors du terrain ; /tmp du jeu est permis")
    s, code, d = c.lancer("cd ~/terrain_terminagotchi/vestibule && mkdir nid && echo pomme > nid/repas.txt && cat nid/repas.txt")
    verifier(s == "pomme\n" and (terrain / "vestibule" / "nid" / "repas.txt").read_text() == "pomme\n"
             and d == str(terrain / "vestibule"), "le VRAI fichier du terrain est écrit (et le jeu voit le vrai dossier)")
    s, code, _d = c.lancer("chmod 444 nid/repas.txt; ls -l nid/repas.txt | cut -c1-10; echo poire >> nid/repas.txt; echo $?")
    verifier(s.startswith("-r--r--r--\n") and "Permission denied" in s and s.endswith("1\n"),
             f"chmod 444 gardé et respecté : Permission denied ({s!r})")
    s, code, _d = c.lancer("echo 'echo Miam' > miam.sh; ./miam.sh; chmod +x miam.sh; ./miam.sh")
    verifier("Permission denied" in s and s.endswith("Miam\n"), f"./miam.sh : refusé sans x, lancé avec chmod +x ({s!r})")
    s, code, _d = c.lancer("rm nid/repas.txt && ls nid | wc -l")
    verifier(s == "0\n", "rm d'un fichier en lecture seule (comme Linux, le dossier est à nous)")
    s, code, _d = c.lancer("cat ~/../lea/terrain_terminagotchi/vestibule/miam.sh; cd ../../.. ; pwd")
    verifier(s == "echo Miam\n/home\n", f"les chemins .. restent dans le Linux virtuel ({s!r})")
    s, code, _d = c.lancer("cd /home/lea/terrain_terminagotchi; ls -d */; whoami")
    verifier(s == "vestibule/\nlea\n", f"ls -d */ ; whoami ({s!r})")
    s, code, _d = c.lancer("ping -c 1 example.com")
    verifier(code == 127 and "terminal du jeu" in s, f"ping : la commande n'existe pas ici, c'est dit clairement ({s.strip()})")
    s, code, _d = c.lancer("Get-ChildItem")
    verifier(code == 127 and "ls" in s, f"un cmdlet de PowerShell : la commande Linux est proposée ({s.strip()})")
    shutil.rmtree(home, ignore_errors=True)


def git_vecteurs():
    """Le petit git du terminal du jeu contre le VRAI git (les scénarios de donnees/temps/vecteurs.json, comme
    tests/jvm/Temps.kt pour le téléphone)."""
    from tg.vsh import git as G
    v = json.loads((RACINE / "donnees" / "temps" / "vecteurs.json").read_text(encoding="utf-8"))["git"]
    print(f"4. Le petit git du terminal du jeu contre le VRAI git ({v.get('version')})")

    def rejouer(pas, nom):
        racine = Path(tempfile.mkdtemp(prefix="tg_vsh_git_"))
        tr = racine / "t"
        (tr / "temps").mkdir(parents=True)
        G.ETAT["afficher"] = lambda p: str(p).replace(str(tr), "{R}").replace("\\", "/")
        n_ok = 0
        for x in pas:
            ou = tr / x["ou"]
            if x["action"] == "git":
                G.ETAT["horloge"] = lambda d=x["date"]: (d, 0)
                r = G.executer(x["args"], ou, tr)
                att = x["sortie"].rstrip("\n")
                egal = r.texte.rstrip("\n") == att and r.code == x["code"]
                n_ok += egal
                if not egal:
                    verifier(False, f"{nom} : git {' '.join(x['args'])} [{x['ou']}]\n      petit ({r.code}) : "
                             f"{r.texte[:300]!r}\n      vrai  ({x['code']}) : {att[:300]!r}")
            elif x["action"] == "ecrire":
                f = ou / x["fichier"]
                with open(f, "a" if x["ajout"] else "w", encoding="utf-8", newline="") as h:
                    h.write(x["texte"])
            elif x["action"] == "grimoire":           # le jeu pose son grimoire avec le petit git (comme sur Windows)
                from tg import core, temps
                ancien_t, ancien_v = core.TERRAIN, os.environ.get("TG_TERMINAL_VIRTUEL")
                core.TERRAIN = tr
                os.environ["TG_TERMINAL_VIRTUEL"] = "1"
                try:
                    partie, born = x["graine"].split(":")
                    e = temps.poser_grimoire({"partie": partie, "born": int(born)})
                finally:
                    core.TERRAIN = ancien_t
                    if ancien_v is None:
                        os.environ.pop("TG_TERMINAL_VIRTUEL", None)
                    else:
                        os.environ["TG_TERMINAL_VIRTUEL"] = ancien_v
                verifier(e == "git", f"{nom} : le grimoire posé par le petit git ({e})")
            elif x["action"] == "lire":
                try:
                    l = (ou / x["fichier"]).read_text(encoding="utf-8")
                except OSError:
                    l = "?"
                verifier(l == x["texte"], f"{nom} : lire {x['fichier']}")
        G.ETAT["horloge"] = None
        G.ETAT["afficher"] = lambda p: p
        shutil.rmtree(racine, ignore_errors=True)
        return n_ok
    n = rejouer(v["album"], "album")
    verifier(True, f"l'album de la leçon : {n} commandes git identiques au vrai git")
    for g in v.get("grimoires", []):
        if isinstance(g, dict) and "pas" in g:
            rejouer(g["pas"], f"grimoire {g.get('graine')}")


PYTHON = [
    ('python3 -c "print(2 + 3 * 4)"', None),
    ("python3 s.py", "printf 'import sys\\nnom = sys.argv[1]\\nprint(nom)\\n' > s.py"),
    ("python3 s.py Pixel 3; echo $?", "printf 'import sys\\nnom = sys.argv[1]\\nprint(nom)\\n' > s.py"),
    ("python3 f.py; echo $?", "printf 'print(\\n' > f.py"),
    ("echo Léa | python3 -c \"print('Salut', input('Nom ? '))\"", None),
    ("python3 nope.py; echo $?", None),
    ("python3 -c 'import sys; print(sys.argv)' a 'b c'", None),
    ("printf 'print(1)\\n' | python3; python3 - x < s.py", "printf 'import sys\\nprint(sys.argv)\\n' > s.py"),
    ("python3 -c 'import sys; sys.exit(3)'; echo $?", None),
    ("python3 -c 'print(\"é\" * 3)' > o; cat o; wc -c o", None),
    ("python3 -c '1/0' 2>/dev/null; echo $?", None),
    ("python3 -c 'print(1); 1/0'", None),
    ("python3 -c 'print(1); 1/0' 2>&1 | tail -n 1", None),
    ("chmod +x p.py; ./p.py un", "printf '#!/usr/bin/env python3\\nimport sys\\nprint(\"shebang\", sys.argv[1:])\\n' > p.py"),
    ("./p.py", "printf '#!/usr/bin/env python3\\nprint(1)\\n' > p.py"),
    ("python3 -c \"import os; print(sorted(os.listdir('.')))\"", "touch b a; mkdir d"),
    ("python3 -c 'open(\"x.txt\", \"w\").write(\"a\\\\nb\\\\n\")'; cat x.txt; wc -l x.txt", None),
    ("python3 --version | cut -c1-9; python3 -V | wc -l", None),
    ("python3 -c \"raise SystemExit('fin')\"; echo $?", None),
    ("python3 -c \"import sys; print('err', file=sys.stderr); print('out')\" 2>/dev/null", None),
    ("python3 u.py", "printf 'def f():\\n    return 7\\n' > m.py; printf 'import m\\nprint(m.f())\\n' > u.py"),
    ("python3 -c 'for i in range(3):\n    print(\"Tour\", i)'", None),
    ("python3 -c 'try:\n    1/0\nexcept Exception:\n    raise ValueError(\"x\")'", None),
    ("python3 serpent.py Pixel 3 | head -n 2; python3 serpent.py 2>&1 | tail -n 1",
     "printf 'import sys\\nnom = sys.argv[1]\\nfois = int(sys.argv[2])\\nfor i in range(fois):\\n    print(f\"{i+1}. Bonjour {nom}\")\\n' > serpent.py"),
    ("seq 3 | python3 -c 'import sys; print(sum(int(l) for l in sys.stdin))'", None),
    ("python3 -c 'import json; print(json.dumps({\"a\": [1, 2]}))' | python3 -c 'import json,sys; print(json.load(sys.stdin)[\"a\"][1])'", None),
]

CURL = [
    "curl -I http://localhost:{P}/",
    "curl -s http://localhost:{P}/eau | head -n 3",
    "curl -o colis.html http://localhost:{P}/feu; cat colis.html",
    "curl -I http://localhost:{P}/volcan_perdu",
    "curl -s http://localhost:{P}/courrier",
    "curl -sv -o /dev/null http://127.0.0.1:{P}/feu",
    "curl -v localhost:{P}/",
    "curl -i localhost:{P}/feu",
    "curl -s -X POST -d a=1 localhost:{P}/ | head -n 3",
    "curl -i -X POST -d a=1 localhost:{P}/ | head -n 1",
    "curl -sf localhost:{P}/nope; echo $?",
    "curl -f localhost:{P}/nope",
    "curl -s -o /dev/null -w '%{{http_code}}\\n' localhost:{P}/nope",
    "curl -s -w '%{{content_type}} %{{size_download}}\\n' -o /dev/null localhost:{P}/feu",
    "curl -sO localhost:{P}/feu; cat feu",
    "curl -o sub/x localhost:{P}/feu; echo $?",
    "curl -O localhost:{P}/; echo $?",
    "curl; echo $?; curl --bogus; echo $?; curl -s; echo $?",
    "curl -H 'Accept: text/plain' -A moi -sv localhost:{P}/feu 2>&1 | grep '^>'",
    "curl -sI localhost:{P}/ | head -n 1; curl -s localhost:{P}/feu | wc -l",
    "curl localhost:{P}/feu localhost:{P}/eau | wc -l",
    "curl -sS -L localhost:{P}/eau | head -n 1",
]


def _norm_curl(s):
    s = re.sub(r"^\* Uses proxy env variable.*\n", "", s, flags=re.M)
    s = re.sub(r"^(< )?Date: [^\r\n]*", r"\1Date: @", s, flags=re.M)
    s = re.sub(r"^> User-Agent: [^\r\n]*", "> User-Agent: @", s, flags=re.M)
    # la barre de progression : les vitesses dépendent de l'instant (le reste doit être pareil)
    s = re.sub(r"(\r[ \d]{3} .{5}  [ \d]{3} .{5}  [ \d]{3} .{5})  .{5}  .{5} (\S+ \S+ \S+) .{5}", r"\1 @ \2 @", s)
    return s


def _phare():
    """Le phare du Port sur 127.0.0.1 (celui du jeu s'il est déjà allumé, sinon un phare pour ce test)."""
    from tg import port
    p = port._ports()[0]
    if port.phare_allume(p):
        return p, None
    from http.server import ThreadingHTTPServer
    import threading
    etat = {"vu": 0}
    srv = ThreadingHTTPServer(("127.0.0.1", p), port._gestionnaire(etat))
    etat["arreter"] = srv.shutdown
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True).start()
    return p, srv


def python_curl():
    print("5. python3 (le Python du jeu) et curl (le phare du Port) : comparés au vrai python3 et au vrai curl")
    if shutil.which("python3"):
        for k, (cmd, prep) in enumerate(PYTHON):
            comparer(f"python#{k}", cmd, prep)
    else:
        racontes.setdefault("python3 (absent de cet ordinateur)", []).append("python")
    if shutil.which("curl"):
        p, srv = _phare()
        try:
            for k, cmd in enumerate(CURL):
                comparer(f"curl#{k}", cmd.format(P=p), norm=_norm_curl)
        finally:
            if srv:
                srv.shutdown()
                srv.server_close()
    else:
        racontes.setdefault("curl (absent de cet ordinateur)", []).append("curl")
    garde()


def garde():
    """Ce que le terminal du jeu refuse (le vrai python3 et le vrai curl, eux, le feraient) : rien ne sort du terrain."""
    print("6. Les garde-fous de python3 et curl dans le terminal du jeu (rien hors du terrain, pas d'Internet)")
    home = Path(tempfile.mkdtemp(prefix="tg_vsh_garde_"))
    terrain = home / "terrain_terminagotchi"
    (terrain / "forge").mkdir(parents=True)
    (home / ".terminagotchi").mkdir()
    (home / "Documents").mkdir()
    (home / "Documents" / "prive.txt").write_text("secret")
    for mode in (("windows",) if os.name == "nt" else ("transparent", "windows")):
        vfs = Vfs(mode=mode, home=home, terrain=terrain, jeu=home / ".terminagotchi", utilisateur="lea")
        c = CoquilleVirtuelle(cwd=terrain / "forge" if mode == "transparent" else None, vfs=vfs, env=ENV)
        if mode == "windows":
            c.lancer("cd ~/terrain_terminagotchi/forge")
        pr = home / "Documents" / "prive.txt"
        hors = home / "hors.txt"
        cas = [
            (f"python3 -c 'open({json.dumps(str(hors))}, \"w\").write(\"x\")'", "PermissionError", 1),
            (f"python3 -c 'print(open({json.dumps(str(pr))}).read())'", "PermissionError", 1),
            (f"python3 -c 'import os; print(os.listdir({json.dumps(str(home))}))'", "PermissionError", 1),
            ("python3 -c 'import os; os.chdir(\"../..\")'", "PermissionError", 1),
            ("python3 -c 'import subprocess; subprocess.run([\"ls\"])'", "PermissionError", 1),
            ("python3 -c 'import os; os.system(\"ls\")'", "PermissionError", 1),
            ("python3 -c 'import urllib.request as u; u.urlopen(\"http://example.com\", timeout=2)'", "PermissionError", 1),
            ("python3 -c 'import socket; s = socket.socket(); s.bind((\"0.0.0.0\", 8000))'", "PermissionError", 1),
            ("python3 -m http.server 8000", "terminal du jeu", 1),
            ("python3 -m pip install x", "terminal du jeu", 1),
            (f"python3 {str(pr) if mode == 'transparent' else '~/Documents/prive.txt'}", "python3", 2),
            ("cd ~; python3 -c 'print(1)'", "terrain", 1),
            ("curl -I https://example.com", "Internet", 6),
            ("curl http://localhost:8000", "phare", 7),
            ("curl --cacert sceau_du_phare.pem https://localhost:8443", "phare", 7),
            ("curl file:///etc/passwd", "Internet", 6),
            ("curl http://127.42.0.2:8042/", "phare", 7),
        ]
        for cmd, attendu, code_att in cas:
            s, code, _d = c.lancer(cmd)
            verifier(attendu in s and code == code_att and not hors.exists(),
                     f"{mode} : `{cmd[:70]}` refusé ({code}, {s.strip().splitlines()[-1][:110] if s.strip() else ''!r})")
            if cmd.startswith("cd ~"):
                c.lancer("cd ~/terrain_terminagotchi/forge" if mode == "windows" else f"cd {terrain / 'forge'}")
        s, code, _d = c.lancer("python3 -c 'open(\"dans.txt\", \"w\").write(\"ok\\n\")'; cat dans.txt")
        verifier(s == "ok\n" and (terrain / "forge" / "dans.txt").read_bytes() == b"ok\n",
                 f"{mode} : python3 écrit dans le terrain, fins de ligne Linux ({s!r})")
        if mode == "windows":
            s, code, _d = c.lancer("printf 'print(1/0)\\n' > z.py; python3 z.py")
            verifier('File "/home/lea/terrain_terminagotchi/forge/z.py", line 1' in s and "print(1/0)" in s,
                     f"windows : le Traceback montre le chemin du terminal du jeu ({s.splitlines()[1:2]})")
            s, code, _d = c.lancer("printf 'import sys\\nprint(open(sys.argv[1]).read())\\n' > lis.py; "
                                   "python3 lis.py ~/terrain_terminagotchi/forge/dans.txt")
            verifier(s == "ok\n\n", f"windows : un chemin du terminal donné au programme est le vrai fichier ({s!r})")
        c.fermer()
    apres = sorted(os.listdir(home))
    verifier(apres == [".terminagotchi", "Documents", "terrain_terminagotchi"] and not hors.exists(),
             f"rien d'écrit hors du terrain et de ~/.terminagotchi ({apres})")
    shutil.rmtree(home, ignore_errors=True)


def main():
    tout = not any(a in sys.argv for a in ("--fiches", "--syntaxe", "--windows", "--git", "--python-curl", "--garde"))
    if tout or "--git" in sys.argv:
        git_vecteurs()
    if tout or "--fiches" in sys.argv:
        fiches()
    if tout or "--syntaxe" in sys.argv:
        syntaxe()
    if tout or "--windows" in sys.argv:
        windows()
    if tout or "--python-curl" in sys.argv:
        python_curl()
    elif "--garde" in sys.argv:                 # (la vraie machine Windows : pas de vrai bash pour comparer)
        garde()
    print(f"\nterminal du jeu : {ok} identiques au vrai bash, {ko} différences, "
          f"{sum(len(v) for v in racontes.values())} cas racontés ({', '.join(sorted(racontes))})")
    if ecarts:
        print("ÉCARTS :")
        for e in ecarts[:80]:
            print("  - " + e.split("\n")[0])
    sys.exit(1 if ko else 0)


if __name__ == "__main__":
    main()
