from __future__ import annotations

import platform
from typing import Dict, Type

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.widgets import RichLog, Static

from domain.manager import CommandExecutionError, FirewallManager
from domain.rules import AllowRule, DenyRule, RejectRule, Rule
from domain.types import Direction, Protocol
from infrastructure.storage import JsonDatabase
from .widgets import AddRuleScreen, ConfirmDialog, RuleForm, RuleTable


class FirewallApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    #banner { padding: 0 1; }
    #rules_table { height: 1fr; }
    #log { height: 10; border: solid #2f2f2f; padding: 0 1; }
    #help { color: #8a8a8a; padding: 0 1; }
    """

    BINDINGS = [
        ("q", "quit", "Quitter"),
        ("a", "add_rule", "Ajouter"),
        ("d", "delete_rule", "Supprimer"),
        ("e", "edit_rule", "Editer"),
        ("p", "apply_rules", "Appliquer"),
        ("t", "focus_table", "Focus table"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.manager = FirewallManager(JsonDatabase.get_instance())
        self._os_name = platform.system()

    def compose(self) -> ComposeResult:
        os_indicator = "🐧" if self._os_name == "Linux" else "🪟" if self._os_name == "Windows" else "💻"
        yield Static(f"phoque - firewall TUI {os_indicator} ({self._os_name})", id="banner")
        yield RuleTable(id="rules_table")
        yield RichLog(id="log", highlight=False, markup=True, wrap=False)
        yield Static(
            "Shortcuts: [a]dd, [e]dit, [d]elete, [p] apply, [t] focus table, [q] quit.",
            id="help",
            markup=False,
        )

    def on_mount(self) -> None:
        self.refresh_rules()
        self.query_one(RuleTable).focus_table()
        backend_info = "iptables" if self._os_name == "Linux" else "netsh advfirewall" if self._os_name == "Windows" else "unknown"
        self._log(f"Backend: {backend_info}. Use [a]/[d]/[p]/[q]; navigate with arrow keys.")

    def refresh_rules(self) -> None:
        table = self.query_one("#rules_table", RuleTable)
        table.update_rules(self.manager.rules)

    def _log(self, message: str, severity: str = "info") -> None:
        colors = {
            "info": "sky_blue3",
            "warning": "yellow1",
            "error": "red1",
            "success": "spring_green3",
        }
        color = colors.get(severity, "plum1")
        log = self.query_one("#log", RichLog)
        log.write(f"[{color}]{escape(message)}[/{color}]")

    def action_add_rule(self) -> None:
        self._log("Add rule: ↑/↓ to pick, Tab to move, Enter to submit, Esc to cancel.", severity="info")
        self.push_screen(AddRuleScreen(), self._handle_rule_creation)

    def action_focus_table(self) -> None:
        self.query_one(RuleTable).focus_table()

    def action_delete_rule(self) -> None:
        table = self.query_one("#rules_table", RuleTable)
        selected = table.get_selected_rule_id()
        if not selected:
            self._log("No rule selected", severity="warning")
            return
        msg = f"Delete rule {selected}? [y/n]"
        self.push_screen(ConfirmDialog(msg), lambda res: self._handle_delete_confirmation(res, selected))

    def action_apply_rules(self) -> None:
        self._apply_rules()

    def action_edit_rule(self) -> None:
        table = self.query_one("#rules_table", RuleTable)
        selected_id = table.get_selected_rule_id()
        if not selected_id:
            self._log("No rule selected", severity="warning")
            return
        rule = self.manager.get_rule(selected_id)
        if not rule:
            self._log("Rule not found", severity="warning")
            return
        self.push_screen(AddRuleScreen(initial_rule=rule), self._handle_rule_creation)

    def _handle_rule_creation(self, event: RuleForm.Submitted | None) -> None:
        if event is None:
            return
        action_raw = event.action
        direction_raw = event.direction.value
        protocol_raw = event.protocol.value
        port_raw = event.port if event.port is not None else None

        action_map: Dict[str, Type[Rule]] = {
            "allow": AllowRule,
            "deny": DenyRule,
            "reject": RejectRule,
        }
        rule_cls = action_map.get(action_raw.lower())
        if not rule_cls:
            self._log("Unknown action (allow/deny/reject)", severity="warning")
            return

        try:
            direction = Direction(direction_raw.upper())
        except ValueError:
            self._log("Invalid direction (in/out/forward)", severity="warning")
            return

        try:
            protocol = Protocol(protocol_raw.upper())
        except ValueError:
            self._log("Invalid protocol (tcp/udp/icmp)", severity="warning")
            return

        if protocol != Protocol.ICMP:
            if port_raw is None:
                self._log("Port required for TCP/UDP", severity="warning")
                return
            port = port_raw
        else:
            port = None

        try:
            rule = rule_cls(direction=direction, protocol=protocol, port=port)
        except ValueError as exc:
            self._log(str(exc), severity="warning")
            return

        if event.rule_id:
            updated = self.manager.update_rule(event.rule_id, rule)
            if updated:
                self.refresh_rules()
                self._log(
                    f"Updated: {rule.type_name} {rule.direction.value} {rule.protocol.value}"
                    + (f" port {rule.port}" if rule.port else ""),
                    severity="success",
                )
            else:
                self._log("Rule not found for update", severity="warning")
        else:
            self.manager.add_rule(rule)
            self.refresh_rules()
            self._log(
                f"Added: {rule.type_name} {rule.direction.value} {rule.protocol.value}"
                + (f" port {rule.port}" if rule.port else ""),
                severity="info",
            )

    def _remove_rule(self, rule_id: str) -> None:
        removed = self.manager.remove_rule(rule_id)
        if removed:
            self.refresh_rules()
            self._log("Rule deleted", severity="success")
        else:
            self._log("Rule not found", severity="warning")

    def _handle_delete_confirmation(self, confirmed: bool | None, rule_id: str) -> None:
        if confirmed:
            self._remove_rule(rule_id)
        else:
            self._log("Deletion cancelled", severity="info")

    def _apply_rules(self) -> None:
        try:
            commands = self.manager.apply_configuration(execute=True)
        except CommandExecutionError as exc:
            self._log(f"Apply failed: {exc.stderr}", severity="error")
            if self._os_name == "Windows":
                self._log("Hint: Run as Administrator for Windows Firewall changes.", severity="warning")
            elif self._os_name == "Linux":
                self._log("Hint: Run with sudo for iptables changes.", severity="warning")
            return
        if not commands:
            self._log("No rules to apply", severity="info")
        else:
            self._log(f"{len(commands)} rule(s) applied", severity="success")
