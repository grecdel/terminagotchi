# 🎛 Contrôle

*The Control Room: running a Linux system from A to Z*

| | |
|---|---|
| **Duration** | about 25 min (3 lessons, 6 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `id`, `cut`, `systemctl`, `journalctl`, `crontab`, `apt` |
| **Skills earned** | Caretaker, Stage manager, Clockmaker |

## Objectives

- **The residents** : who am I, and in which groups? (with `id`, `cut`)
- **The services** : which services are down? (with `systemctl`, `journalctl`)
- **Scheduled tasks** : which tasks come back on their own? (with `crontab`, `apt`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Contrôle » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. The residents → skill « Caretaker »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Who am I, and in which groups? | `id` | uid = your number, groups = your keys. sudo = the administrators' group. |
| 2 | Who else lives in the machine? | `cut -d: -f1 /etc/passwd` | Many "users" are services: each in its own room. |

### 2. The services → skill « Stage manager »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Which services are down? | `systemctl --failed` | A service = a program running in the background (web server, printing…). |
| 2 | Read the latest errors in the system log. | `journalctl -p err -n 20` | The log tells everything that happens: an admin's first reflex when something breaks. |

### 3. Scheduled tasks → skill « Clockmaker »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Which tasks come back on their own? | `crontab -l` | cron runs commands at set times: "0 3 * * *" = every day at 3 am. |
| 2 | Any updates waiting? | `apt list --upgradable` | Updating = plugging the holes. It's security rule number 1. |

## Questions to check understanding

- What does the `id` command do? In which real-life situation would it help you?
- What does the `cut` command do? In which real-life situation would it help you?
- What does the `systemctl` command do? In which real-life situation would it help you?
- What does the `journalctl` command do? In which real-life situation would it help you?
- What does the `crontab` command do? In which real-life situation would it help you?
- What does the `apt` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
