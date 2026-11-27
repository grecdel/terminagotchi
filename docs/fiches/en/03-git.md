# ⏳ Git

*The Library of Time: git, going back in time with your files (git required)*

| | |
|---|---|
| **Duration** | about 35 min (3 lessons, 9 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `git`, `cd`, `echo` |
| **Skills earned** | Archivist, Memory, Chronomancer |

## Objectives

- **My first repository** : from the playground, create a magic notebook that remembers everything. (with `git`, `cd`)
- **First memory** : write the first page of the journal. (with `echo`, `git`)
- **Time travel** : add a line to the journal. (with `echo`, `git`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Git » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. My first repository → skill « Archivist »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | From the playground, create a magic notebook that remembers everything. | `git init carnet` | A git repository! The hidden .git folder keeps the whole history. |
| 2 | Go into the notebook. | `cd carnet` | Here we are. |
| 3 | Ask it how it's doing. | `git status` | git status: the command pros type 100 times a day. |

### 2. First memory → skill « Memory »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Write the first page of the journal. | `echo "jour 1" > journal.txt` | The notebook has seen a new file… but isn't keeping it yet. |
| 2 | Get this page ready for the memory. | `git add journal.txt` | add = putting the page in the envelope. |
| 3 | Seal the memory! | `git commit -m "premier souvenir"` | A commit = a photo of your files at this moment. Forever. *Tip: If git asks for your name: git config --global user.name "Your name" (same for user.email)* |

### 3. Time travel → skill « Chronomancer »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Add a line to the journal. | `echo "jour 2" >> journal.txt` | The journal has changed… |
| 2 | What has changed since the memory? | `git diff` | + in green = added, - in red = removed. |
| 3 | Go back through our memories. | `git log` | Every memory has a unique ID. *Tip: Type q to leave the display.* |

## Questions to check understanding

- What does the `git` command do? In which real-life situation would it help you?
- What does the `cd` command do? In which real-life situation would it help you?
- What does the `echo` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
