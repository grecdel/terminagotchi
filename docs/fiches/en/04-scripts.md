# 🧪 Scripts

*Automate and create YOUR OWN commands*

| | |
|---|---|
| **Duration** | about 30 min (3 lessons, 7 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `echo`, `sh`, `chmod`, `alias`, `miam`, `source` |
| **Skills earned** | Cook, Inventor, Creator |

## Objectives

- **My first recipe** : from the playground, write a recipe in my nest. (with `echo`, `sh`)
- **My own command** : make the recipe executable. (with `chmod`, `alias`, `miam`)
- **Forever** : your command will disappear when the terminal closes. Make it eternal! (with `echo`, `source`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Scripts » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. My first recipe → skill « Cook »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | From the playground, write a recipe in my nest. | `echo 'echo "Miam !"' > nid/miam.sh` | A script = a list of commands stored in a file. |
| 2 | Cook the recipe! | `sh nid/miam.sh` | The script spoke! You just programmed. |

### 2. My own command → skill « Inventor »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Make the recipe executable. | `chmod +x nid/miam.sh` | x = executable: it's now a program. |
| 2 | Invent a command of your own: "miam". | `alias miam='sh ~/terrain_terminagotchi/nid/miam.sh'` | You just created a command that didn't exist! |
| 3 | Try it! | `miam` | YUM! It's the best command in the world. |

### 3. Forever → skill « Creator »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Your command will disappear when the terminal closes. Make it eternal! | `echo "alias miam='sh ~/terrain_terminagotchi/nid/miam.sh'" >> ~/.bashrc` | It's engraved in your configuration. *Tip: ~/.bashrc is read every time a terminal opens.* |
| 2 | Reload your configuration. | `source ~/.bashrc` | From now on, your own inventions feed me ×3! |

## Questions to check understanding

- What does the `echo` command do? In which real-life situation would it help you?
- What does the `sh` command do? In which real-life situation would it help you?
- What does the `chmod` command do? In which real-life situation would it help you?
- What does the `alias` command do? In which real-life situation would it help you?
- What does the `miam` command do? In which real-life situation would it help you?
- What does the `source` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
