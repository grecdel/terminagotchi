# 🏭 Machines

*The Engine Room: hardware, boot, system, virtual machines, cloud*

| | |
|---|---|
| **Duration** | about 25 min (3 lessons, 6 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `lscpu`, `free`, `uptime`, `uname`, `systemd-detect-virt`, `ssh` |
| **Skills earned** | Mechanic, Awakener, Virtualizer |

## Objectives

- **Opening the hood** : what is the machine's brain (processor)? (with `lscpu`, `free`)
- **Waking up** : how long has the machine been awake? (with `uptime`, `uname`)
- **Machines inside the machine** : are we in a real machine… or a virtual machine? (with `systemd-detect-virt`, `ssh`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Machines » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. Opening the hood → skill « Mechanic »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | What is the machine's brain (processor)? | `lscpu` | Cores = the workers; frequency (GHz) = their speed. |
| 2 | And the working memory (RAM)? | `free -h` | RAM = the workbench (fast, wiped when switched off); the disk = the cupboard. |

### 2. Waking up → skill « Awakener »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | How long has the machine been awake? | `uptime` | At boot: firmware (BIOS/UEFI) → bootloader → kernel → services. |
| 2 | Which kernel (the heart of the system) runs all this? | `uname -a` | The kernel talks to the hardware; every program goes through it. |

### 3. Machines inside the machine → skill « Virtualizer »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Are we in a real machine… or a virtual machine? | `systemd-detect-virt` | "none" = a real machine. kvm, vmware, wsl… = a machine simulated by another: the basis of the cloud. |
| 2 | The cloud is thousands of virtual machines rented by the minute. Do you have the tool to connect to them? | `ssh -V` | SSH = the invisible cable to drive a machine remotely, in the cloud as at home. *Tip: If it's missing: sudo apt install openssh-client* |

## Questions to check understanding

- What does the `lscpu` command do? In which real-life situation would it help you?
- What does the `free` command do? In which real-life situation would it help you?
- What does the `uptime` command do? In which real-life situation would it help you?
- What does the `uname` command do? In which real-life situation would it help you?
- What does the `systemd-detect-virt` command do? In which real-life situation would it help you?
- What does the `ssh` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
