from __future__ import annotations

from typing import List, Optional

from textual.app import ComposeResult
from textual.widgets import DataTable, Static

from domain.rules import Rule


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
