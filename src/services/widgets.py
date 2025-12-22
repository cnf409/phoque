from __future__ import annotations

import socket
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from rich.text import Text
from textual import events
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.message import Message
from textual.screen import ModalScreen
from textual.widgets import DataTable, Input, OptionList, Static
from textual.widgets._option_list import Option

from domain.rules import Rule
from domain.types import Direction, Protocol


class RuleForm(Static):
    class Submitted(Message):
        def __init__(
            self,
            action: str,
            direction: Direction,
            protocol: Protocol,
            port: Optional[str],
            interface: Optional[str],
            rule_id: Optional[str] = None,
        ) -> None:
            super().__init__()
            self.action = action
            self.direction = direction
            self.protocol = protocol
            self.port = port
            self.interface = interface
            self.rule_id = rule_id

    class Cancelled(Message):
        pass

    BINDINGS = [("enter", "submit", "Valider"), ("escape", "cancel", "Annuler")]

    DEFAULT_CSS = """
    RuleForm {
        border: solid #3a3a3a;
        padding: 1;
    }
    RuleForm Select, RuleForm Input {
        margin-top: 1;
    }
    RuleForm #form_error {
        color: red;
        margin-top: 1;
    }
    RuleForm #interface_options {
        height: 5;
        margin-top: 1;
    }
    """

    def __init__(self, initial_rule: Optional[Rule] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self.initial_rule = initial_rule
        self._interfaces = self._load_interfaces()

    def compose(self) -> ComposeResult:
        """Build the add/edit form with action/direction/protocol/port/interface controls."""
        title = "Edit rule" if self.initial_rule else "Add rule"
        yield Static(f"{title} (↑/↓ to choose, Tab to move, Enter to submit, Esc to cancel)")
        if self.initial_rule:
            action_map = {
                "ALLOW": "#4ade80",  # green
                "DROP": "#facc15",   # yellow
                "REJECT": "#ef4444", # red
            }
            action_color = action_map.get(self.initial_rule.type_name.upper(), "sky_blue3")
            summary = Text()
            summary.append("ID: ", style="bold")
            summary.append(self.initial_rule.short_id, style="sky_blue3 bold")
            summary.append("  ")
            summary.append("Current: ", style="bold")
            summary.append(self.initial_rule.type_name, style=action_color)
            summary.append(" ")
            summary.append(self.initial_rule.direction.value, style="sky_blue3")
            summary.append(" ")
            summary.append(self.initial_rule.protocol.value, style="sky_blue3")
            if self.initial_rule.port:
                summary.append(f" {self.initial_rule.port}", style="sky_blue3")
            if self.initial_rule.interface:
                summary.append(f" [{self.initial_rule.interface}]", style="sky_blue3")
            yield Static(summary, classes="hint", markup=False)
        yield Static("", id="form_error")
        yield OptionList(Option("Accept", "allow"), Option("Drop", "deny"), Option("Reject", "reject"), id="action")
        yield OptionList(
            Option(Direction.IN.value, Direction.IN.value),
            Option(Direction.OUT.value, Direction.OUT.value),
            Option(Direction.FORWARD.value, Direction.FORWARD.value),
            id="direction",
        )
        yield OptionList(
            Option(Protocol.TCP.value, Protocol.TCP.value),
            Option(Protocol.UDP.value, Protocol.UDP.value),
            Option(Protocol.ICMP.value, Protocol.ICMP.value),
            id="protocol",
        )
        yield Input(placeholder="Port (empty for ICMP)", id="port")
        yield Input(placeholder="Interface (optional, type to filter)", id="interface")
        yield OptionList(*[Option(name, name) for name in self._interfaces], id="interface_options")

    def on_mount(self) -> None:
        self._highlight_defaults()
        self.query_one("#action", OptionList).focus()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        event.stop()

    def on_key(self, event: events.Key) -> None:
        """Handle Enter/Esc manually to avoid relying on focus state."""
        if event.key == "enter":
            focused = getattr(self.app, "focused", None)
            if focused and getattr(focused, "id", None) == "interface_options":
                if self._accept_interface_highlight():
                    event.stop()
                    return
            event.stop()
            self.action_submit()
        elif event.key == "escape":
            event.stop()
            self.action_cancel()

    def on_input_changed(self, event: Input.Changed) -> None:
        self.set_error(None)
        if getattr(event.input, "id", None) == "interface":
            self._filter_interface_options(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.action_submit()

    def action_cancel(self) -> None:
        self.post_message(RuleForm.Cancelled())

    def action_submit(self) -> None:
        """Collect the current selections and emit a Submitted message."""
        self.set_error(None)
        action_select = self.query_one("#action", OptionList)
        direction_select = self.query_one("#direction", OptionList)
        protocol_select = self.query_one("#protocol", OptionList)
        port_input = self.query_one("#port", Input)
        iface_input = self.query_one("#interface", Input)

        action = (action_select.highlighted_option or action_select.get_option_at_index(0)).id.lower()
        direction = Direction((direction_select.highlighted_option or direction_select.get_option_at_index(0)).id)
        protocol = Protocol((protocol_select.highlighted_option or protocol_select.get_option_at_index(0)).id)

        port_value = port_input.value.strip()
        port: Optional[str] = None
        if port_value:
            if port_value == "*":
                port = "*"
            elif "-" in port_value or ":" in port_value:
                port = port_value
            elif port_value.isdigit():
                port = port_value
            else:
                port = None

        interface_value = iface_input.value.strip()
        interface = interface_value or None

        rule_id = str(self.initial_rule.id) if self.initial_rule else None
        self.post_message(RuleForm.Submitted(action, direction, protocol, port, interface, rule_id=rule_id))

    def _highlight_defaults(self) -> None:
        defaults = {
            "action": None,
            "direction": None,
            "protocol": None,
            "port": "",
            "interface": "",
        }
        if self.initial_rule:
            defaults["action"] = self.initial_rule.type_name.lower()
            defaults["direction"] = self.initial_rule.direction.value
            defaults["protocol"] = self.initial_rule.protocol.value
            defaults["port"] = self.initial_rule.port or ""
            defaults["interface"] = self.initial_rule.interface or ""

        for opt_list, value in [
            ("action", defaults["action"]),
            ("direction", defaults["direction"]),
            ("protocol", defaults["protocol"]),
        ]:
            widget = self.query_one(f"#{opt_list}", OptionList)
            if value:
                for idx, option in enumerate(widget.options):
                    if option.id.lower() == value.lower():
                        widget.highlighted = idx
                        break
            if widget.highlighted is None and widget.option_count:
                widget.highlighted = 0

        port_input = self.query_one("#port", Input)
        port_input.value = defaults["port"]
        iface_input = self.query_one("#interface", Input)
        iface_input.value = defaults["interface"]
        self._filter_interface_options(iface_input.value)
        self.set_error(None)

    def _load_interfaces(self) -> List[str]:
        sysfs = Path("/sys/class/net")
        if sysfs.exists():
            names = [path.name for path in sysfs.iterdir() if path.is_dir()]
        else:
            try:
                names = [name for _, name in socket.if_nameindex()]
            except OSError:
                names = []
        return sorted({name for name in names if name}, key=str.lower)

    def _filter_interface_options(self, query: str) -> None:
        option_list = self.query_one("#interface_options", OptionList)
        previous = option_list.highlighted_option.id if option_list.highlighted_option else None
        needle = query.strip().lower()
        if needle:
            matches = [name for name in self._interfaces if needle in name.lower()]
        else:
            matches = list(self._interfaces)

        option_list.clear_options()
        for name in matches:
            option_list.add_option(Option(name, name))

        if not matches:
            option_list.highlighted = None
            return
        if previous and previous in matches:
            option_list.highlighted = matches.index(previous)
        else:
            option_list.highlighted = 0

    def _accept_interface_highlight(self) -> bool:
        option_list = self.query_one("#interface_options", OptionList)
        highlighted = option_list.highlighted_option
        if highlighted is None:
            return False
        iface_input = self.query_one("#interface", Input)
        iface_input.value = str(highlighted.id)
        iface_input.focus()
        return True

    def set_error(self, message: Optional[str]) -> None:
        error = self.query_one("#form_error", Static)
        error.update(message or "")


class AddRuleScreen(ModalScreen[Optional[RuleForm.Submitted]]):
    def __init__(
        self,
        initial_rule: Optional[Rule] = None,
        submit_handler: Optional[Callable[[RuleForm.Submitted], Tuple[bool, Optional[str]]]] = None,
    ) -> None:
        super().__init__()
        self.initial_rule = initial_rule
        self.submit_handler = submit_handler

    def compose(self) -> ComposeResult:
        """Wrap the rule form inside a modal."""
        yield Vertical(
            RuleForm(id="rule_form", initial_rule=self.initial_rule),
            Static("Tab to navigate, Enter to submit, Esc to cancel."),
        )

    def on_mount(self) -> None:
        self.set_focus(self.query_one(RuleForm))

    def on_rule_form_submitted(self, event: RuleForm.Submitted) -> None:
        if self.submit_handler:
            success, error = self.submit_handler(event)
            if success:
                self.dismiss(event)
            else:
                self.query_one(RuleForm).set_error(error or "Invalid values")
            return
        self.dismiss(event)

    def on_rule_form_cancelled(self, _: RuleForm.Cancelled) -> None:
        self.dismiss(None)


class ConfirmDialog(ModalScreen[bool]):
    BINDINGS = [("y", "yes", "Oui"), ("n", "no", "Non"), ("escape", "no", "Annuler")]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
        """Simple yes/no modal."""
        yield Vertical(
            Static(self.message),
            Static("[y] yes / [n] no"),
        )

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)


class RuleTable(Static):
    DEFAULT_CSS = """
    RuleTable DataTable {
        height: 1fr;
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._row_keys: List[str] = []
        self.table = DataTable(zebra_stripes=True)

    def compose(self) -> ComposeResult:
        """Create the rules data table with columns."""
        self.table.add_columns("ID", "Action", "Direction", "Protocol", "Port", "Iface", "Active")
        yield self.table

    def update_rules(self, rules: List[Rule]) -> None:
        """Refresh table rows from the given rules list."""
        self.table.clear(columns=False)
        self._row_keys = []
        for rule in rules:
            active_label = "[green]ON[/green]" if rule.active else "[red]OFF[/red]"
            self.table.add_row(
                rule.short_id,
                rule.type_name,
                rule.direction.value,
                rule.protocol.value,
                rule.port if rule.port is not None else "-",
                rule.interface or "-",
                active_label,
            )
            self._row_keys.append(str(rule.id))
        if self.table.row_count:
            self.table.cursor_coordinate = (0, 0)

    def get_selected_rule_id(self) -> Optional[str]:
        """Return the UUID string of the highlighted rule, or None."""
        coordinate = self.table.cursor_coordinate
        if coordinate is None:
            return None
        index = coordinate.row
        if 0 <= index < len(self._row_keys):
            return self._row_keys[index]
        return None

    def focus_table(self) -> None:
        """Give focus to the underlying DataTable."""
        self.table.focus()
