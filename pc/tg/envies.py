"""Les 6 envies de la créature. Chacune baisse avec le temps et se comble avec un type de commande différent :

  🍖 faim        n'importe quelle commande tapée à la main (voir core.feed)
  🎲 jeu         echo, rev, figlet, les défis éclair, les jeux…
  🔎 curiosité   lire et chercher : cat, less, grep, find, man, --help…
  🧭 exploration se déplacer et regarder : cd, ls, tree, pwd…
  💤 sommeil     baisse un peu à chaque commande ; remonte quand on la laisse tranquille, ou avec « sleep »
  🧼 propreté    faire le ménage : rm, rmdir, mv, clear…

Les mêmes règles existent dans l'appli Android (Envies.kt).
"""
import random
import time

# id, icône, ce qu'elle veut faire, commandes qui la comblent, minutes pour perdre 1 point
ENVIES = [
    ("jeu", "🎲", "jouer", {"echo", "rev", "figlet", "toilet", "cowsay", "fortune", "sl", "cmatrix", "banner", "yes",
                           "lolcat", "doom", "jeu", "defi", "caresse", "danse", "parle", "joue", "devine"}, 8),
    ("curiosite", "🔎", "apprendre", {"man", "help", "info", "tldr", "whatis", "apropos", "cat", "less", "more", "head",
                                     "tail", "grep", "find", "which", "type", "file", "stat", "wc", "lexique",
                                     "get-help", "get-content", "select-string"}, 10),
    ("exploration", "🧭", "explorer", {"cd", "ls", "tree", "pwd", "dir", "du", "df", "get-childitem",
                                      "set-location", "get-location", "carte", "plan"}, 10),
    ("sommeil", "💤", "dormir", {"sleep", "start-sleep"}, 0),
    ("proprete", "🧼", "faire le ménage", {"rm", "rmdir", "mv", "clear", "cls", "trash", "trash-put", "gzip", "zip",
                                         "tar", "remove-item", "move-item", "clear-host"}, 12),
]
PAR_ID = {e[0]: e for e in ENVIES}
GAIN = 8                    # points regagnés par commande qui comble l'envie
FATIGUE = 0.4               # sommeil perdu à chaque commande
REPOS = 120                 # secondes de calme pour regagner 1 point de sommeil


def etat(state):
    env = state.setdefault("envies", {})
    for i, *_ in ENVIES:
        env.setdefault(i, 80.0)
    return env


def tick(state, maintenant=None):
    """Le temps passe : les envies baissent, le sommeil remonte pendant le calme."""
    now = maintenant or time.time()
    env = etat(state)
    dernier = state.get("envies_t", now)
    dt = max(0.0, now - dernier)
    for i, _, _, _, minutes in ENVIES:
        if minutes:
            env[i] = max(0.0, env[i] - dt / (60 * minutes))
    calme = now - state.get("derniere_cmd", now)
    if calme > REPOS:
        env["sommeil"] = min(100.0, env["sommeil"] + min(dt, calme - REPOS) / REPOS)
    state["envies_t"] = now


def commande(state, cmd, ligne=""):
    """Une commande tapée à la main : comble les envies qui lui correspondent. Renvoie le bonus d'XP."""
    env = etat(state)
    state["derniere_cmd"] = time.time()
    env["sommeil"] = max(0.0, env["sommeil"] - FATIGUE)
    bonus = 0
    for i, icone, verbe, cmds, _ in ENVIES:
        ok = cmd in cmds or (i == "curiosite" and "--help" in ligne)
        if not ok:
            continue
        gain = GAIN
        if i == "sommeil":                         # sleep 5 : se reposer 5 secondes, ça compte !
            try:
                gain = 4 + min(30, int(float(ligne.split()[1])) * 2)
            except (IndexError, ValueError):
                gain = 4
        avant = env[i]
        env[i] = min(100.0, env[i] + gain)
        if avant < 40:                             # elle en avait vraiment besoin
            bonus += 2
            from . import core
            core.log(state, f"{icone} merci, j'avais envie de {verbe} !")
    return bonus


def defi_reussi(state):
    env = etat(state)
    env["jeu"] = min(100.0, env["jeu"] + 15)


def la_plus_basse(state):
    env = etat(state)
    i = min(env, key=env.get)
    return PAR_ID[i], env[i]


def phrase(state):
    """Ce que la créature réclame quand une envie est basse, ou None."""
    (i, icone, verbe, cmds, _), v = la_plus_basse(state)
    if v >= 30:
        return None
    exemples = {"jeu": "echo, rev…", "curiosite": "cat, grep, man…", "exploration": "cd, ls, tree…",
                "sommeil": "laisse-moi tranquille un peu, ou tape « sleep 5 »", "proprete": "rm, mv, clear…"}[i]
    return random.choice([f"{icone} J'ai envie de {verbe}… ({exemples})", f"{icone} Et si on allait {verbe} ? ({exemples})"])


def barres(state, largeur=4):
    """Une ligne compacte : 🎲▰▰▰▱ 🔎▰▰▱▱ …"""
    env = etat(state)
    out = []
    for i, icone, *_ in ENVIES:
        n = max(0, min(largeur, round(largeur * env[i] / 100)))
        out.append(icone + "▰" * n + "▱" * (largeur - n))
    return " ".join(out)
