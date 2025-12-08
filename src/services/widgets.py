from __future__ import annotations

from typing import List, Optional

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
        def __init__(self, action: str, direction: Direction, protocol: Protocol, port: Optional[int]) -> None:
            super().__init__()
            self.action = action
            self.direction = direction
            self.protocol = protocol
            self.port = port

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
    """

    def compose(self) -> ComposeResult:
        yield Static("Add rule (↑/↓ to choose, Tab to move, Enter to submit, Esc to cancel)")
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

    def on_mount(self) -> None:
        self._highlight_defaults()
        self.query_one("#action", OptionList).focus()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        event.stop()

    def on_key(self, event: events.Key) -> None:
        if event.key == "enter":
            event.stop()
            self.action_submit()
        elif event.key == "escape":
            event.stop()
            self.action_cancel()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        event.stop()
        self.action_submit()

    def action_cancel(self) -> None:
        self.post_message(RuleForm.Cancelled())

    def action_submit(self) -> None:
        action_select = self.query_one("#action", OptionList)
        direction_select = self.query_one("#direction", OptionList)
        protocol_select = self.query_one("#protocol", OptionList)
        port_input = self.query_one("#port", Input)

        action = (action_select.highlighted_option or action_select.get_option_at_index(0)).id.lower()
        direction = Direction((direction_select.highlighted_option or direction_select.get_option_at_index(0)).id)
        protocol = Protocol((protocol_select.highlighted_option or protocol_select.get_option_at_index(0)).id)

        port_value = port_input.value.strip()
        port: Optional[int] = None
        if port_value:
            try:
                port = int(port_value)
            except ValueError:
                port = None

        self.post_message(RuleForm.Submitted(action, direction, protocol, port))

    def _highlight_defaults(self) -> None:
        for opt_list in ["action", "direction", "protocol"]:
            widget = self.query_one(f"#{opt_list}", OptionList)
            if widget.highlighted is None and widget.option_count:
                widget.highlighted = 0


class AddRuleScreen(ModalScreen[Optional[RuleForm.Submitted]]):
    def compose(self) -> ComposeResult:
        yield Vertical(
            RuleForm(id="rule_form"),
            Static("Tab to navigate, Enter to submit, Esc to cancel."),
        )

    def on_mount(self) -> None:
        self.set_focus(self.query_one(RuleForm))

    def on_rule_form_submitted(self, event: RuleForm.Submitted) -> None:
        self.dismiss(event)

    def on_rule_form_cancelled(self, _: RuleForm.Cancelled) -> None:
        self.dismiss(None)


class ConfirmDialog(ModalScreen[bool]):
    BINDINGS = [("y", "yes", "Oui"), ("n", "no", "Non"), ("escape", "no", "Annuler")]

    def __init__(self, message: str) -> None:
        super().__init__()
        self.message = message

    def compose(self) -> ComposeResult:
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
        self.table.add_columns("ID", "Action", "Direction", "Protocol", "Port")
        yield self.table

    def update_rules(self, rules: List[Rule]) -> None:
        self.table.clear(columns=False)
        self._row_keys = []
        for rule in rules:
            self.table.add_row(
                rule.short_id,
                rule.type_name,
                rule.direction.value,
                rule.protocol.value,
                rule.port if rule.port is not None else "-",
            )
            self._row_keys.append(str(rule.id))
        if self.table.row_count:
            self.table.cursor_coordinate = (0, 0)

    def get_selected_rule_id(self) -> Optional[str]:
        coordinate = self.table.cursor_coordinate
        if coordinate is None:
            return None
        index = coordinate.row
        if 0 <= index < len(self._row_keys):
            return self._row_keys[index]
        return None

    def focus_table(self) -> None:
        self.table.focus()
