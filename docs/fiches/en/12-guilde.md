# 🛠 Guilde

*The Guild of Free Builders: open source, contributing, compiling*

| | |
|---|---|
| **Duration** | about 30 min (3 lessons, 7 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `head`, `grep`, `cp`, `sed`, `diff`, `cc`, `./monde/guilde/bonjour` |
| **Skills earned** | Journeyman, Contributor, Smelter |

## Objectives

- **The rules of free software** : every free project has a licence. Read the beginning of this one. (with `head`, `grep`)
- **My first contribution** : there's a typo in the project. First keep a copy of the original. (with `cp`, `sed`, `diff`)
- **Compiling** : c code must be translated into machine language: compile it. (with `cc`, `./monde/guilde/bonjour`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Guilde » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. The rules of free software → skill « Journeyman »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/guilde/LICENSE`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Every free project has a licence. Read the beginning of this one. | `head -n 3 monde/guilde/LICENSE` | MIT: one of the simplest licences. |
| 2 | What does it allow? Look for the word "use". | `grep -i use monde/guilde/LICENSE` | Use, copy, modify, share: the 4 freedoms of free software. |

### 2. My first contribution → skill « Contributor »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/guilde/projet/bonjour.txt`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | There's a typo in the project. First keep a copy of the original. | `cp monde/guilde/projet/bonjour.txt monde/guilde/projet/bonjour.orig` | The original is safe. |
| 2 | Fix "Bonjur" into "Bonjour". | `sed -i 's/Bonjur/Bonjour/' monde/guilde/projet/bonjour.txt` | Fixed! |
| 3 | Make the patch: the recipe of your fix. | `diff -u monde/guilde/projet/bonjour.orig monde/guilde/projet/bonjour.txt` | - the old line, + the new one: that's what you offer to a project (a "pull request"). Terminagotchi itself is free software: you can contribute to it! |

### 3. Compiling → skill « Smelter »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/guilde/bonjour.c`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | C code must be translated into machine language: compile it. | `cc monde/guilde/bonjour.c -o monde/guilde/bonjour` | The compiler turned your text into a program. *Tip: No compiler? sudo apt install gcc* |
| 2 | Run your compiled program. | `./monde/guilde/bonjour` | Linux, Firefox, Python… all compiled from code open to everyone. |

## Questions to check understanding

- What does the `head` command do? In which real-life situation would it help you?
- What does the `grep` command do? In which real-life situation would it help you?
- What does the `cp` command do? In which real-life situation would it help you?
- What does the `sed` command do? In which real-life situation would it help you?
- What does the `diff` command do? In which real-life situation would it help you?
- What does the `cc` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
