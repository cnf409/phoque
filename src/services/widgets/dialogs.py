from __future__ import annotations

from typing import Optional

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Static

from domain.rules import Rule


class ConfirmDialog(ModalScreen[bool]):
    BINDINGS = [("y", "yes", "Yes"), ("n", "no", "No"), ("escape", "no", "Cancel")]

    DEFAULT_CSS = """
    ConfirmDialog {
        align: center middle;
    }
    ConfirmDialog Vertical {
        width: 80;
        border: solid #3a3a3a;
        padding: 1 2;
    }
    ConfirmDialog .title {
        color: red;
        text-style: bold;
    }
    ConfirmDialog .rule {
        margin-top: 1;
    }
    ConfirmDialog .buttons {
        margin-top: 1;
        color: #8a8a8a;
    }
    """

    def __init__(self, message: str, rule: Optional[Rule] = None) -> None:
        super().__init__()
        self.message = message
        self.rule = rule

    def compose(self) -> ComposeResult:
        """Simple yes/no modal."""
        summary = self._build_rule_summary()
        yield Vertical(
            Static("Delete rule", classes="title"),
            Static(self.message),
            *([Static(summary, classes="rule", markup=False)] if summary else []),
            Static("[y]es / [n]o", classes="buttons", markup=False),
        )

    def action_yes(self) -> None:
        self.dismiss(True)

    def action_no(self) -> None:
        self.dismiss(False)

    def _build_rule_summary(self) -> Optional[Text]:
        if not self.rule:
            return None
        action_map = {
            "ALLOW": "#4ade80",  # green
            "DENY": "#facc15",   # yellow
            "REJECT": "#ef4444", # red
        }
        action_color = action_map.get(self.rule.type_name.upper(), "sky_blue3")
        summary = Text()
        summary.append("ID: ", style="bold")
        summary.append(self.rule.short_id, style="sky_blue3 bold")
        summary.append("  ")
        summary.append("Action: ", style="bold")
        summary.append(self.rule.type_name, style=action_color)
        summary.append("  ")
        summary.append("Direction: ", style="bold")
        summary.append(self.rule.direction.value, style="sky_blue3")
        summary.append("  ")
        summary.append("Protocol: ", style="bold")
        summary.append(self.rule.protocol.value, style="sky_blue3")
        if self.rule.port:
            summary.append("  ")
            summary.append("Port: ", style="bold")
            summary.append(self.rule.port, style="sky_blue3")
        if self.rule.interface:
            summary.append("  ")
            summary.append("Iface: ", style="bold")
            summary.append(self.rule.interface, style="sky_blue3")
        summary.append("  ")
        summary.append("Active: ", style="bold")
        summary.append("ON" if self.rule.active else "OFF", style="green" if self.rule.active else "red")
        return summary
