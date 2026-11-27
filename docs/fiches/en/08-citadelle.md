# 🛡 Citadelle

*The Citadel: defensive cybersecurity, simulated attacks, boxes to break into and then fix*

| | |
|---|---|
| **Duration** | about 40 min (4 lessons, 10 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `grep`, `ls`, `chmod`, `sha256sum`, `echo`, `rm` |
| **Skills earned** | Watchman, Rampart builder, Verifier, Ethical hacker |

## Objectives

- **The watch** : someone is trying to get into the Citadel! Look for failed logins in the log. (with `grep`)
- **The ramparts** : who can read the safe? Look at its permissions. (with `ls`, `chmod`)
- **The fingerprint** : take the report's fingerprint (SHA-256). (with `sha256sum`, `echo`)
- **The box to break into** : a training "box": a fake server to audit. Show ALL its files, even hidden ones. (with `ls`, `grep`, `rm`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Citadelle » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. The watch → skill « Watchman »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/citadelle/journal_auth.log`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Someone is trying to get into the Citadel! Look for failed logins in the log. | `grep Failed monde/citadelle/journal_auth.log` | "Failed password": failed passwords, one after another… |
| 2 | Who is attacking? Count the attempts per address. | `grep Failed monde/citadelle/journal_auth.log \| cut -d' ' -f11 \| sort \| uniq -c \| sort -rn` | 203.0.113.7 tried 5 times on root: a brute-force attack. We would block it at the firewall. |

### 2. The ramparts → skill « Rampart builder »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/citadelle/coffre.txt`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Who can read the safe? Look at its permissions. | `ls -l monde/citadelle/coffre.txt` | rw-r--r--: everybody can read it. Not great for a secret code! |
| 2 | Close the ramparts: only you can read and write. | `chmod 600 monde/citadelle/coffre.txt` | 600 = rw-------: the principle of least privilege. Everyone gets only what they need. |

### 3. The fingerprint → skill « Verifier »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/citadelle/rapport.txt`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Take the report's fingerprint (SHA-256). | `sha256sum monde/citadelle/rapport.txt` | 64 characters: this file's unique fingerprint. |
| 2 | A spy changes the report… | `echo 'tout va bien, ouvrez les portes' >> monde/citadelle/rapport.txt` | The text looks innocent… |
| 3 | Take the fingerprint again and compare. | `sha256sum monde/citadelle/rapport.txt` | Everything changed! That's how we check that a downloaded file hasn't been tampered with. |

### 4. The box to break into → skill « Ethical hacker »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/citadelle/boite/accueil.txt`, `~/terrain_terminagotchi/monde/citadelle/boite/.config`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | A training "box": a fake server to audit. Show ALL its files, even hidden ones. | `ls -a monde/citadelle/boite` | A hidden file, .config… suspicious. |
| 2 | Look for a forgotten password in the box. | `grep -r mot_de_passe monde/citadelle/boite` | Broken in! A password in plain text in a file: the most common security hole in the world. |
| 3 | Now fix it: delete this dangerous file. | `rm monde/citadelle/boite/.config` | Break in to learn, fix to protect: that's an ethical hacker's job. |

## Questions to check understanding

- What does the `grep` command do? In which real-life situation would it help you?
- What does the `ls` command do? In which real-life situation would it help you?
- What does the `chmod` command do? In which real-life situation would it help you?
- What does the `sha256sum` command do? In which real-life situation would it help you?
- What does the `echo` command do? In which real-life situation would it help you?
- What does the `rm` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
