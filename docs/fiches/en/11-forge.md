# 🔨 Forge

*The Forge: programming, your first game, your website, sound*

| | |
|---|---|
| **Duration** | about 25 min (3 lessons, 6 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `cat`, `python3`, `nano`, `echo` |
| **Skills earned** | Game maker, Web weaver, Sound maker |

## Objectives

- **My first game** : here is the code of a little game. Read it! (with `cat`, `python3`, `nano`)
- **My first website** : write a web page. (with `echo`, `python3`)
- **Making sound** : a sound = a wave of numbers. Run the program that makes an A note (440 Hz). (with `python3`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Forge » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. My first game → skill « Game maker »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/forge/devine.py`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Here is the code of a little game. Read it! | `cat monde/forge/devine.py` | random, input, if/else: 3 building blocks and you have a game. |
| 2 | Play! | `python3 monde/forge/devine.py` | You launched a Python program written in 8 lines. |
| 3 | Make it harder: change BORNE = 3 into BORNE = 10. | `nano monde/forge/devine.py` | You modified a game: that's how every programmer starts. *Tip: In nano: edit, then Ctrl+O, Enter (save) and Ctrl+X (quit).* |

### 2. My first website → skill « Web weaver »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Write a web page. | `echo '<h1>Le site de ma créature</h1>' > monde/forge/index.html` | <h1> = a big title. HTML puts text inside tags. |
| 2 | Start a little web server, open http://localhost:8000 in the browser, then Ctrl+C to stop it. | `python3 -m http.server 8000 -d monde/forge` | Your computer became a web server! A real website is just that, on a machine that is always on. |

### 3. Making sound → skill « Sound maker »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/forge/bip.py`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | A sound = a wave of numbers. Run the program that makes an A note (440 Hz). | `python3 monde/forge/bip.py` | 8000 samples per second of a sine wave: there's a sound file, made by you. |

## Questions to check understanding

- What does the `cat` command do? In which real-life situation would it help you?
- What does the `python3` command do? In which real-life situation would it help you?
- What does the `nano` command do? In which real-life situation would it help you?
- What does the `echo` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
