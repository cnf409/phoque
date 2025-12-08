from __future__ import annotations

from typing import Dict, Type

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
    #log { height: 5; border: solid #2f2f2f; padding: 0 1; }
    #help { color: #8a8a8a; padding: 0 1; }
    """

    BINDINGS = [
        ("q", "quit", "Quitter"),
        ("a", "add_rule", "Ajouter"),
        ("d", "delete_rule", "Supprimer"),
        ("p", "apply_rules", "Appliquer"),
        ("t", "focus_table", "Focus table"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.manager = FirewallManager(JsonDatabase.get_instance())

    def compose(self) -> ComposeResult:
        yield Static("phoque - firewall TUI (keyboard only)", id="banner")
        yield RuleTable(id="rules_table")
        yield RichLog(id="log", highlight=False, markup=False, wrap=False)
        yield Static(
            "Shortcuts: [a]dd, [d]elete, [p] apply, [t] focus table, [q] quit.",
            id="help",
            markup=False,
        )

    def on_mount(self) -> None:
        self.refresh_rules()
        self.query_one(RuleTable).focus_table()
        self._log("Use [a]/[d]/[p]/[q]; navigate with arrow keys.")

    def refresh_rules(self) -> None:
        table = self.query_one("#rules_table", RuleTable)
        table.update_rules(self.manager.rules)

    def _log(self, message: str, severity: str = "info") -> None:
        log = self.query_one("#log", RichLog)
        log.write(message)

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

    def _handle_rule_creation(self, event: RuleForm.Submitted | None) -> None:
        if event is None:
            return
        action_raw = event.action
        direction_raw = event.direction.value
        protocol_raw = event.protocol.value
        port_raw = str(event.port) if event.port is not None else None

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

        port: int | None = None
        if protocol != Protocol.ICMP:
            if port_raw is None:
                self._log("Port required for TCP/UDP", severity="warning")
                return
            try:
                port = int(port_raw)
            except ValueError:
                self._log("Port must be an integer", severity="warning")
                return

        try:
            rule = rule_cls(direction=direction, protocol=protocol, port=port)
        except ValueError as exc:
            self._log(str(exc), severity="warning")
            return

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
            self._log("Rule deleted", severity="info")
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
            return
        if not commands:
            self._log("No rules to apply", severity="info")
        else:
            self._log(f"{len(commands)} rule(s) applied", severity="info")
