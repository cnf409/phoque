# phoque – keyboard-only TUI firewall (iptables)

![phoque_logo.png](https://raw.githubusercontent.com/cnf409/phoque/refs/heads/main/logo.png)

Lightweight Textual TUI that drives iptables with a pure-keyboard workflow. Rules are tagged so a re-apply cleans previously applied rules.

## Features
- Add/edit/delete Accept/Drop/Reject rules on INPUT/OUTPUT/FORWARD for TCP/UDP/ICMP.
- Ports: single (`80`), wildcard (`*` = all), range (`1000-2000` or `1000:2000`).
- Optional interface binding (`eth0`, `wlan0`, …) auto-mapped to `-i` (IN/FORWARD) or `-o` (OUT).
- Per-rule active flag (ON/OFF). New rules start OFF; toggling applies immediately.
- Toggle-all action: if all ON ➜ turn all OFF; all OFF ➜ turn all ON; mixed ➜ turn ON the remaining. Always applies after the change.
- Delete de-applies the rule before removal.
- JSON persistence in `data/rules.json`; tagged rules cleaned before every apply.

## Requirements
- Python 3.10+
- `textual` (see `requirements.txt`)
- Linux with iptables; root or `cap_net_admin` on the Python binary to modify firewall.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
# recommended: sudo or setcap so iptables commands succeed
sudo -E .venv/bin/python src/domain/main.py
# or give capabilities once:
# sudo setcap cap_net_admin,cap_net_raw=eip .venv/bin/python3
```

## Shortcuts (keyboard only)
- `[a]` add rule (↑/↓ select, Tab move, Enter submit, Esc cancel)
- `[e]` edit selected rule
- `[d]` delete selected rule (y/n confirm; de-applies first)
- `[x]` toggle selected rule ON/OFF (applies immediately)
- `[p]` toggle all (label changes to “untoggle all” or “toggle remaining” depending on state; applies immediately)
- `[t]` focus table
- `[q]` quit (`Ctrl+C` also quits)

## Rule fields
- Action: Accept / Drop / Reject
- Direction: IN / OUT / FORWARD
- Protocol: TCP / UDP / ICMP
- Port: number, `*`, or range `start-end` (TCP/UDP only; ignored for ICMP)
- Interface: optional `eth0`, `wlan0`, etc. (maps to `-i` for IN/FORWARD, `-o` for OUT)
- Active: ON/OFF indicator in the table (green/red)

## Data & cleanup
- Rules are stored in `data/rules.json`.
- Applied rules are tagged `phoque-<id>`; each apply removes previously tagged rules before re-adding active ones.

## UML diagram
See `diagramme_uml.png` for the domain architecture (Rule hierarchy, manager, storage).
