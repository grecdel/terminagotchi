# ⚙ Système

*Watch over and master the machine*

| | |
|---|---|
| **Duration** | about 30 min (3 lessons, 7 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `whoami`, `ps`, `df`, `du`, `sleep`, `jobs`, `kill` |
| **Skills earned** | Lookout, Steward, Hunter |

## Objectives

- **The lookout** : who is in charge of this machine? (with `whoami`, `ps`)
- **The steward** : is there any room left in the attic (the disk)? (with `df`, `du`)
- **The hunter** : release a program that sleeps in the background. (with `sleep`, `jobs`, `kill`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Système » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. The lookout → skill « Lookout »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Who is in charge of this machine? | `whoami` | It's you! Your username. |
| 2 | Who is running inside the machine right now? | `ps aux` | Each line is a living program, with its number (PID). |

### 2. The steward → skill « Steward »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Is there any room left in the attic (the disk)? | `df -h` | -h = "human": readable sizes (GB, MB). |
| 2 | How much does our playground weigh? | `du -sh ~/terrain_terminagotchi` | Handy for finding what is filling up the disk. |

### 3. The hunter → skill « Hunter »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Release a program that sleeps in the background. | `sleep 300 &` | & = "in the background": the terminal stays free. |
| 2 | Spot it. | `jobs` | There it is, with its number. |
| 3 | Hunt it down! | `kill %1` | Program stopped. Handy when one of them is stuck! |

## Questions to check understanding

- What does the `whoami` command do? In which real-life situation would it help you?
- What does the `ps` command do? In which real-life situation would it help you?
- What does the `df` command do? In which real-life situation would it help you?
- What does the `du` command do? In which real-life situation would it help you?
- What does the `sleep` command do? In which real-life situation would it help you?
- What does the `jobs` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
