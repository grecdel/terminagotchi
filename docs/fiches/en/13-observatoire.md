# 🔭 Observatoire

*The AI Observatory: how an AI learns, makes mistakes, and how to steer it*

| | |
|---|---|
| **Duration** | about 20 min (4 lessons, 5 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `grep`, `tr`, `sort`, `cat` |
| **Skills earned** | Statistician, Seer, Bias detector, AI pilot |

## Objectives

- **Learning by counting** : an AI learns from examples. How many positive reviews? (with `grep`, `tr`)
- **Predicting the next word** : after "le chat" (the cat), which word comes most often? (with `grep`)
- **When AI gets it wrong** : are the training examples balanced? Count. (with `sort`)
- **Steering an assistant** : read this well-written prompt for an AI assistant. (with `cat`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Observatoire » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. Learning by counting → skill « Statistician »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/ia/avis.txt`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | An AI learns from examples. How many positive reviews? | `grep -c positif monde/ia/avis.txt` | 5 positive ones. |
| 2 | Which words come up the most? Count them all. | `tr ' ' '\n' < monde/ia/avis.txt \| sort \| uniq -c \| sort -rn \| head` | "j'adore" (I love) goes with positive reviews: a model learns such links, over billions of texts. |

### 2. Predicting the next word → skill « Seer »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/ia/texte.txt`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | After "le chat" (the cat), which word comes most often? | `grep -o 'le chat [a-z]*' monde/ia/texte.txt \| sort \| uniq -c \| sort -rn` | "dort" (sleeps, 3 times): a language model predicts the most likely word. It doesn't "know", it computes. |

### 3. When AI gets it wrong → skill « Bias detector »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/ia/biais.txt`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Are the training examples balanced? Count. | `sort monde/ia/biais.txt \| uniq -c` | 4 "docteur : il" (he) for 1 "elle" (she): an AI trained on this will believe doctors are men. That's a bias: AI repeats the imbalances in its data. |

### 4. Steering an assistant → skill « AI pilot »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/ia/consigne.txt`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Read this well-written prompt for an AI assistant. | `cat monde/ia/consigne.txt` | Role, context, task, format, verification: a good prompt. And always check what the AI answers! |

## Questions to check understanding

- What does the `grep` command do? In which real-life situation would it help you?
- What does the `tr` command do? In which real-life situation would it help you?
- What does the `sort` command do? In which real-life situation would it help you?
- What does the `cat` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
