from __future__ import annotations

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
        ("ctrl+c", "force_quit", "Quit (no prompt)"),
        ("x", "toggle_rule", "Toggle"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.manager = FirewallManager(JsonDatabase.get_instance())

    def compose(self) -> ComposeResult:
        yield Static("phoque - firewall TUI", id="banner")
        yield RuleTable(id="rules_table")
        yield RichLog(id="log", highlight=False, markup=True, wrap=False)
        yield Static("", id="help", markup=False)

    def on_mount(self) -> None:
        self.refresh_rules()
        self.query_one(RuleTable).focus_table()
        self._log("Use [a]/[e]/[d]/[x]/[p]/[t]/[q]; navigate with arrow keys.")

    def refresh_rules(self) -> None:
        table = self.query_one("#rules_table", RuleTable)
        table.update_rules(self.manager.rules)
        self._update_help_text()

    def _update_help_text(self) -> None:
        label = self._toggle_all_label()
        help_text = (
            f"Shortcuts: [a]dd, [e]dit, [d]elete, [x] toggle, [p] {label}, "
            "[t] focus table, [q] quit."
        )
        self.query_one("#help", Static).update(help_text)

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

    def action_force_quit(self) -> None:
        # Exit immediately without the Textual confirmation dialog.
        self.exit()

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

    def action_toggle_rule(self) -> None:
        table = self.query_one("#rules_table", RuleTable)
        selected_id = table.get_selected_rule_id()
        if not selected_id:
            self._log("No rule selected", severity="warning")
            return
        rule = self.manager.get_rule(selected_id)
        if not rule:
            self._log("Rule not found", severity="warning")
            return
        previous_state = rule.active
        rule.active = not rule.active
        self.manager.db.save(self.manager.rules)
        table.update_rules(self.manager.rules)
        state = "activated" if rule.active else "deactivated"
        self._log(f"Rule {state}", severity="info")
        # Apply immediately to reflect state change on system
        try:
            commands = self.manager.apply_configuration(execute=True)
            self._log(f"Applied {len(commands)} rule(s)", severity="success")
        except CommandExecutionError as exc:
            self._log(f"Apply failed: {exc.stderr}", severity="error")

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
            # New rules start inactive; let user toggle/apply explicitly.
            rule.active = False
            self.manager.add_rule(rule)
            self.refresh_rules()
            self._log(
                f"Added: {rule.type_name} {rule.direction.value} {rule.protocol.value}"
                + (f" port {rule.port}" if rule.port else "")
                + " (inactive by default)",
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
        if not self.manager.rules:
            self._log("No rules to toggle", severity="warning")
            return

        actives = [rule.active for rule in self.manager.rules]
        if all(actives):
            # All active -> deactivate all
            for rule in self.manager.rules:
                rule.active = False
            action_label = "deactivated"
        elif all(not state for state in actives):
            # All inactive -> activate all
            for rule in self.manager.rules:
                rule.active = True
            action_label = "activated"
        else:
            # Mixed -> activate only the inactive ones
            for rule in self.manager.rules:
                if not rule.active:
                    rule.active = True
            action_label = "activated (remaining)"

        self.manager.db.save(self.manager.rules)
        self.refresh_rules()

        try:
            commands = self.manager.apply_configuration(execute=True)
        except CommandExecutionError as exc:
            self._log(f"Apply failed: {exc.stderr}", severity="error")
            self._log("Hint: Run with sudo for iptables changes.", severity="warning")
            return
        self._log(f"All rules {action_label} and applied ({len(commands)} command(s))", severity="success")

    def _toggle_all_label(self) -> str:
        if not self.manager.rules:
            return "toggle all"
        actives = [rule.active for rule in self.manager.rules]
        if all(actives):
            return "untoggle all"
        if all(not state for state in actives):
            return "toggle all"
        return "toggle remaining"
