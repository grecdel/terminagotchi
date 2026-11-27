# 🗝 Crypte

*The Crypt of Codes: cryptography, from ancient codes to the blockchain*

| | |
|---|---|
| **Duration** | about 30 min (4 lessons, 8 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `echo`, `tr`, `base64`, `sha256sum` |
| **Skills earned** | Centurion, Transcriber, Hasher, Chainsmith |

## Objectives

- **Caesar's code** : julius Caesar shifted each letter by 3. Encrypt BONJOUR. (with `echo`, `tr`)
- **The base64 parcel** : base64 turns anything into simple letters. Encode a word. (with `echo`, `base64`)
- **The magic fingerprint** : a.txt and b.txt differ by just one letter. Compare their fingerprints. (with `sha256sum`)
- **The blockchain by hand** : write the first block of the ledger. (with `echo`, `sha256sum`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Crypte » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. Caesar's code → skill « Centurion »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/crypte/message.txt`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Julius Caesar shifted each letter by 3. Encrypt BONJOUR. | `echo BONJOUR \| tr 'A-Z' 'D-ZA-C'` | ERQMRXU: unreadable… except for whoever knows the key (3). |
| 2 | An encrypted message awaits you in the crypt. Decrypt it! | `tr 'D-ZA-C' 'A-Z' < monde/crypte/message.txt` | Only 26 possible keys: a computer breaks Caesar in the blink of an eye. |

### 2. The base64 parcel → skill « Transcriber »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/crypte/colis.b64`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Base64 turns anything into simple letters. Encode a word. | `echo -n secret \| base64` | c2VjcmV0: this is NOT encryption, just wrapping. |
| 2 | Open the crypt's parcel. | `base64 -d monde/crypte/colis.b64` | Anyone can unwrap it: base64 is for carrying, not for hiding. |

### 3. The magic fingerprint → skill « Hasher »

*The game prepares the exercise files by itself: `~/terrain_terminagotchi/monde/crypte/a.txt`, `~/terrain_terminagotchi/monde/crypte/b.txt`.*

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | a.txt and b.txt differ by just one letter. Compare their fingerprints. | `sha256sum monde/crypte/a.txt monde/crypte/b.txt` | One letter changes, the whole fingerprint changes: the avalanche effect. And there's no going back. |

### 4. The blockchain by hand → skill « Chainsmith »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Write the first block of the ledger. | `echo 'bloc 1 : Alice donne 5 pommes à Bob' > monde/crypte/bloc1.txt` | Block 1 is in place. |
| 2 | Block 2 starts with the fingerprint of block 1. | `sha256sum monde/crypte/bloc1.txt > monde/crypte/bloc2.txt` | Block 2 is hooked onto block 1 by its fingerprint. |
| 3 | Add block 2's transaction. | `echo 'bloc 2 : Bob donne 2 pommes à Zoé' >> monde/crypte/bloc2.txt` | If someone tampers with block 1, its fingerprint changes and no longer matches block 2: the whole chain cries thief. That's a blockchain! |

## Questions to check understanding

- What does the `echo` command do? In which real-life situation would it help you?
- What does the `tr` command do? In which real-life situation would it help you?
- What does the `base64` command do? In which real-life situation would it help you?
- What does the `sha256sum` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
