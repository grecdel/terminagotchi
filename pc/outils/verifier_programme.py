"""Le vérificateur de la charte de rigueur (docs/programme.md § 6.2 et § 7.1).

    python3 pc/outils/verifier_programme.py         code de sortie 1 en cas d'erreur

Vérifie donnees/programme.json :
  1. chaque fiche notion a ses champs (enfant, grands, vrai_terminal, limite_image, idees_fausses, sources ; relu_par
     présent, même vide) ; aucune fiche sans source ; les textes existent dans les 14 langues (PC et Android) ;
  2. chaque étape de leçon (PC : lecons.py et histoire.py ; Android : Histoire.kt, Jeu.kt, Arbre.kt, Port.kt, Citadelle.kt) renvoie à au
     moins une fiche (par le motif de la notion) ;
  3. aucune fiche n'est orpheline : chaque fiche sert au moins une étape (PC ou Android) ;
  4. les copies pc/tg/programme.json et app/src/main/assets/programme.json sont identiques à donnees/programme.json ;
  5. les Ponts des Nombres : prérequis connus, graphe sans boucle, fiches complètes (3 exemples, un exercice), et
     les maths déclarées par les étapes et les mondes existent ;
  6. les récompenses par monde : types connus (biomes.json), exploits nommés, variantes réservées dessinées dans le
     bestiaire ;
  7. les étapes du rejeu (« rejeu ») existent dans l'histoire du PC.
Le tirage n'est pas concerné (donnees/anti_triche) : les récompenses choisissent seulement parmi des tirages exacts.
"""
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "pc"))

from tg import histoire, lecons  # noqa: E402

CODES = ["fr", "en", "es", "de", "it", "pt", "zh", "ru", "ja", "hi", "ar", "bn", "id", "ur"]
erreurs = []


def err(m):
    erreurs.append(m)


def langues(dossier):
    return {c: json.loads((dossier / f"{c}.json").read_text(encoding="utf-8")) for c in CODES}


def etapes_pc():
    """{« leçon.étape » : commande} du PC (catalogue et histoire, étapes expertes comprises)."""
    ids = list(dict.fromkeys(list(lecons.PAR_ID) + list(histoire.NOUVELLES)))
    out = {}
    for lid in ids:
        for i, s in enumerate(histoire.lecon_def(lid)["steps"]):
            out[f"{lid}.{i}"] = s.get("cmd") or ""
    return out


_CHAINE = r'"((?:[^"\\]|\\.)*)"'


def etapes_android():
    """Les commandes des étapes Android, relues dans les sources Kotlin (le vrai catalogue est vérifié par
    tests/jvm/Programme.kt)."""
    out = []
    k = RACINE / "app/src/main/java/fr/terminagotchi"
    for f in ("Histoire.kt", "Jeu.kt", "Arbre.kt", "Port.kt", "Citadelle.kt"):
        src = (k / f).read_text(encoding="utf-8")
        for m in re.finditer(r'\b[na]\("\w+", \d+, ' + _CHAINE, src):
            out.append(m.group(1))
        for m in re.finditer(r'Etape\("[\w.]+", ' + _CHAINE, src):
            out.append(m.group(1))
        for m in re.finditer(r'entree\("(\w+)"\)', src):
            out.append(f"cd ~/terrain_terminagotchi/{m.group(1)}")
    return [c.replace('\\"', '"').replace("\\$", "$").replace("${Racine.HOME}", "/home/explorateur") for c in out]


