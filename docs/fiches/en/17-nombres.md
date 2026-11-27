# 🔢 Nombres

*The Bridges of Numbers: binary, hexadecimal, bytes, powers*

| | |
|---|---|
| **Duration** | about 15 min (2 lessons, 4 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `echo`, `printf` |
| **Skills earned** | Binary whiz, Byte weigher |

## Objectives

- **Binary** : a computer only knows 0 and 1. What is 101010 in binary worth? (with `echo`, `printf`)
- **Bytes** : a computer kilobyte is 2 to the power of 10 bytes. Compute 1024 × 1024. (with `echo`, `printf`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Nombres » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. Binary → skill « Binary whiz »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | A computer only knows 0 and 1. What is 101010 in binary worth? | `echo $((2#101010))` | 42! 32 + 8 + 2: each digit is worth double the previous one. |
| 2 | And 255 in hexadecimal (base 16)? | `printf '%x\n' 255` | ff: the #ff0000 (red) colours of web pages are hexadecimal! |

### 2. Bytes → skill « Byte weigher »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | A computer kilobyte is 2 to the power of 10 bytes. Compute 1024 × 1024. | `echo $((1024 * 1024))` | 1,048,576 bytes = 1 MiB. Bit, Byte, Kilo, Mega, Giga, Tera, Peta, Exa: ×1024 at each step. |
| 2 | chmod's 644 permissions are a base-8 number. What is 420 (decimal) in octal? | `printf '%o\n' 420` | 644 = rw-r--r--: 6 = 4+2 (read+write), 4 = read. Maths is everywhere in the terminal! |

## Questions to check understanding

- What does the `echo` command do? In which real-life situation would it help you?
- What does the `printf` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
