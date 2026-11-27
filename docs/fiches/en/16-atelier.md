# 🤖 Atelier

*The Workshop: Raspberry Pi, robots, embedded electronics*

| | |
|---|---|
| **Duration** | about 20 min (2 lessons, 5 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `cat`, `echo`, `for` |
| **Skills earned** | Electronics whiz, Sensor reader |

## Objectives

- **Lighting an LED** : on a Raspberry Pi, a pin (GPIO) is just a file! Look at the state of the LED wired to pin 17. (with `cat`, `echo`, `for`)
- **Reading a sensor** : read the temperature sensor. (with `cat`, `echo`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Atelier » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. Lighting an LED → skill « Electronics whiz »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/atelier/gpio17/value`, `~/terrain_terminagotchi/monde/atelier/gpio17/direction`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | On a Raspberry Pi, a pin (GPIO) is just a file! Look at the state of the LED wired to pin 17. | `cat monde/atelier/gpio17/value` | 0 = off. On Linux, "everything is a file", even an electrical pin. |
| 2 | Turn it on: write 1 into the file. | `echo 1 > monde/atelier/gpio17/value` | 💡 On! On a real Pi, current flows through the LED. |
| 3 | Make it blink 3 times. | `for i in 1 2 3; do echo 1 > monde/atelier/gpio17/value; sleep 1; echo 0 > monde/atelier/gpio17/value; sleep 1; done` | A blinking LED: the "Hello world" of electronics. |

### 2. Reading a sensor → skill « Sensor reader »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/atelier/capteur/temperature`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Read the temperature sensor. | `cat monde/atelier/capteur/temperature` | 21500 = 21.5 °C in millidegrees, just like /sys/class/thermal on a real Pi. |
| 2 | Convert to degrees. | `echo $(( $(cat monde/atelier/capteur/temperature) / 1000 ))` | A robot does this in a loop: read a sensor, compute, act (motor, LED…). |

## Questions to check understanding

- What does the `cat` command do? In which real-life situation would it help you?
- What does the `echo` command do? In which real-life situation would it help you?
- What does the `for` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