def main():
    P = json.loads((RACINE / "donnees/programme.json").read_text(encoding="utf-8"))
    brut = (RACINE / "donnees/programme.json").read_bytes()
    for copie in ("pc/tg/programme.json", "app/src/main/assets/programme.json"):
        if (RACINE / copie).read_bytes() != brut:
            err(f"{copie} n'est pas identique à donnees/programme.json (recopier le fichier)")
    lpc, lan = langues(RACINE / "pc/tg/langues"), langues(RACINE / "app/src/main/assets/langues")

    def cle(k, ou, une_seule=False):
        """La clé existe dans les 14 langues, sur PC et sur Android (une_seule : sur au moins une des deux, pour
        l'image et la phrase des grands qui reprennent les textes propres à chaque lexique)."""
        for code in CODES:
            pc_, an_ = k in lpc[code], k in lan[code]
            if une_seule and (pc_ or an_):
                continue
            if not pc_:
                err(f"{ou} : la clé {k} manque en {code} (PC)")
                return
            if not an_:
                err(f"{ou} : la clé {k} manque en {code} (Android)")
                return

    # 1. les fiches
    notions = P["notions"]
    for nid, n in notions.items():
        for champ in ("motif", "enfant", "grands", "vrai_terminal", "limite_image", "idees_fausses", "sources"):
            if not n.get(champ):
                err(f"fiche {nid} : champ « {champ} » vide ou absent")
        if "relu_par" not in n:
            err(f"fiche {nid} : champ « relu_par » absent (null tant que personne n'a relu)")
        try:
            re.compile(n.get("motif", ""))
        except re.error as e:
            err(f"fiche {nid} : motif invalide ({e})")
        for k in [n.get("enfant"), n.get("grands")]:
            if k:
                cle(k, f"fiche {nid}", une_seule=True)
        for k in [n.get("limite_image")] + list(n.get("idees_fausses") or []):
            if k:
                cle(k, f"fiche {nid}")
        for c in n.get("vrai_terminal") or []:
            if not c.get("cmd") or not (c.get("rejeu") or "sortie" in c or "motif" in c):
                err(f"fiche {nid} : un cas vrai_terminal sans commande ou sans sortie attendue ({c})")
    # 2. chaque étape renvoie à une fiche
    pc = etapes_pc()
    an = etapes_android()
    servies = set()
    for ref, cmd in pc.items():
        ids = [nid for nid, n in notions.items() if re.search(n["motif"], cmd.strip())]
        if not ids:
            err(f"étape PC {ref} (`{cmd}`) : aucune fiche notion")
        servies |= set(ids)
    for cmd in an:
        ids = [nid for nid, n in notions.items() if re.search(n["motif"], cmd.strip())]
        if not ids:
            err(f"étape Android `{cmd}` : aucune fiche notion")
        servies |= set(ids)
    # 3. aucune fiche orpheline
    for nid in notions:
        if nid not in servies:
            err(f"fiche {nid} : orpheline (aucune étape PC ni Android ne s'en sert)")
    # 5. les Ponts des Nombres
    M = P.get("maths", {})
    for mid, n in M.items():
        for p in n.get("prerequis", []):
            if p not in M:
                err(f"maths {mid} : prérequis inconnu {p}")
        cle(n["titre"], f"maths {mid}")
        if n.get("fiche"):
            for champ in ("question", "enfant", "grands", "limite_image", "mots_cles"):
                if not n.get(champ):
                    err(f"maths {mid} : champ « {champ} » absent")
                else:
                    cle(n[champ], f"maths {mid}")
            if len(n.get("exemples", [])) != 3:
                err(f"maths {mid} : il faut 3 exemples résolus")
            for k in n.get("exemples", []) + n.get("idees_fausses", []) + [n["exercice"]["consigne"],
                                                                           n["exercice"]["erreur"]]:
                cle(k, f"maths {mid}")
            if not n.get("sources") or not n.get("vrai_terminal"):
                err(f"maths {mid} : sources ou vrai_terminal absents")

    def boucle(x, chemin):
        if x in chemin:
            err(f"maths : boucle dans les prérequis {' → '.join(chemin + [x])}")
            return
        for p in M.get(x, {}).get("prerequis", []):
            boucle(p, chemin + [x])
    for mid in M:
        boucle(mid, [])
    for ref, e in P.get("etapes", {}).items():
        lid, _, i = ref.rpartition(".")
        if ref not in pc and not any(f'"{lid}"' in s for s in [(RACINE / "app/src/main/java/fr/terminagotchi/Histoire.kt").read_text(encoding="utf-8")]):
            err(f"étape {ref} (maths) : inconnue")
        for m in e.get("maths", []):
            if m not in M:
                err(f"étape {ref} : notion de maths inconnue {m}")
    # 6. les récompenses
    biomes = json.loads((RACINE / "pc/tg/biomes.json").read_text(encoding="utf-8"))
    types = {t["id"] for t in biomes["types"]}
    best = json.loads((RACINE / "pc/tg/bestiaire.json").read_text(encoding="utf-8"))
    variantes = {v["id"] for e in best["especes"] for v in e["variantes"]}
    for m in P.get("mondes", []):
        for t in m.get("types", []):
            if t not in types:
                err(f"monde {m['id']} : type inconnu {t}")
        for mt in m.get("maths", []):
            if mt not in M:
                err(f"monde {m['id']} : notion de maths inconnue {mt}")
        for x in m.get("exploits", []):
            cle(x["nom"], f"exploit {x['id']}")
            if x.get("recompense") not in ("variante", "legendaire", "gardien"):
                err(f"exploit {x['id']} : récompense inconnue {x.get('recompense')}")
            if x.get("recompense") == "gardien":
                gid = m.get("gardiens", {}).get(x.get("boite"))
                if not any(e["id"] == gid and not e.get("secrete") for e in best["especes"]):
                    err(f"exploit {x['id']} : pas de gardien pour la boîte {x.get('boite')}")
            if x.get("recompense") == "variante" and not m.get("types"):
                err(f"exploit {x['id']} : une variante sans type de monde")
        gs = list(m.get("gardiens", {}).values())
        if len(set(gs)) != len(gs) or not all(any(e["id"] == g for e in best["especes"]) for g in gs):
            err(f"monde {m['id']} : gardiens inconnus ou en double {gs}")
        par_espece = {f"{e['id']}:{v['id']}" for e in best["especes"] for v in e["variantes"]}
        for v in m.get("variantes_reservees", []):
            if v not in variantes and v not in par_espece:
                err(f"monde {m['id']} : variante réservée inconnue {v}")
    # 7. le rejeu
    for ref in P.get("rejeu", {}):
        if ref not in pc:
            err(f"rejeu {ref} : étape inconnue dans l'histoire du PC")
    print(f"{len(notions)} fiches notions, {len(pc)} étapes PC, {len(an)} étapes Android, {len(M)} notions de maths, "
          f"{len(P.get('mondes', []))} mondes")
    for e in erreurs:
        print("  ✖", e)
    print("✔ programme conforme à la charte" if not erreurs else f"{len(erreurs)} erreur(s)")
    sys.exit(1 if erreurs else 0)


if __name__ == "__main__":
    main()
