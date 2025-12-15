# phoque: the seal-tight TUI firewall

<img src="https://raw.githubusercontent.com/cnf409/phoque/refs/heads/main/logo.png" alt="phoque logo" width="280"/>

Keyboard-only firewall that lets you add and toggle iptables rules without touching the shell. Rules are tagged and reapplied cleanly each time.

- Supports TCP/UDP/ICMP, single/wildcard/range ports, optional interface binding.
- Rules persisted in `data/rules.json`; each rule is tagged `phoque-<id>` on apply for easy cleanup.
- Delete de-applies the rule; toggle-all flips every rule then reapplies.

Note: school project focused on OOP and good programming practices. The project is still evolving; expect frequent changes and new functionalities.

## Prerequisites
- Linux with iptables available.
- Python 3.10+.
- Ability to run iptables: sudo, or `setcap cap_net_admin,cap_net_raw=eip` on the Python binary.

## Installation 
1) Clone the repo  
```bash
git clone https://github.com/cnf409/phoque.git
cd phoque
```
2) Run the installer  
```bash
./install.sh
```
The script creates `.venv`, installs `requirements.txt`, and drops a `phoque` launcher in `/usr/local/bin` (sudo prompt if needed).

## Run
```bash
phoque                # uses sudo automatically if not root
```

## Uninstall
```bash
./uninstall.sh
```
Removes `/usr/local/bin/phoque` and the `.venv` created by the installer.

## Keyboard shortcuts
- `[a]` add rule (arrow keys / Tab / Enter / Esc)
- `[e]` edit rule
- `[d]` delete rule (y/n confirm; de-applies first)
- `[x]` toggle selected rule ON/OFF (applies immediately)
- `[p]` toggle all (auto-applies)
- `[t]` focus table
- `[q]` quit (`Ctrl+C` also quits)

## How it works
- Domain: `Rule` subclasses (Allow/Deny/Reject) build iptables commands; `FirewallManager` persists and applies them.
- Storage: `JsonDatabase` (`data/rules.json`).
- UI: `FirewallApp` (Textual) with modal forms, confirmation dialogs, and a rules table.
