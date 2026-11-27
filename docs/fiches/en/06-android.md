# 📱 Android

*Control your phone: apps, links, tools*

| | |
|---|---|
| **Duration** | about 60 min (4 lessons, 15 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `termux-toast`, `termux-vibrate`, `termux-torch`, `termux-open-url`, `am`, `pm`, `echo`, `source`, `ouvre`, `termux-battery-status`, `termux-tts-speak`, `termux-clipboard-set` |
| **Skills earned** | Remote control, Doorkeeper, Launcher, Butler |

## Objectives

- **Little powers** : make a little message appear on the screen. (with `termux-toast`, `termux-vibrate`, `termux-torch`)
- **Opening the world** : open a website in your browser. (with `termux-open-url`, `am`)
- **Launching any app** : every app has a secret name (its "package"). Find the one for Settings. (with `pm`, `am`, `echo`, `source`, `ouvre`)
- **The butler** : how is the battery doing? (with `termux-battery-status`, `termux-tts-speak`, `termux-clipboard-set`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Android » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. Little powers → skill « Remote control »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Make a little message appear on the screen. | `termux-toast "Coucou !"` | Termux:API connects the terminal to the phone's features. *Tip: You need the Termux:API app and: pkg install termux-api* |
| 2 | Make me vibrate! | `termux-vibrate -d 400` | -d = duration in milliseconds. |
| 3 | Turn on the flashlight… | `termux-torch on` | Light! Handy in the dark. |
| 4 | … and turn it off. | `termux-torch off` | You control the phone's hardware in one line. |

### 2. Opening the world → skill « Doorkeeper »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Open a website in your browser. | `termux-open-url https://fr.wikipedia.org` | Android picks the right app for this link by itself. |
| 2 | Look up a place on the map. | `am start -a android.intent.action.VIEW -d "geo:0,0?q=Tour Eiffel"` | An "intent" = a request sent to Android: "show me this". |
| 3 | Prepare a call (without calling!). | `am start -a android.intent.action.DIAL -d tel:0123456789` | DIAL opens the keypad with the number: you decide whether to call. |

### 3. Launching any app → skill « Launcher »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Every app has a secret name (its "package"). Find the one for Settings. | `pm list packages \| grep settings` | The Settings package is com.android.settings. |
| 2 | Launch Settings by its secret name. | `am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER com.android.settings` | MAIN + LAUNCHER = "open it as if from its icon". *Tip: If nothing opens: allow Termux to "display over other apps".* |
| 3 | That's long to type… invent your own "ouvre" command, forever! | `echo 'ouvre() { am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER "$1"; }' >> ~/.bashrc` | It's engraved in your configuration. |
| 4 | Reload your configuration. | `source ~/.bashrc` | Your "ouvre" command is ready. |
| 5 | Try it with any app! | `ouvre com.android.settings` | You launch your apps from the keyboard, like a pro. |

### 4. The butler → skill « Butler »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | How is the battery doing? | `termux-battery-status` | percentage = the percentage, status = charging or not. |
| 2 | Make me talk! | `termux-tts-speak "Bonjour, je suis ton Terminagotchi"` | I have a voice now! |
| 3 | Put some text in the clipboard. | `termux-clipboard-set "Coucou"` | Paste it wherever you like: it's in the clipboard. |

## Questions to check understanding

- What does the `termux-toast` command do? In which real-life situation would it help you?
- What does the `termux-vibrate` command do? In which real-life situation would it help you?
- What does the `termux-torch` command do? In which real-life situation would it help you?
- What does the `termux-open-url` command do? In which real-life situation would it help you?
- What does the `am` command do? In which real-life situation would it help you?
- What does the `pm` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
