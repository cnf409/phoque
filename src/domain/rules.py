from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Optional, Type, Union
from uuid import UUID, uuid4

from .types import Direction, Protocol


@dataclass
class Rule(ABC):
    direction: Direction
    protocol: Protocol
    port: Optional[str] = None
    active: bool = True
    id: UUID = field(default_factory=uuid4)

    def __post_init__(self) -> None:
        if self.protocol != Protocol.ICMP:
            if self.port is None:
                raise ValueError("Port is required for TCP and UDP rules")
            self.port = self._normalize_port(self.port)
        else:
            if self.port is not None and self.port != "*":
                # ICMP ignores port, but allow "*" for consistency.
                self.port = None

    @property
    def type_name(self) -> str:
        return self.__class__.__name__.replace("Rule", "").upper()

    @property
    def short_id(self) -> str:
        return str(self.id).split("-")[0]

    @property
    def comment(self) -> str:
        return f"phoque-{self.short_id}"

    def _build_command(self, target: str) -> str:
        parts = [
            "iptables",
            "-A",
            self.direction.chain,
            "-p",
            self.protocol.cli_value,
        ]
        if self.protocol != Protocol.ICMP and self.port not in (None, "*"):
            parts += ["--dport", self._format_port_for_cli(self.port)]
        parts += ["-m", "comment", "--comment", self.comment]
        parts += ["-j", target]
        return " ".join(parts)

    def get_delete_command(self, target: str) -> str:
        # Switch append to delete; keep the same match criteria.
        return self._build_command(target).replace("iptables -A", "iptables -D", 1)

    @abstractmethod
    def get_command(self) -> str:
        ...

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": str(self.id),
            "direction": self.direction.value,
            "protocol": self.protocol.value,
            "port": self.port,
            "active": self.active,
            "type": self.__class__.__name__,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, str]) -> "Rule":
        rule_type = data.get("type")
        rule_cls = _RULE_TYPES.get(rule_type)
        if not rule_cls:
            raise ValueError(f"Unknown rule type: {rule_type}")
        port_value = data.get("port")
        return rule_cls(
            direction=Direction(data["direction"]),
            protocol=Protocol(data["protocol"]),
            port=str(port_value) if port_value is not None else None,
            active=bool(data.get("active", True)),
            id=UUID(data["id"]),
        )

    def _normalize_port(self, port: Union[str, int]) -> str:
        if isinstance(port, int):
            if not 0 < port <= 65535:
                raise ValueError("Port must be between 1 and 65535")
            return str(port)
        value = str(port).strip()
        if value == "*":
            return "*"
        if "-" in value or ":" in value:
            sep = "-" if "-" in value else ":"
            start_str, end_str = value.split(sep, 1)
            try:
                start = int(start_str)
                end = int(end_str)
            except ValueError:
                raise ValueError("Port range must be numeric, e.g. 1000-2000")
            if not (0 < start <= 65535 and 0 < end <= 65535 and start <= end):
                raise ValueError("Port range must be between 1 and 65535 and start<=end")
            return f"{start}:{end}"
        try:
            numeric = int(value)
        except ValueError:
            raise ValueError("Port must be an integer, range (start-end), or '*'")
        if not 0 < numeric <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return str(numeric)

    def _format_port_for_cli(self, port: str) -> str:
        return port.replace("-", ":")


class AllowRule(Rule):
    def get_command(self) -> str:
        return self._build_command("ACCEPT")

    def get_delete_command(self) -> str:
        return super().get_delete_command("ACCEPT")


class DenyRule(Rule):
    def get_command(self) -> str:
        return self._build_command("DROP")

    def get_delete_command(self) -> str:
        return super().get_delete_command("DROP")


class RejectRule(Rule):
    def get_command(self) -> str:
        return self._build_command("REJECT")

    def get_delete_command(self) -> str:
        return super().get_delete_command("REJECT")


_RULE_TYPES: Dict[str, Type[Rule]] = {
    "AllowRule": AllowRule,
    "DenyRule": DenyRule,
    "RejectRule": RejectRule,
}
