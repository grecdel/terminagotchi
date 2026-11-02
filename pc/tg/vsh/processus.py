"""Le terminal du jeu : les processus SIMULÉS du jeu (Windows) — les fictifs de la Citadelle (miner_fictif…) et la
vague du Poste de Contrôle. `ps` les montre comme des processus, `kill PID` les arrête (le jeu le voit)."""


def processus_du_jeu():
    """[(pid, commande)] des processus simulés du jeu encore en vie."""
    out = []
    try:
        from .. import citadelle
        if citadelle._simules():
            for p in citadelle._pids():
                import time
                if p.get("simule") and p.get("fin", 0) > time.time():
                    out.append((p["pid"], p.get("args") or p["nom"]))
    except Exception:                       # noqa: BLE001 — jamais bloquant
        pass
    try:
        from .. import controle
        if controle.simulee():
            sec = controle.donnees()["vague"].get("secondes", 900)
            for pid, nom in controle.vivants():
                out.append((pid, f"{nom} {sec}"))
    except Exception:                       # noqa: BLE001
        pass
    return sorted(out)


def tuer(pid):
    """Arrête un processus simulé du jeu. Renvoie True s'il existait."""
    try:
        from .. import citadelle
        if citadelle._simules() and citadelle.tuer_simule(pid):
            return True
    except Exception:                       # noqa: BLE001
        pass
    try:
        from .. import controle, core
        if controle.simulee() and any(p == pid for p, _n in controle.vivants()):
            res = []
            core.modifier(lambda s: res.append(controle.arreter(s, pid)))
            return bool(res and res[0])
    except Exception:                       # noqa: BLE001
        pass
    return False
