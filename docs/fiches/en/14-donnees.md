# 📊 Données

*The Data Room: sorting, counting, searching, databases (SQL)*

| | |
|---|---|
| **Duration** | about 25 min (3 lessons, 6 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `head`, `wc`, `cut`, `sort`, `sqlite3` |
| **Skills earned** | Data archivist, Sorter, SQL master |

## Objectives

- **The table** : a CSV file: a table written as text. Look at the beginning. (with `head`, `wc`)
- **Sorting and grouping** : how many creatures per family? (column 2) (with `cut`, `sort`)
- **The database** : store the table in a real database. (with `sqlite3`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Données » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. The table → skill « Data archivist »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/donnees/creatures.csv`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | A CSV file: a table written as text. Look at the beginning. | `head -n 5 monde/donnees/creatures.csv` | One line = one creature, commas separate the columns. |
| 2 | How many lines? | `wc -l monde/donnees/creatures.csv` | 15 lines: the header + 14 creatures. |

### 2. Sorting and grouping → skill « Sorter »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | How many creatures per family? (column 2) | `cut -d, -f2 monde/donnees/creatures.csv \| sort \| uniq -c` | cut cuts out a column, sort sorts, uniq -c counts: a real report. |
| 2 | The 3 biggest creatures (column 4, as numbers, in reverse). | `sort -t, -k4 -n -r monde/donnees/creatures.csv \| head -n 3` | Chaosmère, 12 m! -t, = separator, -k4 = column 4, -n = numbers. |

### 3. The database → skill « SQL master »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Store the table in a real database. | `sqlite3 monde/donnees/base.db ".import --csv monde/donnees/creatures.csv creatures"` | A database: tables you query with the SQL language. *Tip: If sqlite3 is missing: sudo apt install sqlite3* |
| 2 | Ask a question in SQL: how many per family? | `sqlite3 monde/donnees/base.db "SELECT famille, COUNT(*) FROM creatures GROUP BY famille;"` | SELECT … FROM … GROUP BY: the language of almost every database in the world. |

## Questions to check understanding

- What does the `head` command do? In which real-life situation would it help you?
- What does the `wc` command do? In which real-life situation would it help you?
- What does the `cut` command do? In which real-life situation would it help you?
- What does the `sort` command do? In which real-life situation would it help you?
- What does the `sqlite3` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
