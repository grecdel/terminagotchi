# ⚓ Port

*Networks: addresses, ports, TCP/UDP, routing, home router, HTTPS*

| | |
|---|---|
| **Duration** | about 35 min (5 lessons, 9 steps) |
| **Audience** | from age 10; from age 7 with an adult (read the instructions aloud) |
| **Prerequisites** | the core lessons (finding your way, creating, reading, searching) |
| **Commands covered** | `ss`, `grep`, `curl`, `nslookup`, `ip`, `ping` |
| **Skills earned** | Captain, Switchman, Lighthouse keeper, Customs officer, Safe keeper |

## Objectives

- **The docks** : a machine has an address (IP) and numbered docks: the ports. Which ones are waiting for boats? (with `ss`, `grep`)
- **TCP and UDP** : watch a connection being made, in chatty mode. (with `curl`, `nslookup`)
- **The lighthouse** : which way do our packets leave? Look at the routing table. (with `ip`, `ping`)
- **The home router** : what is your address as seen from the internet? (with `curl`)
- **The padlock** : look at a website's certificate: its ID card. (with `curl`)

## Getting started

1. Each pupil (or pair) launches the game: `tg` on PC, the Terminagotchi app on a phone. Switch to English with `tg langue en` / `langue en`.
2. Choose the branch: press [a] then « Port » on PC, `arbre` on a phone.
3. Go into the playground: `cd ~/terrain_terminagotchi` (exercise paths start from there).
4. Commands are typed **by hand**: the game refuses copy-paste (on purpose).

## Lesson plan

### 1. The docks → skill « Captain »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | A machine has an address (IP) and numbered docks: the ports. Which ones are waiting for boats? | `ss -tuln` | LISTEN = a dock that is waiting. 22 = SSH, 53 = DNS, 80 = web, 443 = encrypted web. |
| 2 | The dock directory: find out what port 443 is for. | `grep -w 443 /etc/services` | https 443/tcp: every service has its dock number, the same all over the world. |

### 2. TCP and UDP → skill « Switchman »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Watch a connection being made, in chatty mode. | `curl -v https://example.com -o /dev/null` | "Connected to … port 443": TCP does a handshake (SYN, SYN-ACK, ACK) before talking. |
| 2 | DNS, on the other hand, sends a postcard (UDP). Ask a specific server: 1.1.1.1. | `nslookup example.com 1.1.1.1` | UDP, port 53: no handshake, faster, but no guarantee of arrival. |

### 3. The lighthouse → skill « Lighthouse keeper »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Which way do our packets leave? Look at the routing table. | `ip route` | "default" / 0.0.0.0: the gateway, the way out to the internet. At home, it's your router! |
| 2 | Send a signal to the gateway (the address on the "default" line). | `ping -c 2 192.168.1.1` | 1 or 2 ms: it's very close. It's the first relay of every one of your packets. *Tip: Replace 192.168.1.1 with your gateway's address.* |

### 4. The home router → skill « Customs officer »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | What is your address as seen from the internet? | `curl https://api.ipify.org` | Different from your local address: the router translates (NAT) the whole house into a single address. |

### 5. The padlock → skill « Safe keeper »

| Step | The creature asks | Expected command | What to explain |
|---|---|---|---|
| 1 | Look at a website's certificate: its ID card. | `curl -vI https://wikipedia.org` | subject, issuer, expire date: the certificate proves who the site is; then everything is encrypted (TLS). |
| 2 | Compare with a site over http (without the s). | `curl -vI http://example.com` | No certificate, no encryption: over http:// every relay can read. The padlock matters! |

## Questions to check understanding

- What does the `ss` command do? In which real-life situation would it help you?
- What does the `grep` command do? In which real-life situation would it help you?
- What does the `curl` command do? In which real-life situation would it help you?
- What does the `nslookup` command do? In which real-life situation would it help you?
- What does the `ip` command do? In which real-life situation would it help you?
- What does the `ping` command do? In which real-life situation would it help you?
- What surprised you during this session?

## Going further

- The **training room** (`tg entrainement` / `entrainement`) revises these commands against the clock.
- **Class mode** (census website → Class) lets you follow everyone's progress.
