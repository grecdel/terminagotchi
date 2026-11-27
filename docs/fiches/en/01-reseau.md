# 📡 Réseau

*Talking to the internet*

| | |
|---|---|
| **Duration** | about 30 min (3 lessons, 7 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `ping`, `ip`, `curl`, `head`, `nslookup`, `traceroute` |
| **Skills earned** | Radar, Postman, Cartographer |

## Objectives

- **The radar** : is the world out there? Send a little signal. (with `ping`, `ip`)
- **The postman** : knock on a website's door, without going in. (with `curl`, `head`)
- **The cartographer** : ask the internet's phone book for a site's address. (with `nslookup`, `traceroute`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Réseau » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. The radar → skill « Radar »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Is the world out there? Send a little signal. | `ping -c 3 example.com` | Each reply = a round trip. The time (ms) = the latency. |
| 2 | And what's our own address? | `ip a` | The IP address is our house number on the network. |

### 2. The postman → skill « Postman »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Knock on a website's door, without going in. | `curl -I https://example.com` | 200 = "come in!". 404 = not found. 500 = the site is sick. |
| 2 | From the playground, fetch me a parcel (a web page). | `curl -o colis.html https://example.com` | -o = "output": the reply is stored in a file. *Tip: First go into terrain_terminagotchi.* |
| 3 | Open the parcel: look at the first 5 lines. | `head -n 5 colis.html` | HTML: the language of web pages! |

### 3. The cartographer → skill « Cartographer »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Ask the internet's phone book for a site's address. | `nslookup example.com` | DNS translates names (example.com) into IP addresses. |
| 2 | Follow the path of our packets to the site. | `traceroute example.com` | Each line = one router crossed. The internet is a chain of relays! *Tip: If traceroute is missing: sudo apt install traceroute  (or try tracepath)* |

## Questions to check understanding

- What does the `ping` command do? In which real-life situation would it help you?
- What does the `ip` command do? In which real-life situation would it help you?
- What does the `curl` command do? In which real-life situation would it help you?
- What does the `head` command do? In which real-life situation would it help you?
- What does the `nslookup` command do? In which real-life situation would it help you?
- What does the `traceroute` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
