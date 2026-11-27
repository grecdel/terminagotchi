# 🌱 Core lessons

*The basics: finding your way, creating and tidying, reading and searching, permissions*

| | |
|---|---|
| **Duration** | about 60 min (5 lessons, 15 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | none |
| **Commands covered** | `pwd`, `ls`, `cd`, `mkdir`, `echo`, `cat`, `grep`, `chmod`, `cp`, `mv`, `rm` |
| **Skills earned** | Compass, Builder, Inspector, Guardian, Cleaner |

## Objectives

- **Where am I?** : hi there! First question: where are we? (with `pwd`, `ls`, `cd`)
- **Building my nest** : i need a playground. Create it from your personal folder. (with `mkdir`, `cd`)
- **The pantry** : i'm hungry… put an apple in my pantry. (with `echo`, `cat`, `grep`)
- **The shield** : who is allowed to touch my meal? (with `ls`, `chmod`, `echo`)
- **Big clean-up** : make a backup copy of my meal. (with `cp`, `mv`, `rm`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Nothing to choose: the core lessons start by themselves.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. Where am I? → skill « Compass »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Hi there! First question: where are we? | `pwd` | pwd = "print working directory": the folder you are in. |
| 2 | Look at what's around us. | `ls` | Here are the files and folders in this place! |
| 3 | Let's go home (your personal folder). | `cd ~` | ~ means "my personal folder". You know how to get around! |

### 2. Building my nest → skill « Builder »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | I need a playground. Create it from your personal folder. | `mkdir terrain_terminagotchi` | mkdir = "make directory": create a folder. |
| 2 | Let's go inside. | `cd terrain_terminagotchi` | This is our home now. |
| 3 | Build me a nest! | `mkdir nid` | It's perfect! And I can hear noises outside… exploration is open! |

### 3. The pantry → skill « Inspector »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | I'm hungry… put an apple in my pantry. | `echo pomme > nid/repas.txt` | ">" sends text into a file (and overwrites it if it exists!). |
| 2 | Check what's inside. | `cat nid/repas.txt` | Always check before acting: a pro's reflex. |
| 3 | Search for the word "pomme" (apple) in the file. | `grep pomme nid/repas.txt` | Searching for a word in files: superpower unlocked. |

### 4. The shield → skill « Guardian »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Who is allowed to touch my meal? | `ls -l nid` | r = read, w = write, x = execute. |
| 2 | Protect it so nobody can spoil it! | `chmod 444 nid/repas.txt` | Shield on: the file is read-only. |
| 3 | Try adding a pear to it, just to see… | `echo poire >> nid/repas.txt` | Denied! ">>" appends to the end, but the shield holds. |

### 5. Big clean-up → skill « Cleaner »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Make a backup copy of my meal. | `cp nid/repas.txt nid/secours.txt` | cp = copy. The original doesn't move. |
| 2 | Move the copy into the playground, named reserve.txt. | `mv nid/secours.txt reserve.txt` | mv is used to move AND to rename. |
| 3 | We don't need it anymore: delete it. | `rm reserve.txt` | Careful: rm does NOT go through the trash. Always double-check first! *Tip: If it asks for confirmation, answer y.* |

## Questions to check understanding

- What does the `pwd` command do? In which real-life situation would it help you?
- What does the `ls` command do? In which real-life situation would it help you?
- What does the `cd` command do? In which real-life situation would it help you?
- What does the `mkdir` command do? In which real-life situation would it help you?
- What does the `echo` command do? In which real-life situation would it help you?
- What does the `cat` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
