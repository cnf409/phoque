# phoque - keyboard-only TUI firewall

A lightweight Textual TUI that wraps iptables/nftables-like rules with a simple keyboard workflow (add/delete/apply). Rules are tagged so re-applying cleans up previous state.

## Features
- Add/drop/reject rules on INPUT/OUTPUT/FORWARD with TCP/UDP/ICMP.
- Wildcard (`*`) or range (`1000-2000`) ports for TCP/UDP.
- JSON persistence (`data/rules.json`), auto-clean before apply via rule comments.
- Pure keyboard: shortcuts and modal dialogs, no mouse needed.

## Requirements
- Python 3.10+
- `textual` (see `requirements.txt`)
- Root or `cap_net_admin` on the Python binary to run iptables.

## Setup
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run
```bash
# recommend root or setcap to let iptables succeed
sudo -E .venv/bin/python src/domain/main.py
```

## Shortcuts
- `[a]` add rule (↑/↓ select, Tab move, Enter submit, Esc cancel)
- `[d]` delete selected rule (y/n confirm)
- `[p]` apply current rules (cleans previous tagged rules, then reapplies)
- `[t]` focus table
- `[q]` quit

## Rule inputs
- Action: Accept / Drop / Reject
- Direction: IN / OUT / FORWARD
- Protocol: TCP / UDP / ICMP
- Port (TCP/UDP): number (80), wildcard `*`, or range `1000-2000` (or `1000:2000`). ICMP ignores port.

## Notes on permissions
- iptables needs root. Either run with `sudo -E .venv/bin/python src/domain/main.py` or give caps:  
  `sudo setcap cap_net_admin,cap_net_raw=eip .venv/bin/python3`

## Data
- Rules are stored in `data/rules.json`. Tagged rules use comment `phoque-<id>` for cleanup on apply.

## UML diagram
See `diagramme_uml.png` for the domain architecture (Rule hierarchy, manager, storage).
