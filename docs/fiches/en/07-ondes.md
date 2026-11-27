# 📡 Ondes

*The Tower of Waves: radio, Wi-Fi, Bluetooth, LoRa and mesh networks*

| | |
|---|---|
| **Duration** | about 25 min (3 lessons, 6 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `python3`, `nmcli`, `rfkill`, `cat`, `grep` |
| **Skills earned** | Dowser, Radar operator, Mesh weaver |

## Objectives

- **Wavelength** : a wave makes ripples: length = speed of light ÷ frequency. Compute Wi-Fi's (2.4 GHz). (with `python3`)
- **The networks around me** : which Wi-Fi networks can you hear? (with `nmcli`, `rfkill`)
- **The mesh network** : with no antenna and no internet, LoRa radios (Meshtastic) relay each other. Read the mesh log. (with `cat`, `grep`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Ondes » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. Wavelength → skill « Dowser »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | A wave makes ripples: length = speed of light ÷ frequency. Compute Wi-Fi's (2.4 GHz). | `python3 -c "print(3e8 / 2.4e9)"` | 0.125 m: 12.5 cm. Antennas are often a quarter or half a wave long. |
| 2 | And LoRa, the radio of connected objects (868 MHz in Europe)? | `python3 -c "print(3e8 / 868e6)"` | 34.5 cm: a longer wave goes through walls and hills better. LoRa reaches kilometres! |

### 2. The networks around me → skill « Radar operator »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Which Wi-Fi networks can you hear? | `nmcli dev wifi list` | SSID = the name, SIGNAL: −30 dBm excellent, −80 weak. The channel = the lane within the frequency. *Tip: Without Wi-Fi (computer plugged in with a cable), the list may be empty: that's normal.* |
| 2 | Are the machine's radios switched on? | `rfkill list` | Wi-Fi, Bluetooth, 4G: every radio has its own switch. "Airplane mode" = everything off. |

### 3. The mesh network → skill « Mesh weaver »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/ondes/maillage.txt`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | With no antenna and no internet, LoRa radios (Meshtastic) relay each other. Read the mesh log. | `cat monde/ondes/maillage.txt` | Each node passes the message on to the next one: that's a mesh network. |
| 2 | How many relays? Count the "relayé" (relayed) lines. | `grep -c relayé monde/ondes/maillage.txt` | 3 relays for 4 km: in the mountains or after a storm, this saves lives. |

## Questions to check understanding

- What does the `python3` command do? In which real-life situation would it help you?
- What does the `nmcli` command do? In which real-life situation would it help you?
- What does the `rfkill` command do? In which real-life situation would it help you?
- What does the `cat` command do? In which real-life situation would it help you?
- What does the `grep` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
